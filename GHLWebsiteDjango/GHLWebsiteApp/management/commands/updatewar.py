from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, F, Window
from django.db.models.functions import Rank, Coalesce
from GHLWebsiteApp.models import SkaterWAR, SkaterRecord, Season, Position

LINEAR_WEIGHTS = {
    "goal"             : Decimal("1.00"),
    "assist"           : Decimal("0.70"),
    "shot_attempt"     : Decimal("0.03"),
    "takeaway"         : Decimal("0.05"),
    "blocked_shot"     : Decimal("0.03"),
    "pen_drawn"        : Decimal("0.19"),
    "pen_taken"        : Decimal("-0.19"),
    "faceoff_win"      : Decimal("0.015")  # per win ≈ 3-sec OZ possession
}

COMPONENTS = [
    ("gar_offence",   "gar_offence_pct"),
    ("gar_defence",   "gar_defence_pct"),
    ("gar_turnover",  "gar_turnover_pct"),
    ("gar_penalties", "gar_penalties_pct"),
    ("gar_faceoffs",  "gar_faceoffs_pct"),
    ("war",           "war_percentile"),          # keeps WAR% fresh too
]

G_PER_WIN = Decimal("5.2976")                 # compute once per league via logistic model

CENTER_POS = 5   # EA enum for centres

