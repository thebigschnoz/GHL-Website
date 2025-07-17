from decimal import Decimal
from collections import defaultdict
from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, F, Window, DecimalField
from django.db.models.functions import Rank, Coalesce, Cast
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
        buckets = defaultdict(list)           # {pos_id: [row, …]}

        qs = (SkaterWAR.objects
            .filter(season=season)
            .select_related("position")     # avoids extra queries
            .only("id", "position", "games_played",
                    *(c for c, _ in COMPONENTS)))  # load just the needed fields

        for row in qs:
            buckets[row.position_id].append(row)

        # ②  loop over every component
        for comp, pct_field in COMPONENTS:

            # Which positions to include?
            positions = [CENTER_POS] if comp == "gar_faceoffs" else buckets.keys()

            for pos in positions:
                cohort = buckets.get(pos, [])
                if not cohort:
                    continue

                # --- build a list of (rate, row) ---
                with_rates = [
                    (row.__dict__[comp] / row.games_played if row.games_played else Decimal("0"), row)
                    for row in cohort
                ]

                # sort ascending: lowest value => 0th percentile
                with_rates.sort(key=lambda tup: tup[0])

                # inclusive percentile
                n = len(with_rates)
                i = 0
                while i < n:
                    j = i
                    # group ties so they share a percentile
                    while j < n and with_rates[j][0] == with_rates[i][0]:
                        j += 1
                    pct = (Decimal(j) / Decimal(n) * 100).quantize(Decimal("0.01"))
                    for _, row in with_rates[i:j]:
                        setattr(row, pct_field, pct)
                    i = j

            # --- blank face-off pct for non-centres ---
            if comp == "gar_faceoffs":
                for pos, cohort in buckets.items():
                    if pos == CENTER_POS:
                        continue
                    for row in cohort:
                        row.gar_faceoffs_pct = None

        # ③  one bulk update per field – fastest on SQLite
        #    (could also bulk_update once per COMPONENTS batch)
        fields_to_update = [pct for _, pct in COMPONENTS]
        with transaction.atomic():
            for pos_rows in buckets.values():
                SkaterWAR.objects.bulk_update(pos_rows, fields_to_update)


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
        self.stdout.write(self.style.SUCCESS(f"Found {qs.count()} skater records for season {season.season_text}."))
        rep_baseline = {}          # {pos_id: GAR_per_game_for_replacement}
        for pos_id in qs.values_list('position', flat=True).distinct():
            rep_pool = (qs.filter(position=pos_id)
                        .order_by('gp')[: max(1, qs.filter(position=pos_id)
                                                    .count() // 5)])  # bottom-20 %
            rep_events = sum(
                ((row['goals']   * LINEAR_WEIGHTS['goal'])   +
                (row['assists'] * LINEAR_WEIGHTS['assist']) +
                (row['shots']   * LINEAR_WEIGHTS['shot_attempt']) +
                (row['takeaways']*LINEAR_WEIGHTS['takeaway']) +
                (row['blocks']  * LINEAR_WEIGHTS['blocked_shot']))
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

            SkaterWAR.objects.update_or_create(
                player_id   = row['ea_player_num'],
                position_id = row['position'],
                season      = season,
                defaults    = dict(
                    games_played   = row['gp'],
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
        self.stdout.write(f"GAR and WAR totals successfully computed for {qs.count()} skater records.")
        positions = Position.objects.values_list('ea_pos', flat=True)  # get all position IDs
        for pos in positions:
            cohort = (SkaterWAR.objects
                    .filter(season=season, position=pos)
                    .annotate(
                        war_rate = F('war') / Cast('games_played', DecimalField())
                    )
                    .order_by('war_rate'))              # ascending = worst → best

            n = cohort.count()
            for i, sk in enumerate(cohort, start=1):
                pct = (Decimal(i) / Decimal(n)) * 100
                sk.war_percentile = pct.quantize(Decimal('0.01'))
            SkaterWAR.objects.bulk_update(cohort, ['war_percentile'])
        self.stdout.write(f"WAR percentiles updated for {qs.count()} skater records.")

        self.assign_percentiles(season)
        self.stdout.write(self.style.SUCCESS("WAR update completed!"))

    
