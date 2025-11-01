import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
from django.conf import settings
from asgiref.sync import sync_to_async
import asyncio
from GHLWebsiteApp.models import Player, SkaterRecord
from GHLWebsiteApp.models import *
from django.db.models import Sum, Count, Case, When, Avg, F, Window, FloatField, Q, ExpressionWrapper, Value, OuterRef, Subquery, CharField
from django.db.models.functions import Cast, Rank, Round, Lower, Coalesce
from GHLWebsiteApp.views import get_seasonSetting

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found. Make sure it's in your .env file.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
async def statsskater(interaction: discord.Interaction, username: str):
    logger.info(f"Command /statsskater triggered for username: {username}")
    await interaction.response.defer()
    try:
        logger.info("Trying exact username match")
        player = await sync_to_async(Player.objects.filter)(username__iexact=username)
        if not await sync_to_async(player.exists)():
            logger.info("Trying partial username match")
            player = await sync_to_async(Player.objects.filter)(username__icontains=username)
        if not await sync_to_async(player.exists)():
            await interaction.followup.send(f"⚠️ Player '{username}' not found.")
            logger.warning("Player not found.")
            return
        count = await sync_to_async(player.count)()
        if count > 1:
            logger.info(f"Multiple players found: {count} total")
            matches = await sync_to_async(lambda: ", ".join(player.values_list("username", flat=True)[:5]))()
            await interaction.followup.send(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
            return
        player = await sync_to_async(player.first)()
        logger.info(f"Found player: {player.username}")

        # Aggregate skater stats
        season = await sync_to_async(get_seasonSetting)()
        if season is None:
            await interaction.followup.send("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")
            logger.warning("No active season found.")
            return

        def get_skater_stats():           
            return SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=player).exclude(position=0).aggregate(
                total_fow=Coalesce(Sum("fow"), 0),
                total_fol=Coalesce(Sum("fol"), 0),
            ).annotate(
                sgp=Count("game_num"),
                sgoals=Sum("goals"),
                sppg=Sum("ppg"),
                sshg=Sum("shg"),
                sassists=Sum("assists"),
                sumsog=Sum("sog"),
                sumshotatt=Sum("shot_attempts"),
                sumpassatt=Sum("pass_att"),
                sshotperc=Cast(Sum("goals"), models.FloatField())/Cast(Case(
                        When(sumsog=0, then=1),
                        default=Sum("sog"),
                        output_field=models.FloatField()
                    ), models.FloatField())*100,
                spassperc=Cast(Sum("pass_comp"), models.FloatField())/Cast(Case(
                        When(sumpassatt=0, then=1),
                        default=Sum("pass_att"),
                        output_field=models.FloatField()
                    ), models.FloatField())*100,
                shits=Avg("hits"),
                spims=Avg("pims"),
                sdrawn=Avg("pens_drawn"),
                sbs=Avg("blocked_shots"),
                sfaceoffperc = Case(
                    When(
                        Q(total_fow__gt=0) | Q(total_fol__gt=0),
                        then=Cast(F("total_fow") * 100.0 / (F("total_fow") + F("total_fol")), FloatField())
                    ),
                    default=0,
                    output_field=FloatField()
                )
            ).first()
        logger.info("Querying skater stats...")
        try:
            stats = await asyncio.wait_for(sync_to_async(get_skater_stats)(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Skater stats query timed out.")
            await interaction.followup.send("⚠️ Stats are taking too long. Try again later.")
            return
        if stats is None:
            logger.info("No stats found for player.")
            await interaction.followup.send(f"⚠️ No stats found for player '{username}' in the current season.")
            return
        logger.info("Sending response.")
        response_message = (
            f"🏒 **{player.username}** — Season Stats ({stats['sgp']} GP)\n"
            f"Goals: **{stats.sgoals}** ({stats['sppg']} PP, {stats['sshg']} SH)\n"
            f"Assists: **{stats['sassists']}**\n"
            f"S%: **{stats['sshotperc']}**\n"
            f"Pass%: **{stats['spassperc']}**\n"
            f"Hits/GP: **{stats['shits']}**, PIMs/GP: **{stats['spims']}**, Drawn/GP: **{stats['sdrawn']}**, Blocks/GP: **{stats['sbs']}**, FO%: **{stats['sfaceoffperc']}**"
        )
        await interaction.followup.send(response_message)
    except Exception as e:
        logger.exception(f"Error in /statsskater command: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}")
        except discord.InteractionResponded:
            logger.warning("Interaction already responded to. Skipping follow-up.")
        return

@bot.tree.command(name="statsgoalie", description="Show a player's goalie stats for this season")
@app_commands.describe(username="Enter a player's username")
async def statsgoalie(interaction: discord.Interaction, username: str):
    logger.info(f"Command /statsgoalie triggered for username: {username}")
    await interaction.response.defer()
    try:
        logger.info("Trying exact username match")
        player = await sync_to_async(Player.objects.filter)(username__iexact=username)
        if not await sync_to_async(player.exists)():
            logger.info("Trying partial username match")
            player = await sync_to_async(Player.objects.filter)(username__icontains=username)
        if not await sync_to_async(player.exists)():
            await interaction.followup.send(f"⚠️ Player '{username}' not found.")
            logger.warning("Player not found.")
            return
        count = await sync_to_async(player.count)()
        if count > 1:
            logger.info(f"Multiple players found: {count} total")
            matches = await sync_to_async(lambda: ", ".join(player.values_list("username", flat=True)[:5]))()
            await interaction.followup.send(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
            return
        player = await sync_to_async(player.first)()
        logger.info(f"Found player: {player.username}")
        # Aggregate skater stats
        season = await sync_to_async(get_seasonSetting)()
        if season is None:
            await interaction.followup.send("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")
            logger.warning("No active season found.")
            return
        def get_goalie_stats():
            return GoalieRecord.objects.filter(game_num__season_num=season, ea_player_num=player).aggregate(
                ggp = Count("game_num"),
                gsvp = (Cast(Sum("saves"), models.FloatField())/Cast(Sum("shots_against"), models.FloatField()))*100,
                ggaa = ((Cast(Sum("shots_against"), models.FloatField())-Cast(Sum("saves"), models.FloatField()))/Cast(Sum("game_num__gamelength"), models.FloatField()))*3600,
                gshutouts =Sum(Case(
                    When(shutout=True, then=1),
                    default=0,
                    output_field=models.IntegerField()
                )),
                gwins = Sum(Case(
                    When(win=True, then=1),
                    default=0,
                    output_field=models.IntegerField()
                )),
                glosses = Sum(Case(
                    When(loss=True, then=1),
                    default=0,
                    output_field=models.IntegerField()
                )),
                gotlosses = Sum(Case(
                    When(otloss=True, then=1),
                    default=0,
                    output_field=models.IntegerField()
                )),
            )
        logger.info("Querying goalie stats...")
        try:
            stats = await asyncio.wait_for(sync_to_async(get_goalie_stats)(), timeout=10)
        except asyncio.TimeoutError:
            await interaction.followup.send("⚠️ Stats are taking too long. Try again later.")
            logger.error("Goalie stats query timed out.")
            return
        if stats is None:
            await interaction.followup.send(f"⚠️ No stats found for player '{username}' in the current season.")
            logger.info("No stats found for player.")
            return
        logger.info("Sending response.")
        response_message = (
            f"🏒 **{player.username}** — Season Stats ({stats['ggp']} GP)\n"
            f"SV%: **{stats['gsvp']}**\n"
            f"GAA: **{stats['ggaa']}**\n"
            f"Shutouts: **{stats['gshutouts']}**\n"
            f"Record: **{stats['gwins']}-{stats['glosses']}-{stats['gotlosses']}**"
        )
        # Return as Discord webhook-compatible JSON
        await interaction.followup.send(response_message)
    except Exception as e:
        logger.exception(f"Error in /statsgoalie command: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}")
        except discord.InteractionResponded:
            logger.warning("Interaction already responded to. Skipping follow-up.")
        return
