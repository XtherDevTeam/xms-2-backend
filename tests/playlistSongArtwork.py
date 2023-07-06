import requests

r = requests.post("http://localhost:11453/xms/v1/signin", json={"username": "JerryChau", "password": "YoimiyaIsMyWaifu"})
print(r.content.decode('utf-8'))
r = requests.get("http://localhost:11453/xms/v1/music/song/1/artwork", cookies=r.cookies, stream=True)

with open("testArtwork.jpg", "wb+") as artwork:
    for i in r.iter_content(1048576):
        artwork.write(i)