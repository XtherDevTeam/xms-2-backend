import requests

r = requests.post("http://localhost:11453/xms/v1/signin", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu"})
print(r.content.decode('utf-8'))
r = requests.post("http://localhost:11453/xms/v1/music/playlist/create", json={"name": "2023 Summer", "description": "Fireworks are for now, but friends are forever!"}, cookies=r.cookies)
print(r.content.decode('utf-8'))