from celery import shared_task
from kombu import Connection, Exchange, Producer
from django.conf import settings

@shared_task
def send_game_message_task(players):
    """
    Envía un mensaje genérico al servicio de juegos con los datos de los jugadores.
    """
    message = {
        "left_player_id": players["left_player_id"],
        "left_player_username": players["left_player_username"],
        "right_player_id": players["right_player_id"],
        "right_player_username": players["right_player_username"],
    }
    print(f"Enviando mensaje al servicio de juegos!!!!: {message}")
    # Conexión con RabbitMQ
    with Connection(settings.CELERY_BROKER_URL) as conn:
        exchange = Exchange('games', type='direct', durable=True)  # Exchange llamado 'games'
        producer = Producer(conn)
        producer.publish(
            message,
            exchange=exchange,
            routing_key='games.create_game',  # Enrutar el mensaje a la clave 'games.create_game'
            serializer='json'
        )
