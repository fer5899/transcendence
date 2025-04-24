import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as redis
import asyncio
from django.db.models import Q
from asgiref.sync import sync_to_async
import time
import jwt

from game import settings as s
from game_app import serializers
from game_app import models
from game_app import utils

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayerConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:

            await self.accept()

            if not await self.find_out_game():
                return

            self.redis = redis.Redis(host="redis", port=6379, decode_responses=True)

            self.determine_controllers()
            self.last_paddle_update = 0

            await self.send_initial_information()

            self.update_game_state_task = asyncio.create_task(self.update_game_state())

        except Exception as e:
            logger.error(f"Error in connect: {e}", exc_info=True)

    def extract_user_data(self):
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b"cookie", b"")

        if cookie_header:
            for c in cookie_header.decode().split(";"):
                if "accessToken" in c:
                    jwt_token = c.split("=")[1]
                    try:
                        self.user_data = jwt.decode(jwt_token, options={"verify_signature": False})
                    except jwt.DecodeError as e:
                        logger.error(f"Error decoding token: {e}")
                    break

    async def find_out_game(self):
        self.extract_user_data()
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

    def determine_controllers(self):
        if (
            self.game.left_player_id == self.user_data["user_id"]
            and self.game.right_player_id == self.user_data["user_id"]
        ):
            self.left_paddle_controller = ["letters"]
            self.right_paddle_controller = ["arrows"]
        elif self.game.left_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = ["letters", "arrows"]
            self.right_paddle_controller = []
            if self.game.right_player_id == 0:
                self.right_paddle_controller.append("computer")
        elif self.game.right_player_id == self.user_data["user_id"]:
            self.left_paddle_controller = []
            self.right_paddle_controller = ["letters", "arrows"]
            if self.game.left_player_id == 0:
                self.left_paddle_controller.append("computer")

    async def send_initial_information(self):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "initial_information",
                    "game_id": self.game.id,
                    "left_player_id": self.game.left_player_id,
                    "right_player_id": self.game.right_player_id,
                    "left_player_username": self.game.left_player_username,
                    "right_player_username": self.game.right_player_username,
                    "tournament_id": self.game.tournament_id,
                    "field_height": s.FIELD_HEIGHT,
                    "field_width": s.FIELD_WIDTH,
                    "ball_radius": s.BALL_RADIUS,
                    "paddle_offset": s.PADDLE_OFFSET,
                    "paddle_radius": s.PADDLE_RADIUS,
                    "paddle_edge_angle_radians": s.PADDLE_EDGE_ANGLE_RADIANS,
                    "fps": s.FPS,
                }
            )
        )

    async def send_error_and_close(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))
        await self.close()

    async def load_game_state(self, redis_client: redis.Redis):
        ball_data = await redis_client.get(f"game:{self.game.id}:ball")

        left_paddle_data = await redis_client.get(f"game:{self.game.id}:left_paddle_y")

        right_paddle_data = await redis_client.get(
            f"game:{self.game.id}:right_paddle_y"
        )

        scores_data = await redis_client.get(f"game:{self.game.id}:scores")
        winner_username_data = await redis_client.get(
            f"game:{self.game.id}:winner_username"
        )
        is_finished_data = await redis_client.get(f"game:{self.game.id}:is_finished")
        start_countdown_data = await redis_client.get(
            f"game:{self.game.id}:start_countdown"
        )
        next_side_to_collide_data = await redis_client.get(
        f"game:{self.game.id}:next_side_to_collide"
    )

        if (
            ball_data
            and left_paddle_data
            and right_paddle_data
            and scores_data
            and is_finished_data
            and start_countdown_data
            and next_side_to_collide_data
        ):

            scores = json.loads(scores_data)
            game_state_data = {
                "ball": json.loads(ball_data),
                "left": {
                    "paddle_y": json.loads(left_paddle_data),
                    "score": scores["left"],
                },
                "right": {
                    "paddle_y": json.loads(right_paddle_data),
                    "score": scores["right"],
                },
                "winner_username": str(winner_username_data),
                "is_finished": int(is_finished_data),
                "start_countdown": int(start_countdown_data),
                "next_side_to_collide": str(next_side_to_collide_data),
            }

            game_state_serializer = serializers.GameStateSerializer(
                data=game_state_data
            )
            if game_state_serializer.is_valid():

                self.game_state = models.GameState.from_dict(
                    game_state_serializer.validated_data
                )

            else:

                raise Exception(f"Invalid game state: {game_state_serializer.errors}")
        else:
            raise Exception("Game state not found")

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

        if time.time() < self.last_paddle_update + 1 / s.FPS:
            return

        await self.load_game_state(self.redis)

        for key in event["keys"]:
            direction_multiplier = 1 if key in ["arrowDown", "s"] else -1

            for controller in self.left_paddle_controller:
                if (controller == "letters" and key in ["w", "s"]) or (
                    controller == "arrows" and key in ["arrowUp", "arrowDown"]
                ):
                    self.game_state.left.paddle_y += (
                        s.PADDLE_MOVE_AMOUNT * direction_multiplier
                    )
                    self.game_state.left.paddle_y = max(
                        s.PADDLE_HEIGHT / 2,
                        min(
                            s.FIELD_HEIGHT - s.PADDLE_HEIGHT / 2,
                            self.game_state.left.paddle_y,
                        ),
                    )
                    await self.redis.set(
                        f"game:{self.game.id}:left_paddle_y",
                        json.dumps(self.game_state.left.paddle_y),
                    )
                    if len(self.left_paddle_controller) == 2:
                        self.last_paddle_update = time.time()
                        return

            for controller in self.right_paddle_controller:
                if (controller == "letters" and key in ["w", "s"]) or (
                    controller == "arrows" and key in ["arrowUp", "arrowDown"]
                ):
                    self.game_state.right.paddle_y += (
                        s.PADDLE_MOVE_AMOUNT * direction_multiplier
                    )
                    self.game_state.right.paddle_y = max(
                        s.PADDLE_HEIGHT / 2,
                        min(
                            s.FIELD_HEIGHT - s.PADDLE_HEIGHT / 2,
                            self.game_state.right.paddle_y,
                        ),
                    )
                    await self.redis.set(
                        f"game:{self.game.id}:right_paddle_y",
                        json.dumps(self.game_state.right.paddle_y),
                    )
                    if len(self.right_paddle_controller) == 2:
                        self.last_paddle_update = time.time()
                        return

        self.last_paddle_update = time.time()

    async def update_game_state(self):
        while True:
            await self.load_game_state(self.redis)

            await self.send_game_state()

            # Esperar hasta el siguiente frame
            await asyncio.sleep(1 / s.FPS)


class RockPaperScissorsConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            await self.accept()

            if not await self.find_out_game():
                return

            self.redis = redis.Redis(host="redis", port=6379, decode_responses=True)

            await self.send_initial_information()

            self.update_game_state_task = asyncio.create_task(self.update_game_state())
        except Exception as e:
            logger.error(f"Error in connect: {e}", exc_info=True)

    def extract_user_data(self):
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b"cookie", b"")

        if cookie_header:
            for c in cookie_header.decode().split(";"):
                if "accessToken" in c:
                    jwt_token = c.split("=")[1]
                    try:
                        self.user_data = jwt.decode(jwt_token, options={"verify_signature": False})
                    except jwt.DecodeError as e:
                        logger.error(f"Error decoding token: {e}")
                    break

    async def find_out_game(self):
        self.extract_user_data()
        if not self.user_data or not self.user_data.get("user_id"):
            await self.send_error_and_close("Invalid user data")
            return False

        try:
            self.game = await self.query_db_for_game()
        except models.RockPaperScissorsGame.DoesNotExist:
            await self.send_error_and_close("User not registered in any game")
            return False
        except models.RockPaperScissorsGame.MultipleObjectsReturned:
            await self.send_error_and_close("User registered in multiple games")
            return False

        return True

    @sync_to_async
    def query_db_for_game(self):
        return models.RockPaperScissorsGame.objects.get(
            (
                Q(left_player_id=self.user_data["user_id"])
                | Q(right_player_id=self.user_data["user_id"])
            )
            & Q(is_finished=False)
        )

    async def send_initial_information(self):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "initial_information",
                    "game_id": self.game.id,
                    "left_player_id": self.game.left_player_id,
                    "right_player_id": self.game.right_player_id,
                    "left_player_username": self.game.left_player_username,
                    "right_player_username": self.game.right_player_username,
                    "left_player_choice": await self.redis.get(
                        f"rps:{self.game.id}:left_choice"
                    ),
                    "right_player_choice": await self.redis.get(
                        f"rps:{self.game.id}:right_choice"
                    ),
                    "timer_start": s.RPS_GAME_TIMER_LENGTH,
                }
            )
        )

    async def send_error_and_close(self, error_message):
        await self.send(text_data=json.dumps({"type": "error", "message": error_message}))
        await self.close()

    async def load_game_state(self, redis_client: redis.Redis):
        time_left_data = await redis_client.get(f"rps:{self.game.id}:time_left")
        left_choice_data = await redis_client.get(f"rps:{self.game.id}:left_choice")
        right_choice_data = await redis_client.get(f"rps:{self.game.id}:right_choice")
        winner_username_data = await redis_client.get(
            f"rps:{self.game.id}:winner_username"
        )
        is_finished_data = await redis_client.get(f"rps:{self.game.id}:is_finished")

        if (
            time_left_data
            and left_choice_data
            and right_choice_data
            and is_finished_data
        ):
            self.game_state = {
                "time_left": int(time_left_data),
                "left_choice": str(left_choice_data),
                "right_choice": str(right_choice_data),
                "winner_username": str(winner_username_data),
                "is_finished": int(is_finished_data),
            }
        else:
            raise Exception("Game state not found")

    async def send_game_state(self):
        await self.send(
            text_data=json.dumps(
                {"type": "game_state_update", "game_state": self.game_state}
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "update_game_state_task"):
            self.update_game_state_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            event = json.loads(text_data)

            handlers = {"choice_change": self.choice_update}

            if "type" in event:
                await handlers[event["type"]](event)

    async def choice_update(self, event):
        if not event.get("choices"):
            return

        if self.user_data["user_id"] == self.game.left_player_id:
            await self.redis.set(
                f"rps:{self.game.id}:left_choice", str(event["choices"]["leftPlayer"])
            )
        if self.user_data["user_id"] == self.game.right_player_id:
            await self.redis.set(
                f"rps:{self.game.id}:right_choice", str(event["choices"]["rightPlayer"])
            )

    async def update_game_state(self):
        while True:
            await self.load_game_state(self.redis)

            await self.send_game_state()

            await asyncio.sleep(1 / s.FPS)
