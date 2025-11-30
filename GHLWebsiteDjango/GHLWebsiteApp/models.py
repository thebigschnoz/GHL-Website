from django.db import models
from django.utils import timezone
from django.db.models import Q
from django.db.models.functions import Lower
from decimal import *
from django.contrib.auth.models import AbstractUser, User, Group
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

class Season(models.Model):
    SEASON_CHOICES = [
        ('preseason', 'Preseason'),
        ('regular', 'Regular Season'),
        ('playoffs', 'Playoffs'),
    ]
    season_num = models.AutoField(primary_key=True, verbose_name="Autonum")
    season_text = models.CharField(max_length=50, verbose_name="Season Name")
    season_type = models.CharField(max_length=20, choices=SEASON_CHOICES, default='preseason', verbose_name="Season Type", help_text="Preseason, Regular Season, or Playoffs")
    isActive = models.BooleanField(default=False, verbose_name="Is Active Season", help_text="Only one season can be active at a time")
    start_date = models.DateField(verbose_name="Start Date", blank=True, null=True)
    signups_open = models.BooleanField(
        default=False,
        verbose_name="Signups Open",
        help_text="If true, players can submit signups for this season."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['isActive'],
                condition=models.Q(isActive=True),
                name='unique_active_season',
                violation_error_message="There can only be one active season at a time."
            )
        ]

    def __str__(self):
        return self.season_text

class Team(models.Model):
    ea_club_num = models.IntegerField(primary_key=True, verbose_name="EA Club Number")
    club_full_name = models.CharField(max_length=50, verbose_name="Full Club Name")
    club_abbr = models.CharField(max_length=3, verbose_name="Club Abbreviation", help_text="3-letter abbreviation for the club")
    team_logo_link = models.TextField(blank=True, null=True, verbose_name="Team Logo Link", help_text="Link to the team logo image")
    isActive = models.BooleanField(default=True, verbose_name="Is Active Team", help_text="Indicates if the team is currently active in the league")
    team_color = models.CharField(max_length=7, default="#000000", verbose_name="Team Color", help_text="Hex color code for the team's primary color")
    team_code = models.CharField(max_length=6, verbose_name="Game Matchup Code", help_text="GHL specific matchup code to be used in EA NHL games", blank=True, null=True)
    team_location = models.CharField(max_length=50, verbose_name="Team Location", help_text="Location of the team, e.g., 'New York', 'Toronto'", default="Location")
    team_name = models.CharField(max_length=50, verbose_name="Team Name", help_text="Name of the team, e.g., 'Rangers', 'Maple Leafs'", default="Name")
    manager = models.OneToOneField('User', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Team Manager", help_text="User who manages the team in the GHL", related_name="team_manager")
    ass_manager = models.OneToOneField('User', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Team Assistant Manager", help_text="User who is the assistant manager for the team in the GHL", related_name="team_assistant_manager")

    def __str__(self):
        return self.club_full_name
    
    class Meta:
        ordering = [Lower('club_full_name')]

    def save(self, *args, **kwargs):
        # Store previous values so we can detect changes
        if self.pk:
            old = Team.objects.filter(pk=self.pk).first()
            old_manager = old.manager if old else None
            old_ass_manager = old.ass_manager if old else None
        else:
            old_manager = None
            old_ass_manager = None

        super().save(*args, **kwargs)

        # Group we assign/remove
        group, _ = Group.objects.get_or_create(name="Team Managers")

        # ✅ 1. ADD group to new manager(s)
        for user in [self.manager, self.ass_manager]:
            if user:
                user.groups.add(group)

        # ✅ 2. REMOVE group from OLD manager if they no longer manage ANY team
        for old_user in [old_manager, old_ass_manager]:
            if old_user and old_user not in [self.manager, self.ass_manager]:
                still_manager = Team.objects.filter(
                    Q(manager=old_user) | Q(ass_manager=old_user)
                ).exists()
                if not still_manager:
                    old_user.groups.remove(group)

class Game(models.Model):
    game_num = models.AutoField(primary_key=True)
    season_num = models.ForeignKey(Season, on_delete=models.CASCADE)
    gamelength = models.PositiveIntegerField(verbose_name="Game Length in seconds", default="3600", blank=True, null=True)
    expected_time = models.DateTimeField(verbose_name="Expected Game Time", blank=True, null=True)
    played_time = models.DateTimeField(verbose_name="Actual Game Time", blank=True, null=True)
    dnf = models.BooleanField(default=False, verbose_name="DNF", blank=True, null=True)
    a_team_num = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="a_team", verbose_name="Away Team")
    h_team_num = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="h_team", verbose_name="Home Team")
    a_team_gf = models.IntegerField(verbose_name="Away Score", default="0", blank=True)
    h_team_gf = models.IntegerField(verbose_name="Home Score", default="0", blank=True)

