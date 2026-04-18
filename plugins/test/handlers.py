import json

def test(dm, taskInfo, args: list):
    try:
        taskInfo.setLogText(f"Success with arguments: {json.dumps(args)}")
        taskInfo.ended()
    except Exception as e:
        print(e, str(e))