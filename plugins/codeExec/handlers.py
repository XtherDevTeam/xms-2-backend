import multiprocessing
import subprocess
import time

def execution(taskInfo, arg: str, timeout: int):
    limitation = timeout * 2
    currentCount = 0
    process = subprocess.Popen(arg, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
                
            currentCount += 1
            if currentCount > limitation:
                logText += 'TERMINATED due to timeout'
                process.terminate()
                taskInfo.setLogText(logText)
                taskInfo.ended()
                return
            else:
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

    

def exec(dm, taskInfo, args: list):
    try:
        execution(taskInfo, args[0], args[1])
    except Exception as e:
        taskInfo.setLogText(f'ERROR {str(e)}')
        taskInfo.ended()