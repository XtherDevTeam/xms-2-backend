import requests

r = requests.post("http://localhost:11453/xms/v1/signin", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu"})
print(r.content.decode('utf-8'))
r = requests.get("http://localhost:11453/xms/v1/drive/dir", json={"path": "/"}, cookies=r.cookies)
print(r.content.decode('utf-8'))