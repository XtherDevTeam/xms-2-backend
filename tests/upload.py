import requests

r = requests.post("http://localhost:11453/xms/v1/signin", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu"})
print(r.content.decode('utf-8'))
r = requests.post("http://localhost:11453/xms/v1/drive/upload", params={"path": "/"}, cookies=r.cookies, files={"111.txt": open("111.txt", "rb+")})
print(r.content.decode('utf-8'))