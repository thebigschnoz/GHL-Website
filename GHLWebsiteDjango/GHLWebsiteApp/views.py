from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .forms import UploadFileForm, CustomUserCreationForm
from datetime import datetime
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F, Window, FloatField, Q
from django.db.models.functions import Cast, Rank, Round, Lower
from django.http import JsonResponse, HttpResponse
from decimal import *
from itertools import chain
import random
import pandas as pd
from io import BytesIO
import csv
import pytz
from django.utils.timezone import localtime
from django.core.paginator import Paginator
# from points_table_simulator import PointsTableSimulator

def get_seasonSetting():
    seasonSetting = Season.objects.filter(isActive=True).first().season_num
    if not seasonSetting:
        seasonSetting = 1
    return seasonSetting

def calculate_leaders():
    season = get_seasonSetting()
    Leader.objects.all().delete()
    skatergames = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None)
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
        leaders_goals = SkaterRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(numgoals=Sum("goals")).order_by("-numgoals").first()
        leaders_assists = SkaterRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(numassists=Sum("assists")).order_by("-numassists").first()
        leaders_points = SkaterRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(numpoints=Sum("points")).order_by("-numpoints").first()
        leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).order_by("-shootperc").first()
        leaders_svp = GoalieRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum").first()
        leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(
            shutoutcount=Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(shutoutcount__gte=1).order_by("-shutoutcount").first()
        leaders_wins = GoalieRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(
            wincount=Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(wincount__gte=1).order_by("-wincount").first()
        leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=season).values("ea_player_num").annotate(
            gaatotal=((Cast(Sum("shots_against"), 
                models.FloatField())-Cast(Sum("saves"), 
                models.FloatField()))/Cast(Sum("game_num__gamelength"),
                models.FloatField()))*3600
            ).order_by("gaatotal").first()
        Leader.objects.bulk_create(
            [
                Leader(attribute="Pts", player=Player.objects.get(ea_player_num=leaders_points["ea_player_num"]), stat=leaders_points["numpoints"]),
                Leader(attribute="G", player=Player.objects.get(ea_player_num=leaders_goals["ea_player_num"]), stat=leaders_goals["numgoals"]),
                Leader(attribute="A", player=Player.objects.get(ea_player_num=leaders_assists["ea_player_num"]), stat=leaders_assists["numassists"]),
                Leader(attribute="SH%", player=Player.objects.get(ea_player_num=leaders_shooting["ea_player_num"]), stat=leaders_shooting["shootperc"]),
                Leader(attribute="GAA", player=Player.objects.get(ea_player_num=leaders_gaa["ea_player_num"]), stat=leaders_gaa["gaatotal"]),
                Leader(attribute="SV%", player=Player.objects.get(ea_player_num=leaders_svp["ea_player_num"]), stat=leaders_svp["savepercsum"]),
                Leader(attribute="W", player=Player.objects.get(ea_player_num=leaders_wins["ea_player_num"]), stat=leaders_wins["wincount"]),
            ]
        )
        if leaders_shutouts:
            Leader.objects.create(attribute="SO", player=Player.objects.get(ea_player_num=leaders_shutouts["ea_player_num"]), stat=leaders_shutouts["shutoutcount"])
        else:
            Leader.objects.create(attribute="SO", player=None, stat=0)

def calculate_standings():
    season = get_seasonSetting()
    teams = Team.objects.filter(isActive=True)
    for team in teams:
        gamelist = Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team).exclude(played_time=None).count() + Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team).exclude(played_time=None).count()
        if not gamelist:
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=season), defaults={"wins":0, "losses":0, "otlosses":0, "points":0, "goalsfor":0, "goalsagainst":0, "gp":0, "winperc":Decimal(0), "ppperc":Decimal(0), "pkperc":Decimal(0), "lastten":"0-0-0", "playoffs": ""})
        else:
            wins = Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team, a_team_gf__gt=F("h_team_gf")).exclude(played_time=None).count() + Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team, h_team_gf__gt=F("a_team_gf")).exclude(played_time=None).count()
            losses = Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team, gamelength__lte=3600, a_team_gf__lt=F("h_team_gf")).exclude(played_time=None).count() + Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team, gamelength__lte=3600, h_team_gf__lt=F("a_team_gf")).exclude(played_time=None).count()
            otlosses = Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team, gamelength__gt=3600, a_team_gf__lt=F("h_team_gf")).exclude(played_time=None).count() + Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team, gamelength__gt=3600, h_team_gf__lt=F("a_team_gf")).exclude(played_time=None).count()
            points = wins * 2 + otlosses
            goalsfor = (Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team).exclude(played_time=None).aggregate(Sum("a_team_gf"))["a_team_gf__sum"] or 0) + (Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team).exclude(played_time=None).aggregate(Sum("h_team_gf"))["h_team_gf__sum"] or 0)
            goalsagainst = (Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team).exclude(played_time=None).aggregate(Sum("h_team_gf"))["h_team_gf__sum"] or 0) + (Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team).exclude(played_time=None).aggregate(Sum("a_team_gf"))["a_team_gf__sum"] or 0)
            gp = gamelist
            try:
                winperc = round((Decimal(points) / Decimal(gp*2))*100, 1)
            except:
                winperc = Decimal(0)
            ppocalc = TeamRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).aggregate(Sum("ppo_team"))["ppo_team__sum"] # total power play opportunities for the team
            if ppocalc == 0:
                ppperc = Decimal(0)
            else:
                try:
                    ppperc = round((Decimal(TeamRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).aggregate(Sum("ppg_team"))["ppg_team__sum"]) / Decimal(ppocalc))*100, 1)
                except:
                    ppperc = Decimal(0)
            pkgames = Game.objects.filter(season_num=season, a_team_num__isActive=True, a_team_num=team).exclude(played_time=None) | Game.objects.filter(season_num=season, h_team_num__isActive=True, h_team_num=team).exclude(played_time=None) # get all games team is in
            pkoppscalc = Decimal(TeamRecord.objects.filter(game_num__in=pkgames).exclude(ea_club_num=team, game_num__played_time=None).aggregate(Sum("ppo_team"))["ppo_team__sum"]) # total TeamRecord power play opportunities in pkgames excluding the team
            if pkoppscalc == 0:
                pkperc = Decimal(0)
            else:
                try:
                    pkperc = round((1 - (Decimal(TeamRecord.objects.filter(game_num__in=pkgames).exclude(ea_club_num=team, game_num__played_time=None).aggregate(Sum("ppg_team"))["ppg_team__sum"]) / pkoppscalc))*100, 1)
                except:
                    pkperc = Decimal(0)
            lasttengames = TeamRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).order_by("-game_num")[:10:-1]
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

            recent_games = TeamRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).order_by("-game_num")
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
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=season), defaults={'wins': wins, 'losses': losses, 'otlosses': otlosses, 'points': points, 'goalsfor': goalsfor, 'goalsagainst': goalsagainst, "gp": gp, "winperc": winperc, "ppperc": ppperc, "pkperc": pkperc, "lastten": lastten, "streak": streak, "playoffs": ""})

    # Compile schedule for PointsTableSimulator
    '''games = Game.objects.filter(season_num=season).values(
        "game_num", 
        "h_team_num__club_full_name", 
        "a_team_num__club_full_name", 
        "played_time", 
        "h_team_gf", 
        "a_team_gf"
    )

    # Prepare CSV data
    csv_data = [["match_number", "home", "away", "winner"]]
    for game in games:
        if game["played_time"]:
            if game["h_team_gf"] > game["a_team_gf"]:
                winner = game["h_team_num__club_full_name"]
            elif game["h_team_gf"] < game["a_team_gf"]:
                winner = game["a_team_num__club_full_name"]
            else:
                winner = "draw"
        else:
            winner = "no result"
        csv_data.append([game["game_num"], game["h_team_num__club_full_name"], game["a_team_num__club_full_name"], winner])

    # Run the simulator
    simulator = PointsTableSimulator(
        tournament_schedule=csv_data,
        points_for_a_win=2,
        points_for_a_loss=0,
    )
    standings_table = simulator.current_points_table

    # Update playoff status in Standing objects
    for standing in Standing.objects.filter(season=season):
        if standing.team.club_full_name in playoff_locks:
            standing.playoffs = "x"  # Clinched Playoff Spot
        if standing.team.club_full_name == presidents_trophy_winner:
            standing.playoffs = "p"  # President's Trophy
        standing.save()'''

