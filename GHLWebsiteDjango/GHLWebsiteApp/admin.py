from django.contrib import admin

from .models import *

# Register your models here.
class TeamListAdmin(admin.ModelAdmin):
    list_display = ("club_full_name", "ea_club_num", "club_abbr", "isActive", "team_logo_link")

class BuildsAdmin(admin.ModelAdmin):
    list_display = ("build", "buildShort")

class PlayerListAdmin(admin.ModelAdmin):
    list_display = ("username", "current_team")

class SeasonsAdmin(admin.ModelAdmin):
    list_display = ("season_text", "season_num", "isPlayoff")

class GameAdmin(admin.ModelAdmin):
    list_display = ("game_num", "season_num", "gamelength", "expected_time", "played_time")

admin.site.register(Season, SeasonsAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(AwardTitle)
admin.site.register(Team, TeamListAdmin)
admin.site.register(Player, PlayerListAdmin)
admin.site.register(Position)
admin.site.register(Build, BuildsAdmin)
admin.site.register(AwardAssign)
admin.site.register(SkaterRecord)
admin.site.register(GoalieRecord)
admin.site.register(TeamRecord)
admin.site.register(Standing)