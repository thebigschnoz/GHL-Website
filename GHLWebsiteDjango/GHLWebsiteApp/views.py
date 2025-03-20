from django.shortcuts import render, get_object_or_404
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.core import serializers
from decimal import *
import random, json

seasonSetting = 1 # Current season in GHL

def get_seasonSetting():
    return seasonSetting

def calculate_leaders():
    Leader.objects.all().delete()
    skatergames = SkaterRecord.objects.filter(game_num__season_num=seasonSetting)
    if not skatergames:
        Leader.objects.bulk_create(
        [
            Leader(attribute="Pts", stat=0),
            Leader(attribute="G", stat=0),
            Leader(attribute="A", stat=0),
            Leader(attribute="SH%", stat=0),
            Leader(attribute="GAA", stat=0),
            Leader(attribute="SV%", stat=0),
            Leader(attribute="W", stat=0),
            Leader(attribute="SO", stat=0),
        ]
    )
    else:
        leaders_goals = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numgoals=Sum("goals")).filter(numgoals__gt=0).order_by("-numgoals")[:1]
        leaders_assists = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numassists=Sum("assists")).filter(numassists__gt=0).order_by("-numassists")[:1]
        leaders_points = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(numpoints=Sum("points")).filter(numpoints__gt=0).order_by("-numpoints")[:1]
        leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).filter(shootperc__gt=0).order_by("-shootperc")[:1]
        leaders_svp = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:1]
        leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
            shutoutcount=Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(shutoutcount__gte=1).order_by("-shutoutcount")[:1]
        leaders_wins = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(
            wincount=Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(wincount__gte=1).order_by("-wincount")[:1]
        leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).annotate(gaatotal=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600).order_by("gaatotal")[:1]
        Leader.objects.bulk_create(
            [
                Leader(attribute="Pts", player=leaders_points[0].ea_player_num, stat=leaders_points[0].numpoints),
                Leader(attribute="G", player=leaders_goals[0].ea_player_num, stat=leaders_goals[0].numgoals),
                Leader(attribute="A", player=leaders_assists[0].ea_player_num, stat=leaders_assists[0].numassists),
                Leader(attribute="SH%", player=leaders_shooting[0].ea_player_num, stat=leaders_shooting[0].shootperc),
                Leader(attribute="GAA", player=leaders_gaa[0].ea_player_num, stat=leaders_gaa[0].gaatotal),
                Leader(attribute="SV%", player=leaders_svp[0].ea_player_num, stat=leaders_svp[0].savepercsum),
                Leader(attribute="W", player=leaders_wins[0].ea_player_num, stat=leaders_wins[0].wincount),
                Leader(attribute="SO", player=leaders_shutouts[0].ea_player_num, stat=leaders_shutouts[0].shutoutcount),
            ]
        )

