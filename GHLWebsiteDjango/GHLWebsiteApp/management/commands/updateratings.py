from django.core.management.base import BaseCommand
from GHLWebsiteApp.models import SkaterRecord, GameSkaterRating, TeamRecord, SkaterRating
from GHLWebsiteApp.views import get_seasonSetting
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
    'pass_pct': 0.3,
    'giveaways': -0.75,
    'takeaways': 1.5,
    'interceptions': 1.2,
    'blocked_shots': 1,
    'pims': -1,
    'pens_drawn': 6,
    'plus_minus': 5,
    'hits': 0.25,
    'def_constant': 15, # Constant for standardizing defense rating
}

DEFENSE_ONLY_COEFF = {
    'goals_against': -2.5,
    'shots_against': -0.35,
    'win': 15,
}

TEAMPLAY_COEFF = {
    'goals_for': 12.5,
    'goals_against': -12.5,
    'shots_for': 1.2,
    'power_play': 15,
    'penalty_kill': -15,
    'possession_diff': 0.2,
    'constant': 50, # Constant for standardizing team play rating
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

class Command(BaseCommand):
    help = "Calculate per-game skater ratings"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation of all GameSkaterRatings (delete and recalculate)',
        )
        parser.add_argument(
            '--allseasons',
            action='store_true',
            help='Recalculate all seasons, not just the current one',
        )
        parser.add_argument(
            '--thisseason',
            action='store_true',
            help='Deletes and completely recalculates the active season. Best used when changing weights and coefficients.',
        )

    def get_opponent_sog(skater_record):
        game = skater_record.game_num
        my_team = skater_record.ea_club_num
        opponent_team = (
            game.h_team_num if my_team == game.a_team_num
            else game.a_team_num
        )
        opponent_team_record = TeamRecord.objects.filter(
            game_num=game,
            ea_club_num=opponent_team
        ).first()
        return opponent_team_record.sog_team if opponent_team_record else 0
    
    def get_opponent_toa(skater_record):
        game = skater_record.game_num
        my_team = skater_record.ea_club_num
        opponent_team = (
            game.h_team_num if my_team == game.a_team_num
            else game.a_team_num
        )
        opponent_team_record = TeamRecord.objects.filter(
            game_num=game,
            ea_club_num=opponent_team
        ).first()
        return opponent_team_record.toa_team if opponent_team_record else 0


    def handle(self, *args, **options):
        count = 0
        force = options['force']
        allseasons = options['allseasons']
        thisseason = options['thisseason']

        if force:
            GameSkaterRating.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted all existing GameSkaterRatings (forced recalc)."))
        if thisseason:
            GameSkaterRating.objects.filter(skater_record__game_num__season_num__isActive=True).delete()
            self.stdout.write(self.style.WARNING("Deleted all GameSkaterRatings for the current season (forced recalc)."))
            
        # STEP 1 : Calculate per-game skater ratings
        for skater in SkaterRecord.objects.exclude(position=0).select_related('position', 'game_num', 'ea_club_num'):
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
            defn = min(sum([
                getattr(skater, field, 0) * Decimal(coeff)
                for field, coeff in DEFENSE_COEFF.items()
            ]),Decimal(0))
            if not is_forward:
                shots_against = self.get_opponent_sog(skater)
                if team_record.goals_for > team_record.goals_against:
                    win = 1
                else:
                    win = 0
                defn += Decimal(
                    team_record.goals_against * DEFENSE_ONLY_COEFF['goals_against'] +
                    shots_against * DEFENSE_ONLY_COEFF['shots_against'] + # Pull from opposing TeamRecord
                    win * DEFENSE_ONLY_COEFF['win']  # Compare between two records.
                )
            # Team Play
            team = min(Decimal(
                team_record.goals_for * TEAMPLAY_COEFF['goals_for'] +
                team_record.goals_against * TEAMPLAY_COEFF['goals_against'] +
                team_record.sog_team * TEAMPLAY_COEFF['shots_for'] +
                team_record.ppg_team * TEAMPLAY_COEFF['power_play'] +
                team_record.shg_team * TEAMPLAY_COEFF['penalty_kill'] +
                TEAMPLAY_COEFF['constant']
            ), Decimal(0))

            # Possession
            team += Decimal((team_record.toa_team - self.get_opponent_toa(skater)) * TEAMPLAY_COEFF['possession_diff'])

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
        self.stdout.write(f'Rated {count} skater games.')
        
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
        self.stdout.write(f'Aggregated ratings for {len(ratings_map)} player-season-position combinations.')
        
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
        if allseasons:
            for season in SkaterRating.objects.values_list("season", flat=True).distinct():
                set_percentiles_for_season(season)
            self.stdout.write('Percentiles calculated for all seasons.')
        else:
            season = get_seasonSetting()
            set_percentiles_for_season(season)
            self.stdout.write(f'Percentiles calculated for Season ID {season}.')

        # STEP 4 : Remove Goalie Games
        gameskaterratingcount = skaterratingcount = 0
        for rating in GameSkaterRating.objects.filter(skater_record__position=0):
            gameskaterratingcount += 1
            rating.delete()
        if gameskaterratingcount > 0:
            self.stdout.write(f'Removed {gameskaterratingcount} inadvertently calculated goalie game ratings.')
        for rating in SkaterRating.objects.filter(position=0):
            skaterratingcount += 1
            rating.delete()
        if skaterratingcount > 0:
            self.stdout.write(f'Removed {skaterratingcount} inadvertently calculated goalie positional ratings.')

        self.stdout.write(self.style.SUCCESS('Ratings update complete!'))
