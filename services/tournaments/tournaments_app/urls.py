from django.urls import path
from . import views

urlpatterns = [
    path('create', views.create_tournament, name='create_tournament'),
    path('', views.list_tournaments, name='list_tournaments'),
    path('<int:tournament_id>/join', views.join_tournament, name='join_tournament'),
	path('player_counts', views.list_tournament_player_counts, name='list_tournament_player_counts'),
]
