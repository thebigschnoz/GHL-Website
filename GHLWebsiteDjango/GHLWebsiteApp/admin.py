from django import forms
from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.core.management import call_command
from django.urls import reverse
from django.contrib import messages
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.utils.html import format_html
from .models import User
from django.contrib.contenttypes.models import ContentType

from .models import *

class CustomAdminSite(AdminSite):
    site_header = "GHL Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-poll-api/', self.admin_view(self.run_poll_api), name='run_poll_api'),
            path('run-leaders/', self.admin_view(self.run_leaders), name='run_leaders'),
        ]
        return custom_urls + urls

    def run_poll_api(self, request):
        try:
            # Call the management command
            call_command('poll_api', force=True)
            messages.success(request, "Poll API command executed successfully!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return HttpResponseRedirect(reverse('custom_admin:index'))
    
    def run_leaders(self, request):
        try:
            call_command('leaders')
            messages.success(request, "Leaders command executed successfully!")
        except Exception as e:
            messages.error(request, f"Error running leaders command: {str(e)}")
        return HttpResponseRedirect(reverse('custom_admin:index'))


# Register the custom admin site
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register your models here.
class TeamListAdmin(admin.ModelAdmin):
    list_display = ("club_full_name", "ea_club_num", "club_abbr", "isActive", "team_color", "team_code", "manager", "ass_manager")
    list_filter = ("isActive",)

class TeamRecordAdmin(admin.ModelAdmin):
    list_display = ("ea_club_num__club_abbr", "game_num__season_num__season_text", "game_num")
    list_filter = ("game_num__season_num__season_text", "ea_club_num__club_abbr")

class BuildsAdmin(admin.ModelAdmin):
    list_display = ("build", "buildShort")

class PlayerListAdmin(admin.ModelAdmin):
    list_display = ("username", "current_team__club_full_name")
    search_fields = ("username",)

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
            call_command("mergegame", game_num, merge_game_num)
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

        schedule = queryset[0].schedule_num
        if not schedule:
            messages.error(request, "No valid schedule selected.")
            return
        try:
            call_command("createschedule", schedule)
            messages.success(request, f"Schedule {schedule} has been successfully generated.")
        except Exception as e:
            messages.error(request, f"Error running schedule {schedule}: {str(e)}")

    run_scheduler.short_description = "Run selected schedule"

class CustomUserAdmin(UserAdmin):
    model = User

    # Remove unwanted fields from the user change form
    fieldsets = (
        (None, {"fields": ("username", "password", "player_link")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "player_link", "is_staff", "is_superuser", "groups"),
        }),
    )

    list_display = (
        "username",
        "date_joined",
        "is_superuser",
        "is_admin_group",
        "is_media_group",
        "is_team_manager_group",
        "linked_player",
    )

    autocomplete_fields = ["player_link"]

    def is_in_group(self, obj, group_name):
        return obj.groups.filter(name=group_name).exists()

    @admin.display(boolean=True, description='Admin Group')
    def is_admin_group(self, obj):
        return self.is_in_group(obj, "Admins")

    @admin.display(boolean=True, description='Media Group')
    def is_media_group(self, obj):
        return self.is_in_group(obj, "Media")

    @admin.display(boolean=True, description='Team Managers Group')
    def is_team_manager_group(self, obj):
        return self.is_in_group(obj, "Team Managers")

    @admin.display(description="Linked Player")
    def linked_player(self, obj):
        if obj.player_link:
            ct = ContentType.objects.get_for_model(obj.player_link)
            url_name = f"custom_admin:{ct.app_label}_{ct.model}_change"
            url = reverse(url_name, args=[obj.player_link.ea_player_num])
            return format_html('<a href="{}">{}</a>', url, obj.player_link.username)
        return "-"

class AnnouncementAdminForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = "__all__"

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("created_at","author")
    list_filter = ("author",)
    form = AnnouncementAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # On the add page, hide the author field
        if obj is None:
            if "author" in form.base_fields:
                form.base_fields["author"].widget = forms.HiddenInput()
        return form

    def save_model(self, request, obj, form, change):
        if not change or not obj.author:
            obj.author = request.user
        obj.save()

class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("player", "week_start")

class SkaterRatingAdmin(admin.ModelAdmin):
    list_display = ("season", "player", "position", "ovr_pct")
    list_filter = ("season__season_text",)

class GameSkaterRatingAdmin(admin.ModelAdmin):
    list_display = ("skater_record__ea_player_num", "skater_record__game_num__game_num", "skater_record__game_num__season_num__season_text", "overall_rating", "offense_rating", "defense_rating", "teamplay_rating", "game_result_bonus")
    list_filter = ("skater_record__game_num__season_num__season_text",)

class SalaryAdmin(admin.ModelAdmin):
    list_display = ("player", "season", "amount")
    list_filter = ("season__season_text",)
    search_fields = ("player__username",)

class TeamServerBindingAdmin(admin.ModelAdmin):
    list_display = ("guild_id", "team")
    search_fields = ("guild_id", "team__club_abbr", "team__club_full_name")

class PSBAdmin(admin.ModelAdmin):
    list_display = ("guild_id", "requested_team", "requested_by", "requested_at")
    search_fields = ("guild_id", "requested_team__club_abbr")

class StandingAdmin(admin.ModelAdmin):
    list_display = ("team", "season", "points", "playoffs")
    list_filter = ("season__season_text",)

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
custom_admin_site.register(TeamRecord, TeamRecordAdmin)
custom_admin_site.register(Standing, StandingAdmin)
custom_admin_site.register(Leader)
custom_admin_site.register(AwardVote)
custom_admin_site.register(User, CustomUserAdmin)
custom_admin_site.register(Group, GroupAdmin)
custom_admin_site.register(PlayoffRound, PlayoffRoundAdmin)
custom_admin_site.register(PlayoffSeries, PlayoffSeriesAdmin)
custom_admin_site.register(Schedule, ScheduleAdmin)
custom_admin_site.register(BannedUser)
custom_admin_site.register(Announcement, AnnouncementAdmin)
custom_admin_site.register(PlayerAvailability, AvailabilityAdmin)
custom_admin_site.register(SkaterRating, SkaterRatingAdmin)
custom_admin_site.register(GameSkaterRating, GameSkaterRatingAdmin)
custom_admin_site.register(GoalieRating)
custom_admin_site.register(GameGoalieRating)
custom_admin_site.register(TradeBlockPlayer)
custom_admin_site.register(TeamNeed)
custom_admin_site.register(Salary, SalaryAdmin)
custom_admin_site.register(TeamServerBinding, TeamServerBindingAdmin)
custom_admin_site.register(PendingServerBinding, PSBAdmin)
custom_admin_site.register(PlayoffConfig)