def get_scoreboard():
    season = get_seasonSetting()
    data = Game.objects.filter(season_num=season).order_by("-played_time")[:20]
    return data

def GamesRequest(request):
    season = get_seasonSetting()
    data = Game.objects.filter(season_num=season).values("game_num", "gamelength", "played_time", "a_team_num__club_abbr", "h_team_num__club_abbr", "a_team_num__team_logo_link", "h_team_num__team_logo_link" "a_team_gf", "h_team_gf").order_by("-played_time")[:15]
    response = JsonResponse(dict(gamelist=list(data)), safe=False)
    return response

def index(request):
    season = get_seasonSetting()
    allgames = SkaterRecord.objects.filter(game_num__season_num=season)
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
        gp = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=randomplayer).count()
        goals = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=randomplayer).aggregate(Sum("goals"))["goals__sum"]
        assists = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=randomplayer).aggregate(Sum("assists"))["assists__sum"]
        plusminus = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=randomplayer).aggregate(Sum("plus_minus"))["plus_minus__sum"]
        pims = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=randomplayer).aggregate(Sum("pims"))["pims__sum"]
        thisseason = 1
    season = Season.objects.get(season_num=get_seasonSetting())
    standings = Standing.objects.filter(season=season).order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
    leaders = Leader.objects.all().values("attribute", "stat", "player__username")
    announcements = Announcement.objects.order_by('-created_at')
    paginator = Paginator(announcements, 1)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {"standings": standings, "leaders": leaders, "thisseason": thisseason, "username": username, "gp": gp, "goals": goals, "assists": assists, "plusminus": plusminus, "pims": pims, "season": season, "announcement": page_obj}
    return render(request, "GHLWebsiteApp/index.html", context)

