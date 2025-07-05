from GHLWebsiteApp.views import get_scoreboard

def scoreboard_context(request):
    return {
        "scoreboard": get_scoreboard()
    }