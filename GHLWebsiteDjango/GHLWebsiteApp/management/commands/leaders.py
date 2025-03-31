from django.core.management.base import BaseCommand, CommandError
from views import calculate_leaders, calculate_standings

class Command(BaseCommand):
    help = "Refresh leaderboards and standings"

    def handle(self, *args, **options):
        calculate_leaders()
        calculate_standings()
        self.stdout.write(self.style.SUCCESS("Leaders and standings refreshed"))