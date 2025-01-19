from celery import shared_task
from game_app.models import Game

@shared_task
def create_game_task(players):
    """
    Procesa el mensaje recibido desde el servicio de torneos y crea un juego.
    """
    print(f"Creando un juego con los siguientes datos: {players}")
    
    # Crear una instancia del modelo Game
    game = Game.objects.create(
        left_player_id=players["left_player_id"],
        left_player_username=players["left_player_username"],
        right_player_id=players["right_player_id"],
        right_player_username=players["right_player_username"]
    )
    
    return game.id

