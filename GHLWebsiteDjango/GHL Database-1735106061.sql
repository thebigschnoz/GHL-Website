CREATE TABLE IF NOT EXISTS `AwardsList` (
	`awardid` INTEGER NOT NULL,
	`awardname` TEXT NOT NULL,
	`awarddesc` TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS `Awards` (
	`awardid` INTEGER NOT NULL,
	`eaplayerid` INTEGER NOT NULL,
	`awardtype` INTEGER NOT NULL,
	`seaonid` INTEGER NOT NULL,
FOREIGN KEY(`eaplayerid`) REFERENCES `PlayerList`(`eaplayerid`),
FOREIGN KEY(`awardtype`) REFERENCES `AwardsList`(`awardid`),
FOREIGN KEY(`seaonid`) REFERENCES `Seasons`(`seasonid`)
);
CREATE TABLE IF NOT EXISTS `Seasons` (
	`seasonid` INTEGER NOT NULL,
	`seasontext` TEXT NOT NULL,
	`isplayoff` REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS `Games` (
	`gameid` INTEGER NOT NULL,
	`seasonid` INTEGER NOT NULL,
	`length` INTEGER NOT NULL,
FOREIGN KEY(`seasonid`) REFERENCES `Seasons`(`seasonid`)
);
CREATE TABLE IF NOT EXISTS `PlayerList` (
	`eaplayerid` INTEGER NOT NULL,
	`username` TEXT NOT NULL UNIQUE,
	`currentteam` INTEGER
);
CREATE TABLE IF NOT EXISTS `TeamList` (
	`eaclubid` INTEGER NOT NULL,
	`clubfullname` TEXT NOT NULL,
	`clubabbr` TEXT NOT NULL,
	`clublocation` TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS `GoalieRecords` (
	`eaplayerid` INTEGER NOT NULL,
	`gameid` INTEGER NOT NULL,
	`eaclubid` INTEGER NOT NULL,
	`shotsagainst` INTEGER NOT NULL,
	`saves` INTEGER NOT NULL,
	`breakawayshots` INTEGER NOT NULL,
	`breakawaysaves` INTEGER NOT NULL,
	`psshots` INTEGER NOT NULL,
	`pssaves` INTEGER NOT NULL,
FOREIGN KEY(`eaplayerid`) REFERENCES `PlayerList`(`eaplayerid`),
FOREIGN KEY(`gameid`) REFERENCES `Games`(`gameid`),
FOREIGN KEY(`eaclubid`) REFERENCES `TeamList`(`eaclubid`)
);
CREATE TABLE IF NOT EXISTS `SkaterRecords` (
	`eaplayerid` INTEGER NOT NULL,
	`gameid` INTEGER NOT NULL,
	`eaclubid` INTEGER NOT NULL,
	`position` INTEGER NOT NULL,
	`build` INTEGER NOT NULL,
	`goals` INTEGER NOT NULL,
	`assists` INTEGER NOT NULL,
	`hits` INTEGER NOT NULL,
	`plusminus` INTEGER NOT NULL,
	`sog` INTEGER NOT NULL,
	`totalshots` INTEGER NOT NULL,
	`deflections` INTEGER NOT NULL,
	`ppg` INTEGER NOT NULL,
	`shg` INTEGER NOT NULL,
	`passatt` INTEGER NOT NULL,
	`passcomp` INTEGER NOT NULL,
	`saucerpass` INTEGER NOT NULL,
	`bs` INTEGER NOT NULL,
	`takeaways` INTEGER NOT NULL,
	`interceptions` INTEGER NOT NULL,
	`giveaways` INTEGER NOT NULL,
	`pensdrawn` INTEGER NOT NULL,
	`pims` INTEGER NOT NULL,
	`pkclears` INTEGER NOT NULL,
	`posstime` INTEGER NOT NULL,
	`fow` INTEGER NOT NULL,
	`fol` INTEGER NOT NULL,
FOREIGN KEY(`eaplayerid`) REFERENCES `PlayerList`(`eaplayerid`),
FOREIGN KEY(`gameid`) REFERENCES `Games`(`gameid`),
FOREIGN KEY(`eaclubid`) REFERENCES `TeamList`(`eaclubid`)
);
CREATE TABLE IF NOT EXISTS `TeamRecords` (
	`gameid` INTEGER NOT NULL,
	`eaclubid` INTEGER NOT NULL,
	`homeaway` REAL NOT NULL,
	`goalsfor` INTEGER NOT NULL,
	`goalsagainst` INTEGER NOT NULL,
	`passattteam` INTEGER NOT NULL,
	`passcompteam` INTEGER NOT NULL,
	`ppgteam` INTEGER NOT NULL,
	`ppoteam` INTEGER NOT NULL,
	`sogteam` INTEGER NOT NULL,
	`toateam` INTEGER NOT NULL,
	`dnf` REAL NOT NULL,
	`fowteam` INTEGER NOT NULL,
	`folteam` INTEGER NOT NULL,
	`hitsteam` INTEGER NOT NULL,
	`pimteam` INTEGER NOT NULL,
	`shgteam` INTEGER NOT NULL,
	`shotattteam` INTEGER NOT NULL,
FOREIGN KEY(`gameid`) REFERENCES `Games`(`gameid`),
FOREIGN KEY(`eaclubid`) REFERENCES `TeamList`(`eaclubid`)
);
CREATE TABLE IF NOT EXISTS `Positions` (
	`eapos` INTEGER NOT NULL,
	`position` TEXT NOT NULL,
FOREIGN KEY(`eapos`) REFERENCES `SkaterRecords`(`position`)
);
CREATE TABLE IF NOT EXISTS `Builds` (
	`eabuild` INTEGER NOT NULL,
	`buildname` TEXT NOT NULL,
FOREIGN KEY(`eabuild`) REFERENCES `SkaterRecords`(`build`)
);