class Schedule(models.Model):

    schedule_num = models.AutoField(primary_key=True)
    season_num = models.ForeignKey(Season, on_delete=models.CASCADE, verbose_name="Season")
    games_per_matchup = models.PositiveIntegerField(verbose_name="Home Games per Matchup", default=8)
    start_date = models.DateField(verbose_name="Start Date", blank=True, null=True)

    def __str__(self):
        return f"{self.season_num.season_text}"

class AwardTitle(models.Model):
    award_num = models.IntegerField(primary_key=True)
    award_Name = models.CharField(max_length=50, verbose_name="Name")
    award_Desc = models.TextField(blank=True, verbose_name="Description")
    assign_or_vote = models.BooleanField(default=False, verbose_name="Assign/Vote", help_text="True = Assign, False = Vote")

    def __str__(self):
        return self.award_Name
    
class Position(models.Model):
    ea_pos = models.IntegerField(primary_key=True)
    position = models.CharField(max_length=20)
    positionShort = models.CharField(max_length=2)

    def __str__(self):
        return self.position

class Player(models.Model):
    ea_player_num = models.IntegerField(primary_key=True)
    jersey_num = models.PositiveSmallIntegerField(verbose_name="Jersey Number", default=99, blank=True, null=True)
    username = models.CharField(max_length=16)
    current_team = models.ForeignKey(Team, on_delete = models.CASCADE, blank=True, null=True)
    primarypos = models.ForeignKey(Position, on_delete = models.CASCADE, related_name="primary", blank=True, null=True)
    secondarypos = models.ManyToManyField(Position, related_name="secondary", blank=True)
    playerpic = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username
    
    class Meta:
        ordering = [Lower('username')]

