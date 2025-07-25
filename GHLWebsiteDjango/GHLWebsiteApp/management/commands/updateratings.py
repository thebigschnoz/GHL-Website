from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from GHLWebsiteApp.models import SkaterRecord, GameSkaterRating, TeamRecord, SkaterRating
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from scipy.stats import rankdata

# Coefficient Maps (abbreviated for clarity)
OFFENSE_COEFF = {
    'goals': 22.5,
    'assists': 9.5,
    'sog': 2.0,
    'poss_time': 0.05,
    'fow': 0.5,
    'fol': -0.5,
}

DEFENSE_COEFF = {
    'pass_pct': 30,
    'giveaways': -0.75,
    'takeaways': 1.5,
    'interceptions': 1.2,
    'blocked_shots': 2,
    'pims': -0.5,
    'pens_drawn': 6,
    'plus_minus': 5,
    'hits': 0.25,
}

TEAMPLAY_COEFF = {
    'goals_for': 12.5,
    'goals_against': -12.5,
    'shots_for': 1.2,
    'power_play': 0.15,
    'penalty_kill': 0.15,
    'possession_diff': 0.2,
    'constant': 50
}

GAME_RESULT_COEFF = {
    'reg_win': 10,
    'ot_win': 6.6,
    'ot_loss': 3.3,
    'reg_loss': 0,
}

# Role Weights
FORWARD_WEIGHTS = {'off': 0.60, 'def': 0.15, 'team': 0.25}
DEFENSE_WEIGHTS = {'off': 0.15, 'def': 0.60, 'team': 0.25}

FORWARD_POS = {'LW', 'RW', 'C'}
DEF_POS = {'LD', 'RD'}

class Command(BaseCommand):
    help = "Calculate per-game skater ratings"

    def handle(self, *args, **kwargs):
        count = 0
        # STEP 1 : Calculate per-game skater ratings
        for skater in SkaterRecord.objects.select_related('position', 'game_num', 'ea_club_num'):
            if GameSkaterRating.objects.filter(skater_record=skater).exists():
                continue  # Skip already rated

            team_record = TeamRecord.objects.filter(
                game_num=skater.game_num,
                ea_club_num=skater.ea_club_num
            ).first()
            if not team_record:
                continue

            pos = skater.position.positionShort.upper()
            is_forward = pos in FORWARD_POS

            # Offense
            off = sum([
                getattr(skater, field, 0) * Decimal(coeff)
                for field, coeff in OFFENSE_COEFF.items()
            ])

            # Defense
            defn = sum([
                getattr(skater, field, 0) * Decimal(coeff)
                for field, coeff in DEFENSE_COEFF.items()
            ])

            # Team Play
            team = (
                team_record.goals_for * TEAMPLAY_COEFF['goals_for'] +
                team_record.goals_against * TEAMPLAY_COEFF['goals_against'] +
                team_record.sog_team * TEAMPLAY_COEFF['shots_for'] +
                TEAMPLAY_COEFF['constant']
            )

            # Possession
            team += (team_record.toa_team - team_record.toa_team) * TEAMPLAY_COEFF['possession_diff']

            # Game Result Bonus
            g = skater.game_num
            gf, ga = (g.a_team_gf, g.h_team_gf) if skater.ea_club_num == g.a_team_num else (g.h_team_gf, g.a_team_gf)
            result = 'reg_win' if gf > ga and g.gamelength == 3600 else \
                     'ot_win' if gf > ga and g.gamelength > 3600 else \
                     'ot_loss' if gf < ga and g.gamelength > 3600 else \
                     'reg_loss'
            result_bonus = Decimal(GAME_RESULT_COEFF[result])

            # Apply weights
            weights = FORWARD_WEIGHTS if is_forward else DEFENSE_WEIGHTS
            ovr = (
                off * Decimal(weights['off']) +
                defn * Decimal(weights['def']) +
                team * Decimal(weights['team']) +
                result_bonus
            )

            GameSkaterRating.objects.create(
                skater_record=skater,
                offense_rating=round(off, 2),
                defense_rating=round(defn, 2),
                teamplay_rating=round(team, 2),
                game_result_bonus=result_bonus,
                overall_rating=round(ovr, 2)
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Rated {count} skater games.'))
        
        # STEP 2 : Aggregate per-player-season-position
        ratings_map = defaultdict(list)

        for rating in GameSkaterRating.objects.select_related('skater_record__game_num', 'skater_record__position', 'skater_record__ea_player_num'):
            rec = rating.skater_record
            key = (rec.ea_player_num, rec.game_num.season_num, rec.position)
            ratings_map[key].append(rating)

        for (player, season, position), ratings in ratings_map.items():
            off_avg = sum(r.offense_rating for r in ratings) / len(ratings)
            def_avg = sum(r.defense_rating for r in ratings) / len(ratings)
            team_avg = sum(r.teamplay_rating for r in ratings) / len(ratings)
            ovr_avg = sum(r.overall_rating for r in ratings) / len(ratings)

            skater_rating, _ = SkaterRating.objects.update_or_create(
                player=player,
                season=season,
                position=position,
                weights_version="v1",
                defaults={
                    "games_played": len(ratings),
                    "off_rat": round(off_avg, 2),
                    "def_rat": round(def_avg, 2),
                    "team_rat": round(team_avg, 2),
                    "ovr_rat": round(ovr_avg, 2),
                }
            )
        
        # STEP 3 : Calculate percentiles for each position in each season
        def set_percentiles_for_season(season_id):
            all_ratings = list(SkaterRating.objects.filter(season=season_id, weights_version="v1").select_related("position"))
            if not all_ratings:
                return

            by_pos = defaultdict(list)
            for rating in all_ratings:
                by_pos[rating.position_id].append(rating)

            for pos_id, group in by_pos.items():
                def pct(arr):
                    return rankdata(arr, method='average') / len(arr) * 100

                off_arr = [r.off_rat for r in group]
                def_arr = [r.def_rat for r in group]
                team_arr = [r.team_rat for r in group]
                ovr_arr = [r.ovr_rat for r in group]

                off_pcts = pct(off_arr)
                def_pcts = pct(def_arr)
                team_pcts = pct(team_arr)
                ovr_pcts = pct(ovr_arr)

                for i, rating in enumerate(group):
                    rating.off_pct = round(off_pcts[i], 2)
                    rating.def_pct = round(def_pcts[i], 2)
                    rating.team_pct = round(team_pcts[i], 2)
                    rating.ovr_pct = round(ovr_pcts[i], 2)
                    rating.save(update_fields=["off_pct", "def_pct", "team_pct", "ovr_pct"])

        # Call each season
        for season in SkaterRating.objects.values_list("season", flat=True).distinct():
            set_percentiles_for_season(season)
