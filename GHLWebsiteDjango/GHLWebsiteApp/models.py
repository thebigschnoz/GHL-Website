from django.db import models
from decimal import *

class Season(models.Model):
    season_num = models.AutoField(primary_key=True)
    season_text = models.CharField(max_length=50)
    isPlayoff = models.BooleanField(default=0)

class Team(models.Model):
    ea_club_num = models.IntegerField(primary_key=True)
    club_full_name = models.CharField(max_length=50)
    club_abbr = models.CharField(max_length=3)
    club_location = models.CharField(max_length=25)
    team_logo_link = models.TextField(blank=True, null=True)
    isActive = models.BooleanField(default=True)

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
    award_Name = models.CharField(max_length=50)
    award_Desc = models.TextField(blank=True)
    
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

class Build(models.Model):
    ea_build = models.IntegerField(primary_key=True)
    build = models.CharField(max_length=25)
    buildShort = models.CharField(max_length=3)

class AwardAssign(models.Model):
    award_num = models.AutoField(primary_key=True)
    ea_player_num = models.ForeignKey(Player, on_delete = models.CASCADE)
    award_type = models.ForeignKey(AwardTitle, on_delete = models.CASCADE)
    season_num = models.ForeignKey(Season, on_delete = models.CASCADE)

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
        if self.shot_attempts > 0:
            shotpct = (self.goals / self.shot_attempts) * 100
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
    winperc = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    ppperc = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    pkperc = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    lastten = models.CharField(max_length=8, default="n/a")
    streak = models.CharField(max_length=4, default="n/a")

    class Meta:
        ordering = ['-points', '-wins', '-goalsfor', 'goalsagainst', 'team__club_full_name']

    
class AwardVote(models.Model):
    ea_player_num = models.ForeignKey(Player, on_delete=models.CASCADE)
    award_num = models.ForeignKey(AwardTitle, on_delete=models.CASCADE)
    season_num = models.ForeignKey(Season, on_delete=models.CASCADE)
    votes_num = models.SmallIntegerField(default=0)

class Leader(models.Model):
    attribute = models.CharField(max_length=3)
    player = models.ForeignKey(Player, blank=True, null=True, on_delete=models.CASCADE)
    stat = models.DecimalField(max_digits=5, decimal_places=2, default=0)