def calculate_standings():
    teams = Team.objects.filter(isActive=True)
    for team in teams:
        gamelist = Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team).count() + Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team).count()
        if not gamelist:
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=seasonSetting), defaults={"wins":0, "losses":0, "otlosses":0, "points":0, "goalsfor":0, "goalsagainst":0, "gp":0, "winperc":Decimal(0), "ppperc":Decimal(0), "pkperc":Decimal(0), "lastten":"0-0-0"})
        else:
            wins = Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team, a_team_gf__gt=F("h_team_gf")).count() + Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team, h_team_gf__gt=F("a_team_gf")).count()
            losses = Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team, gamelength__lte=3600, a_team_gf__lt=F("h_team_gf")).count() + Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team, gamelength__lte=3600, h_team_gf__lt=F("a_team_gf")).count()
            otlosses = Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team, gamelength__gt=3600, a_team_gf__lt=F("h_team_gf")).count() + Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team, gamelength__gt=3600, h_team_gf__lt=F("a_team_gf")).count()
            points = wins * 2 + otlosses
            goalsfor = (Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team).aggregate(Sum("a_team_gf"))["a_team_gf__sum"] or 0) + (Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team).aggregate(Sum("h_team_gf"))["h_team_gf__sum"] or 0)
            goalsagainst = (Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team).aggregate(Sum("h_team_gf"))["h_team_gf__sum"] or 0) + (Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team).aggregate(Sum("a_team_gf"))["a_team_gf__sum"] or 0)
            gp = gamelist
            try:
                winperc = round((Decimal(points) / Decimal(gp*2))*100, 1)
            except InvalidOperation:
                winperc = Decimal(0)
            ppocalc = TeamRecord.objects.filter(game_num__season_num=seasonSetting, ea_club_num=team).aggregate(Sum("ppo_team"))["ppo_team__sum"] # total power play opportunities for the team
            if ppocalc == 0:
                ppperc = Decimal(0)
            else:
                try:
                    ppperc = round((Decimal(TeamRecord.objects.filter(game_num__season_num=seasonSetting, ea_club_num=team).aggregate(Sum("ppg_team"))["ppg_team__sum"]) / Decimal(ppocalc))*100, 1)
                except InvalidOperation:
                    ppperc = Decimal(0)
            pkgames = Game.objects.filter(season_num=seasonSetting, a_team_num__isActive=True, a_team_num=team) | Game.objects.filter(season_num=seasonSetting, h_team_num__isActive=True, h_team_num=team) # get all games team is in
            pkoppscalc = Decimal(TeamRecord.objects.filter(game_num__in=pkgames).exclude(ea_club_num=team).aggregate(Sum("ppo_team"))["ppo_team__sum"]) # total TeamRecord power play opportunities in pkgames excluding the team
            if pkoppscalc == 0:
                pkperc = Decimal(0)
            else:
                try:
                    pkperc = round((1 - (Decimal(TeamRecord.objects.filter(game_num__in=pkgames).exclude(ea_club_num=team).aggregate(Sum("ppg_team"))["ppg_team__sum"]) / pkoppscalc))*100, 1)
                except InvalidOperation:
                    pkperc = Decimal(0)
            lasttengames = TeamRecord.objects.filter(game_num__season_num=seasonSetting, ea_club_num=team).order_by("-game_num")[:10:-1]
                # this is where I totally forgot that I made TeamRecord as a model. Schnoz, you idiot
            l10w = l10l = l10otl = 0
            for game in lasttengames:
                if game.goals_for > game.goals_against:
                    l10w += 1
                elif game.game_num.gamelength > 3600:
                    l10otl += 1
                else:
                    l10l += 1
            lastten = f"{l10w}-{l10l}-{l10otl}"

            recent_games = TeamRecord.objects.filter(game_num__season_num=seasonSetting, ea_club_num=team).order_by("-game_num")
            streak_type = None
            streak_count = 0
            if not recent_games:
                streak = "n/a"
            else:
                for game in recent_games:
                    if streak_type is None:
                        if game.goals_for > game.goals_against:
                            streak_type = "W"
                            streak_count = 1
                        else:
                            streak_type = "L"
                            streak_count = 1
                    else:
                        if (streak_type == "W" and game.goals_for > game.goals_against) or (streak_type == "L" and game.goals_for < game.goals_against):
                            streak_count += 1
                        else:
                            break
                streak = f"{streak_type}{streak_count}"
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=seasonSetting), defaults={'wins': wins, 'losses': losses, 'otlosses': otlosses, 'points': points, 'goalsfor': goalsfor, 'goalsagainst': goalsagainst, "gp": gp, "winperc": winperc, "ppperc": ppperc, "pkperc": pkperc, "lastten": lastten, "streak": streak})

def get_scoreboard():
    data = Game.objects.filter(season_num=seasonSetting).order_by("-played_time")[:15]
    return data

def GamesRequest(request):
    data = Game.objects.filter(season_num=seasonSetting).values("game_num", "gamelength", "played_time", "a_team_num__club_abbr", "h_team_num__club_abbr", "a_team_num__team_logo_link", "h_team_num__team_logo_link" "a_team_gf", "h_team_gf").order_by("-played_time")[:15]
    response = JsonResponse(dict(gamelist=list(data)), safe=False)
    return response

