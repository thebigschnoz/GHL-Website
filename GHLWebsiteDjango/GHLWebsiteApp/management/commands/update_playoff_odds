from django.core.management.base import BaseCommand
from GHLWebsiteApp.playoff_sim import get_active_season, update_playoff_flags_from_odds

class Command(BaseCommand):
    help = "Run Monte Carlo simulation to update playoff odds and clinching flags."

    def add_arguments(self, parser):
        parser.add_argument("--iterations", type=int, default=5000)

    def handle(self, *args, **options):
        season = get_active_season()
        iterations = options["iterations"]
        self.stdout.write(f"Running playoff simulation for {season} with {iterations} iterations...")
        update_playoff_flags_from_odds(season, iterations=iterations)
        self.stdout.write("Done.")
