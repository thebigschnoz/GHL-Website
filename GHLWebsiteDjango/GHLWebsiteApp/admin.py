from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.core.management import call_command
from django.urls import reverse
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from .models import *

class CustomAdminSite(AdminSite):
    site_header = "GHL Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-poll-api/', self.admin_view(self.run_poll_api), name='run_poll_api'),
        ]
        return custom_urls + urls

    def run_poll_api(self, request):
        try:
            # Call the management command
            call_command('poll_api')
            messages.success(request, "Poll API command executed successfully!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return HttpResponseRedirect(reverse('custom_admin:index'))

# Register the custom admin site
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register your models here.
class TeamListAdmin(admin.ModelAdmin):
    list_display = ("club_full_name", "ea_club_num", "club_abbr", "isActive", "team_color", "team_code")
    list_filter = ("isActive",)

class BuildsAdmin(admin.ModelAdmin):
    list_display = ("build", "buildShort")

class PlayerListAdmin(admin.ModelAdmin):
    list_display = ("username", "current_team__club_full_name")

class SeasonsAdmin(admin.ModelAdmin):
    list_display = ("season_text", "start_date", "season_type", "season_num", "isActive")

class GameAdmin(admin.ModelAdmin):
    list_display = ("game_num", "season_num__season_text", "gamelength", "a_team_num__club_abbr", "h_team_num__club_abbr", "expected_time", "played_time", "dnf")
    list_filter = ("season_num__season_text", "dnf")
    actions = ["merge_games"]

    def merge_games(self, request, queryset):
        # Ensure exactly two games are selected
        if queryset.count() != 2:
            messages.error(request, "Please select exactly two games to merge.")
            return

        # Get the game numbers
        games = list(queryset.order_by("game_num"))
        game_num = games[0].game_num
        merge_game_num = games[1].game_num

        try:
            # Call the mergegame management command
            call_command("mergegame", game_num=game_num, merge_game_num=merge_game_num)
            messages.success(request, f"Successfully merged game {merge_game_num} into game {game_num}.")
        except Exception as e:
            messages.error(request, f"Error during merge: {str(e)}")

    merge_games.short_description = "Merge selected games (order matters: first into second)"

class SkaterRecordAdmin(admin.ModelAdmin):
    list_display = ("ea_player_num__username", "game_num__game_num", "game_num__played_time")
    list_filter = ("game_num__season_num__season_text", "ea_club_num__club_abbr", "game_num__played_time", "game_num__expected_time")
    search_fields = ("ea_player_num__username", "game_num__game_num")

class GoalieRecordAdmin(admin.ModelAdmin):
    list_display = ("ea_player_num__username", "game_num__game_num", "game_num__played_time")
    list_filter = ("game_num__season_num__season_text", "ea_club_num__club_abbr", "game_num__played_time", "game_num__expected_time")
    search_fields = ("ea_player_num__username", "game_num__game_num")

class AwardAssignAdmin(admin.ModelAdmin):
    filter_horizontal = ("players",)

class PlayoffRoundAdmin(admin.ModelAdmin):
    list_display = ("round_name", "season", "round_num")

class PlayoffSeriesAdmin(admin.ModelAdmin):
    list_display = ("season__season_text", "low_seed__club_abbr", "high_seed__club_abbr")
    list_filter = ("season__season_text",)

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("schedule_num", "season_num", "start_date")
    actions = ["run_scheduler"]
    
    def run_scheduler(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, "Please select exactly one schedule to run.")
            return

        schedule = queryset[0]
        try: 
            call_command("createschedule", schedule_id=schedule)
            messages.success(request, f"Schedule {schedule} has been successfully run.")
        except Exception as e:
            messages.error(request, f"Error running schedule: {str(e)}")

    run_scheduler.short_description = "Run selected schedule"

custom_admin_site.register(Season, SeasonsAdmin)
custom_admin_site.register(Game, GameAdmin)
custom_admin_site.register(AwardTitle)
custom_admin_site.register(Team, TeamListAdmin)
custom_admin_site.register(Player, PlayerListAdmin)
custom_admin_site.register(Position)
custom_admin_site.register(Build, BuildsAdmin)
custom_admin_site.register(AwardAssign, AwardAssignAdmin)
custom_admin_site.register(SkaterRecord, SkaterRecordAdmin)
custom_admin_site.register(GoalieRecord, GoalieRecordAdmin)
custom_admin_site.register(TeamRecord)
custom_admin_site.register(Standing)
custom_admin_site.register(Leader)
custom_admin_site.register(AwardVote)
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group, GroupAdmin)
custom_admin_site.register(PlayoffRound, PlayoffRoundAdmin)
custom_admin_site.register(PlayoffSeries, PlayoffSeriesAdmin)
custom_admin_site.register(Schedule, ScheduleAdmin)
