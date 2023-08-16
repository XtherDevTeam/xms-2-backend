import multiprocessing
import subprocess
import time
import os

def downloadMusic(taskInfo, searchParam: str, realSavePath: str, proxyType: bool, proxyUrl: str):
    env = os.environ.copy()
    if proxyType == "HTTP(S)":
        env['http_proxy'] = proxyUrl
        env['https_proxy'] = proxyUrl
    
    cmdline = f'python3 -m spotdl --audio youtube-music --lyrics musixmatch --format mp3 --bitrate auto download "{searchParam}"'
    process = subprocess.Popen(cmdline, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=realSavePath)
    
    logs = []
    try:
        while process.poll() is None:
            time.sleep(0.5)
            for i in process.stdout.readlines()[-100:]:
                logs.append(i)
            logs = logs[-100:]
            logText = ''
            for i in logs:
                logText += i
                
            taskInfo.setLogText(logText)
                
        for i in process.stdout.readlines()[-100:]:
            logs.append(i)
        logs = logs[-100:]
        logText = ''
        for i in logs:
            logText += i
        logText += f'OK with status code {process.returncode}'
        
        taskInfo.setLogText(logText)
        taskInfo.ended()
    except Exception as e:
        process.terminate()
        taskInfo.setLogText(f'ERROR {str(e)}')
        taskInfo.ended()

    

def download(dm, taskInfo, args: list):
    try:
        task = dm.queryTask(taskInfo.id)['data']
        data = taskInfo.db.query("select * from config", one=True)
        path = os.path.realpath(dm.queryFileUploadRealpath(task['owner'], args[1])['data'])
        downloadMusic(taskInfo, args[0], path, data['proxyType'], data['proxyUrl'])
    except Exception as e:
        taskInfo.setLogText(f'ERROR {str(e)}')
        taskInfo.ended()