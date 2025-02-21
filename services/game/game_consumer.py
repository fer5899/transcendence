import json
import django
from redis import asyncio as redis
import os
import random
import asyncio
from asgiref.sync import sync_to_async
import math
import time
from celery import current_app
from django.utils.timezone import now

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "game.settings")
django.setup()

from game_app import serializers
from game import settings as s
from game_app.models import GameState, Game, Ball, RockPaperScissorsGame

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def discover_games():
    redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
    while True:
        try:
            discovered_rps_id = await redis_client.lpop("rps_queue")
            discovered_game_id = await redis_client.lpop("game_queue")
            if not discovered_game_id and not discovered_rps_id:
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(
                0.1
            )  # Small delay to allow the game state to be created in redis
            if discovered_rps_id:
                asyncio.create_task(play_rock_paper_scissors(int(discovered_rps_id)))
                print(f"Rock Paper Scissors discovered: {discovered_rps_id}")
            if discovered_game_id:
                asyncio.create_task(play_game(int(discovered_game_id)))
                print(f"Game discovered: {discovered_game_id}")
        except Exception as e:
            logger.error(f"Error in discover_games: {e}", exc_info=True)


async def play_game(game_id: int):
    try:
        redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        game = await query_db_for_game(game_id)

        async with asyncio.TaskGroup() as tg:
            if game.left_player_id == 0:
                tg.create_task(control_paddle_by_computer(game_id, "left"))
            elif game.right_player_id == 0:
                tg.create_task(control_paddle_by_computer(game_id, "right"))

            game_state = await load_game_state(redis_client, game_id)

            while (
                game_state.left.score < s.WINNER_SCORE
                and game_state.right.score < s.WINNER_SCORE
            ):
                game_state = await load_game_state(redis_client, game_id)
                game_state = check_collisions(game_state)
                game_state.ball.x += game_state.ball.dx
                game_state.ball.y += game_state.ball.dy
                await save_game_state(redis_client, game_id, game_state)
                await asyncio.sleep(1 / s.FPS)

        game.is_finished = True
        game.finished_at = now()
        game.winner_username = (
            game.left_player_username
            if game_state.left.score == s.WINNER_SCORE
            else game.right_player_username
        )
        game.left_player_score = game_state.left.score
        game.right_player_score = game_state.right.score
        await redis_client.set(f"game:{game_id}:is_finished", "1")
        await redis_client.set(f"game:{game_id}:winner_username", game.winner_username)
        await save_game_ending(game)
    except Exception as e:
        logger.error(f"Error in play_game: {e}", exc_info=True)


@sync_to_async
def query_db_for_game(game_id):
    return Game.objects.get(pk=game_id)


async def control_paddle_by_computer(game_id, side):
    try:
        redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        final_paddle_y = 0
        target_paddle_y = 0
        last_seen_ball = Ball(
            s.INITIAL_GAME_STATE["ball"]["x"], s.INITIAL_GAME_STATE["ball"]["y"], 0, 0
        )
        last_seen_time = time.time()
        refresh_rate = 1 / 10
        while True:
            game_state = await load_game_state(redis_client, game_id)

            if side == "left":
                final_paddle_y = game_state.left.paddle_y
            elif side == "right":
                final_paddle_y = game_state.right.paddle_y

            # Refresh the last seen ball position every refresh_rate seconds
            if time.time() - last_seen_time > refresh_rate:
                last_seen_time = time.time()
                last_seen_ball = game_state.ball
                target_paddle_y = determine_target_paddle_y(
                    last_seen_ball, side, target_paddle_y
                )

            final_paddle_y = approach_target_paddle_y(final_paddle_y, target_paddle_y)

            await redis_client.set(
                f"game:{game_id}:{side}_paddle_y", json.dumps(final_paddle_y)
            )
            await asyncio.sleep(1 / s.FPS)
    except Exception as e:
        logger.error(f"Error in control_paddle_by_computer: {e}", exc_info=True)


def determine_target_paddle_y(last_seen_ball: Ball, side, target_paddle_y):
    # Don't calculate target if ball is moving away from the computer paddle
    if (side == "left" and last_seen_ball.dx > 0) or (
        side == "right" and last_seen_ball.dx < 0
    ):
        return target_paddle_y

    ball_velocity_angle = math.atan2(last_seen_ball.dy, last_seen_ball.dx)
    x_distance_to_goal = (
        s.FIELD_WIDTH - last_seen_ball.x if side == "right" else last_seen_ball.x
    )
    y_distance_to_goal = x_distance_to_goal * math.tan(ball_velocity_angle)  # WARNING

    target_paddle_y = last_seen_ball.y + y_distance_to_goal

    # There is at least one wall rebound
    if target_paddle_y > s.FIELD_HEIGHT or target_paddle_y < 0:
        distance_to_first_rebound = (
            s.FIELD_HEIGHT - last_seen_ball.y
            if target_paddle_y > s.FIELD_HEIGHT
            else last_seen_ball.y
        )
        amount_of_rebounds = (
            int(y_distance_to_goal - distance_to_first_rebound) // s.FIELD_HEIGHT
        )
        final_offset = (
            int(y_distance_to_goal - distance_to_first_rebound) % s.FIELD_HEIGHT
        )
        if target_paddle_y > s.FIELD_HEIGHT:
            if amount_of_rebounds % 2 == 0:
                target_paddle_y = s.FIELD_HEIGHT - final_offset
            else:
                target_paddle_y = final_offset
        else:
            if amount_of_rebounds % 2 == 0:
                target_paddle_y = final_offset
            else:
                target_paddle_y = s.FIELD_HEIGHT - final_offset

    return target_paddle_y


