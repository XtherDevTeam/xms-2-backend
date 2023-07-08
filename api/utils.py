import hashlib
import logging
import os
import music_tag


class XmediaCenterException(BaseException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def makePasswordMd5(userPassword: str):
    return hashlib.md5(f'YoimiyaJyannGaTaisukidesu!XmediaCenter2(JerryChau){userPassword}'.encode('utf-8')).hexdigest()


def makeResult(ok: bool, data):
    return {'ok': ok, 'data': data}


def checkIfUserNameValid(s: str) -> bool:
    if len(s) > 15:
        return False

    d = ['!', '@', '$', '%', '^', '&', '*',
         '(', ')', '{', '}', '[', ']', ';', ':', '"', '\'', '~']
    for i in d:
        s.replace(i, '~')

    if '~' in s:
        return False
    else:
        return True


def catchError(logger: logging.Logger, result):
    if result['ok']:
        return result['data']
    else:
        logger.error(str(result['data']))
        raise XmediaCenterException(result)


def rmdir(path: str):
    for i in os.listdir(path):
        p = os.path.join(path, i)
        if os.path.isfile(p):
            os.remove(p)
        else:
            rmdir(p)
    os.rmdir(path)


def getSongInfo(songPath: str):
    file = music_tag.load_file(songPath)
    return {
        'title': file['title'].value,  # type: ignore
        'album': file['album'].value,  # type: ignore
        'artist': file['artist'].value,  # type: ignore
        'composer': file['composer'].value,  # type: ignore
    }


def getSongArtwork(songPath: str):
    file = music_tag.load_file(songPath)
    return {
        'mime': file['artwork'].first.mime,  # type: ignore
        'artwork': file['artwork'].first.data  # type: ignore
    }
