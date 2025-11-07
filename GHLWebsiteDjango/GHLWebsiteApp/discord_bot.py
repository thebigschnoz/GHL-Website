import os
from dotenv import load_dotenv
import datetime
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
from zoneinfo import ZoneInfo

load_dotenv()

LOG_CHANNEL_ID = 1435172225060962374
TOKEN = os.getenv("DISCORD_TOKEN")
LEAGUE_ADMIN_ROLE = "All Admins"
LEAGUE_GUILD_ID = 1021563211759230976

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found. Make sure it's in your .env file.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def bot_log(message: str):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

@bot.event
async def on_ready():
    print(f"✅ Discord bot logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print(f"🔁 Slash commands synced")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

def get_team_ranking(team):
    ordered_teams = list(
        Standing.objects.select_related("team").filter(season=get_seasonSetting())
        .order_by('-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name')
        .values_list("team__ea_club_num", flat=True)
    )
    try:
        position = ordered_teams.index(team.ea_club_num) + 1
        total = len(ordered_teams)
        return position, total
    except ValueError:
        return None, len(ordered_teams)

def get_team_leaders(team):
    season = Season.objects.filter(isActive=True).first()
    
    leaders = {}

    leader_goals = SkaterRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num__username").annotate(
        goals=Sum("goals")
    ).order_by("-goals").first()
    if leader_goals:
        leaders["Goals"] = (leader_goals["ea_player_num__username"], leader_goals["goals"])

    leader_assists = SkaterRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num__username").annotate(
        assists=Sum("assists")
    ).order_by("-assists").first()
    if leader_assists:
        leaders["Assists"] = (leader_assists["ea_player_num__username"], leader_assists["assists"])

    leader_shooting = SkaterRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num", "ea_player_num__username").annotate(
        shootperc=(Cast(Sum("goals"), FloatField()) / Cast(Sum("sog"), FloatField())) * 100
    ).order_by("-shootperc").first()
    if leader_shooting:
        leaders["Shooting %"] = (leader_shooting["ea_player_num__username"], round(leader_shooting["shootperc"], 1))

    leader_hits = SkaterRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num", "ea_player_num__username").annotate(
        avg_hits=Avg("hits")
    ).order_by("-avg_hits").first()
    if leader_hits:
        leaders["Hits/GP"] = (leader_hits["ea_player_num__username"], round(leader_hits["avg_hits"], 1))

    leader_blocks = SkaterRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num", "ea_player_num__username").annotate(
        avg_blocks=Avg("blocked_shots")
    ).order_by("-avg_blocks").first()
    if leader_blocks:
        leaders["Blocks/GP"] = (leader_blocks["ea_player_num__username"], round(leader_blocks["avg_blocks"], 2))

    leader_goalie_svperc = GoalieRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num", "ea_player_num__username").annotate(
        svperc=(Cast(Sum("saves"), FloatField()) / Cast(Sum("shots_against"), FloatField())) * 100
    ).order_by("-svperc").first()
    if leader_goalie_svperc:
        leaders["SV%"] = (leader_goalie_svperc["ea_player_num__username"], round(leader_goalie_svperc["svperc"], 2))

    leader_goalie_gaa = GoalieRecord.objects.filter(
        ea_player_num__current_team=team,
        game_num__season_num=season
    ).values("ea_player_num", "ea_player_num__username").annotate(
        ggaa=((Cast(Sum("shots_against"), FloatField()) - Cast(Sum("saves"), FloatField())) / Cast(Sum("game_num__gamelength"), FloatField())) * 3600
    ).order_by("ggaa").first()
    if leader_goalie_gaa:
        leaders["GAA"] = (leader_goalie_gaa["ea_player_num__username"], round(leader_goalie_gaa["ggaa"], 2))
    return leaders

def get_pp_ranking(team):
    standings = (
        Standing.objects.filter(season=get_seasonSetting())
        .order_by('-ppperc')
        .values_list("team__ea_club_num", flat=True)
    )
    try:
        position = list(standings).index(team.ea_club_num) + 1
        return position
    except ValueError:
        return None