def index(request):
    allgames = SkaterRecord.objects.filter(game_num__season_num=seasonSetting)
    if not allgames:
        if not SkaterRecord.objects.all():
            randomplayer = gp = goals = assists = plusminus = pims = "(No GP yet)"
            thisseason = 0
        else:
            randomplayer = random.choice(Player.objects.all())
            username = randomplayer.username
            gp = SkaterRecord.objects.filter(ea_player_num=randomplayer).count()
            goals = SkaterRecord.objects.filter(ea_player_num=randomplayer).aggregate(Sum("goals"))["goals__sum"]
            assists = SkaterRecord.objects.filter(ea_player_num=randomplayer).aggregate(Sum("assists"))["assists__sum"]
            plusminus = SkaterRecord.objects.filter(ea_player_num=randomplayer).aggregate(Sum("plus_minus"))["plus_minus__sum"]
            pims = SkaterRecord.objects.filter(ea_player_num=randomplayer).aggregate(Sum("pims"))["pims__sum"]
            thisseason = 0
    else:
        randomgame = random.choice(allgames)
        randomplayer = randomgame.ea_player_num
        username = randomplayer.username
        gp = SkaterRecord.objects.filter(game_num__season_num=seasonSetting, ea_player_num=randomplayer).count()
        goals = SkaterRecord.objects.filter(game_num__season_num=seasonSetting, ea_player_num=randomplayer).aggregate(Sum("goals"))["goals__sum"]
        assists = SkaterRecord.objects.filter(game_num__season_num=seasonSetting, ea_player_num=randomplayer).aggregate(Sum("assists"))["assists__sum"]
        plusminus = SkaterRecord.objects.filter(game_num__season_num=seasonSetting, ea_player_num=randomplayer).aggregate(Sum("plus_minus"))["plus_minus__sum"]
        pims = SkaterRecord.objects.filter(game_num__season_num=seasonSetting, ea_player_num=randomplayer).aggregate(Sum("pims"))["pims__sum"]
        thisseason = 1
    standings = Standing.objects.filter(season=seasonSetting).order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
    leaders = Leader.objects.all().values("attribute", "stat", "player__username")
    scoreboard = get_scoreboard()
    context = {"standings": standings, "leaders": leaders, "thisseason": thisseason, "username": username, "gp": gp, "goals": goals, "assists": assists, "plusminus": plusminus, "pims": pims, "scoreboard": scoreboard}
    return render(request, "GHLWebsiteApp/index.html", context)

def standings(request):
    standings = Standing.objects.filter(season=seasonSetting).order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
    season = Season.objects.get(season_num=seasonSetting)
    return render(request, "GHLWebsiteApp/standings.html", {"standings": standings, "scoreboard": get_scoreboard(), "season": season})

