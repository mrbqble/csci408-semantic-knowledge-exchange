"""OMEN helper: extract the 500 Cityscapes val images and report the environment."""
import zipfile
from pathlib import Path

import cv2
import torch
import transformers
from PIL import features

here = Path(__file__).resolve().parent            # ...\csci408-probe\iter1
zp = here.parent / "leftImg8bit_trainvaltest.zip"
out = here / "data" / "cityscapes_val"
out.mkdir(parents=True, exist_ok=True)

z = zipfile.ZipFile(zp)
vals = [n for n in z.namelist() if n.startswith("leftImg8bit/val/") and n.endswith(".png")]
new = 0
for name in vals:
    dst = out / Path(name).name
    if not dst.exists():
        with z.open(name) as src, open(dst, "wb") as f:
            f.write(src.read())
        new += 1
print("val pngs in zip:", len(vals), "| newly extracted:", new, "| on disk:", len(list(out.glob("*.png"))))
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
print("transformers", transformers.__version__, "| cv2", cv2.__version__, "| webp", features.check("webp"))
