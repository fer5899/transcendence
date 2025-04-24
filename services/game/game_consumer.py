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
import psycopg2

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "game.settings")
django.setup()

from game_app import serializers
from game import settings as s
from game_app.models import GameState, Game, Ball, RockPaperScissorsGame

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def discover_games():
    await end_unfinished_games()
    running_games = set()
    redis_client = redis.Redis(connection_pool=redis_pool, auto_close_connection_pool=False)
    while True:
        discovered_rps_id = await redis_client.lpop("rps_queue")
        discovered_game_id = await redis_client.lpop("game_queue")
        if not discovered_game_id and not discovered_rps_id:
            continue
        await asyncio.sleep(0.1)  # To allow the game state to be created in redis
        if discovered_rps_id:
            task = asyncio.create_task(play_rps_game(int(discovered_rps_id)))
            running_games.add(task)
        if discovered_game_id:
            task = asyncio.create_task(play_pong_game(int(discovered_game_id)))
            running_games.add(task)

async def finish_pong_game(redis_client: redis.Redis, game: Game, game_state: GameState):
    # If there is a tie, add a point to a random player
    if game_state.left.score == game_state.right.score:
        if random.choice([True, False]):
            game_state.left.score += 1
        else:
            game_state.right.score += 1

    game.is_finished = True
    game.finished_at = now()

    if game_state.left.score > game_state.right.score:
        game.winner_id = game.left_player_id
        game.winner_username = game.left_player_username
    else:
        game.winner_id = game.right_player_id
        game.winner_username = game.right_player_username

    game.left_player_score = game_state.left.score
    game.right_player_score = game_state.right.score

    await redis_client.set(f"game:{game.id}:is_finished", "1")
    await redis_client.set(f"game:{game.id}:winner_username", game.winner_username)
    await save_game_ending(game)

    if game.tournament_id > 0:
        end_game_data = {
            "winner": game.winner_username,
            "winner_id": game.winner_id,
            "loser": (game.left_player_username if game.winner_username == game.right_player_username else game.right_player_username),
            "loser_id": (game.left_player_id if game.winner_username == game.right_player_username else game.right_player_id),
            "tournament_id": game.tournament_id,
            "tree_index": game.tree_index,
        }
        current_app.send_task(
            "game_end",
            args=[end_game_data],
            queue="matchmaking_tasks",
        )

async def play_pong_game(game_id: int):
    try:
        redis_client = redis.Redis(connection_pool=redis_pool, auto_close_connection_pool=False)
        game = await query_db_for_game(game_id)

        async with asyncio.TaskGroup() as tg:
            if game.left_player_id == 0:
                tg.create_task(control_paddle_by_computer(game_id, "left"))
            elif game.right_player_id == 0:
                tg.create_task(control_paddle_by_computer(game_id, "right"))

            game_state = await determine_initial_serve(
                game, await load_game_state(redis_client, game_id)
            )
            game_state.next_side_to_collide = "left" if game_state.ball.dx < 0 else "right"
            await save_game_state(redis_client, game_id, game_state)

            while game_state.start_countdown > 0:
                await asyncio.sleep(1)
                game_state.start_countdown -= 1
                await redis_client.set(
                    f"game:{game_id}:start_countdown", str(game_state.start_countdown)
                )

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
            await finish_pong_game(redis_client, game, game_state)
    except Exception as e:
        logger.error(f"Error in play_pong_game: {e}", exc_info=True)
        await finish_pong_game(redis_client, game, game_state)


@sync_to_async
def query_db_for_game(game_id):
    return Game.objects.get(pk=game_id)


async def control_paddle_by_computer(game_id, side):
    try:
        redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        final_paddle_y = 0.5
        target_paddle_y = 0.5
        game_state = await load_game_state(redis_client, game_id)
        last_seen_ball = game_state.ball
        last_seen_time = time.time()
        refresh_rate = s.AI_REFRESH_RATE
        while True:
            game_state = await load_game_state(redis_client, game_id)

            if game_state.is_finished:
                break

            if side == "left":
                final_paddle_y = game_state.left.paddle_y
            elif side == "right":
                final_paddle_y = game_state.right.paddle_y

            # Refresh the last seen ball position every refresh_rate seconds
            if time.time() - last_seen_time > refresh_rate:
                if game_state.ball.dx != 0:
                    last_seen_time = time.time()
                last_seen_ball = game_state.ball
                target_paddle_y = determine_target_paddle_y(
                    last_seen_ball, side, target_paddle_y
                )

            final_paddle_y = approach_target_paddle_y(final_paddle_y, target_paddle_y)

            await redis_client.set(
                f"game:{game_id}:{side}_paddle_y", json.dumps(final_paddle_y)
            )
            await asyncio.sleep(2 / s.FPS)
    except Exception as e:
        logger.error(f"Error in control_paddle_by_computer: {e}", exc_info=True)
    finally:
        await redis_client.close(close_connection_pool=False)


