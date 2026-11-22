#!/usr/bin/env python3
"""Canny threshold sweep for the MMSD edge map (Iteration 1).

The seed paper generates edge maps "using the Canny edge detector with the
default threshold settings", but OpenCV's Canny has no default thresholds. This
script measures the lossless-WebP edge-map size under several settings,
including Gaussian pre-smoothing (scikit-image's Canny smooths with sigma = 1
by default), to see which setting reproduces the paper's 18.41 KB on Cityscapes.

Usage
  python canny_sweep.py --images data/cityscapes_val --out results/iteration1_canny_sweep_cityscapes_val.json
"""
import argparse
import json
import statistics
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import mmsd_sender as ms

# (label, gaussian sigma or 0 for none, low, high)
SETTINGS = [
    ("canny_50_150", 0, 50, 150),
    ("canny_100_200", 0, 100, 200),     # mmsd_sender.py default
    ("canny_150_250", 0, 150, 250),
    ("canny_200_300", 0, 200, 300),
    ("blur1_canny_100_200", 1.0, 100, 200),
    ("blur1_canny_50_150", 1.0, 50, 150),
]


def edges(rgb, sigma, low, high):
    gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
    if sigma:
        gray = cv2.GaussianBlur(gray, (0, 0), sigma)
    return cv2.Canny(gray, low, high)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if args.limit:
        files = files[: args.limit]
    rows = []
    for f in files:
        rgb = Image.open(f).convert("RGB")
        row = {"file": f.name}
        for label, sigma, low, high in SETTINGS:
            e = edges(rgb, sigma, low, high)
            row[label] = {"bytes": len(ms.encode_edges(e)), "edge_pixel_share": float((e > 0).mean())}
        rows.append(row)
    summary = {label: {"mean_kb": statistics.fmean(r[label]["bytes"] for r in rows) / 1024,
                       "mean_edge_pixel_share": statistics.fmean(r[label]["edge_pixel_share"] for r in rows)}
               for label, *_ in SETTINGS}
    result = {"config": {"images": str(args.images), "n": len(rows), "encoding": "lossless WebP",
                         "settings": SETTINGS},
              "seed_table2_edge_kb": ms.SEED_TABLE2["edge_kb"], "summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    for label, s in summary.items():
        print(f"{label:22s} {s['mean_kb']:6.2f} KB  edge pixels {100 * s['mean_edge_pixel_share']:.2f}%")
    print(f"paper: {ms.SEED_TABLE2['edge_kb']} KB | wrote {args.out}")


if __name__ == "__main__":
    main()
