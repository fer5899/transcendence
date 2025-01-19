# game_app/tasks.py
from celery import shared_task
import json
from game_app.models import Game

@shared_task
def create_game_task(game_id, players):
    # Aquí puedes agregar la lógica que quieras para crear el juego
    print(f"Creando el juego {game_id} con jugadores: {players}")
    
    # Lógica para guardar el juego en la base de datos
    game = Game.objects.create(id=game_id, players=json.dumps(players))
    return game.id