def determine_target_paddle_y(last_seen_ball: Ball, side, target_paddle_y):
    # Don't calculate target if ball is moving away from the computer paddle
    if (side == "left" and last_seen_ball.dx > 0) or (
        side == "right" and last_seen_ball.dx < 0
    ):
        return target_paddle_y
    
    if last_seen_ball.dx == 0:
        return target_paddle_y

    target_x = (s.FIELD_WIDTH - s.BALL_RADIUS) if side == "right" else s.BALL_RADIUS

    ball_direction_angle = math.atan2(last_seen_ball.dy, last_seen_ball.dx)
    changing_ball_dy = last_seen_ball.dy
    start_line_x = last_seen_ball.x
    start_line_y = last_seen_ball.y

    end_line_x = target_x
    end_line_y = start_line_y + (end_line_x - start_line_x) * math.tan(ball_direction_angle)

    if (end_line_y > s.FIELD_HEIGHT - s.BALL_RADIUS):
        end_line_y = s.FIELD_HEIGHT - s.BALL_RADIUS
        end_line_x = (end_line_y - start_line_y) / math.tan(ball_direction_angle) + start_line_x
    elif (end_line_y < s.BALL_RADIUS):
        end_line_y = s.BALL_RADIUS
        end_line_x = (end_line_y - start_line_y) / math.tan(ball_direction_angle) + start_line_x

    while (1):
        start_line_x = end_line_x
        start_line_y = end_line_y
        end_line_x = target_x
        changing_ball_dy = -changing_ball_dy
        ball_direction_angle = math.atan2(changing_ball_dy, last_seen_ball.dx)
        end_line_y = start_line_y + (end_line_x - start_line_x) * math.tan(ball_direction_angle)
        if (end_line_y > s.FIELD_HEIGHT - s.BALL_RADIUS):
            end_line_y = s.FIELD_HEIGHT - s.BALL_RADIUS
            end_line_x = (end_line_y - start_line_y) / math.tan(ball_direction_angle) + start_line_x
        elif (end_line_y < s.BALL_RADIUS):
            end_line_y = s.BALL_RADIUS
            end_line_x = (end_line_y - start_line_y) / math.tan(ball_direction_angle) + start_line_x
        if (side == "right" and end_line_x >= target_x) or (side == "left" and end_line_x <= target_x):
            break

    target_paddle_y = end_line_y

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
    start_countdown_data = await redis_client.get(f"game:{game_id}:start_countdown")
    next_side_to_collide_data = await redis_client.get(
        f"game:{game_id}:next_side_to_collide"
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
            "left": {"paddle_y": json.loads(left_paddle_data), "score": scores["left"]},
            "right": {
                "paddle_y": json.loads(right_paddle_data),
                "score": scores["right"],
            },
            "winner_username": winner_username_data,
            "is_finished": int(is_finished_data),
            "start_countdown": int(start_countdown_data),
            "next_side_to_collide": next_side_to_collide_data,
        }
        game_state_serializer = serializers.GameStateSerializer(data=game_state_data)
        if game_state_serializer.is_valid():
            return GameState.from_dict(game_state_serializer.validated_data)
        else:
            raise Exception(f"Invalid game state: {game_state_serializer.errors}")
    else:
        return None


async def save_game_state(redis_client: redis.Redis, game_id, game_state: GameState):
    await redis_client.set(
        f"game:{game_id}:ball", json.dumps(game_state.ball.to_dict())
    )
    await redis_client.set(
        f"game:{game_id}:scores",
        json.dumps({"left": game_state.left.score, "right": game_state.right.score}),
    )
    await redis_client.set(
        f"game:{game_id}:next_side_to_collide", game_state.next_side_to_collide
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
        "left",
    )

    # Right paddle
    game_state = check_paddle_collision(
        game_state,
        s.FIELD_WIDTH + s.PADDLE_OFFSET,
        game_state.right.paddle_y,
        "right",
    )

    # Left wall
    if game_state.ball.x <= 0:
        game_state.right.score += 1
        game_state.ball.x = s.FIELD_WIDTH / 2
        game_state.ball.y = s.FIELD_HEIGHT / 2
        game_state.ball.dx = s.INITIAL_BALL_SPEED  # Serve to the right
        game_state.next_side_to_collide = "right"
        game_state.ball.dy = random.choice([-1, 1]) * s.INITIAL_BALL_SPEED
        return game_state

    # Right wall
    if game_state.ball.x >= s.FIELD_WIDTH:
        game_state.left.score += 1
        game_state.ball.x = s.FIELD_WIDTH / 2
        game_state.ball.y = s.FIELD_HEIGHT / 2
        game_state.ball.dx = -s.INITIAL_BALL_SPEED  # Serve to the left
        game_state.next_side_to_collide = "left"
        game_state.ball.dy = random.choice([-1, 1]) * s.INITIAL_BALL_SPEED
        return game_state

    return game_state


def check_paddle_collision(
    game_state: GameState,
    paddle_center_x_position,
    paddle_center_y_position,
    paddle_side,
):
    if paddle_side != game_state.next_side_to_collide:
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
    game_state.next_side_to_collide = "left" if paddle_side == "right" else "right"

    # Ensure the ball is always moving towards the opposite side of the last collision
    if game_state.next_side_to_collide == "left" and game_state.ball.dx > -s.MINIMUM_X_SPEED:
        game_state.ball.dx = -s.MINIMUM_X_SPEED
    elif game_state.next_side_to_collide == "right" and game_state.ball.dx < s.MINIMUM_X_SPEED:
        game_state.ball.dx = s.MINIMUM_X_SPEED


    return game_state


