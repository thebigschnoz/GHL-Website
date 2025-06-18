import datetime
from collections import deque
from itertools import chain
from random import shuffle

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from GHLWebsiteApp.models import Game, Schedule, Team, Field

class Command(BaseCommand):
    help = "Generate and save games for a given schedule ID."
    # TODO: Determine how game totals are being calculated and add logic

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", type=int, help="ID of the schedule to generate games for")
        parser.add_argument("--no-shuffle", action="store_true", help="Disable team shuffle")
        parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")

    def handle(self, *args, **options):
        schedule_id = options["schedule_id"]
        shuffle_order = not options["no_shuffle"]
        dry_run = options["dry_run"]

        try:
            schedule = Schedule.objects.select_related("league", "season").get(id=schedule_id)
            # TODO: Address select_related
            # TODO: Possibly change schedule ID
        except Schedule.DoesNotExist:
            raise CommandError(f"Schedule with ID {schedule_id} does not exist.")

        generator = ScheduleGenerator(schedule)
        games = generator.generate_and_save_games(shuffle_order=shuffle_order, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS(f"Generated {len(games)} games."))


class ScheduleGenerator:
    def __init__(self, schedule: Schedule, blackout_dates: list[datetime.datetime] | None = None):
        self.schedule = schedule
        self.blackout_dates = blackout_dates

    @property
    def total_games(self) -> int:
        # Returns the total number of games based on the schedule's properties.
        return self.schedule.total_games

    @property
    def teams(self) -> list[Team]:
        # Fetches all teams associated with the league of the schedule.
        teams = Team.objects.filter(isActive=True)
        if not teams:
            raise ValueError("The league does not have any teams associated.")
        return list(teams)

    def split_teams(self, teams: list[Team]) -> tuple[list[Team], list[Team]]:
        # Splits the list of teams into two equal halves and returns them.
        if len(teams) % 2 != 0:
            raise ValueError("List length must be even.")
        mid = len(teams) // 2
        return teams[:mid], teams[mid:]

    def determine_field(self, match_count: int, concurrent_games: int | None = None) -> str:
        fields = [f.name for f in Field]
        concurrent_games = concurrent_games or self.schedule.concurrent_games
        if match_count == 1 or match_count > concurrent_games:
            return fields[0]
        return fields[match_count - 1]

    def home_or_away(self, round_number: int, match: tuple[Team, Team]) -> tuple[Team, Team]:
        # Determines the home and away teams based on the round number.
        return match if round_number % 2 == 0 else match[::-1]

    def check_for_bye(self, match: tuple[Team, Team]) -> bool:
        # Checks if either team in the match is a "Bye Week" team and returns True if so.
        return match[0].name == "Bye Week" or match[1].name == "Bye Week"

    def increment_matchday(self, current_date: datetime.date) -> datetime.date:
        # Increments the matchday by a specified number of days and returns the new date.
        next_date = current_date + datetime.timedelta(days=1)
        while next_date.weekday() in (4, 5):  # Skip Friday (4) and Saturday (5)
            next_date += datetime.timedelta(days=1)
        return next_date

    def determine_start_times(self, base_date: datetime.date) -> list[datetime.datetime]:
        # Determines the start time for a game based on the matchday and match count.
        return [datetime.datetime.combine(base_date, t) for t in self.allowed_times]

    def create_matchups(self, matchday: int, teams: list[Team]) -> list[tuple[Team, Team]]:
        # Creates matchups (aka pairings) for the given matchday based on the teams.
        if len(teams) % 2 != 0:
            teams.append(Team(name="Bye Week"))  # Not persisted
        home, away = self.split_teams(teams)
        matchups = list(zip(home, away))
        if matchday != 1:
            rotation = deque(chain(*matchups))
            anchor = rotation.popleft()
            rotation.rotate(matchday)
            rotation.appendleft(anchor)
            home, away = self.split_teams(list(rotation))
            matchups = list(zip(home, away))
        return matchups

    def create_games(self, matchday: int, round_number: int, teams: list[Team], date: datetime.date) -> list[Game]:
        # Creates games for the given matchday and round number based on the teams.
        matchups = self.create_matchups(matchday, teams)
        games = []
        for count, match in enumerate(matchups):
            home, away = self.home_or_away(round_number, match)
            games.append(Game(
                game_num = count + 1,
                season_num = self.schedule.season_num,
                h_team_num = home,
                a_team_num = away,
                game_length = int(None),
                expected_time = self.determine_start_times(matchday, count),
            ))
        return games

    def generate_and_save_games(self, shuffle_order: bool = True, dry_run: bool = False) -> list[Game]:
        # Generates and saves games for the schedule, optionally shuffling teams or performing a dry run.
        if self.schedule.games.exists():
            raise ValueError("Schedule already has games...")

        teams = self.teams
        if shuffle_order:
            shuffle(teams)

        rounds, remaining = divmod(self.total_games, len(teams))
        if rounds == 0:
            raise ValueError("Not enough matchdays for all teams to play each other.")

        all_games: list[Game] = []
        for matchday in range(1, self.total_games - remaining + 1):
            round_number = matchday // len(teams) + 1
            current_date = self.increment_matchday(current_date)
            matchday_games = self.create_games(matchday, round_number, teams, current_date)
            all_games.extend(matchday_games)

        if not dry_run:
            with transaction.atomic():
                Game.objects.bulk_create(all_games)

        return all_games