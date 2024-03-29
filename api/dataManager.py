import sqlite3
import api.utils as utils
import logging
import os
import mimetypes
import time
import json
import sys
import threading
from typing import Any


def getCurrentTime():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))


class databaseObject:
    def __init__(self, dbPath: str) -> None:
        self.db = sqlite3.connect(dbPath, check_same_thread=False)

    def query(self, query, args=(), one=False):
        cur = self.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
                   for idx, value in enumerate(row)) for row in cur.fetchall()]
        lastrowid = cur.lastrowid
        cur.close()
        if query.startswith('insert'):
            return lastrowid
        else:
            return (rv[0] if rv else None) if one else rv

    def runScript(self, query: str):
        self.db.executescript(query)
        self.db.commit()
        return None

    def close(self):
        self.db.close()


class dataManager:
    class taskInfo:
        def __init__(self, dbObject: databaseObject, taskId: int):
            self.db = dbObject
            self.id = taskId

        def setLogText(self, text: str):
            self.db.query(
                "update taskList set logText = ? where id = ?", (text, self.id))

        def ended(self):
            self.db.query(
                "update taskList set endTime = ? where id = ?", (getCurrentTime(), self.id))

    def __init__(self, dbObject: databaseObject, appRoot: str, pluginsPath: str, enabledModule) -> None:
        self.db = dbObject
        self._logger = logging.getLogger("dataManager")
        self.plugins = {}
        for i in enabledModule.enabled:
            data = i.registry()
            self.plugins[data['name']] = {'info': data, 'handlers': i.handlers}

    def logger(self) -> logging.Logger:
        return self._logger

    def getXmsBlobPath(self):
        try:
            d = self.db.query("select xmsBlobPath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:

                return utils.makeResult(True, d['xmsBlobPath'].replace(
                    '$', utils.catchError(self.logger(), self.getXmsRootPath())))
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsRootPath(self):
        try:
            d = self.db.query("select xmsRootPath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['xmsRootPath'])
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsDrivePath(self):
        try:
            d = self.db.query("select xmsDrivePath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['xmsDrivePath'].replace(
                    '$', utils.catchError(self.logger(), self.getXmsRootPath())))
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsHost(self):
        try:
            d = self.db.query("select host from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['host'])
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsPort(self):
        try:
            d = self.db.query("select port from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['port'])
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def executeInitScript(self, scriptPath: str = './scripts/init.sql'):
        try:
            self.logger().debug(
                f"trying to executing initScript (path={scriptPath})...")
            with open(scriptPath, 'r') as file:
                try:
                    self.db.runScript(file.read())
                    return utils.makeResult(True, "success")
                except sqlite3.Error as e:
                    return utils.makeResult(False, str(e))
        except Exception as e:
            return utils.makeResult(False, str(e))

    def updateXmsRootPath(self, newRootPath: str):
        try:
            self.db.query("update config set xmsRootPath = ?", (newRootPath, ))
            return utils.makeResult(True, "success")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateXmsBlobPath(self, newBlobPath: str):
        try:
            self.db.query("update config set xmsBlobPath = ?", (newBlobPath, ))
            return utils.makeResult(True, "success")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateXmsDrivePath(self, newDrivePath: str):
        try:
            self.db.query("update config set xmsDrivePath = ?",
                          (newDrivePath, ))
            return utils.makeResult(True, "success")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateXmsHost(self, newHost: str):
        try:
            self.db.query("update config set host = ?", (newHost, ))
            return utils.makeResult(True, "success")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateXmsPort(self, newPort: int):
        try:
            self.db.query("update config set port = ?", (newPort, ))
            return utils.makeResult(True, "success")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsConfig(self):
        return utils.makeResult(True, self.db.query("select * from config", one=True))

    def updateXmsConfig(self, config):
        try:
            self.db.query("update config set serverId = ?, xmsRootPath = ?, xmsBlobPath = ?, xmsDrivePath = ?, host = ?, port = ?, proxyType = ?, proxyUrl = ?, allowRegister = ?, enableInviteCode = ?, inviteCode = ?",
                          (config['serverId'], config['xmsRootPath'], config['xmsBlobPath'], config['xmsDrivePath'], config['host'], config['port'], config['proxyType'], config['proxyUrl'], config['allowRegister'], config['enableInviteCode'], config['inviteCode']))
            return utils.makeResult(True, "success")
        except KeyError as e:
            return utils.makeResult(False, f"invalid request: missing {e}")

    # use username instead of uid because system don't know uid when creating user
    # update: done some tricks to query function, now it will return lastRowId a.k.a uid
    def createUserDrive(self, uid: str):
        drivePath = utils.catchError(self.logger(), self.getXmsDrivePath())
        try:
            os.makedirs(f"{drivePath}/{uid}", exist_ok=True)
            return utils.makeResult(True, "success")
        except Exception as e:
            return utils.makeResult(False, str(e))

    def deleteUserDrive(self, uid: int):
        drivePath = utils.catchError(self.logger(), self.getXmsDrivePath())
        if self.checkIfUserExistById(uid) is None:
            return utils.makeResult(False, "user not exist while deleting user drive")
        else:
            try:
                utils.rmdir(f"{drivePath}/{uid}")
                return utils.makeResult(True, "success")
            except OSError as e:
                return utils.makeResult(False, f"unable to delete user drive: {str(e)}")

    def createUser(self, userName: str, userPassword: str, userSlogan: str, level: int):
        if not utils.checkIfUserNameValid(userName):
            return utils.makeResult(False, "invalid username")

        if self.checkIfUserExistByUserName(userName) is not None:
            return utils.makeResult(False, "user with the same username already exists")

        try:
            # 0 is user, 1 is admin, 2 is superadmin
            with open(utils.catchError(self.logger(), self.getXmsBlobPath()) + "/avatar.jpg", "rb+") as a:
                with open(utils.catchError(self.logger(), self.getXmsBlobPath()) + "/headImage.jpg", "rb+") as b:
                    uid = self.db.query("insert into users (name, slogan, level, passwordMd5, avatar, headImage) values (?,?,?,?,?,?)",
                                        (userName, userSlogan, level, utils.makePasswordMd5(userPassword), a.read(), b.read()))
                    return self.createUserDrive(uid)
        except Exception as e:
            return utils.makeResult(False, str(e))

    def getUserDrivePath(self, uid: int):
        if self.checkIfUserExistById(uid) is None:
            return utils.makeResult(False, "user not exist")

        drivePath = utils.catchError(self.logger(), self.getXmsDrivePath())
        return utils.makeResult(True, f"{drivePath}/{uid}")

    def getUserDriveDirInfo(self, uid: int, path: str):
        # in this step, we can make sure that the uid is valid
        filesCnt = 0
        files = []
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            try:
                dir = os.listdir(base)
                for i in dir:
                    fullPath = os.path.join(base, i)
                    fileInfo = utils.getPathInfo(fullPath)
                    fileInfo["path"] = os.path.join(path, i)
                    files.append(fileInfo)
                    filesCnt += int(fileInfo["type"] == "file")
                return utils.makeResult(True, {
                    "list": files,
                    "info": {
                        "total": len(files),
                        "files": filesCnt,
                        "dirs": len(files) - filesCnt
                    }
                })
            except Exception as e:
                return utils.makeResult(False, str(e))
        else:
            return base

    def createDirInUserDrive(self, uid: int, path: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            try:
                os.makedirs(base, 0o777)
                return utils.makeResult(True, "success")
            except OSError as e:
                return utils.makeResult(False, str(e))
        else:
            return base

    def updateSongPathInSongList(self, oldPath: str, newPath: str):
        self.db.query(
            "update songlist set path = ? where path = ?", (newPath, oldPath))

    def renameInUserDrive(self, uid: int, path: str, newName: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            newPath = os.path.join(os.path.dirname(base), newName)
            try:
                mime = mimetypes.guess_type(base)[0]
                if mime is not None and mime.startswith('audio/'):
                    self.updateSongPathInSongList(base, newPath)
                os.rename(base, newPath)
            except OSError as e:
                return utils.makeResult(False, str(e))

            return utils.makeResult(True, "success")
        else:
            return base

    def moveInUserDrive(self, uid: int, path: str, newPath: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            newBase = f"{base['data']}/{path}"
            newPath = f"{base['data']}/{newPath}/{os.path.basename(newBase)}"
            try:
                self.updateSongPathInSongList(newBase, newPath)
                utils.move(newBase, newPath)
            except utils.shutil.Error as e:
                return utils.makeResult(False, str(e))

            return utils.makeResult(True, "success")
        else:
            return base

    def copyInUserDrive(self, uid: int, path: str, newPath: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            newBase = f"{base['data']}/{path}"
            newPath = f"{base['data']}/{newPath}/{os.path.basename(newBase)}"

            try:
                utils.copy(newBase, newPath)
            except utils.shutil.Error as e:
                return utils.makeResult(False, str(e))

            return utils.makeResult(True, "success")
        else:
            return base

    def deleteInUserDrive(self, uid: int, path: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            try:
                if os.path.isfile(base):
                    self.db.query("delete from playCount where path = ?", (path, ))
                    self.db.query("delete from songList where path = ?", (path, ))
                    os.remove(base)
                else:
                    utils.rmdir(base)

                return utils.makeResult(True, "success")
            except OSError as e:
                return utils.makeResult(False, str(e))
        else:
            return base

    def queryFileRealpath(self, uid: int, path: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            try:
                if os.path.isfile(base):
                    mime = mimetypes.guess_type(path)[0]
                    if mime is None:
                        mime = 'application/octet-stream'
                    return utils.makeResult(True, {"path": base, "mime": mime})
                else:
                    return utils.makeResult(False, f"not a file: {path}")
            except OSError as e:
                return utils.makeResult(False, str(e))
        else:
            return base

    def queryFileUploadRealpath(self, uid: int, path: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            return utils.makeResult(True, base)
        else:
            return base

    def queryUser(self, uid: int):
        try:
            d = self.db.query(
                "select id, name, slogan, level from users where id = ?", (uid, ), one=True)
            if d is not None:
                return utils.makeResult(True, d)
            else:
                return utils.makeResult(False, "user not found")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def deleteUser(self, uid: int):
        if self.checkIfUserExistById(uid) is None:
            return utils.makeResult(False, "user not exist")
        else:
            self.deleteUserDrive(uid)
            self.db.query("delete from users where id = ?")
            return utils.makeResult(True, "success")

    def checkIfUserExistById(self, uid: int):
        try:
            d = self.db.query(
                "select id from users where id = ?", (uid, ), one=True)
            if d is not None:
                return d['id']
            else:
                return None
        except sqlite3.Error as e:
            return None

    def checkIfUserExistByUserName(self, username: str):
        try:
            d = self.db.query(
                "select id from users where name = ?", (username, ), one=True)
            if d is not None:
                return d['id']
        except sqlite3.Error as e:
            return None

    def getUserAvatar(self, uid: int):
        try:
            d = self.db.query(
                "select avatar, avatarMime from users where id = ?", (uid, ), one=True)

            if d is not None:
                return utils.makeResult(True, d)
            else:
                return utils.makeResult(False, "user not found")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getUserHeadImage(self, uid: int):
        try:
            d = self.db.query(
                "select headImage, headImageMime from users where id = ?", (uid, ), one=True)
            if d is not None:
                return utils.makeResult(True, d)
            else:
                return utils.makeResult(False, "user not found")
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateUserUsername(self, uid: int, newUserName: str):
        try:
            d = self.db.query(
                "update users set name = ? where id = ?", (newUserName, uid))
            return utils.makeResult(True, d)
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateUserSlogan(self, uid: int, newSlogan: str):
        try:
            d = self.db.query(
                "update users set slogan = ? where id = ?", (newSlogan, uid))
            return utils.makeResult(True, d)
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def queryUserPassword(self, uid: int):
        try:
            d = self.db.query(
                "select passwordMd5 from users where id = ?", (uid, ), one=True)
            if d is None:
                return utils.makeResult(False, "user not exist")
            else:
                return utils.makeResult(True, d['passwordMd5'])
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def updateUserPassword(self, uid: int, oldPwd: str, newPwd: str):
        d = self.queryUserPassword(uid)
        if d['ok']:
            if d['data'] != utils.makePasswordMd5(oldPwd):
                return utils.makeResult(False, "old password not match")
            self.db.query("update users set passwordMd5 = ? where id = ?",
                          (utils.makePasswordMd5(newPwd), uid))
            return utils.makeResult(True, "success")
        else:
            return utils.makeResult(False, "user not exist")

    def updateUserAvatar(self, uid: int, avatar: bytes, mime: str):
        uid = self.checkIfUserExistById(uid)
        if uid is not None:
            try:
                self.db.query(
                    "update users set avatar = ?, avatarMime = ? where id = ?", (avatar, mime, uid))
                return utils.makeResult(True, "success")
            except sqlite3.Error as e:
                return utils.makeResult(False, str(e))

    def updateUserHeadImage(self, uid: int, headImage: bytes, mime: str):
        uid = self.checkIfUserExistById(uid)
        if uid is not None:
            try:
                self.db.query(
                    "update users set headImage = ?, headImageMime = ? where id = ?", (headImage, mime, uid))
                return utils.makeResult(True, "success")
            except sqlite3.Error as e:
                return utils.makeResult(False, str(e))

    def vertifyUserLogin(self, username: str, password: str):
        uid = self.checkIfUserExistByUserName(username)
        if uid is not None:
            if self.queryUserPassword(uid)['data'] == utils.makePasswordMd5(password):
                return uid
            else:
                return None
        else:
            return None

    def checkUserPlaylistIfExistByPlaylistName(self, uid: int, name: str):
        d = self.db.query(
            "select id from playlists where name = ? and owner = ?", (name, uid), one=True)
        if d is not None:
            return d['id']
        else:
            return d

    def checkUserPlaylistIfExistByPlaylistId(self, id: int):
        d = self.db.query(
            "select id, owner from playlists where id = ?", (id, ), one=True)
        return d

    def queryUserOwnPlaylists(self, uid: int):
        data = self.db.query(
            "select * from playlists where owner = ?", (uid, ))
        return data

    def queryUserOwnTaskList(self, uid: int):
        data = self.db.query(
            "select id, name, plugin, handler, creationTime, endTime from taskList where owner = ? order by id desc", (uid, ))
        return utils.makeResult(True, data)

    def queryPlaylistArtwork(self, playlistId: int):
        data = self.db.query(
            "select id from songlist where playlistId = ? order by sortId desc limit ?", (playlistId, 1), one=True)
        blobPath = utils.catchError(self.logger(), self.getXmsBlobPath())
        if data == None:
            with open(f'{blobPath}/defaultArtwork.png', 'rb') as default:
                return utils.makeResult(True, {"artwork": default.read(), "mime": "image/png"})
        return self.querySongArtworkFromPlaylist(data['id'])

    def createUserPlaylist(self, uid: int, name: str, description: str):
        if self.checkUserPlaylistIfExistByPlaylistName(uid, name) is not None:
            return utils.makeResult(False, "playlist with the same playlist name already exists")
        if self.checkIfUserExistById(uid) is not None:
            self.db.query("insert into playlists (name, owner, description, creationDate) values (?, ?, ?, ?)",
                          (name, uid, description, getCurrentTime()))

            playlistId = self.checkUserPlaylistIfExistByPlaylistName(uid, name)
            data = self.queryUserOwnPlaylists(uid)
            data.append(playlistId)
            return utils.makeResult(True, playlistId)
        else:
            return utils.makeResult(False, "user not exist")

    def deleteUserPlaylistById(self, id: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(id)
        if data is None:
            return utils.makeResult(False, "playlist not exist")
        else:
            self.db.query("delete from playlists where id = ?", (id, ))
            return utils.makeResult(True, "success")

    def checkIfSongExistInPlaylistByPath(self, playlistId: int, songPath: str):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        return self.db.query("select id from songlist where path = ? and playlistId = ?", (songPath, playlistId), one=True)

    def checkIfSongExistInPlaylistById(self, playlistId: int, songId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        return self.db.query("select * from songlist where id = ?", (songId, ), one=True)

    def getPlaylistSongsCount(self, playlistId: int):
        return self.db.query("select count(1) as count from songlist where playlistId = ?", (playlistId, ), one=True)['count']

    def increasePlaylistPlayCount(self, playlistId: int):
        if self.checkUserPlaylistIfExistByPlaylistId(playlistId) is None:
            return utils.makeResult(False, "playlist not exist")
        
        self.db.query("update playlists set playCount = ? where id = ?", (self.db.query("select playCount from playlists where id = ?", (playlistId, ), one=True)['playCount']+1, playlistId))
        return utils.makeResult(True, "success")

    def increaseSongPlayCount(self, uid: int, songId: int):
        if self.checkIfUserExistById(uid) is None:
            return utils.makeResult(False, "user not exist")
        
        data = self.querySongFromPlaylist(songId)
        
        if data["ok"]:
            print(data)
            plays = self.db.query("select plays from playCount where path = ? and owner = ?", (data["data"]["path"], uid), one=True)["plays"]
            plays += 1
            self.db.query("update playCount set plays = ? where path = ? and owner = ?", (plays, data["data"]["path"], uid))
            return utils.makeResult(True, "success")
        
        return utils.makeResult(False, "song not exist")
    
    def insertSongToPlaylist(self, playlistId: int, songPath: str):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        if self.checkIfSongExistInPlaylistByPath(playlistId, songPath) is not None:
            return utils.makeResult(False, "the song has already been in the playlist")

        sortId = self.db.query('select sortId from songlist order by sortId desc limit 1', one=True)
        self.db.query(
            "insert into songlist (path, playlistId, sortId) values (?, ?, ?)", (songPath, playlistId, sortId['sortId'] + 1 if sortId is not None else 0))
        if len(self.db.query('select 1 from playCount where path = ?', (songPath, ))) == 0:
            self.db.query(
                "insert into playCount (path, owner) values (?, ?)", (songPath, data['owner']))

        return utils.makeResult(
            True, self.checkIfSongExistInPlaylistByPath(playlistId, songPath)['id'])

    def deleteSongFromPlaylist(self, playlistId: int, songId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        if self.checkIfSongExistInPlaylistById(playlistId, songId) is None:
            return utils.makeResult(False, "the song isn't in the playlist")

        self.db.query("delete from songlist where id = ?", (songId, ))
        return utils.makeResult(True, "success")

    def queryUserPlaylistSongs(self, playlistId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        songs = self.db.query(
            "select * from songlist where playlistId = ? order by sortId desc", (playlistId, ))

        for i in songs:
            i['info'] = utils.getSongInfo(utils.catchError(
                self.logger(), self.queryFileRealpath(data['owner'], i['path']))['path'])

        return utils.makeResult(True, songs)

    def querySongFromPlaylist(self, songId: int):
        data = self.db.query(
            "select path, playlistId, sortId from songlist where id = ?", (songId, ), one=True)

        if data is None:
            return utils.makeResult(False, "song not exist")

        playlist = self.queryUserPlaylistInfo(
            data['playlistId'])['data']

        songInfo = utils.getSongInfo(utils.catchError(
            self.logger(), self.queryFileRealpath(playlist['owner'], data['path']))['path'])
        songInfo['owner'] = playlist['owner']
        songInfo['path'] = data['path']

        return utils.makeResult(True, songInfo)

    def querySongArtworkFromPlaylist(self, songId: int):
        data = self.db.query(
            "select path, playlistId from songlist where id = ?", (songId, ), one=True)
        if data is None:
            return utils.makeResult(False, "song not exist")

        playlist = self.queryUserPlaylistInfo(
            data['playlistId'])['data']

        try:
            return utils.makeResult(True, utils.getSongArtwork(utils.catchError(
                self.logger(), self.queryFileRealpath(playlist['owner'], data['path']))['path']))
        except Exception as e:
            print(e)
            blobPath = utils.catchError(self.logger(), self.getXmsBlobPath())

            with open(f'{blobPath}/defaultArtwork.png', 'rb') as default:
                return utils.makeResult(True, {"artwork": default.read(), "mime": "image/png"})

    def updatePlaylistInfo(self, playlistId: int, uid: int, name: str, description: str):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")
        elif data['owner'] != uid:
            return utils.makeResult(False, "user isn't the owner of the playlist")

        self.db.query("update playlists set name = ?, description = ? where id = ?",
                      (name, description, playlistId, ))

        return utils.makeResult(True, "success")

    def queryUserPlaylistInfo(self, playlistId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        d = self.db.query(
            "select * from playlists where id = ?", (playlistId, ), one=True)
        return utils.makeResult(True, d)

    def swapTwoSongsInPlaylistSongList(self, src: int, dest: int):
        srcData = self.db.query(
            "select sortId, id from songlist where id = ?", (src, ), one=True)
        destData = self.db.query(
            "select sortId, id from songlist where id = ?", (dest, ), one=True)
        if srcData is None:
            return utils.makeResult(False, f'SongId({src}) not exist')
        elif destData is None:
            return utils.makeResult(False, f'SongId({src}) not exist')

        self.db.query("update songlist set sortId = ? where id = ?",
                      (destData['sortId'], srcData['id']))
        self.db.query("update songlist set sortId = ? where id = ?",
                      (srcData['sortId'], destData['id']))

        return utils.makeResult(True, "success")

    def createShareLink(self, uid: int, path: str):
        rpath = self.getUserDrivePath(uid)
        if not rpath['ok']:
            return rpath

        test = self.db.query(
            "select id from shareLinksList where owner = ? and path = ?", (uid, path), one=True)
        if test is not None:
            return utils.makeResult(True, test['id'])

        rpath = f"{rpath['data']}/{path}"
        if os.access(rpath, os.F_OK):
            linkId = utils.getRandom10CharString(uid)
            self.db.query(
                "insert into shareLinksList (id, path, owner) values (?, ?, ?)", (linkId, path, uid))
            return utils.makeResult(True, linkId)
        else:
            return utils.makeResult(False, "path not exist")

    def queryShareLink(self, linkId: str):
        data = self.db.query(
            "select * from shareLinksList where id = ?", (linkId, ), one=True)

        if data is None:
            return utils.makeResult(False, "share link not exist")

        rpath = self.getUserDrivePath(data['owner'])
        if not rpath['ok']:
            return rpath

        else:
            path = f"{rpath['data']}/{data['path']}"
            pathInfo = utils.getPathInfo(path)
            data["info"] = pathInfo
            data['owner'] = utils.catchError(
                self.logger(), self.queryUser(data['owner']))
            return utils.makeResult(True, data)

    def queryUserShareLinks(self, uid: int):
        data = self.db.query(
            "select * from shareLinksList where owner = ?", (uid, ))
        return utils.makeResult(True, data)

    def deleteShareLink(self, uid: int, linkId: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data
        if data['data']['owner']['id'] != uid:
            return utils.makeResult(False, "user isn't the owner of the share link")
        self.db.query(
            "delete from shareLinksList where id = ?", (linkId, ))
        return utils.makeResult(True, "success")

    def queryShareLinkFileRealpath(self, linkId: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        data = self.queryFileRealpath(data['owner']['id'], data['path'])
        return data

    def queryShareLinkDirInfo(self, linkId: str, path: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        l = self.getUserDriveDirInfo(
            data['owner']['id'], f"{data['path']}/{path}")
        if not l['ok']:
            return l

        for i in l['data']['list']:
            if not data['path'].startswith('/'):
                data['path'] = f"/{data['path']}"
            if not i['path'].startswith('/'):
                i['path'] = f"/{i['path']}"

            data['path'] = os.path.normpath(data['path'])
            i['path'] = os.path.normpath(i['path'])

            i['path'] = i['path'][len(
                os.path.commonpath([i['path'], data['path']])):]

        return l

    def queryShareLinkDirFileRealpath(self, linkId: str, path: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        data = self.queryFileRealpath(
            data['owner']['id'], f"{data['path']}/{path}")
        return data

    def queryAvaliablePlugins(self):
        plugins = []
        for i in self.plugins:
            plugins.append({'name': i, 'info': self.plugins[i]['info']})
        return utils.makeResult(True, plugins)

    def queryTask(self, taskId: int):
        data = self.db.query(
            "select * from taskList where id = ?", (taskId, ), one=True)
        if data is None:
            return utils.makeResult(False, "task not exist")
        else:
            return utils.makeResult(True, data)

    def createTask(self, uid: int, name: str, plugin: str, handler: str, args: list):
        if plugin not in self.plugins:
            return utils.makeResult(False, "plugin not exist")

        user = self.queryUser(uid)
        if not user['ok']:
            return user

        if user['data']['level'] < self.plugins[plugin]['info']['avaliablepermissionLevel']:
            return utils.makeResult(False, "user's permission level is lower than requirement")

        taskId = self.db.query(
            'insert into taskList (owner, name, plugin, handler, args, creationTime) values (?, ?, ?, ?, ?, ?)',
            (uid, name, plugin, handler, json.dumps(args), getCurrentTime()))
        try:
            handlerCallable = self.plugins[plugin]['handlers'].__getattribute__(
                handler)
            threading.Thread(
                target=handlerCallable, args=(self, self.taskInfo(self.db, taskId), args)).start()

            return utils.makeResult(True, taskId)
        except AttributeError:
            return utils.makeResult(False, "specified handler not exist")
        except TypeError:
            return utils.makeResult(False, "invalid task arguments")

    def deleteTask(self, uid: int, taskId: int):
        task = self.queryTask(taskId)
        if not task['ok']:
            return task

        if task['data']['owner'] != uid:
            return utils.makeResult("user isn't the owner of this task")

        self.db.query("delete from taskList where id = ?", (taskId, ))

        return utils.makeResult(True, "success")

    def getUserList(self):
        return utils.makeResult(True, self.db.query("select id, name, slogan, level from users"))

    def updateUserPermissionLevel(self, uid, newLevel):
        if self.checkIfUserExistById(uid) is not None:
            self.db.query("update users set level = ? where id = ?",
                          (newLevel, uid), one=True)
            return utils.makeResult(True, "success")
        else:
            return utils.makeResult(False, "user not exist")


    def queryMusicStatistics(self, uid):
        if self.checkIfUserExistById(uid) is not None:
            raw = self.db.query('select * from playCount where owner = ? and plays != 0 order by plays desc limit 100', (uid, ))
            for i in raw:
                i['info'] = utils.getSongInfo(utils.catchError(
                    self.logger(), self.queryFileRealpath(uid, i['path']))['path'])
            return utils.makeResult(True, raw)
        else:
            return utils.makeResult(False, "user not exist")