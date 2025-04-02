from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.models import *

# Home is 0 and Away is 1

class Command(BaseCommand):
    help = "Swap home and away teams"

    def add_arguments(self, parser):
        parser.add_argument("game_num", type=int, help="The game number to swap teams for")

    def handle(self, *args, **options):
        game = Game.objects.filter(game_num=options["game_num"]).first()
        if not game:
            raise CommandError("Game not found")
        self.stdout.write(f"Swapping home and away teams for game {game.game_num}...")

        # Swap teams
        old_home = Team.objects.get(ea_club_num=game.h_team_num.ea_club_num)
        old_away = Team.objects.get(ea_club_num=game.a_team_num.ea_club_num)
        game.h_team_num = old_away
        game.a_team_num = old_home

        # Swap a_team_gf and h_team_gf
        old_home_gf = game.h_team_gf
        old_away_gf = game.a_team_gf
        game.h_team_gf = old_away_gf
        game.a_team_gf = old_home_gf

        # Swap TeamRecords' home_away values
        old_home_record = TeamRecord.objects.filter(game_num=game.game_num, ea_club_num=old_home.ea_club_num).first()
        old_away_record = TeamRecord.objects.filter(game_num=game.game_num, ea_club_num=old_away.ea_club_num).first()
        if old_home_record.home_away == 0:
            old_home_record.home_away = 1
        else:
            old_home_record.home_away = 0
        if old_away_record.home_away == 0:
            old_away_record.home_away = 1
        else:
            old_away_record.home_away = 0
        
        # Save changes
        game.save()
        old_home_record.save()
        old_away_record.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully swapped home and away teams for game {game.game_num}"))