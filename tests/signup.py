import requests

r = requests.post("http://localhost:11453/xms/v1/signup", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu", "slogan": "Fireworks are for now, but friends are forever!"})
print(r.content.decode('utf-8'))