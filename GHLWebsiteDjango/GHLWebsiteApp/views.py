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

def player(request, player):
    playernum = get_object_or_404(PlayerList, pk=player)
    allskatergames = playernum.skaterrecords_set.all()
    if not allskatergames:
        sk_gp = sk_g = sk_a = sk_hits = sk_plus_minus = sk_sog = sk_shot_att = sk_ppg = sk_shg = sk_pass_att = sk_pass_comp = sk_bs = sk_tk = sk_int = sk_gva = sk_pens_drawn = sk_pims = sk_pk_clears = sk_poss_time = sk_sht_perc = sk_sht_eff = sk_pass_perc = sk_fo_perc = sk_fow = sk_fol = 0
        print("No Skater Stats")
    else:
        sk_gp = allskatergames.aggregate(Count("game_num"))["game_num__count"]
        sk_g = allskatergames.aggregate(Sum("goals"))["goals__sum"]
        sk_a = allskatergames.aggregate(Sum("assists"))["assists__sum"]
        sk_hits = allskatergames.aggregate(Sum("hits"))["hits__sum"]
        sk_plus_minus = allskatergames.aggregate(Sum("plus_minus"))["plus_minus__sum"]
        sk_sog = allskatergames.aggregate(Sum("sog"))["sog__sum"]
        sk_shot_att = allskatergames.aggregate(Sum("shot_attempts"))["shot_attempts__sum"]
        sk_ppg = allskatergames.aggregate(Sum("ppg"))["ppg__sum"]
        sk_shg = allskatergames.aggregate(Sum("shg"))["shg__sum"]
        sk_pass_att = allskatergames.aggregate(Sum("pass_att"))["pass_att__sum"]
        sk_pass_comp = allskatergames.aggregate(Sum("pass_comp"))["pass_comp__sum"]
        sk_bs = allskatergames.aggregate(Sum("blocked_shots"))["blocked_shots__sum"]
        sk_tk = allskatergames.aggregate(Sum("takeaways"))["takeaways__sum"]
        sk_int = allskatergames.aggregate(Sum("interceptions"))["interceptions__sum"]
        sk_gva = allskatergames.aggregate(Sum("giveaways"))["giveaways__sum"]
        sk_pens_drawn = allskatergames.aggregate(Sum("pens_drawn"))["pens_drawn__sum"]
        sk_pims = allskatergames.aggregate(Sum("pims"))["pims__sum"]
        sk_pk_clears = allskatergames.aggregate(Sum("pk_clears"))["pk_clears__sum"]
        sk_poss_time = round((allskatergames.aggregate(Sum("poss_time"))["poss_time__sum"])/sk_gp, 1)
        sk_fow = allskatergames.aggregate(Sum("fow"))["fow__sum"]
        sk_fol = allskatergames.aggregate(Sum("fol"))["fol__sum"]
        sk_sht_perc = round((sk_g / sk_sog)*100, 1)
        sk_sht_eff = round(sk_sog / sk_shot_att, 3)*100
        sk_pass_perc = round((sk_pass_comp / sk_pass_att)*100, 1)
        if sk_fol + sk_fow > 0:
            sk_fo_perc = round((sk_fow / (sk_fow + sk_fol))* 100, 1) 
        else:
            sk_fo_perc = "n/a"

    allgoaliegames = playernum.goalierecords_set.all()
    if not allgoaliegames:
        g_gp = g_sha = g_sav = g_br_sh = g_br_sa = g_ps_sh = g_ps_sa = g_ga =  g_svp = 0
    else:
        g_gp = allgoaliegames.aggregate(Count("game_num"))["game_num__count"]
        g_sha = allgoaliegames.aggregate(Sum("shots_against"))["shots_against__sum"]
        g_sav = allgoaliegames.aggregate(Sum("saves"))["saves__sum"]
        g_br_sh = allgoaliegames.aggregate(Sum("breakaway_shots"))["breakaway_shots__sum"]
        g_br_sa = allgoaliegames.aggregate(Sum("breakaway_saves"))["breakaway_saves__sum"]
        g_ps_sh = allgoaliegames.aggregate(Sum("ps_shots"))["ps_shots__sum"]
        g_ps_sa = allgoaliegames.aggregate(Sum("ps_saves"))["ps_saves__sum"]
        g_ga = g_sha - g_sav
        g_svp = round((g_sav / g_sha)*100,1)
        if g_br_sh > 0:
            g_br_perc = round((g_br_sa / g_br_sh)*100,1)
        else:
            g_br_perc = "n/a"
        if g_ps_sh > 0:
            g_ps_perc = round((g_ps_sa / g_ps_sh)*100,1)
        else:
            g_ps_perc = "n/a"

    sk_p = sk_g + sk_a
    context = {
        "playernum": playernum, 
        "sk_gp": sk_gp, 
        "sk_g": sk_g, 
        "sk_a": sk_a, 
        "sk_p": sk_p,
        "sk_hits": sk_hits, 
        "sk_plus_minus": sk_plus_minus, 
        "sk_sog": sk_sog, 
        "sk_sht_perc": sk_sht_perc,
        "sk_sht_eff": sk_sht_eff,
        "sk_ppg": sk_ppg,
        "sk_shg": sk_shg,
        "sk_pass_perc": sk_pass_perc,
        "sk_bs": sk_bs,
        "sk_tk": sk_tk,
        "sk_int": sk_int,
        "sk_gva": sk_gva,
        "sk_pens_drawn": sk_pens_drawn,
        "sk_pims": sk_pims,
        "sk_pk_clears": sk_pk_clears,
        "sk_poss_time": sk_poss_time,
        "sk_fo_perc": sk_fo_perc,
        "g_gp": g_gp,
        "g_ga": g_ga,
        "g_sha": g_sha,
        "g_svp": g_svp,
        "g_br_sh": g_br_sh,
        "g_ps_sh": g_ps_sh,
        "g_br_perc": g_br_perc,
        "g_ps_perc": g_ps_perc,
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html")

def awards(request, awardnum):
    award = get_object_or_404(AwardsList, pk=awardnum)
    return render(request, "GHLWebsiteApp/awards.html", {"award": award})