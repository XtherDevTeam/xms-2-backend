import flask
import flask_cors
import requests
import logging
import time
import os
import re
import api.flaskSession
import json
from io import BytesIO

import api.dataManager
import api.utils
import api.xms

import plugins.enabled

database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(
    database, "./root", "./plugins", plugins.enabled)

webLogger = logging.Logger("webApplication")
webApplication = flask.Flask(__name__)

flask_cors.CORS(webApplication)


def checkIfLoggedIn():
    return flask.session.get("loginState")

def checkIfLoggedInSession(s):
    return json.loads(api.flaskSession.decode(s))['loginState']


def parseRequestRange(s, flen):
    s = s[s.find('=')+1:]
    c = s.split('-')
    if len(c) != 2:
        return None
    else:
        if c[0] == '' and c[1] == '':
            return [0, flen - 1]
        elif c[1] == '':
            return [int(c[0]), flen - 1]
        elif c[0] == '':
            return [flen - int(c[1]) - 1, flen - 1]
        else:
            return [int(i) for i in c]


def makeFileResponse(path, mime):
    isPreview = not mime.startswith('application')
    if flask.request.headers.get('Range') != None:
        fileLength = os.path.getsize(path)
        
        reqRange = parseRequestRange(flask.request.headers.get('Range'), fileLength)
        
        response_file = bytes()

        with open(path, 'rb') as file:
            file.seek(reqRange[0])
            response_file = file.read(reqRange[1] - reqRange[0] + 1)

        response = flask.make_response(response_file)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Range'] = 'bytes ' + \
            str(reqRange[0]) + '-' + \
            str(reqRange[1]) + '/' + str(fileLength)
        response.headers['Content-Type'] = mime
        if response.headers['Content-Type'].startswith('application'):
            response.headers['Content-Disposition'] = "attachment; filename=" + \
                os.path.basename(path)

        response.status_code = 206
        return response
    return flask.send_file(path, as_attachment=not isPreview, download_name=os.path.basename(path), mimetype=mime)


def routeAfterRequest(d):
    dataManager.db.db.commit()
    return d


webApplication.after_request(routeAfterRequest)


@webApplication.route("/xms/v1/info", methods=["GET"])
def routeInfo():
    cfg = dataManager.getXmsConfig()['data']
    return {
        "coreCodeName": api.xms.xmsCoreCodeName,
        "coreBuildNumber": api.xms.xmsCoreBuildNumber,
        "xmsProjectAuthor": api.xms.xmsProjectAuthor,
        "serverTime": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time())),
        "instanceName": api.xms.xmsInstanceName,
        "instanceDescription": api.xms.xmsInstanceDescription,
        "allowRegister": cfg['allowRegister'],
        "enableInviteCode": cfg['enableInviteCode']
    }


@webApplication.route("/xms/v1/config", methods=["GET"])
def routeConfig():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    if dataManager.queryUser(uid)['data']['level'] < 1:
        return api.utils.makeResult(False, "user is not admin")
    return dataManager.getXmsConfig()


@webApplication.route("/xms/v1/config/update", methods=["POST"])
def routeConfigUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    if dataManager.queryUser(uid)['data']['level'] < 1:
        return api.utils.makeResult(False, "user is not admin")
    data = flask.request.get_json(silent=True)
    if data is None:
        return api.utils.makeResult(False, "invalid request")

    return dataManager.updateXmsConfig(data)


@webApplication.route("/xms/v1/info/plugins", methods=["GET"])
def routeInfoPlugins():
    return dataManager.queryAvaliablePlugins()


@webApplication.route("/xms/v1/signin", methods=["POST"])
def routeSignIn():
    data = flask.request.get_json()
    username = data.get("username")
    password = data.get("password")
    if username is None or password is None:
        return api.utils.makeResult(False, "incomplete request")
    else:
        if isinstance(username, str) and isinstance(password, str):
            uid = dataManager.vertifyUserLogin(username, password)
            if uid is not None:
                flask.session['loginState'] = uid
                return api.utils.makeResult(True, "success")
            else:
                return api.utils.makeResult(False, "invalid username or password")
        else:
            return api.utils.makeResult(False, "invalid request")