def standings(request):
    season = Season.objects.get(season_num=get_seasonSetting())
    if not season.season_type == "playoffs":
        standings = Standing.objects.filter(season=season).order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
        rounds = None
    else:
        standings = PlayoffSeries.objects.filter(season=season).order_by('round_num', 'low_seed_num')
        rounds = PlayoffRound.objects.filter(season=season).order_by('round_num')
    return render(request, "GHLWebsiteApp/standings.html", {"standings": standings, "season": season, "rounds": rounds})

def leaders(request):
    season = get_seasonSetting()
    leaders_goals = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numgoals=Sum("goals")).filter(numgoals__gt=0).order_by("-numgoals")[:10]
    leaders_assists = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numassists=Sum("assists")).filter(numassists__gt=0).order_by("-numassists")[:10]
    leaders_points = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numpoints=Sum("points")).filter(numpoints__gt=0).order_by("-numpoints")[:10]
    leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).filter(shootperc__gt=0).order_by("-shootperc")[:10]
    leaders_svp = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:10]
    leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        shutoutcount=Sum(Case(
        When(shutout=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(shutoutcount__gte=1).order_by("-shutoutcount")[:10]
    leaders_wins = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        wincount=Sum(Case(
        When(win=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(wincount__gte=1).order_by("-wincount")[:10]
    leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(gaatotal=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600).order_by("gaatotal")[:10]
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

def skaters(request, season=None):
    if season is None:
        season = get_seasonSetting()
    all_skaters = SkaterRecord.objects.filter(game_num__season_num=season).exclude(position=0).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        skatersgp=Count("game_num"),
        skatersgoals=Sum("goals"),
        skatersassists=Sum("assists"),
        skaterspoints=Sum("points"),
        skatersplusminus=Sum("plus_minus"),
        skatershits=Sum("hits"),
        skaterspims=Sum("pims"),
        skaterssog=Sum("sog"),
        skatersposs=Avg("poss_time"),
        skatersppg=Sum("ppg"),
        skatersshg=Sum("shg"),
    ).order_by("-skaterspoints", "-skatersgoals", "-skatersgp", "skaterspims", "ea_player_num__username")
    season = Season.objects.get(season_num=season)
    seasonlist = Season.objects.exclude(season_type="preseason").order_by("-start_date")
    context = {
        "all_skaters": all_skaters,
        "season": season,
        "seasonlist": seasonlist,
    }
    return render(request, "GHLWebsiteApp/skaters.html", context)

def skatersAdvanced(request, season=None):
    if season is None:
        season = get_seasonSetting()
    all_skaters = SkaterRecord.objects.filter(game_num__season_num=season).exclude(position=0).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        total_fow=Sum("fow"),
        total_fol=Sum("fol"),
    ).annotate(
        sumsog=Sum("sog"),
        sumshotatt=Sum("shot_attempts"),
        sumpassatt=Sum("pass_att"),
        skatersshotperc=Cast(Sum("goals"), models.FloatField())/Cast(Case(
                When(sumsog=0, then=1),
                default=Sum("sog"),
                output_field=models.FloatField()
            ), models.FloatField())*100,
        skatersshoteffperc=Cast(Sum("sog"), models.FloatField())/Cast(Case(
                When(sumshotatt=0, then=1),
                default=Sum("shot_attempts"),
                output_field=models.FloatField()
            ), models.FloatField())*100,
        skaterspassperc=Cast(Sum("pass_comp"), models.FloatField())/Cast(Case(
                When(sumpassatt=0, then=1),
                default=Sum("pass_att"),
                output_field=models.FloatField()
            ), models.FloatField())*100,
        skaterstka=Avg("takeaways"),
        skatersint=Avg("interceptions"),
        skatersgva=Avg("giveaways"),
        skaterspims=Avg("pims"),
        skatersdrawn=Avg("pens_drawn"),
        skatersbs=Avg("blocked_shots"),
        skatersfo=Case(
            When(
                total_fow__isnull=False,
                total_fol__isnull=False,
                then=Cast(F("total_fow") * 100.0 / (F("total_fow") + F("total_fol")), FloatField())
        ),default=0, output_field=FloatField()), # TODO: Find out why players without fow/fol are showing up with blanks
    ).order_by("ea_player_num__username")
    season = Season.objects.get(season_num=season)
    seasonlist = Season.objects.exclude(season_type="preseason").order_by("-start_date")
    context = {
        "all_skaters": all_skaters,
        "season": season,
        "seasonlist": seasonlist,
    }
    return render(request, "GHLWebsiteApp/advanced.html", context)

def goalies(request, season=None):
    if season is None:
        season = get_seasonSetting()
    all_goalies = GoalieRecord.objects.filter(game_num__season_num=season).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
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
    season = Season.objects.get(season_num=season)
    seasonlist = Season.objects.exclude(season_type="preseason").order_by("-start_date")
    context = {
        "all_goalies": all_goalies,
        "season": season,
        "seasonlist": seasonlist,
    }
    return render(request, "GHLWebsiteApp/goalies.html", context)

def team(request, team, season=None):
    season_id = request.GET.get('season')  # Retrieve season ID from query parameters
    if season_id:
        season = get_object_or_404(Season, pk=season_id)  # Use the provided season
    else:
        season = get_seasonSetting()  # Default to the active season
    teamnum = get_object_or_404(Team, pk=team)
    skaterrecords = SkaterRecord.objects.filter(ea_club_num=teamnum.ea_club_num, game_num__season_num=season).exclude(position="0").values("ea_player_num", "ea_player_num__username").annotate(
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
    goalierecords = GoalieRecord.objects.filter(ea_club_num=teamnum.ea_club_num, game_num__season_num=season).values("ea_player_num", "ea_player_num__username").annotate(
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
    awaygames = Game.objects.filter(season_num=season, a_team_num=teamnum)
    homegames = Game.objects.filter(season_num=season, h_team_num=teamnum)
    teamgames = sorted(
        chain (awaygames, homegames),
        key=lambda game: (game.expected_time is None, game.expected_time or game.game_num),
    )
    roster = Player.objects.filter(current_team=teamnum).exclude(banneduser__isnull=False).order_by(Lower("username"))
    seasons = Season.objects.filter(
        models.Q(game__a_team_num=team) | models.Q(game__h_team_num=team)
    ).exclude(
        season_text__icontains="Test"  # Exclude seasons where season_text contains "Test"
    ).distinct()
    context = {"team": teamnum, "skaterrecords": skaterrecords, "goalierecords": goalierecords, "teamgames": teamgames, "roster": roster, "seasons": seasons}  
    return render(request, "GHLWebsiteApp/team.html", context)

def game(request, game):
    season = get_seasonSetting()
    gamenum = get_object_or_404(Game, pk=game)
    a_skater_records = SkaterRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num).exclude(position="0")
    h_skater_records = SkaterRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num).exclude(position="0")
    a_goalie_records = GoalieRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num)
    h_goalie_records = GoalieRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num)
    a_team_standing = Standing.objects.filter(team=gamenum.a_team_num.ea_club_num, season=season)
    h_team_standing = Standing.objects.filter(team=gamenum.h_team_num.ea_club_num, season=season)
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
    }
    return render(request, "GHLWebsiteApp/game.html", context)

def player(request, player):
    seasonSetting = get_seasonSetting()
    playernum = get_object_or_404(Player, pk=player)

    # Group and aggregate skater records by season
    skater_season_totals = SkaterRecord.objects.filter(
        ea_player_num=playernum
    ).exclude(
        game_num__season_num__season_text="Test Season"
    ).exclude(
        position="0"
    ).values(
        "game_num__season_num__season_text"
    ).annotate(
        sk_gp=Count("game_num"),
        sk_g=Sum("goals"),
        sk_a=Sum("assists"),
        sk_p=Sum("points"),
        sk_hits=Sum("hits"),
        sk_plus_minus=Sum("plus_minus"),
        sk_sog=Sum("sog"),
        sk_shot_att=Sum("shot_attempts"),
        sk_ppg=Sum("ppg"),
        sk_shg=Sum("shg"),
        sk_pass_att=Sum("pass_att"),
        sk_pass_comp=Sum("pass_comp"),
        sk_bs=Sum("blocked_shots"),
        sk_tk=Sum("takeaways"),
        sk_int=Sum("interceptions"),
        sk_gva=Sum("giveaways"),
        sk_pens_drawn=Sum("pens_drawn"),
        sk_pims=Sum("pims"),
        sk_pk_clears=Sum("pk_clears"),
        sk_poss_time=Round(Avg("poss_time"),1),
        sk_fow=Sum("fow"),
        sk_fol=Sum("fol"),
    ).order_by("-game_num__season_num")

    # Calculated values for each season
    for season in skater_season_totals:
        season["sk_shot_perc"] = (
            round((season["sk_g"] / season["sk_sog"]) * 100, 1)
            if season["sk_sog"] > 0 else "-"
        )
        season["sk_shot_eff"] = (
            round((season["sk_sog"] / season["sk_shot_att"]) * 100, 1)
            if season["sk_shot_att"] > 0 else "-"
        )
        season["sk_pass_perc"] = (
            round((season["sk_pass_comp"] / season["sk_pass_att"]) * 100, 1)
            if season["sk_pass_att"] > 0 else "-"
        )
        season["sk_fo_perc"] = (
            round((season["sk_fow"] / (season["sk_fow"] + season["sk_fol"])) * 100, 1)
            if (season["sk_fow"] + season["sk_fol"]) > 0 else "-"
        )


    # Group and aggregate goalie records by season
    goalie_season_totals = playernum.goalierecord_set.exclude(
        game_num__season_num__season_text="Test Season"
    ).values(
        "game_num__season_num__season_text"
    ).annotate(
        g_gp=Count("game_num"),
        g_sha=Sum("shots_against"),
        g_sav=Sum("saves"),
        g_br_sh=Sum("breakaway_shots"),
        g_br_sa=Sum("breakaway_saves"),
        g_ps_sh=Sum("ps_shots"),
        g_ps_sa=Sum("ps_saves"),
        g_so=Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        g_wins=Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        g_losses=Sum(Case(
            When(loss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        g_otlosses=Sum(Case(
            When(otloss=True, then=1),
            default=0,
            output_field=models.IntegerField()
        )),
        g_toi=(Sum("game_num__gamelength")/60),
    ).order_by("-game_num__season_num")

    # Calculated values for each season
    for season in goalie_season_totals:
        season["g_ga"] = season["g_sha"] - season["g_sav"] if season["g_sha"] and season["g_sav"] else 0
        season["g_svp"] = (
            round((season["g_sav"] / season["g_sha"]) * 100, 1)
            if season["g_sha"] > 0 else "-"
        )
        season["g_gaa"] = (
            round((season["g_ga"] / (season["g_toi"] / 60)), 2)
            if season["g_toi"] > 0 else "-"
        )
        season["g_br_perc"] = (
            round((season["g_br_sa"] / season["g_br_sh"]) * 100, 1)
            if season["g_br_sh"] > 0 else "-"
        )
        season["g_ps_perc"] = (
            round((season["g_ps_sa"] / season["g_ps_sh"]) * 100, 1)
            if season["g_ps_sh"] > 0 else "-"
        )

    if not playernum.current_team:
        sk_team_num = 0
    else:
        sk_team_num = playernum.current_team.ea_club_num

    skater_games = Game.objects.filter(skaterrecord__ea_player_num=playernum, season_num=seasonSetting)
    goalie_games = Game.objects.filter(goalierecord__ea_player_num=playernum, season_num=seasonSetting)
    if skater_games.exists() or goalie_games.exists():
        all_games = skater_games.union(goalie_games).order_by("-expected_time")
    else:
        all_games = []
    context = {
        "playernum": playernum, 
        "skater_season_totals": skater_season_totals,
        "goalie_season_totals": goalie_season_totals,
        "sk_team_num": sk_team_num,
        "games": all_games,
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def draft(request):
    return render(request, "GHLWebsiteApp/draft.html")

def awards(request, awardnum):
    award = get_object_or_404(AwardTitle, pk=awardnum)
    if award.assign_or_vote == True: # Assigns
        awardhistory = AwardAssign.objects.filter(award_type=awardnum).exclude(season_num__start_date = None).order_by("-season_num__start_date")[1:]
        awardrecent = AwardAssign.objects.filter(award_type=awardnum).exclude(season_num__start_date = None).order_by("-season_num__start_date")[:1]
    else: # Votes
        awardhistory = ( # Wait, we only want the winners for the history. Not every top three. Or do we?
            AwardVote.objects.filter(award_type=awardnum).exclude(season_num__start_date = None)
            .annotate(
                rank=Window(
                    expression=Rank(),
                    partition_by=F("season_num"),
                    order_by=F("votes_num").desc()
                )
            )
            .filter(rank__lte=1)  # Keep only the top one each season
            .order_by("-season_num__start_date")  # Sort by season
        )[1:]
        awardrecent = (
            AwardVote.objects.filter(award_type=awardnum).exclude(season_num__start_date = None)
            .annotate(
                rank=Window(
                    expression=Rank(),
                    partition_by=F("season_num"),
                    order_by=F("votes_num").desc()
                )
            )
            .filter(rank__lte=3)  # Keep only the top 3 each season
            .order_by("-season_num__start_date", "rank")[:3]
        )
    return render(request, "GHLWebsiteApp/awards.html", {
        "awardslist": AwardTitle.objects.all().order_by("award_num"),
        "award": award,
        "awardhistory": awardhistory,
        "awardrecent": awardrecent,
    })

def awardsDef(request):
    return awards(request, "1")

def glossary(request):
    return render(request, "GHLWebsiteApp/glossary.html")

def playerlist(request):
    players = Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username"))
    player_data = []

    for player in players:
        # Combine distinct regular season_nums from both records
        skater_seasons = set(player.skaterrecord_set.filter(game_num__season_num__season_type='regular').exclude(position=0)
                            .values_list('game_num__season_num', flat=True))
        goalie_seasons = set(player.goalierecord_set.filter(game_num__season_num__season_type='regular')
                            .values_list('game_num__season_num', flat=True))
        combined_seasons = skater_seasons.union(goalie_seasons)

        total_games = (
            player.skaterrecord_set.filter(game_num__season_num__season_type='regular').exclude(position=0).values('game_num').distinct().count()
            + player.goalierecord_set.filter(game_num__season_num__season_type='regular').values('game_num').distinct().count()
        )

        player_data.append({
            "player": player,
            "total_seasons": len(combined_seasons),
            "total_games": total_games,
        })
    return render(request, "GHLWebsiteApp/playerlist.html", {"all_players": player_data,})

@login_required
def user_profile(request):
    # TODO: Add user profile functionality here
    pass

def upload_file(request):
    season = get_seasonSetting()
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                df = pd.read_excel(file)
                for _, row in df.iterrows():
                    expected_time = row['Expected Game Time']
                    if isinstance(expected_time, str):
                        # Parse the string into a datetime object
                        expected_time = datetime.strptime(expected_time, '%Y-%m-%d %H:%M:%S')
                    game, created = Game.objects.get_or_create(
                        game_num=row['Game Num'],
                        season_num=Season.objects.get(season_num=season),
                        defaults={
                            "a_team_num": Team.objects.get(ea_club_num=row['Away Team']),
                            "h_team_num": Team.objects.get(ea_club_num=row['Home Team']),
                            "expected_time": expected_time,
                        }
                    )
                    if created:
                        messages.success(request, f'Successfully imported {game.game_num}')
                    else:
                        messages.warning(request, f'{game.game_num} already exists')
                return redirect('upload_file')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
    else:
        form = UploadFileForm()
    return render(request, 'GHLWebsiteApp/upload.html', {'form': form})

def export_team(request, team_id):
    team = get_object_or_404(Team, ea_club_num=team_id)
    games = Game.objects.filter(
        models.Q(a_team_num=team) | models.Q(h_team_num=team), season_num = get_seasonSetting()
    ).exclude(played_time__isnull = False).order_by('expected_time')

    # Create the HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{team.club_abbr}_games.csv"'

    writer = csv.writer(response)
    writer.writerow(['Expected Time', 'H or A', 'Opponent', 'Matchup Code'])

    for game in games:
        if game.h_team_num == team:
            role = 'Home'
            opponent = game.a_team_num.club_abbr
        else:
            role = 'Away'
            opponent = game.h_team_num.club_abbr
        writer.writerow([
            localtime(game.expected_time.astimezone(pytz.timezone('US/Eastern'))).strftime('%m/%d %I:%M'),
            role,
            opponent,
            game.h_team_num.team_code,
        ])

    return response

def export_player_data(request):
    player_data = SkaterRecord.objects.all().values(
        "ea_player_num__username",  # Replace ea_player_num with username
        "ea_club_num__club_full_name",  # Replace ea_club_num with club full name
        "position__positionShort", "build__buildShort", "goals", "assists", "points", "hits", "plus_minus", "pims", "sog", "shot_attempts", "deflections", "ppg", "shg", "pass_att", "pass_comp", "saucer_pass", "blocked_shots", "takeaways", "interceptions", "giveaways", "pens_drawn", "pk_clears", "poss_time", "fow", "fol"  # Include other fields as needed
    )
    goalie_data = GoalieRecord.objects.all().values(
        "ea_player_num__username",  # Replace ea_player_num with username
        "ea_club_num__club_full_name",  # Replace ea_club_num with club full name
        "saves", "shots_against", "win", "loss", "otloss", "shutout", "breakaway_shots", "breakaway_saves", "ps_shots", "ps_saves"  # Include other fields as needed
    )
    player_df = pd.DataFrame(list(player_data))
    goalie_df = pd.DataFrame(list(goalie_data))
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        player_df.to_excel(writer, sheet_name='Player Data', index=False)
        goalie_df.to_excel(writer, sheet_name='Goalie Data', index=False)
    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ghl_data.xlsx"'

    return response

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! You can now log in.")
            return redirect('login')  # redirect to login page
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})