def get_pk_ranking(team):
    standings = (
        Standing.objects.filter(season=get_seasonSetting())
        .order_by('-pkperc')
        .values_list("team__ea_club_num", flat=True)
    )
    try:
        position = list(standings).index(team.ea_club_num) + 1
        return position
    except ValueError:
        return None

def ordinal_suffix(n):
    if 10 <= n % 100 <= 20:
        return 'th'
    else:
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

async def is_league_admin(interaction):
    # Must be executed inside the LEAGUE_GUILD
    if interaction.guild_id != LEAGUE_GUILD_ID:
        return False
    
    # Must have the required role inside the league server
    return any(r.name == LEAGUE_ADMIN_ROLE for r in interaction.user.roles)
    
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
        
        has_skater_stats = await sync_to_async(
            lambda: SkaterRecord.objects.filter(
                game_num__season_num=season,
                ea_player_num=player
            ).exclude(position=0).exists()
        )()
        if not has_skater_stats:
            await interaction.followup.send(f"⚠️ Player '{username}' has not played any skater games this season.")
            return

        def get_skater_stats():           
            return SkaterRecord.objects.filter(game_num__season_num=season, ea_player_num=player).exclude(position=0).aggregate(
                sgp=Count("game_num"),
                sgoals=Sum("goals"),
                sppg=Sum("ppg"),
                sshg=Sum("shg"),
                sassists=Sum("assists"),
                sumsog=Sum("sog"),
                sumshotatt=Sum("shot_attempts"),
                sumpassatt=Sum("pass_att"),
                sumpasscomp=Sum("pass_comp"),
                shits=Avg("hits"),
                spims=Avg("pims"),
                sdrawn=Avg("pens_drawn"),
                sbs=Avg("blocked_shots"),
                total_fow=Coalesce(Sum("fow"), 0),
                total_fol=Coalesce(Sum("fol"), 0),
                sint=Avg("interceptions"),
                stka=Avg("takeaways"),
                sgva=Avg("giveaways"),
            )
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
        shotperc = (
            (stats["sgoals"] or 0) / (stats["sumsog"] or 1) * 100
            if stats["sumsog"] else 0
        )
        passperc = (
            (stats["sumpasscomp"] or 0) / (stats["sumpassatt"] or 1) * 100
            if stats["sumpassatt"] else 0
        )
        faceoffperc = (
            (stats["total_fow"] * 100.0 / (stats["total_fow"] + stats["total_fol"]))
            if (stats["total_fow"] + stats["total_fol"]) > 0 else 0
        )
        logger.info("Sending response.")
        response_message = (
            f"**{player.username}** — Season Stats ({stats['sgp']} GP)\n"
            f"Goals: **{stats['sgoals']}** ({stats['sppg']} PP, {stats['sshg']} SH)\n"
            f"Assists: **{stats['sassists']}**\n"
            f"S%: **{shotperc:.1f}%**\n"
            f"Pass%: **{passperc:.1f}%**\n"
            f"Hits/GP: **{stats['shits']:.1f}**, PIMs/GP: **{stats['spims']:.1f}**, Drawn/GP: **{stats['sdrawn']:.1f}**, Blocks/GP: **{stats['sbs']:.1f}**, FO%: **{faceoffperc:.1f}%**\n"
            f"INT/GP: **{stats['sint']:.1f}**, TK/GP: **{stats['stka']:.1f}**, GV/GP: **{stats['sgva']:.1f}**"
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
        has_goalie_stats = await sync_to_async(
            lambda: GoalieRecord.objects.filter(
                game_num__season_num=season,
                ea_player_num=player
            ).exists()
        )()
        if not has_goalie_stats:
            await interaction.followup.send(f"⚠️ Player '{username}' has not played any goalie games this season.")
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
            f"**{player.username}** — Season Stats ({stats['ggp']} GP)\n"
            f"SV%: **{stats['gsvp']:.2f}%**\n"
            f"GAA: **{stats['ggaa']:.2f}**\n"
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

@bot.tree.command(name="team", description="Show team stats for a given team")
@app_commands.describe(teamname="Enter a team's name or abbreviation")
async def team(interaction: discord.Interaction, teamname: str):
    logger.info(f"Command /team triggered for teamname: {teamname}")
    await interaction.response.defer()
    try:
        logger.info("Trying exact team name match")
        team = await sync_to_async(Team.objects.filter)(Q(club_full_name__iexact=teamname) | Q(club_abbr__iexact=teamname))
        if not await sync_to_async(team.exists)():
            logger.info("Trying partial team name match")
            team = await sync_to_async(Team.objects.filter)(Q(club_full_name__icontains=teamname) | Q(club_abbr__icontains=teamname))
        if not await sync_to_async(team.exists)():
            await interaction.followup.send(f"⚠️ Team '{teamname}' not found.")
            logger.warning("Team not found.")
            return
        count = await sync_to_async(team.count)()
        if count > 1:
            logger.info(f"Multiple teams found: {count} total")
            matches = await sync_to_async(lambda: ", ".join(team.values_list("name", flat=True)[:5]))()
            await interaction.followup.send(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
            return
        team = await sync_to_async(team.first)()
        logger.info(f"Found team: {team.club_full_name}")

        # Aggregate team stats
        season = await sync_to_async(get_seasonSetting)()
        if season is None:
            await interaction.followup.send("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")
            logger.warning("No active season found.")
            return

        def get_team_stats():
            return Standing.objects.filter(team=team, season=season).first()
        leaders = await sync_to_async(get_team_leaders)(team)
        leader_lines = "\n".join(
            f"**{label}**: {username} ({value})" for label, (username, value) in leaders.items()
        )
        logger.info("Querying team stats...")
        try:
            stats = await asyncio.wait_for(sync_to_async(get_team_stats)(), timeout=10)
        except asyncio.TimeoutError:
            logger.error("Team stats query timed out.")
            await interaction.followup.send("⚠️ Stats are taking too long. Try again later.")
            return
        if stats is None:
            await interaction.followup.send(f"⚠️ No stats found for team '{teamname}' in the current season.")
            logger.info("No stats found for team.")
            return
        position, total = await sync_to_async(get_team_ranking)(team)
        pp_rank = await sync_to_async(get_pp_ranking)(team)
        pk_rank = await sync_to_async(get_pk_ranking)(team)
        if position:
            standing_line = f"📈 Current Standing: **{position}{ordinal_suffix(position)}** out of {total}\n"
        else:
            standing_line = "📈 Standing not available yet.\n"
        if pp_rank:
            pp_rank = f"{pp_rank}{ordinal_suffix(pp_rank)}"
        if pk_rank:
            pk_rank = f"{pk_rank}{ordinal_suffix(pk_rank)}"
        logger.info("Sending response.")
        response_message = (
            f"**{team.club_full_name}** — Team Stats\n"
            f"{standing_line}"
            f"Record: **{stats.wins}-{stats.losses}-{stats.otlosses}**, Streak: **{stats.streak}\n**"
            f"GF/GA (Diff): **{stats.goalsfor}/{stats.goalsagainst} ({stats.goalsfor - stats.goalsagainst})**\n"
            f"PP%: **{stats.ppperc:.2f}%** ({pp_rank}), PK%: **{stats.pkperc:.2f}%** ({pk_rank})\n\n"
        )
        if leader_lines:
            response_message += (f"👑 __Team Leaders__:\n{leader_lines}")
        else:
            response_message += "👑 No team leader data available."
        await interaction.followup.send(response_message)
    except Exception as e:
        logger.exception(f"Error in /team command: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}")
        except discord.InteractionResponded:
            logger.warning("Interaction already responded to. Skipping follow-up.")
        return

@bot.tree.command(name="upcoming", description="Show upcoming ten games for a team")
@app_commands.describe(teamname="Enter a team's name or abbreviation")
async def upcoming(interaction: discord.Interaction, teamname: str):
    logger.info(f"Command /team triggered for teamname: {teamname}")
    await interaction.response.defer()
    try:
        logger.info("Trying exact team name match")
        team = await sync_to_async(Team.objects.filter)(Q(club_full_name__iexact=teamname) | Q(club_abbr__iexact=teamname))
        if not await sync_to_async(team.exists)():
            logger.info("Trying partial team name match")
            team = await sync_to_async(Team.objects.filter)(Q(club_full_name__icontains=teamname) | Q(club_abbr__icontains=teamname))
        if not await sync_to_async(team.exists)():
            await interaction.followup.send(f"⚠️ Team '{teamname}' not found.")
            logger.warning("Team not found.")
            return
        count = await sync_to_async(team.count)()
        if count > 1:
            logger.info(f"Multiple teams found: {count} total")
            matches = await sync_to_async(lambda: ", ".join(team.values_list("name", flat=True)[:5]))()
            await interaction.followup.send(f"⚠️ Multiple matches found: {matches}\nPlease be more specific.")
            return
        team = await sync_to_async(team.first)()
        logger.info(f"Found team: {team.club_full_name}")

        # Aggregate team stats
        season = await sync_to_async(get_seasonSetting)()
        if season is None:
            await interaction.followup.send("⚠️ No active season found. Please try again later when Schnoz isn't breaking the website.")
            logger.warning("No active season found.")
            return
        def get_upcoming_games():
            return list(
                Game.objects.filter(season_num=season).filter(
                Q(h_team_num=team) | Q(a_team_num=team)
            ).filter(played_time__isnull=True)
            .select_related("h_team_num", "a_team_num")
            .order_by("expected_time")[:10])
        upcoming_games = await asyncio.wait_for(sync_to_async(get_upcoming_games)(), timeout=10)
        if not upcoming_games:
            await interaction.followup.send(f"No upcoming games found for {team.club_abbr}.")
            return
        game_info_lines = []
        for game in upcoming_games:
            if game.h_team_num == team:
                opponent = game.a_team_num
                location = "Home"
                team_code = team.team_code
            else:
                opponent = game.h_team_num
                location = "Away"
                team_code = opponent.team_code

            if game.expected_time:
                est_time = game.expected_time.astimezone(ZoneInfo("America/New_York"))
                game_time = est_time.strftime("%b %d %-I:%M")
            else:
                game_time = "TBD"
            game_info_lines.append(f"- {game_time} | {location} vs {opponent.club_abbr} | **{team_code}**")

        message = f"🗓️ Upcoming Games for **{team.club_abbr}**:\n" + "\n".join(game_info_lines)
        await interaction.followup.send(message)
    except Exception as e:
        logger.exception(f"Error in /team command: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}")
        except discord.InteractionResponded:
            logger.warning("Interaction already responded to. Skipping follow-up.")
        return

@bot.tree.command(name="lineups", description="Show scheduled lineups for the current GHL week")
@app_commands.describe(teamname="Enter a team's name or abbreviation")
async def lineups(interaction: discord.Interaction, teamname: str):
    await interaction.response.defer()

    binding = await sync_to_async(
        TeamServerBinding.objects.filter(guild_id=interaction.guild_id).select_related("team").first)()

    if not binding:
        return await interaction.followup.send(
            "⛔ This server is not registered. A server admin must run `/set_team_server TEAMCODE` first.",
            ephemeral=True
        )

    if binding.team:
        # Server is restricted to one team — override user input
        team = binding.team
    else:
        # This is the main server (or a server intentionally set as unrestricted)
        team = None  # unrestricted server (main league server)

    def get_current_ghl_week_start():
        eastern = ZoneInfo("America/New_York")
        now = datetime.datetime.now(eastern).date()
        weekday = now.weekday()  # Monday = 0 ... Sunday = 6

        # GHL Week = Friday (4) → Thursday (10)
        # If today is Fri (4) or Sat (5), we jump ahead to NEXT Friday
        if weekday in (4, 5):  # Friday or Saturday
            days_until_next_friday = (4 - weekday) % 7
            week_start = now + datetime.timedelta(days=days_until_next_friday)
        else:
            # Otherwise, find the most recent Friday
            days_since_friday = (weekday - 4) % 7
            week_start = now - datetime.timedelta(days=days_since_friday)

        return week_start

    try:
        # --- Resolve Team ---
        def resolve_team():
            qs = Team.objects.filter(
                Q(club_full_name__iexact=teamname) | Q(club_abbr__iexact=teamname)
            )
            if not qs.exists():
                qs = Team.objects.filter(
                    Q(club_full_name__icontains=teamname) | Q(club_abbr__icontains=teamname)
                )
            return qs.first() if qs.exists() else None

        team = await sync_to_async(resolve_team)()
        if not team:
            await interaction.followup.send(f"⚠️ Team '{teamname}' not found.")
            return

        # --- Determine EST Friday-Thursday week range ---
        week_start = await sync_to_async(get_current_ghl_week_start)()
        week_end = week_start + datetime.timedelta(days=6)

        # --- Get team games for this week ---
        def fetch_games():
            return list(
                Game.objects.filter(
                    expected_time__date__gte=week_start,
                    expected_time__date__lte=week_end,
                ).filter(
                    Q(h_team_num=team) | Q(a_team_num=team)
                ).select_related("h_team_num", "a_team_num")
                .order_by("expected_time")
            )

        games = await sync_to_async(fetch_games)()
        if not games:
            await interaction.followup.send(f"No games scheduled for {team.club_abbr} this week.")
            return

        # --- Fetch scheduling rows for all those games ---
        def fetch_schedules():
            return list(
                Scheduling.objects.filter(game__in=games, team=team)
                .select_related("player", "position", "game")
            )

        schedules = await sync_to_async(fetch_schedules)()

        # Build mapping: {game_id: {posShort: username}}
        schedule_map = {}
        for s in schedules:
            schedule_map.setdefault(s.game.game_num, {})[s.position.positionShort] = s.player.username

        # --- Build output text ---
        lines = [
            f"📝 **Lineups for {team.club_abbr}** "
            f"({week_start:%b %d}–{week_end:%b %d})\n"
        ]

        est = ZoneInfo("America/New_York")
        positions = ["C", "LW", "RW", "LD", "RD", "G"]

        for g in games:
            local_time = g.expected_time.astimezone(est)
            opponent = g.a_team_num if g.h_team_num == team else g.h_team_num
            homeaway = "vs" if g.h_team_num == team else "@"
            code_to_display = team.team_code if homeaway == "vs" else opponent.team_code

            # --- Get opponent record ---
            def get_record():
                try:
                    s = Standing.objects.get(team=opponent)
                    return f"{s.wins}-{s.losses}-{s.otlosses}"
                except Standing.DoesNotExist:
                    return "0-0-0"

            record = await sync_to_async(get_record)()

            # Header line for game
            lines.append(
                f"__{local_time:%a %-I:%M %p} {homeaway} {opponent.club_abbr} ({record})__\n"
                f"(*{code_to_display}*)"
            )

            # Position assignments
            assigned = schedule_map.get(g.game_num, {})
            for pos in positions:
                lines.append(f"{pos}: {assigned.get(pos, '—')}")
            lines.append("")  # spacer line

        await interaction.followup.send("\n".join(lines))

    except Exception as e:
        logger.exception(f"Error in /lineups command: {e}")
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="request", description="Request to bind this server to a team. Admins only.")
@app_commands.checks.has_permissions(administrator=True)
async def request(interaction: discord.Interaction, club_abbr: str):
    team = await sync_to_async(Team.objects.filter(club_abbr__iexact=club_abbr).first)()
    if not team:
        return await interaction.followup.send(f"❌ Team `{club_abbr}` not found.", ephemeral=True)

    # Store request
    await sync_to_async(PendingServerBinding.objects.update_or_create)(
        guild_id=interaction.guild_id,
        defaults={"requested_team": team, "requested_by": interaction.user.id},
    )

    # DM the requester
    try:
        await interaction.user.send(f"✅ Your server binding request for **{team.club_abbr}** has been submitted and awaits approval.")
    except:
        pass  # user has DMs disabled

    # Notify them in server
    await interaction.response.send_message(
        "✅ Request submitted. A league admin must approve it before `/lineups` will work.",
        ephemeral=True
    )

    # Log to league server
    await bot_log(
        f"📩 Binding request: `{interaction.guild.name}` ({interaction.guild_id}) → **{team.club_abbr}** (requested by `{interaction.user}`)"
    )


@bot.tree.command(name="clearteam", description="Unbind THIS server from any team. Admins only.")
@app_commands.checks.has_permissions(administrator=True)
async def clearteam(interaction: discord.Interaction):
    deleted, _ = await sync_to_async(TeamServerBinding.objects.filter(guild_id=interaction.guild_id).delete)()
    if deleted:
        msg = "✅ Server unbound. `/lineups` is now blocked until bound again."
        await bot_log(f"🗑️ `{interaction.user}` unbound guild `{interaction.guild.name}` ({interaction.guild_id})")
    else:
        msg = "ℹ️ This server wasn’t bound."
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="approve", description="Approve a pending team server binding. League admins only.")
async def approve(interaction: discord.Interaction, guild_id: str):
    if not is_league_admin(interaction):
        return await interaction.followup.send("⛔ You do not have permission.", ephemeral=True)

    pending = await sync_to_async(PendingServerBinding.objects.filter(guild_id=guild_id).select_related("requested_team").first)()
    if not pending:
        return await interaction.followup.send("❌ No pending request found for that guild.", ephemeral=True)

    # Apply binding
    await sync_to_async(TeamServerBinding.objects.update_or_create)(
        guild_id=guild_id,
        defaults={"team": pending.requested_team},
    )

    # Notify requester if possible
    user = await bot.fetch_user(pending.requested_by)
    try:
        await user.send(f"✅ Your server binding request has been approved! **{pending.requested_team.club_abbr}** is now active.")
    except:
        pass

    await sync_to_async(pending.delete)()

    await interaction.response.send_message("✅ Approved and applied.", ephemeral=True)
    await bot_log(f"✅ Approved: `{guild_id}` → **{pending.requested_team.club_abbr}** by `{interaction.user}`")

