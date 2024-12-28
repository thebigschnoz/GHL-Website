from django.contrib import admin

from .models import Seasons, Games, AwardsList, TeamList, PlayerList, Positions, Builds, Awards, SkaterRecords, GoalieRecords, TeamRecords

# Register your models here.
class TeamListAdmin(admin.ModelAdmin):
    list_display = ("club_full_name", "ea_club_num", "club_abbr", "team_logo_link")

class BuildsAdmin(admin.ModelAdmin):
    list_display = ("build", "buildShort")

class PlayerListAdmin(admin.ModelAdmin):
    list_display = ("username", "current_team")

class SeasonsAdmin(admin.ModelAdmin):
    list_display = ("season_text", "season_num", "isPlayoff")

admin.site.register(Seasons, SeasonsAdmin)
admin.site.register(Games)
admin.site.register(AwardsList)
admin.site.register(TeamList, TeamListAdmin)
admin.site.register(PlayerList, PlayerListAdmin)
admin.site.register(Positions)
admin.site.register(Builds, BuildsAdmin)
admin.site.register(Awards)
admin.site.register(SkaterRecords)
admin.site.register(GoalieRecords)
admin.site.register(TeamRecords)