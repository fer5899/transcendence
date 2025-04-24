from celery import shared_task
from game_app.models import Game, GameState, RockPaperScissorsGame
from game_app.serializers import GameSerializer, RockPaperScissorsGameSerializer
import redis
from game import settings as s
import json
from celery import Celery, current_app
from django.db import transaction
import random
import time

def check_ia_vs_ia(game_data):
    if game_data["left_player_id"] == 0 and game_data["right_player_id"] == 0:
        winner_side = random.choice(["left", "right"])
        if winner_side == "left":
            winner_username = game_data["left_player_username"]
            loser_username = game_data["right_player_username"]
        else:
            winner_username = game_data["right_player_username"]
            loser_username = game_data["left_player_username"]

        delay = random.randint(1, 6)
        time.sleep(delay)
        current_app.send_task( 
            "game_end",
            args=[{
                "tournament_id": game_data["tournament_id"],
                "winner": winner_username,
                "loser": loser_username,
                "tree_index": game_data["tree_index"],
                "type": "game_end",
            }],
            queue="matchmaking_tasks",
        )
        return True
    return False

@shared_task(name="create_game")
def create_game(game_data):
    if check_ia_vs_ia(game_data): return
    with transaction.atomic():
        serializer = RockPaperScissorsGameSerializer(data=game_data)
        if not serializer.is_valid():
            return
        rps_record = serializer.save()
        redis_client = redis.Redis(host="redis", port=6379)
        redis_client.set(f"rps:{rps_record.id}:time_left", str(s.RPS_GAME_TIMER_LENGTH))
        redis_client.set(
            f"rps:{rps_record.id}:left_choice", str(random.choice(s.RPS_CHOICES))
        )
        redis_client.set(
            f"rps:{rps_record.id}:right_choice", str(random.choice(s.RPS_CHOICES))
        )
        redis_client.set(f"rps:{rps_record.id}:winner_username", "")
        redis_client.set(f"rps:{rps_record.id}:is_finished", "0")
        redis_client.rpush("rps_queue", f"{rps_record.id}")


@shared_task(name="launch_game")
def launch_game(game_data):
    with transaction.atomic():
        serializer = GameSerializer(data=game_data)
        if not serializer.is_valid():
            return
        game = serializer.save()
        redis_client = redis.Redis(host="redis", port=6379)
        redis_client.set(
            f"game:{game.id}:ball", json.dumps(s.INITIAL_GAME_STATE["ball"])
        )
        redis_client.set(
            f"game:{game.id}:left_paddle_y",
            json.dumps(s.INITIAL_GAME_STATE["left_paddle_y"]),
        )
        redis_client.set(
            f"game:{game.id}:right_paddle_y",
            json.dumps(s.INITIAL_GAME_STATE["right_paddle_y"]),
        )
        redis_client.set(
            f"game:{game.id}:scores", json.dumps(s.INITIAL_GAME_STATE["scores"])
        )
        redis_client.set(f"game:{game.id}:winner_username", "")
        redis_client.set(f"game:{game.id}:is_finished", "0")
        redis_client.set(f"game:{game.id}:start_countdown", str(s.START_COUNTDOWN))
        redis_client.set(f"game:{game.id}:next_side_to_collide", "left")
        redis_client.rpush("game_queue", f"{game.id}")
