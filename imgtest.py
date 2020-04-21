import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import json
import io
from PIL import Image

with open("data/world_data_clean.json") as file:
    data = json.load(file)

img = plt.imread("world-maps/world_1.png")
fig, ax = plt.subplots(1)
ax.set_aspect('equal')
ax.axis("off")
ax.imshow(img)
point = data["world_1.png"]["19"]
circ = Circle((point["x"], point["y"]), 30, color='#0000FFC8')
ax.add_patch(circ)

img = io.BytesIO()
plt.savefig(img, transparent=True, bbox_inches='tight', pad_inches=0, format='png', dpi=500)
img.seek(0)
im = Image.open(img, "r")
im.show()