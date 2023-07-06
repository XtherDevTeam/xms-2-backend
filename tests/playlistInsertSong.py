import requests

r = requests.post("http://localhost:11453/xms/v1/signin", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu"})
print(r.content.decode('utf-8'))
r = requests.post("http://localhost:11453/xms/v1/music/playlist/1/songs/insert", json={"songPath": "/Amewomate.mp3"}, cookies=r.cookies)
print(r.content.decode('utf-8'))