class User(AbstractUser):
    """Custom user model for GHL Website"""
    player_link = models.OneToOneField(Player, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Link to your player stats", help_text="Link to the player's profile in the GHL database")

    class Meta:
        ordering = [Lower('username')]

    def __str__(self):
        return self.username

class Build(models.Model):
    ea_build = models.IntegerField(primary_key=True)
    build = models.CharField(max_length=25)
    buildShort = models.CharField(max_length=3)

class AwardAssign(models.Model):
    award_num = models.AutoField(primary_key=True)
    players = models.ManyToManyField(Player, blank=True, verbose_name="Players")
    team = models.ForeignKey(Team, on_delete = models.CASCADE, verbose_name="Team", null=True)
    award_type = models.ForeignKey(AwardTitle, on_delete = models.CASCADE, verbose_name="Award")
    season_num = models.ForeignKey(Season, on_delete = models.CASCADE, verbose_name="Season")

    def __str__(self):
        return f"{self.season_num.season_text} - {self.award_type.award_Name}"

class SkaterRecord(models.Model):
    ea_player_num = models.ForeignKey(Player, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Game, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(Team, on_delete = models.CASCADE)
    position = models.ForeignKey(Position, on_delete = models.CASCADE)
    build = models.ForeignKey(Build, on_delete = models.CASCADE)
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)
    hits = models.PositiveSmallIntegerField(default=0)
    plus_minus = models.SmallIntegerField(default=0)
    sog = models.PositiveSmallIntegerField(default=0)
    shot_attempts = models.PositiveSmallIntegerField(default=0)
    deflections = models.PositiveSmallIntegerField(default=0)
    ppg = models.PositiveSmallIntegerField(default=0)
    shg = models.PositiveSmallIntegerField(default=0)
    pass_att = models.PositiveSmallIntegerField(default=0)
    pass_comp = models.PositiveSmallIntegerField(default=0)
    saucer_pass = models.PositiveSmallIntegerField(default=0)
    blocked_shots = models.PositiveSmallIntegerField(default=0)
    takeaways = models.PositiveSmallIntegerField(default=0)
    interceptions = models.PositiveSmallIntegerField(default=0)
    giveaways = models.PositiveSmallIntegerField(default=0)
    pens_drawn = models.PositiveSmallIntegerField(default=0)
    pims = models.PositiveSmallIntegerField(default=0)
    pk_clears = models.PositiveSmallIntegerField(default=0)
    poss_time = models.PositiveSmallIntegerField(default=0)
    fow = models.PositiveSmallIntegerField(default=0)
    fol = models.PositiveSmallIntegerField(default=0)
    shot_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    shot_eff = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pass_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def pointscalc(self):
        totalpoints = self.goals + self.assists
        return totalpoints
    
    @property
    def shotpctcalc(self):
        if self.sog > 0:
            shotpct = (self.goals / self.sog) * 100
            return shotpct
        else:
            return Decimal("0")
        
    @property
    def shoteffcalc(self):
        if self.shot_attempts > 0:
            shoteff = (self.sog / (self.shot_attempts + self.deflections)) * 100
            return shoteff
        else:
            return Decimal("0")
        
    @property
    def passpctcalc(self):
        if self.pass_att > 0:
            passpct = (self.pass_comp / self.pass_att) * 100
            return passpct
        else:
            return Decimal("0")
    
    def save(self, *args, **kwargs):
        self.points = self.pointscalc
        self.shot_pct = self.shotpctcalc
        self.shot_eff = self.shoteffcalc
        self.pass_pct = self.passpctcalc
        super(SkaterRecord, self).save(*args, **kwargs)

class GoalieRecord(models.Model):
    ea_player_num = models.ForeignKey(Player, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Game, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(Team, on_delete = models.CASCADE)
    shots_against = models.PositiveSmallIntegerField(default=0)
    saves = models.PositiveSmallIntegerField(default=0)
    save_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    gaa = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    win = models.BooleanField(default=0)
    loss = models.BooleanField(default=0)
    otloss = models.BooleanField(default=0)
    shutout = models.BooleanField(default=0)
    breakaway_shots = models.PositiveSmallIntegerField(default=0)
    breakaway_saves = models.PositiveSmallIntegerField(default=0)
    ps_shots = models.PositiveSmallIntegerField(default=0)
    ps_saves = models.PositiveSmallIntegerField(default=0)

    @property
    def wincalc(self):
        if self.ea_club_num == self.game_num.a_team_num:
            if self.game_num.a_team_gf > self.game_num.h_team_gf:
                return 1
            else:
                return 0
        else:
            if self.game_num.h_team_gf > self.game_num.a_team_gf:
                return 1
            else:
                return 0
            
    @property
    def losscalc(self):
        if self.game_num.gamelength == 3600:
            if self.ea_club_num == self.game_num.a_team_num:
                if self.game_num.a_team_gf < self.game_num.h_team_gf:
                    return 1
                else:
                    return 0
            else:
                if self.game_num.h_team_gf < self.game_num.a_team_gf:
                    return 1
                else:
                    return 0
        else:
            return 0
        
    @property
    def otlosscalc(self):
        if self.game_num.gamelength > 3600:
            if self.ea_club_num == self.game_num.a_team_num:
                if self.game_num.a_team_gf < self.game_num.h_team_gf:
                    return 1
                else:
                    return 0
            else:
                if self.game_num.h_team_gf < self.game_num.a_team_gf:
                    return 1
                else:
                    return 0
        else:
            return 0

    @property
    def shutoutcalc(self):
        if self.shots_against == self.saves:
            return 1
        else:
            return 0
        
    @property
    def savepctcalc(self):
        if self.shots_against > 0:
            savepct = (self.saves / self.shots_against) * 100
            return savepct
        else:
            return 0
    
    @property
    def gaacalc(self):
        if self.shots_against > 0:
            gaa = Decimal(((self.shots_against - self.saves) * 3600) / self.game_num.gamelength)
            return gaa
        else:
            return 0
    
    def save(self, *args, **kwargs):
        self.win = self.wincalc
        self.loss = self.losscalc
        self.otloss = self.otlosscalc
        self.shutout = self.shutoutcalc
        self.save_pct = self.savepctcalc
        self.gaa = self.gaacalc
        super(GoalieRecord, self).save(*args, **kwargs)

class TeamRecord(models.Model):
    game_num = models.ForeignKey(Game, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(Team, on_delete = models.CASCADE)
    home_away = models.BooleanField()
    goals_for = models.PositiveSmallIntegerField(default="0")
    goals_against = models.PositiveSmallIntegerField(default="0")
    pass_att_team = models.PositiveSmallIntegerField(default="0")
    pass_comp_team = models.PositiveSmallIntegerField(default="0")
    ppg_team = models.PositiveSmallIntegerField(default="0")
    ppo_team = models.PositiveSmallIntegerField(default="0")
    sog_team = models.PositiveSmallIntegerField(default="0")
    toa_team = models.PositiveSmallIntegerField(default="0")
    dnf = models.BooleanField(default="0")
    fow_team = models.PositiveSmallIntegerField(default="0")
    fol_team = models.PositiveSmallIntegerField(default="0")
    hits_team = models.PositiveSmallIntegerField(default="0")
    pims_team = models.PositiveSmallIntegerField(default="0")
    shg_team = models.PositiveSmallIntegerField(default="0")
    shot_att_team = models.PositiveSmallIntegerField(default="0")
    
class Standing(models.Model):
    PLAYOFF_STATUS_CHOICES = [
        ("x", "Clinched Playoff Spot"),
        ("y", "Clinched Division"),
        ("z", "Clinched Conference"),
        ("p", "President's Trophy"),
        ("", "No Status"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    otlosses = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    goalsfor = models.IntegerField(default=0)
    goalsagainst = models.IntegerField(default=0)
    gp = models.IntegerField(default=0)
    winperc = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    ppperc = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    pkperc = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    lastten = models.CharField(max_length=8, default="n/a")
    streak = models.CharField(max_length=4, default="n/a")
    playoffs = models.CharField(max_length=1, choices=PLAYOFF_STATUS_CHOICES, default="", blank=True, verbose_name="Playoff Status", help_text="Indicates playoff status of the team")

    class Meta:
        ordering = ['-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name']

class PlayoffRound(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, verbose_name="Season")
    round_num = models.PositiveSmallIntegerField(verbose_name="Round Number")  # e.g., 1 for first round, etc.
    round_name = models.CharField(max_length=50, verbose_name="Round Name", help_text="Name of the playoff round (e.g., Quarterfinals, Semifinals, Finals)")

    def __str__(self):
        return f"{self.season.season_text}, Round {self.round_num}"

class PlayoffSeries(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, verbose_name="Season")
    round_num = models.ForeignKey(PlayoffRound, on_delete=models.CASCADE, verbose_name="Round Number", related_name="series_in_round")
    low_seed = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="low_seed_series", verbose_name="Low Seed", null=True, blank=True)
    high_seed = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="high_seed_series", verbose_name="High Seed", null=True, blank=True)
    low_seed_num = models.PositiveSmallIntegerField(default=0, verbose_name="Low Seed Number", help_text="1 for lowest seed, 2 for second lowest, etc.", null=True, blank=True)
    high_seed_num = models.PositiveSmallIntegerField(default=0, verbose_name="High Seed Number", help_text="8 for highest seed, 7 for second highest, etc.", null=True, blank=True)
    low_seed_wins = models.PositiveSmallIntegerField(default=0, verbose_name="Low Seed Wins")
    high_seed_wins = models.PositiveSmallIntegerField(default=0, verbose_name="High Seed Wins")
    series_winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="series_winner", verbose_name="Series Winner")

    def update_series_winner(self):
        '''Automatically set the series winner if one team reaches 4 wins.'''
        if self.low_seed_wins >= 4:
            self.series_winner = self.low_seed
        elif self.high_seed_wins >= 4:
            self.series_winner = self.high_seed
        else:
            self.series_winner = None
        self.save()

class PlayoffConfig(models.Model):
    season = models.OneToOneField(
        Season,
        on_delete=models.CASCADE,
        related_name="playoff_config",
    )
    playoff_teams = models.PositiveSmallIntegerField(
        default=8,
        help_text="Total number of teams that qualify for playoffs from this season."
    )
    # TODO: add conference/division logic if needed
    # use_conferences = models.BooleanField(default=False)
    # teams_per_conference = models.PositiveSmallIntegerField(default=0)
    # etc.

    def __str__(self):
        return f"{self.season.season_text} playoff config"

class AwardVote(models.Model):
    ea_player_num = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name="Player")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name="Team", null=True)
    award_type = models.ForeignKey(AwardTitle, on_delete=models.CASCADE, verbose_name="Award")
    season_num = models.ForeignKey(Season, on_delete=models.CASCADE, verbose_name="Season")
    votes_num = models.SmallIntegerField(default=0, verbose_name="Votes")

    def __str__(self):
        return f"{self.season_num.season_text} - {self.award_type.award_Name} - {self.ea_player_num.username}"

