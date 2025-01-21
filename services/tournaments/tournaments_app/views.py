from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Tournament
from .serializers import TournamentSerializer
import redis
from django.conf import settings
import json



redis_client = redis.Redis(
    host=settings.REDIS_HOST,
	port=settings.REDIS_PORT,
	db=settings.REDIS_DB,
    decode_responses= True
)

@api_view(['POST'])
def create_tournament(request):
    print("entering create_tournament")
    print(request.data)
    serializer = TournamentSerializer(data=request.data)
    if serializer.is_valid():
        tournament = serializer.save()
        redis_client.publish('tournaments_channel', f'{tournament.id}')
        redis_client.set(f'tournament_{tournament.id}_player_count', 0)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    print("serializer.errors")
    print(serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_tournaments(request):
    tournaments = Tournament.objects.all()
    serializer = TournamentSerializer(tournaments, many=True)
    return Response(serializer.data)

# Prepare this for allowing users to join a tournament, be aware
# of the edge cases like the tournament not existing or the user already being in the tournament.
# or the tournament being full. TAKE CARE OF THIS !!! JAVI WILL BE TESTING THIS !!!
@api_view(['POST'])
def join_tournament(request, tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        players = {
            "left_player_id": 1,
            "left_player_username": "Jugador1",
            "right_player_id": 2,
            "right_player_username": "Jugador2",
        }
        print("One player joined!!! Sending message to games service.")
        # send_game_message_task.apply_async(kwargs={'players': players})
        print("Tarea enviada a Celery")
        # redis_client.incr(f'tournament_{tournament.id}_player_count')
        # redis_client.publish('tournaments_channel', json.dumps({
    	# "tournamentId": tournament.id,
    	# "user_count": redis_client.get(f'tournament_{tournament.id}_player_count')}))
        return Response({"message": f"Te has unido al torneo '{tournament.name}'."}, status=status.HTTP_200_OK)
    except Tournament.DoesNotExist:
        return Response({"error": "Torneo no encontrado."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def list_tournament_player_counts(request):
    keys = redis_client.scan_iter(match='tournament_*_player_count')
    tournament_counts = {}
    for key in keys:
        tournament_id = key.split('_')[1]  # Extraer el ID del torneo de la clave
        tournament_counts[tournament_id] = redis_client.get(key)
    return Response(tournament_counts, status=status.HTTP_200_OK)