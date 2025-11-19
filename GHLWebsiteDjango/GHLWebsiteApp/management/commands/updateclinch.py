from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.playoff_sim import get_active_season, update_playoff_flags_from_odds

class Command(BaseCommand):
    help = "Run Monte Carlo simulation to update playoff odds and clinching flags."

    def add_arguments(self, parser):
        parser.add_argument("--iterations", type=int, default=5000)

    def handle(self, *args, **options):
        try:
            season = get_active_season()
        except ValueError as e:
            # Active season missing or wrong type (not 'regular')
            raise CommandError(str(e))
        iterations = options["iterations"]
        self.stdout.write(f"Running playoff simulation for {season} with {iterations} iterations...")
        try:
            update_playoff_flags_from_odds(season, iterations=iterations)
        except ValueError as e:
            # Missing playoff config, etc.
            raise CommandError(str(e))
        self.stdout.write("Done.")
