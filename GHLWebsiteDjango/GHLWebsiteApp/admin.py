from django.contrib import admin

from .models import Seasons, Games, AwardsList, TeamList, PlayerList, Positions, Builds, Awards, SkaterRecords, GoalieRecords, TeamRecords

# Register your models here.

admin.site.register(Seasons)
admin.site.register(Games)
admin.site.register(AwardsList)
admin.site.register(TeamList)
admin.site.register(PlayerList)
admin.site.register(Positions)
admin.site.register(Builds)
admin.site.register(Awards)
admin.site.register(SkaterRecords)
admin.site.register(GoalieRecords)
admin.site.register(TeamRecords)