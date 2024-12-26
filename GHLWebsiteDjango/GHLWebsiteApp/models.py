from django.db import models

class Seasons(models.Model):
    season_num = models.AutoField(primary_key=True)
    season_text = models.CharField(max_length=50)
    isPlayoff = models.BooleanField()
    def __str__(self):
        return self.season_text

class Games(models.Model):
    game_num = models.AutoField(primary_key=True)
    season_num = models.ForeignKey(Seasons, on_delete=models.PROTECT)
    game_length = models.PositiveIntegerField()
    def __str__(self):
        return str(self.game_num)

class AwardsList(models.Model):
    award_num = models.IntegerField(primary_key=True)
    award_Name = models.CharField(max_length=50)
    award_Desc = models.TextField(blank=True)
    def __str__(self):
        return self.award_Name

class TeamList(models.Model):
    ea_club_num = models.IntegerField(primary_key=True)
    club_full_name = models.CharField(max_length=50)
    club_abbr = models.CharField(max_length=3)
    club_location = models.CharField(max_length=25)
    team_logo_link = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.club_full_name

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
        return str(self.award_type) + " Season ID " + str(self.season_num)

class SkaterRecords(models.Model):
    ea_player_num = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    position = models.ForeignKey(Positions, on_delete = models.CASCADE)
    build = models.ForeignKey(Builds, on_delete = models.CASCADE)
    goals = models.PositiveSmallIntegerField(default="0")
    assists = models.PositiveSmallIntegerField(default="0")
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
    def __str__(self):
        return str(self.ea_player_num) + " Game " + str(self.game_num)

class GoalieRecords(models.Model):
    ea_player_num = models.ForeignKey(PlayerList, on_delete = models.CASCADE)
    game_num = models.ForeignKey(Games, on_delete = models.CASCADE)
    ea_club_num = models.ForeignKey(TeamList, on_delete = models.CASCADE)
    shots_against = models.PositiveSmallIntegerField(default="0")
    saves = models.PositiveSmallIntegerField(default="0")
    breakaway_shots = models.PositiveSmallIntegerField(default="0")
    breakaway_saves = models.PositiveSmallIntegerField(default="0")
    ps_shots = models.PositiveSmallIntegerField(default="0")
    ps_saves = models.PositiveSmallIntegerField(default="0")
    def __str__(self):
        return str(self.ea_player_num) + " Game " + str(self.game_num)

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
        return "Club " + str(self.ea_club_num) + " Game " + str(self.game_num)