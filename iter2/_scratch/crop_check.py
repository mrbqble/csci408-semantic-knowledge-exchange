import json
from PIL import Image
rows = [json.loads(l) for l in open("data/train_crops/train/metadata.jsonl")]
r = next(x for x in rows if x["small_vehicle_blobs"] >= 3)
print(r["case"], r["cam"], r["x0"], r["y0"], r["small_vehicle_blobs"], "|", r["text"])
d = "data/train_crops/"
tiles = [Image.open(d + r[k]).convert("RGB") for k in ("image", "conditioning_seg", "conditioning_edge")]
sheet = Image.new("RGB", (3 * 512, 512))
for i, t in enumerate(tiles): sheet.paste(t, (i * 512, 0))
sheet.save("_scratch/crop_check.jpg", quality=88)
