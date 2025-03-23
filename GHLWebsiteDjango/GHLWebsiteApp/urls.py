from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('standings/', views.standings, name="standings"),
    path('leaders/', views.leaders, name="leaders"),
    path('skaters/', views.skaters, name="skaters"),
    path('goalies/', views.goalies, name="goalies"),
    path('team/<int:team>/', views.team, name="team"),
    path('player/', views.skaters, name="playernonum"),
    path('player/<int:player>/', views.player, name="player"),
    path('awards/', views.awardsDef, name="awardsDef"),
    path('awards/<int:award>/', views.awards, name="awards"),
    path('draft/', views.draft, name="draft"),
    # path('game/', views.calendar, name="calendar"),
    path('game/<int:game>/', views.game, name="game"),
    path('gameapi/', views.GamesRequest, name="gamesrequest"),
    path('uploadcsvforgames/', views.upload_file, name="upload_file"),
]