from GHLWebsiteApp.views import get_seasonSetting, calculate_leaders, calculate_standings
from GHLWebsiteApp.models import Game
import httpx
from GHLWebsiteApp.models import *
from datetime import datetime, time, date
import pytz
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

BASE_API_URL = "https://proclubs.ea.com/api/nhl/clubs/matches?matchType=club_private&platform=common-gen5&clubIds="
               
class Command(BaseCommand):
    help = "Polls the EA API for game data and updates the database"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force the script to run even if no games are scheduled')


    def fetch_and_process_games(self, team_id):
        c = httpx.Client(http2=True)
        try:
            url = f"{BASE_API_URL}{team_id}"
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'referer': 'https://proclubs.ea.com/',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'upgrade-insecure-requests': '1',
            }
            self.stdout.write(f"Fetching data from {url}...")
            response = c.get(url, timeout=15, headers=headers)
            self.stdout.write(f"Response status code: {response.status_code}")
            response.raise_for_status()
        except httpx.ConnectTimeout:
            raise CommandError(f"Request to pull data for team {team_id} timed out")
        except httpx.RequestError as e:
            raise CommandError(f"Error fetching data: {e}")
        else:
            self.stdout.write("Parsing JSON response...")
            data = response.json()  # Parse JSON

            # Define the time range in EST
            est = pytz.timezone('US/Eastern')
            start_time = time(21, 1)  # 9:01pm
            end_time = time(22, 45)   # 10:45pm
            
            # Process the data
            for game in data:
                timestamp = game.get("timestamp", 0)
                game_time = datetime.fromtimestamp(timestamp, est).time()
                game_date = datetime.fromtimestamp(timestamp, est).date()

                # Check if the game time is within the desired range
                if not (start_time <= game_time <= end_time):
                    seasonSetting = 2
                    self.stdout.write(f"Game time is not within the desired range - setting season to test season")
                else:
                    seasonSetting = get_seasonSetting()
                    self.stdout.write(f"Game time is within the desired range - using season setting {seasonSetting}")

                # Extract team numbers
                teamnumbers = iter(game["clubs"].keys())
                try:
                    first_team_num = next(teamnumbers)
                    second_team_num = next(teamnumbers)
                except StopIteration:
                    self.stdout.write("Not enough teams in the game data - skipping game")
                    continue

                # Determine which team is home and away
                if game['clubs'][first_team_num]['teamSide'] == 1:
                    a_team_num = first_team_num
                    h_team_num = second_team_num
                else:
                    a_team_num = second_team_num
                    h_team_num = first_team_num

                # Fetch the Team instances
                try:
                    a_team_instance = Team.objects.get(ea_club_num=a_team_num)
                    h_team_instance = Team.objects.get(ea_club_num=h_team_num)
                    if a_team_instance.isActive == False or h_team_instance.isActive == False:
                        self.stdout.write(f"One of the teams is inactive - skipping game")
                        continue
                except Team.DoesNotExist:
                    self.stdout.write(f"One of the teams does not exist in the database - skipping game")
                    continue
                self.stdout.write(f"Processing game between {game['clubs'][a_team_num]['details']['name']} and {game['clubs'][h_team_num]['details']['name']}")

                # Extract dnf value
                dnf = any(
                    player_data.get("player_dnf", 0) == 1
                    for team_id, team_players in game["players"].items()
                    for player_id, player_data in team_players.items()
                )
                if dnf:
                    self.stdout.write("DNF detected - setting season to test season")
                    seasonSetting = 2

                # Fetch the Season instance
                try:
                    season_instance = Season.objects.get(pk=seasonSetting)
                except Season.DoesNotExist:
                    raise CommandError(f"Season with id {seasonSetting} does not exist")

                # Make sure it's a private game
                is_private_game = any(
                    club_data.get("cNhlOnlineGameType") == "5"
                    for club_id, club_data in game["clubs"].items()
                )
                if not is_private_game:
                    self.stdout.write("Not a private game - skipping")
                    continue
                
                game_num = game.get("matchId", 0)

                # Check if the match already exists
                if Game.objects.filter(game_num=game_num).exists():
                    self.stdout.write(f"Game {game_num} already exists in database - skipping")
                    continue

                # Calculate gamelength (max 'toi' from all players)
                gamelength = max(
                    player_data.get("toiseconds", 0)
                    for team_id, team_players in game["players"].items()
                    for player_id, player_data in team_players.items()
                )

                # Extract gfraw values for a_team_gf and h_team_gf
                a_team_gf = game["clubs"][a_team_num].get("gfraw", 0)
                h_team_gf = game["clubs"][h_team_num].get("gfraw", 0)
                self.stdout.write(f"Game ended with score {a_team_gf} - {h_team_gf}")
        
                # Find the matching game by date and team numbers
                matching_games = Game.objects.filter(
                    a_team_num=a_team_instance,
                    h_team_num=h_team_instance,
                    expected_time__date=game_date,
                    played_time = None # Make sure you're not using a game that's already been downloaded if a team plays same opponent twice in a day
                ).order_by("expected_time")
                matching_games_flipped = Game.objects.filter(
                        a_team_num=h_team_instance,
                        h_team_num=a_team_instance,
                        expected_time__date=game_date,
                        played_time = None # Make sure you're not using a game that's already been downloaded if a team plays same opponent twice in a day
                ).order_by("expected_time")
                # If there is a matching game, use its expected time
                if matching_games.exists():
                    expected_time = matching_games.first().expected_time
                elif matching_games_flipped.exists():
                        expected_time = matching_games_flipped.first().expected_time
                        # Swap variables for flipped game
                        a_team_gf, h_team_gf = h_team_gf, a_team_gf
                        a_team_num, h_team_num = h_team_num, a_team_num
                        a_team_instance, h_team_instance = h_team_instance, a_team_instance
                else:
                    expected_time = None

                # Create game record
                game_obj = Game(
                    game_num=game_num,
                    a_team_num=a_team_instance,
                    h_team_num=h_team_instance,
                    played_time=datetime.fromtimestamp(timestamp, est),
                    expected_time=expected_time,
                    dnf=dnf,
                    gamelength=int(gamelength),
                    a_team_gf=int(a_team_gf),
                    h_team_gf=int(h_team_gf),
                    season_num=season_instance,
                )
                if matching_games.exists() and season_instance.season_num == get_seasonSetting():
                    matching_games.first().delete()
                elif matching_games_flipped.exists() and season_instance.season_num == get_seasonSetting():
                    matching_games_flipped.first().delete()
                game_obj.save()
                self.stdout.write(f"Created new game {game_num}")
                
                # Parse team stats
                for club_id, club_data in game["clubs"].items():
                    try:
                        team_instance = Team.objects.get(ea_club_num=club_id)
                    except Team.DoesNotExist:
                        self.stdout.write(f"Team with team_num {club_id} does not exist in the database - skipping")
                        continue
                    pass_att_team = game["aggregate"].get(club_id, {}).get("skpassattempts", 0)
                    pass_comp_team = game["aggregate"].get(club_id, {}).get("skpasses", 0)
                    fow_team = game["aggregate"].get(club_id, {}).get("skfow", 0)
                    fol_team = game["aggregate"].get(club_id, {}).get("skfol", 0)
                    hits_team = game["aggregate"].get(club_id, {}).get("skhits", 0)
                    pims_team = game["aggregate"].get(club_id, {}).get("skpim", 0)
                    shg_team = game["aggregate"].get(club_id, {}).get("skshg", 0)
                    shot_att_team = game["aggregate"].get(club_id, {}).get("skshots", 0)
                    teamrecord_obj, _ = TeamRecord.objects.update_or_create(
                        ea_club_num=team_instance,
                        game_num=game_obj,
                        defaults={
                            "home_away": club_data.get("teamSide", 0),
                            "goals_for": club_data.get("gfraw", 0),
                            "goals_against": club_data.get("garaw", 0),
                            "pass_att_team": pass_att_team,
                            "pass_comp_team": pass_comp_team,
                            "ppg_team": club_data.get("ppg", 0),
                            "ppo_team": club_data.get("ppo", 0),
                            "sog_team": club_data.get("shots", 0),
                            "toa_team": club_data.get("toa", 0),
                            "dnf": club_data.get("winnerByDnf", False) or club_data.get("winnerByGoalieDnf", False),
                            "fow_team": fow_team,
                            "fol_team": fol_team,
                            "hits_team": hits_team,
                            "pims_team": pims_team,
                            "shg_team": shg_team,
                            "shot_att_team": shot_att_team,
                        }
                    )
                self.stdout.write(f"Processed team stats for game {game_num}")

                # Parse skater stats
                for team_id, team_players in game["players"].items():
                    for player_id, player_data in team_players.items():
                        players_team_instance = Team.objects.get(ea_club_num=team_id)
                        if seasonSetting == 2:
                            # Create player, but don't give current team
                            player_instance, _ = Player.objects.get_or_create(
                            ea_player_num=player_id,
                            defaults={
                                "username": player_data.get("playername", "Username Not Found"),
                                "current_team": None
                            })
                        else:
                            player_instance, _ = Player.objects.get_or_create(
                                ea_player_num=player_id,
                                defaults={
                                    "username": player_data.get("playername", "Username Not Found"),
                                    "current_team": players_team_instance
                            })
                            player_instance.current_team = players_team_instance
                            player_instance.save()
                        pos_sorted = Position.objects.get(ea_pos=player_data.get("posSorted", 0))
                        build = player_data.get("class", 0)
                        try:
                            player_class = Build.objects.get(ea_build=build)
                        except:
                            player_class = Build.objects.get(ea_build=30)
                        skgoals = int(player_data.get("skgoals", 0))
                        skassists = int(player_data.get("skassists", 0))
                        skhits = int(player_data.get("skhits", 0))
                        skplusmin = int(player_data.get("skplusmin", 0))
                        skshots = int(player_data.get("skshots", 0))
                        skshotattempts = int(player_data.get("skshotattempts", 0))
                        skdeflections = int(player_data.get("skdeflections", 0))
                        skppg = int(player_data.get("skppg", 0))
                        skshg = int(player_data.get("skshg", 0))
                        skpassattempts = int(player_data.get("skpassattempts", 0))
                        skpasses = int(player_data.get("skpasses", 0))
                        sksaucerpasses = int(player_data.get("sksaucerpasses", 0))
                        skbs = int(player_data.get("skbs", 0))
                        sktakeaways = int(player_data.get("sktakeaways", 0))
                        skinterceptions = int(player_data.get("skinterceptions", 0))
                        skgiveaways = int(player_data.get("skgiveaways", 0))
                        skpenaltiesdrawn = int(player_data.get("skpenaltiesdrawn", 0))
                        skpim = int(player_data.get("skpim", 0))
                        skpkclearzone = int(player_data.get("skpkclearzone", 0))
                        skpossession = int(player_data.get("skpossession", 0))
                        skfow = int(player_data.get("skfow", 0))
                        skfol = int(player_data.get("skfol", 0))

                        skater_obj, _ = SkaterRecord.objects.update_or_create(
                            ea_player_num=player_instance,
                            game_num=game_obj,
                            ea_club_num=players_team_instance,
                            defaults={
                                "position": pos_sorted,
                                "build": player_class,
                                "goals": skgoals,
                                "assists": skassists,
                                "hits": skhits,
                                "plus_minus": skplusmin,
                                "sog": skshots,
                                "shot_attempts": skshotattempts,
                                "deflections": skdeflections,
                                "ppg": skppg,
                                "shg": skshg,
                                "pass_att": skpassattempts,
                                "pass_comp": skpasses,
                                "saucer_pass": sksaucerpasses,
                                "blocked_shots": skbs,
                                "takeaways": sktakeaways,
                                "interceptions": skinterceptions,
                                "giveaways": skgiveaways,
                                "pens_drawn": skpenaltiesdrawn,
                                "pims": skpim,
                                "pk_clears": skpkclearzone,
                                "poss_time": skpossession,
                                "fow": skfow,
                                "fol": skfol,
                            }
                        )

                        # If pos_sorted is 0, add a GoalieRecord
                        if pos_sorted == Position.objects.get(ea_pos=0):
                            shots_against = int(player_data.get("glshots", 0))
                            saves = int(player_data.get("glsaves", 0))
                            breakaway_shots = int(player_data.get("glbrkshots", 0))
                            breakaway_saves = int(player_data.get("glbrksaves", 0))
                            ps_shots = int(player_data.get("glpenshots", 0))
                            ps_saves = int(player_data.get("glpensaves", 0))

                            goalie_obj, _ = GoalieRecord.objects.update_or_create(
                                ea_player_num=player_instance,
                                game_num=game_obj,
                                ea_club_num=players_team_instance,
                                defaults={
                                    "shots_against": shots_against,
                                    "saves": saves,
                                    "breakaway_shots": breakaway_shots,
                                    "breakaway_saves": breakaway_saves,
                                    "ps_shots": ps_shots,
                                    "ps_saves": ps_saves,
                                }
                            )
                self.stdout.write(f"Processed skater stats for game {game_num}")
            calculate_standings()
            self.stdout.write("Recalculated standings")
            calculate_leaders()
            self.stdout.write("Recalculated leaders")            
        

    def handle(self, *args, **options):
        today = date.today()
        games_today = Game.objects.filter(expected_time__date=today, played_time=None).exists()
        if not games_today and not options['force']:
            self.stdout.write("No games scheduled for today. Use --force to override.")
            return
        self.stdout.write("Polling EA API for game data...")
        self.stdout.write("Getting active teamlist...")
        active_teams = Team.objects.filter(isActive=True) # Gets active teams
        self.stdout.write(f"Found {len(active_teams)} active teams")
        for team in active_teams:
            self.stdout.write(f"Fetching and processing games for {team.club_full_name}")
            clubnum = team.ea_club_num
            self.fetch_and_process_games(clubnum)
            self.stdout.write(self.style.SUCCESS(f"Finished processing games for {team.club_full_name}"))
        self.stdout.write(self.style.SUCCESS("Finished polling EA API for game data"))
        call_command("updateratings")