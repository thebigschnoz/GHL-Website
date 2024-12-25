from django.shortcuts import render, get_object_or_404
from GHLWebsiteApp.models import *

# Create your views here.
def index(request):
    return render(request, "GHLWebsiteApp/index.html")

def standings(request):
    return render(request, "GHLWebsiteApp/standings.html")

def leaders(request):
    return render(request, "GHLWebsiteApp/leaders.html")

def skaters(request):
    return render(request, "GHLWebsiteApp/skaters.html")

def goalies(request):
    return render(request, "GHLWebsiteApp/goalies.html")

def team(request, teamID):
    thisteam = get_object_or_404(TeamList, pk=teamID)
    return render(request, "GHLWebsiteApp/team.html", {"teamID": thisteam})

def player(request, playerID):
    thisplayer = get_object_or_404(PlayerList, pk=playerID)
    return render(request, "GHLWebsiteApp/player.html", {"playerID": thisplayer})

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html")

def awards(request, award):
    thisaward = get_object_or_404(AwardsList, pk=award)
    return render(request, "GHLWebsiteApp/awards.html", {"award": thisaward})