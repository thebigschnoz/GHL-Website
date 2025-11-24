from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.playoff_sim import get_active_season, update_playoff_flags_from_odds
from GHLWebsiteApp.models import Game
import datetime
from django.utils import timezone
from zoneinfo import ZoneInfo


class Command(BaseCommand):
    help = "Run Monte Carlo simulation to update playoff odds and clinching flags."

    def add_arguments(self, parser):
        parser.add_argument("--iterations", type=int, default=5000)
        parser.add_argument("--gameplayed", action="store_true", help="Only run if at least one game was played yesterday in the active regular season.")

    def handle(self, *args, **options):
        print(f"[updateclinch] Starting run at {datetime.datetime.utcnow().isoformat()}Z")
        gameplayed = options["gameplayed"]
        try:
            season = get_active_season()
        except ValueError as e:
            # Active season missing or wrong type (not 'regular')
            raise CommandError(str(e))
        if gameplayed:
            # Define the 24h window in EST, then convert to UTC for DB lookup
            eastern = ZoneInfo("America/New_York")
            now_est = timezone.now().astimezone(eastern)
            start_est = now_est - datetime.timedelta(hours=24)

            # Convert back to UTC-aware datetimes for filtering
            # (Django stores datetimes in UTC by default)
            start_utc = start_est.astimezone(datetime.timezone.utc)
            now_utc = now_est.astimezone(datetime.timezone.utc)

            had_games = Game.objects.filter(
                season_num=season,
                played_time__gte=start_utc,
                played_time__lte=now_utc,
            ).exists()

            if not had_games:
                self.stdout.write(
                    "[updateclinch] No games played in the last 24 hours for "
                    f"season '{season.season_text}'. Skipping playoff simulation."
                )
                return

            self.stdout.write(
                "[updateclinch] Detected games played in the last 24 hours for "
                f"season '{season.season_text}'. Running playoff simulation..."
            )
        iterations = options["iterations"]
        self.stdout.write(f"Running playoff simulation for {season} with {iterations} iterations...")
        try:
            update_playoff_flags_from_odds(season, iterations=iterations)
        except ValueError as e:
            # Missing playoff config, etc.
            raise CommandError(str(e))
        self.stdout.write("Done.")
