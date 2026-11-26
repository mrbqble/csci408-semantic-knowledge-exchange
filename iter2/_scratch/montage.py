import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, "..")
case = sys.argv[1]
orig = Image.open(rf"C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd\{case}\cam1.jpg").convert("RGB").resize((768, 432))
seg = Image.open(rf"data\carla_v2_payloads\{case}\cam1_seg.webp").convert("RGB").resize((768, 432), Image.NEAREST)
tiles = [("original cam1", orig), ("seg payload cam1", seg)]
for name, p in [("k1", f"results/smoke/k1/{case}_cam1.png"), ("prompt_only", f"results/smoke/prompt_only/{case}.png"), ("ipa_seg", f"results/smoke/ipa_seg/{case}.png")]:
    tiles.append((name, Image.open(p).convert("RGB").resize((768, 432))))
W, H = 768, 432
sheet = Image.new("RGB", (W * 2, H * 3), "white")
for i, (label, im) in enumerate(tiles):
    x, y = (i % 2) * W, (i // 2) * H
    sheet.paste(im, (x, y))
    d = ImageDraw.Draw(sheet); d.rectangle([x, y, x + 230, y + 18], fill="black"); d.text((x + 4, y + 3), label, fill="white")
sheet.save(f"results/smoke/montage_{case}.jpg", quality=88)
print("ok")
