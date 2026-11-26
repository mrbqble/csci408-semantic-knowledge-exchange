#!/usr/bin/env python3
"""Does the sender's segmenter find more vehicles when it looks at the photo at a higher input resolution? (CARLA v3, cam1, GPU)

The sender today runs Mask2Former (Cityscapes semantic) on the photo shrunk to 512x1024. Here the same model runs at larger input sizes; the label map
is resized to the 1024x576 map that is transmitted and scored against the 917 ground-truth vehicles:
  own blob / merged blob / no blob  share of vehicles, from the vehicle region of that map (as in loss_breakdown.py)
  recall / precision                plain vehicle blobs, and blobs split by the distance-transform watershed (alpha 0.5), vs ground-truth boxes
  seconds per photo, peak GPU memory
The payload size does not change (the map is still sent at 1024x576); only the sender's compute does.
Usage: python seg_resolution.py
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import gtlib
from blob_split import H, W, instance_boxes

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "iter1"))
import mmsd_sender as ms  # noqa: E402

SIZES = [(512, 1024), (768, 1376), (1024, 1824), (1088, 1920)]     # (height, width); the first is the sender's current operating point


def main():
    import torch
    device = ms.pick_device("auto")
    seg = ms.Segmenter(device)
    cases = gtlib.gt_cases()
    zero_edge = np.zeros((H, W), np.uint8)
    print(f"{len(cases)} cases, {sum(len(c['boxes']) for c in cases)} ground-truth vehicles", flush=True)
    print(gtlib.header(), flush=True)
    out = {}
    for size in SIZES:
        seg.input_size = size
        masks, secs, failed = {}, [], None
        torch.cuda.reset_peak_memory_stats()
        try:
            for i, c in enumerate(cases):
                rgb = Image.open(c["photo"]).convert("RGB")
                if i == 0:
                    seg(rgb)                                  # untimed warm-up at this size
                torch.cuda.synchronize(); t = time.perf_counter()
                labels = seg(rgb)
                torch.cuda.synchronize(); secs.append(time.perf_counter() - t)
                small = cv2.resize(labels, (W, H), interpolation=cv2.INTER_NEAREST)
                masks[c["name"]] = np.isin(small, (13, 14, 15)).astype(np.uint8)
        except RuntimeError as e:                             # CUDA out of memory
            failed = str(e)[:90]
            torch.cuda.empty_cache()
        label = f"{size[0]}x{size[1]}"
        if failed:
            print(f"{label:34} failed: {failed}", flush=True)
            out[label] = {"failed": failed}
            continue
        cats = {c["name"]: gtlib.categories(c["boxes"], masks[c["name"]]) for c in cases}
        plain = {c["name"]: instance_boxes(masks[c["name"]], zero_edge, "none", {}) for c in cases}
        split = {c["name"]: instance_boxes(masks[c["name"]], zero_edge, "dist", {"alpha": 0.5}) for c in cases}
        s_plain, s_split = gtlib.score(cases, plain, cats), gtlib.score(cases, split, cats)
        print(gtlib.row(label + " plain blobs", s_plain), flush=True)
        print(gtlib.row(label + " + dist split", s_split), f"   {1000 * np.mean(secs):.0f} ms/photo, peak {torch.cuda.max_memory_allocated() / 2**20:.0f} MB", flush=True)
        shares = {k: sum(v.count(k) for v in cats.values()) / sum(len(v) for v in cats.values()) for k in ("own blob", "merged blob", "no blob")}
        out[label] = {"shares": shares, "plain": s_plain, "split": s_split, "ms_per_photo": 1000 * float(np.mean(secs)),
                      "peak_mb": torch.cuda.max_memory_allocated() / 2**20}
        print(f"{'':34} share of vehicles: own {shares['own blob']:.2f}, merged {shares['merged blob']:.2f}, no blob {shares['no blob']:.2f}", flush=True)
    Path("results").mkdir(exist_ok=True)
    Path("results/seg_resolution.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
