from django.db import models
from django.db.models.functions import Lower
from decimal import *

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
    ea_club_num = models.IntegerField(primary_key=True)
    club_full_name = models.CharField(max_length=50)
    club_abbr = models.CharField(max_length=3)
    club_location = models.CharField(max_length=25)
    team_logo_link = models.TextField(blank=True, null=True)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.club_full_name
    
    class Meta:
        ordering = [Lower('club_full_name')]

class Game(models.Model):
    game_num = models.AutoField(primary_key=True)
    season_num = models.ForeignKey(Season, on_delete=models.CASCADE)
    gamelength = models.PositiveIntegerField(verbose_name="Game Length in seconds", default="3600", blank=True, null=True)
    expected_time = models.DateTimeField(verbose_name="Expected Game Time", blank=True, null=True)
    played_time = models.DateTimeField(verbose_name="Actual Game Time", blank=True, null=True)
    dnf = models.BooleanField(default=False, verbose_name="DNF", blank=True, null=True)
    a_team_num = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="a_team")
    h_team_num = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="h_team")
    a_team_gf = models.IntegerField(verbose_name="Away Score", default="0", blank=True)
    h_team_gf = models.IntegerField(verbose_name="Home Score", default="0", blank=True)

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

class Player(models.Model):
    ea_player_num = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=16)
    current_team = models.ForeignKey(Team, on_delete = models.CASCADE, blank=True, null=True)
    primarypos = models.ForeignKey(Position, on_delete = models.CASCADE, related_name="primary", blank=True, null=True)
    secondarypos = models.ManyToManyField(Position, related_name="secondary", blank=True)
    playerpic = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username
    
    class Meta:
        ordering = [Lower('username')]

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
            shoteff = (self.sog / self.shot_attempts) * 100
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
    low_seed = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="low_seed_series", verbose_name="Low Seed")
    high_seed = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="high_seed_series", verbose_name="High Seed")
    low_seed_num = models.PositiveSmallIntegerField(default=0, verbose_name="Low Seed Number", help_text="1 for lowest seed, 2 for second lowest, etc.")
    high_seed_num = models.PositiveSmallIntegerField(default=0, verbose_name="High Seed Number", help_text="8 for highest seed, 7 for second highest, etc.")
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

    def __str__(self):
        return f"Round {self.round_num}: {self.low_seed.club_full_name} vs {self.high_seed.club_full_name}"

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
