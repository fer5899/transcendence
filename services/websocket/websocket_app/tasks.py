from celery import shared_task
from celery import Celery

app = Celery('websocket_project', broker='amqp://guest:guest@message-broker:5672//')

#This task sends a message to the matchmaking service to start the matchmaking process

@shared_task
def send_start_matchmaking_task(message):
   
    app.send_task(
        'start_matchmaking',
        args=[message],
        queue='matchmaking_tasks')


@shared_task
def end_game_simulation(message):
   
    app.send_task(
        'game_end',
        args=[message],
        queue='matchmaking_tasks')
