"""Shared scoring helpers for the sender-side experiments on CARLA v3 (Rec1 = cam1, 917 ground-truth vehicles).

Ground truth: vehicles visible with >= 80 px at 960x540, boxes scaled to the 1024x576 frame of the transmitted segmentation map.
Categories (from the plain vehicle blobs of the transmitted map, as in loss_breakdown.py): own blob / merged blob / no blob.
"""
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import paths
from blob_split import BINS, H, S, W, match, vehicle_mask

PAY = Path("data/v3_payloads")


def gt_cases():
    manifest = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    out = []
    for case in manifest["cases"]:
        gt = [i for i in case["cameras"][0]["instances"] if i["kind"] == "car" and i["counts_in_gt"]]
        if not gt:
            continue
        boxes = [(max(int(v[0] * S), 0), max(int(v[1] * S), 0), min(int(round(v[2] * S)) + 1, W), min(int(round(v[3] * S)) + 1, H))
                 for v in (g["bbox_px"] for g in gt)]
        seg = Image.open(PAY / case["folder"] / "cam1_seg.webp").convert("RGB")
        out.append({"name": case["folder"], "boxes": boxes, "photo": paths.CARLA_V3 / case["folder"] / "cam1.jpg",
                    "payload_mask": vehicle_mask(seg), "cars": case["cameras"][0]["counts"]["cars"]})
    return out


def categories(boxes, mask):
    """own blob / merged blob / no blob for every ground-truth box, from a binary vehicle mask in the 1024x576 frame."""
    n, lab = cv2.connectedComponents(mask, connectivity=8)
    best, cover = [], []
    for (x1, y1, x2, y2) in boxes:
        sub = lab[y1:y2, x1:x2]
        cnt = np.bincount(sub[sub > 0].ravel(), minlength=n) if (sub > 0).any() else np.zeros(n, int)
        best.append(int(cnt.argmax()) if cnt.max() > 0 else 0)
        cover.append(float((sub > 0).mean()))
    owners = defaultdict(list)
    for gi, b in enumerate(best):
        if b > 0 and cover[gi] >= 0.30:
            owners[b].append(gi)
    return ["no blob" if (best[g] == 0 or cover[g] < 0.30) else ("merged blob" if len(owners[best[g]]) >= 2 else "own blob") for g in range(len(boxes))]


def side(b):
    return ((b[2] - b[0]) * (b[3] - b[1])) ** 0.5


def score(cases, preds, cats):
    """cases: gt_cases(); preds: {case name: [boxes in the 1024x576 frame]}; cats: {case name: categories of its gt boxes}."""
    tp5 = tp3 = npred = total = 0
    bins = {b[2]: [0, 0] for b in BINS}
    cat = defaultdict(lambda: [0, 0])
    errs = []
    for c in cases:
        pb = preds.get(c["name"], [])
        h5, h3 = match(c["boxes"], pb, 0.5), match(c["boxes"], pb, 0.3)
        tp5 += int(h5.sum()); tp3 += int(h3.sum()); npred += len(pb); total += len(c["boxes"])
        errs.append(len(pb) - len(c["boxes"]))
        for gi, b in enumerate(c["boxes"]):
            for lo, hi, name in BINS:
                if lo <= side(b) < hi:
                    bins[name][0] += 1; bins[name][1] += int(h5[gi])
            k = cats[c["name"]][gi]
            cat[k][0] += 1; cat[k][1] += int(h5[gi])
    e = np.array(errs, float)
    return {"recall5": tp5 / total, "recall3": tp3 / total, "precision5": tp5 / max(npred, 1), "n_pred": npred,
            "bins": {k: v[1] / max(v[0], 1) for k, v in bins.items()},
            "cats": {k: (v[1] / max(v[0], 1), v[0]) for k, v in cat.items()},
            "count_mae": float(np.abs(e).mean()), "count_bias": float(e.mean()), "within1": float((np.abs(e) <= 1).mean())}


def header():
    return (f"{'method':34}{'rec@.5':>7}{'@.3':>6}{'prec':>6}" + "".join(f"{b[2]:>9}" for b in BINS) +
            f"{'own':>6}{'merged':>8}{'noblob':>8}{'MAE':>6}{'bias':>6}{'in±1':>6}")


def row(label, s):
    c = s["cats"]
    return (f"{label:34}{s['recall5']:7.2f}{s['recall3']:6.2f}{s['precision5']:6.2f}" + "".join(f"{s['bins'][b[2]]:9.2f}" for b in BINS) +
            f"{c.get('own blob', (float('nan'), 0))[0]:6.2f}{c.get('merged blob', (float('nan'), 0))[0]:8.2f}{c.get('no blob', (float('nan'), 0))[0]:8.2f}"
            f"{s['count_mae']:6.2f}{s['count_bias']:6.2f}{s['within1']:6.2f}")
