from django.shortcuts import render, get_object_or_404
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F
from django.db.models.functions import Cast

seasonSetting = 1 # Current season in GHL

# Create your views here.
def index(request):
    return render(request, "GHLWebsiteApp/index.html")

def standings(request):
    return render(request, "GHLWebsiteApp/standings.html")

def leaders(request):
    leaders_goals = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numgoals=Sum("goals")).order_by("-numgoals")[:10]
    leaders_assists = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numassists=Sum("assists")).order_by("-numassists")[:10]
    leaders_points = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numpoints=(Sum("goals")+Sum("assists"))).order_by("-numpoints")[:10]
    leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).order_by("-shootperc")[:10]
    leaders_svp = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:10]
    leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
        shutoutcount=Sum(Case(
        When(shutout=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).order_by("-shutoutcount")[:10]
    leaders_wins = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
        wincount=Sum(Case(
        When(win=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).order_by("-wincount")[:10]
    leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(gaatotal=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600).order_by("gaatotal")[:10]
    #for player in leaders_goals, leaders_assists, leaders_points, leaders_shooting, leaders_svp, leaders_shutouts, leaders_wins, leaders_gaa:
        #playerobj = PlayerList.objects.get(pk=player)
        #teamabbr = playerobj.club_abbr
        #player.append({"teamabbr": teamabbr})
    context = {
        "leaders_goals": leaders_goals,
        "leaders_assists": leaders_assists,
        "leaders_points": leaders_points,
        "leaders_shooting": leaders_shooting,
        "leaders_svp": leaders_svp,
        "leaders_shutouts": leaders_shutouts,
        "leaders_wins": leaders_wins,
        "leaders_gaa": leaders_gaa,
    }
    return render(request, "GHLWebsiteApp/leaders.html", context)

def skaters(request):
    all_skaters = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
        skatersgp=Count("game_num"),
        skatersgoals=Sum("goals"),
        skatersassists=Sum("assists"),
        skaterspoints=Sum("points"),
        skatersplusminus=Sum("plus_minus"),
        skatershits=Sum("hits"),
        skaterspims=Sum("pims"),
        skaterssog=Sum("sog"),
        skatersposs=Avg("poss_time"),
        skatersbs=Avg("blocked_shots"),
        skatersppg=Sum("ppg"),
        skatersshg=Sum("shg"),
    ).order_by("ea_player_num")
    context = {
        "all_skaters": all_skaters
    }
    return render(request, "GHLWebsiteApp/skaters.html", context)

def goalies(request):
    all_goalies = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
        goaliesgp=Count("game_num"),
        goaliesshots=Sum("shots_against"),
        goaliesga=(Sum("shots_against")-Sum("saves")),
        goaliessaves=Sum("saves"),
        goaliessvp=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100,
        goaliesgaa=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600,
        #goaliesshutouts
        #goalieswins
        #goalieslosses
        #goaliesotlosses
    ).order_by("ea_player_num")
    context = {
        "all_goalies": all_goalies
    }
    return render(request, "GHLWebsiteApp/goalies.html", context)

def team(request, team):
    teamnum = get_object_or_404(Team, pk=team)
    context = {"team": teamnum}
    return render(request, "GHLWebsiteApp/team.html", context)

def player(request, player):
    playernum = get_object_or_404(Player, pk=player)
    allskatergames = playernum.skaterrecords_set.filter(season_num = seasonSetting)
    if not allskatergames:
        sk_gp = sk_g = sk_a = sk_hits = sk_plus_minus = sk_sog = sk_shot_att = sk_ppg = sk_shg = sk_pass_att = sk_pass_comp = sk_bs = sk_tk = sk_int = sk_gva = sk_pens_drawn = sk_pims = sk_pk_clears = sk_poss_time = sk_sht_perc = sk_sht_eff = sk_pass_perc = sk_fo_perc = sk_fow = sk_fol = 0
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
        g_gp = g_sha = g_sav = g_br_sh = g_br_sa = g_ps_sh = g_ps_sa = g_ga =  g_svp = g_br_perc = g_ps_perc = 0
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
    sk_team_num = playernum.current_team.ea_club_num
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
        "sk_team_num": sk_team_num,
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html")

def awards(request, awardnum):
    award = get_object_or_404(AwardTitle, pk=awardnum)
    return render(request, "GHLWebsiteApp/awards.html", {"award": award})

def calculate_standings(Season):
    teams = Team.objects.filter(isActive=True)
    standings = []
    for team in teams:
        wins = Game.objects.filter(season_num=seasonSetting, a_team_num=team, a_team_gf__gt=F("h_team_gf")).count() + Game.objects.filter(h_team_num=team, h_team_gf__gt=F("a_team_gf")).count()
        losses = Game.objects.filter(season_num=seasonSetting, a_team_num=team, gamelength__lte=3600, a_team_gf__lt=F('h_team_gf')).count() + Game.objects.filter(team2=team, h_team_gf__lt=F('a_team_gf')).count()
        otlosses = Game.objects.filter(season_num=seasonSetting, a_team_num=team, gamelength__gt=3600, a_team_gf=F('h_team_gf')).count() + Game.objects.filter(team2=team, h_team_gf=F('a_team_gf')).count()
        points = wins * 2 + otlosses
        standings.append({"team": team.name, "wins": wins, "losses": losses, "otlosses": otlosses, "points": points})
    standings = sorted(standings, key=lambda x: x["points"], reverse=True)
    return standings