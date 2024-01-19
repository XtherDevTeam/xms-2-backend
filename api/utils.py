import hashlib
import logging
import os
import music_tag
import random
import time
import mimetypes
import shutil

random.seed(int(time.time() * 100))


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
    shutil.rmtree(path)
    
    
def move(path: str, newPath: str):
    shutil.move(path, newPath)
    
    
def copy(path: str, newPath: str):
    shutil.copy(path, newPath)


def getSongInfo(songPath: str):
    file = music_tag.load_file(songPath)
    return {
        'title': file['title'].value,  
        'album': file['album'].value,  
        'artist': file['artist'].value,  
        'composer': file['composer'].value,  
    }


def getSongArtwork(songPath: str):
    file = music_tag.load_file(songPath)
    print("where's my change", file['artwork'].first)
    return {
        'mime': 'image/png',  
        'artwork': file['artwork'].first.data  
    }


def getRandom10CharString(salt):
    return hashlib.md5(f'{int(time.time() * 100)}{str(salt)}{random.randint(0, 114514191)}'.encode('utf-8')).hexdigest()[0:10]


def getPathInfo(path: str):
    fileStat = os.stat(path)
    mime = mimetypes.guess_type(path)[0]
    return {
        "filename": os.path.basename(path),
        "type": "file" if os.path.isfile(path) else "dir",
        "lastModified": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(fileStat.st_mtime)),
        "mime": mime if mime is not None else "application/octet-stream" if os.path.isfile(path) else "None"
    }
