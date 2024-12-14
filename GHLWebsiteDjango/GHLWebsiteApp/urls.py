from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('standings/', views.standings, name="standings"),
    path('leaders/', views.leaders, name="leaders"),
    path('skaters/', views.skaters, name="skaters"),
    path('goalies/', views.goalies, name="goalies"),
    path('team/<int:teamID>/', views.team, name="team"),
    path('player/<int:playerID>/', views.player, name="player"),
    path('awards/', views.awardsDef, name="awardsDef"),
    path('awards/<int:award>/', views.awards, name="awards"),
    path('draft/', views.draft, name="draft"),
]
