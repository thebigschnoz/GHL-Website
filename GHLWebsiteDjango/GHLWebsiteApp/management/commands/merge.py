from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.models import *
import pandas as pd
from django.db.models import Model
from django.db.models.fields import Field

class Command(BaseCommand):
    help = "Merge two or more games together"

    def add_arguments(self, parser):
        parser.add_argument("game_num", type=int, help="The game number to merge into")
        parser.add_argument("merge_game_num", type=int, help="The game number to merge into the game_num")
    
    def handle(self, *args, **options):
        game_num = options["game_num"]
        merge_game_num = options["merge_game_num"]
        try:
            survivor_game = Game.objects.get(game_num=game_num)
            merge_game = Game.objects.get(game_num=merge_game_num)
        except Game.DoesNotExist:
            raise CommandError("One or both of the specified games do not exist.")

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
                    
                    # Handle other field types as needed (e.g., ForeignKey, ManyToManyField)
                    # Add custom logic here if necessary

        survivor_game.save() # Save the updated survivor_game
        merge_game.delete() # Delete the merged game

        self.stdout.write(self.style.SUCCESS(f"Successfully merged game {merge_game_num} into game {game_num}."))