class Command(BaseCommand):
    help = "Re/compute WAR for every player-season"

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            help="The season number to compute WAR for. Defaults to the active season if not provided."
        )

    def assign_percentiles(self, season):
        for comp, pct_field in COMPONENTS:
            # Filter by position (only centers for faceoff)
            if comp == "gar_faceoffs":
                positions_to_rank = [CENTER_POS]
            else:
                positions_to_rank = SkaterWAR.objects.filter(season=season).values_list('position', flat=True).distinct()

            for pos in positions_to_rank:
                cohort = (SkaterWAR.objects
                        .filter(season=season, position=pos)
                        .order_by(comp))  # ascending

                total = cohort.count()
                updates = []
                for i, sk in enumerate(cohort, start=1):
                    percentile = (Decimal(i) / Decimal(total)) * 100
                    setattr(sk, pct_field, percentile.quantize(Decimal("0.01")))
                    updates.append(sk)

                SkaterWAR.objects.bulk_update(updates, [pct_field])

            # Nullify faceoff percentiles for non-centres
            if comp == "gar_faceoffs":
                SkaterWAR.objects.filter(
                    season=season
                ).exclude(position=CENTER_POS).update(gar_faceoffs_pct=None)


    def handle(self, *args, **options):
        season_num = options.get('season')
        if season_num:
            try:
                season = Season.objects.get(season_num=season_num)
            except Season.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Season with season_num {season_num} does not exist!"))
                return
            self.stdout.write(self.style.SUCCESS(f"Using specified season: {season.season_text}"))
        else:
            season = Season.objects.get(isActive=True)  # Default to active season
            self.stdout.write(self.style.SUCCESS(f"Using active season: {season.season_text}"))

        if not season:
            self.stdout.write(self.style.ERROR("No active season found! WAR cannot be computed."))
            return
        if season.season_type != 'regular':
            self.stdout.write(self.style.ERROR("WAR can only be computed for regular seasons."))
            return

        qs = (SkaterRecord.objects
            .filter(game_num__season_num=season)
            .values('ea_player_num', 'position', 'game_num__gamelength')
            .exclude(position=0)   # group by player and position
            .annotate(
                gp          = Count('game_num', distinct=True),
                goals       = Coalesce(Sum('goals'), 0),
                assists     = Coalesce(Sum('assists'), 0),
                shots       = Coalesce(Sum('shot_attempts'), 0),
                takeaways   = Coalesce(Sum('takeaways'), 0),
                blocks      = Coalesce(Sum('blocked_shots'), 0),
                pen_drawn   = Coalesce(Sum('pens_drawn'), 0),
                pen_taken   = Coalesce(Sum('pims'), 0),
                fow         = Coalesce(Sum('fow'), 0),
                fol         = Coalesce(Sum('fol'), 0),
            )
        )
        rep_baseline = {}          # {pos_id: GAR_per_game_for_replacement}
        for pos_id in qs.values_list('position', flat=True).distinct():
            rep_pool = (qs.filter(position=pos_id)
                        .order_by('gp')[: max(1, qs.filter(position=pos_id)
                                                    .count() // 5)])  # bottom-20 %
            rep_events = sum(
                (row['goals']   * LINEAR_WEIGHTS['goal']   +
                row['assists'] * LINEAR_WEIGHTS['assist'] +
                row['shots']   * LINEAR_WEIGHTS['shot_attempt'] +
                row['takeaways']*LINEAR_WEIGHTS['takeaway'] +
                row['blocks']  * LINEAR_WEIGHTS['blocked_shot'])
                for row in rep_pool
            )
            rep_games  = sum(row['gp'] for row in rep_pool) or 1
            rep_baseline[pos_id] = Decimal(rep_events) / Decimal(rep_games)   # **per game**
        # replacement level = bottom 20 % of TOI at position
        subquery = qs.annotate(
                        rank=Window(
                            expression=Rank(),
                            order_by=F('gp').asc()
                        )
                    )

        total_players = subquery.count()
        replacement_cut = int(total_players * 0.2)

        rep_pool = subquery.filter(rank__lte=replacement_cut)

        # average GAR/60 for replacement skaters
        rep_gar60 = (rep_pool.aggregate(rep=Sum(
                        (F('goals')   * LINEAR_WEIGHTS['goal'])   +
                        (F('assists') * LINEAR_WEIGHTS['assist']) +
                        (F('shots')   * LINEAR_WEIGHTS['shot_attempt'])   +
                        (F('takeaways') * LINEAR_WEIGHTS['takeaway'])     +
                        (F('blocks')    * LINEAR_WEIGHTS['blocked_shot'])
                    ))['rep'] or 0) / (rep_pool.aggregate(gp=Sum('gp'))['gp'] or 1)

        for row in qs:
            gar = (
                (row['goals']   * LINEAR_WEIGHTS['goal'])   +
                (row['assists'] * LINEAR_WEIGHTS['assist']) +
                (row['shots']   * LINEAR_WEIGHTS['shot_attempt'])   +
                (row['takeaways'] * LINEAR_WEIGHTS['takeaway'])     +
                (row['blocks']    * LINEAR_WEIGHTS['blocked_shot']) +
                (row['pen_drawn'] * LINEAR_WEIGHTS['pen_drawn'])    +
                (row['pen_taken'] * LINEAR_WEIGHTS['pen_taken'])    +
                ((row['fow'] - row['fol']) * LINEAR_WEIGHTS['faceoff_win'])
            )
            print(f"Computed GAR for player {row['ea_player_num']} as {row['position']}: {gar:.2f}")

            gar_off = (row['goals'] * LINEAR_WEIGHTS['goal']) + (row['assists'] * LINEAR_WEIGHTS['assist'])
            gar_def = (row['blocks'] * LINEAR_WEIGHTS['blocked_shot'])
            gar_turn= (row['takeaways'] * LINEAR_WEIGHTS['takeaway']) + (row['shots'] * LINEAR_WEIGHTS['shot_attempt'])
            gar_pen = (row['pen_drawn'] * LINEAR_WEIGHTS['pen_drawn']) + (row['pen_taken'] * LINEAR_WEIGHTS['pen_taken'])
            rep_per_game = rep_baseline[row['position']]
            if row['position'] == CENTER_POS:
                gar_fo = (row['fow'] - row['fol']) * LINEAR_WEIGHTS['faceoff_win']
            else:
                gar_fo = Decimal("0")          # keeps WAR math correct

            gar_above_rep = gar - rep_per_game * row['gp']
            if gar_above_rep.is_nan():
                gar_above_rep = Decimal("0.0")
            war = gar_above_rep / G_PER_WIN
            print(f"Computed WAR for player {row['ea_player_num']} as {row['position']}: {war:.2f}")

            SkaterWAR.objects.update_or_create(
                player_id   = row['ea_player_num'],
                position_id = row['position'],
                season      = season,
                defaults    = dict(
                    position_id   = row['position'],
                    gar_offence   = gar_off,
                    gar_defence   = gar_def,
                    gar_turnover  = gar_turn,
                    gar_penalties = gar_pen,
                    gar_faceoffs  = gar_fo,
                    gar_total     = gar_above_rep,
                    war           = war,
                    weights_version="v1"
                )
            )
        positions = Position.objects.values_list('ea_pos', flat=True)  # get all position IDs
        for pos in positions:                                  # loop once per position
            cohort = (SkaterWAR.objects
                    .filter(season=season, position=pos)
                    .order_by('war'))                        # ascending

            n = cohort.count()
            for i, skater in enumerate(cohort, start=1):
                pct = (Decimal(i) / Decimal(n)) * 100          # Inclusive style
                skater.war_percentile = pct.quantize(Decimal('0.01'))
            SkaterWAR.objects.bulk_update(cohort, ['war_percentile'])

        self.assign_percentiles(season)
        self.stdout.write(self.style.SUCCESS("WAR update completed!"))

    
