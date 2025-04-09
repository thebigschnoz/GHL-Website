from django.contrib import admin

from .models import *

# Register your models here.
class TeamListAdmin(admin.ModelAdmin):
    list_display = ("club_full_name", "ea_club_num", "club_abbr", "isActive")

class BuildsAdmin(admin.ModelAdmin):
    list_display = ("build", "buildShort")

class PlayerListAdmin(admin.ModelAdmin):
    list_display = ("username", "current_team__club_full_name")

class SeasonsAdmin(admin.ModelAdmin):
    list_display = ("season_text", "season_num", "isPlayoff")

class GameAdmin(admin.ModelAdmin):
    list_display = ("game_num", "season_num__season_text", "gamelength", "a_team_num__club_abbr", "h_team_num__club_abbr", "expected_time", "played_time", "dnf")
    list_filter = ("season_num__season_text", "dnf")
    search_fields = ("game_num")

class SkaterRecordAdmin(admin.ModelAdmin):
    list_display = ("ea_player_num__username", "game_num__game_num", "game_num__played_time")
    list_filter = ("game_num__season_num__season_text", "game_num__a_team_num", "game_num__h_team_num", "game_num__played_time", "game_num__expected_time")
    search_fields = ("ea_player_num__username", "game_num__game_num")

class GoalieRecordAdmin(admin.ModelAdmin):
    list_display = ("ea_player_num__username", "game_num__game_num", "game_num__played_time")
    list_filter = ("game_num__season_num__season_text", "game_num__a_team_num__club_abbr", "game_num__h_team_num__club_abbr", "game_num__played_time", "game_num__expected_time")
    search_fields = ("ea_player_num__username", "game_num__game_num")

admin.site.register(Season, SeasonsAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(AwardTitle)
admin.site.register(Team, TeamListAdmin)
admin.site.register(Player, PlayerListAdmin)
admin.site.register(Position)
admin.site.register(Build, BuildsAdmin)
admin.site.register(AwardAssign)
admin.site.register(SkaterRecord, SkaterRecordAdmin)
admin.site.register(GoalieRecord, GoalieRecordAdmin)
admin.site.register(TeamRecord)
admin.site.register(Standing)
admin.site.register(Leader)