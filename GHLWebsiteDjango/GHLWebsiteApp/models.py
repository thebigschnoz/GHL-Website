from django.db import models

class Seasons(models.Model):
    season_num = models.AutoField(primary_key=True)
    season_text = models.CharField(max_length=50)
    isPlayoff = models.BooleanField(default=0)
    def __str__(self):
        return self.season_text

class TeamList(models.Model):
    ea_club_num = models.IntegerField(primary_key=True)
    club_full_name = models.CharField(max_length=50)
    club_abbr = models.CharField(max_length=3)
    club_location = models.CharField(max_length=25)
    team_logo_link = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.club_abbr

class Games(models.Model):
    game_num = models.AutoField(primary_key=True)
    season_num = models.ForeignKey(Seasons, on_delete=models.CASCADE)
    game_length = models.PositiveIntegerField(verbose_name="Game Length in seconds", default="3600", blank=True, null=True)
    expected_time = models.DateTimeField(verbose_name="Expected Game Time", blank=True, null=True)
    played_time = models.DateTimeField(verbose_name="Actual Game Time", blank=True, null=True)
    dnf = models.BooleanField(default=False, verbose_name="DNF", blank=True, null=True)
    a_team_num = models.ForeignKey(TeamList, on_delete=models.CASCADE, related_name="a_team")
    h_team_num = models.ForeignKey(TeamList, on_delete=models.CASCADE, related_name="h_team")
    a_team_gf = models.IntegerField(verbose_name="Away Score", default="0", blank=True)
    h_team_gf = models.IntegerField(verbose_name="Home Score", default="0", blank=True)
    a_team_points = models.PositiveSmallIntegerField(default="0", verbose_name="Away Team's Standings Points")
    h_team_points = models.PositiveSmallIntegerField(default="0", verbose_name="Home Team's Standings Points")

    @property
    def pointscalc(self):
        if self.game_length <= "3600":
            if self.a_team_gf > self.h_team_gf:
                new_a_team_points = "2"
                new_h_team_points = "0"
            else:
                new_a_team_points = "0"
                new_h_team_points = "2"
        else:
            if self.a_team_gf > self.h_team_gf:
                new_a_team_points = "2"
                new_h_team_points = "1"
            else:
                new_a_team_points = "1"
                new_h_team_points = "2"
        return new_a_team_points, new_h_team_points

    def save(self, *args, **kwargs):
        self.a_team_points = self.pointscalc[0]
        self.h_team_points = self.pointscalc[1]
        super(Games, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.a_team_num} @ {self.h_team_num},  {self.expected_time}"

class AwardsList(models.Model):
    award_num = models.IntegerField(primary_key=True)
    award_Name = models.CharField(max_length=50)
    award_Desc = models.TextField(blank=True)
    def __str__(self):
        return self.award_Name

class PlayerList(models.Model):
    ea_player_num = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=16)
    current_team = models.ForeignKey(TeamList, on_delete = models.CASCADE, blank=True, null=True)
    def __str__(self):
        return self.username

class Positions(models.Model):
    ea_pos = models.IntegerField(primary_key=True)
    position = models.CharField(max_length=20)
    positionShort = models.CharField(max_length=2)
    def __str__(self):
        return self.positionShort

class Builds(models.Model):
    ea_build = models.IntegerField(primary_key=True)
    build = models.CharField(max_length=25)
    buildShort = models.CharField(max_length=3)
    def __str__(self):
        return self.buildShort

class Awards(models.Model):
    award_num = models.AutoField(primary_key=True)
    ea_player_num = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    award_type = models.ForeignKey(AwardsList, on_delete = models.CASCADE)
    season_num = models.ForeignKey(Seasons, on_delete = models.CASCADE)
    def __str__(self):
        return f"{self.award_type} Season {self.season_num}"

class SkaterRecords(models.Model):
    ea_player_num = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    position = models.ForeignKey(Positions, on_delete = models.CASCADE)
    build = models.ForeignKey(Builds, on_delete = models.CASCADE)
    goals = models.PositiveSmallIntegerField(default="0")
    assists = models.PositiveSmallIntegerField(default="0")
    points = models.PositiveSmallIntegerField(default="0")
    hits = models.PositiveSmallIntegerField(default="0")
    plus_minus = models.SmallIntegerField(default="0")
    sog = models.PositiveSmallIntegerField(default="0")
    shot_attempts = models.PositiveSmallIntegerField(default="0")
    deflections = models.PositiveSmallIntegerField(default="0")
    ppg = models.PositiveSmallIntegerField(default="0")
    shg = models.PositiveSmallIntegerField(default="0")
    pass_att = models.PositiveSmallIntegerField(default="0")
    pass_comp = models.PositiveSmallIntegerField(default="0")
    saucer_pass = models.PositiveSmallIntegerField(default="0")
    blocked_shots = models.PositiveSmallIntegerField(default="0")
    takeaways = models.PositiveSmallIntegerField(default="0")
    interceptions = models.PositiveSmallIntegerField(default="0")
    giveaways = models.PositiveSmallIntegerField(default="0")
    pens_drawn = models.PositiveSmallIntegerField(default="0")
    pims = models.PositiveSmallIntegerField(default="0")
    pk_clears = models.PositiveSmallIntegerField(default="0")
    poss_time = models.PositiveSmallIntegerField(default="0")
    fow = models.PositiveSmallIntegerField(default="0")
    fol = models.PositiveSmallIntegerField(default="0")

    @property
    def pointscalc(self):
        totalpoints = self.goals + self.assists
        return totalpoints
    
    def save(self, *args, **kwargs):
        self.points = self.pointscalc
        super(SkaterRecords, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.ea_player_num} Game {self.game_num}"

class GoalieRecords(models.Model):
    ea_player_num = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    shots_against = models.PositiveSmallIntegerField(default="0")
    saves = models.PositiveSmallIntegerField(default="0")
    shutout = models.BooleanField(default="0")
    breakaway_shots = models.PositiveSmallIntegerField(default="0")
    breakaway_saves = models.PositiveSmallIntegerField(default="0")
    ps_shots = models.PositiveSmallIntegerField(default="0")
    ps_saves = models.PositiveSmallIntegerField(default="0")

    @property
    def shutoutcalc(self):
        if self.shots_against == self.saves:
            return 1
        else:
            return 0
    
    def save(self, *args, **kwargs):
        self.shutout = self.shutoutcalc
        super(GoalieRecords, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.ea_player_num} Game {self.game_num}"

class TeamRecords(models.Model):
    game_num = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(TeamList, on_delete = models.CASCADE)
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
    def __str__(self):
        return f"Club {self.ea_club_num} Game {self.game_num}"