class Leader(models.Model):
    attribute = models.CharField(max_length=3)
    player = models.ForeignKey(Player, blank=True, null=True, on_delete=models.CASCADE)
    stat = models.DecimalField(max_digits=5, decimal_places=2, default=0)

class BannedUser(models.Model):
    """Model to store banned users."""
    user = models.OneToOneField(Player, on_delete=models.CASCADE, verbose_name="Banned User")
    reason = models.TextField(verbose_name="Reason for Ban", help_text="Reason why the user was banned")
    ban_date = models.DateTimeField(auto_now_add=True, verbose_name="Ban Date", help_text="Date and time when the user was banned")
    ban_duration = models.DurationField(verbose_name="Ban Duration", help_text="Duration of the ban. Use '0' for permanent bans.", default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}"
    
class Announcement(models.Model):
    """Model to store announcements."""
    content = models.TextField(verbose_name="Announcement Content", help_text="Content of the announcement")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At", help_text="Date and time when the announcement was created")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Author", help_text="User who created the announcement", null=True, blank=True)

    def __str__(self):
        return f"Announcement by {self.author.username} on {self.created_at.strftime('%Y-%m-%d')}"
    
class PlayerAvailability(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    week_start = models.DateField(help_text="Sunday date for the start of the week")
    sunday = models.BooleanField(default=False)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True, help_text="Any extra info from the player")

    class Meta:
        unique_together = ('player', 'week_start')

    def __str__(self):
        return f"{self.player.username} availability for week of {self.week_start}"

