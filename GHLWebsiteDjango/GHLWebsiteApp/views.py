from django.shortcuts import render

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
    return render(request, "GHLWebsiteApp/team.html", {"teamID": teamID})

def player(request, playerID):
    return render(request, "GHLWebsiteApp/player.html", {"playerID": playerID})

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html")

def awards(request, award):
    return render(request, "GHLWebsiteApp/awards.html", {"award": award})