#!/usr/bin/env python3
"""Scene-level evaluation on the v3 dataset (visible-object ids and world positions in the manifest).

Two references per case:
  GT_rec1   objects visible from Rec1 (cam1), >= 80 px at 960x540 (the manifest counts, now with ids)
  GT_union  objects visible from at least one camera of the case (the occlusion-free scene)
Kinds: vehicles (cars, trucks, buses) and pedestrians. A GT object's position is its bounding-box centre (x, y, metres,
CARLA world frame); parked static-mesh cars have no actor, so their position is backprojected from the render's depth.

Methods (positions are ground-plane x, y in metres):
  generative (oracle_gen = detector on the original photo, k1, prompt_only): detections in Rec1's master view; the
      ground-contact point (bottom centre of the box) is projected through Rec1's pose
  geofuse F0  Rec1's own blobs in its received segmentation map
  geofuse F3  F0 + objects Rec1 lacks that >= 2 cameras agree on and that project into Rec1's frame
  geofuse scene_all   every associated object of every camera
  geofuse scene_min2  objects confirmed by >= 2 cameras
Matching: Hungarian on ground distance within a gate. Reported per method and reference: count MAE and bias
(per case), pooled recall and precision, and the median position error of the matches.

Usage: python eval_union.py --manifest M --geofuse DIR --analysis DIR --variants oracle_gen,k1,prompt_only --out file.json
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

import geom

VEH_CLASSES = ("car", "truck", "bus")


def gt_objects(case):
    """kind -> {id: {'xy': (x, y), 'cams': set(camera index)}} for objects counted in GT (>= 80 px) by any camera."""
    out = {"vehicle": {}, "pedestrian": {}}
    best = {}
    for ci, cam in enumerate(case["cameras"]):
        for inst in cam["instances"]:
            kind = {"car": "vehicle", "pedestrian": "pedestrian"}.get(inst["kind"])
            if kind is None or not inst["counts_in_gt"]:
                continue
            d = out[kind].setdefault(inst["id"], {"xy": None, "cams": set()})
            d["cams"].add(ci)
            w = inst.get("world")
            if w and np.isfinite(w["x"]) and np.isfinite(w["y"]):       # a few actors report NaN transforms: use depth instead
                d["xy"] = (w["x"], w["y"])
            elif d["xy"] is None or inst["visible_px"] > best.get(inst["id"], 0):
                if inst["visible_px"] > best.get(inst["id"], 0):       # fallback: depth backprojection from the best view
                    p = geom.depth_point(cam, inst["centroid_px"][0], inst["centroid_px"][1], inst["depth_m"])
                    d["xy"] = (float(p[0]), float(p[1])); d["fallback"] = True
                    best[inst["id"]] = inst["visible_px"]
    return out


def match(pred_xy, gt_xy, gate):
    """pred_xy may contain None (no ground position). Returns matched distances."""
    idx = [i for i, p in enumerate(pred_xy) if p is not None]
    if not idx or not gt_xy:
        return []
    P = np.array([pred_xy[i] for i in idx]); G = np.array(gt_xy)
    cost = np.hypot(P[:, None, 0] - G[None, :, 0], P[:, None, 1] - G[None, :, 1])
    r, c = linear_sum_assignment(cost)
    return [float(cost[i, j]) for i, j in zip(r, c) if cost[i, j] <= gate]


class Acc:
    def __init__(self):
        self.err, self.tp, self.npred, self.ngt, self.dist = [], 0, 0, 0, []

    def add(self, pred_xy, gt_xy, gate):
        d = match(pred_xy, gt_xy, gate)
        self.err.append(len(pred_xy) - len(gt_xy)); self.tp += len(d); self.npred += len(pred_xy); self.ngt += len(gt_xy); self.dist += d

    def summary(self):
        e = np.array(self.err, float)
        return {"n_cases": len(e), "count_mae": float(np.abs(e).mean()), "count_bias": float(e.mean()),
                "recall": self.tp / self.ngt if self.ngt else None, "precision": self.tp / self.npred if self.npred else None,
                "median_pos_err_m": float(np.median(self.dist)) if self.dist else None, "mean_gt": self.ngt / len(e), "mean_pred": self.npred / len(e)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--geofuse", required=True, type=Path)
    ap.add_argument("--analysis", required=True, type=Path, help="<coordinator out>/analysis")
    ap.add_argument("--variants", default="oracle_gen,k1,prompt_only")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--gate-veh", type=float, default=3.0)
    ap.add_argument("--gate-ped", type=float, default=2.0)
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text())
    variants = args.variants.split(",")
    acc = defaultdict(Acc)
    ref_sizes = defaultdict(list)
    for case in manifest["cases"]:
        name = case["folder"]
        gf = args.geofuse / f"{name}.json"
        if not gf.exists():
            continue
        g = json.loads(gf.read_text())
        gt = gt_objects(case)
        cam1 = case["cameras"][0]
        for kind, gate, grp, classes in (("vehicle", args.gate_veh, "vehicle", VEH_CLASSES), ("pedestrian", args.gate_ped, "person", ("person",))):
            rec1_ids = [i for i, d in gt[kind].items() if 0 in d["cams"]]
            gt_rec1 = [gt[kind][i]["xy"] for i in rec1_ids]
            gt_union = [d["xy"] for d in gt[kind].values()]
            ref_sizes[kind].append((len(gt_rec1), len(gt_union)))
            preds = {}
            for v in variants:
                f = args.analysis / v / f"{name}.json"
                if f.exists():
                    row = json.loads(f.read_text()); sx = geom.W_IMG / row["master_size"][0]; sy = geom.H_IMG / row["master_size"][1]
                    xy = []
                    for d in row["detections"]:
                        if d["class"] in classes:
                            gp = geom.ground_point(cam1, d["ground_contact_master_px"][0] * sx, d["ground_contact_master_px"][1] * sy)
                            xy.append(None if gp is None else (float(gp[0]), float(gp[1])))
                    preds[v] = xy
            objs = g["objects"][grp]["list"]
            xy_of = lambda o: tuple(o["world_xy_m"])
            f0 = [o for o in objs if "cam1" in o["seen_by"]]
            preds["geofuse_F0"] = [xy_of(o) for o in f0]
            preds["geofuse_F3"] = [xy_of(o) for o in f0] + [xy_of(o) for o in objs if "cam1" not in o["seen_by"] and o["in_ref_frame"] and len(o["seen_by"]) >= 2]
            preds["geofuse_scene_all"] = [xy_of(o) for o in objs]
            preds["geofuse_scene_min2"] = [xy_of(o) for o in objs if len(o["seen_by"]) >= 2]
            for m, xy in preds.items():
                acc[(kind, m, "rec1")].add(xy, gt_rec1, gate)
                acc[(kind, m, "union")].add(xy, gt_union, gate)
    result = {"gates_m": {"vehicle": args.gate_veh, "pedestrian": args.gate_ped},
              "mean_gt_per_case": {k: {"rec1": float(np.mean([a for a, _ in v])), "union": float(np.mean([b for _, b in v])),
                                        "hidden_from_rec1": float(np.mean([b - a for a, b in v]))} for k, v in ref_sizes.items()},
              "results": {f"{k}|{m}|vs_{r}": a.summary() for (k, m, r), a in sorted(acc.items())}}
    args.out.write_text(json.dumps(result, indent=1))
    print("mean GT objects per case:", json.dumps(result["mean_gt_per_case"]))
    print(f"{'kind':11}{'method':20}{'ref':7}{'MAE':>6}{'bias':>7}{'recall':>8}{'prec':>7}{'pos err m':>11}")
    for key, s in result["results"].items():
        k, m, r = key.split("|")
        if s["recall"] is None:
            continue
        print(f"{k:11}{m:20}{r[3:]:7}{s['count_mae']:6.2f}{s['count_bias']:7.2f}{s['recall']:8.2f}{(s['precision'] or 0):7.2f}{(s['median_pos_err_m'] or float('nan')):11.2f}")


if __name__ == "__main__":
    main()
