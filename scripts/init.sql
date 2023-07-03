drop table if exists users;
drop table if exists config;
drop table if exists playlists;

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
    musicPlaybackCount  string default '{}',
    ownPlaylists        string default '[]'
);


create table playlists (
    id                  integer primary key autoincrement,
    name                string not null,
    owner               integer not null,
    description         string not null,
    creationDate        string not null,
    playCount           integer default 0,
    songs               string default '[]'
);


create table config (
    serverId            string  default 'YoimiyaGaTaisukidesu!',
    xmsRootPath         string default './root',
    xmsBlobPath         string default '$/blob',
    xmsDrivePath        string default '$/drive',
    host                string default '0.0.0.0',
    port                integer default 11453
);

insert into config (serverId) values ("YoimiyaGaTaisukidesu");