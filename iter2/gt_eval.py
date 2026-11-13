#!/usr/bin/env python3
"""Ground-truth evaluation of master-view runs on CARLA v3 (instance ids), Rec1 (cam1) only.

For every run given (an `analysis/<variant>` folder written by analysis.py): detections of vehicles (car, truck, bus) are matched to the
ground-truth vehicles (visible >= 80 px at 960x540, box scaled to the 1024x576 frame) by Hungarian matching at IoU >= 0.5 and 0.3.
Reported: pooled recall (also by box size), precision (matched detections / detections), cars MAE against the ground-truth count, seconds
per image, and the paired change in per-case recall against the first run (95% bootstrap CI over cases).

Usage:
  python gt_eval.py --cases 1-24 --out results/gt_eval.json \
      default=results/v3/analysis/prompt_only  big=results/v3_2048/analysis/prompt_only
(the first `label=folder` is the baseline). Detections are mapped to the 1024x576 frame through the master_size stored in every file.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

import paths
from analysis import box_iou, paired_boot

S = 1024 / 960
VEH = ("car", "truck", "bus")
BINS = [(0, 24, "<24 px"), (24, 48, "24-48 px"), (48, 120, "48-120 px"), (120, 1e9, ">120 px")]


def gt_boxes(case):
    out = []
    for g in case["cameras"][0]["instances"]:
        if g["kind"] == "car" and g["counts_in_gt"]:
            x1, y1, x2, y2 = g["bbox_px"]
            out.append((x1 * S, y1 * S, (x2 + 1) * S, (y2 + 1) * S))
    return out


def hits(gt, det, thr):
    h = np.zeros(len(gt), bool)
    if gt and det:
        iou = box_iou(np.array(gt, float), np.array(det, float))
        r, c = linear_sum_assignment(-iou)
        for i, j in zip(r, c):
            h[i] = iou[i, j] >= thr
    return h


def parse_cases(text):
    want = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        want.update(range(int(a), int(b or a) + 1))
    return want


def evaluate(folder, manifest, want):
    """-> dict with per-case recall list and pooled statistics for one analysis folder."""
    res = {"case": [], "recall5": [], "tp5": 0, "tp3": 0, "n_gt": 0, "n_det": 0, "bins": {b[2]: [0, 0] for b in BINS}, "err": [], "sec": []}
    for case in manifest["cases"]:
        if case["case"] not in want:
            continue
        f = Path(folder) / f"{case['folder']}.json"
        if not f.exists():
            continue
        row = json.loads(f.read_text())
        gt = gt_boxes(case)
        sx, sy = 1024 / row["master_size"][0], 576 / row["master_size"][1]
        det = [[d["bbox_master_px"][0] * sx, d["bbox_master_px"][1] * sy, d["bbox_master_px"][2] * sx, d["bbox_master_px"][3] * sy]
               for d in row["detections"] if d["class"] in VEH]
        h5, h3 = hits(gt, det, 0.5), hits(gt, det, 0.3)
        res["case"].append(case["folder"])
        res["recall5"].append(float(h5.mean()) if gt else None)
        res["tp5"] += int(h5.sum()); res["tp3"] += int(h3.sum()); res["n_gt"] += len(gt); res["n_det"] += len(det)
        for gi, (x1, y1, x2, y2) in enumerate(gt):
            side = ((x2 - x1) * (y2 - y1)) ** 0.5
            for lo, hi, name in BINS:
                if lo <= side < hi:
                    res["bins"][name][0] += 1; res["bins"][name][1] += int(h5[gi])
        res["err"].append(abs(row["counts"]["cars_4wheel"] - case["cameras"][0]["counts"]["cars"]))
        if row.get("seconds") is not None:
            res["sec"].append(row["seconds"])
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", nargs="+", help="label=analysis/<variant> folder; the first is the baseline")
    ap.add_argument("--cases", default="1-112")
    ap.add_argument("--manifest", type=Path, default=paths.CARLA_V3 / "manifest.json")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text())
    want = parse_cases(args.cases)
    runs = [(r.split("=", 1)[0], r.split("=", 1)[1]) for r in args.runs]
    results = {label: evaluate(folder, manifest, want) for label, folder in runs}
    base_label = runs[0][0]
    base = results[base_label]
    print(f"{'run':18}{'cases':>6}{'n GT':>6}{'rec@.5':>8}{'rec@.3':>8}" + "".join(f"{b[2]:>10}" for b in BINS) + f"{'prec@.5':>9}{'carsMAE':>9}{'s/img':>7}   paired d-recall vs {base_label}")
    summary = {}
    for label, r in results.items():
        n = r["n_gt"]
        pair = ""
        if label != base_label:
            common = [(a, b) for c, a, b in zip(base["case"], base["recall5"], r["recall5"]) if a is not None and b is not None and c in r["case"]]
            idx = {c: v for c, v in zip(r["case"], r["recall5"])}
            common = [(a, idx[c]) for c, a in zip(base["case"], base["recall5"]) if a is not None and idx.get(c) is not None]
            p = paired_boot([a for a, _ in common], [b for _, b in common]) if len(common) > 1 else None
            if p:
                lo, hi = p["ci95"]
                pair = f"{p['mean_diff']:+.3f} [{lo:+.3f}, {hi:+.3f}] n={p['n']}" + ("  (CI above 0)" if lo > 0 else "  (CI below 0)" if hi < 0 else "")
        line = (f"{label:18}{len(r['case']):6}{n:6}{r['tp5'] / n:8.3f}{r['tp3'] / n:8.3f}" +
                "".join(f"{r['bins'][b[2]][1] / max(r['bins'][b[2]][0], 1):10.2f}" for b in BINS) +
                f"{r['tp5'] / max(r['n_det'], 1):9.2f}{np.mean(r['err']):9.2f}{(np.mean(r['sec']) if r['sec'] else float('nan')):7.1f}   {pair}")
        print(line)
        summary[label] = {"cases": len(r["case"]), "n_gt": n, "recall5": r["tp5"] / n, "recall3": r["tp3"] / n, "precision5": r["tp5"] / max(r["n_det"], 1),
                          "bins": {k: v[1] / max(v[0], 1) for k, v in r["bins"].items()}, "cars_mae": float(np.mean(r["err"])),
                          "seconds": float(np.mean(r["sec"])) if r["sec"] else None, "paired": pair}
    if args.out:
        args.out.write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
