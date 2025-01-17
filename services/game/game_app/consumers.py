import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
import asyncio
import jwt
from game_app import serializers
from game_app import models
import random
from django.db.models import Q
from asgiref.sync import sync_to_async


class GameConsumer(AsyncWebsocketConsumer):

    group_tasks = {}
    field_width = 600
    field_height = 400
    fps = 60
    ball_radius = field_width / 50
    paddle_height = field_height / 4
    paddle_width = field_width / 50
    paddle_move_amount = field_height / 50
    initial_dx = fps * field_width / 5
    initial_dy = fps * field_height / 5
    ball_speed_increment = 1.1
    is_colliding = False

    initial_game_state = {
        "ball": {
            "x": field_width / 2,
            "y": field_height / 2,
            "dx": initial_dx,
            "dy": initial_dy,
        },
        "left": {"paddle_y": field_height / 2, "score": 0},
        "right": {"paddle_y": field_height / 2, "score": 0},
    }

    async def connect(self):

        print("Connected to game consumer")
        await self.accept()
        if not await self.find_out_game():
            print("No game found")
            return

        self.redis = redis.from_url("redis://redis:6379")

        if not await self.initialize_game_state():
            return

        await self.add_connection_to_group()

        if self.game_group_name not in self.group_tasks:
            self.group_tasks[self.game_group_name] = asyncio.create_task(
                self.game_loop()
            )

        await self.save_and_broadcast_game_state()


    async def find_out_game(self):
        self.user_data = self.extract_user_data_from_jwt()
        print(f"User data: {self.user_data}")
        if not self.user_data or not self.user_data.get("user_id"):
            await self.send_error_and_close("Invalid user data")
            print("Invalid user data at find_out_game")
            return False

        try:
            await self.query_db_for_game()
        except models.Game.DoesNotExist:
            await self.send_error_and_close("User not registered in any game")
            print("User not registered in any game")
            return False
        except models.Game.MultipleObjectsReturned:
            await self.send_error_and_close("User registered in multiple games")
            print("User registered in multiple games")
            return False

        return True
    
    @sync_to_async
    def query_db_for_game(self):
        self.game = models.Game.objects.get(
                (
                    Q(left_player_id=self.user_data["user_id"])
                    | Q(right_player_id=self.user_data["user_id"])
                )
                & Q(is_finished=False)
            )

    def extract_user_data_from_jwt(self):
        user_data = {}
        headers = dict(self.scope["headers"])
        cookie_header = headers[b"cookie"]
        if cookie_header:
            for c in cookie_header.decode().split(";"):
                if "accessToken" in c:
                    jwt_token = c.split("=")[1]
                    try:
                        payload = jwt.decode(
                            jwt_token, options={"verify_signature": False}
                        )
                        user_data["username"] = payload.get("username")
                        user_data["user_id"] = payload.get("user_id")
                    except jwt.DecodeError as e:
                        print(f"Error decoding token: {e}")
                    break
        return user_data

    async def initialize_game_state(self):
        self.game_state = models.GameState.from_dict(self.initial_game_state)
        self.game_state.ball.dx *= random.choice([-1, 1])
        self.game_state.ball.dy *= random.choice([-1, 1])

        if not (await self.determine_controllers()):
            return False

        return True

    async def determine_controllers(self):
        if (
            self.game.left_player_id == self.user_data["user_id"]
            and self.game.right_player_id == self.user_data["user_id"]
        ):
            self.left_paddle_controller = ["letters"]
            self.right_paddle_controller = ["arrows"]
            return True
        if self.game.left_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = ["letters", "arrows"]
            self.right_paddle_controller = []
            if self.game.right_player_id == 0:
                self.right_paddle_controller.append("computer")
            return True
        if self.game.right_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = []
            self.right_paddle_controller = ["letters", "arrows"]
            if self.game.left_player_id == 0:
                self.left_paddle_controller.append("computer")
            return True

    async def add_connection_to_group(self):
        self.game_group_name = f"game_{self.game.id}"
        await self.channel_layer.group_add(self.game_group_name, self.channel_name)

    async def send_error_and_close(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))
        await self.close()

    async def save_and_broadcast_game_state(self):
        await self.redis.set(
            f"game:{self.game.id}", json.dumps(self.game_state.to_dict())
        )
        await self.channel_layer.group_send(
            self.game_group_name,
            {"type": "game_state_update", "game_state": self.game_state.to_dict()},
        )

    async def game_state_update(self, event):
        serializer = serializers.GameStateSerializer(data=event["game_state"])
        if not serializer.is_valid():
            print(f"Errors: {serializer.errors}")
            return
        self.game_state = models.GameState.from_dict(serializer.validated_data)
        await self.send(
            text_data=json.dumps(
                {"type": "game_state_update", "game_state": serializer.validated_data}
            )
        )

    async def disconnect(self, close_code):
        # Abandonar el grupo de canales
        if not hasattr(self, "game_group_name"):
            return
        await self.channel_layer.group_discard(self.game_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            event = json.loads(text_data)

            handlers = {"paddle_move": self.receive_paddle_update}

            if "type" in event:
                await handlers[event["type"]](event)

    async def receive_paddle_update(self, event):
        if not event.get("key"):
            return
        
        direction_multiplier = (
            1 if (event["key"] == "arrowDown" or event["key"] == "s") else -1
        )

        for controller in self.left_paddle_controller:
            if (controller == "letters" and event["key"] in ["w", "s"]) or (
                controller == "arrows" and event["key"] in ["arrowUp", "arrowDown"]
            ):
                self.game_state.left.paddle_y += (
                    self.paddle_move_amount * direction_multiplier
                )

        for controller in self.right_paddle_controller:
            if (controller == "letters" and event["key"] in ["w", "s"]) or (
                controller == "arrows" and event["key"] in ["arrowUp", "arrowDown"]
            ):
                self.game_state.right.paddle_y += (
                    self.paddle_move_amount * direction_multiplier
                )

        # Limit paddle movement
        self.game_state.left.paddle_y = max(
            self.paddle_height / 2,
            min(
                self.field_height - self.paddle_height / 2,
                self.game_state.left.paddle_y,
            ),
        )

        self.game_state.right.paddle_y = max(
            self.paddle_height / 2,
            min(
                self.field_height - self.paddle_height / 2,
                self.game_state.right.paddle_y,
            ),
        )

    def check_collisions(self):
        # Top and bottom walls
        if (
            self.game_state.ball.y - self.ball_radius <= 0
            or self.game_state.ball.y + self.ball_radius >= self.field_height
        ):
            self.game_state.ball.dy *= -1
            return

        # Left paddle
        if (
            self.game_state.ball.x - self.ball_radius <= self.paddle_width
            and self.game_state.ball.x - self.ball_radius > 0
            and not self.is_colliding
        ):
            if (
                self.game_state.ball.y
                >= self.game_state.left.paddle_y - self.paddle_height / 2
                and self.game_state.ball.y
                <= self.game_state.left.paddle_y + self.paddle_height / 2
            ):
                self.game_state.ball.dx *= -self.ball_speed_increment
                self.game_state.ball.dy *= self.ball_speed_increment
                self.is_colliding = True
                return

        # Right paddle
        if (
            self.game_state.ball.x + self.ball_radius
            >= self.field_width - self.paddle_width
            and self.game_state.ball.x + self.ball_radius < self.field_width
            and not self.is_colliding
        ):
            if (
                self.game_state.ball.y
                >= self.game_state.right.paddle_y - self.paddle_height / 2
                and self.game_state.ball.y
                <= self.game_state.right.paddle_y + self.paddle_height / 2
            ):
                self.game_state.ball.dx *= -self.ball_speed_increment
                self.game_state.ball.dy *= self.ball_speed_increment
                self.is_colliding = True
                return

        # Left and right walls
        if self.game_state.ball.x - self.ball_radius <= 0:
            self.game_state.left.score += 1
            self.game_state.ball.x = self.field_width / 2
            self.game_state.ball.y = self.field_height / 2
            self.game_state.ball.dx = -2
            self.game_state.ball.dy = random.choice([-2, 2])
            return
        if self.game_state.ball.x + self.ball_radius >= self.field_width:
            self.game_state.right.score += 1
            self.game_state.ball.x = self.field_width / 2
            self.game_state.ball.y = self.field_height / 2
            self.game_state.ball.dx = 2
            self.game_state.ball.dy = random.choice([-2, 2])
            return

        self.is_colliding = False

    async def game_loop(self):

        while True:
            # Mover la bola
            self.game_state.ball.x += self.game_state.ball.dx
            self.game_state.ball.y += self.game_state.ball.dy

            # Comprobar colisiones
            self.check_collisions()

            await self.save_and_broadcast_game_state()

            # Esperar hasta el siguiente frame
            await asyncio.sleep(1 / self.fps)
