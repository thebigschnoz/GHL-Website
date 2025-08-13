from django.core.management.base import BaseCommand
from GHLWebsiteApp.models import SkaterRecord, GameSkaterRating, TeamRecord, SkaterRating, GoalieRecord, GameGoalieRating, GoalieRating
from GHLWebsiteApp.views import get_seasonSetting
from decimal import Decimal
from collections import defaultdict
from scipy.stats import rankdata

# Coefficient Maps (abbreviated for clarity)
OFFENSE_COEFF = {
    'goals': 20,
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
}
DEFENSE_CONSTANT = 15 # Constant for standardizing defense rating

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
    'possession_diff': 0.025,
    'constant': 30, # Constant for standardizing team play rating
}

GOALIE_COEFF = {
    'saves': 1,
    'goals_against': -4.25,
    'shots_against': 1.8,
    'shutouts': 45,
    'constant': 25, # Constant for standardizing goalie rating
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
    
    def clamp_0_100(self, x: Decimal) -> Decimal:
        return max(Decimal(0), min(Decimal(100), x))
    
    def _get_team_records_for_goalie(self, gr):
        """Return (team_record, opp_record) for this goalie game."""
        game = gr.game_num
        team = gr.ea_club_num
        team_rec = TeamRecord.objects.filter(game_num=game, ea_club_num=team).first()
        opp_team = game.h_team_num if team == game.a_team_num else game.a_team_num
        opp_rec = TeamRecord.objects.filter(game_num=game, ea_club_num=opp_team).first()
        return team_rec, opp_rec

    def _compute_teamplay_rating(self, team_rec, opp_rec):
        """Same formula you use for skaters’ teamplay_rating."""
        if not team_rec or not opp_rec:
            return Decimal(0)
        team = Decimal(
            team_rec.goals_for    * TEAMPLAY_COEFF['goals_for']   +
            team_rec.goals_against* TEAMPLAY_COEFF['goals_against'] +
            team_rec.sog_team     * TEAMPLAY_COEFF['shots_for']   +
            team_rec.ppg_team     * TEAMPLAY_COEFF['power_play']  +
            team_rec.shg_team     * TEAMPLAY_COEFF['penalty_kill']+
            TEAMPLAY_COEFF['constant']
        )
        # possession differential
        team += Decimal((team_rec.toa_team - (opp_rec.toa_team or 0)) * TEAMPLAY_COEFF['possession_diff'])
        return team

    def _result_bonus_for_game(self, our_team, game):
        gf, ga = (game.a_team_gf, game.h_team_gf) if our_team == game.a_team_num else (game.h_team_gf, game.a_team_gf)
        key = 'reg_win' if gf > ga and game.gamelength == 3600 else \
            'ot_win'  if gf > ga and game.gamelength and game.gamelength > 3600 else \
            'ot_loss' if gf < ga and game.gamelength and game.gamelength > 3600 else \
            'reg_loss'
        return Decimal(GAME_RESULT_COEFF[key])

    def get_opponent_sog(self, skater_record):
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
    
    def get_opponent_toa(self, skater_record):
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
        skater_count = 0
        force = options['force']
        allseasons = options['allseasons']
        thisseason = options['thisseason']

        if force:
            GameSkaterRating.objects.all().delete()
            GameGoalieRating.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted all existing ratings (forced recalc)."))
        if thisseason:
            GameSkaterRating.objects.filter(skater_record__game_num__season_num__isActive=True).delete()
            GameGoalieRating.objects.filter(goalie_record__game_num__season_num__isActive=True).delete()
            self.stdout.write(self.style.WARNING("Deleted all ratings for the current season (forced recalc)."))
            
        # STEP 1 : Calculate per-game skater ratings
        for skater in SkaterRecord.objects.exclude(position__positionShort="G").select_related('position', 'game_num', 'ea_club_num'):
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
            ]) + Decimal(DEFENSE_CONSTANT)
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
            team = Decimal(
                team_record.goals_for * TEAMPLAY_COEFF['goals_for'] +
                team_record.goals_against * TEAMPLAY_COEFF['goals_against'] +
                team_record.sog_team * TEAMPLAY_COEFF['shots_for'] +
                team_record.ppg_team * TEAMPLAY_COEFF['power_play'] +
                team_record.shg_team * TEAMPLAY_COEFF['penalty_kill'] +
                TEAMPLAY_COEFF['constant']
            )

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
            ovr = max(Decimal(0), min(Decimal(100), ovr))
            GameSkaterRating.objects.create(
                skater_record=skater,
                offense_rating=round(off, 2),
                defense_rating=round(defn, 2),
                teamplay_rating=round(team, 2),
                game_result_bonus=result_bonus,
                overall_rating=round(ovr, 2)
            )
            skater_count += 1
        self.stdout.write(f'Rated {skater_count} skater games.')

        goalie_count = 0
        goalies = GoalieRecord.objects.select_related('game_num', 'ea_club_num', 'ea_player_num')
        for gr in goalies:
            if GameGoalieRating.objects.filter(goalie_record=gr).exists():
                continue

            # --- goalie_rating (shot-stopping + workload + shutout + constant) ---
            saves_part          = Decimal(gr.saves or 0) * Decimal(GOALIE_COEFF['saves'])
            goals_against       = (gr.shots_against or 0) - (gr.saves or 0)
            goals_against_part  = Decimal(goals_against) * Decimal(GOALIE_COEFF['goals_against'])
            workload_part       = Decimal(gr.shots_against or 0) * Decimal(GOALIE_COEFF['shots_against'])
            shutout_part        = Decimal(1 if gr.shutout else 0) * Decimal(GOALIE_COEFF['shutouts'])
            constant_part       = Decimal(GOALIE_COEFF['constant'])

            goalie_rating = saves_part + goals_against_part + workload_part + shutout_part + constant_part

            # --- teamplay_rating (same as skaters) ---
            team_rec, opp_rec = self._get_team_records_for_goalie(gr)
            teamplay_rating = self._compute_teamplay_rating(team_rec, opp_rec)

            # --- game_result_bonus (same as skaters) ---
            game_result_bonus = self._result_bonus_for_game(gr.ea_club_num, gr.game_num)

            # --- overall (sum, clamped 0..100) ---
            overall_rating = self.clamp_0_100((Decimal(.9) * goalie_rating) + (Decimal(.1) * teamplay_rating) + game_result_bonus)

            GameGoalieRating.objects.create(
                goalie_record=gr,
                goalie_rating=round(goalie_rating, 2),
                teamplay_rating=round(teamplay_rating, 2),
                game_result_bonus=round(game_result_bonus, 2),
                overall_rating=round(overall_rating, 2),
            )
            goalie_count += 1

        self.stdout.write(f'Rated {goalie_count} goalie games.')
        
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

        goalie_ratings_map = defaultdict(list)
        for grating in GameGoalieRating.objects.select_related('goalie_record__game_num',
                                                            'goalie_record__ea_player_num'):
            gr = grating.goalie_record
            key = (gr.ea_player_num, gr.game_num.season_num)
            goalie_ratings_map[key].append(grating)

        for (player, season), ratings in goalie_ratings_map.items():
            games = len(ratings)
            gk_avg   = sum(r.goalie_rating   for r in ratings) / games if games else Decimal(0)
            team_avg = sum(r.teamplay_rating for r in ratings) / games if games else Decimal(0)
            ovr_avg  = sum(r.overall_rating  for r in ratings) / games if games else Decimal(0)

            GoalieRating.objects.update_or_create(
                player=player,
                season=season,
                weights_version="v1",
                defaults={
                    "games_played": games,
                    "gk_rat":   round(gk_avg,   2),
                    "team_rat": round(team_avg, 2),
                    "ovr_rat":  round(ovr_avg,  2),
                }
            )

        self.stdout.write(f'Aggregated ratings for {len(goalie_ratings_map)} goalie player-season combos.')
        
        # STEP 3 : Calculate percentiles for each position in each season
        def set_skater_percentiles_for_season(season_id):
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

        def set_goalie_percentiles_for_season(season_id):
            rows = list(GoalieRating.objects.filter(season=season_id, weights_version="v1"))
            if not rows:
                return

            def pct(arr):
                from scipy.stats import rankdata
                return rankdata(arr, method='average') / len(arr) * 100

            gk_arr   = [float(r.gk_rat)   for r in rows]
            team_arr = [float(r.team_rat) for r in rows]
            ovr_arr  = [float(r.ovr_rat)  for r in rows]

            gk_p   = pct(gk_arr)
            team_p = pct(team_arr)
            ovr_p  = pct(ovr_arr)

            for i, r in enumerate(rows):
                r.gk_pct   = round(gk_p[i],   2)
                r.team_pct = round(team_p[i], 2)
                r.ovr_pct  = round(ovr_p[i],  2)
                r.save(update_fields=["gk_pct", "team_pct", "ovr_pct"])


        # Call each season
        if allseasons:
            sk_seasons = SkaterRating.objects.values_list("season", flat=True).distinct()
            gk_seasons = GoalieRating.objects.values_list("season", flat=True).distinct()
            for s in set(list(sk_seasons) + list(gk_seasons)):
                set_skater_percentiles_for_season(s)
                set_goalie_percentiles_for_season(s)
            self.stdout.write('Percentiles calculated for all seasons (skaters & goalies).')
        else:
            season_id = get_seasonSetting()
            set_skater_percentiles_for_season(season_id)
            set_goalie_percentiles_for_season(season_id)
            self.stdout.write(f'Percentiles calculated for Season ID {season_id} (skaters & goalies).')


        # STEP 4 : Remove Goalie Games
        gameskaterratingcount = skaterratingcount = 0
        for rating in GameSkaterRating.objects.filter(skater_record__position=0):
            gameskaterratingcount += 1
            rating.delete()
        if gameskaterratingcount > 0:
            self.stdout.write(f'Removed {gameskaterratingcount} inadvertently calculated skater-as-goalie game ratings.')
        for rating in SkaterRating.objects.filter(position=0):
            skaterratingcount += 1
            rating.delete()
        if skaterratingcount > 0:
            self.stdout.write(f'Removed {skaterratingcount} inadvertently calculated skater-as-goalie positional ratings.')

        self.stdout.write(self.style.SUCCESS('Ratings update complete!'))
