from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('standings/', views.standings, name="standings"),
    path('leaders/', views.leaders, name="leaders"),
    path('skaters/', views.skaters, name="skaters"),
    path('skaters/advanced/', views.skatersAdvanced, name="skatersAdvanced"),
    path('goalies/', views.goalies, name="goalies"),
    path('team/<int:team>/', views.team, name="team"),
    path('player/', views.skaters, name="playernonum"),
    path('player/<int:player>/', views.player, name="player"),
    path('playerlist/', views.playerlist, name="playerlist"),
    path('awards/', views.awardsDef, name="awardsDef"),
    path('awards/<int:awardnum>/', views.awards, name="awards"),
    path('draft/', views.draft, name="draft"),
    path('game/<int:game>/', views.game, name="game"),
    path('gameapi/', views.GamesRequest, name="gamesrequest"),
    path('uploadcsvforgames/', views.upload_file, name="upload_file"),
    path('glossary/', views.glossary, name="glossary"),
    path('export/team/<int:team_id>/', views.export_team, name="export_team"),
    path('export/playerdata/', views.export_player_data, name="export_player_data"),
]