@webApplication.route("/xms/v1/signout", methods=["POST"])
def routeSignOut():
    if "loginState" in flask.session:
        del flask.session["loginState"]
        return api.utils.makeResult(True, "success")
    else:
        return api.utils.makeResult(False, "user haven't logged in yet")


@webApplication.route("/xms/v1/signup", methods=["POST"])
def routeSignUp():
    data = flask.request.get_json()
    cfg = dataManager.getXmsConfig()['data']
    username = data.get("username")
    password = data.get("password")
    slogan = data.get("slogan")
    inviteCode = data.get("inviteCode")
    if cfg['allowRegister'] == 0:
        return api.utils.makeResult(False, "registration is disabled")

    if username is None or password is None or slogan is None:
        return api.utils.makeResult(False, "incomplete request")
    else:
        if cfg['enableInviteCode'] == 1 and inviteCode != cfg['inviteCode']:
            return api.utils.makeResult(False, "invalid inviteCode")
        if isinstance(username, str) and isinstance(password, str) and isinstance(slogan, str):
            return dataManager.createUser(username, password, slogan, 0)
        else:
            return api.utils.makeResult(False, "invalid request")


@webApplication.route("/xms/v1/user/status", methods=["GET"])
def routeUserStatus():
    uid = checkIfLoggedIn()
    if uid == None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    else:
        return api.utils.makeResult(True, {"status": "logged in", "uid": uid})


@webApplication.route("/xms/v1/user/<uid>/info", methods=["GET"])
def routeUserInfo(uid):
    uid = int(uid)
    return dataManager.queryUser(uid)


@webApplication.route("/xms/v1/user/<uid>/sharelinks", methods=["GET"])
def routeUserShareLinks(uid):
    uid = int(uid)
    return dataManager.queryUserShareLinks(uid)


@webApplication.route("/xms/v1/user/tasks", methods=["GET"])
def routeUserTasks():
    uid = checkIfLoggedIn()
    if uid == None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    return dataManager.queryUserOwnTaskList(uid)


@webApplication.route("/xms/v1/user/<uid>/avatar", methods=["GET"])
def routeUserAvatar(uid):
    uid = int(uid)
    avatar = dataManager.getUserAvatar(uid)
    if avatar['ok']:
        file = BytesIO(avatar['data']["avatar"])
        return flask.send_file(file, avatar['data']["avatarMime"])
    else:
        return avatar


@webApplication.route("/xms/v1/user/<uid>/headimg", methods=["GET"])
def routeUserHeadImg(uid):
    uid = int(uid)
    headImg = dataManager.getUserHeadImage(uid)
    if headImg['ok']:
        file = BytesIO(headImg['data']["headImage"])
        return flask.send_file(file, headImg['data']["headImageMime"])
    else:
        return headImg


@webApplication.route("/xms/v1/user/playlists", methods=["GET"])
def routeUserPlaylists():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    return api.utils.makeResult(True, dataManager.queryUserOwnPlaylists(uid))


@webApplication.route("/xms/v1/user/password/update", methods=["POST"])
def routeUserPasswordUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    oldPassword = data.get('oldPassword')
    newPassword = data.get('newPassword')
    if oldPassword is None or not isinstance(oldPassword, str) or len(oldPassword) == 0:
        return api.utils.makeResult(False, "invalid request")
    if newPassword is None or not isinstance(newPassword, str) or len(newPassword) == 0:
        return api.utils.makeResult(False, "invalid request")

    return dataManager.updateUserPassword(uid, oldPassword, newPassword)


@webApplication.route("/xms/v1/user/username/update", methods=["POST"])
def routeUserUsernameUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    newUsername = data.get('newUsername')
    if newUsername is None or not isinstance(newUsername, str) or len(newUsername) == 0:
        return api.utils.makeResult(False, "invalid request")

    return dataManager.updateUserUsername(uid, newUsername)


