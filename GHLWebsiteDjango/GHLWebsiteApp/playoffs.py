from django.db import transaction
from datetime import datetime, time, timedelta
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .views import get_seasonSetting

from .models import Season, Standing, PlayoffConfig, PlayoffRound, PlayoffSeries

def get_upcoming_sunday_9pm():
    """
    Return the next Sunday at 21:00 in the current timezone.
    'Week' flips at Sunday 9pm: if we're already past this week's
    Sunday 9pm, move to next Sunday.
    """
    now = timezone.localtime(timezone.now())
    tz = timezone.get_current_timezone()

    # Monday=0 ... Sunday=6
    days_until_sunday = (6 - now.weekday()) % 7
    sunday_date = (now + timedelta(days=days_until_sunday)).date()

    first_slot = timezone.make_aware(
        datetime.combine(sunday_date, time(21, 0)),
        tz
    )

    if first_slot <= now:
        # We’re already at/after this Sunday's 9pm; use next week.
        sunday_date = sunday_date + timedelta(days=7)
        first_slot = timezone.make_aware(
            datetime.combine(sunday_date, time(21, 0)),
            tz
        )

    return first_slot


def get_playoff_game_slots():
    """
    Seven slots for a series:
    Sun 9:00, Sun 9:45, Mon 9:00, Mon 9:45, Tue 9:00, Wed 9:00, Thu 9:00.
    """
    first = get_upcoming_sunday_9pm()
    return [
        first,                              # G1 Sun 9:00
        first + timedelta(minutes=45),      # G2 Sun 9:45
        first + timedelta(days=1),          # G3 Mon 9:00
        first + timedelta(days=1, minutes=45),  # G4 Mon 9:45
        first + timedelta(days=2),          # G5 Tue 9:00
        first + timedelta(days=3),          # G6 Wed 9:00
        first + timedelta(days=4),          # G7 Thu 9:00
    ]


def create_games_for_series(series, slots=None):
    """
    Create 7 Game rows for a given PlayoffSeries.

    Better (high) seed home pattern: H, H, A, A, H, A, H.
    """
    from .models import Game  # avoid circular imports just in case

    if slots is None:
        slots = get_playoff_game_slots()

    home_pattern = ["high", "high", "low", "low", "high", "low", "high"]

    for when, home_side in zip(slots, home_pattern):
        if home_side == "high":
            home = series.high_seed
            away = series.low_seed
        else:
            home = series.low_seed
            away = series.high_seed

        Game.objects.create(
            season_num=series.season,
            expected_time=when,
            gamelength=3600,
            dnf=False,
            a_team_num=away,
            h_team_num=home,
        )


def create_games_for_round(round_obj):
    """
    Create games for every series in a PlayoffRound.
    All series share the same weekly time grid.
    """
    slots = get_playoff_game_slots()
    for series in PlayoffSeries.objects.filter(
        season=round_obj.season,
        round_num=round_obj
    ):
        create_games_for_series(series, slots)


def get_playoff_seeds(season: Season):
    """
    Return a list of (seed_number, standing) for the given season.
    Seed 1 = best team, Seed N = worst playoff team.
    """
    # How many teams?
    config, _ = PlayoffConfig.objects.get_or_create(season=season)
    playoff_teams = config.playoff_teams

    standings_qs = (
        Standing.objects
        .filter(season=season)
        .order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
    )

    standings_list = list(standings_qs[:playoff_teams])

    return list(enumerate(standings_list, start=1))  # [(1, Standing), (2, Standing), ...]

@staff_member_required
@transaction.atomic
def start_playoffs(request):
    season = Season.objects.get(season_num=get_seasonSetting())

    if season.season_type != "regular":
        messages.error(request, "Season must be in 'regular' state to start playoffs.")
        return redirect("standings")
    
    seeds = get_playoff_seeds(season)  # [(seed, Standing), ...]
    num_teams = len(seeds)

    playoff_season_text = f"{season.season_text} Playoffs"

    # Remove isActive from the previous season
    season.isActive = False
    season.save()

    # Create the new Season object for playoffs
    new_season = Season.objects.create(
        season_text=playoff_season_text,
        season_type="playoffs",
        start_date=timezone.now(),
        isActive=True
    )

    # This new season becomes the working season for the rest of this function
    season = new_season

    if num_teams == 0 or (num_teams & (num_teams - 1)) != 0:
        # Require a power-of-two for now (4, 8, 16...)
        messages.error(
            request,
            f"Playoffs need a power-of-two number of teams (4, 8, 16...), got {num_teams}."
        )
        return redirect("standings")

    # Nuke any previous playoff data for this season
    PlayoffSeries.objects.filter(season=season).delete()
    PlayoffRound.objects.filter(season=season).delete()

    # Create Round 1
    round1, _ = PlayoffRound.objects.get_or_create(
        season=season,
        round_num=1,
        defaults={"round_name": "Quarterfinals" if num_teams == 8 else "Round 1"},
    )

    # Pair: 1 vs N, 2 vs N-1, etc.
    pairs = []
    left = 0
    right = num_teams - 1
    while left < right:
        high_seed_num, high_standing = seeds[left]
        low_seed_num, low_standing = seeds[right]
        pairs.append((high_seed_num, high_standing.team,
                      low_seed_num,  low_standing.team))
        left += 1
        right -= 1

    # Create series rows
    # Your semantics: high_seed_num field = 8 for highest seed, 7 for next, etc.
    for high_seed, high_team, low_seed, low_team in pairs:
        PlayoffSeries.objects.create(
            season=season,
            round_num=round1,
            high_seed=high_team,
            low_seed=low_team,
            # 1 = best → N ; N = worst → 1
            high_seed_num=num_teams - high_seed + 1,
            low_seed_num=num_teams - low_seed + 1,
            high_seed_wins=0,
            low_seed_wins=0,
        )
    create_games_for_round(round1)
    messages.success(
        request,
        f"Created {len(pairs)} playoff series for {season.season_text} and switched to playoffs."
    )
    return redirect("standings")

