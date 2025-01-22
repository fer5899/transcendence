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
from game import settings as s


class PlayerConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        await self.accept()

        if not await self.find_out_game():
            return

        self.redis = redis.Redis(host="redis", port=6379)

        self.determine_controllers()

        self.update_game_state_task = asyncio.create_task(self.update_game_state())

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

    def determine_controllers(self):
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

    async def send_error_and_close(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))
        await self.close()

    async def load_game_state(self, redis_client):
        game_state_data = await redis_client.get(f"game:{self.game.id}")
        if game_state_data:
            game_state_serializer = serializers.GameStateSerializer(
                data=json.loads(game_state_data)
            )
            if game_state_serializer.is_valid():
                self.game_state = models.GameState.from_dict(
                    game_state_serializer.validated_data
                )
            else:
                raise Exception(f"Invalid game state: {game_state_serializer.errors}")
        else:
            raise Exception("Game state not found")

    async def save_game_state(self, redis_client):
        await redis_client.set(
            f"game:{self.game.id}", json.dumps(self.game_state.to_dict())
        )

    async def send_game_state(self):
        await self.send(
            text_data=json.dumps(
                {"type": "game_state_update", "game_state": self.game_state.to_dict()}
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "update_game_state_task"):
            self.update_game_state_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            event = json.loads(text_data)

            handlers = {"paddle_move": self.receive_paddle_update}

            if "type" in event:
                await handlers[event["type"]](event)

    async def receive_paddle_update(self, event):
        if not event.get("keys"):
            return

        async with self.redis.pipeline() as pipe:
            while True:
                try:
                    # Make sure we are the only ones updating the game state
                    await pipe.watch(f"game:{self.game.id}")

                    await self.load_game_state(pipe)

                    for key in event["keys"]:
                        direction_multiplier = 1 if key in ["arrowDown", "s"] else -1

                        for controller in self.left_paddle_controller:
                            if (controller == "letters" and key in ["w", "s"]) or (
                                controller == "arrows"
                                and key in ["arrowUp", "arrowDown"]
                            ):
                                self.game_state.left.paddle_y += (
                                    s.PADDLE_MOVE_AMOUNT * direction_multiplier
                                )

                        for controller in self.right_paddle_controller:
                            if (controller == "letters" and key in ["w", "s"]) or (
                                controller == "arrows"
                                and key in ["arrowUp", "arrowDown"]
                            ):
                                self.game_state.right.paddle_y += (
                                    s.PADDLE_MOVE_AMOUNT * direction_multiplier
                                )

                    # Limit paddle movement
                    self.game_state.left.paddle_y = max(
                        s.PADDLE_HEIGHT / 2,
                        min(
                            s.FIELD_HEIGHT - s.PADDLE_HEIGHT / 2,
                            self.game_state.left.paddle_y,
                        ),
                    )

                    self.game_state.right.paddle_y = max(
                        s.PADDLE_HEIGHT / 2,
                        min(
                            s.FIELD_HEIGHT - s.PADDLE_HEIGHT / 2,
                            self.game_state.right.paddle_y,
                        ),
                    )

                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    await self.save_game_state(pipe)
                    await pipe.execute()
                    break
                except redis.WatchError:
                    # Retry if someone else modified the game state
                    continue

    async def update_game_state(self):
        while True:
            await self.load_game_state(self.redis)

            await self.send_game_state()

            # Esperar hasta el siguiente frame
            await asyncio.sleep(1 / s.FPS)