@bot.tree.command(name="viewbindings", description="View all registered and pending server bindings. League admins only.")
async def viewbindings(interaction: discord.Interaction):
    if not is_league_admin(interaction):
        return await interaction.followup.send("⛔ You do not have permission.", ephemeral=True)

    approved = await sync_to_async(list)(
        TeamServerBinding.objects.select_related("team").all()
    )
    pending = await sync_to_async(list)(
        PendingServerBinding.objects.select_related("requested_team").all()
    )

    msg = "**✅ Approved Bindings:**\n"
    if approved:
        for b in approved:
            msg += f"• `{b.guild_id}` → **{b.team.club_abbr if b.team else 'UNBOUND'}**\n"
    else:
        msg += "• *(none)*\n"

    msg += "\n**⏳ Pending Requests:**\n"
    if pending:
        for p in pending:
            msg += f"• `{p.guild_id}` → **{p.requested_team.club_abbr}** (by <@{p.requested_by}>)\n"
    else:
        msg += "• *(none)*"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(
    name="deny",
    description="Deny a pending server binding request. League admins only."
)
async def deny(interaction: discord.Interaction, guild_id: str):
    # Must be run inside the main league Discord, and must have the required role
    if interaction.guild_id != LEAGUE_GUILD_ID:
        return await interaction.followup.send(
            "⛔ This command can only be used inside the main league server.",
            ephemeral=True
        )

    if not any(r.name == LEAGUE_ADMIN_ROLE for r in interaction.user.roles):
        return await interaction.followup.send(
            "⛔ You do not have permission to perform this action.",
            ephemeral=True
        )

    pending = await sync_to_async(
        PendingServerBinding.objects.filter(guild_id=guild_id).select_related("requested_team").first
    )()

    if not pending:
        return await interaction.followup.send(
            "❌ No pending request found for that guild.",
            ephemeral=True
        )

    # Try to DM requester
    try:
        user = await bot.fetch_user(pending.requested_by)
        await user.send(
            f"❌ Your server binding request for **{pending.requested_team.club_abbr}** was denied."
        )
    except:
        pass  # DMs blocked or invalid user

    # Delete request
    await sync_to_async(pending.delete)()

    # Acknowledge in admin server
    await interaction.response.send_message(
        f"✅ Denied request from guild `{guild_id}` for team **{pending.requested_team.club_abbr}**.",
        ephemeral=True
    )

    # Log to league log channel
    await bot_log(
        f"❌ DENIED by `{interaction.user}` — `{guild_id}` → **{pending.requested_team.club_abbr}**"
    )
