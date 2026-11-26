#!/usr/bin/env python3
"""Can the payload we already send (segmentation map + full-resolution edge map) separate touching vehicles? CPU only.

For Rec1 (cam1) of every CARLA v3 case: take the vehicle (car, truck, bus) region of the received segmentation map and split it into
instances with
  none   connected components (what the receiver sees today)
  dist   distance-transform watershed: one marker per blob peak (distance >= alpha * the blob's maximum)
  edge   the received edge map cuts the blob (edge pixels removed, pieces become markers), pieces then regrown by watershed
  both   edge cut first, then dist inside every piece
The instances are scored against the v3 ground truth (917 vehicles visible with >= 80 px at 960x540, boxes scaled to the 1024x576 map):
Hungarian matching of component boxes to ground-truth boxes at IoU >= 0.5 (and 0.3), pooled recall and precision, recall by size and by what
the plain blobs look like (own blob / merged blob / no blob, as in loss_breakdown.py), and per-case count error against the ground-truth count.
The receiver's own recall on the same ground truth (prompt_only, IoU 0.5) is 0.48 and the detector on the original photo gets 0.76.

All settings below are tried on the same 112 cases they are scored on: a sweep, so the best row is optimistic.
Usage: python blob_split.py
"""
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

import geofuse
import paths
from analysis import box_iou

PAY = Path("data/v3_payloads")
S = 1024 / 960
W, H = 1024, 576
MIN_AREA = 12
VEH = (13, 14, 15)
BINS = [(0, 24, "<24 px"), (24, 48, "24-48 px"), (48, 120, "48-120 px"), (120, 1e9, ">120 px")]
CONFIGS = [("none", {}), ("dist", {"alpha": 0.5}), ("dist", {"alpha": 0.6}),
           ("edge", {"dil": 1}), ("edge", {"dil": 1, "minpiece": 30}), ("edge", {"dil": 1, "minpiece": 60}), ("edge", {"dil": 1, "minpiece": 120}),
           ("edge", {"dil": 2, "minpiece": 30}), ("edge", {"dil": 2, "minpiece": 60}), ("edge", {"dil": 2, "minpiece": 120}),
           ("both", {"alpha": 0.6, "dil": 1, "minpiece": 60}), ("both", {"alpha": 0.6, "dil": 2, "minpiece": 60}),
           ("both", {"alpha": 0.6, "dil": 1, "minpiece": 120}), ("both", {"alpha": 0.6, "dil": 2, "minpiece": 120})]


def vehicle_mask(seg):
    a = np.asarray(seg).astype(np.int64)
    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    return np.isin(key, [geofuse.KEY[t] for t in VEH]).astype(np.uint8)


def edge_map(edge_l):
    arr = cv2.resize(np.asarray(edge_l), (W, H), interpolation=cv2.INTER_AREA)
    return (arr > 40).astype(np.uint8)


def regrow(roi, markers):
    """Watershed the pixels of the binary crop `roi` from the integer `markers` (0 = unknown); labels 1..n inside the crop."""
    n = int(markers.max())
    if n <= 1:
        return roi.astype(np.int32) * max(n, 1)
    dist = cv2.distanceTransform(roi, cv2.DIST_L2, 3)
    land = (255 * (1 - dist / max(dist.max(), 1e-6))).astype(np.uint8)
    land[roi == 0] = 255
    m = markers.astype(np.int32).copy()
    m[roi == 0] = n + 1                             # background marker
    cv2.watershed(cv2.merge([land, land, land]), m)
    m[(m == n + 1) | (m < 0)] = 0
    miss = (roi > 0) & (m == 0)                     # boundary pixels: give them to the nearest labelled pixel
    if miss.any() and (m > 0).any():
        _, lab = cv2.distanceTransformWithLabels((m == 0).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
        ys, xs = np.nonzero(m > 0)
        ref = np.zeros(int(lab.max()) + 1, np.int32)
        ref[lab[ys, xs]] = m[ys, xs]
        m[miss] = ref[lab[miss]]
    return m * (roi > 0)


def dist_markers(roi, alpha):
    dist = cv2.distanceTransform(roi, cv2.DIST_L2, 3)
    mx = dist.max()
    core = (dist >= max(alpha * mx, min(2.0, mx))).astype(np.uint8) * (roi > 0)
    _, mk = cv2.connectedComponents(core, connectivity=8)
    return mk.astype(np.int32)


def edge_markers(roi, edge_roi, dil, minpiece=6):
    cut = edge_roi
    if dil:
        cut = cv2.dilate(cut, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8))
    pieces = roi & (1 - cut)
    n, lab, st, _ = cv2.connectedComponentsWithStats(pieces, connectivity=8)
    markers = np.zeros(roi.shape, np.int32)
    k = 0
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= minpiece:
            k += 1; markers[lab == i] = k
    return markers


def split_blob(roi, edge_roi, method, p):
    """Instance labels (1..n) of one blob crop."""
    if method == "none":
        return roi.astype(np.int32)
    if method == "dist":
        mk = dist_markers(roi, p["alpha"])
    else:
        mk = edge_markers(roi, edge_roi, p["dil"], p.get("minpiece", 6))
    if mk.max() == 0:
        return roi.astype(np.int32)                 # nothing to split on: the blob stays whole
    lab = regrow(roi, mk)
    if method == "both":                            # dist split inside every edge piece
        out, nxt = np.zeros_like(lab), 0
        for i in range(1, int(lab.max()) + 1):
            sub = (lab == i).astype(np.uint8)
            if not sub.any():
                continue
            mk2 = dist_markers(sub, p["alpha"])
            sl = regrow(sub, mk2) if mk2.max() > 1 else sub.astype(np.int32)
            for j in range(1, int(sl.max()) + 1):
                nxt += 1; out[sl == j] = nxt
        lab = out
    return lab


