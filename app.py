import flask
import flask_cors
import requests
import logging
import time
import os
import re
from io import BytesIO

import api.dataManager
import api.utils
import api.xms

database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(database, "./root")

webLogger = logging.Logger("webApplication")
webApplication = flask.Flask(__name__)

flask_cors.CORS(webApplication)


def checkIfLoggedIn():
    return flask.session.get("loginState")


def makeFileResponse(path, mime):
    isPreview = not mime.startswith('application')
    if flask.request.headers.get('Range') != None:
        startIndex = 0
        part_length = 2 * 1024 * 1024
        startIndex = int(flask.request.headers.get('Range')[flask.request.headers.get(  # type:ignore
            'Range').find('=')+1:flask.request.headers.get('Range').find('-')])  # type:ignore
        endIndex = startIndex + part_length - 1
        fileLength = os.path.getsize(path)

        if endIndex > fileLength:
            endIndex = fileLength - 1

        response_file = bytes()

        with open(path, 'rb') as file:
            file.seek(startIndex)
            response_file = file.read(part_length)

        response = flask.make_response(response_file)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Range'] = 'bytes ' + \
            str(startIndex) + '-' + \
            str(endIndex) + '/' + str(fileLength)
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
    return {
        "coreCodeName": api.xms.xmsCoreCodeName,
        "coreBuildNumber": api.xms.xmsCoreBuildNumber,
        "xmsProjectAuthor": api.xms.xmsProjectAuthor,
        "serverTime": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time())),
        "instanceName": api.xms.xmsInstanceName,
        "instanceDescription": api.xms.xmsInstanceDescription,
    }


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
    username = data.get("username")
    password = data.get("password")
    slogan = data.get("slogan")
    if username is None or password is None or slogan is None:
        return api.utils.makeResult(False, "incomplete request")
    else:
        if isinstance(username, str) and isinstance(password, str) and isinstance(slogan, str):
            return dataManager.createUser(username, password, slogan, 2)
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

    if not avatar.content_type.startswith("image/"):  # type: ignore
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

    if not headimg.content_type.startswith("image/"):  # type: ignore
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
        webLogger.info(f"uploading files: {i} {j.filename}")
        result = dataManager.queryFileUploadRealpath(
            uid, f"{path}/{j.filename}")
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
    if d['owner'] != uid:  # type: ignore
        return api.utils.makeResult(False, "user isn't the owner of playlist")
    return dataManager.deleteUserPlaylistById(id)


@webApplication.route("/xms/v1/music/playlist/<id>/info", methods=["GET"])
def routeMusicPlaylistInfo(id):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:  # type: ignore
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
        return api.utils.makeResult(False, "premission denied")

    return api.utils.makeResult(True, songInfo)


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
        return api.utils.makeResult(False, "premission denied")

    data = dataManager.querySongArtworkFromPlaylist(id)
    if data['ok']:
        return flask.send_file(BytesIO(data['data']['artwork']), data['data']['mime'])
    else:
        return data


@webApplication.route("/xms/v1/music/playlist/<id>/songs/<offset>/<limit>", methods=["GET"])
def routeMusicPlaylistSongs(id, offset, limit):
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    d = dataManager.checkUserPlaylistIfExistByPlaylistId(id)
    if d is None:
        return api.utils.makeResult(False, "playlist not exist")
    if d['owner'] != uid:  # type: ignore
        return api.utils.makeResult(False, "user isn't the owner of playlist")

    return dataManager.queryUserPlaylistSongs(id, limit, offset)


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
    if d['owner'] != uid:  # type: ignore
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
    if d['owner'] != uid:  # type: ignore
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
    return dataManager.deleteShareLink(id)


@webApplication.route("/xms/v1/sharelink/<id>/file", methods=["POST"])
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


@webApplication.route("/xms/v1/sharelink/<id>/dir/file", methods=["POST"])
def routeShareLinkDirFile(id: str):
    data = flask.request.get_json()
    path = data.get('path')
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


if __name__ == "__main__":
    # print(dataManager.executeInitScript())
    webApplication.config["SECRET_KEY"] = 'Fireworks are for now, but friends are forever!'
    webApplication.run(host=api.utils.catchError(webLogger, dataManager.getXmsHost(
    )), port=api.utils.catchError(webLogger, dataManager.getXmsPort()))
