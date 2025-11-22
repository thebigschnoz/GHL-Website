from GHLWebsiteApp.views import get_scoreboard, get_seasonSetting
from GHLWebsiteApp.models import Season

def scoreboard_context(request):
    return {
        "scoreboard": get_scoreboard()
    }

def active_season(request):
    try:
        season = Season.objects.get(season_num=get_seasonSetting())
    except Season.DoesNotExist:
        season = None
    return {"active_season": season}