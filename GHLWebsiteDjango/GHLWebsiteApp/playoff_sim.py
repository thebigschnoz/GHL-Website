import random
from collections import defaultdict


from .models import Season, Game, Standing, PlayoffConfig, Team

def get_active_season():
    return Season.objects.get(isActive=True)


def get_playoff_config(season: Season) -> PlayoffConfig:
    return PlayoffConfig.objects.get(season=season)


def get_current_standings(season: Season):
    """
    Returns a list of Standing objects for this season, ordered the same
    way as your Meta ordering (points, wins, GF, GA, name).
    """
    return list(
        Standing.objects.filter(season=season)
        .select_related("team")
        .order_by("-points", "-wins", "-goalsfor", "goalsagainst", "team__club_full_name")
    )


def get_remaining_games(season: Season):
    """
    Unplayed games = no played_time set (you can tweak this if needed).
    """
    return list(
        Game.objects.filter(season_num=season, played_time__isnull=True)
        .select_related("a_team_num", "h_team_num")
    )

def build_base_points_table(standings):
    """
    Returns a dict: team_id -> current points
    """
    return {s.team_id: s.points for s in standings}


def build_games_left(remaining_games):
    """
    For debugging/analysis: how many remaining games per team
    """
    games_left = defaultdict(int)
    for g in remaining_games:
        games_left[g.h_team_num_id] += 1
        games_left[g.a_team_num_id] += 1
    return games_left

def simulate_season_once(
    season: Season,
    base_points: dict[int, int],
    remaining_games,
) -> list[int]:
    """
    Run one random completion of the season.
    Return a list of team_ids sorted by final standings.
    """
    # Copy base points
    points = dict(base_points)

    for g in remaining_games:
        # Simple probability model; adjust if you want
        outcome = random.random()

        if outcome < 0.45:
            # home reg win: 2 points
            points[g.h_team_num_id] += 2
        elif outcome < 0.90:
            # away reg win
            points[g.a_team_num_id] += 2
        else:
            # OT result: 2 pts winner, 1 pt loser
            if random.random() < 0.5:
                points[g.h_team_num_id] += 2
                points[g.a_team_num_id] += 1
            else:
                points[g.a_team_num_id] += 2
                points[g.h_team_num_id] += 1

    # We need to sort teams using your same tiebreak rules:
    # points desc, wins desc, GF desc, GA asc, name asc.
    # We only have points here, but we can approximate by
    # merging in current standings data.
    standings_map = {
        s.team_id: s for s in Standing.objects.filter(season=season).select_related("team")
    }

    def sort_key(team_id):
        s = standings_map.get(team_id)
        # Use current wins/GF/GA as tie-break proxies. For a more
        # accurate simulation, you'd also randomize goals, etc.
        return (
            -points[team_id],
            -(s.wins if s else 0),
            -(s.goalsfor if s else 0),
            (s.goalsagainst if s else 0),
            s.team.club_full_name if s else "",
        )

    sorted_teams = sorted(points.keys(), key=sort_key)
    return sorted_teams

def compute_playoff_odds(season: Season, iterations: int = 5000):
    cfg = get_playoff_config(season)
    standings = get_current_standings(season)
    remaining_games = get_remaining_games(season)

    if not remaining_games:
        # season effectively done, just mark top N
        sorted_teams = [s.team_id for s in standings]
        return {
            s.team_id: 1.0 if i < cfg.playoff_teams else 0.0
            for i, s in enumerate(standings)
        }

    base_points = build_base_points_table(standings)

    qualify_counts = {s.team_id: 0 for s in standings}

    for _ in range(iterations):
        final_order = simulate_season_once(season, base_points, remaining_games)
        qualifiers = set(final_order[:cfg.playoff_teams])
        for team_id in qualifiers:
            if team_id in qualify_counts:
                qualify_counts[team_id] += 1

    odds = {
        team_id: qualify_counts[team_id] / iterations
        for team_id in qualify_counts
    }
    return odds

def update_playoff_flags_from_odds(season: Season, iterations: int = 5000):
    odds = compute_playoff_odds(season, iterations=iterations)
    standings = Standing.objects.filter(season=season).select_related("team")

    for s in standings:
        p = odds.get(s.team_id, 0.0)
        old_code = s.playoffs
        new_code = old_code

        if p >= 0.999 and old_code == "":
            new_code = "x"  # clinched playoff spot
        # Optional: add elimination code if you add it to choices
        # elif p <= 0.001 and old_code == "":
        #     new_code = "e"

        if new_code != old_code:
            s.playoffs = new_code
            s.save(update_fields=["playoffs"])