def approach_target_paddle_y(final_paddle_y, target_paddle_y):
    if final_paddle_y < target_paddle_y - s.PADDLE_MOVE_AMOUNT:
        final_paddle_y += s.PADDLE_MOVE_AMOUNT
    elif final_paddle_y > target_paddle_y + s.PADDLE_MOVE_AMOUNT:
        final_paddle_y -= s.PADDLE_MOVE_AMOUNT
    final_paddle_y = max(
        s.PADDLE_HEIGHT / 2,
        min(s.FIELD_HEIGHT - s.PADDLE_HEIGHT / 2, final_paddle_y),
    )

    return final_paddle_y


async def load_game_state(redis_client: redis.Redis, game_id):
    ball_data = await redis_client.get(f"game:{game_id}:ball")
    left_paddle_data = await redis_client.get(f"game:{game_id}:left_paddle_y")
    right_paddle_data = await redis_client.get(f"game:{game_id}:right_paddle_y")
    scores_data = await redis_client.get(f"game:{game_id}:scores")
    winner_username_data = await redis_client.get(f"game:{game_id}:winner_username")
    is_finished_data = await redis_client.get(f"game:{game_id}:is_finished")

    if (
        ball_data
        and left_paddle_data
        and right_paddle_data
        and scores_data
        and is_finished_data
    ):
        scores = json.loads(scores_data)
        game_state_data = {
            "ball": json.loads(ball_data),
            "left": {"paddle_y": json.loads(left_paddle_data), "score": scores["left"]},
            "right": {
                "paddle_y": json.loads(right_paddle_data),
                "score": scores["right"],
            },
            "winner_username": winner_username_data,
            "is_finished": int(is_finished_data),
        }
        game_state_serializer = serializers.GameStateSerializer(data=game_state_data)
        if game_state_serializer.is_valid():
            return GameState.from_dict(game_state_serializer.validated_data)
        else:
            raise Exception(f"Invalid game state: {game_state_serializer.errors}")
    else:
        raise Exception("Game state not found")


async def save_game_state(redis_client: redis.Redis, game_id, game_state: GameState):
    await redis_client.set(
        f"game:{game_id}:ball", json.dumps(game_state.ball.to_dict())
    )
    await redis_client.set(
        f"game:{game_id}:scores",
        json.dumps({"left": game_state.left.score, "right": game_state.right.score}),
    )


def check_collisions(game_state: GameState):
    # Top and bottom walls
    if (
        game_state.ball.y - s.BALL_RADIUS <= 0
        or game_state.ball.y + s.BALL_RADIUS >= s.FIELD_HEIGHT
    ):
        game_state.ball.dy *= -1
        return game_state

    # Left paddle
    game_state = check_paddle_collision(
        game_state,
        -s.PADDLE_OFFSET,
        game_state.left.paddle_y,
        1,
    )

    # Right paddle
    game_state = check_paddle_collision(
        game_state,
        s.FIELD_WIDTH + s.PADDLE_OFFSET,
        game_state.right.paddle_y,
        -1,
    )

    # Left wall
    if game_state.ball.x <= 0:
        game_state.right.score += 1
        game_state.ball.x = s.FIELD_WIDTH / 2
        game_state.ball.y = s.FIELD_HEIGHT / 2
        game_state.ball.dx = s.INITIAL_BALL_SPEED  # Serve to the right
        game_state.ball.dy = random.choice([-1, 1]) * s.INITIAL_BALL_SPEED
        return game_state

    # Right wall
    if game_state.ball.x >= s.FIELD_WIDTH:
        game_state.left.score += 1
        game_state.ball.x = s.FIELD_WIDTH / 2
        game_state.ball.y = s.FIELD_HEIGHT / 2
        game_state.ball.dx = -s.INITIAL_BALL_SPEED  # Serve to the left
        game_state.ball.dy = random.choice([-1, 1]) * s.INITIAL_BALL_SPEED
        return game_state

    return game_state