class SkaterRating(models.Model):
    player   = models.ForeignKey(Player,  on_delete=models.CASCADE)
    season   = models.ForeignKey(Season,  on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True)
    # building blocks
    games_played   = models.PositiveSmallIntegerField(default=0)
    off_rat   = models.DecimalField(max_digits=6, decimal_places=2)
    def_rat   = models.DecimalField(max_digits=6, decimal_places=2)
    team_rat  = models.DecimalField(max_digits=6, decimal_places=2)
    ovr_rat  = models.DecimalField(max_digits=6, decimal_places=2)
    off_pct   = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    def_pct   = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    team_pct  = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ovr_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    weights_version = models.CharField(max_length=10, default="v1")       # easy A/B tests
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("player", "season", "position", "weights_version")
        ordering        = ["-ovr_pct", "player__username"]

    def __str__(self):
        return f"{self.player.username} - {self.position.positionShort} ({self.season.season_text}) - OVR: {self.ovr_pct:.2f}"
    
class GameSkaterRating(models.Model):
    skater_record = models.OneToOneField(SkaterRecord, on_delete=models.CASCADE, related_name='gameskaterrating')
    offense_rating = models.DecimalField(max_digits=6, decimal_places=2)
    defense_rating = models.DecimalField(max_digits=6, decimal_places=2)
    teamplay_rating = models.DecimalField(max_digits=6, decimal_places=2)
    game_result_bonus = models.DecimalField(max_digits=5, decimal_places=2)
    overall_rating = models.DecimalField(max_digits=6, decimal_places=2)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('skater_record',)
    
class GameGoalieRating(models.Model):
    goalie_record = models.OneToOneField(GoalieRecord, on_delete=models.CASCADE, related_name='gamegoalierating')
    goalie_rating = models.DecimalField(max_digits=6, decimal_places=2)
    teamplay_rating = models.DecimalField(max_digits=6, decimal_places=2)
    game_result_bonus = models.DecimalField(max_digits=6, decimal_places=2)
    overall_rating = models.DecimalField(max_digits=6, decimal_places=2)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('goalie_record',)

class GoalieRating(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)

    games_played = models.PositiveSmallIntegerField(default=0)
    gk_rat = models.DecimalField(max_digits=6, decimal_places=2)
    team_rat = models.DecimalField(max_digits=6, decimal_places=2)
    ovr_rat = models.DecimalField(max_digits=6, decimal_places=2)
    gk_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    team_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ovr_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    weights_version = models.CharField(max_length=10, default="v1")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("player", "season", "weights_version")
        ordering = ["-gk_pct", "player__username"]

    def __str__(self):
        return f"{self.player.username} (G) ({self.season.season_text}) - RAT: {self.gk_pct or 0:.2f}"

