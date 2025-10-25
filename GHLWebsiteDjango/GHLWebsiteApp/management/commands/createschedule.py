from datetime import *
from random import shuffle
from django.core.management.base import BaseCommand, CommandError
from GHLWebsiteApp.models import Game, Schedule, Team

class Command(BaseCommand):
    help = "Generate and save games for a given schedule ID."

    def add_arguments(self, parser):
        parser.add_argument("schedule_id", type=int, help="ID of the schedule to generate games for")
        parser.add_argument('--skip-date', action='append', default=[],
                            help='A single date to skip (YYYY-MM-DD). May be repeated.')
        parser.add_argument('--skip-dates', default='',
                            help='Comma-separated dates to skip (YYYY-MM-DD,YYYY-MM-DD,...)')
        parser.add_argument('--skip-range', action='append', default=[],
                            help='A date range to skip (YYYY-MM-DD:YYYY-MM-DD). May be repeated.')
        parser.add_argument('--skip-weekdays', default='',
                            help='Comma-separated weekdays to skip (mon,tue,wed,thu,fri,sat,sun)')

    # --- helpers ---
    def _parse_date(self, s):
        try:
            return datetime.strptime(s.strip(), '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid date: {s} (expected YYYY-MM-DD)')

    def _parse_date_list(self, s):
        return [self._parse_date(x) for x in s.split(',') if x.strip()]

    def _parse_range(self, s):
        try:
            start_s, end_s = s.split(':', 1)
        except ValueError:
            raise CommandError(f'Invalid range: {s} (expected YYYY-MM-DD:YYYY-MM-DD)')
        start = self._parse_date(start_s)
        end = self._parse_date(end_s)
        if end < start:
            raise CommandError(f'Invalid range: {s} (end before start)')
        cur = start
        out = []
        while cur <= end:
            out.append(cur)
            cur = cur + timedelta(days=1)
        return out
    
    def _parse_weekdays(self, s: str) -> set[int]:
        WEEKDAY_MAP = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
        }
        tokens = [t.strip().lower() for t in s.split(',') if t.strip()]
        bad = [t for t in tokens if t not in WEEKDAY_MAP]
        if bad:
            raise CommandError(f'Invalid weekday(s): {", ".join(bad)} (use mon,tue,wed,thu,fri,sat,sun)')
        return {WEEKDAY_MAP[t] for t in tokens}

    def _build_skip_dates(self, options, start_date=None, end_date=None):
        skip = set()

        # single dates & list
        for d in options['skip_date']:
            skip.add(self._parse_date(d))
        if options['skip_dates']:
            skip.update(self._parse_date_list(options['skip_dates']))

        # ranges
        for r in options['skip_range']:
            skip.update(self._parse_range(r))

        # weekdays (optionally constrain to season window if provided)
        weekdays = self._parse_weekdays(options['skip_weekdays']) if options['skip_weekdays'] else set()
        if weekdays:
            # If your command knows the season window, pass start_date/end_date; otherwise we’ll generate lazily.
            if start_date and end_date:
                cur = start_date
                while cur <= end_date:
                    if cur.weekday() in weekdays:
                        skip.add(cur)
                    cur += timedelta(days=1)
            # else: we’ll check weekday on-the-fly in the scheduler loop

        return skip, weekdays

    def handle(self, *args, **options):
        schedule_id = options["schedule_id"]

        try:
            schedule = Schedule.objects.get(schedule_num=schedule_id)
        except Schedule.DoesNotExist:
            raise CommandError(f"Schedule with ID {schedule_id} does not exist.")
        
         # Build skip dates / weekdays using the schedule window start
        skip_dates, skip_weekdays = self._build_skip_dates(
            options,
            start_date=schedule.start_date,  # if you also know end_date, pass it too
            end_date=None
        )

        generator = ScheduleGenerator(schedule, 
                                    self.stdout,
                                    skip_dates=skip_dates,
                                    skip_weekdays=skip_weekdays,)
        games = generator.generate_and_save_games()
        self.stdout.write(self.style.SUCCESS(f"Generated {len(games)} games."))


class ScheduleGenerator:
    def __init__(self, schedule: Schedule, stdout=None, skip_dates: set[datetime.date] | None = None,
                 skip_weekdays: set[int] | None = None):
        self.schedule = schedule
        self.skip_dates = skip_dates or set()
        self.skip_weekdays = skip_weekdays or set()
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
            current_date += timedelta(days=1)
        while True:
            # current_date here is a date (not datetime) per your method contract
            # Skip fixed weekdays (existing Fri/Sat) + dynamic self.skip_weekdays
            if current_date.weekday() in (4, 5) or current_date.weekday() in self.skip_weekdays:
                current_date += timedelta(days=1)
                continue
            # Skip explicit blackout dates
            if current_date in self.skip_dates:
                current_date += timedelta(days=1)
                continue
            break
            
        current_date = datetime.combine(current_date, self.allowed_times[time_counter])
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
        current_date = datetime.combine(self.schedule.start_date, self.allowed_times[0]) # Sets the starting date and time for the schedule
        time_counter = 0
        # bump start forward until it’s an allowed day
        while True:
            start_day = current_date.date()
            if start_day.weekday() in (4, 5) or start_day.weekday() in self.skip_weekdays or start_day in self.skip_dates:
                # advance by a day, keep same first slot
                next_day = start_day + timedelta(days=1)
                current_date = datetime.combine(next_day, self.allowed_times[0])
                continue
            break
        stack = []
        while matchups:
            remaining_teams = set(self.teams)
            daily_matchups = []
            stack = []  # Each entry: (daily_matchups, matchups, remaining_teams, tried_pairs)
            day = current_date.date()
            if day.weekday() in (4, 5) or day.weekday() in self.skip_weekdays or day in self.skip_dates:
                self.stdout.write(f"Skipping blocked date: {day.isoformat()}")
                current_date, time_counter = self.increment_matchday(day, time_counter)
                continue

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