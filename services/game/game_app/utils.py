import jwt
from django.db.models import Q

from game_app.models import Game, RockPaperScissorsGame

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_user_data_from_request(request):
	jwt_token = request.COOKIES.get('accessToken')
	user_data = {}
	if jwt_token:
		try:
			payload = dict(
				jwt.decode(jwt_token, options={"verify_signature": False})
			)
			user_data["username"] = payload.get("username")
			user_data["user_id"] = payload.get("user_id")
		except jwt.DecodeError as e:
			logger.error(f"JWT Decode Error: {e}")
	return user_data


def query_for_active_game(user_id):
    active_game_data = {"has_active_pong_game": False, "has_active_rps_game": False}
    error = {"error": "Multiple active games found"}
    try:
        game = Game.objects.get(
            (Q(left_player_id=user_id) | Q(right_player_id=user_id))
            & Q(is_finished=False)
        )
    except Game.MultipleObjectsReturned:
        return error
    except Game.DoesNotExist:
        game = None

    try:
        rps_game = RockPaperScissorsGame.objects.get(
            (Q(left_player_id=user_id) | Q(right_player_id=user_id))
            & Q(is_finished=False)
        )
    except RockPaperScissorsGame.MultipleObjectsReturned:
        return error
    except RockPaperScissorsGame.DoesNotExist:
        rps_game = None

    if rps_game:
        active_game_data["has_active_rps_game"] = True
    elif game:
        active_game_data["has_active_pong_game"] = True

    return active_game_data
