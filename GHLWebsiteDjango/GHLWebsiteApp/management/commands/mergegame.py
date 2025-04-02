from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.models import *
from django.db.models import Model
from django.db.models.fields import Field
from ...views import calculate_leaders, calculate_standings

class Command(BaseCommand):
    help = "Merge two or more games together"

    def add_arguments(self, parser):
        parser.add_argument("game_num", type=int, help="The game number to merge into")
        parser.add_argument("merge_game_num", type=int, help="The game number to merge into the game_num")
    
    def handle(self, *args, **options):
        game_num = options["game_num"]
        merge_game_num = options["merge_game_num"]
        self.stdout.write(f"Merging game {merge_game_num} into game {game_num}...")
        try:
            survivor_game = Game.objects.get(game_num=game_num)
            merge_game = Game.objects.get(game_num=merge_game_num)
        except Game.DoesNotExist:
            raise CommandError("One or both of the specified games do not exist.")

        if survivor_game.expected_time == None:
            survivor_game.expected_time = merge_game.expected_time
        if survivor_game.played_time == None:
            survivor_game.played_time = merge_game.played_time
        if survivor_game.dnf == False or merge_game.dnf == False:
            survivor_game.dnf = False

        # Iterate through fields and merge attributes
        for field in Game._meta.get_fields():
            if isinstance(field, Field) and not field.auto_created:
                field_name = field.name
                if hasattr(survivor_game, field_name) and hasattr(merge_game, field_name):
                    survivor_value = getattr(survivor_game, field_name)
                    merge_value = getattr(merge_game, field_name)

                    # Handle numeric fields
                    if isinstance(survivor_value, (int, float)) and isinstance(merge_value, (int, float)):
                        setattr(survivor_game, field_name, survivor_value + merge_value)
                    
                    # Handle string fields (concatenate or choose one)
                    elif isinstance(survivor_value, str) and isinstance(merge_value, str):
                        setattr(survivor_game, field_name, f"{survivor_value} {merge_value}".strip())
                    
        # Merge all TeamRecords, Skater Records, and GameRecords from merge_game into survivor_game

        # Find matching TeamRecords by game_num
        teamrecordlist_survivor = TeamRecord.objects.filter(game_num=survivor_game.game_num) #  The TeamRecords from the survivor game
        teamrecordlist_merge = TeamRecord.objects.filter(game_num=merge_game.game_num) #  The TeamRecords from the merge game

        for record in teamrecordlist_merge: #  For each of the TeamRecords from the merged game...
            survivor_team = teamrecordlist_survivor.filter(ea_club_num=record.ea_club_num).first() #  ...find the corresponding TeamRecord in the survivor game
            if survivor_team.exists():
                for field in TeamRecord._meta.get_fields():
                    if isinstance(field, Field) and not field.auto_created:
                        field_name = field.name
                        survivor_value = getattr(survivor_team, field_name, None)
                        merge_value = getattr(record, field_name, None)

                        # Handle DNF field
                        if field_name == "dnf":
                            setattr(survivor_team, field_name, survivor_value or merge_value)
                            continue
                        # Add all integer fields together
                        elif isinstance(survivor_value, (int, float)) and isinstance(merge_value, (int, float)):
                            setattr(survivor_team, field_name, survivor_value + merge_value)

                survivor_team.save()  # Save the survivor teamrecord
                record.delete()  # Delete the merged teamrecord
            else:
                # If no matching survivor_team exists, reassign the record to survivor_game
                record.game_num = survivor_game
                record.save()
                self.stdout.write(self.style.WARNING(f"TeamRecord {record.ea_club_num} from game {merge_game_num} was not found in game {game_num}. Reassigned to game {game_num}."))
        
        # Find matching SkaterRecords by game_num 
        skaterlist_survivor = SkaterRecord.objects.filter(game_num=survivor_game.game_num)
        skaterlist_merge = SkaterRecord.objects.filter(game_num=merge_game.game_num)

        for merge_skater in skaterlist_merge:
            # Match SkaterRecords by ea_player_num
            survivor_skater = skaterlist_survivor.filter(ea_player_num=merge_skater.ea_player_num).first()
            if survivor_skater:
                # Add all integer fields together
                for field in SkaterRecord._meta.get_fields():
                    if isinstance(field, Field) and not field.auto_created:
                        field_name = field.name
                        survivor_value = getattr(survivor_skater, field_name, None)
                        merge_value = getattr(merge_skater, field_name, None)

                        # Handle numeric fields
                        if isinstance(survivor_value, (int, float)) and isinstance(merge_value, (int, float)):
                            setattr(survivor_skater, field_name, survivor_value + merge_value)

                survivor_skater.save()  # Save the survivor skater
                merge_skater.delete()  # Delete the merged skater
            else:
                # If no matching survivor_skater exists, reassign the merge_skater to survivor_game
                merge_skater.game_num = survivor_game
                merge_skater.save()
                self.stdout.write(self.style.WARNING(f"SkaterRecord {merge_skater.ea_player_num} from game {merge_game_num} was not found in game {game_num}. Reassigned to game {game_num}."))

        # Find matching SkaterRecords by game_num 
        goalielist_survivor = GoalieRecord.objects.filter(game_num=survivor_game.game_num)
        goalielist_merge = GoalieRecord.objects.filter(game_num=merge_game.game_num)

        for merge_goalie in goalielist_merge:
            # Match GoalieRecords by ea_player_num
            survivor_goalie = goalielist_survivor.filter(ea_player_num=merge_goalie.ea_player_num).first()
            if survivor_goalie:
                # Add all integer fields together
                for field in GoalieRecord._meta.get_fields():
                    if isinstance(field, Field) and not field.auto_created:
                        field_name = field.name
                        survivor_value = getattr(survivor_skater, field_name, None)
                        merge_value = getattr(merge_skater, field_name, None)

                        # Handle numeric fields
                        if isinstance(survivor_value, (int, float)) and isinstance(merge_value, (int, float)):
                            setattr(survivor_skater, field_name, survivor_value + merge_value)

                survivor_goalie.save()  # Save the survivor skater
                merge_goalie.delete()  # Delete the merged skater
            else:
                # If no matching survivor_skater exists, reassign the merge_skater to survivor_game
                merge_goalie.game_num = survivor_game
                merge_goalie.save()
                self.stdout.write(self.style.WARNING(f"GoalieRecord {merge_goalie.ea_player_num} from game {merge_game_num} was not found in game {game_num}. Reassigned to game {game_num}."))

        survivor_game.save() # Save the survivor game
        merge_game.delete() # Delete the merged game

        self.stdout.write(self.style.SUCCESS(f"Successfully merged game {merge_game_num} into game {game_num}."))
        calculate_leaders()
        calculate_standings()
        self.stdout.write(self.style.SUCCESS("Leaders and standings refreshed."))