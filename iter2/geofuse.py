#!/usr/bin/env python3
"""Position-preserving multi-camera fusion on the payloads (Iteration 2, experiment; CPU only).

Uses only what the coordinator receives (the segmentation maps) plus each camera's pose, which in
this dataset comes from the CARLA manifest (a real deployment would have to supply a calibration):
  1. every camera: connected components of the vehicle (car, truck, bus) and person (person, rider)
     classes in its segmentation map; the foot point of a blob is the bottom centre of its box
  2. foot point -> ground plane z = 0 through the camera pose (geom.py)
  3. data association: cameras in order (Rec1 first); each camera's blobs are matched to the existing
     objects by Hungarian matching on ground distance (gate R); unmatched blobs open new objects, and an
     object takes at most one blob per camera
  4. count in Rec1's frame:
       F0  Rec1's own blobs                                      (no fusion: the baseline)
       F2  F0 + objects without a Rec1 blob that project inside Rec1's image
       F3  F0 + such objects that at least two cameras agree on
Output per case: objects with class, world position (x, y metres), pixel position in the Rec1 frame,
the cameras that saw them. Counts are compared with the manifest ground truth of the Rec1 camera.

Usage: python geofuse.py --out results/geofuse [--min-area 10] [--gate 2.5]
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment

import geom

PAL = np.array([(128, 64, 128), (244, 35, 232), (70, 70, 70), (102, 102, 156), (190, 153, 153), (153, 153, 153), (250, 170, 30),
                (220, 220, 0), (107, 142, 35), (152, 251, 152), (70, 130, 180), (220, 20, 60), (255, 0, 0), (0, 0, 142), (0, 0, 70),
                (0, 60, 100), (0, 80, 100), (0, 0, 230), (119, 11, 32)], dtype=np.int64)
KEY = (PAL[:, 0] << 16) | (PAL[:, 1] << 8) | PAL[:, 2]
GROUPS = {"vehicle": {13: "car", 14: "truck", 15: "bus"}, "person": {11: "person", 12: "person"}}
from paths import CARLA_V2  # noqa: E402

MANIFEST = CARLA_V2 / "manifest.json"
PAYLOADS = Path("data/carla_v2_payloads")


def blobs(seg_rgb, ids, min_area):
    a = np.asarray(seg_rgb).astype(np.int64)
    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    mask = np.isin(key, [KEY[t] for t in ids]).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < min_area:
            continue
        votes = {t: int((key[lab == i] == KEY[t]).sum()) for t in ids}
        out.append({"bbox": (int(x), int(y), int(w), int(h)), "area": int(area), "class": ids[max(votes, key=votes.get)],
                    "foot": (x + w / 2, y + h), "edge_cut": bool(y + h >= geom.H_IMG - 1)})
    return out


def group_mask(seg_rgb, ids):
    a = np.asarray(seg_rgb).astype(np.int64)
    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    return np.isin(key, [KEY[t] for t in ids]).astype(np.uint8)


def associate(per_cam, gate):
    """per_cam: list (Rec1 first) of lists of blobs with 'xy'. Returns objects: {'members': [(cam, blob)], 'xy': centroid}."""
    objs = []
    for ci, bl in enumerate(per_cam):
        pts = [b for b in bl if b.get("xy") is not None]
        if not pts:
            continue
        matched = set()
        if objs:
            cost = np.array([[np.hypot(*(b["xy"] - o["xy"])) for o in objs] for b in pts])
            r, c = linear_sum_assignment(cost)
            for i, j in zip(r, c):
                if cost[i, j] <= gate:
                    objs[j]["members"].append((ci, pts[i]))
                    objs[j]["xy"] = np.mean([m[1]["xy"] for m in objs[j]["members"]], axis=0)
                    matched.add(i)
        for i, b in enumerate(pts):
            if i not in matched:
                objs.append({"members": [(ci, b)], "xy": b["xy"]})
    return objs


def stats(err):
    e = np.array(err, float)
    return {"mae": float(np.abs(e).mean()), "bias": float(e.mean()), "within1": float((np.abs(e) <= 1).mean())}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--min-area", type=int, default=10)
    ap.add_argument("--gate", type=float, default=2.5, help="vehicles; people use gate/2.5")
    ap.add_argument("--cases", default="1-112")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--payloads", type=Path, default=PAYLOADS)
    args = ap.parse_args()
    a, _, b = args.cases.partition("-")
    want = set(range(int(a), int(b or a) + 1))
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text())
    res = {g: {k: [] for k in ("F0", "F2", "F3", "F4", "F5")} for g in GROUPS}
    spreads = {g: [] for g in GROUPS}
    for case in manifest["cases"]:
        if case["case"] not in want:
            continue
        cams = case["cameras"]
        segs = [Image.open(args.payloads / case["folder"] / f"{Path(c['file']).stem}_seg.webp").convert("RGB") for c in cams]
        out_case = {"case": case["folder"], "reference": Path(cams[0]["file"]).stem, "objects": {}}
        for g, ids in GROUPS.items():
            gate = args.gate if g == "vehicle" else args.gate / 2.5
            per_cam = []
            for cam, seg in zip(cams, segs):
                bl = blobs(seg, ids, args.min_area)
                for blb in bl:
                    gp = geom.ground_point(cam, *blb["foot"])
                    blb["xy"] = None if gp is None else gp[:2]
                per_cam.append(bl)
            objs = associate(per_cam, gate)
            ref_cam = cams[0]
            f0 = len(per_cam[0])
            extra, extra2, extra4, extra5 = 0, 0, 0, 0
            ref_mask = cv2.dilate(group_mask(segs[0], ids), np.ones((5, 5), np.uint8))
            listing = []
            for o in objs:
                has_ref = any(ci == 0 for ci, _ in o["members"])
                px = geom.project(ref_cam, (o["xy"][0], o["xy"][1], 0.0))
                in_ref = bool(px and 0 <= px[0] < geom.W_IMG and 0 <= px[1] < geom.H_IMG)
                in_mask = bool(in_ref and ref_mask[int(px[1]), int(px[0])] > 0)
                two = len({ci for ci, _ in o["members"]}) >= 2
                if not has_ref and in_ref:
                    extra += 1
                    extra2 += int(two)
                if not has_ref and in_mask:
                    extra4 += 1
                    extra5 += int(two)
                if len(o["members"]) >= 2:
                    pts = np.array([m[1]["xy"] for m in o["members"]])
                    spreads[g].append(float(np.linalg.norm(pts - pts.mean(0), axis=1).max()))
                votes = {}
                for _, m in o["members"]:
                    votes[m["class"]] = votes.get(m["class"], 0) + m["area"]
                listing.append({"class": max(votes, key=votes.get), "world_xy_m": [round(float(o["xy"][0]), 2), round(float(o["xy"][1]), 2)],
                                "ref_pixel_1920x1080": None if not px else [round(px[0] * 1920 / geom.W_IMG, 1), round(px[1] * 1080 / geom.H_IMG, 1)],
                                "in_ref_frame": in_ref, "seen_by": sorted({cams[ci]["file"][:-4] for ci, _ in o["members"]})})
            gt = cams[0]["counts"]["cars" if g == "vehicle" else "pedestrians"]
            for k, v in (("F0", f0), ("F2", f0 + extra), ("F3", f0 + extra2), ("F4", f0 + extra4), ("F5", f0 + extra5)):
                res[g][k].append(v - gt)
            out_case["objects"][g] = {"F0": f0, "F2": f0 + extra, "F3": f0 + extra2, "F4": f0 + extra4, "F5": f0 + extra5, "gt": gt, "list": listing}
        (args.out / f"{case['folder']}.json").write_text(json.dumps(out_case, indent=1))
    summary = {"min_area": args.min_area, "gate": args.gate, "n_cases": len(res["vehicle"]["F0"]),
               "counts_vs_gt": {g: {k: stats(v) for k, v in d.items()} for g, d in res.items()},
               "association_spread_m": {g: ({"n": len(s), "median": float(np.median(s)), "p90": float(np.percentile(s, 90))} if s else None) for g, s in spreads.items()}}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