@sync_to_async
def save_game_ending(game: Game):
    game.save()


@sync_to_async
def determine_initial_serve(game: Game, game_state: GameState):
    game_state.ball.dy *= random.choice([-1, 1])

    if not game.rock_paper_scissors_id or game.rock_paper_scissors_id <= 0:
        game_state.ball.dx *= random.choice([-1, 1])  # Serve to a random side
        return game_state

    try:
        rps_record = RockPaperScissorsGame.objects.get(pk=game.rock_paper_scissors_id)
        if (
            rps_record.winner_username == game.left_player_username
        ):  # Left player won the RPS, serves
            game_state.ball.dx = -s.INITIAL_BALL_SPEED
        elif (
            rps_record.winner_username == game.right_player_username
        ):  # Right player won the RPS, serves
            game_state.ball.dx = s.INITIAL_BALL_SPEED
        else:
            game_state.ball.dx *= random.choice([-1, 1])  # Serve to a random side

    except RockPaperScissorsGame.DoesNotExist:
        game_state.ball.dx *= random.choice([-1, 1])  # Serve to a random side

    return game_state


async def finish_rps_game(redis_client: redis.Redis, rps_record: RockPaperScissorsGame, winner_username: str):
    try:
        if winner_username != "":
            left_choice_data = await redis_client.get(f"rps:{rps_record.id}:left_choice")
            right_choice_data = await redis_client.get(f"rps:{rps_record.id}:right_choice")
            rps_record.winner_username = winner_username
            rps_record.winner_id = (
                rps_record.left_player_id
                if winner_username == rps_record.left_player_username
                else rps_record.right_player_id
            )
        else:
            # Randomize the winner in case of a tie
            rps_record.winner_username = random.choice(
                [rps_record.left_player_username, rps_record.right_player_username]
            )
            rps_record.winner_id = (
                rps_record.left_player_id
                if rps_record.winner_username == rps_record.left_player_username
                else rps_record.right_player_id
            )
            left_choice_data = "rock" if rps_record.winner_id == rps_record.left_player_id else "scissors"
            right_choice_data = "rock" if rps_record.winner_id == rps_record.right_player_id else "scissors"
            
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
            "is_local_game": rps_record.is_local_game,
        }
        current_app.send_task(
            "launch_game",
            args=[game_data],
            queue="game_tasks",
        )
    except Exception as e:
        logger.error(f"Error in finish_rps_game: {e}", exc_info=True)

async def play_rps_game(rps_id: int):
    try:
        redis_client = redis.Redis(connection_pool=redis_pool, auto_close_connection_pool=False)
        rps_record = await query_db_for_rps(rps_id)

        winner_username = ""
        winner_username = await play_rps_round(rps_record, redis_client)

        while winner_username == "":
            await asyncio.sleep(2)  # Wait before the next round
            await redis_client.set(
                f"rps:{rps_record.id}:time_left", str(s.RPS_GAME_TIMER_LENGTH)
            )
            await redis_client.set(f"rps:{rps_record.id}:is_finished", "0")
            winner_username = await play_rps_round(rps_record, redis_client)

    except Exception as e:
        logger.error(f"Error in play_rps_game: {e}", exc_info=True)
    finally:
        await finish_rps_game(redis_client, rps_record, winner_username)


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

@sync_to_async
def get_unfinished_games():
    try:
        unfinished_pong_games = list(Game.objects.filter(is_finished=False))
        unfinished_rps_games = list(RockPaperScissorsGame.objects.filter(is_finished=False))
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {e}")
        time.sleep(3)
        return get_unfinished_games()
    return unfinished_pong_games, unfinished_rps_games


async def end_unfinished_games():
    redis_client = redis.Redis(connection_pool=redis_pool, auto_close_connection_pool=False)
    unfinished_pong_games, unfinished_rps_games = await get_unfinished_games()
    for pong_game in unfinished_pong_games:
        pong_game_state = await load_game_state(redis_client, pong_game.id)
        if pong_game_state is None:
            pong_game_state = GameState.from_dict(
                {
                    "ball": {"x": 0, "y": 0, "dx": 0, "dy": 0},
                    "left": {"paddle_y": 0, "score": 0},
                    "right": {"paddle_y": 0, "score": 0},
                    "winner_username": "",
                    "is_finished": False,
                    "start_countdown": s.START_COUNTDOWN,
                    "next_side_to_collide": "",
                }
            )
        await finish_pong_game(redis_client, pong_game, pong_game_state)
    for rps_game in unfinished_rps_games:
        await finish_rps_game(redis_client, rps_game, "")
    await redis_client.aclose()
        

if __name__ == "__main__":
    redis_pool = redis.ConnectionPool(host=s.REDIS_HOST, port=s.REDIS_PORT, decode_responses=True)
    asyncio.run(discover_games())
