import json
from pathlib import Path
from PIL import Image, ImageDraw
a = Path("results/pilot_cs/analysis")
gaps = []
for f in sorted((a / "k1").glob("case*.json")):
    k = json.loads(f.read_text()); o = json.loads((a / "oracle_gen" / f.name).read_text())
    gaps.append((o["counts"]["cars_4wheel"] - k["counts"]["cars_4wheel"], k["case"], o["counts"]["cars_4wheel"], k["counts"]["cars_4wheel"], o["counts"]["pedestrians"], k["counts"]["pedestrians"]))
gaps.sort(reverse=True)
print(gaps[:5]); print("zero/neg gap cases:", [g[1] for g in gaps if g[0] <= 0])
pick = [gaps[0][1], gaps[len(gaps)//2][1]]
W, H = 768, 432
sheet = Image.new("RGB", (W * 2, H * 2), "white")
for r, case in enumerate(pick):
    for c, v in enumerate(("oracle_gen", "k1")):
        im = Image.open(a / v / f"{case}_det.jpg").convert("RGB").resize((W, H))
        d = ImageDraw.Draw(im); d.rectangle([0, 0, 260, 16], fill="black"); d.text((4, 3), f"{case} {v}", fill="white")
        sheet.paste(im, (c * W, r * H))
sheet.save("results/pilot_cs/k1_vs_oracle.jpg", quality=88)
