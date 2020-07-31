import json
from io import BytesIO

import cloudinary.api
from PIL import Image

cloudinary.config(
  cloud_name = "darkmattr",
  api_key = "622135512941369",
  api_secret = "tuZdXvyFCostDHdYfOlM39fCDvU"
)

with open('data/skinToPos.json') as file:
    data = json.load(file)

infile = 'renders.png'
im = Image.open(infile)
im = im.crop((0,0,50,31200))

d = {}
for r in data:
    d[int(r)] = {}
    for skin in data[r]:
        pos = data[r][skin]
        im1 = im.crop((0, (pos*50), 50, (pos*50)+50))
        bytes = BytesIO()
        im1.save(bytes, format='PNG')
        bytes.seek(0)
        name = f"realm-pics/Skin-{r}-{skin}"
        res = cloudinary.uploader.upload(bytes, public_id=name)
        print(res['secure_url'])
        d[int(r)][int(skin)] = res['secure_url']

with open('data/skinImages.json', 'w') as file:
    json.dump(d, file)


with open('data/rdefinitions.json') as file:
    data = json.load(file)

infile = 'renders.png'
im = Image.open(infile)


d = {}
for r in data:
    id = str(r)
    x = data[r][3]
    y = data[r][4]
    im1 = im.crop((x, y, x+46, y+46))
    bytes = BytesIO()
    im1.save(bytes, format='PNG')
    bytes.seek(0)
    name = f"realm-pics/Item-{id}"
    res = cloudinary.uploader.upload(bytes, public_id=name)
    print(res['secure_url'])
    d[id] = res['secure_url']

with open('data/itemImages.json', 'w') as file:
    json.dump(d, file)


with open('data/rpetdefinitions.json') as file:
    rdata = json.load(file)

infile = 'renders.png'
im = Image.open(infile)

for r in rdata:
    id = str(r)
    x = rdata[r][1]
    y = rdata[r][2]
    im1 = im.crop((x, y, x+46, y+46))
    bytes = BytesIO()
    im1.save(bytes, format='PNG')
    bytes.seek(0)
    name = f"realm-pics/Item-{id}"
    res = cloudinary.uploader.upload(bytes, public_id=name)
    print(res['secure_url'])
    dict[id] = res['secure_url']

with open('data/itemImages.json', 'w') as file:
    json.dump(dict, file)