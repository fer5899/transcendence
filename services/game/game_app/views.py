from django.db.models import Q
from requests import Request
from rest_framework import generics
from celery import current_app
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


from game_app.models import Game, RockPaperScissorsGame
from game_app.serializers import GameSerializer, RockPaperScissorsGameSerializer
from game_app import tasks
from game_app import utils



@api_view(["GET"])
def has_active_game(request):
    user_data = utils.extract_user_data_from_request(request)

    user_id = user_data.get("user_id")
    if not user_id:
        return Response(
            {"error": "User not found with JWT"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    active_game_data = utils.query_for_active_game(user_id)
    if active_game_data.get("error"):
        return Response(
            active_game_data,
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    return Response(active_game_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_game(request : Request):
    user_data = utils.extract_user_data_from_request(request)
    game_type = request.data.get("type")
    user_id = user_data.get("user_id")
    username = user_data.get("username")
    if not game_type:
        return Response(
            {"error": "No game type provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if game_type not in ["computer", "player"]:
        return Response(
            {"error": "Invalid game type"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not user_id or not username:
        return Response(
            {"error": "User information not found with JWT"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    active_game_data = utils.query_for_active_game(user_id)
    if active_game_data.get("error"):
        return Response(
            active_game_data,
            status=status.HTTP_400_BAD_REQUEST,
        )
    if active_game_data["has_active_pong_game"]:
        return Response(
            {"error": "User already has an active game"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if active_game_data["has_active_rps_game"]:
        return Response(
            {"error": "User already has an active Rock Paper Scissors game"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    if game_type == "computer":
        game_creation_data = {
            "left_player_id": user_id,
            "left_player_username": username,
            "right_player_id": 0,
            "right_player_username": "La Máquina",
            "tournament_id": 0,
            "tree_index": 0
        }
        current_app.send_task(
            "create_game",
            args=[game_creation_data],
            queue="game_tasks",
        )
    elif game_type == "player":
        game_creation_data = {
            "left_player_id": user_id,
            "left_player_username": username,
            "right_player_id": user_id,
            "right_player_username": "Invitado",
            "tournament_id": 0,
            "tree_index": 0,
            "is_local_game": True,
        }
        current_app.send_task(
            "create_game",
            args=[game_creation_data],
            queue="game_tasks",
        )

    return Response(
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_match_statistics(request, user_id):
    online_pong_matches= Game.objects.filter(
        (Q(left_player_id=user_id) | Q(right_player_id=user_id)) & Q(is_local_game=False)
    )
    online_pong_matches_played = online_pong_matches.count()
    online_pong_matches_won = online_pong_matches.filter(winner_id=user_id).count()

    online_rps_matches_won = RockPaperScissorsGame.objects.filter(
        Q(is_local_game=False) & Q(winner_id=user_id)
    ).count()

    return Response(
        {
            "online_matches_played": online_pong_matches_played,
            "online_pong_matches_won": online_pong_matches_won,
            "online_rps_matches_won": online_rps_matches_won,
        },
        status=status.HTTP_200_OK,
    )



@api_view(["GET"])
def get_match_history(request, user_id):
    
    
    rps_games = RockPaperScissorsGame.objects.filter(
        Q(left_player_id=user_id) | Q(right_player_id=user_id)
    ).order_by("-created_at")

    pong_games = Game.objects.filter(
        Q(left_player_id=user_id) | Q(right_player_id=user_id)
    ).order_by("-created_at")
    
    rps_games_data = RockPaperScissorsGameSerializer(rps_games, many=True).data
    pong_games_data = GameSerializer(pong_games, many=True).data

    matches = [{"pong": pong_data, "rps": rps_data} for pong_data, rps_data in zip(pong_games_data, rps_games_data)]

    tournament_matches = {}
    online_matches = []
    local_matches = []
    for match in matches:
        tournament_id = match["pong"]["tournament_id"]
        if tournament_id != 0:
            try:
                tournament_matches[tournament_id].append(match)
            except KeyError:
                tournament_matches[tournament_id] = [match]
        elif match["pong"]["is_local_game"]:
            local_matches.append(match)
        else:
            online_matches.append(match)
    
    return Response(data={"tournament_matches": tournament_matches, 
                          "online_matches": online_matches, 
                          "local_matches": local_matches,
                          }, status=status.HTTP_200_OK)
