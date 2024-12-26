from django.shortcuts import render, get_object_or_404
from GHLWebsiteApp.models import *
from django.db.models import Avg, Sum, Count

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

def team(request, teamnum):
    team = get_object_or_404(TeamList, pk=teamnum)
    context = {"team": team}
    return render(request, "GHLWebsiteApp/team.html", context)

def player(request, playernum):
    player = get_object_or_404(PlayerList, pk=playernum)
    try: 
        allskatergames = player.skaterrecords_set.all()
    except player.skaterrecords_set.DoesNotExist:
        sk_gp = sk_g = sk_a = sk_hits = sk_plus_minus = sk_sog = sk_shot_att = sk_deflections = sk_ppg = sk_shg = sk_pass_att = sk_pass_comp = sk_saucer = sk_bs = sk_tk = sk_int = sk_gwa = sk_pens_drawn = sk_pims = sk_pk_clears = sk_poss_time = sk_fow = sk_fol = 0
    sk_gp = allskatergames.objects.aggregate(Count("game_num"))
    sk_g = allskatergames.objects.aggregate(Sum("goals"))
    sk_a = allskatergames.objects.aggregate(Sum("assists"))
    sk_hits = allskatergames.objects.aggregate(Sum("hits"))
    sk_plus_minus = allskatergames.objects.aggregate(Sum("plus_minus"))
    sk_sog = allskatergames.objects.aggregate(Sum("sog"))
    sk_shot_att = allskatergames.objects.aggregate(Sum("shot_attempts"))
    sk_deflections = allskatergames.objects.aggregate(Sum("deflections"))
    sk_ppg = allskatergames.objects.aggregate(Sum("ppg"))
    sk_shg = allskatergames.objects.aggregate(Sum("shg"))
    sk_pass_att = allskatergames.objects.aggregate(Sum("pass_att"))
    sk_pass_comp = allskatergames.objects.aggregate(Sum("pass_comp"))
    sk_saucer = allskatergames.objects.aggregate(Sum("saucer_pass"))
    sk_bs = allskatergames.objects.aggregate(Sum("blocked_shots"))
    sk_tk = allskatergames.objects.aggregate(Sum("takeaways"))
    sk_int = allskatergames.objects.aggregate(Sum("interceptions"))
    sk_gwa = allskatergames.objects.aggregate(Sum("giveaways"))
    sk_pens_drawn = allskatergames.objects.aggregate(Sum("pens_drawn"))
    sk_pims = allskatergames.objects.aggregate(Sum("pims"))
    sk_pk_clears = allskatergames.objects.aggregate(Sum("pk_clears"))
    sk_poss_time = allskatergames.objects.aggregate(Sum("poss_time"))
    sk_fow = allskatergames.objects.aggregate(Sum("fow"))
    sk_fol = allskatergames.objects.aggregate(Sum("fol"))
    try:
        allgoaliegames = player.goalierecords_set.all()
    except player.goalierecords_set.DoesNotExist:
        g_gp = g_sha = g_sav = g_br_sh = g_br_sa = g_ps_sh = g_ps_sa = 0
    g_gp = allgoaliegames.objects.aggregate(Count("game_num"))
    g_sha = allgoaliegames.objects.aggregate(Sum("shots_against"))
    g_sav = allgoaliegames.objects.aggregate(Sum("saves"))
    g_br_sh = allgoaliegames.objects.aggregate(Sum("breakaway_shots"))
    g_br_sa = allgoaliegames.objects.aggregate(Sum("breakaway_saves"))
    g_ps_sh = allgoaliegames.objects.aggregate(Sum("ps_shots"))
    g_ps_sa = allgoaliegames.objects.aggregate(Sum("ps_saves"))
    context = {
        "playerID": player, 
        "sk_gp": sk_gp, 
        "sk_g": sk_g, 
        "sk_a": sk_a, 
        "sk_hits": sk_hits, 
        "sk_plus_minus": sk_plus_minus, 
        "sk_sog": sk_sog, 
        "sk_shot_att": sk_shot_att, 
        "sk_deflections": sk_deflections,
        "sk_ppg": sk_ppg,
        "sk_shg": sk_shg,
        "sk_pass_att": sk_pass_att,
        "sk_pass_comp": sk_pass_comp,
        "sk_saucer": sk_saucer,
        "sk_bs": sk_bs,
        "sk_tk": sk_tk,
        "sk_int": sk_int,
        "sk_gwa": sk_gwa,
        "sk_pens_drawn": sk_pens_drawn,
        "sk_pims": sk_pims,
        "sk_pk_clears": sk_pk_clears,
        "sk_poss_time": sk_poss_time,
        "sk_fow": sk_fow,
        "sk_fol": sk_fol,
        "g_gp": g_gp,
        "g_sha": g_sha,
        "g_sav": g_sav,
        "g_br_sh": g_br_sh,
        "g_br_sa": g_br_sa,
        "g_ps_sh": g_ps_sh,
        "g_ps_sa": g_ps_sa,
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html")

def awards(request, awardnum):
    award = get_object_or_404(AwardsList, pk=awardnum)
    return render(request, "GHLWebsiteApp/awards.html", {"award": award})