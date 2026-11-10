#!/usr/bin/env python3
"""Where are Rec1's vehicles lost? Breakdown on CARLA v3 (instance ground truth), cam1 only.

Every ground-truth vehicle (car/truck/bus visible with >= 80 px at 960x540, box scaled to the 1024x576 master view) is assigned to a
category by what Rec1's received segmentation map shows at its box:
  no blob      less than 30% of its box is labelled vehicle (the segmenter missed it or it is tiny)
  merged blob  the vehicle blob it overlaps most is also the best blob of at least one other ground-truth vehicle
  own blob     the blob it overlaps most belongs to it alone
and by size (side of its box). For each group: how often the detector finds it on the ORIGINAL photo (ceiling) and on the receiver's
`prompt_only` master view (IoU >= 0.5 with its box; Hungarian matching so a detection is used once).

Usage: python loss_breakdown.py
"""
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment

import paths
from analysis import box_iou
import geofuse

ANA = Path("results/v3/analysis")
PAY = Path("data/v3_payloads")
S = 1024 / 960
VEH_CLASSES = ("car", "truck", "bus")
BINS = [(0, 24, "<24 px"), (24, 48, "24-48 px"), (48, 120, "48-120 px"), (120, 1e9, ">120 px")]


def found(gt_boxes, det_boxes, thr):
    hit = np.zeros(len(gt_boxes), bool)
    if len(gt_boxes) and len(det_boxes):
        iou = box_iou(np.array(gt_boxes, float), np.array(det_boxes, float))
        r, c = linear_sum_assignment(-iou)
        for i, j in zip(r, c):
            hit[i] = iou[i, j] >= thr
    return hit


def main():
    manifest = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    rows = []        # one per GT vehicle: category, size, oracle hit, receiver hit@0.5, @0.3
    blobs_total = blobs_merged = blobs_empty = 0
    for case in manifest["cases"]:
        name = case["folder"]
        gt = [i for i in case["cameras"][0]["instances"] if i["kind"] == "car" and i["counts_in_gt"]]
        if not gt:
            continue
        seg = Image.open(PAY / name / "cam1_seg.webp").convert("RGB")
        a = np.asarray(seg).astype(np.int64)
        key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
        mask = np.isin(key, [geofuse.KEY[t] for t in (13, 14, 15)]).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        boxes = []
        for g in gt:
            x1, y1, x2, y2 = (v * S for v in g["bbox_px"])
            boxes.append((max(int(x1), 0), max(int(y1), 0), min(int(round(x2)) + 1, 1024), min(int(round(y2)) + 1, 576)))
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
        blobs_total += n - 1
        blobs_merged += sum(1 for v in owners.values() if len(v) >= 2)
        blobs_empty += (n - 1) - len(owners)
        orc = json.loads((ANA / "oracle_gen" / f"{name}.json").read_text())["detections"]
        rec = json.loads((ANA / "prompt_only" / f"{name}.json").read_text())["detections"]
        ob = [d["bbox_master_px"] for d in orc if d["class"] in VEH_CLASSES]
        rb = [d["bbox_master_px"] for d in rec if d["class"] in VEH_CLASSES]
        gb = [list(b) for b in boxes]
        ho, hr5, hr3 = found(gb, ob, 0.5), found(gb, rb, 0.5), found(gb, rb, 0.3)
        for gi, (x1, y1, x2, y2) in enumerate(boxes):
            cat = "no blob" if (best[gi] == 0 or cover[gi] < 0.30) else ("merged blob" if len(owners[best[gi]]) >= 2 else "own blob")
            side = ((x2 - x1) * (y2 - y1)) ** 0.5
            rows.append({"cat": cat, "side": side, "oracle": bool(ho[gi]), "rec5": bool(hr5[gi]), "rec3": bool(hr3[gi])})
    total = len(rows)

    def table(title, groups):
        print(f"\n{title}")
        print(f"{'group':14}{'n':>6}{'share':>8}{'detector on original':>22}{'receiver @IoU.5':>17}{'receiver @IoU.3':>17}")
        for g, rs in groups:
            if not rs:
                continue
            f = lambda k: sum(r[k] for r in rs) / len(rs)
            print(f"{g:14}{len(rs):6}{len(rs) / total:8.2f}{f('oracle'):22.2f}{f('rec5'):17.2f}{f('rec3'):17.2f}")

    print(f"CARLA v3, cam1, {total} ground-truth vehicles in {len(manifest['cases'])} cases; vehicle blobs in the received maps: {blobs_total} "
          f"({blobs_merged} hold >= 2 ground-truth vehicles, {blobs_empty} hold none)")
    table("By what the received segmentation map shows", [(c, [r for r in rows if r["cat"] == c]) for c in ("own blob", "merged blob", "no blob")] + [("all", rows)])
    table("By size (side of the ground-truth box in the 1024x576 view)", [(n_, [r for r in rows if lo <= r["side"] < hi]) for lo, hi, n_ in BINS] + [("all", rows)])
    print("\nBy size x category: receiver @IoU.5 (n)")
    for lo, hi, n_ in BINS:
        cells = []
        for c in ("own blob", "merged blob", "no blob"):
            rs = [r for r in rows if lo <= r["side"] < hi and r["cat"] == c]
            cells.append(f"{c}: {sum(r['rec5'] for r in rs) / len(rs):.2f} (n={len(rs)})" if rs else f"{c}: - (n=0)")
        print(f"{n_:10} " + " | ".join(cells))
    json.dump({"n_gt": total, "blobs": blobs_total, "merged_blobs": blobs_merged}, open("results/loss_breakdown.json", "w"))


if __name__ == "__main__":
    main()
