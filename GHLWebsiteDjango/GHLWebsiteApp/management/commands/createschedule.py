import datetime
from random import shuffle

from django.core.management.base import BaseCommand, CommandError

from GHLWebsiteApp.models import Game, Schedule, Team

class Command(BaseCommand):
    help = "Generate and save games for a given schedule ID."

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", type=int, help="ID of the schedule to generate games for")

    def handle(self, *args, **options):
        schedule_id = options["schedule_id"]

        try:
            schedule = Schedule.objects.get(schedule_num=schedule_id)
        except Schedule.DoesNotExist:
            raise CommandError(f"Schedule with ID {schedule_id} does not exist.")

        generator = ScheduleGenerator(schedule, self.stdout)
        games = generator.generate_and_save_games()
        self.stdout.write(self.style.SUCCESS(f"Generated {len(games)} games."))


class ScheduleGenerator:
    def __init__(self, schedule: Schedule, stdout=None, blackout_dates: list[datetime.datetime] | None = None):
        self.schedule = schedule
        self.blackout_dates = blackout_dates
        self.allowed_times = [datetime.time(21, 0), datetime.time(21, 45)]
        self.stdout = stdout

    @property
    def teams(self) -> list[Team]:
        # Fetches all teams associated with the league of the schedule.
        teams = Team.objects.filter(isActive=True)
        if not teams:
            raise ValueError("The league does not have any active teams.")
        return list(teams)

    @property
    def total_games(self) -> int:
        # Returns the total number of games based on the schedule's properties.
        total_games = len(self.teams) * self.schedule.games_per_matchup / 2
        return total_games

    '''def split_teams(self, teams: list[Team]) -> tuple[list[Team], list[Team]]:
        # Splits the list of teams into two equal halves and returns them.
        if len(teams) % 2 != 0:
            raise ValueError("List length must be even.")
        mid = len(teams) // 2
        return teams[:mid], teams[mid:]'''

    def increment_matchday(self, current_date: datetime.date, time_counter: int) -> tuple[datetime.date,int]:
        # Increments the matchday and returns the new datetime.
        day_counter = len(self.allowed_times)
        time_counter += 1
        if time_counter >= day_counter:
            time_counter = 0
            current_date += datetime.timedelta(days=1)
        while current_date.weekday() in (4, 5):  # Skip Friday (4) and Saturday (5)
            current_date += datetime.timedelta(days=1)
            
        current_date = datetime.datetime.combine(current_date, self.allowed_times[time_counter])
        return current_date, time_counter

    def create_all_matchups(self, teams: list[Team]) -> list[tuple[Team, Team]]:
        # Creates all possible matchups from the list of teams.
        matchups = []
        for n in range(0, self.schedule.games_per_matchup):
            for i in range(0, len(teams)):
                opponents = list(team for team in teams if team != teams[i])
                for opponent in range(0, len(opponents)):
                    matchups.append((teams[i], opponents[opponent]))
        # Shuffle the matchups to randomize the order.
        shuffle(matchups)
        return matchups
    
    def generate_and_save_games(self) -> list[Game]:
        # Generates and saves games based on the schedule and teams.
        if not self.teams:
            raise ValueError("No active teams available to generate games.")

        matchups = self.create_all_matchups(self.teams)
        games = []
        current_date = datetime.datetime.combine(self.schedule.start_date, self.allowed_times[0]) # Sets the starting date and time for the schedule
        time_counter = 0

        stack = []
        while matchups:
            remaining_teams = set(self.teams)
            daily_matchups = []
            stack = []  # Each entry: (daily_matchups, matchups, remaining_teams, tried_pairs)

            while len(remaining_teams) > 1:
                made_progress = False
                team_list = list(remaining_teams)
                shuffle(team_list)
                current_team = team_list[0]

                # Generate matchups for current team that are still valid
                possible_games = [
                    m for m in matchups
                    if current_team in m and m[0] in remaining_teams and m[1] in remaining_teams
                ]

                # Try each possible game, tracking which were attempted
                tried = set()
                if stack:
                    _, _, _, tried = stack[-1]

                for game in possible_games:
                    if game in tried or (game[1], game[0]) in tried:
                        continue

                    # Push state before making the move
                    stack.append((
                        daily_matchups.copy(),
                        matchups.copy(),
                        remaining_teams.copy(),
                        tried | {game}
                    ))

                    daily_matchups.append(game)
                    matchups.remove(game)
                    remaining_teams.remove(game[0])
                    remaining_teams.remove(game[1])
                    self.stdout.write(f"Chosen matchup: {game[0].club_abbr} vs {game[1].club_abbr}")
                    made_progress = True
                    break

                if not made_progress:
                    self.stdout.write("No valid matchup found. Backtracking...")
                    if not stack:
                        raise RuntimeError("Backtracking failed. Cannot complete schedule.")
                    daily_matchups, matchups, remaining_teams, _ = stack.pop()

            # Save the day’s games
            self.stdout.write(f"Creating games for date: {current_date.strftime('%Y-%m-%d %H:%M')}")
            for matchup in daily_matchups:
                games.append(Game(
                    season_num=self.schedule.season_num,
                    expected_time=current_date,
                    a_team_num=matchup[0],
                    h_team_num=matchup[1],
                ))

            self.stdout.write(f"Remaining matchups: {len(matchups)}")
            current_date, time_counter = self.increment_matchday(current_date, time_counter)

        Game.objects.bulk_create(games)
        self.stdout.write(f"Total games created: {len(games)} for {self.schedule.season_num}")
        return games