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

    field_width = 600
    field_height = 400
    fps = 60
    ball_radius = field_width / 50
    paddle_height = field_height / 4
    paddle_width = field_width / 50
    paddle_move_amount = field_height / 50
    initial_ball_speed = field_height / 2 / fps
    ball_speed_increment = 1.1

    initial_game_state = {
        "ball": {
            "x": field_width / 2,
            "y": field_height / 2,
            "dx": initial_ball_speed,
            "dy": initial_ball_speed,
        },
        "left": {"paddle_y": field_height / 2, "score": 0},
        "right": {"paddle_y": field_height / 2, "score": 0},
    }

    async def connect(self):

        await self.accept()

        if not await self.find_out_game():
            return

        self.redis = redis.from_url("redis://redis:6379")

        await self.determine_controllers()

        await self.add_connection_to_group()

        await self.initialize_game_loop()

        await self.send_initial_information()

    async def find_out_game(self):
        self.user_data = self.extract_user_data_from_jwt()
        if not self.user_data or not self.user_data.get("user_id"):
            await self.send_error_and_close("Invalid user data")
            return False

        try:
            await self.query_db_for_game()
        except models.Game.DoesNotExist:
            await self.send_error_and_close("User not registered in any game")
            return False
        except models.Game.MultipleObjectsReturned:
            await self.send_error_and_close("User registered in multiple games")
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

    async def determine_controllers(self):
        if (
            self.game.left_player_id == self.user_data["user_id"]
            and self.game.right_player_id == self.user_data["user_id"]
        ):
            self.left_paddle_controller = ["letters"]
            self.right_paddle_controller = ["arrows"]

        if self.game.left_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = ["letters", "arrows"]
            self.right_paddle_controller = []
            if self.game.right_player_id == 0:
                self.right_paddle_controller.append("computer")

        if self.game.right_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = []
            self.right_paddle_controller = ["letters", "arrows"]
            if self.game.left_player_id == 0:
                self.left_paddle_controller.append("computer")

    async def add_connection_to_group(self):
        self.game_group_name = f"game_{self.game.id}"
        await self.channel_layer.group_add(self.game_group_name, self.channel_name)

    async def initialize_game_loop(self):
        print("initialize_game_loop")
        if not hasattr(self.channel_layer, "shared_tasks"):
            self.channel_layer.shared_tasks = {}
        if self.game_group_name not in self.channel_layer.shared_tasks:
            self.game_state = models.GameState.from_dict(self.initial_game_state)
            self.game_state.ball.dx *= random.choice([-1, 1])
            self.game_state.ball.dy *= random.choice([-1, 1])
            await self.redis.set(
                f"game:{self.game.id}:ball", json.dumps(self.game_state.ball.to_dict())
            )
            await self.redis.set(
                f"game:{self.game.id}:paddle:left",
                str(self.game_state.left.paddle_y),
            )
            await self.redis.set(
                f"game:{self.game.id}:paddle:right",
                str(self.game_state.right.paddle_y),
            )
            await self.redis.set(
                f"game:{self.game.id}:scores",
                json.dumps(
                    {
                        "left": self.game_state.left.score,
                        "right": self.game_state.right.score,
                    }
                ),
            )

            self.channel_layer.shared_tasks[self.game_group_name] = asyncio.create_task(
                self.shared_game_loop()
            )

    async def send_error_and_close(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))
        await self.close()

    async def send_initial_information(self):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "initial_information",
                    "usernames": {
                        "left_username": self.game.left_player_username,
                        "right_username": self.game.right_player_username,
                    },
                    "ball_state": self.game_state.ball.to_dict(),
                    "left_paddle_state": self.game_state.left.paddle_y,
                    "right_paddle_state": self.game_state.right.paddle_y,
                    "scores": {
                        "left": self.game_state.left.score,
                        "right": self.game_state.right.score,
                    },
                }
            )
        )

    async def save_and_broadcast_ball_state(self):
        await self.redis.set(
            f"game:{self.game.id}:ball", json.dumps(self.game_state.ball.to_dict())
        )
        await self.channel_layer.group_send(
            self.game_group_name,
            {"type": "ball_state_update", "ball_state": self.game_state.ball.to_dict()},
        )

    async def save_and_broadcast_left_paddle_state(self):
        await self.redis.set(
            f"game:{self.game.id}:paddle:left", str(self.game_state.left.paddle_y)
        )
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "left_paddle_state_update",
                "paddle_y": self.game_state.left.paddle_y,
            },
        )

    async def save_and_broadcast_right_paddle_state(self):
        await self.redis.set(
            f"game:{self.game.id}:paddle:right", str(self.game_state.right.paddle_y)
        )
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "right_paddle_state_update",
                "paddle_y": self.game_state.right.paddle_y,
            },
        )

    async def save_and_broadcast_scores_state(self):
        await self.redis.set(
            f"game:{self.game.id}:scores",
            json.dumps(
                {
                    "left": self.game_state.left.score,
                    "right": self.game_state.right.score,
                }
            ),
        )
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "scores_state_update",
                "scores": {
                    "left": self.game_state.left.score,
                    "right": self.game_state.right.score,
                },
            },
        )

    async def ball_state_update(self, event):
        self.game_state.ball = models.Ball.from_dict(event["ball_state"])
        await self.send(
            text_data=json.dumps(
                {"type": "ball_state_update", "ball_state": event["ball_state"]}
            )
        )

    async def left_paddle_state_update(self, event):
        self.game_state.left.paddle_y = event["paddle_y"]
        await self.send(
            text_data=json.dumps(
                {"type": "left_paddle_state_update", "paddle_y": event["paddle_y"]}
            )
        )

    async def right_paddle_state_update(self, event):
        self.game_state.right.paddle_y = event["paddle_y"]
        await self.send(
            text_data=json.dumps(
                {"type": "right_paddle_state_update", "paddle_y": event["paddle_y"]}
            )
        )

    async def scores_state_update(self, event):
        self.game_state.left.score = event["scores"]["left"]
        self.game_state.right.score = event["scores"]["right"]
        await self.send(
            text_data=json.dumps(
                {
                    "type": "scores_state_update",
                    "scores": event["scores"],
                }
            )
        )

    async def load_full_game_state(self):
        self.game_state.ball = models.Ball.from_dict(
                json.loads(await self.redis.get(f"game:{self.game.id}:ball"))
            )
        self.game_state.left.paddle_y = float(await self.redis.get(f"game:{self.game.id}:paddle:left"))
        self.game_state.right.paddle_y = float(await self.redis.get(f"game:{self.game.id}:paddle:right"))
        self.game_state.left.score = json.loads(await self.redis.get(f"game:{self.game.id}:scores"))["left"]
        self.game_state.right.score = json.loads(await self.redis.get(f"game:{self.game.id}:scores"))["right"]

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.game_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            event = json.loads(text_data)

            handlers = {"paddle_move": self.receive_paddle_update}

            if "type" in event:
                await handlers[event["type"]](event)

    async def receive_paddle_update(self, event):
        if not event.get("keys"):
            return

        self.game_state.left.paddle_y = float(await self.redis.get(f"game:{self.game.id}:paddle:left"))
        self.game_state.right.paddle_y = float(await self.redis.get(f"game:{self.game.id}:paddle:right"))

        for key in event["keys"]:
            direction_multiplier = 1 if key in ["arrowDown", "s"] else -1

            for controller in self.left_paddle_controller:
                if (controller == "letters" and key in ["w", "s"]) or (
                    controller == "arrows" and key in ["arrowUp", "arrowDown"]
                ):
                    self.game_state.left.paddle_y += (
                        self.paddle_move_amount * direction_multiplier
                    )
                    await self.save_and_broadcast_left_paddle_state()

            for controller in self.right_paddle_controller:
                if (controller == "letters" and key in ["w", "s"]) or (
                    controller == "arrows" and key in ["arrowUp", "arrowDown"]
                ):
                    self.game_state.right.paddle_y += (
                        self.paddle_move_amount * direction_multiplier
                    )
                    await self.save_and_broadcast_right_paddle_state()

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

    async def check_collisions(self):
        # Top and bottom walls
        if (
            self.game_state.ball.y - self.ball_radius <= 0
            or self.game_state.ball.y + self.ball_radius >= self.field_height
        ):
            self.game_state.ball.dy *= -1
            return

        # Left paddle
        self.check_paddle_collision(
            self.paddle_width,
            self.game_state.left.paddle_y,
            bounce_away_direction=1,
        )

        # Right paddle
        self.check_paddle_collision(
            self.field_width - self.paddle_width,
            self.game_state.right.paddle_y,
            bounce_away_direction=-1,
        )

        # Left wall
        if self.game_state.ball.x <= 0:
            self.game_state.right.score += 1
            self.game_state.ball.x = self.field_width / 2
            self.game_state.ball.y = self.field_height / 2
            self.game_state.ball.dx = self.initial_ball_speed  # Serve to the right
            self.game_state.ball.dy = random.choice([-1, 1]) * self.initial_ball_speed
            await self.save_and_broadcast_scores_state()
            return

        # Right wall
        if self.game_state.ball.x >= self.field_width:
            self.game_state.left.score += 1
            self.game_state.ball.x = self.field_width / 2
            self.game_state.ball.y = self.field_height / 2
            self.game_state.ball.dx = -self.initial_ball_speed  # Serve to the left
            self.game_state.ball.dy = random.choice([-1, 1]) * self.initial_ball_speed
            await self.save_and_broadcast_scores_state()
            return

    def check_paddle_collision(
        self, paddle_x_position, paddle_y_position, bounce_away_direction
    ):
        ball_left_border = self.game_state.ball.x - self.ball_radius
        ball_right_border = self.game_state.ball.x + self.ball_radius
        ball_top_border = self.game_state.ball.y - self.ball_radius
        ball_bottom_border = self.game_state.ball.y + self.ball_radius
        paddle_top_border = paddle_y_position - self.paddle_height / 2
        paddle_bottom_border = paddle_y_position + self.paddle_height / 2

        # If the ball is moving away from the paddle, it has already collided
        if bounce_away_direction * self.game_state.ball.dx > 0:
            return

        # If the ball is not within the paddle's x position, it can't collide
        if not (
            ball_left_border <= paddle_x_position
            and ball_right_border >= paddle_x_position
        ):
            return

        if (
            ball_top_border <= paddle_bottom_border
            and ball_bottom_border >= paddle_top_border
        ):
            self.game_state.ball.dx *= -self.ball_speed_increment
            self.game_state.ball.dy *= self.ball_speed_increment

    async def shared_game_loop(self):

        while True:
            await self.load_full_game_state()
            # Comprobar colisiones
            await self.check_collisions()

            # Mover la bola
            self.game_state.ball.x += self.game_state.ball.dx
            self.game_state.ball.y += self.game_state.ball.dy

            await self.save_and_broadcast_ball_state()

            # Esperar hasta el siguiente frame
            await asyncio.sleep(1 / self.fps)
