#!/usr/bin/env python3
"""Prepare Cityscapes val subset and re-run the feasibility probe at full 2048x1024.

Run AFTER csDownload has fetched the zips into this directory.
Works with whatever is present:
  - gtFine_trainvaltest.zip alone  -> measures ground-truth label-map payload
                                      at full res (the fast, 241 MB answer)
  - + leftImg8bit_trainvaltest.zip -> full probe: seg + edges + caption + JPEG

Usage:
    .\\.venv\\Scripts\\python.exe prep_cityscapes.py
"""
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
GT_ZIP = ROOT / "gtFine_trainvaltest.zip"
IMG_ZIP = ROOT / "leftImg8bit_trainvaltest.zip"
CS_IMG = ROOT / "images_cityscapes"
CS_GT = ROOT / "gt_cityscapes"
N = 25


def val_members(zf, suffix):
    """Val-split entries only, sorted for determinism."""
    return sorted(n for n in zf.namelist()
                  if "/val/" in n and n.endswith(suffix))


def extract(zf, names, outdir):
    outdir.mkdir(exist_ok=True)
    for n in names:
        target = outdir / Path(n).name
        with zf.open(n) as src, open(target, "wb") as dst:
            dst.write(src.read())
    return len(names)


# ---- ground truth label maps (available from the 241 MB package alone) ----
if GT_ZIP.exists():
    print(f"Reading {GT_ZIP.name}...")
    with zipfile.ZipFile(GT_ZIP) as z:
        gt = val_members(z, "_gtFine_labelIds.png")[:N]
        n = extract(z, gt, CS_GT)
    print(f"  extracted {n} ground-truth label maps -> {CS_GT.name}/")

    # payload of GT label maps at native 2048x1024, palettised like the probe does
    import io
    import numpy as np
    from PIL import Image
    sizes = []
    for p in sorted(CS_GT.glob("*.png")):
        arr = np.array(Image.open(p))
        buf = io.BytesIO()
        Image.fromarray(arr.astype(np.uint8), mode="P").save(
            buf, format="PNG", optimize=True)
        sizes.append(len(buf.getvalue()))
    mean_gt = sum(sizes) / len(sizes)
    print(f"\n  GROUND-TRUTH segmentation payload @2048x1024: {mean_gt:,.0f} B "
          f"({mean_gt/1024:.1f} KB)")
    print(f"  Compare: SegFormer-B0 prediction @0.27 MP was 409 B")
    print(f"  Ratio: {mean_gt/409:.1f}x")
    print("  NOTE: hand-annotated GT is more detailed than model output -> "
          "treat as an UPPER bound.\n")
else:
    print(f"[skip] {GT_ZIP.name} not found")

# ---- real images (needs the 11 GB package) ----
if IMG_ZIP.exists():
    print(f"Reading {IMG_ZIP.name} (large, be patient)...")
    with zipfile.ZipFile(IMG_ZIP) as z:
        imgs = val_members(z, "_leftImg8bit.png")[:N]
        n = extract(z, imgs, CS_IMG)
    print(f"  extracted {n} images -> {CS_IMG.name}/")

    py = ROOT / ".venv" / "Scripts" / "python.exe"
    if not py.exists():
        py = Path(sys.executable)
    print("\nRunning probe at full Cityscapes resolution...\n")
    subprocess.run([str(py), str(ROOT / "semantic_probe.py"),
                    "--images", str(CS_IMG), "--device", "cpu",
                    "--threads", "4", "--out", "probe_cityscapes.json"],
                   cwd=ROOT, check=False)
else:
    print(f"[skip] {IMG_ZIP.name} not found - "
          f"run the gtFine step first, it answers the main question")
