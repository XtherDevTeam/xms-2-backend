import sqlite3
import api.utils as utils
import logging
import os
import mimetypes
import time
import json
from typing import Any


class databaseObject:
    def __init__(self, dbPath: str) -> None:
        self.db = sqlite3.connect(dbPath, check_same_thread=False)

    def query(self, query, args=(), one=False):
        cur = self.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
                   for idx, value in enumerate(row)) for row in cur.fetchall()]
        self.db.commit()

        return (rv[0] if rv else None) if one else rv

    def runScript(self, query: str):
        self.db.executescript(query)
        self.db.commit()
        return None

    def close(self):
        self.db.close()


class dataManager:
    def __init__(self, dbObject: databaseObject, appRoot: str) -> None:
        self.db = dbObject
        self._logger = logging.getLogger("dataManager")

    def logger(self) -> logging.Logger:
        return self._logger

    def getXmsBlobPath(self):
        try:
            d = self.db.query("select xmsBlobPath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:

                return utils.makeResult(True, d['xmsBlobPath'].replace(  # type: ignore
                    '$', utils.catchError(self.logger(), self.getXmsRootPath())))
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsRootPath(self):
        try:
            d = self.db.query("select xmsRootPath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['xmsRootPath'])  # type: ignore
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsDrivePath(self):
        try:
            d = self.db.query("select xmsDrivePath from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['xmsDrivePath'].replace(  # type: ignore
                    '$', utils.catchError(self.logger(), self.getXmsRootPath())))
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsHost(self):
        try:
            d = self.db.query("select host from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['host'])  # type: ignore
        except sqlite3.Error as e:
            return utils.makeResult(False, str(e))

    def getXmsPort(self):
        try:
            d = self.db.query("select port from config", one=True)
            if d is None:
                return utils.makeResult(False, "uninitialized")
            else:
                return utils.makeResult(True, d['port'])  # type: ignore
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

    # use username instead of uid because system don't know uid when creating user
    def createUserDrive(self, username: str):
        drivePath = utils.catchError(self.logger(), self.getXmsDrivePath())
        uid = self.checkIfUserExistByUserName(username)
        if uid is None:
            return utils.makeResult(False, "user not exist while creating user drive")
        else:
            try:
                os.makedirs(f"{drivePath}/{uid}")
                return utils.makeResult(True, "success")
            except OSError as e:
                return utils.makeResult(False, f"unable to create user drive: {str(e)}")

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
            # 0 is superadmin, 1 is admin, 2 is user
            with open(utils.catchError(self.logger(), self.getXmsBlobPath()) + "/avatar.jpg", "rb+") as a:
                with open(utils.catchError(self.logger(), self.getXmsBlobPath()) + "/headImage.jpg", "rb+") as b:
                    self.db.query("insert into users (name, slogan, level, passwordMd5, avatar, headImage) values (?,?,?,?,?,?)",
                                  (userName, userSlogan, level, utils.makePasswordMd5(userPassword), a.read(), b.read()))
            return self.createUserDrive(userName)
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

    def renameInUserDrive(self, uid: int, path: str, newName: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            os.rename(base, os.path.join(os.path.dirname(base), newName))
            return utils.makeResult(True, "success")
        else:
            return base

    def moveInUserDrive(self, uid: int, path: str, newPath: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            newBase = f"{base['data']}/{path}"
            newPath = f"{base['data']}/{newPath}/{os.path.basename(newBase)}"
            os.rename(newBase, newPath)
            return utils.makeResult(True, "success")
        else:
            return base

    def deleteInUserDrive(self, uid: int, path: str):
        base = self.getUserDrivePath(uid)
        if base['ok']:
            base = f"{base['data']}/{path}"
            try:
                if os.path.isfile(base):
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

    def checkIfUserExistById(self, uid: int):
        try:
            d = self.db.query(
                "select id from users where id = ?", (uid, ), one=True)
            if d is not None:
                return d['id']  # type: ignore
        except sqlite3.Error as e:
            return None

    def checkIfUserExistByUserName(self, username: str):
        try:
            d = self.db.query(
                "select id from users where name = ?", (username, ), one=True)
            if d is not None:
                return d['id']  # type: ignore
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
                return utils.makeResult(True, d['passwordMd5'])  # type: ignore
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
        uid = self.checkIfUserExistById(uid)  # type: ignore
        if uid is not None:
            try:
                self.db.query(
                    "update users set avatar = ?, avatarMime = ? where id = ?", (avatar, mime, uid))
                return utils.makeResult(True, "success")
            except sqlite3.Error as e:
                return utils.makeResult(False, str(e))

    def updateUserHeadImage(self, uid: int, headImage: bytes, mime: str):
        uid = self.checkIfUserExistById(uid)  # type: ignore
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
            return d['id']  # type: ignore
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

    def createUserPlaylist(self, uid: int, name: str, description: str):
        if self.checkUserPlaylistIfExistByPlaylistName(uid, name) is not None:
            return utils.makeResult(False, "playlist with the same playlist name already exists")
        if self.checkIfUserExistById(uid) is not None:
            self.db.query("insert into playlists (name, owner, description, creationDate) values (?, ?, ?, ?)",
                          (name, uid, description, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))

            playlistId = self.checkUserPlaylistIfExistByPlaylistName(uid, name)
            data = self.queryUserOwnPlaylists(uid)
            data.append(playlistId)  # type: ignore
            return utils.makeResult(True, playlistId)
        else:
            return utils.makeResult(False, "user not exist")

    def deleteUserPlaylistById(self, id: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(id)
        if data is None:
            return utils.makeResult(False, "playlist not exist")
        else:
            p = self.queryUserOwnPlaylists(data['owner'])  # type: ignore
            p.remove(id)  # type: ignore
            self.updateUserOwnPlaylists(data['owner'], p)  # type: ignore
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

    def insertSongToPlaylist(self, playlistId: int, songPath: str):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        if self.checkIfSongExistInPlaylistByPath(playlistId, songPath) is not None:
            return utils.makeResult(False, "the song has already been in the playlist")

        self.db.query(
            "insert into songlist (path, playlistId) values (?, ?)", (songPath, playlistId))
        return utils.makeResult(
            True, self.checkIfSongExistInPlaylistByPath(playlistId, songPath)['id'])  # type: ignore

    def deleteSongFromPlaylist(self, playlistId: int, songId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        if self.checkIfSongExistInPlaylistById(playlistId, songId) is None:
            return utils.makeResult(False, "the song isn't in the playlist")

        self.db.query("delete from songlist where id = ?", (songId))
        return utils.makeResult(True, "success")

    def queryUserPlaylistSongs(self, playlistId: int, limit: int, offset: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        songs = self.db.query(
            "select * from songlist where playlistId = ? order by id desc limit ? offset ?", (playlistId, limit, offset))

        for i in songs:  # type: ignore
            i['info'] = utils.getSongInfo(utils.catchError(  # type: ignore
                self.logger(), self.queryFileRealpath(data['owner'], i['path']))['path'])  # type: ignore

        return utils.makeResult(True, songs)

    def querySongFromPlaylist(self, songId: int):
        data = self.db.query(
            "select path, playlistId from songlist where id = ?", (songId, ), one=True)
        if data is None:
            return utils.makeResult(False, "song not exist")

        playlist = self.queryUserPlaylistInfo(
            data['playlistId'])['data']  # type: ignore

        songInfo = utils.getSongInfo(utils.catchError(  # type: ignore
            self.logger(), self.queryFileRealpath(playlist['owner'], data['path']))['path'])  # type: ignore
        songInfo['owner'] = playlist['owner']

        return utils.makeResult(True, songInfo)

    def querySongArtworkFromPlaylist(self, songId: int):
        data = self.db.query(
            "select path, playlistId from songlist where id = ?", (songId, ), one=True)
        if data is None:
            return utils.makeResult(False, "song not exist")

        playlist = self.queryUserPlaylistInfo(
            data['playlistId'])['data']  # type: ignore

        try:
            return utils.makeResult(True, utils.getSongArtwork(utils.catchError(  # type: ignore
                self.logger(), self.queryFileRealpath(playlist['owner'], data['path']))['path']))  # type: ignore
        except Exception as e:
            print(e)
            blobPath = utils.catchError(self.logger(), self.getXmsBlobPath())

            with open(f'{blobPath}/defaultArtwork.jpg', 'rb') as default:
                return utils.makeResult(True, {"artwork": default.read(), "mime": "image/jpeg"})

    def queryUserPlaylistInfo(self, playlistId: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(playlistId)
        if data is None:
            return utils.makeResult(False, "playlist not exist")

        d = self.db.query(
            "select * from playlists where id = ?", (playlistId, ), one=True)
        return utils.makeResult(True, d)

    def createShareLink(self, uid: int, path: str):
        rpath = self.getUserDrivePath(uid)
        if not rpath['ok']:
            return rpath

        test = self.db.query("select id from shareLinksList where owner = ? and path = ?", (uid, path), one=True)
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
        else:
            path = f"{self.getUserDrivePath(data['owner'])}/{data['path']}"
            pathInfo = utils.getPathInfo(path)
            data["info"] = pathInfo
            return utils.makeResult(True, data)

    def queryUserShareLinks(self, uid: int):
        data = self.db.query(
            "select * from shareLinksList where owner = ?", (uid, ))
        return utils.makeResult(True, data)

    def deleteShareLink(self, uid: int, linkId: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data
        if data['data']['owner'] != uid:
            return utils.makeResult(False, "user isn't the owner of the share link")
        self.db.query(
            "delete from shareLinksList where linkId = ?", (linkId, ))
        return utils.makeResult(True, "success")

    def queryShareLinkFileRealpath(self, linkId: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        data = self.queryFileRealpath(data['owner'], data['path'])
        return data

    def queryShareLinkDirInfo(self, linkId: str, path: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        data = self.getUserDriveDirInfo(
            data['owner'], f"{data['path']}/{path}")
        return data

    def queryShareLinkDirFileRealpath(self, linkId: str, path: str):
        data = self.queryShareLink(linkId)
        if not data['ok']:
            return data

        data = data['data']
        data = self.queryFileRealpath(
            data['owner'], f"{data['path']}/{path}")
        return data