@webApplication.route("/xms/v1/user/slogan/update", methods=["POST"])
def routeUserSloganUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    newSlogan = data.get('newSlogan')
    if newSlogan is None or not isinstance(newSlogan, str) or len(newSlogan) == 0:
        return api.utils.makeResult(False, "invalid request")

    return dataManager.updateUserSlogan(uid, newSlogan)


@webApplication.route("/xms/v1/user/avatar/update", methods=["POST"])
def routeUserAvatarUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    avatar = flask.request.files.get('image')
    if avatar is None:
        return api.utils.makeResult(False, "invalid request")

    if not avatar.content_type.startswith("image/"):
        return api.utils.makeResult(False, "not an image file")

    image = avatar.stream.read()

    return dataManager.updateUserAvatar(uid, image, avatar.content_type)


@webApplication.route("/xms/v1/user/headimg/update", methods=["POST"])
def routeUserHeadImgUpdate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    headimg = flask.request.files.get('image')
    if headimg is None:
        return api.utils.makeResult(False, "invalid request")

    if not headimg.content_type.startswith("image/"):
        return api.utils.makeResult(False, "not an image file")

    image = headimg.stream.read()

    return dataManager.updateUserHeadImage(uid, image, headimg.content_type)


@webApplication.route("/xms/v1/drive/dir", methods=["POST"])
def routeDriveDir():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.getUserDriveDirInfo(uid, path)


@webApplication.route("/xms/v1/drive/createdir", methods=["POST"])
def routeDriveCreateDir():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    name = data.get('name')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    if name is None or not isinstance(name, str):
        return api.utils.makeResult(False, "invalid request")

    result = re.match(r'[^~\x22/\(\)\&\[\]\{\}]+', name)
    if result is None or result.group() != name:
        return api.utils.makeResult(False, "invalid folder name")

    return dataManager.createDirInUserDrive(uid, os.path.join(path, name))


@webApplication.route("/xms/v1/drive/delete", methods=["POST"])
def routeDriveDelete():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.deleteInUserDrive(uid, path)


