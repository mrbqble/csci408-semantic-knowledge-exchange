#!/usr/bin/env python3
"""Encoding ablation for the MMSD sender maps (Iteration 1).

The seed paper says the segmentation and edge maps are "compressed using WebP"
but not which WebP mode or quality. Payload depends heavily on that choice, so
this script measures the same maps under several encodings:

  webp_q80        lossy WebP, Pillow default quality (mmsd_sender.py default)
  webp_q50        lossy WebP, quality 50
  webp_lossless   lossless WebP
  png             optimised PNG (palettised colour map; 1-bit edges), as in
                  the September feasibility probe

Usage
  python encoding_ablation.py --images data/coco_urban --out results/iteration1_encoding_ablation_coco_urban.json
"""
import argparse
import io
import json
import statistics
from pathlib import Path

import numpy as np
from PIL import Image

import mmsd_sender as ms


def _save(img, **kw):
    buf = io.BytesIO()
    img.save(buf, **kw)
    return len(buf.getvalue())


def seg_variants(labels):
    rgb = Image.fromarray(ms.colourise(labels), mode="RGB").resize(ms.SEG_SIZE, Image.NEAREST)
    idx = Image.fromarray(labels, mode="L").resize(ms.SEG_SIZE, Image.NEAREST)
    pal = idx.convert("P")
    pal.putpalette(ms.CITYSCAPES_PALETTE.flatten().tolist())
    return {"webp_q80": _save(rgb, format="WEBP", quality=80),
            "webp_q50": _save(rgb, format="WEBP", quality=50),
            "webp_lossless": _save(rgb, format="WEBP", lossless=True),
            "png": _save(pal, format="PNG", optimize=True)}


def edge_variants(edges):
    gray = Image.fromarray(edges, mode="L")
    return {"webp_q80": _save(gray, format="WEBP", quality=80),
            "webp_q50": _save(gray, format="WEBP", quality=50),
            "webp_lossless": _save(gray, format="WEBP", lossless=True),
            "png": _save(gray.convert("1"), format="PNG", optimize=True)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()

    device = ms.pick_device(args.device)
    seg = ms.Segmenter(device)
    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    rows = []
    for f in files:
        rgb = Image.open(f).convert("RGB")
        rows.append({"file": f.name, "w": rgb.width, "h": rgb.height,
                     "seg": seg_variants(seg(rgb)), "edge": edge_variants(ms.canny_edges(rgb))})
    summary = {}
    for part in ("seg", "edge"):
        summary[part] = {k: statistics.fmean(r[part][k] for r in rows) for k in rows[0][part]}
    result = {"config": {"images": str(args.images), "n": len(rows), "seg_size": ms.SEG_SIZE,
                         "canny": [ms.CANNY_LOW, ms.CANNY_HIGH], "seg_model": ms.SEG_MODEL},
              "seed_table2": ms.SEED_TABLE2, "summary_mean_bytes": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    for part in ("seg", "edge"):
        print(part, {k: f"{v/1024:.2f} KB" for k, v in summary[part].items()})
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
