from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('standings/', views.standings, name="standings"),
    path('team/<int:teamID>', views.team, name="team"),
    path('player/<int:playerID>', views.player, name="player"),
]
