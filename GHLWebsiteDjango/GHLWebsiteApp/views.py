from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from .forms import *
import datetime
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F, Window, FloatField, Q, ExpressionWrapper, Value, OuterRef, Subquery, IntegerField, DecimalField
from django.db.models.functions import Cast, Rank, Round, Lower, Coalesce
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from decimal import *
from itertools import chain
import random
import pandas as pd
from io import BytesIO
import csv
import pytz
import json
import requests
from django.utils import timezone as django_timezone
from django.utils.timezone import localtime
from django.core.paginator import Paginator
from dal import autocomplete
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
# from points_table_simulator import PointsTableSimulator
est = pytz.timezone("America/New_York")

def media_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_authenticated and u.groups.filter(name="Media").exists()
    )(view_func)
    return decorated_view_func

def manager_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_authenticated and u.groups.filter(name="Team Managers").exists()
    )(view_func)
    return decorated_view_func

def get_user_team(user):
    try:
        return Team.objects.get(Q(manager=user) | Q(ass_manager=user))
    except Team.DoesNotExist:
        return None

@manager_required
def add_trade_block_player(request):
    if request.method == 'POST':
        form = TradeBlockForm(request.POST)
        if form.is_valid():
            trade = form.save(commit=False)
            trade.team = get_user_team(request.user)
            trade.save()
            messages.success(request, 'Player added to trade block successfully.')
            return redirect('team_management')
        else:
            messages.error(request, 'Please correct the errors below.')
            return render(request, 'add_trade.html', {'form': form})
    else:
        form = TradeBlockForm()
    return render(request, 'add_trade.html', {'form': form})

@manager_required
def delete_trade_block_player(request, pk):
    trade = get_object_or_404(TradeBlockPlayer, pk=pk)
    if trade.team.manager != request.user:
        return HttpResponseForbidden()
    trade.delete()
    return redirect('team_management')

def get_seasonSetting():
    try:
        seasonSetting = Season.objects.filter(isActive=True).first().season_num
    except AttributeError:
        seasonSetting = 1
    return seasonSetting # Returns an integer

def get_signup_season():
    """
    Season whose Signup records should be used for scheduling.

    - If the active season is regular: use that.
    - If the active season is playoffs: use the most recent regular season
      (by start_date, falling back to season_num).
    """
    active = Season.objects.filter(isActive=True).first()
    if not active:
        return None

    if active.season_type == "regular":
        return active

    qs = Season.objects.filter(season_type="regular")

    # Prefer regular seasons that started on/before the active season
    if active.start_date:
        qs = qs.filter(start_date__lte=active.start_date)

    # Latest regular season by date, then by PK as tiebreaker
    qs = qs.order_by("-start_date", "-season_num")

    return qs.first()

