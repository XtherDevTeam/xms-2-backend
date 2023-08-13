drop table if exists users;
drop table if exists config;
drop table if exists playlists;
drop table if exists songlist;
drop table if exists shareLinksList;
drop table if exists articles;
drop table if exists taskList;
drop table if exists settings;

create table users (
    id                  integer primary key autoincrement,
    name                string not null,
    slogan              string default 'Fireworks are for now, but friends are forever!',
    level               integer not null,
    passwordMd5         string not null,
    headImage           blob not null,
    headImageMime       string default 'image/jpeg',
    avatar              blob not null,
    avatarMime          string default 'image/jpeg',
    musicPlaybackCount  string default '{}'
);

-- songs are saved in songlist
create table playlists (
    id                  integer primary key autoincrement,
    name                string not null,
    owner               integer not null,
    description         string not null,
    creationDate        string not null,
    playCount           integer default 0
);

-- saved the songs from playlist
create table songlist (
    id                  integer primary key autoincrement,
    path                string not null,
    playlistId          integer not null,
    sortId              integer not null
);


-- saved users share links
create table shareLinksList (
    id                  string primary key,
    path                string not null,
    owner               integer not null
);


create table articles (
    id                  integer primary key,
    title               string not null,
    subtitle            string not null,
    creationTime        string not null,
    views               string not null,
    text                string not null
);


create table config (
    serverId            string  default 'YoimiyaGaTaisukidesu!',
    xmsRootPath         string default './root',
    xmsBlobPath         string default '$/blob',
    xmsDrivePath        string default '$/drive',
    host                string default '0.0.0.0',
    port                integer default 11453,
    proxyType           string default 'None',
    proxyUrl            string default '',
    allowRegister       integer default 0,
    enableInviteCode    integer default 0,
    inviteCode          string default ''
);

create table taskList (
    id                  integer primary key autoincrement,
    name                string not null,
    plugin              string not null,
    handler             string not null,
    args                string default '[]',
    logText             string default '',
    creationTime        string not null,
    endTime             string default '0000-00-00 00:00:00',
    owner               integer not null
);

insert into config (serverId) values ("YoimiyaGaTaisukidesu");