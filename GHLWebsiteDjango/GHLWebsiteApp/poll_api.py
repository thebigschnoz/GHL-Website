from .views import get_seasonSetting, calculate_leaders, calculate_standings
import requests, json
from .models import Game, TeamRecord, SkaterRecord, GoalieRecord, Player
from datetime import datetime, time, timedelta
import pytz

BASE_API_URL = "https://proclubs.ea.com/api/nhl/clubs/gamees?gameType=club_private&platform=common-gen5&clubIds="
SEASON_SETTING = get_seasonSetting()

def fetch_and_process_games(team_id):
    try:
        # Construct the URL with the team ID
        url = f"{BASE_API_URL}{team_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()  # Parse JSON

        # Define the time range in EST
        est = pytz.timezone('US/Eastern')
        start_time = time(21, 10)  # 9:10pm
        end_time = time(22, 45)    # 10:45pm
        
        # Process the data
        for game in data:
            timestamp = game.get("timestamp", 0)
            game_time = datetime.fromtimestamp(timestamp, est).time()

            # Check if the game time is within the desired range
            if not (start_time <= game_time <= end_time):
                continue

            # Make sure it's a private game
            is_private_game = any(
                club_data.get("cNhlOnlineGameType") == "5"
                for club_id, club_data in game["clubs"].items()
            )
            if not is_private_game:
                print(f"Skipping game {game['gameId']} due to invalid Game Type")
                continue

            game_num = game.get("matchId", 0)

            # Check if the match already exists
            if Game.objects.filter(game_num=game_num).exists():
                print(f"Skipping match {game_num} as it already exists in the database.")
                continue

            # Calculate gamelength (max 'toi' from all players)
            gamelength = max(
                player_data.get("toiseconds", 0)
                for team_id, team_players in game["players"].items()
                for player_id, player_data in team_players.items()
            )

            # Extract team numbers
            teamnumbers = iter(game["clubs"].keys())
            a_team_num = next(teamnumbers)
            h_team_num = next(teamnumbers)

            # Extract dnf value
            dnf = game["clubs"][a_team_num]["dnf"] or game["clubs"][h_team_num]["dnf"]

            # Extract gfraw values for a_team_gf and h_team_gf
            a_team_gf = game["clubs"][a_team_num].get("gfraw", 0)
            h_team_gf = game["clubs"][h_team_num].get("gfraw", 0)
    
            # Get or create game record
            game_obj, created = Game.objects.get_or_create(
                game_num=game_num,
                defaults={"season_num": SEASON_SETTING,
                          "gamelength": gamelength,
                          "played_time": timestamp,
                          "dnf": dnf,
                          "a_team_num": a_team_num,
                          "h_team_num": h_team_num,
                          "a_team_gf": a_team_gf,
                          "h_team_gf": h_team_gf
                          }
            )
            
            # Parse team stats
            for club_id, club_data in game["clubs"].items():
                pass_att_team = game["aggregates"].get(club_id, {}).get("skpassattempts", 0)
                pass_comp_team = game["aggregates"].get(club_id, {}).get("skpasses", 0)
                fow_team = game["aggregates"].get(club_id, {}).get("skfow", 0)
                fol_team = game["aggregates"].get(club_id, {}).get("skfol", 0)
                hits_team = game["aggregates"].get(club_id, {}).get("skhits", 0)
                pims_team = game["aggregates"].get(club_id, {}).get("skpim", 0)
                shg_team = game["aggregates"].get(club_id, {}).get("skshg", 0)
                shot_att_team = game["aggregates"].get(club_id, {}).get("skshots", 0)
                teamrecord_obj, _ = TeamRecord.objects.update_or_create(
                    ea_club_num=club_id,
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

            # Parse skater stats
            for team_id, team_players in game["players"].items():
                for player_id, player_data in team_players.items():
                    pos_sorted = player_data.get("posSorted", 0)
                    player_class = player_data.get("class", 0)
                    skgoals = player_data.get("skgoals", 0)
                    skassists = player_data.get("skassists")
                    skhits = player_data.get("skhits", 0)
                    skplusmin = player_data.get("skplusmin", 0)
                    skshots = player_data.get("skshots", 0)
                    skshotattempts = player_data.get("skshotattempts", 0)
                    skdeflections = player_data.get("skdeflections", 0)
                    skppg = player_data.get("skppg", 0)
                    skshg = player_data.get("skshg", 0)
                    skpassattempts = player_data.get("skpassattempts", 0)
                    skpasses = player_data.get("skpasses", 0)
                    sksaucerpasses = player_data.get("sksaucerpasses", 0)
                    skbs = player_data.get("skbs", 0)
                    sktakeaways = player_data.get("sktakeaways", 0)
                    skinterceptions = player_data.get("skinterceptions", 0)
                    skgiveaways = player_data.get("skgiveaways", 0)
                    skpenaltiesdrawn = player_data.get("skpenaltiesdrawn", 0)
                    skpim = player_data.get("skpim", 0)
                    skpkclearzone = player_data.get("skpkclearzone", 0)
                    skpossession = player_data.get("skpossession", 0)
                    skfow = player_data.get("skfow", 0)
                    skfol = player_data.get("skfol", 0)

                    skater_obj, _ = SkaterRecord.objects.update_or_create(
                        ea_player_num=player_id,
                        game_num=game_obj,
                        ea_club_num=team_id,
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

                    # Update or create Player
                    player_obj, created = Player.objects.get_or_create(
                        ea_player_num=player_id,
                        defaults={"username": player_data.get("playername", "Username Not Found"),
                                  "current_team": team_id
                    })

                    # If pos_sorted is 0, add a GoalieRecord
                    if pos_sorted == 0:
                        shots_against = player_data.get("glshots", 0)
                        saves = player_data.get("glsaves", 0)
                        breakaway_shots = player_data.get("glbrkshots", 0)
                        breakaway_saves = player_data.get("glbrksaves", 0)
                        ps_shots = player_data.get("glpenshots", 0)
                        ps_saves = player_data.get("glpensaves", 0)

                        goalie_obj, _ = GoalieRecord.objects.update_or_create(
                            ea_player_num=player_id,
                            game_num=game_obj,
                            ea_club_num=team_id,
                            defaults={
                                "shots_against": shots_against,
                                "saves": saves,
                                "breakaway_shots": breakaway_shots,
                                "breakaway_saves": breakaway_saves,
                                "ps_shots": ps_shots,
                                "ps_saves": ps_saves,
                            }
                        )
        calculate_standings()
        calculate_leaders()
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for team {team_id}: {e}")