@csrf_exempt
def discord_webhook(request):
    if request.method == "GET":
        code = request.GET.get("code")
        state = request.GET.get("state")
        if not code:
            return JsonResponse({"error": "No code received"}, status=400)
        # If you want, you can exchange `code` for a token here using Discord’s OAuth2 API
        return JsonResponse({"message": "✅ Bot authorized successfully!", "code": code})
    return JsonResponse({"error": "Invalid request method"}, status=405)

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
        leaders_goals = SkaterRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(numgoals=Sum("goals")).order_by("-numgoals").first()
        leaders_assists = SkaterRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(numassists=Sum("assists")).order_by("-numassists").first()
        leaders_points = SkaterRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(numpoints=Sum("points")).order_by("-numpoints").first()
        leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).order_by("-shootperc").first()
        leaders_svp = GoalieRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum").first()
        leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(
            shutoutcount=Sum(Case(
            When(shutout=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(shutoutcount__gte=1).order_by("-shutoutcount").first()
        leaders_wins = GoalieRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(
            wincount=Sum(Case(
            When(win=True, then=1),
            default=0,
            output_field=models.IntegerField()
        ))).filter(wincount__gte=1).order_by("-wincount").first()
        leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num").annotate(
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
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=season), defaults={"wins":0, "losses":0, "otlosses":0, "points":0, "goalsfor":0, "goalsagainst":0, "gp":0, "winperc":Decimal(0), "ppperc":Decimal(0), "pkperc":Decimal(0), "lastten":"0-0-0"})
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
            standing, created = Standing.objects.update_or_create(team=team, season=Season.objects.get(season_num=season), defaults={'wins': wins, 'losses': losses, 'otlosses': otlosses, 'points': points, 'goalsfor': goalsfor, 'goalsagainst': goalsagainst, "gp": gp, "winperc": winperc, "ppperc": ppperc, "pkperc": pkperc, "lastten": lastten, "streak": streak})

def get_scoreboard():
    season = get_seasonSetting()
    data = Game.objects.filter(season_num=season).order_by("-played_time", "expected_time")[:20]
    return data

def get_default_week_start():
    eastern = pytz.timezone("America/New_York")
    now_est = django_timezone.now().astimezone(eastern)
    today = now_est.date()

    if today.weekday() == 6:
        # It's Sunday
        if now_est.hour < 20:
            week_start = today
        else:
            week_start = today + datetime.timedelta(days=7)
    else:
        # Not Sunday
        days_until_sunday = 6 - today.weekday()
        week_start = today + datetime.timedelta(days=days_until_sunday)

    return week_start

def aggregate_skater_stats(player, season_filter=None, exclude_test=True):
    """
    Aggregate basic skater stats for a player.
    If season_filter is None -> career (optionally excluding 'Test Season').
    Returns a dict with keys matching STAT_FIELDS below, or {} if no games.
    """
    qs = SkaterRecord.objects.filter(ea_player_num=player).exclude(position=0)

    if exclude_test:
        qs = qs.exclude(game_num__season_num__season_text="Test Season")

    if season_filter is not None:
        qs = qs.filter(game_num__season_num=season_filter)

    agg = qs.aggregate(
        gp=Count("game_num", distinct=True),
        g=Coalesce(Sum("goals"), 0),
        a=Coalesce(Sum("assists"), 0),
        p=Coalesce(Sum("points"), 0),
        plus_minus=Coalesce(Sum("plus_minus"), 0),
        pims=Coalesce(Sum("pims"), 0),
        sog=Coalesce(Sum("sog"), 0),
        hits=Coalesce(Sum("hits"), 0),
        shot_att=Coalesce(Sum("shot_attempts"), 0),
        deflections=Coalesce(Sum("deflections"), 0),
        pass_att=Coalesce(Sum("pass_att"), 0),
        pass_comp=Coalesce(Sum("pass_comp"), 0),
    )

    if agg["gp"] == 0:
        return {}

    # Derived stats
    gp = float(agg["gp"])
    g = float(agg["g"])
    a = float(agg["a"])
    p = float(agg["p"])
    plus_minus = float(agg["plus_minus"])
    pims = float(agg["pims"])
    sog = float(agg["sog"])
    hits = float(agg["hits"])
    shot_att = float(agg["shot_att"])
    defl = float(agg["deflections"])
    pass_att = float(agg["pass_att"])
    pass_comp = float(agg["pass_comp"])

    def per_game(val):
        return round(val / gp, 2) if gp > 0 else None

    if sog > 0:
        shot_perc = round((g / sog) * 100.0, 1)
    else:
        shot_perc = None

    if (shot_att + defl) > 0:
        shot_eff = round((sog / (shot_att + defl)) * 100.0, 1)
    else:
        shot_eff = None

    if pass_att > 0:
        pass_perc = round((pass_comp / pass_att) * 100.0, 1)
    else:
        pass_perc = None

    return {
        "gp": int(gp),
        "g_per": per_game(g),
        "a_per": per_game(a),
        "p_per": per_game(p),
        "plus_minus_per": per_game(plus_minus),
        "pims_per": per_game(pims),
        "hits_per": per_game(hits),
        "sog_per": per_game(sog),
        "shot_perc": shot_perc,
        "shot_eff": shot_eff,
        "pass_perc": pass_perc,
    }

def aggregate_goalie_stats(player, season_filter=None, exclude_test=True):
    qs = GoalieRecord.objects.filter(ea_player_num=player)

    if exclude_test:
        qs = qs.exclude(game_num__season_num__season_text="Test Season")

    if season_filter is not None:
        qs = qs.filter(game_num__season_num=season_filter)

    agg = qs.aggregate(
        gp=Count("game_num", distinct=True),
        shots=Coalesce(Sum("shots_against"), 0),
        saves=Coalesce(Sum("saves"), 0),
        shutouts=Sum(
            Case(
                When(shutout=True, then=1),
                default=0,
                output_field=models.IntegerField(),
            )
        ),
        wins=Sum(
            Case(
                When(win=True, then=1),
                default=0,
                output_field=models.IntegerField(),
            )
        ),
        losses=Sum(
            Case(
                When(loss=True, then=1),
                default=0,
                output_field=models.IntegerField(),
            )
        ),
        otlosses=Sum(
            Case(
                When(otloss=True, then=1),
                default=0,
                output_field=models.IntegerField(),
            )
        ),
        seconds_played=Coalesce(Sum("game_num__gamelength"), 0),
    )

    if agg["gp"] == 0:
        return {}

    gp = float(agg["gp"])
    shots = float(agg["shots"])
    saves = float(agg["saves"])
    goals_against = shots - saves
    seconds_played = float(agg["seconds_played"]) or 0.0

    sh_per_gp = round(shots / gp, 1) if gp > 0 else None

    if shots > 0:
        sv_perc = round((saves / shots) * 100.0, 1)
    else:
        sv_perc = None

    if seconds_played > 0:
        gaa = round(goals_against * 3600.0 / seconds_played, 2)
    else:
        gaa = None

    wins = int(agg["wins"])
    losses = int(agg["losses"])
    otlosses = int(agg["otlosses"])
    shutouts = int(agg["shutouts"])

    record = f"{wins}-{losses}-{otlosses}"

    return {
        "gp_goalie": int(gp),
        "shots_per_gp": sh_per_gp,   # SH/GP
        "sv_perc": sv_perc,          # SV%
        "gaa": gaa,                  # GAA
        "record": record,            # unsorted string
        "so": shutouts,              # shutouts
    }


def compare_players(request):
    season_id = get_seasonSetting()
    season = Season.objects.get(season_num=season_id)

    from .forms import ComparePlayersForm  # or rely on the wildcard import at top

    form = ComparePlayersForm(request.GET or None)

    players = []
    if form.is_valid():
        seen = set()
        for field in ["player1", "player2", "player3", "player4", "player5"]:
            p = form.cleaned_data.get(field)
            if p and p.pk not in seen:
                players.append(p)
                seen.add(p.pk)

    # Nothing selected yet -> mostly blank page with just the form
    if not players:
        context = {
            "form": form,
            "season": season,
            "players": [],
            "season_rows": [],
            "career_rows": [],
            "goalie_season_rows": [],
            "goalie_career_rows": [],
            "season_has_games": False,
        }
        return render(request, "GHLWebsiteApp/compare_players.html", context)

    # Define which stats we compare and whether higher is better
    SKATER_STAT_FIELDS = [
        {"key": "gp", "label": "GP", "higher": True},
        {"key": "g_per", "label": "G/GP", "higher": True},
        {"key": "a_per", "label": "A/GP", "higher": True},
        {"key": "p_per", "label": "Pts/GP", "higher": True},
        {"key": "plus_minus_per", "label": "+/-/GP", "higher": True},
        {"key": "pims_per", "label": "PIM/GP", "higher": False},  # lower better
        {"key": "hits_per", "label": "Hits/GP", "higher": True},
        {"key": "sog_per", "label": "SOG/GP", "higher": True},
        {"key": "shot_perc", "label": "SH%", "higher": True},
        {"key": "shot_eff", "label": "Shot Eff%", "higher": True},
        {"key": "pass_perc", "label": "Pass%", "higher": True},
    ]

    GOALIE_STAT_FIELDS = [
        {"key": "gp_goalie", "label": "GP (G)", "higher": True},
        {"key": "shots_per_gp", "label": "SH/GP", "higher": None},   # no "best"
        {"key": "sv_perc", "label": "SV%", "higher": True},
        {"key": "gaa", "label": "GAA", "higher": False},             # lower better
        {"key": "record", "label": "Record", "higher": None},        # unsorted
        {"key": "so", "label": "SO", "higher": True},
    ]

    players_data = []
    for p in players:
        sk_season = aggregate_skater_stats(p, season_filter=season_id)
        sk_career = aggregate_skater_stats(p, season_filter=None, exclude_test=True)

        g_season = aggregate_goalie_stats(p, season_filter=season_id)
        g_career = aggregate_goalie_stats(p, season_filter=None, exclude_test=True)

        players_data.append(
            {
                "player": p,
                "season_sk": sk_season,
                "career_sk": sk_career,
                "season_g": g_season,
                "career_g": g_career,
            }
        )

    season_has_games = any(d["season_sk"].get("gp", 0) > 0 for d in players_data)

    def build_rows(scope_key, stat_fields):
        rows = []
        for stat in stat_fields:
            key = stat["key"]
            label = stat["label"]
            higher = stat["higher"]

            values = []
            numeric_values = []

            for d in players_data:
                stats_dict = d.get(scope_key, {}) or {}
                v = stats_dict.get(key)
                values.append(v)
                if isinstance(v, (int, float, Decimal)):
                    numeric_values.append(v)

            # Skip if everyone is missing this stat
            if not any(v is not None for v in values):
                continue

            best_indices = set()
            if numeric_values and higher is not None:
                best_val = max(numeric_values) if higher else min(numeric_values)
                for idx, v in enumerate(values):
                    if v == best_val:
                        best_indices.add(idx)

            row = {"label": label, "key": key, "values": []}
            for idx, v in enumerate(values):
                row["values"].append(
                    {
                        "value": v,
                        "is_best": idx in best_indices and v is not None,
                    }
                )
            rows.append(row)
        return rows

    season_rows = build_rows("season_sk", SKATER_STAT_FIELDS)
    career_rows = build_rows("career_sk", SKATER_STAT_FIELDS)
    goalie_season_rows = build_rows("season_g", GOALIE_STAT_FIELDS)
    goalie_career_rows = build_rows("career_g", GOALIE_STAT_FIELDS)

    context = {
        "form": form,
        "season": season,
        "players": players,
        "season_rows": season_rows,
        "career_rows": career_rows,
        "goalie_season_rows": goalie_season_rows,
        "goalie_career_rows": goalie_career_rows,
        "season_has_games": season_has_games,
    }
    return render(request, "GHLWebsiteApp/compare_players.html", context)

def GamesRequest(request):
    season = get_seasonSetting()
    data = Game.objects.filter(season_num=season).values("game_num", "gamelength", "played_time", "a_team_num__club_abbr", "h_team_num__club_abbr", "a_team_num__team_logo_link", "h_team_num__team_logo_link" "a_team_gf", "h_team_gf").order_by("-played_time")[:15]
    response = JsonResponse(dict(gamelist=list(data)), safe=False)
    return response

def index(request):
    season = get_seasonSetting()
    allgames = SkaterRecord.objects.filter(game_num__season_num=season).exclude(ea_player_num__banneduser__isnull=False)
    if not allgames:
        if not SkaterRecord.objects.all():
            randomplayer = gp = goals = assists = plusminus = pims = "(No GP yet)"
            thisseason = 0
        else:
            randomplayer = random.choice(Player.objects.all().exclude(banneduser__isnull=False))
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
    activeteams = Team.objects.filter(isActive=True)
    context = {"standings": standings, "leaders": leaders, "thisseason": thisseason, "username": username, "gp": gp, "goals": goals, "assists": assists, "plusminus": plusminus, "pims": pims, "season": season, "announcement": page_obj, "activeteams": activeteams}
    return render(request, "GHLWebsiteApp/index.html", context)

def standings(request):
    season = Season.objects.get(season_num=get_seasonSetting())
    if season.season_type != "playoffs":
        standings = Standing.objects.filter(season=season)\
            .order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
        rounds = None
        brackets_payload = None
    else:
    # --- Playoffs path: build brackets-viewer payload with zero-based ids ---

        # All series in order by round then low seed
        series_qs = (
            PlayoffSeries.objects
            .filter(season=season)
            .select_related('low_seed', 'high_seed', 'round_num')
            .order_by('round_num__round_num', 'low_seed_num')
        )

        # participants: map Team.ea_club_num -> 0-based participant id
        team_to_pid = {}
        participants = []
        next_pid = 0

        def pid(team: Team | None):
            nonlocal next_pid
            if team is None:
                return None
            key = team.ea_club_num
            if key not in team_to_pid:
                team_to_pid[key] = next_pid
                participants.append({
                    "id": next_pid,                 # <-- 0-based participant id
                    "tournament_id": 0,             # arbitrary (viewer ignores it)
                    "name": team.club_abbr,
                    "icon": team.team_logo_link or None,
                })
                next_pid += 1
            return team_to_pid[key]

        # Exactly one stage and one group, both zero-based ids
        groups = [{
            "id": 0,                                # <-- 0-based group id
            "stage_id": 0,
            "number": 1,                            # viewer display number (1-based)
        }]

        # Build rounds structure and matches
        rounds = []
        matches = []
        matchGames = []  # optional (we're not using per-game entries for a series)

        # Grab round metadata; round.number (display) must be contiguous 1..N
        ordered_rounds = (
            PlayoffRound.objects
            .filter(season=season)
            .order_by('round_num')
            .values('round_num', 'round_name')
        )
        roundnum_to_meta = {r['round_num']: r for r in ordered_rounds}

        # Group series by logical round number from DB
        by_round: dict[int, list[PlayoffSeries]] = defaultdict(list)
        for s in series_qs:
            by_round[s.round_num.round_num].append(s)

        # Build seeding from the first (earliest) round
        min_round = min(by_round.keys()) if by_round else None
        seed_entries = []  # list of (team, seed_num)

        if min_round is not None:
            for s in by_round[min_round]:
                # Note: In your help text, high_seed_num: 8 = highest seed, 7 = next...
                if s.high_seed:
                    seed_entries.append((s.high_seed, s.high_seed_num or 0))
                if s.low_seed:
                    seed_entries.append((s.low_seed, s.low_seed_num or 0))

            # If a team appears twice (shouldn't in a clean bracket), keep the better (higher) seed number.
            best_seed_for_team = {}
            for team, seed in seed_entries:
                if team is None:
                    continue
                if team.ea_club_num not in best_seed_for_team:
                    best_seed_for_team[team.ea_club_num] = seed
                else:
                    # Keep the higher seed number since your schema says higher = better
                    best_seed_for_team[team.ea_club_num] = max(best_seed_for_team[team.ea_club_num], seed)

            # Order by seed DESC (8,7,6,...1)
            ordered_team_ids = sorted(best_seed_for_team.keys(), key=lambda k: best_seed_for_team[k], reverse=False)

            # Build the seeding array as NAMES (Brackets Manager typical format)
            seeding_names = []
            for team_id in ordered_team_ids:
                # find team object back from the series lists (fast path: use one of the series)
                # since we still have series_qs, build a small cache
                # or just reconstruct from a Team queryset if you prefer
                # here we’ll scan once into a dict for O(1) lookup:
                pass

        # Build a quick lookup of team_id -> Team object (from the series we already have)
        team_obj_by_id = {}
        for series in series_qs:
            if series.high_seed:
                team_obj_by_id[series.high_seed.ea_club_num] = series.high_seed
            if series.low_seed:
                team_obj_by_id[series.low_seed.ea_club_num] = series.low_seed

        seeding_names = []
        if min_round is not None:
            for team_id in ordered_team_ids:
                team_obj = team_obj_by_id.get(team_id)
                if team_obj:
                    seeding_names.append(team_obj.club_full_name)

        stages = [{
            "id": 0,                                # <-- 0-based stage id
            "name": f"{season.season_text}",
            "type": "single_elimination",
            "number": 1,                            # viewer display number (1-based)
            "settings": {
                "seedOrdering": ['natural', 'reverse', 'natural'],
                "grandFinal": "none",
            },
            "seeding": seeding_names,
        }]
        # Build fast index: for each round, which series involve a given team?
        index_by_round_team = defaultdict(lambda: defaultdict(list))
        for rnd, lst in by_round.items():
            for s in lst:
                index_by_round_team[rnd][s.high_seed_id].append(s)
                index_by_round_team[rnd][s.low_seed_id].append(s)

        min_round = min(by_round.keys()) if by_round else 0
        max_round = max(by_round.keys()) if by_round else 0

        # 0-based ids for rounds & matches
        next_round_id = 0
        next_match_id = 0

        # Iterate rounds in logical order
        for display_idx, logical_round_num in enumerate(sorted(by_round.keys()), start=1):
            round_series = by_round[logical_round_num]

            # Create the round object
            rounds.append({
                "id": next_round_id,                # <-- 0-based round id
                "group_id": 0,
                "stage_id": 0,
                "number": display_idx,             # viewer display number (1..N), resets at 1 for first round
                "name": roundnum_to_meta.get(logical_round_num, {}).get("round_name")
                        or f"Round {display_idx}",
            })

            # Per-round match numbering (1..M within this round)
            match_number = 1

            # Create matches for this round
            for s in round_series:
                high_w = getattr(s, "high_seed_wins", 0) or 0
                low_w  = getattr(s, "low_seed_wins", 0) or 0

                # ---- STATUS COMPUTATION ----
                # Completed / Archived check
                if s.series_winner_id:
                    # Completed by default
                    status = 4
                    # Archived if a next-round series including the winner is also completed
                    next_round = logical_round_num + 1
                    if next_round <= max_round:
                        next_series_list = index_by_round_team.get(next_round, {}).get(s.series_winner_id, [])
                        if any(ns.series_winner_id for ns in next_series_list):
                            status = 5
                else:
                    # Readiness vs previous round
                    if logical_round_num == min_round:
                        # First round: both entrants are seeded/ready
                        high_ready = True
                        low_ready = True
                    else:
                        prev_round = logical_round_num - 1
                        prev_high_list = index_by_round_team.get(prev_round, {}).get(s.high_seed_id, [])
                        prev_low_list  = index_by_round_team.get(prev_round, {}).get(s.low_seed_id, [])
                        high_ready = any(ps.series_winner_id == s.high_seed_id for ps in prev_high_list)
                        low_ready  = any(ps.series_winner_id == s.low_seed_id  for ps in prev_low_list)

                    if high_ready and low_ready:
                        # Running if games have started (wins recorded) but no winner yet
                        status = 3 if (high_w + low_w) > 0 else 2
                    elif high_ready or low_ready:
                        status = 1
                    else:
                        status = 0

                if s.series_winner is None:
                    high_res = None
                    low_res  = None
                else:
                    high_res = "win" if s.series_winner_id == s.high_seed_id else "loss"
                    low_res  = "win" if s.series_winner_id == s.low_seed_id else "loss"

                matches.append({
                    "id": next_match_id,            # <-- 0-based match id (unique globally)
                    "stage_id": 0,
                    "group_id": 0,
                    "round_id": next_round_id,      # link to 0-based round id above
                    "number": match_number,         # per-round order (1..), resets every round
                    "status": status,
                    "opponent1": {
                        "id": pid(s.high_seed),
                        "score": high_w,
                        "result": high_res,
                    } if pid(s.high_seed) is not None else None,
                    "opponent2": {
                        "id": pid(s.low_seed),
                        "score": low_w,
                        "result": low_res,
                    } if pid(s.low_seed) is not None else None,
                })
                next_match_id += 1
                match_number += 1

            next_round_id += 1

        brackets_payload = {
            "stages": stages,
            "groups": groups,
            "rounds": rounds,
            "matches": matches,
            "matchGames": matchGames,
            "participants": participants,
        }
        standings = None  # not used in playoffs template now
    return render(request, "GHLWebsiteApp/standings.html",
                  {"standings": standings, "season": season, "brackets_json": json.dumps(brackets_payload)})

def leaders(request):
    season = get_seasonSetting()
    leaders_goals = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numgoals=Sum("goals")).filter(numgoals__gt=0).order_by("-numgoals")[:10]
    leaders_assists = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numassists=Sum("assists")).filter(numassists__gt=0).order_by("-numassists")[:10]
    leaders_points = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(numpoints=Sum("points")).filter(numpoints__gt=0).order_by("-numpoints")[:10]
    leaders_shooting = SkaterRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).filter(shootperc__gt=0).order_by("-shootperc")[:10]
    leaders_svp = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:10]
    leaders_shutouts = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        shutoutcount=Sum(Case(
        When(shutout=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(shutoutcount__gte=1).order_by("-shutoutcount")[:10]
    leaders_wins = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        wincount=Sum(Case(
        When(win=True, then=1),
        default=0,
        output_field=models.IntegerField()
    ))).filter(wincount__gte=1).order_by("-wincount")[:10]
    leaders_gaa = GoalieRecord.objects.filter(game_num__season_num=season).exclude(game_num__played_time=None).exclude(ea_player_num__banneduser__isnull=False).values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(gaatotal=((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600).order_by("gaatotal")[:10]
    missing_shutouts = max(10 - len(leaders_shutouts), 0)
    missing_wins = max(10 - len(leaders_wins), 0)
    context = {
        "leaders_goals": leaders_goals,
        "leaders_assists": leaders_assists,
        "leaders_points": leaders_points,
        "leaders_shooting": leaders_shooting,
        "leaders_svp": leaders_svp,
        "leaders_shutouts": leaders_shutouts,
        "leaders_wins": leaders_wins,
        "leaders_gaa": leaders_gaa,
        "missing_shutouts": missing_shutouts,
        "missing_wins": missing_wins,
    }
    return render(request, "GHLWebsiteApp/leaders.html", context)

def skaters(request, season=None):
    pos_filter = request.GET.get("pos")  # "F", "D", or None
    if season is None:
        season = get_seasonSetting()
    skater_qs = SkaterRecord.objects.filter(
        game_num__season_num=season
    ).exclude(position=0)
    if pos_filter == "F":
        skater_qs = skater_qs.filter(position__positionShort__in=["LW", "C", "RW"])
    elif pos_filter == "D":
        skater_qs = skater_qs.filter(position__positionShort__in=["LD", "RD"])
    all_skaters = skater_qs.values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
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
        "pos_filter": pos_filter,
    }
    return render(request, "GHLWebsiteApp/skaters.html", context)

def skatersAdvanced(request, season=None):
    pos_filter = request.GET.get("pos")  # "F", "D", or None
    if season is None:
        season = get_seasonSetting()
    skater_qs = SkaterRecord.objects.filter(game_num__season_num=season).exclude(position=0)
    if pos_filter == "F":
        skater_qs = skater_qs.filter(position__positionShort__in=["LW", "C", "RW"])
    elif pos_filter == "D":
        skater_qs = skater_qs.filter(position__positionShort__in=["LD", "RD"])
    all_skaters = skater_qs.values("ea_player_num", "ea_player_num__username", "ea_player_num__current_team__club_abbr").annotate(
        total_fow=Coalesce(Sum("fow"), 0),
        total_fol=Coalesce(Sum("fol"), 0),
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
                default=(Sum("shot_attempts")+Sum("deflections")),
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
        skatersfo = Case(
            When(
                Q(total_fow__gt=0) | Q(total_fol__gt=0),
                then=Cast(F("total_fow") * 100.0 / (F("total_fow") + F("total_fol")), FloatField())
            ),
            default=0,
            output_field=FloatField()
        )
    ).order_by("ea_player_num__username")
    season = Season.objects.get(season_num=season)
    seasonlist = Season.objects.exclude(season_type="preseason").order_by("-start_date")
    context = {
        "all_skaters": all_skaters,
        "season": season,
        "seasonlist": seasonlist,
        "pos_filter": pos_filter,
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
        skatersshoteffperc=Cast(Sum("sog"), models.FloatField())/(Cast(Sum("shot_attempts"), models.FloatField()) + Cast(Sum("deflections"), models.FloatField()))*100,
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
    latest_salary = Subquery(
    Salary.objects
        .filter(player=OuterRef('pk'))
        .order_by('-season__start_date')
        .values('amount')[:1]
    )

    roster = roster.annotate(
        latest_salary=Coalesce(
            Cast(latest_salary, output_field=DecimalField(max_digits=10, decimal_places=0)),
            0,
            output_field=DecimalField(max_digits=10, decimal_places=0)
        )
    )
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
    a_team_standing = Standing.objects.filter(team=gamenum.a_team_num.ea_club_num, season=season).first()
    h_team_standing = Standing.objects.filter(team=gamenum.h_team_num.ea_club_num, season=season).first()
    a_team_record = TeamRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.a_team_num.ea_club_num).first()
    h_team_record = TeamRecord.objects.filter(game_num=gamenum.game_num, ea_club_num=gamenum.h_team_num.ea_club_num).first()
    comparison_stats = {}
    if a_team_record and h_team_record:
        def calculate_percentage(home_value, away_value):
            total = home_value + away_value
            if total == 0:
                return 50, 50
            home_percentage = round((home_value / total) * 100, 1)
            away_percentage = round((away_value / total) * 100, 1)
            return home_percentage, away_percentage

        # Calculate percentages for each stat
        comparison_stats['home_sogperc'], comparison_stats['away_sogperc'] = calculate_percentage(
            h_team_record.sog_team, a_team_record.sog_team
        )
        comparison_stats['home_hitsperc'], comparison_stats['away_hitsperc'] = calculate_percentage(
            h_team_record.hits_team, a_team_record.hits_team
        )
        comparison_stats['home_toaperc'], comparison_stats['away_toaperc'] = calculate_percentage(
            h_team_record.toa_team, a_team_record.toa_team
        )
        comparison_stats['home_fowperc'], comparison_stats['away_fowperc'] = calculate_percentage(
            h_team_record.fow_team, a_team_record.fow_team
        )
        comparison_stats['home_pimsperc'], comparison_stats['away_pimsperc'] = calculate_percentage(
            h_team_record.pims_team, a_team_record.pims_team
        )

        # Calculate passing percentage
        h_pass_comp = h_team_record.pass_comp_team or 0
        h_pass_att = h_team_record.pass_att_team or 1  # Avoid division by zero
        a_pass_comp = a_team_record.pass_comp_team or 0
        a_pass_att = a_team_record.pass_att_team or 1  # Avoid division by zero
        comparison_stats['home_passperc'], comparison_stats['away_passperc'] = calculate_percentage(
            h_pass_comp / h_pass_att, a_pass_comp / a_pass_att
        )

        # Calculate powerplay percentage
        h_ppg = h_team_record.ppg_team or 0
        h_ppo = h_team_record.ppo_team or 1  # Avoid division by zero
        a_ppg = a_team_record.ppg_team or 0
        a_ppo = a_team_record.ppo_team or 1  # Avoid division by zero
        comparison_stats['home_ppperc'], comparison_stats['away_ppperc'] = calculate_percentage(
            h_ppg / h_ppo, a_ppg / a_ppo
        )

    # Format TOA
    a_team_toa_formatted = h_team_toa_formatted = "0:00"
    if a_team_record:
        a_team_min = a_team_record.toa_team // 60
        a_team_sec = a_team_record.toa_team % 60
        a_team_toa_formatted = f"{a_team_min}:{a_team_sec:02d}"
    if h_team_record:
        h_team_min = h_team_record.toa_team // 60
        h_team_sec = h_team_record.toa_team % 60
        h_team_toa_formatted = f"{h_team_min}:{h_team_sec:02d}"
    gamelength_min = gamenum.gamelength // 60
    gamelength_sec = gamenum.gamelength % 60
    gamelength_formatted = f"{gamelength_min}:{gamelength_sec:02d}"

    skater_ratings = (
        GameSkaterRating.objects
        .filter(skater_record__game_num=game)
        .select_related("skater_record__ea_player_num")
        .annotate(
            username=F("skater_record__ea_player_num__username"),
            goals=F("skater_record__goals"),
            assists=F("skater_record__assists"),
            hits=F("skater_record__hits"),
            blocked_shots=F("skater_record__blocked_shots"),
        )
        .values("username", "overall_rating", "goals", "assists", "hits", "blocked_shots")
    )
    goalie_ratings = (
        GameGoalieRating.objects
        .filter(goalie_record__game_num=game)
        .select_related("goalie_record__ea_player_num")
        .annotate(
            username=F("goalie_record__ea_player_num__username"),
            saves=F("goalie_record__saves"),
            shots_against=F("goalie_record__shots_against"),
            sv_perc=F("goalie_record__save_pct"),
            gaa=F("goalie_record__gaa"),
        )
        .values("username", "overall_rating", "saves", "sv_perc", "gaa")
    )
    all_ratings = list(skater_ratings) + list(goalie_ratings)
    all_ratings.sort(key=lambda r: float(r["overall_rating"]), reverse=True)
    three_stars = all_ratings[:3]
    positions_order = ["C", "LW", "RW", "LD", "RD", "G"]

    def get_lineup(team_obj):
        schedules = (
            Scheduling.objects
            .filter(game=gamenum, team=team_obj)
            .select_related("player", "position")
        )

        pos_map = {}
        for s in schedules:
            if s.player and s.position:
                pos_map[s.position.positionShort] = s.player

        lines = []
        has_any = False
        for pos in positions_order:
            player = pos_map.get(pos)
            if player:
                has_any = True
            lines.append(
                {
                    "pos": pos,
                    "player": player,
                }
            )

        return {
            "has_any": has_any,
            "lines": lines,
        }

    away_lineup = get_lineup(gamenum.a_team_num)
    home_lineup = get_lineup(gamenum.h_team_num)
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
        "comparison_stats": comparison_stats,
        "gamelength": gamelength_formatted,
        "three_stars": three_stars,
        "away_lineup": away_lineup,
        "home_lineup": home_lineup,
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
        sk_fow=Coalesce(Sum("fow"), 0),
        sk_fol=Coalesce(Sum("fol"), 0),
        sk_deflections=Coalesce(Sum("deflections"), 0),
    ).order_by("-game_num__season_num")

    # Calculated values for each season
    for season in skater_season_totals:
        season["sk_shot_perc"] = (
            round((season["sk_g"] / season["sk_sog"]) * 100, 1)
            if season["sk_sog"] > 0 else "-"
        )
        season["sk_shot_eff"] = (
            round((season["sk_sog"]/ (season["sk_shot_att"] + season["sk_deflections"]) ) * 100, 1)
            if season["sk_shot_att"] > 0 else "-"
        )
        season["sk_pass_perc"] = (
            round((season["sk_pass_comp"] / season["sk_pass_att"]) * 100, 1)
            if season["sk_pass_att"] > 0 else "-"
        )
        fow = season["sk_fow"]
        fol = season["sk_fol"]
        total = fow + fol
        if (total > 0):
            season["sk_fo_perc"] = round((fow / total) * 100, 1)
        else:
            season["sk_fo_perc"] = "-"

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
    game_data = []
    for game in all_games:
        skater_record = SkaterRecord.objects.filter(game_num=game, ea_player_num=playernum).first()
        if not skater_record.position.positionShort == "G":
            rating = GameSkaterRating.objects.filter(skater_record=skater_record).first()
        else:
            goalie_record = GoalieRecord.objects.filter(game_num=game, ea_player_num=playernum).first()
            rating = GameGoalieRating.objects.filter(goalie_record=goalie_record).first()
        game_data.append({
            "game": game,
            "position": skater_record.position.positionShort if skater_record and skater_record.position else "G",
            "rating": rating.overall_rating if rating else "-",
        })
    
    position_mapping = {
        0: 'G',   # Goalie
        5: 'C',   # Center
        4: 'LW',  # Left Wing
        3: 'RW',  # Right Wing
        2: 'LD',  # Left Defense
        1: 'RD',  # Right Defense
    }
    skaterratings = SkaterRating.objects.filter(
        player=playernum,
        season=seasonSetting)
    goalieratings = GoalieRating.objects.filter(
        player=playernum,
        season=seasonSetting
    )
    position_counts = SkaterRecord.objects.filter(
        ea_player_num=playernum,
        game_num__season_num=seasonSetting,
        game_num__played_time__isnull=False,
    ).values("position").annotate(gp=Count("game_num")).order_by("position")
    position_games = {
        position_mapping.get(entry["position"], "Unknown"): entry["gp"]
        for entry in position_counts
    }
    currentseason = Season.objects.get(season_num=get_seasonSetting()).season_text

    # 1) Directly-assigned awards
    assigned_qs = (
        AwardAssign.objects
        .filter(players=playernum)
        .select_related("award_type")
        .annotate(award_name=F("award_type__award_Name"))
        .values("award_name")
    )

    # 2) Vote winners = rows where votes_num == MAX(votes_num) per (award_type, season)
    top_votes_sq = (
        AwardVote.objects
        .filter(season_num=OuterRef("season_num"), award_type=OuterRef("award_type"))
        .order_by("-votes_num")
        .values("votes_num")[:1]
    )

    winners_qs = (
        AwardVote.objects
        .annotate(top_votes=Subquery(top_votes_sq))
        .filter(votes_num=F("top_votes"), ea_player_num=player)
        .select_related("award_type")
        .annotate(award_name=F("award_type__award_Name"))
        .values("award_name")
    )

    # Combine, de-duplicate (in case your admin both assigned & voted the same award-season), and sort
    combined = list(chain(assigned_qs, winners_qs))

    # Aggregate counts manually since combined is a list (not queryset)
    award_counts = {}
    for row in combined:
        name = row["award_name"]
        award_counts[name] = award_counts.get(name, 0) + 1

    # 4️⃣ Convert to list for template rendering
    award_totals = [{"award_name": k, "count": v} for k, v in award_counts.items()]
    award_totals.sort(key=lambda a: (-a["count"], a["award_name"]))  # sort by most wins first

    context = {
        "playernum": playernum, 
        "skater_season_totals": skater_season_totals,
        "goalie_season_totals": goalie_season_totals,
        "sk_team_num": sk_team_num,
        "games": game_data,
        "position_games": position_games,
        "currentseason": currentseason,
        "skaterratings": skaterratings,
        "goalieratings": goalieratings,
        "award_totals": award_totals,
        }
    return render(request, "GHLWebsiteApp/player.html", context)

def playerlog(request, player):
    playernum = get_object_or_404(Player, pk=player)
    skater_games = Game.objects.filter(skaterrecord__ea_player_num=playernum).exclude(season_num__season_text__in="Test")
    goalie_games = Game.objects.filter(goalierecord__ea_player_num=playernum).exclude(season_num__season_text__in="Test")
    if skater_games.exists() or goalie_games.exists():
        all_games = skater_games.union(goalie_games).order_by("-expected_time")
    else:
        all_games = []
    game_data = []
    for game in all_games:
        skater_record = SkaterRecord.objects.filter(game_num=game, ea_player_num=playernum).first()
        if not skater_record.position.positionShort == "G":
            rating = GameSkaterRating.objects.filter(skater_record=skater_record).first()
        else:
            goalie_record = GoalieRecord.objects.filter(game_num=game, ea_player_num=playernum).first()
            rating = GameGoalieRating.objects.filter(goalie_record=goalie_record).first()
        game_data.append({
            "game": game,
            "position": skater_record.position.positionShort if skater_record and skater_record.position else "G",
            "rating": rating.overall_rating if rating else "-",
        })
    context = {"playernum": playernum, "games": game_data}
    return render(request, "GHLWebsiteApp/playerlog.html", context)

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
        latest_salary = (
            Salary.objects
            .filter(player=player)
            .order_by('-season__start_date')
            .values_list('amount', flat=True)
            .first()
        )

        total_games = (
            player.skaterrecord_set.filter(game_num__season_num__season_type='regular').exclude(position=0).values('game_num').distinct().count()
            + player.goalierecord_set.filter(game_num__season_num__season_type='regular').values('game_num').distinct().count()
        )

        player_data.append({
            "player": player,
            "total_seasons": len(combined_seasons),
            "total_games": total_games,
            "number": player.jersey_num if player.jersey_num else "00",
            "salary": latest_salary if latest_salary is not None else "—",
        })
    return render(request, "GHLWebsiteApp/playerlist.html", {"all_players": player_data,})

@login_required
def user_profile(request):
    user = request.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, user=user, instance=user)
        if form.is_valid():
            # Save User (updates player_link)
            user = form.save()

            # Save Player details if player_link exists
            player = user.player_link
            if player:
                player.jersey_num = form.cleaned_data.get('jersey_num')
                player.primarypos = form.cleaned_data.get('primarypos')
                player.save()

                # many-to-many must be set via set()
                player.secondarypos.set(form.cleaned_data.get('secondarypos'))

            messages.success(request, "Your profile has been updated.")
            return redirect('user_profile')
    else:
        form = UserProfileForm(user=user, instance=user)

    return render(request, 'GHLWebsiteApp/user_profile.html', {
        'form': form
    })

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
                        expected_time = datetime.datetime.strptime(expected_time, '%Y-%m-%d %H:%M:%S')
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
        "game_num", # Game Number
        "position__positionShort", "build__buildShort", "goals", "assists", "points", "hits", "plus_minus", "pims", "sog", "shot_attempts", "deflections", "ppg", "shg", "pass_att", "pass_comp", "saucer_pass", "blocked_shots", "takeaways", "interceptions", "giveaways", "pens_drawn", "pk_clears", "poss_time", "fow", "fol"  # Include other fields as needed
    )
    goalie_data = GoalieRecord.objects.all().values(
        "ea_player_num__username",  # Replace ea_player_num with username
        "ea_club_num__club_full_name",  # Replace ea_club_num with club full name
        "game_num", # Game Number
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

def export_war(request):
    war_data = SkaterRating.objects.all().exclude(position=0).values(
        "player__username",  # Replace player with username
        "position__positionShort", 
        "season__season_text",
        "games_played", "off_rat", "def_rat", "team_rat", "ovr_rat", "off_pct", "def_pct", "team_pct", "ovr_pct",
    )
    war_df = pd.DataFrame(list(war_data))
    war_df.columns = [
        "Username", "Position", "Season", "Games Played", 
        "Offensive Rating", "Defensive Rating", "Team Rating", "Overall Rating", 
        "Offensive Percentile", "Defensive Percentile", "Team Percentile", "Overall Percentile"
    ]
    for col in ["Games Played", "Overall Percentile"]:
        war_df[col] = pd.to_numeric(war_df[col], errors="coerce")
    ranked = war_df.sort_values(
        ["Username", "Season", "Games Played", "Overall Percentile"],
        ascending=[True, True, False, False]
    )
    def pick_top2(g):
        # Pick the top two (or one if only one) ratings for each player in a season, and combine to a weighted overall.
        primary_pos = g.iloc[0]["Position"]
        primary_rat = g.iloc[0]["Overall Percentile"]
        if len(g) > 1:
            secondary_pos = g.iloc[1]["Position"]
            secondary_rat = g.iloc[1]["Overall Percentile"]
            weighted_rat = (
                primary_rat * g.iloc[0]["Games Played"] +
                secondary_rat * g.iloc[1]["Games Played"]
                ) / (g.iloc[0]["Games Played"] + g.iloc[1]["Games Played"])
        else:
            secondary_pos = ""
            secondary_rat = pd.NA
            weighted_rat = primary_rat
        return pd.Series({
            "Primary Position": primary_pos,
            "Primary Rating": (round(primary_rat, 2) if primary_pos else ""),
            "Secondary Position": secondary_pos,
            "Secondary Rating": (round(secondary_rat, 2) if secondary_pos else ""),
            "Weighted Rating": round(weighted_rat, 2)
        })
    primsec = (
        ranked.groupby(["Username", "Season"], as_index=False)
              .apply(pick_top2)
              .reset_index(drop=True)
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        war_df.to_excel(writer, sheet_name='Ratings Data', index=False)
        primsec.to_excel(writer, sheet_name='Primary-Secondary', index=False)
    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ghl_war.xlsx"'
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

def player_details(request, player_id):
    player = get_object_or_404(Player, pk=player_id)
    data = {
        "jersey_num": player.jersey_num,
        "primarypos": player.primarypos.pk if player.primarypos else None,
        "secondarypos": [p.pk for p in player.secondarypos.all()],
    }
    return JsonResponse(data)

def build_weekly_player_line(player, week_start, season):
    """
    Build a one-line summary of this player's weekly stats
    as skater and/or goalie between week_start and week_start+7.
    """
    week_end = week_start + datetime.timedelta(days=7)

    # Skater stats (per game)
    sk_qs = SkaterRecord.objects.filter(
        ea_player_num=player,
        game_num__played_time__gte=week_start,
        game_num__played_time__lt=week_end,
        game_num__season_num=season,
    ).exclude(position=0)

    sk_gp = sk_qs.count()
    sk_line = None
    if sk_gp > 0:
        sk_agg = sk_qs.aggregate(
            g=Coalesce(Sum("goals"), 0),
            a=Coalesce(Sum("assists"), 0),
            pts=Coalesce(Sum("points"), 0),
            sog=Coalesce(Sum("sog"), 0),
            hits=Coalesce(Sum("hits"), 0),
            pim=Coalesce(Sum("pims"), 0),
        )
        def per_game(v):
            return (v or 0) / sk_gp

        sk_line = (
            f"Skater: {sk_gp} GP, "
            f"{per_game(sk_agg['g']):.2f} G/GP, "
            f"{per_game(sk_agg['a']):.2f} A/GP, "
            f"{per_game(sk_agg['pts']):.2f} P/GP, "
            f"{per_game(sk_agg['hits']):.2f} Hits/GP, "
            f"{per_game(sk_agg['sog']):.2f} SOG/GP, "
            f"{per_game(sk_agg['pim']):.2f} PIM/GP"
        )

    # Goalie stats
    g_qs = GoalieRecord.objects.filter(
        ea_player_num=player,
        game_num__played_time__gte=week_start,
        game_num__played_time__lt=week_end,
        game_num__season_num=season,
    )

    g_gp = g_qs.count()
    g_line = None
    if g_gp > 0:
        g_agg = g_qs.aggregate(
            shots=Coalesce(Sum("shots_against"), 0),
            saves=Coalesce(Sum("saves"), 0),
            so=Sum(Case(
                When(shutout=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            wins=Sum(Case(
                When(win=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            losses=Sum(Case(
                When(loss=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            otl=Sum(Case(
                When(otloss=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            toi=Coalesce(Sum("game_num__gamelength"), 0),
        )
        shots = float(g_agg["shots"] or 0)
        saves = float(g_agg["saves"] or 0)
        goals = float((g_agg["shots"]-g_agg["saves"]) or 0)

        sv_pct = (saves / shots * 100.0) if shots > 0 else None
        gaa = ((goals / float(g_agg["toi"])) * 3600) if g_gp > 0 else None
        record = f"{int(g_agg['wins'] or 0)}-{int(g_agg['losses'] or 0)}-{int(g_agg['otl'] or 0)}"

        parts = [f"Goalie: {g_gp} GP"]
        if sv_pct is not None:
            parts.append(f"{sv_pct:.1f}% SV")
        if gaa is not None:
            parts.append(f"{gaa:.2f} GAA")
        parts.append(f"Record {record}")
        parts.append(f"SO: {int(g_agg['so'] or 0)}")
        g_line = ", ".join(parts)

    if sk_line and g_line:
        return sk_line + " | " + g_line
    elif sk_line:
        return sk_line
    elif g_line:
        return g_line
    else:
        return "No stats recorded this week."

def post_three_stars_to_discord(three_stars: WeeklyThreeStars, week_start: datetime.date, season: Season):
    DEBUG = False

    if DEBUG:
        print("Posting weekly three stars to Discord...")
    url = getattr(settings, "DISCORD_SPORTSCENTER_WEBHOOK_URL", "")
    if not url:
        print("No webhook configured; silently skipping")
        return

    week_label = week_start.strftime("%b %d, %Y")
    title = f"**GHL Weekly Three Stars – Week of {week_label} ({season.season_text})**"

    lines = [title, ""]

    stars = [
        ("1st Star", three_stars.first_star),
        ("2nd Star", three_stars.second_star),
        ("3rd Star", three_stars.third_star),
    ]

    for label, player in stars:
        stat_line = build_weekly_player_line(player, week_start, season.season_num)
        lines.append(f"**{label}: {player.username}** — {stat_line}")

    if three_stars.blurb:
        lines.append("")
        lines.append(f"{three_stars.blurb}")
    lines.append("")
    lines.append("@everyone")

    if DEBUG:
        print("Discord message content:")
        for line in lines:
            print(line)
    payload = {"content": "\n".join(lines), "allowed_mentions": {"parse": ["everyone"]},}
               
    try:
        requests.post(url, json=payload, timeout=5)
        if DEBUG:
            print("Posted successfully.")
    except Exception as e:
        print(f"Error posting three stars to Discord: {e}")

@media_required
def weekly_stats_view(request):
    # Build list of weeks (Sundays) for dropdown
    DEBUG = False
    weeks_set = set()
    season_num = get_seasonSetting()
    prev_season = season_num - 1 if season_num > 1 else season_num
    season_ids = [season_num, prev_season]

    if season_num is not None:
        # Fetch all played_times in this season
        dates_qs = (
            SkaterRecord.objects
            .filter(game_num__season_num__in=season_ids)
            .exclude(position=0)
            .values_list('game_num__played_time', flat=True)
        )
        for dt in dates_qs:
            if dt:
                played_date = dt.date()
                # Find previous Sunday
                days_since_sunday = (played_date.weekday() + 1) % 7
                sunday_date = played_date - datetime.timedelta(days=days_since_sunday)
                weeks_set.add(sunday_date)

    weeks = sorted(weeks_set, reverse=True)

    # Handle user's selected week
    if request.method == "POST":
        selected_week_str = request.POST.get("week") or request.GET.get("week")
    else:
        selected_week_str = request.GET.get("week")

    if selected_week_str:
        try:
            selected_week = datetime.datetime.strptime(selected_week_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            selected_week = weeks[0] if weeks else None
    else:
        selected_week = weeks[0] if weeks else None

    if selected_week:
        # Boundaries of selected week (Sunday → Saturday)
        start_date = django_timezone.make_aware(
            datetime.datetime.combine(
                selected_week,
                datetime.time.min
            ),
            datetime.timezone.utc
        )
        end_date = start_date + datetime.timedelta(days=7)

        # Filter Skater Records
        skater_qs = SkaterRecord.objects.filter(
            game_num__played_time__gte=start_date,
            game_num__played_time__lt=end_date,
            game_num__season_num = season_num
        ).exclude(position=0).order_by(Lower('ea_player_num__username'))

        if DEBUG:
            print("start_date =", start_date)
            print("end_date =", end_date)
            for record in skater_qs:
                print(record.game_num.played_time)

        # Filter Goalie Records
        goalie_qs = GoalieRecord.objects.filter(
            game_num__played_time__gte=start_date,
            game_num__played_time__lt=end_date,
            game_num__season_num = season_num
        ).order_by(Lower('ea_player_num__username'))
    else:
        skater_qs = SkaterRecord.objects.none()
        goalie_qs = GoalieRecord.objects.none()

    skater_map = defaultdict(lambda: {
        'total_goals': 0,
        'total_assists': 0,
        'total_points': 0,
        'total_sog': 0,
        'games_played': 0,
        'plus_minus': 0,
        'hits': 0,
        'postime': 0,
        'pass_att': 0,
        'pass_comp': 0,
        'taekaways': 0,
        'interceptions': 0,
        'blocked_shots': 0,
    })

    for record in skater_qs:
        ea_player_num = record.ea_player_num.ea_player_num
        skater_map[ea_player_num]['total_goals'] += record.goals
        skater_map[ea_player_num]['total_assists'] += record.assists
        skater_map[ea_player_num]['total_points'] += record.points
        skater_map[ea_player_num]['total_sog'] += record.sog or 0
        skater_map[ea_player_num]['plus_minus'] += record.plus_minus or 0
        skater_map[ea_player_num]['games_played'] += 1
        skater_map[ea_player_num]['hits'] += record.hits or 0
        skater_map[ea_player_num]['postime'] += record.poss_time or 0
        skater_map[ea_player_num]['pass_att'] += record.pass_att or 0
        skater_map[ea_player_num]['pass_comp'] += record.pass_comp or 0
        skater_map[ea_player_num]['taekaways'] += record.takeaways or 0
        skater_map[ea_player_num]['interceptions'] += record.interceptions or 0
        skater_map[ea_player_num]['blocked_shots'] += record.blocked_shots or 0

    player_map = Player.objects.in_bulk(field_name='ea_player_num')

    skater_stats = []
    for ea_player_num, stats in skater_map.items():
        player = player_map.get(ea_player_num)
        shot_perc = (
            (stats['total_goals'] * 100.0 / stats['total_sog'])
            if stats['total_sog'] > 0 else 0.0
        )
        pass_perc = (
            (stats['pass_comp'] * 100.0 / stats['pass_att'])
            if stats['pass_att'] > 0 else 0.0
        )
        posspergame = (
            (stats['postime'] / stats['games_played'])
        )
        tkpergame = (
            (stats['taekaways'] / stats['games_played'])
        )
        intpergame = (
            (stats['interceptions'] / stats['games_played'])
        )
        bspergame = (
            (stats['blocked_shots'] / stats['games_played'])
        )

        skater_stats.append({
            'week': selected_week,
            'player_name': player.username if player else 'Unknown',
            'ea_player_num': player.ea_player_num,
            'total_goals': stats['total_goals'],
            'total_assists': stats['total_assists'],
            'total_points': stats['total_points'],
            'games_played': stats['games_played'],
            'shot_perc': round(shot_perc, 2),
            'plus_minus': stats['plus_minus'],
            'hits': stats['hits'],
            'pass_perc': round(pass_perc, 2),
            'postime': round(posspergame, 1),
            'tkpergame': round(tkpergame, 1),
            'intpergame': round(intpergame, 1),
            'bspergame': round(bspergame, 1),
        })

    skater_stats.sort(key=lambda x: (
        -x['total_points'],
        -x['total_goals'],
        -x['plus_minus']
    ))
    goalie_map = defaultdict(lambda: {
        'shots_against': 0,
        'saves': 0,
        'shutouts': 0,
        'games_played': 0,
        'seconds_played': 0,
    })

    for record in goalie_qs:
        ea_player_num = record.ea_player_num.ea_player_num
        seconds_played = record.game_num.gamelength or 3600
        goalie_map[ea_player_num]['shots_against'] += record.shots_against or 0
        goalie_map[ea_player_num]['saves'] += record.saves or 0
        goalie_map[ea_player_num]['shutouts'] += record.shutout or 0
        goalie_map[ea_player_num]['games_played'] += 1
        goalie_map[ea_player_num]['seconds_played'] += seconds_played

    goalie_stats = []
    for ea_player_num, stats in goalie_map.items():
        player = player_map.get(ea_player_num)
        svp = (
            (stats['saves'] * 100.0 / stats['shots_against'])
            if stats['shots_against'] > 0 else 0.0
        )
        gaa = (
            (stats['shots_against'] - stats['saves']) / (stats['seconds_played']) * 3600
        )
        goalie_stats.append({
            'week': selected_week,
            'player_name': player.username if player else 'Unknown',
            'ea_player_num': ea_player_num,
            'shots_against': stats['shots_against'],
            'saves': stats['saves'],
            'shutouts': stats['shutouts'],
            'games_played': stats['games_played'],
            'svp': round(svp, 1) if stats['shots_against'] > 0 else 0.0,
            'gaa': round(gaa, 2) if stats['seconds_played'] > 0 else 0.0,
        })

    goalie_stats.sort(key=lambda x: (-x['svp'], x['games_played']))
    player_ids = set()
    if selected_week:
        player_ids.update(
            skater_qs.values_list("ea_player_num__pk", flat=True)
        )
        player_ids.update(
            goalie_qs.values_list("ea_player_num__pk", flat=True)
        )

    players_for_week = Player.objects.filter(
        pk__in=player_ids
    ).order_by(Lower("username"))

    # Existing three-stars (if any) for this season + week
    three_stars = WeeklyThreeStars.objects.filter(
        season=season_num,
        week_start=selected_week,
    ).select_related("first_star", "second_star", "third_star").first()

    # --- Handle POST: saving three stars ---
    if request.method == "POST" and "save_three_stars" in request.POST:
        week_str = request.POST.get("week")  # hidden field in form
        try:
            selected_week = datetime.datetime.strptime(week_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            messages.error(request, "Invalid week selected.")
            return redirect("weekly_stats")

        first_id = request.POST.get("first_star") or None
        second_id = request.POST.get("second_star") or None
        third_id = request.POST.get("third_star") or None
        blurb = (request.POST.get("blurb") or "").strip()

        if DEBUG:
            print("POST DATA:", dict(request.POST))

        if not first_id or not second_id or not third_id:
            messages.error(request, "You must select all three stars.")
            return redirect(f"{reverse('weekly_stats')}?week={selected_week:%Y-%m-%d}")

        if len({first_id, second_id, third_id}) < 3:
            messages.error(request, "Each star must be a different player.")
            return redirect(f"{reverse('weekly_stats')}?week={selected_week:%Y-%m-%d}")

        try:
            first_player = Player.objects.get(pk=first_id)
            second_player = Player.objects.get(pk=second_id)
            third_player = Player.objects.get(pk=third_id)
        except Player.DoesNotExist:
            messages.error(request, "Invalid player selected.")
            return redirect(f"{reverse('weekly_stats')}?week={selected_week:%Y-%m-%d}")

        three_stars, created = WeeklyThreeStars.objects.update_or_create(
            season=Season.objects.get(season_num=season_num),
            week_start=selected_week,
            defaults={
                "first_star": first_player,
                "second_star": second_player,
                "third_star": third_player,
                "blurb": blurb or None,
            },
        )

        # Fire Discord webhook (don’t let errors break the request)
        seasonInstance = Season.objects.get(season_num=season_num)
        try:
            post_three_stars_to_discord(three_stars, selected_week, seasonInstance)
        except Exception as e:
            print(f"[ThreeStars] Discord webhook failed: {e}")

        messages.success(request, "Weekly Three Stars saved.")
        return redirect(f"{reverse('weekly_stats')}?week={selected_week:%Y-%m-%d}")

    # Render
    context = {
        "season": season_num,
        "weeks": weeks,
        "selected_week": selected_week,
        "skater_stats": skater_stats,
        "goalie_stats": goalie_stats,
        "players_for_week": players_for_week,
        "three_stars": three_stars,
    }
    return render(request, "GHLWebsiteApp/weekly_stats.html", context)

@manager_required
def manager_view(request):
    # This view is for managers to access the manager dashboard
    standings = Standing.objects.filter(season=get_seasonSetting()).order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
    my_standing = Standing.objects.filter(season=get_seasonSetting(), team=request.user.player_link.current_team.ea_club_num).first() if hasattr(request.user, 'player_link') else None
    season = get_seasonSetting()
    team = None
    if hasattr(request.user, 'player_link') and request.user.player_link:
        player = request.user.player_link
        if player.current_team:
            team = player.current_team
            leader_goals = SkaterRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username").annotate(numgoals=Sum("goals")).filter(numgoals__gt=0).order_by("-numgoals")[:1]
            leader_assists = SkaterRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username").annotate(numassists=Sum("assists")).filter(numassists__gt=0).order_by("-numassists")[:1]
            leader_points = SkaterRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username").annotate(numpoints=Sum("points")).filter(numpoints__gt=0).order_by("-numpoints")[:1]
            leader_shooting = SkaterRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username").annotate(shootperc=(Cast(Sum("goals"), models.FloatField())/Cast(Sum("sog"), models.FloatField()))*100).filter(shootperc__gt=0).order_by("-shootperc")[:1]
            leader_svp = GoalieRecord.objects.filter(game_num__season_num=season, ea_club_num=team).exclude(game_num__played_time=None).values("ea_player_num", "ea_player_num__username").annotate(savepercsum=(Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100).order_by("-savepercsum")[:1]
            leader_hits = (
                SkaterRecord.objects
                .filter(game_num__season_num=season, ea_club_num=team)
                .values("ea_player_num", "ea_player_num__username")
                .annotate(
                    total_hits=Sum('hits'),
                    games=Count('id'),
                    hits_per_game=ExpressionWrapper(
                        F('total_hits') / F('games'),
                        output_field=FloatField()
                    )
                )
                .order_by('-hits_per_game')
            )[:1]
            leader_blocks = (
                SkaterRecord.objects
                .filter(game_num__season_num=season, ea_club_num=team)
                .values("ea_player_num", "ea_player_num__username")
                .annotate(
                    total_blocks=Sum('blocked_shots'),
                    games=Count('id'),
                    blocks_per_game=ExpressionWrapper(
                        F('total_blocks') / F('games'),
                        output_field=FloatField()
                    )
                )
                .order_by('-blocks_per_game')
            )[:1]
            leader_gaa = (
                GoalieRecord.objects
                .filter(game_num__season_num=season, ea_club_num=team)
                .values("ea_player_num", "ea_player_num__username")
                .annotate(
                    goals_against=Sum(F('shots_against') - F('saves')),
                    seconds_played=Sum(F('game_num__gamelength')),
                    gaa=Case(
                        When(seconds_played=0, then=Value(0.0)),
                        default=F('goals_against') * 3600.0 / F('seconds_played'),
                        output_field=FloatField(),
                    )
                )
                .order_by('gaa')
            )[:1]
            # TODO: Make sure players are still on the team and not traded
            team_leaders = {
                "G": leader_goals[0] if leader_goals else None,
                "A": leader_assists[0] if leader_assists else None,
                "P": leader_points[0] if leader_points else None,
                "S%": leader_shooting[0] if leader_shooting else None,
                "HIT": leader_hits[0] if leader_hits else None,
                "BLK": leader_blocks[0] if leader_blocks else None,
                "SV%": leader_svp[0] if leader_svp else None,
                "GAA": leader_gaa[0] if leader_gaa else None,
            }
        else:
            messages.error(request, "You are currently not linked to a team. Either adjust your linked player, or contact the league manager.")
            return redirect('user_profile')
        now = timezone.now()
        upcoming_games = (
            Game.objects
            .filter(
                season_num=season,
                expected_time__gt=now,
                played_time__isnull=True  # Ensure the game hasn't been played yet
            )
            .filter(
                Q(a_team_num=team) | Q(h_team_num=team)
            )
            .order_by('expected_time')[:10]
        )
        eastern = pytz.timezone("America/New_York")
        now_est = django_timezone.now().astimezone(eastern)
        today = now_est.date() # Returns today's date in EST
        
        # find this week's Sunday
        days_since_sunday = (today.weekday() + 1) % 7 # Calculates days since previous Sunday
        this_sunday = today - datetime.timedelta(days=days_since_sunday) # "This Sunday" is the previous Sunday

        if days_since_sunday >= 5: # If Friday or Saturday
            sunday = this_sunday + datetime.timedelta(days=7)
        else:
            sunday = this_sunday

        # Query availability for the correct week
        availability_qs = PlayerAvailability.objects.filter(
            player__current_team=team,
            week_start=sunday,
        )
    else:
        messages.error(request, "You are currently not linked to a team. Either adjust your linked player, or contact the league manager.")
        redirect('user_profile')

    userteam = get_user_team(request.user)
    block = TradeBlockPlayer.objects.filter(player__current_team=userteam).order_by('player__username')
    needs = TeamNeed.objects.filter(team=userteam)

    context = {
        'team': team,
        "standings": standings,
        "team_leaders": team_leaders,
        "upcoming_games": upcoming_games,
        "availability": availability_qs,
        "my_standing": my_standing,
        "block": block,
        "needs": needs,
    }
    return render(request, 'GHLWebsiteApp/manager_dashboard.html', context)

@login_required
def player_availability_view(request):
    player = request.user.player_link

    week_param = request.GET.get("week_start")

    if week_param:
        try:
            week_start = datetime.date.fromisoformat(week_param)
        except ValueError:
            week_start = get_default_week_start()
    else:
        week_start = get_default_week_start()

    # --- Get or create existing availability record for that week ---
    availability_obj, created = PlayerAvailability.objects.get_or_create(
        player=player,
        week_start=week_start
    )

    # --- Bind form (POST updates existing row; GET only shows form) ---
    if request.method == "POST":
        form = PlayerAvailabilityForm(request.POST, instance=availability_obj, player=player)
        if form.is_valid():
            form.save()
            messages.success(request, "Availability saved successfully.")
            return redirect(f"{request.path}?week_start={week_start.isoformat()}")
    else:
        # Bind with initial so dropdown shows correct week
        form = PlayerAvailabilityForm(
            instance=availability_obj,
            initial={"week_start": week_start},
            player=player
        )

    # --- For template: supply day/checkbox fields in a friendly structure ---
    day_form_fields = [
        ("Sunday", form["sunday"]),
        ("Monday", form["monday"]),
        ("Tuesday", form["tuesday"]),
        ("Wednesday", form["wednesday"]),
        ("Thursday", form["thursday"]),
    ]

    context = {
        "form": form,
        "day_form_fields": day_form_fields,
    }

    return render(request, "GHLWebsiteApp/player_availability.html", context)

@manager_required
def team_scheduling_view(request):
    player = request.user.player_link
    team = player.current_team
    season = get_seasonSetting()

    if not team:
        messages.error(request, "You are not assigned to a team.")
        return redirect("user_profile")

    # --- Determine current/selected week ---
    week_str = request.GET.get("week")
    if week_str:
        try:
            sunday = datetime.datetime.strptime(week_str, "%B %d, %Y").date()
        except ValueError:
            eastern = pytz.timezone("America/New_York")
            now_est = django_timezone.now().astimezone(eastern)
            today = now_est.date()
            days_since_sunday = (today.weekday() + 1) % 7
            this_sunday = today - datetime.timedelta(days=days_since_sunday)
            sunday = this_sunday + datetime.timedelta(days=7 if days_since_sunday >= 5 else 0)
    else:
        eastern = pytz.timezone("America/New_York")
        now_est = django_timezone.now().astimezone(eastern)
        today = now_est.date()
        days_since_sunday = (today.weekday() + 1) % 7
        this_sunday = today - datetime.timedelta(days=days_since_sunday)
        sunday = this_sunday + datetime.timedelta(days=7 if days_since_sunday >= 5 else 0)

    if "week" not in request.GET:
        return redirect(f"{request.path}?week={sunday.strftime('%B %d, %Y')}")


    # --- Get games for the week ---
    start_dt = timezone.make_aware(datetime.datetime.combine(sunday, datetime.time.min))
    end_dt = start_dt + datetime.timedelta(days=7)

    print("Team:", team)
    print("Season:", season)
    print("Start:", start_dt)
    print("End:", end_dt)

    # ---- Get all games for this team & week ----
    games_qs = Game.objects.filter(
        season_num=season,
        expected_time__date__gte=sunday,
        expected_time__date__lt=sunday + datetime.timedelta(days=7),
    ).filter(
        Q(h_team_num=team) | Q(a_team_num=team)
    ).order_by("expected_time")

    # ---- Convert to EST and attach weekday ----
    games = []
    for g in games_qs:
        local_dt = g.expected_time.astimezone(est)   # convert before tuple packing
        games.append((g, local_dt.weekday()))

    # --- Availability for team this week ---
    availability = PlayerAvailability.objects.filter(player__current_team=team, week_start=sunday)
    availability_map = {a.player.ea_player_num: a for a in availability}

    # --- Current scheduling assignments ---
    game_objs = [g for (g, weekday) in games]   # strip weekday, keep actual Game objects
    scheduling = Scheduling.objects.filter(game__in=game_objs, team=team)
    schedule_map = {(s.game_id, s.position_id): s.player_id for s in scheduling}

    # --- Get positions + players on team ---
    positions = list(
        Position.objects.annotate(
            sort_order=Case(
                When(positionShort='C', then=Value(0)),
                When(positionShort='LW', then=Value(1)),
                When(positionShort='RW', then=Value(2)),
                When(positionShort='LD', then=Value(3)),
                When(positionShort='RD', then=Value(4)),
                When(positionShort='G', then=Value(5)),
                default=Value(99),
                output_field=IntegerField()
            )
        ).order_by('sort_order')
    )
    players = team.player_set.all().order_by("username")
    signup_season = get_signup_season()
    player_caps = {}
    if signup_season:
        signups = Signup.objects.filter(season=signup_season, player__in=players)
        for s in signups:
            if not s.player_id:
                continue
            max_games = s.days_per_week * 2  # 2 games per night
            player_caps[s.player_id] = {
                "name": s.player.username,
                "max_games": max_games,
                "nights": s.days_per_week,
            }

    # --- Save handler ---
    if request.method == "POST":
        for game_obj, weekday in games:
            for pos in positions:
                field_name = f"game_{game_obj.game_num}_pos_{pos.positionShort}"
                player_id = request.POST.get(field_name)

                if player_id:
                    Scheduling.objects.update_or_create(
                        game=game_obj,
                        team=team,
                        position=pos,
                        defaults={"player_id": player_id}
                    )
                else:
                    Scheduling.objects.filter(
                        game=game_obj,
                        team=team,
                        position=pos
                    ).delete()
        messages.success(request, "Schedule saved successfully.")
        return redirect(f"{request.path}?week={sunday.strftime('%B %d, %Y')}")

    # --- All Sundays with games for week dropdown ---
    game_dates = (
        Game.objects
        .filter(season_num=season, played_time__isnull=True)
        .filter(Q(h_team_num=team) | Q(a_team_num=team))
        .values_list("expected_time", flat=True)
    )

    sundays = set()
    for dt in game_dates:
        est_date = dt.astimezone(pytz.timezone("America/New_York")).date()
        week_sunday = est_date - datetime.timedelta(days=(est_date.weekday() + 1) % 7)
        sundays.add(week_sunday)

    if sunday not in sundays:
        sundays.add(sunday)

    week_choices = [d.strftime("%B %d, %Y") for d in sorted(sundays)]
    selected_week_str = sunday.strftime("%B %d, %Y")

    context = {
        "games": games,
        "positions": positions,
        "players": players,
        "schedule_map": schedule_map,
        "availability_map": availability_map,
        "sunday": sunday,
        "week_choices": week_choices,
        "selected_week_str": selected_week_str,
        "player_caps_json": json.dumps(player_caps),
    }
    return render(request, "GHLWebsiteApp/team_scheduling.html", context)

@staff_member_required
def tools(request):
    try:
        season = Season.objects.get(season_num=get_seasonSetting())
    except Season.DoesNotExist:
        season = None
    if request.method == "POST" and "signup_action" in request.POST:
        action = request.POST["signup_action"]
        if action == "open":
            season.signups_open = True
        elif action == "close":
            season.signups_open = False
        season.save()

    # Signup stats
    signups_qs = Signup.objects.filter(season=season)

    total_signups = signups_qs.count()

    primary_breakdown = (
        signups_qs
        .values("primary_position__positionShort", "primary_position__position")
        .annotate(count=Count("id"))
        .order_by("primary_position__positionShort")
    )

    secondary_breakdown = (
        signups_qs
        .values("secondary_positions__positionShort", "secondary_positions__position")
        .annotate(count=Count("id"))
        .order_by("secondary_positions__positionShort")
    )

    context = {
        "season": season,
        "total_signups": total_signups,
        "primary_breakdown": primary_breakdown,
        "secondary_breakdown": secondary_breakdown,
    }
    return render(request, "GHLWebsiteApp/tools.html", context)

@login_required
def season_signup(request):
    # Active season
    season = Season.objects.get(season_num=get_seasonSetting())

    # Guard: signups must be open
    if not getattr(season, "signups_open", False):
        return HttpResponseForbidden("Signups are currently closed for this season.")

    # Single signup per user per season
    try:
        instance = Signup.objects.get(season=season, user=request.user)
    except Signup.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = SignupForm(request.POST, instance=instance)
        if form.is_valid():
            signup = form.save(commit=False)
            signup.user = request.user

            # Link to Player if available
            player = getattr(request.user, "player_link", None)
            if player:
                signup.player = player

            signup.season = season
            signup.save()
            messages.success(request, "Your signup has been submitted.")
            return redirect("season_signup")
    else:
        form = SignupForm(instance=instance)

    return render(
        request,
        "GHLWebsiteApp/signup_form.html",
        {
            "form": form,
            "season": season,
            "signups_open": season.signups_open,
        },
    )

@manager_required
def signup_list(request):
    season = Season.objects.get(season_num=get_seasonSetting())
    signups = (
        Signup.objects
        .filter(season=season)
        .select_related("user", "player", "primary_position")
        .prefetch_related("secondary_positions")
        .order_by("user__username")
    )

    # CSV download if requested
    if request.GET.get("download") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="signups_{season.season_text}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Site Name",
            "Username",
            "Primary Pos",
            "Secondary Pos",
            "Nights",
            "Scheduling Issues",
            "Invited By",
            "Committed?",
            "Other Leagues",
            "Created At",
        ])

        for s in signups:
            secondaries = ", ".join(
                s.secondary_positions.order_by("positionShort").values_list("positionShort", flat=True)
            )
            writer.writerow([
                s.user.username,
                s.player.username if s.player else "",
                s.primary_position.positionShort if s.primary_position else "",
                secondaries,
                s.days_per_week,
                (s.scheduling_issues or "").replace("\n", " "),
                s.invited_by_name or "",
                "Yes" if s.committed_to_league else "No",
                (s.other_league_obligations or "").replace("\n", " "),
                localtime(s.created_at).strftime("%Y-%m-%d %H:%M"),
            ])

        return response

    return render(
        request,
        "GHLWebsiteApp/signup_list.html",
        {
            "season": season,
            "signups": signups,
        },
    )


class PlayerAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        linked_ids = User.objects.filter(
            player_link__isnull=False
        ).values_list('player_link_id', flat=True)

        qs = Player.objects.exclude(ea_player_num__in=linked_ids)

        if self.q:
            qs = qs.filter(username__icontains=self.q)

        return qs