@webApplication.route("/xms/v1/drive/copy", methods=["POST"])
def routeDriveCopy():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    path = data.get('path')
    newPath = data.get('newPath')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    if newPath is None or not isinstance(newPath, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.copyInUserDrive(uid, path, newPath)


@webApplication.route("/xms/v1/drive/rename", methods=["POST"])
def routeDriveRename():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    path = data.get('path')
    newName = data.get('newName')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    if newName is None or not isinstance(newName, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.renameInUserDrive(uid, path, newName)


@webApplication.route("/xms/v1/drive/move", methods=["POST"])
def routeDriveMove():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    path = data.get('path')
    newPath = data.get('newPath')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    if newPath is None or not isinstance(newPath, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.moveInUserDrive(uid, path, newPath)


@webApplication.route("/xms/v1/drive/file", methods=["GET"])
def routeDriveFile():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    path = flask.request.args.get('path')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    try:
        result = dataManager.queryFileRealpath(uid, path)
        if result['ok']:
            result = result['data']
            return makeFileResponse(result['path'], result['mime'])
        else:
            return result
    except OSError as e:
        return api.utils.makeResult(False, str(e))


@webApplication.route("/xms/v1/drive/upload", methods=["POST"])
def routeDriveUpload():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    path = flask.request.args.get("path", type=str)
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    for i in flask.request.files:
        j = flask.request.files[i]
        print(f"uploading files: {i} {j.filename}")
        result = dataManager.queryFileUploadRealpath(
            uid, f"{path}/{j.filename}")
        if result['ok']:
            j.save(result['data'])
        else:
            return result

    return api.utils.makeResult(True, "success")


@webApplication.route("/xms/v1/mobile/drive/upload", methods=["POST"])
def routeMobileDriveUpload():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    filename = flask.request.args.get("filename", type=str)
    if filename is None or not isinstance(filename, str):
        return api.utils.makeResult(False, "invalid request")
    
    path = flask.request.args.get("path", type=str)
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    for i in flask.request.files:
        j = flask.request.files[i]
        print(f"uploading files12321312312: {i} {filename}")
        result = dataManager.queryFileUploadRealpath(
            uid, f"{path}/{filename}")
        if result['ok']:
            j.save(result['data'])
        else:
            return result

    return api.utils.makeResult(True, "success")



@webApplication.route("/xms/v1/music/playlist/create", methods=["POST"])
def routeMusicPlaylistCreate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    name = data.get('name')
    description = data.get('description')
    if "name" not in data or "description" not in data:
        return api.utils.makeResult(False, "incomplete request")

    if not isinstance(name, str) or not isinstance(description, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.createUserPlaylist(uid, name, description)


@webApplication.route("/xms/v1/music/playlist/delete", methods=["POST"])
def routeMusicPlaylistDelete():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    id = data.get('id')
    if not isinstance(id, int):
        return api.utils.makeResult(False, "invalid request")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")
    return dataManager.deleteUserPlaylistById(id)


@webApplication.route("/xms/v1/music/playlist/<id>/edit", methods=["POST"])
def routeMusicPlaylistEdit(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    name = data.get('name')
    description = data.get('description')
    if "name" not in data or "description" not in data:
        return api.utils.makeResult(False, "incomplete request")

    if not isinstance(name, str) or not isinstance(description, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.updatePlaylistInfo(id, uid, name, description)


@webApplication.route("/xms/v1/music/playlist/<id>/info", methods=["GET"])
def routeMusicPlaylistInfo(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    return dataManager.queryUserPlaylistInfo(id)


@webApplication.route("/xms/v1/music/song/<id>/info", methods=["GET"])
def routeMusicSongInfo(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    songInfo = dataManager.querySongFromPlaylist(id)
    if not songInfo['ok']:
        return songInfo

    songInfo = songInfo['data']
    if songInfo['owner'] != uid:
        return api.utils.makeResult(False, "permission denied")

    return api.utils.makeResult(True, songInfo)


@webApplication.route("/xms/v1/music/song/<id>/increasePlayCount", methods=["POST"])
def routeMusicSongIncreasePlayCount(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    return dataManager.increaseSongPlayCount(uid, id)

@webApplication.route("/xms/v1/music/playlist/<id>/increasePlayCount", methods=["POST"])
def routePlaylistIncreasePlayCount(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    return dataManager.increasePlaylistPlayCount(id)


@webApplication.route("/xms/v1/music/playlist/<id>/artwork")
def routePlaylistArtwork(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = dataManager.queryPlaylistArtwork(id)
    if data['ok']:
        return flask.send_file(BytesIO(data['data']['artwork']), data['data']['mime'])
    else:
        return data


@webApplication.route("/xms/v1/music/song/<id>/artwork", methods=["GET"])
def routeMusicSongArtwork(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    songInfo = dataManager.querySongFromPlaylist(id)
    if not songInfo['ok']:
        return songInfo

    songInfo = songInfo['data']
    if songInfo['owner'] != uid:
        return api.utils.makeResult(False, "permission denied")

    data = dataManager.querySongArtworkFromPlaylist(id)
    if data['ok']:
        return flask.send_file(BytesIO(data['data']['artwork']), data['data']['mime'])
    else:
        return data
    
@webApplication.route("/xms/v1/mobile/music/song/<id>/artwork", methods=["GET"])
def routeMobileMusicSongArtwork(id):
    session = flask.request.args.get('session')
    if session is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    
    uid = checkIfLoggedInSession(session)

    songInfo = dataManager.querySongFromPlaylist(id)
    if not songInfo['ok']:
        return songInfo

    songInfo = songInfo['data']
    if songInfo['owner'] != uid:
        return api.utils.makeResult(False, "permission denied")

    data = dataManager.querySongArtworkFromPlaylist(id)
    if data['ok']:
        return flask.send_file(BytesIO(data['data']['artwork']), data['data']['mime'])
    else:
        return data


@webApplication.route("/xms/v1/music/playlist/<id>/songs/<sid>/file", methods=["GET"])
def routeMusicPlaylistSongsFile(id, sid):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(int(id))
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    data = dataManager.db.query(
        "select id, path from songlist where id = ?", (sid, ), one=True)
    if data is None:
        return api.utils.makeResult(False, f'SongId({sid}) not exist')

    path = api.utils.catchError(
        webLogger, dataManager.queryFileRealpath(uid, data['path']))
    return makeFileResponse(path['path'], path['mime'])


@webApplication.route("/xms/v1/mobile/music/playlist/<id>/songs/<sid>/file", methods=["GET"])
def routeMobileMusicPlaylistSongsFile(id, sid):
    session = flask.request.args.get('session')
    if session is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    
    uid = checkIfLoggedInSession(session)
    
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(int(id))
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    data = dataManager.db.query(
        "select id, path from songlist where id = ?", (sid, ), one=True)
    if data is None:
        return api.utils.makeResult(False, f'SongId({sid}) not exist')

    path = api.utils.catchError(
        webLogger, dataManager.queryFileRealpath(uid, data['path']))
    return makeFileResponse(path['path'], path['mime'])


@webApplication.route("/xms/v1/music/playlist/<id>/songs", methods=["GET"])
def routeMusicPlaylistSongs(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(int(id))
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    return dataManager.queryUserPlaylistSongs(id)


@webApplication.route("/xms/v1/music/playlist/<id>/songs/swap/<src>/<dest>", methods=["POST"])
def routeMusicPlaylistSongsSwap(id, src, dest):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    try:
        d = dataManager.checkUserPlaylistIfExistByPlaylistId(int(id))
        if d is None:
            return api.utils.makeResult(False, "playlist not exist")
        if d['owner'] != uid:
            return api.utils.makeResult(False, "user isn't the owner of playlist")

        return dataManager.swapTwoSongsInPlaylistSongList(int(src), int(dest))
    except ValueError as e:
        return api.utils.makeResult(False, str(e))


@webApplication.route("/xms/v1/music/playlist/<id>/songs/insert", methods=["POST"])
def routeMusicPlaylistSongsInsert(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('songPath')
    if not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    if dataManager.queryFileRealpath(uid, path)['ok']:
        return dataManager.insertSongToPlaylist(id, path)
    else:
        return api.utils.makeResult(False, "file not exist")


@webApplication.route("/xms/v1/music/playlist/<id>/songs/delete", methods=["POST"])
def routeMusicPlaylistSongsDelete(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    sid = data.get('songId')
    if not isinstance(sid, int):
        return api.utils.makeResult(False, "invalid request")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    return dataManager.deleteSongFromPlaylist(id, sid)


@webApplication.route("/xms/v1/sharelink/create", methods=["POST"])
def routeShareLinkCreate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    if not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.createShareLink(uid, path)


@webApplication.route("/xms/v1/sharelink/<id>/info", methods=["GET"])
def routeShareLinkInfo(id: str):
    return dataManager.queryShareLink(id)


@webApplication.route("/xms/v1/sharelink/<id>/delete", methods=["POST"])
def routeShareLinkDelete(id: str):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    return dataManager.deleteShareLink(uid, id)


@webApplication.route("/xms/v1/sharelink/<id>/file", methods=["GET"])
def routeShareLinkFile(id: str):
    try:
        result = dataManager.queryShareLinkFileRealpath(id)
        if result['ok']:
            return makeFileResponse(result['data']['path'], result['data']['mime'])
        else:
            return result
    except OSError as e:
        return api.utils.makeResult(False, str(e))


@webApplication.route("/xms/v1/sharelink/<id>/dir", methods=["POST"])
def routeShareLinkDir(id: str):
    data = flask.request.get_json()
    path = data.get('path')
    if not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    return dataManager.queryShareLinkDirInfo(id, path)


@webApplication.route("/xms/v1/sharelink/<id>/dir/file", methods=["GET"])
def routeShareLinkDirFile(id: str):
    path = flask.request.args.get('path')
    if not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")
    try:
        result = dataManager.queryShareLinkDirFileRealpath(id, path)
        if result['ok']:
            return makeFileResponse(result['data']['path'], result['data']['mime'])
        else:
            return result
    except OSError as e:
        return api.utils.makeResult(False, str(e))


@webApplication.route("/xms/v1/task/create", methods=["POST"])
def routeTaskCreate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    data = flask.request.get_json()
    print(data)

    name = data.get('name')
    if name is None or not isinstance(name, str):
        return api.utils.makeResult(False, "invalid request")

    plugin = data.get('plugin')
    if name is None or not isinstance(plugin, str):
        return api.utils.makeResult(False, "invalid request")

    handler = data.get('handler')
    if name is None or not isinstance(handler, str):
        return api.utils.makeResult(False, "invalid request")

    args = data.get('args')
    if name is None or not isinstance(args, list):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.createTask(uid, name, plugin, handler, args)


@webApplication.route("/xms/v1/task/<id>/info", methods=["GET"])
def routeTaskInfo(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    try:
        id = int(id)
    except:
        return api.utils.makeResult(False, "invalid request")

    data = dataManager.queryTask(id)
    if data['ok'] and data['data']['owner'] != uid:
        return api.utils.makeResult(False, "user isn't the owner of this task")
    else:
        return data


@webApplication.route("/xms/v1/task/<id>/delete", methods=["POST"])
def routeTaskDelete(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    try:
        id = int(id)
    except:
        return api.utils.makeResult(False, "invalid request")

    return dataManager.deleteTask(uid, id)


@webApplication.route("/xms/v1/user/manage/list", methods=["GET"])
def userManageList():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    if dataManager.queryUser(uid)['data']['level'] == 2:
        return dataManager.getUserList()
    else:
        return api.utils.makeResult(False, "permission denied")


@webApplication.route("/xms/v1/user/manage/delete", methods=["POST"])
def userManageDelete():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    if dataManager.queryUser(uid)['data']['level'] == 2:
        data = flask.request.get_json(silent=True)
        if data.get('id') is None or not isinstance(data['id'], int):
            return api.utils.makeResult(False, "invalid request")

        return dataManager.deleteUser(data['id'])
    else:
        return api.utils.makeResult(False, "permission denied")


@webApplication.route("/xms/v1/user/manage/updateLevel", methods=["POST"])
def userManageUpdateLevel():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    if dataManager.queryUser(uid)['data']['level'] == 2:
        data = flask.request.get_json(silent=True)
        if data.get('id') is None or not isinstance(data['id'], int):
            return api.utils.makeResult(False, "invalid request")
        if data.get('level') is None or not isinstance(data['level'], int):
            return api.utils.makeResult(False, "invalid request")

        return dataManager.updateUserPermissionLevel(data['id'], data['level'])
    else:
        return api.utils.makeResult(False, "permission denied")


@webApplication.route("/xms/v1/user/manage/create", methods=["POST"])
def userManageCreate():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")

    if dataManager.queryUser(uid)['data']['level'] == 2:
        data = flask.request.get_json(silent=True)
        if data.get('name') is None or not isinstance(data['name'], str):
            return api.utils.makeResult(False, "invalid request")
        if data.get('password') is None or not isinstance(data['password'], str):
            return api.utils.makeResult(False, "invalid request")
        if data.get('slogan') is None or not isinstance(data['slogan'], str):
            return api.utils.makeResult(False, "invalid request")
        if data.get('level') is None or not isinstance(data['level'], int):
            return api.utils.makeResult(False, "invalid request")

        return dataManager.createUser(data['name'], data['password'], data['slogan'], data['level'])
    else:
        return api.utils.makeResult(False, "permission denied")


if __name__ == "__main__":
    # print(dataManager.executeInitScript())
    webApplication.config[
        "SECRET_KEY"] = f'Fireworks are for now, but friends are forever!'
    webApplication.run(host=api.utils.catchError(webLogger, dataManager.getXmsHost(
    )), port=api.utils.catchError(webLogger, dataManager.getXmsPort()))
