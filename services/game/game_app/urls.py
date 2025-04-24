from django.contrib import admin
from django.urls import path
from game_app import views

urlpatterns = [
    path("active/", views.has_active_game),
    path("create/", views.create_game),
	path("statistics/<int:user_id>/", views.get_match_statistics),
	path("history/<int:user_id>/", views.get_match_history),
]
