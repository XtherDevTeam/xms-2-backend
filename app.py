import flask
import flask_cors
import requests
import logging
import time
import os
from io import BytesIO

import api.dataManager
import api.utils
import api.xms

database = api.dataManager.databaseObject("./root/blob/xms.db")
dataManager = api.dataManager.dataManager(database, "./root")

webLogger = logging.Logger("webApplication")
webApplication = flask.Flask(__name__)


def checkIfLoggedIn():
    return flask.session.get("loginState")


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
        "serverTime": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
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


@webApplication.route("/xms/v1/drive/dir", methods=["GET"])
def routeDriveDir():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    return dataManager.getUserDriveDirInfo(uid, path)


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


@webApplication.route("/xms/v1/drive/file", methods=["GET"])
def routeDriveFile():
    uid = checkIfLoggedIn()
    if uid is None:
        return api.utils.makeResult(False, "user haven't logged in yet")
    data = flask.request.get_json()
    path = data.get('path')
    if path is None or not isinstance(path, str):
        return api.utils.makeResult(False, "invalid request")

    try:
        result = dataManager.queryFileRealpath(uid, path)
        if result['ok']:
            result = result['data']
            isPreview = result['mime'].startswith('application')
            if flask.request.headers.get('Range') != None:
                startIndex = 0
                part_length = 2 * 1024 * 1024
                startIndex = int(flask.request.headers.get('Range')[flask.request.headers.get(  # type:ignore
                    'Range').find('=')+1:flask.request.headers.get('Range').find('-')])  # type:ignore
                endIndex = startIndex + part_length - 1
                fileLength = os.path.getsize(result['path'])

                if endIndex > fileLength:
                    endIndex = fileLength - 1

                response_file = bytes()

                with open(result['path'], 'rb') as file:
                    file.seek(startIndex)
                    response_file = file.read(part_length)

                response = flask.make_response(response_file)
                response.headers['Accept-Ranges'] = 'bytes'
                response.headers['Content-Range'] = 'bytes ' + \
                    str(startIndex) + '-' + \
                    str(endIndex) + '/' + str(fileLength)
                response.headers['Content-Type'] = result['mime']
                if response.headers['Content-Type'].startswith('application'):
                    response.headers['Content-Disposition'] = "attachment; filename=" + \
                        os.path.basename(result['path'])

                response.status_code = 206
                return response
            return flask.send_file(result['path'], as_attachment=not isPreview, download_name=os.path.basename(result['path']), mimetype=result['mime'])
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
        webLogger.info(f"uploading files: {i}")
        result = dataManager.queryFileUploadRealpath(uid, f"{path}/{i}")
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


if __name__ == "__main__":
    # print(dataManager.executeInitScript())
    webApplication.config["SECRET_KEY"] = 'Fireworks are for now, but friends are forever!'
    webApplication.run(host=api.utils.catchError(webLogger, dataManager.getXmsHost(
    )), port=api.utils.catchError(webLogger, dataManager.getXmsPort()))
