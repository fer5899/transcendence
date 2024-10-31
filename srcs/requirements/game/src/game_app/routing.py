from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/game/', consumers.PongConsumer.as_asgi()),
]