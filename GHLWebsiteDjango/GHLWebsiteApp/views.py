from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, "GHLWebsiteApp/index.html")

def standings(request):
    return render(request, "GHLWebsiteApp/standings.html")

def team(request, teamID):
    return render(request, "GHLWebsiteApp/team.html", {"teamID": teamID})

def player(request, playerID):
    return render(request, "GHLWebsiteApp/player.html", {"playerID": playerID})