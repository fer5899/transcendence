from django.urls import re_path
from game_app import consumers

websocket_urlpatterns = [
    re_path(r"ws/game/$", consumers.PlayerConsumer.as_asgi()),
]