def check_paddle_collision(
    game_state: GameState,
    paddle_center_x_position,
    paddle_center_y_position,
    bounce_away_direction,
):
    # If the ball is not moving towards the paddle, no collision
    if game_state.ball.dx * bounce_away_direction > 0:
        return game_state

    centers_distance = math.sqrt(
        (game_state.ball.x - paddle_center_x_position) ** 2
        + (game_state.ball.y - paddle_center_y_position) ** 2
    )

    # If the ball is not close enough to the paddle, no collision
    if centers_distance > s.BALL_RADIUS + s.PADDLE_RADIUS:
        return game_state

    # Bounce the ball away from the paddle
    collision_angle = math.atan2(
        game_state.ball.y - paddle_center_y_position,
        game_state.ball.x - paddle_center_x_position,
    )
    initial_angle = math.atan2(game_state.ball.dy, game_state.ball.dx)
    theta = math.pi + collision_angle - initial_angle
    final_angle = collision_angle + theta
    initial_magnitude = math.sqrt(game_state.ball.dx**2 + game_state.ball.dy**2)
    final_magnitude = initial_magnitude * s.BALL_SPEED_INCREMENT
    game_state.ball.dx = final_magnitude * math.cos(final_angle)
    game_state.ball.dy = final_magnitude * math.sin(final_angle)

    if abs(game_state.ball.dx) < s.MINIMUM_X_SPEED:
        game_state.ball.dx = (
            s.MINIMUM_X_SPEED if game_state.ball.dx > 0 else -s.MINIMUM_X_SPEED
        )

    return game_state


@sync_to_async
def save_game_ending(game: Game):
    game.save()


async def play_rock_paper_scissors(rps_id: int):
    try:
        redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        rps_record = await query_db_for_rps(rps_id)

        winner_username = await play_rps_round(rps_record, redis_client)

        while winner_username == "":
            await asyncio.sleep(2)  # Wait before the next round
            await redis_client.set(
                f"rps:{rps_record.id}:time_left", str(s.RPS_GAME_TIMER_LENGTH)
            )
            await redis_client.set(f"rps:{rps_record.id}:is_finished", "0")
            winner_username = await play_rps_round(rps_record, redis_client)

        rps_record.winner_username = winner_username
        left_choice_data = await redis_client.get(f"rps:{rps_record.id}:left_choice")
        right_choice_data = await redis_client.get(f"rps:{rps_record.id}:right_choice")
        rps_record.left_player_choice = str(left_choice_data)
        rps_record.right_player_choice = str(right_choice_data)
        rps_record.is_finished = True
        rps_record.finished_at = now()
        await save_rps_ending(rps_record)
        game_data = {
            "left_player_id": rps_record.left_player_id,
            "left_player_username": rps_record.left_player_username,
            "right_player_id": rps_record.right_player_id,
            "right_player_username": rps_record.right_player_username,
            "tournament_id": rps_record.tournament_id,
            "tree_index": rps_record.tree_index,
            "rock_paper_scissors_id": rps_record.id,
        }
        current_app.send_task(
            "launch_game",
            args=[game_data],
            queue="game_tasks",
        )
    except Exception as e:
        logger.error(f"Error in play_rock_paper_scissors: {e}", exc_info=True)


@sync_to_async
def query_db_for_rps(game_id):
    return RockPaperScissorsGame.objects.get(pk=game_id)


async def play_rps_round(rps_record: RockPaperScissorsGame, redis_client: redis.Redis):
    try:
        time_left = int(await redis_client.get(f"rps:{rps_record.id}:time_left"))

        # Initial countdown
        while time_left > 0:
            await asyncio.sleep(1)
            time_left -= 1

            # AI players
            if rps_record.left_player_id == 0:
                await redis_client.set(
                    f"rps:{rps_record.id}:left_choice",
                    random.choice(s.RPS_CHOICES),
                )
            if rps_record.right_player_id == 0:
                await redis_client.set(
                    f"rps:{rps_record.id}:right_choice",
                    random.choice(s.RPS_CHOICES),
                )

            await redis_client.set(f"rps:{rps_record.id}:time_left", str(time_left))

        left_choice_data = await redis_client.get(f"rps:{rps_record.id}:left_choice")
        left_choice = str(left_choice_data)
        right_choice_data = await redis_client.get(f"rps:{rps_record.id}:right_choice")
        right_choice = str(right_choice_data)

        winner_username = determine_winner(
            left_choice,
            right_choice,
            rps_record.left_player_username,
            rps_record.right_player_username,
        )

        await redis_client.set(f"rps:{rps_record.id}:winner_username", winner_username)
        await redis_client.set(f"rps:{rps_record.id}:is_finished", "1")

        return winner_username
    except Exception as e:
        logger.error(f"Error in play_rps_round: {e}", exc_info=True)


def determine_winner(
    left_choice, right_choice, left_player_username, right_player_username
):
    if left_choice == right_choice:
        return ""
    if left_choice == "rock":
        return (
            right_player_username if right_choice == "paper" else left_player_username
        )
    if left_choice == "paper":
        return (
            right_player_username
            if right_choice == "scissors"
            else left_player_username
        )
    if left_choice == "scissors":
        return right_player_username if right_choice == "rock" else left_player_username
    raise Exception(f"Invalid choices: {left_choice}, {right_choice}")


@sync_to_async
def save_rps_ending(rps_record: RockPaperScissorsGame):
    rps_record.save()


if __name__ == "__main__":
    asyncio.run(discover_games())
