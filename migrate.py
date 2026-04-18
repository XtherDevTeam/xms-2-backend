"""
XmediaCenter 2 Upgrade Migration Script
This script will create playCount table and insert all existing songs into this table for all users.

@params databasePath str the database to connect
"""

import api.dataManager
import plugins.enabled

# params
databasePath = "./root/blob/xms.db"
appRoot = "./root"
pluginsPath = "./plugins"


database = api.dataManager.databaseObject(databasePath)
dataManager = api.dataManager.dataManager(database, appRoot, pluginsPath, plugins.enabled)

def createTable():
    dataManager.db.query("drop table if exists playCount;")
    dataManager.db.query(
        """
        create table playCount (
            id                  integer primary key autoincrement,
            path                string not null,
            owner               integer,
            plays               integer default 0
        );
        """
    )
    
def insertItem(path, owner):
    dataManager.db.query(
            "insert into playCount (path, owner) values (?, ?)", (path, owner))
    
def migrateData():
    playlist = dataManager.db.query("select * from playlists")
    for i in playlist:
        print(f"Migrating playlist '{i['name']}'(UID={i['owner']})...")
        songs = dataManager.db.query("select * from songList")
        for j in songs:
            print(f"Inserting {j['path']} into playCount...")
            insertItem(j['path'], i['owner'])
    
    result = len(dataManager.db.query("select * from playCount"))
    print(f"Done! Inserted {result} record(s).")
    database.db.commit()
    dataManager.db.close()
    
if __name__ == "__main__":
    createTable()
    migrateData()