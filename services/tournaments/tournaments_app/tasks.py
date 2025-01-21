from celery import shared_task
# from kombu import Connection, Exchange, Producer
from django.conf import settings

# @shared_task
# def send_game_message_task(players):
#     """
#     Envía un mensaje genérico al servicio de juegos con los datos de los jugadores.
#     """
#     message = {
#         "left_player_id": players["left_player_id"],
#         "left_player_username": players["left_player_username"],
#         "right_player_id": players["right_player_id"],
#         "right_player_username": players["right_player_username"],
#     }
#     print(f"Enviando mensaje al servicio de juegos!!!!: {message}")
#     # Conexión con RabbitMQ
#     with Connection(settings.CELERY_BROKER_URL) as conn:
#         exchange = Exchange('games', type='direct', durable=True)  # Exchange llamado 'games'
#         producer = Producer(conn)
#         producer.publish(
#             message,
#             exchange=exchange,
#             routing_key='task.shared',  
#             serializer='json'
#         )

# service2/send_task.py
from celery import Celery

# Conectamos al broker compartido
app = Celery(broker='amqp://guest:guest@rabbitmq:5672/')

# Enviar la tarea registrada en el Servicio 1
result = app.send_task("game.add", args=[4, 5], queue="create_game")

# Imprimir el resultado de la tarea
# print(f"Task ID: {result.id}")
# print(f"Resultado: {result.get(timeout=10)}")
task_result = result.get(timeout=10)  # Aquí esperamos 10 segundos a que se procese la tarea
print(f"Task result: {task_result}")
