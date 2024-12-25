from django.db import models

# Create your models here.

class Seasons(models.Model):
    season_ID = models.AutoField(primary_key=True)
    season_text = models.CharField(max_length=50)
    isPlayoff = models.BooleanField()
    def __str__(self):
        return self.season_text

class Games(models.Model):
    game_ID = models.AutoField(primary_key=True)
    season_ID = models.ForeignKey(Seasons, on_delete=models.PROTECT)
    game_length = models.PositiveIntegerField()
    def __str__(self):
        return str(self.game_ID)

class AwardsList(models.Model):
    award_ID = models.IntegerField(primary_key=True)
    award_Name = models.CharField(max_length=50)
    award_Desc = models.TextField(blank=True)
    def __str__(self):
        return self.award_Name

class TeamList(models.Model):
    ea_club_ID = models.IntegerField(primary_key=True)
    club_full_name = models.CharField(max_length=50)
    club_abbr = models.CharField(max_length=3)
    club_location = models.CharField(max_length=25)
    team_logo_link = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.club_full_name

class PlayerList(models.Model):
    ea_player_ID = models.IntegerField(primary_key=True)
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
    award_ID = models.AutoField(primary_key=True)
    ea_player_ID = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    award_type = models.ForeignKey(AwardsList, on_delete = models.CASCADE)
    season_ID = models.ForeignKey(Seasons, on_delete = models.CASCADE)
    def __str__(self):
        return str(self.award_type) + " Season ID " + str(self.season_ID)

class SkaterRecords(models.Model):
    ea_player_ID = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_ID = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_ID = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    position = models.ForeignKey(Positions, on_delete = models.CASCADE)
    build = models.ForeignKey(Builds, on_delete = models.CASCADE)
    goals = models.PositiveSmallIntegerField()
    assists = models.PositiveSmallIntegerField()
    hits = models.PositiveSmallIntegerField()
    plus_minus = models.SmallIntegerField()
    sog = models.PositiveSmallIntegerField()
    shot_attempts = models.PositiveSmallIntegerField()
    deflections = models.PositiveSmallIntegerField()
    ppg = models.PositiveSmallIntegerField()
    shg = models.PositiveSmallIntegerField()
    pass_att = models.PositiveSmallIntegerField()
    pass_comp = models.PositiveSmallIntegerField()
    saucer_pass = models.PositiveSmallIntegerField()
    blocked_shots = models.PositiveSmallIntegerField()
    takeaways = models.PositiveSmallIntegerField()
    interceptions = models.PositiveSmallIntegerField()
    giveaways = models.PositiveSmallIntegerField()
    pens_drawn = models.PositiveSmallIntegerField()
    pims = models.PositiveSmallIntegerField()
    pk_clears = models.PositiveSmallIntegerField()
    poss_time = models.PositiveSmallIntegerField()
    fow = models.PositiveSmallIntegerField()
    fol = models.PositiveSmallIntegerField()
    def __str__(self):
        return str(self.ea_player_ID) + " Game " + str(self.game_ID)

class GoalieRecords(models.Model):
    ea_player_ID = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_ID = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_ID = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    shots_against = models.PositiveSmallIntegerField()
    saves = models.PositiveSmallIntegerField()
    breakaway_shots = models.PositiveSmallIntegerField()
    breakaway_saves = models.PositiveSmallIntegerField()
    ps_shots = models.PositiveSmallIntegerField()
    ps_saves = models.PositiveSmallIntegerField()
    def __str__(self):
        return str(self.ea_player_ID) + " Game " + str(self.game_ID)

class TeamRecords(models.Model):
    game_ID = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_ID = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    home_away = models.BooleanField()
    goals_for = models.PositiveSmallIntegerField()
    goals_against = models.PositiveSmallIntegerField()
    pass_att_team = models.PositiveSmallIntegerField()
    pass_comp_team = models.PositiveSmallIntegerField()
    ppg_team = models.PositiveSmallIntegerField()
    ppo_team = models.PositiveSmallIntegerField()
    sog_team = models.PositiveSmallIntegerField()
    toa_team = models.PositiveSmallIntegerField()
    dnf = models.BooleanField()
    fow_team = models.PositiveSmallIntegerField()
    fol_team = models.PositiveSmallIntegerField()
    hits_team = models.PositiveSmallIntegerField()
    pims_team = models.PositiveSmallIntegerField()
    shg_team = models.PositiveSmallIntegerField()
    shot_att_team = models.PositiveSmallIntegerField()
    def __str__(self):
        return "Club " + str(self.ea_club_ID) + " Game " + str(self.game_ID)