class TradeBlockPlayer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    listed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Optional notes about the trade value or desired return")

    def __str__(self):
        return f"{self.player.username} on block for {self.team.club_abbr}"

class TeamNeed(models.Model):
    TEAM_NEED_CHOICES = [
        ('any', 'Any'),
        ('key', 'Key'),
        ('core', 'Core'),
        ('depth', 'Depth'),
        ('prospect', 'Prospect'),
        ('avail', 'Schedule Availability'),
        ('cap', 'Cap Space'),
    ]
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.ManyToManyField(Position, blank=True, verbose_name="Position Needed")
    skill = models.CharField(max_length=10, choices=TEAM_NEED_CHOICES, default='any', verbose_name="Need Type")
    note = models.CharField(max_length=100, blank=True, help_text="E.g. 'Top-4 LD', 'Faceoff specialist', etc.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team.club_abbr} needs - {self.created_at}"

class Scheduling(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['game', 'team', 'position']

class Salary(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['player', 'season']

    def __str__(self):
        return f"{self.player.username} - {self.season.season_text} - ${self.amount:,.0f}"
    
class TeamServerBinding(models.Model):
    guild_id = models.BigIntegerField(unique=True, verbose_name="Discord Guild ID", help_text="The Discord server (guild) ID")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.guild_id} → {self.team.team_code if self.team else 'UNBOUND'}"
    
class PendingServerBinding(models.Model):
    guild_id = models.BigIntegerField(unique=True)
    requested_team = models.ForeignKey(Team, on_delete=models.CASCADE)
    requested_by = models.BigIntegerField()  # discord user ID
    requested_at = models.DateTimeField(auto_now_add=True)

class Signup(models.Model):
    """Season signup from a user/player."""

    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        verbose_name="Season",
        help_text="Season this signup applies to.",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Website User",
        help_text="Account used to submit the signup.",
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Linked Player (optional)",
        help_text="If linked, ties signup directly to a Player record.",
    )
    primary_position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="signup_primary",
        verbose_name="Primary Position",
    )
    secondary_positions = models.ManyToManyField(
        Position,
        blank=True,
        related_name="signup_secondary",
        verbose_name="Secondary Positions",
        help_text="Should include the primary position as well.",
    )
    days_per_week = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2), MaxValueValidator(5)],
        verbose_name="Nights per Week",
        help_text="How many nights per week the player can commit (2–5).",
    )
    scheduling_issues = models.TextField(
        blank=True,
        verbose_name="Scheduling Issues",
        help_text="Holidays, work constraints, etc.",
    )
    invited_by_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Invited By",
        help_text="Who invited them to the league (username or friend).",
    )
    committed_to_league = models.BooleanField(
        default=True,
        verbose_name="Committed to GHL",
        help_text="True if they intend to prioritize this league.",
    )
    other_league_obligations = models.TextField(
        blank=True,
        verbose_name="Other League Obligations",
        help_text="Any existing leagues/teams they also play with.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("season", "user")  # one signup per user per season
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} signup for {self.season.season_text}"

    def ensure_primary_in_secondaries(self):
        """Ensure primary position is always in the M2M secondaries."""
        if self.primary_position and self.pk:
            if not self.secondary_positions.filter(pk=self.primary_position.pk).exists():
                self.secondary_positions.add(self.primary_position)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After we have a PK, enforce the primary ∈ secondaries rule.
        self.ensure_primary_in_secondaries()

class WeeklyThreeStars(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    week_start = models.DateField()  # your GHL week start (Fri / Sun – whatever you're using)

    first_star = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="three_star_first"
    )
    second_star = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="three_star_second"
    )
    third_star = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="three_star_third"
    )

    blurb = models.TextField(blank=True)  # optional write-up for the bot to print
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("season", "week_start")

    def __str__(self):
        return f"{self.season} – week of {self.week_start} three stars"

class TwitchStreamer(models.Model):
    username = models.CharField(max_length=100, unique=True)
    user_id = models.CharField(max_length=100)
    subscribed = models.BooleanField(default=True)

    def __str__(self):
        return self.username

class Chirp(models.Model):
    text = models.TextField(
        help_text="Use {mention} where the target's Discord mention should go."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:40]}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Season)
def ensure_playoff_config(sender, instance: Season, created, **kwargs):
    """
    Ensure every regular-season Season has a PlayoffConfig.
    Runs on create and on update.
    """
    if created and instance.season_type == "regular":
        PlayoffConfig.objects.get_or_create(season=instance)