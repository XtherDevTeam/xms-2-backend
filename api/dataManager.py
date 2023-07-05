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
                    files.append({
                        "filename": i,
                        "path": i,
                        "type": "file" if os.path.isfile(fullPath) else "dir",
                    })
                    filesCnt += int(os.path.isfile(fullPath))
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
                os.makedirs(base, 777)
                return utils.makeResult(True, "success")
            except OSError as e:
                return utils.makeResult(False, str(e))
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

    def updateUserInfo(self, uid: int, userName: str, userSlogan: str):
        try:
            d = self.db.query(
                "update users set name = ?, slogan = ? where id = ?", (userName, userSlogan, uid))
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
            if d['data']['passwordMd5'] != utils.makePasswordMd5(oldPwd):
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
                    "update users set headImage = ?, headImageMime = ? where id = ?", (headImage, mime, ))
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
            "select ownPlaylists from users where id = ?", (uid, ), one=True)['ownPlaylists']  # type: ignore
        return json.loads(data)

    def updateUserOwnPlaylists(self, uid: int, data: list):
        self.db.query(
            "update users set ownPlaylists = ? where id = ?", (json.dumps(data), uid))
        return None

    def createUserPlaylist(self, uid: int, name: str, description: str):
        if self.checkUserPlaylistIfExistByPlaylistName(uid, name) is not None:
            return utils.makeResult(False, "playlist with the same playlist name already exists")
        if self.checkIfUserExistById(uid) is not None:
            self.db.query("insert into playlists (name, owner, description, creationDate) values (?, ?, ?, ?)",
                          (name, uid, description, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))

            playlistId = self.checkUserPlaylistIfExistByPlaylistName(uid, name)
            data = self.queryUserOwnPlaylists(uid)
            data.append(playlistId)
            self.updateUserOwnPlaylists(uid, data)
            return utils.makeResult(True, playlistId)
        else:
            return utils.makeResult(False, "user not exist")

    def deleteUserPlaylistById(self, id: int):
        data = self.checkUserPlaylistIfExistByPlaylistId(id)
        if data is None:
            return utils.makeResult(False, "playlist not exist")
        else:
            p = self.queryUserOwnPlaylists(data['owner'])  # type: ignore
            p.remove(id)
            self.updateUserOwnPlaylists(data['owner'], p)  # type: ignore
            self.db.query("delete from playlists where id = ?", (id, ))
            return utils.makeResult(True, "success")