def leaders(request):
    leaders_goals = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numgoals=Sum("goals")).filter(numgoals__gt=0).order_by("-numgoals")[:10]
    leaders_assists = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numassists=Sum("assists")).filter(numassists__gt=0).order_by("-numassists")[:10]
    leaders_points = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numpoints=Sum("points")).filter(numpoints__gt=0).order_by("-numpoints")[:10]
    leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).filter(shootperc__gt=0).order_by("-shootperc")[:10]
    leaders_svp = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:10]
    leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        shutoutcount=Sum(Case(
        When(shutout=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(shutoutcount__gte=1).order_by("-shutoutcount")[:10]
    leaders_wins = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        wincount=Sum(Case(
        When(win=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(wincount__gte=1).order_by("-wincount")[:10]
    leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(gaatotal=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600).order_by("gaatotal")[:10]
    context = {
        "leaders_goals": leaders_goals,
        "leaders_assists": leaders_assists,
        "leaders_points": leaders_points,
        "leaders_shooting": leaders_shooting,
        "leaders_svp": leaders_svp,
        "leaders_shutouts": leaders_shutouts,
        "leaders_wins": leaders_wins,
        "leaders_gaa": leaders_gaa,
        "scoreboard": get_scoreboard()
    }
    return render(request, "GHLWebsiteApp/leaders.html", context)

def skaters(request):
    all_skaters = SkaterRecord.objects.filter(game_num__season_num=seasonSetting).exclude(position=0).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
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
    ).order_by("-skaterspoints", "-skatersgoals", "-skatersgp", "skaterspims", "ea_player_num__username")
    season = Season.objects.get(season_num=seasonSetting)
    context = {
        "all_skaters": all_skaters,
        "scoreboard": get_scoreboard(),
        "season": season
    }
    return render(request, "GHLWebsiteApp/skaters.html", context)

def goalies(request):
    all_goalies = GoalieRecord.objects.filter(game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        goaliesgp = Count("game_num"),
        goaliesshots = Sum("shots_against"),
        goaliesga = (Sum("shots_against")-Sum("saves")),
        goaliessaves = Sum("saves"),
        goaliessvp = (Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100,
        goaliesgaa = ((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600,
        goaliesshutouts =Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goalieswins = Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goalieslosses = Sum(Case(
            When(loss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goaliesotlosses = Sum(Case(
            When(otloss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
    ).order_by("-goaliessvp", "-goalieswins", "-goaliesshutouts", "ea_player_num__username")
    season = Season.objects.get(season_num=seasonSetting)
    context = {
        "all_goalies": all_goalies,
        "scoreboard": get_scoreboard(),
        "season": season
    }
    return render(request, "GHLWebsiteApp/goalies.html", context)

def team(request, team):
    teamnum = get_object_or_404(Team, pk=team)
    skaterrecords = SkaterRecord.objects.filter(ea_club_num=teamnum.ea_club_num, game_num__season_num=seasonSetting).exclude(position="0").values("ea_player_num", "ea_player_num__username").annotate(
        skatersgp=Count("game_num"),
        skatersgoals=Sum("goals"),
        skatersassists=Sum("assists"),
        skaterspoints=Sum("points"),
        skaterssog=Sum("sog"),
        skatersdeflections=Sum("deflections"),
        skatersplusminus=Sum("plus_minus"),
        skatershits=Sum("hits"),
        skaterspims=Sum("pims"),
        skatersfow=Sum("fow"),
        skatersfol=Sum("fol"),
        skatersposs=Avg("poss_time"),
        skatersbs=Avg("blocked_shots"),
        skatersint=Sum("interceptions"),
        skatersgva=Sum("giveaways"),
        skaterstakeaways=Sum("takeaways"),
        skaterspensdrawn=Sum("pens_drawn"),
        skaterspkclears=Sum("pk_clears"),
        skatersppg=Sum("ppg"),
        skatersshg=Sum("shg"),
        skatersshotperc=Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField())*100,
        skatersshoteffperc=Cast(Sum("sog"), models.FloatField())/Cast(Sum("shot_attempts"), models.FloatField())*100,
        skaterspassperc=Cast(Sum("pass_comp"), models.FloatField())/Cast(Sum("pass_att"), models.FloatField())*100,
    ).order_by("ea_player_num")
    goalierecords = GoalieRecord.objects.filter(ea_club_num=teamnum.ea_club_num, game_num__season_num=seasonSetting).values("ea_player_num", "ea_player_num__username").annotate(
        goaliesgp = Count("game_num"),
        goaliesshots = Sum("shots_against"),
        goaliessaves = Sum("saves"),
        goaliessvp = (Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100,
        goaliesbashots = Sum("breakaway_shots"),
        goaliesbasaves = Sum("breakaway_saves"),
        goaliespsshots = Sum("ps_shots"),
        goaliespssaves = Sum("ps_saves"),
        goaliesgaa = ((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600,
        goaliesshutouts =Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goalieswins = Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goalieslosses = Sum(Case(
            When(loss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        goaliesotlosses = Sum(Case(
            When(otloss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
    ).order_by("ea_player_num")
    teamgames = Game.objects.filter(season_num=seasonSetting, a_team_num=teamnum) | Game.objects.filter(season_num=seasonSetting, h_team_num=teamnum)
    context = {"team": teamnum, "scoreboard": get_scoreboard(), "skaterrecords": skaterrecords, "goalierecords": goalierecords, "teamgames": teamgames}  
    return render(request, "GHLWebsiteApp/team.html", context)

def game(request, game):
    gamenum = get_object_or_404(Game, pk=game)
    a_skater_records = SkaterRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num).exclude(position="0")
    h_skater_records = SkaterRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num).exclude(position="0")
    a_goalie_records = GoalieRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num)
    h_goalie_records = GoalieRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num)
    a_team_standing = Standing.objects.filter(team=gamenum.a_team_num.ea_club_num, season=seasonSetting)
    h_team_standing = Standing.objects.filter(team=gamenum.h_team_num.ea_club_num, season=seasonSetting)
    a_team_record = TeamRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num)
    h_team_record = TeamRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num)
    a_team_toa_formatted = h_team_toa_formatted = "0:00"
    if a_team_record:
        a_team_min = a_team_record[0].toa_team // 60
        a_team_sec = a_team_record[0].toa_team % 60
        a_team_toa_formatted = f"{a_team_min}:{a_team_sec:02d}"
    if h_team_record:
        h_team_min = h_team_record[0].toa_team // 60
        h_team_sec = h_team_record[0].toa_team % 60
        h_team_toa_formatted = f"{h_team_min}:{h_team_sec:02d}"
    print(a_team_record)
    context = {"game": gamenum,
               "a_skater_records": a_skater_records,
               "h_skater_records": h_skater_records,
               "a_goalie_records": a_goalie_records,
               "h_goalie_records": h_goalie_records,
               "a_team_standing": a_team_standing,
               "h_team_standing": h_team_standing,
               "a_team_record": a_team_record,
               "h_team_record": h_team_record,
               "a_team_toa": a_team_toa_formatted,
               "h_team_toa": h_team_toa_formatted,
               "scoreboard": get_scoreboard()}
    return render(request, "GHLWebsiteApp/game.html", context)

def player(request, player):
    playernum = get_object_or_404(Player, pk=player)
    allskatergames = playernum.skaterrecord_set.filter(game_num__season_num=seasonSetting).exclude(position="0")
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
        if sk_shot_att > 0:
            if sk_sog > 0:
                sk_sht_perc = round((sk_g / sk_sog)*100, 1)
            else:
                sk_sht_perc = "-"
            sk_sht_eff = round(sk_sog / sk_shot_att, 3)*100
        else:
            sk_sht_perc = sk_sht_eff = "-"

        sk_pass_perc = round((sk_pass_comp / sk_pass_att)*100, 1)
        if sk_fol + sk_fow > 0:
            sk_fo_perc = round((sk_fow / (sk_fow + sk_fol))* 100, 1) 
        else:
            sk_fo_perc = "-"

    allgoaliegames = playernum.goalierecord_set.all()
    if not allgoaliegames:
        g_gp = g_so = g_wins = g_losses = g_otlosses = g_toi = g_sha = g_sav = g_gaa = g_br_sh = g_br_sa = g_ps_sh = g_ps_sa = g_ga =  g_svp = g_br_perc = g_ps_perc = 0
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
        g_so = allgoaliegames.aggregate(g_so=Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )))["g_so"]
        g_wins = allgoaliegames.aggregate(g_wins=Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )))["g_wins"]
        g_losses = allgoaliegames.aggregate(g_losses=Sum(Case(
            When(loss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )))["g_losses"]
        g_otlosses = allgoaliegames.aggregate(g_otlosses=Sum(Case(
            When(otloss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )))["g_otlosses"]
        g_gaa = allgoaliegames.aggregate(g_gaa=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600)["g_gaa"]
        g_toi = allgoaliegames.aggregate(g_toi=Sum("game_num__gamelength")/60)["g_toi"]

    sk_p = sk_g + sk_a
    if not playernum.current_team:
        sk_team_num = 0
    else:
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
        "g_so": g_so,
        "g_wins": g_wins,
        "g_losses": g_losses,
        "g_otlosses": g_otlosses,
        "g_gaa": g_gaa,
        "g_toi": g_toi,
        "sk_team_num": sk_team_num,
        "scoreboard": get_scoreboard()
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awardsDef(request):
    return render(request, "GHLWebsiteApp/awards.html", {"scoreboard": get_scoreboard()})

def awards(request, awardnum):
    award = get_object_or_404(AwardTitle, pk=awardnum)
    awardhistory = AwardAssign.objects.filter(award=awardnum).order_by("-season_num")
    awardvotes = AwardVote.objects.filter(award=awardnum).order_by("-votes_num")[:3]
    return render(request, "GHLWebsiteApp/awards.html", {
        "award": award,
        "awardvotes": awardvotes,
        "awardhistory": awardhistory,
        "scoreboard": get_scoreboard()
    })