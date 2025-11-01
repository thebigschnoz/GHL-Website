import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from django.conf import settings
from GHLWebsiteApp.models import Player, SkaterRecord
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F, Window, FloatField, Q, ExpressionWrapper, Value, OuterRef, Subquery, CharField
from django.db.models.functions import Cast, Rank, Round, Lower, Coalesce
from views import get_seasonSetting

TOKEN = "MTMyNDk0OTYxNTg4MzMyNTQ1MA.GiVUYx.hPeE9kxo5UEKN9VLoH3LqeR7Lhacl5VmSokqqw"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Discord bot logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print(f"🔁 Slash commands synced")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# --- SLASH COMMANDS ---
@bot.tree.command(name="statsskater", description="Show a player's skater stats for this season")
@app_commands.describe(username="Enter a player's username")
async def stats(interaction: discord.Interaction, username: str):
    try:
        player = Player.objects.get(username__iexact=username)
        if not player.exists():
            player = Player.objects.filter(username__icontaines=username)
        if not player.exists():
            await interaction.response.send_message(f"⚠️ Player '{username}' not found.")
        if player.count() > 1:
            matches = ", ".join(player.values_list("username", flat=True)[:5])
            await interaction.response.send_message(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
        player = player.first()

        # Aggregate skater stats
        season = get_seasonSetting()
        if season is None:
            await interaction.response.send_message("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")            
        stats = SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=player).exclude(position=0).annotate(
            total_fow=Coalesce(Sum("fow"), 0),
            total_fol=Coalesce(Sum("fol"), 0),
        ).annotate(
            gp=Count("game_num"),
            goals=Sum("goals"),
            ppg=Sum("ppg"),
            shg=Sum("shg"),
            assists=Sum("assists"),
            sumsog=Sum("sog"),
            sumshotatt=Sum("shot_attempts"),
            sumpassatt=Sum("pass_att"),
            shotperc=Cast(Sum("goals"), models.FloatField())/Cast(Case(
                    When(sumsog=0, then=1),
                    default=Sum("sog"),
                    output_field=models.FloatField()
                ), models.FloatField())*100,
            passperc=Cast(Sum("pass_comp"), models.FloatField())/Cast(Case(
                    When(sumpassatt=0, then=1),
                    default=Sum("pass_att"),
                    output_field=models.FloatField()
                ), models.FloatField())*100,
            hits=Avg("hits"),
            pims=Avg("pims"),
            drawn=Avg("pens_drawn"),
            bs=Avg("blocked_shots"),
            faceoffperc = Case(
                When(
                    Q(total_fow__gt=0) | Q(total_fol__gt=0),
                    then=Cast(F("total_fow") * 100.0 / (F("total_fow") + F("total_fol")), FloatField())
                ),
                default=0,
                output_field=FloatField()
            )
        ).first()
        if stats is None:
            await interaction.response.send_message(f"⚠️ No stats found for player '{username}' in the current season.")
        response_message = (
            f"🏒 **{player.username}** — Season Stats ({stats.gp} GP)\n"
            f"Goals: **{stats.goals}** ({stats.ppg} PP, {stats.shg} SH)\n"
            f"Assists: **{stats.assists}**\n"
            f"S%: **{stats.shotperc}**\n"
            f"Pass%: **{stats.passperc}**\n"
            f"Hits/GP: **{stats.hits}**, PIMs/GP: **{stats.pims}**, Drawn/GP: **{stats.drawn}**, Blocks/GP: **{stats.bs}**, FO%: **{stats.faceoffperc}**"
        )
        # Return as Discord webhook-compatible JSON
        await interaction.response.send_message(response_message)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")

@bot.tree.command(name="statsgoalie", description="Show a player's goalie stats for this season")
@app_commands.describe(username="Enter a player's username")
async def stats(interaction: discord.Interaction, username: str):
    try:
        player = Player.objects.get(username__iexact=username)
        if not player.exists():
            player = Player.objects.filter(username__icontaines=username)
        if not player.exists():
            await interaction.response.send_message(f"⚠️ Player '{username}' not found.")
        if player.count() > 1:
            matches = ", ".join(player.values_list("username", flat=True)[:5])
            await interaction.response.send_message(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
        player = player.first()

        # Aggregate skater stats
        season = get_seasonSetting()
        if season is None:
            await interaction.response.send_message("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")
        stats = GoalieRecord.objects.filter(game_num__season_num=season, ea_player_num=player).annotate(
            gp = Count("game_num"),
            svp = (Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100,
            gaa = ((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600,
            shutouts =Sum(Case(
                When(shutout=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            wins = Sum(Case(
                When(win=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            losses = Sum(Case(
                When(loss=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
            otlosses = Sum(Case(
                When(otloss=True, then=1),
                default=0,
                output_field=models.IntegerField()
            )),
        ).first()
        if stats is None:
            await interaction.response.send_message(f"⚠️ No stats found for player '{username}' in the current season.")
        response_message = (
            f"🏒 **{player.username}** — Season Stats ({stats.gp} GP)\n"
            f"SV%: **{stats.svp}**\n"
            f"GAA: **{stats.gaa}**\n"
            f"Shutouts: **{stats.shutouts}**\n"
            f"Record: **{stats.wins}-{stats.losses}-{stats.otlosses}**"
        )
        # Return as Discord webhook-compatible JSON
        await interaction.response.send_message(response_message)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}")
