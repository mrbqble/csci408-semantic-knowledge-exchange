import json
from PIL import Image, ImageDraw
import paths
case = 112
meta = json.load(open(f"results/v3/prompt_refine/case{case}.json"))
orig = Image.open(paths.CARLA_V3 / f"case{case}" / "cam1.jpg").convert("RGB").resize((1024, 576), Image.LANCZOS)
a = Image.open(f"results/v3/prompt_only/case{case}.png").convert("RGB"); b = Image.open(f"results/v3/prompt_refine/case{case}.png").convert("RGB")
wins = [w for w in meta["refine"]["windows"] if "error" not in w][:3]
print([(w["x0"], w["y0"], w["n_blobs"]) for w in wins], meta["refine"]["uncovered_blobs"])
Z = 384
sheet = Image.new("RGB", (3 * Z, len(wins) * Z), "white")
for r, w in enumerate(wins):
    box = (w["x0"], w["y0"], w["x0"] + 128, w["y0"] + 128)
    for c, im in enumerate((orig, a, b)):
        sheet.paste(im.crop(box).resize((Z, Z), Image.BICUBIC), (c * Z, r * Z))
sheet.save("_scratch/peek_refine.jpg", quality=90)