@staff_member_required
@transaction.atomic
def advance_round(request):
    season = Season.objects.get(season_num=get_seasonSetting())

    if season.season_type != "playoffs":
        messages.error(request, "Season must be in 'playoffs' state to advance a round.")
        return redirect("tools")

    # Find all rounds for this season
    rounds_qs = PlayoffRound.objects.filter(season=season)
    if not rounds_qs.exists():
        messages.error(request, "No playoff rounds exist for this season.")
        return redirect("tools")

    # We'll advance from the last (highest-numbered) existing round
    current_round = rounds_qs.order_by("-round_num").first()
    current_round_num = current_round.round_num

    current_series_qs = PlayoffSeries.objects.filter(season=season, round_num=current_round)
    if not current_series_qs.exists():
        messages.error(request, f"Round {current_round_num} has no series to advance from.")
        return redirect("tools")

    # All series must have a winner
    incomplete = current_series_qs.filter(series_winner__isnull=True)
    if incomplete.exists():
        messages.error(
            request,
            f"Cannot advance: Round {current_round_num} still has unfinished series."
        )
        return redirect("tools")

    # Collect winners in a deterministic order (id for now; good enough)
    winners = [s.series_winner for s in current_series_qs.order_by("id")]

    # If only one winner, playoffs are done – don't create a new round
    if len(winners) == 1:
        champion = winners[0]
        messages.info(
            request,
            f"Round {current_round_num} is complete and {champion.club_full_name} "
            "has already won the championship. No further round created."
        )
        return redirect("standings")

    # Check that next round doesn't already exist
    next_round_num = current_round_num + 1
    if PlayoffRound.objects.filter(season=season, round_num=next_round_num).exists():
        messages.error(
            request,
            f"Round {next_round_num} already exists. Delete it manually if you really want to rebuild it."
        )
        return redirect("tools")

    # Round name based on how many series we'll get
    series_count_next = len(winners) // 2
    if series_count_next == 1:
        next_round_name = "Final"
    elif series_count_next == 2:
        next_round_name = "Semifinals"
    elif series_count_next == 4:
        next_round_name = "Quarterfinals"
    else:
        next_round_name = f"Round {next_round_num}"

    next_round = PlayoffRound.objects.create(
        season=season,
        round_num=next_round_num,
        round_name=next_round_name,
    )

    # Use original playoff seeding (from final regular standings) to decide who is "high" vs "low"
    # This keeps "better seed vs worse seed" logic even in later rounds.
    seeds = get_playoff_seeds(season)  # [(seed_num, Standing), ...]
    seed_by_team_id = {standing.team.id: seed for seed, standing in seeds}

    config, _ = PlayoffConfig.objects.get_or_create(season=season)
    total_playoff_teams = config.playoff_teams

    # Sort winners by ORIGINAL seed (1 = best)
    winners_sorted = sorted(
        winners,
        key=lambda t: seed_by_team_id.get(t.pk, 9999)
    )

    # Pair best vs worst, next best vs next worst, etc.
    pairs = []
    left = 0
    right = len(winners_sorted) - 1
    while left < right:
        high_team = winners_sorted[left]   # better seed (numerically lower)
        low_team = winners_sorted[right]   # worse seed
        high_seed = seed_by_team_id.get(high_team.pk)
        low_seed = seed_by_team_id.get(low_team.pk)
        pairs.append((high_team, high_seed, low_team, low_seed))
        left += 1
        right -= 1

    for high_team, high_seed, low_team, low_seed in pairs:
        # These seed-number fields are mostly for bookkeeping; your viewer builds seeding
        # from the first round anyway. :contentReference[oaicite:2]{index=2}
        PlayoffSeries.objects.create(
            season=season,
            round_num=next_round,
            high_seed=high_team,
            low_seed=low_team,
            high_seed_num=(
                total_playoff_teams - high_seed + 1
                if high_seed is not None else 0
            ),
            low_seed_num=(
                total_playoff_teams - low_seed + 1
                if low_seed is not None else 0
            ),
            high_seed_wins=0,
            low_seed_wins=0,
        )
    create_games_for_round(next_round)
    messages.success(
        request,
        f"Advanced to Round {next_round_num} ({next_round.round_name}) with {len(pairs)} series created."
    )
    return redirect("standings")