def instance_boxes(mask, edge, method, p):
    """Boxes (x1, y1, x2, y2) of the instances of a whole vehicle mask, blob by blob on small crops."""
    n, cc, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in st[i])
        if area < MIN_AREA:
            continue
        roi = (cc[y:y + h, x:x + w] == i).astype(np.uint8)
        pad = cv2.copyMakeBorder(roi, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        epad = cv2.copyMakeBorder(edge[y:y + h, x:x + w], 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        lab = split_blob(pad, epad, method, p)
        for j, sl in enumerate(ndimage.find_objects(lab), start=1):
            if sl is None:
                continue
            ys, xs = sl
            if int((lab[sl] == j).sum()) >= MIN_AREA:
                boxes.append((x + xs.start - 1, y + ys.start - 1, x + xs.stop - 1, y + ys.stop - 1))
    return boxes


def match(gt, pred, thr):
    hit = np.zeros(len(gt), bool)
    if len(gt) and len(pred):
        iou = box_iou(np.array(gt, float), np.array(pred, float))
        r, c = linear_sum_assignment(-iou)
        for i, j in zip(r, c):
            hit[i] = iou[i, j] >= thr
    return hit


def main():
    manifest = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    cases = []
    for case in manifest["cases"]:
        gt = [i for i in case["cameras"][0]["instances"] if i["kind"] == "car" and i["counts_in_gt"]]
        if not gt:
            continue
        boxes = [(max(int(v[0] * S), 0), max(int(v[1] * S), 0), min(int(round(v[2] * S)) + 1, W), min(int(round(v[3] * S)) + 1, H))
                 for v in (g["bbox_px"] for g in gt)]
        seg = Image.open(PAY / case["folder"] / "cam1_seg.webp").convert("RGB")
        edge = edge_map(Image.open(PAY / case["folder"] / "cam1_edge.webp").convert("L"))
        cases.append((case["folder"], boxes, vehicle_mask(seg), edge))
    cats = {}                                       # category of every ground-truth vehicle from the plain blobs
    for name, boxes, mask, _ in cases:
        n, lab = cv2.connectedComponents(mask, connectivity=8)
        best, cover = [], []
        for (x1, y1, x2, y2) in boxes:
            sub = lab[y1:y2, x1:x2]
            cnt = np.bincount(sub[sub > 0].ravel(), minlength=n) if (sub > 0).any() else np.zeros(n, int)
            best.append(int(cnt.argmax()) if cnt.max() > 0 else 0); cover.append(float((sub > 0).mean()))
        owners = defaultdict(list)
        for gi, b in enumerate(best):
            if b > 0 and cover[gi] >= 0.30:
                owners[b].append(gi)
        cats[name] = ["no blob" if (best[g] == 0 or cover[g] < 0.30) else ("merged blob" if len(owners[best[g]]) >= 2 else "own blob") for g in range(len(boxes))]
    total = sum(len(b) for _, b, _, _ in cases)
    print(f"{total} ground-truth vehicles in {len(cases)} cases (cam1). Receiver (prompt_only) recall on the same ground truth: 0.48 @IoU.5; detector on the original: 0.76\n", flush=True)
    print(f"{'method':24}{'recall@.5':>10}{'@.3':>7}{'prec@.5':>9}" + "".join(f"{n:>10}" for _, _, n in BINS) + f"{'merged':>8}{'MAE':>6}{'bias':>6}{'in±1':>6}", flush=True)
    results = []
    for method, p in CONFIGS:
        tp5 = tp3 = npred = 0
        bins = {b[2]: [0, 0] for b in BINS}; cat_hit = defaultdict(lambda: [0, 0]); errs = []
        for name, boxes, mask, edge in cases:
            pb = instance_boxes(mask, edge, method, p)
            h5, h3 = match(boxes, pb, 0.5), match(boxes, pb, 0.3)
            tp5 += int(h5.sum()); tp3 += int(h3.sum()); npred += len(pb); errs.append(len(pb) - len(boxes))
            for gi, (x1, y1, x2, y2) in enumerate(boxes):
                side = ((x2 - x1) * (y2 - y1)) ** 0.5
                for lo, hi, bn in BINS:
                    if lo <= side < hi:
                        bins[bn][0] += 1; bins[bn][1] += int(h5[gi])
                c = cats[name][gi]; cat_hit[c][0] += 1; cat_hit[c][1] += int(h5[gi])
        e = np.array(errs, float)
        label = method + (" " + ",".join(f"{k}={v}" for k, v in p.items()) if p else "")
        r = dict(method=label, recall5=tp5 / total, recall3=tp3 / total, precision5=tp5 / max(npred, 1),
                 bins={k: v[1] / v[0] for k, v in bins.items()}, merged=cat_hit["merged blob"][1] / cat_hit["merged blob"][0],
                 own=cat_hit["own blob"][1] / cat_hit["own blob"][0], count_mae=float(np.abs(e).mean()), count_bias=float(e.mean()),
                 within1=float((np.abs(e) <= 1).mean()), n_pred=npred)
        results.append(r)
        print(f"{label:24}{r['recall5']:10.2f}{r['recall3']:7.2f}{r['precision5']:9.2f}" + "".join(f"{r['bins'][n]:10.2f}" for _, _, n in BINS) +
              f"{r['merged']:8.2f}{r['count_mae']:6.2f}{r['count_bias']:6.2f}{r['within1']:6.2f}", flush=True)
    Path("results").mkdir(exist_ok=True)
    Path("results/blob_split.json").write_text(json.dumps({"n_gt": total, "results": results}, indent=1))


if __name__ == "__main__":
    main()
