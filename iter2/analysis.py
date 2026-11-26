#!/usr/bin/env python3
"""Analysis module (Iteration 2): vehicle counts, classes and positions of a master view.

Runs the same detector on
  * every reconstruction (master views of each coordinator variant), and
  * the ORIGINAL photo of the reference camera, as the detector's own ceiling
    (`oracle_gen`: original resized to the master-view size; `oracle_full`: native 1920x1080),
so a reconstruction is never judged harder than the detector itself.

Detector: torchvision COCO Faster R-CNN v2, score >= 0.5, as in Iteration 1 (palette_eval.py).
Classes kept: car, truck, bus, motorcycle, bicycle, person.

Per case and variant it writes <out>/analysis/<variant>/caseK.json:
  counts per class, vehicle totals, and every detection with its class, score and position
  (pixel box and centre in the master view and in the reference camera's original frame).
Plus <out>/analysis/detections.csv, <out>/analysis/counts.csv and <out>/analysis/summary.json.
When the dataset has a CARLA manifest, counts are compared with its ground truth
(cars = cars+trucks+buses, two-wheelers, pedestrians visible from the reference camera,
>= 80 px at 960x540), and detections with the oracle's by Hungarian matching at IoU >= 0.5.

Usage
  python analysis.py --out results/carla_v2 --dataset C:/carla_multicam_kit/output/carla_dataset_v2_low2m_3to6cams_hd \
      --payloads data/carla_v2_payloads --variants k1,prompt_only,ipa_recon
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCORE_MIN, MATCH_IOU = 0.5, 0.5
CLASSES = {1: "person", 2: "bicycle", 3: "car", 4: "motorcycle", 6: "bus", 8: "truck"}
FOUR_WHEEL, TWO_WHEEL = ("car", "truck", "bus"), ("motorcycle", "bicycle")
COLOURS = {"car": (0, 200, 255), "truck": (255, 140, 0), "bus": (255, 215, 0), "motorcycle": (180, 80, 255),
           "bicycle": (80, 255, 120), "person": (255, 60, 60)}


class Detector:
    def __init__(self, device="cuda"):
        from torchvision.models.detection import FasterRCNN_ResNet50_FPN_V2_Weights, fasterrcnn_resnet50_fpn_v2
        weights = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
        self.model = fasterrcnn_resnet50_fpn_v2(weights=weights).to(device).eval()
        self.tf, self.device = weights.transforms(), device
        self.name = f"torchvision fasterrcnn_resnet50_fpn_v2, {weights.name}"

    def __call__(self, img):
        import torch
        with torch.no_grad():
            out = self.model([self.tf(img).to(self.device)])[0]
        boxes, labels, scores = (out[k].cpu().numpy() for k in ("boxes", "labels", "scores"))
        keep = (scores >= SCORE_MIN) & np.isin(labels, list(CLASSES))
        order = np.argsort(-scores[keep])
        return [{"class": CLASSES[int(l)], "score": float(s), "xyxy": [float(v) for v in b]}
                for b, l, s in zip(boxes[keep][order], labels[keep][order], scores[keep][order])]


def counts_of(dets):
    c = {n: 0 for n in CLASSES.values()}
    for d in dets:
        c[d["class"]] += 1
    c["cars_4wheel"] = sum(c[n] for n in FOUR_WHEEL)
    c["two_wheelers"] = sum(c[n] for n in TWO_WHEEL)
    c["vehicles"] = c["cars_4wheel"] + c["motorcycle"]          # Iteration 1 definition: car, bus, truck, motorcycle
    c["pedestrians"] = c["person"]
    return c


def box_iou(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter)


def n_matched(ref_boxes, rec_boxes):
    from scipy.optimize import linear_sum_assignment
    iou = box_iou(np.array(ref_boxes).reshape(-1, 4), np.array(rec_boxes).reshape(-1, 4))
    if iou.size == 0:
        return 0
    r, c = linear_sum_assignment(-iou)
    return int((iou[r, c] >= MATCH_IOU).sum())


def boxes_of(dets, names):
    return [d["xyxy"] for d in dets if d["class"] in names]


def describe(dets, sx, sy):
    """Detections with pixel positions in the master view and in the reference camera's original frame."""
    out = []
    for i, d in enumerate(dets):
        x1, y1, x2, y2 = d["xyxy"]
        out.append({"id": i, "class": d["class"], "score": round(d["score"], 3),
                    "bbox_master_px": [round(v, 1) for v in (x1, y1, x2, y2)],
                    "center_master_px": [round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                    "ground_contact_master_px": [round((x1 + x2) / 2, 1), round(y2, 1)],
                    "bbox_reference_px": [round(x1 * sx, 1), round(y1 * sy, 1), round(x2 * sx, 1), round(y2 * sy, 1)],
                    "center_reference_px": [round((x1 + x2) / 2 * sx, 1), round((y1 + y2) / 2 * sy, 1)]})
    return out


def overlay(img, dets, path):
    im = img.copy().convert("RGB")
    d = ImageDraw.Draw(im)
    for det in dets:
        x1, y1, x2, y2 = det["xyxy"]
        col = COLOURS[det["class"]]
        d.rectangle([x1, y1, x2, y2], outline=col, width=2)
        d.text((x1 + 2, max(0, y1 - 11)), f"{det['class']} {det['score']:.2f}", fill=col)
    im.save(path, quality=90)


def gt_from_manifest(dataset):
    mf = dataset / "manifest.json"
    if not mf.exists():
        return {}
    gt = {}
    for c in json.loads(mf.read_text())["cases"]:
        for cam in c["cameras"]:
            k = cam["counts"]
            gt[(c["folder"], Path(cam["file"]).stem)] = {"cars_4wheel": k["cars"], "pedestrians": k["pedestrians"],
                                                         "two_wheelers": k.get("two_wheelers", 0)}
    return gt


def find_original(dataset, case, cam):
    for ext in (".jpg", ".jpeg", ".png"):
        p = dataset / case / f"{cam}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"{case}/{cam}")


def reference_cam(out, case):
    """Reference camera recorded by the coordinator (any non-k1 variant), cam1 otherwise."""
    for d in sorted(out.iterdir()):
        if d.is_dir() and d.name not in ("k1", "analysis"):
            f = d / f"{case}.json"
            if f.exists():
                return json.loads(f.read_text())["reference"]
    return "cam1"


def variant_image(out, variant, case, cam):
    if variant == "k1":
        return out / "k1" / f"{case}_{cam}.png"
    return out / variant / f"{case}.png"


# ---------------------------------------------------------------- statistics
def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.fmean(vals) if vals else None


def pearson(x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def paired_boot(a, b, n_boot=2000):
    """Mean of (b - a) over cases with a 95% bootstrap interval; a, b aligned lists."""
    d = np.array([y - x for x, y in zip(a, b) if x is not None and y is not None], float)
    if len(d) < 2:
        return None
    rng = np.random.default_rng(0)
    boot = rng.choice(d, size=(n_boot, len(d))).mean(axis=1)
    return {"n": int(len(d)), "mean_diff": float(d.mean()), "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}


def summarise(rows):
    s = {"n_cases": len(rows)}
    for key in ("cars_4wheel", "pedestrians", "two_wheelers"):
        det = [r["counts"][key] for r in rows]
        s[f"mean_{key}"] = mean(det)
        gt = [r["gt"][key] for r in rows if r.get("gt")]
        if len(gt) == len(rows) and gt:
            err = [d - g for d, g in zip(det, gt)]
            s[f"gt_mean_{key}"] = mean(gt)
            s[f"{key}_mae_vs_gt"] = mean([abs(e) for e in err])
            s[f"{key}_bias_vs_gt"] = mean(err)
            s[f"{key}_exact_vs_gt"] = mean([e == 0 for e in err])
            s[f"{key}_within1_vs_gt"] = mean([abs(e) <= 1 for e in err])
            s[f"{key}_pearson_vs_gt"] = pearson(det, gt)
    for key in ("vehicle_recall", "vehicle_precision", "person_recall", "person_precision", "vehicle_count_abs_err_vs_oracle",
                "person_count_abs_err_vs_oracle", "seconds"):
        s[key] = mean([r.get(key) for r in rows])
    return s


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path, help="coordinator output root")
    ap.add_argument("--dataset", required=True, type=Path, help="dataset with the original photos (and manifest.json for CARLA)")
    ap.add_argument("--payloads", type=Path, default=None, help="payload dir, for payload size statistics")
    ap.add_argument("--variants", default="k1,prompt_only,ipa_seg")
    ap.add_argument("--cases", default="", help="e.g. 1-20 (default: every case with a master view)")
    ap.add_argument("--no-overlays", action="store_true")
    ap.add_argument("--analysis-dir", type=Path, default=None, help="write the analysis here instead of <out>/analysis")
    args = ap.parse_args()
    if sys.platform == "win32":      # keep the laptop awake during long runs
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

    det = Detector()
    gt_all = gt_from_manifest(args.dataset)
    ana = args.analysis_dir or args.out / "analysis"
    ana.mkdir(parents=True, exist_ok=True)
    variants = args.variants.split(",")
    probe = variants[0]
    cases = sorted({p.stem.split("_")[0] if probe == "k1" else p.stem
                    for p in (args.out / probe).glob("case*.png")}, key=lambda c: int(c[4:]))
    if args.cases:
        want = set()
        for part in args.cases.split(","):
            a, _, b = part.partition("-")
            want.update(range(int(a), int(b or a) + 1))
        cases = [c for c in cases if int(c[4:]) in want]
    print(f"{len(cases)} cases, variants {variants}, detector {det.name}", flush=True)

    rows = {v: [] for v in ["oracle_full", "oracle_gen"] + variants}
    det_csv = []
    for ci, case in enumerate(cases, 1):
        cam = reference_cam(args.out, case)
        orig = Image.open(find_original(args.dataset, case, cam)).convert("RGB")
        gt = gt_all.get((case, cam))
        per_case = {}
        # detector ceiling on the original
        d_full = det(orig)
        results = {"oracle_full": (d_full, orig, orig.size)}
        for v in variants:
            f = variant_image(args.out, v, case, cam)
            if not f.exists():
                continue
            img = Image.open(f).convert("RGB")
            if "oracle_gen" not in results:
                results["oracle_gen"] = (det(orig.resize(img.size, Image.LANCZOS)), orig.resize(img.size, Image.LANCZOS), img.size)
            results[v] = (det(img), img, img.size)
        oracle = results.get("oracle_gen", (d_full, orig, orig.size))[0]
        for v, (dets, img, size) in results.items():
            sx, sy = orig.width / size[0], orig.height / size[1]
            c = counts_of(dets)
            row = {"case": case, "reference": cam, "variant": v, "master_size": list(size), "counts": c, "gt": gt,
                   "detections": describe(dets, sx, sy)}
            if v not in ("oracle_full", "oracle_gen"):
                ref_veh, rec_veh = boxes_of(oracle, FOUR_WHEEL + ("motorcycle",)), boxes_of(dets, FOUR_WHEEL + ("motorcycle",))
                ref_per, rec_per = boxes_of(oracle, ("person",)), boxes_of(dets, ("person",))
                mv, mp = n_matched(ref_veh, rec_veh), n_matched(ref_per, rec_per)
                row.update(vehicle_recall=mv / len(ref_veh) if ref_veh else None,
                           vehicle_precision=mv / len(rec_veh) if rec_veh else None,
                           person_recall=mp / len(ref_per) if ref_per else None,
                           person_precision=mp / len(rec_per) if rec_per else None,
                           vehicle_count_abs_err_vs_oracle=abs(len(rec_veh) - len(ref_veh)),
                           person_count_abs_err_vs_oracle=abs(len(rec_per) - len(ref_per)))
                sidecar = args.out / v / (f"{case}_{cam}.json" if v == "k1" else f"{case}.json")
                if sidecar.exists():
                    meta = json.loads(sidecar.read_text())
                    row["seconds"], row["prompt"] = meta["seconds"], meta["prompt"]
            rows[v].append(row)
            vdir = ana / v
            vdir.mkdir(exist_ok=True)
            (vdir / f"{case}.json").write_text(json.dumps(row, indent=1))
            if not args.no_overlays:
                overlay(img, dets, vdir / f"{case}_det.jpg")
            for d in row["detections"]:
                det_csv.append({"case": case, "variant": v, "reference": cam, "id": d["id"], "class": d["class"], "score": d["score"],
                                "x1": d["bbox_master_px"][0], "y1": d["bbox_master_px"][1], "x2": d["bbox_master_px"][2], "y2": d["bbox_master_px"][3],
                                "cx": d["center_master_px"][0], "cy": d["center_master_px"][1],
                                "ref_cx": d["center_reference_px"][0], "ref_cy": d["center_reference_px"][1]})
        print(f"[{ci}/{len(cases)}] {case}: " + ", ".join(
            f"{v} {rows[v][-1]['counts']['cars_4wheel']}c/{rows[v][-1]['counts']['pedestrians']}p" for v in rows if rows[v]) +
            (f" | GT {gt['cars_4wheel']}c/{gt['pedestrians']}p" if gt else ""), flush=True)

    with open(ana / "detections.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(det_csv[0].keys()) if det_csv else ["case"])
        w.writeheader(); w.writerows(det_csv)
    with open(ana / "counts.csv", "w", newline="") as f:
        cols = ["case", "variant", "reference", "car", "truck", "bus", "motorcycle", "bicycle", "person", "cars_4wheel", "vehicles",
                "two_wheelers", "pedestrians", "gt_cars", "gt_pedestrians", "gt_two_wheelers"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for v, rs in rows.items():
            for r in rs:
                c, g = r["counts"], r["gt"] or {}
                w.writerow({"case": r["case"], "variant": v, "reference": r["reference"], **{k: c[k] for k in cols[3:13]},
                            "gt_cars": g.get("cars_4wheel"), "gt_pedestrians": g.get("pedestrians"), "gt_two_wheelers": g.get("two_wheelers")})

    summary = {"detector": det.name, "score_min": SCORE_MIN, "match_iou": MATCH_IOU,
               "variants": {v: summarise(rs) for v, rs in rows.items() if rs}, "paired_abs_error_vs_gt": {}}
    base = "k1" if rows.get("k1") else None
    if base and gt_all:
        for v in variants:
            if v == base or not rows[v]:
                continue
            for key in ("cars_4wheel", "pedestrians"):
                a = [abs(r["counts"][key] - r["gt"][key]) for r in rows[base]]
                b = [abs(r["counts"][key] - r["gt"][key]) for r in rows[v]]
                if len(a) == len(b):
                    summary["paired_abs_error_vs_gt"][f"{v}_minus_{base}_{key}"] = paired_boot(a, b)
    if args.payloads and (args.payloads / "payload_index.json").exists():
        idx = json.loads((args.payloads / "payload_index.json").read_text())
        tot = [v["total_b"] for v in idx.values()]
        summary["payload_per_camera_kb_mean"] = statistics.fmean(tot) / 1024
        summary["original_photo_kb_mean"] = statistics.fmean(v["file_b"] for v in idx.values()) / 1024
    (ana / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1), flush=True)
    print("ANALYSIS_DONE", flush=True)


if __name__ == "__main__":
    main()
