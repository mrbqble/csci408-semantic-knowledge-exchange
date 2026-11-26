#!/usr/bin/env python3
"""Palette evaluation at scale: the authors' receiver vs ADE20K colours (Iteration 1).

Rebuilds a spread of Cityscapes val images two ways (receiver settings as in
receiver_smoke_test.py, i.e. the seed authors' settings):

  A_cs_full   Cityscapes-palette segmentation map + edges (the authors' receiver)
  B_ade_full  the same map recoloured to ADE20K (palette_test.py) + edges

and scores every reconstruction against its original image:
  * semantic fidelity: Mask2Former labels vs those of the original (pixel accuracy,
    mIoU over classes present in the original, per-class IoU), as in palette_test.py;
  * vehicles: torchvision's COCO Faster R-CNN (v2) detections of cars, motorcycles,
    buses and trucks with score >= 0.5 in original and reconstruction; count error,
    and position matches (IoU >= 0.5, Hungarian matching) as recall and precision;
    people are counted separately;
  * colourfulness (Hasler and Suesstrunk, 2003).
The summary adds paired B - A differences with 95% bootstrap intervals.

Long runs are resumable: reconstructions already on disk are not regenerated. On
Windows the script keeps the machine awake while it runs.

Usage
  python palette_eval.py --components data/components_m2f --originals data/cityscapes_val \
      --step 5 --limit 100 --out results/iteration1_palette_eval_100.json --save-dir results/palette100
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

import mmsd_sender as ms
import palette_test as pt
import receiver_smoke_test as rx

VARIANTS = {"A_cs_full": ("cs", [1.0, 1.0]), "B_ade_full": ("ade", [1.0, 1.0])}
VEHICLE_LABELS = (3, 4, 6, 8)        # torchvision COCO ids: car, motorcycle, bus, truck
PERSON_LABEL = 1
SCORE_MIN, MATCH_IOU = 0.5, 0.5
PAIRED = ["pixel_acc", "miou", "iou_road", "iou_sidewalk", "iou_building", "iou_vegetation", "iou_sky",
          "iou_person", "iou_car", "count_abs_err", "recall", "precision", "people_abs_err", "colourfulness"]


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def keep_awake():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED


def box_iou(a, b):
    """Pairwise IoU of xyxy boxes, (n, 4) x (m, 4) -> (n, m)."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter)


def matched(ref_boxes, rec_boxes, thr=MATCH_IOU):
    """Number of one-to-one box matches with IoU >= thr (Hungarian matching on IoU)."""
    from scipy.optimize import linear_sum_assignment
    iou = box_iou(ref_boxes, rec_boxes)
    if iou.size == 0:
        return 0
    r, c = linear_sum_assignment(-iou)
    return int((iou[r, c] >= thr).sum())


def vehicle_metrics(ref, rec):
    (rb, rp), (cb, cp) = ref, rec
    m = matched(rb, cb)
    return {"n_vehicles_original": len(rb), "n_vehicles_recon": len(cb), "count_abs_err": abs(len(cb) - len(rb)),
            "count_exact": len(cb) == len(rb), "count_within1": abs(len(cb) - len(rb)) <= 1, "matched": m,
            "recall": m / len(rb) if len(rb) else None, "precision": m / len(cb) if len(cb) else None,
            "n_people_original": rp, "n_people_recon": cp, "people_abs_err": abs(cp - rp)}


class Detector:
    def __init__(self, device):
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
        keep = scores >= SCORE_MIN
        return boxes[keep & np.isin(labels, VEHICLE_LABELS)], int((keep & (labels == PERSON_LABEL)).sum())


def mean_of(rows, v, k):
    vals = [float(r[v][k]) for r in rows if r[v].get(k) is not None]
    return statistics.fmean(vals) if vals else None


def paired_diff(rows, k, a="A_cs_full", b="B_ade_full", n_boot=2000):
    d = np.array([r[b][k] - r[a][k] for r in rows if r[a].get(k) is not None and r[b].get(k) is not None], float)
    if len(d) == 0:
        return None
    rng = np.random.default_rng(0)
    boot = rng.choice(d, size=(n_boot, len(d))).mean(axis=1)
    return {"n": int(len(d)), "mean_b_minus_a": float(d.mean()), "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "share_b_higher": float((d > 0).mean()), "share_equal": float((d == 0).mean())}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--components", required=True, type=Path)
    ap.add_argument("--originals", required=True, type=Path)
    ap.add_argument("--step", type=int, default=5, help="take every n-th image of the sorted set")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--save-dir", required=True, type=Path)
    ap.add_argument("--eval-only", action="store_true", help="score reconstructions already on disk")
    args = ap.parse_args()

    import torch
    keep_awake()
    stems = sorted(p.name[: -len("_seg.webp")] for p in args.components.glob("*_seg.webp"))[:: args.step][: args.limit]
    for v in VARIANTS:
        (args.save_dir / v).mkdir(parents=True, exist_ok=True)
    todo = [(v, s) for s in stems for v in VARIANTS if not (args.save_dir / v / f"{s}.png").exists()]
    log(f"{len(stems)} images; {len(todo)} reconstructions to generate")

    gen_seconds, sd_id = {v: [] for v in VARIANTS}, None
    if todo and not args.eval_only:
        pipe, sd_id = rx.load_pipeline(offload=False)
        for k, (v, stem) in enumerate(todo, 1):
            palette, scales = VARIANTS[v]
            seg, edge, caption = rx.load_components(args.components, stem)
            if palette == "ade":
                seg = pt.cs_rgb_to_ade_rgb(seg)
            torch.cuda.synchronize(); t = time.perf_counter()
            img = pipe(prompt=caption, image=[edge, seg], num_inference_steps=rx.STEPS, guidance_scale=rx.GUIDANCE,
                       height=rx.TARGET_SIZE[1], width=rx.TARGET_SIZE[0], controlnet_conditioning_scale=scales,
                       generator=torch.Generator(device="cuda").manual_seed(rx.SEED)).images[0]
            torch.cuda.synchronize(); gen_seconds[v].append(time.perf_counter() - t)
            img.save(args.save_dir / v / f"{stem}.png")
            log(f"[{k}/{len(todo)}] {v} {stem}: {gen_seconds[v][-1]:.1f} s")
        del pipe
        torch.cuda.empty_cache()
    missing = [(v, s) for s in stems for v in VARIANTS if not (args.save_dir / v / f"{s}.png").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} reconstructions missing, e.g. {missing[:3]}")

    log("evaluating")
    seg_model, det = ms.Segmenter("cuda"), Detector("cuda")
    rows = []
    for i, stem in enumerate(stems, 1):
        orig = Image.open(args.originals / f"{stem}.png").convert("RGB")
        ref_labels, ref_det = seg_model(orig), det(orig)
        row = {"stem": stem, "colourfulness_original": pt.colourfulness(orig)}
        for v in VARIANTS:
            rec = Image.open(args.save_dir / v / f"{stem}.png").convert("RGB")
            if rec.size != orig.size:
                rec = rec.resize(orig.size, Image.LANCZOS)
            row[v] = {**pt.fidelity(ref_labels, seg_model(rec)), **vehicle_metrics(ref_det, det(rec)),
                      "colourfulness": pt.colourfulness(rec)}
        rows.append(row)
        if i % 10 == 0 or i == len(stems):
            log(f"evaluated {i}/{len(stems)}")

    metrics = ["pixel_acc", "miou", *[f"iou_{n}" for n in pt.KEY_CLASSES], "count_abs_err", "count_exact", "count_within1",
               "recall", "precision", "people_abs_err", "colourfulness"]
    summary = {}
    for v in VARIANTS:
        summary[v] = {k: mean_of(rows, v, k) for k in metrics}
        summary[v]["recall_pooled"] = sum(r[v]["matched"] for r in rows) / max(1, sum(r[v]["n_vehicles_original"] for r in rows))
        summary[v]["precision_pooled"] = sum(r[v]["matched"] for r in rows) / max(1, sum(r[v]["n_vehicles_recon"] for r in rows))
    summary["original"] = {"colourfulness": statistics.fmean(r["colourfulness_original"] for r in rows),
                           "vehicles_per_image": statistics.fmean(r["A_cs_full"]["n_vehicles_original"] for r in rows)}
    result = {"config": {"n": len(stems), "step": args.step, "sd_model": sd_id, "variants": {v: f"{p} palette, controlnet scales {s} (edge, seg)" for v, (p, s) in VARIANTS.items()},
                         "receiver": "authors' settings (see receiver_smoke_test.py)", "detector": det.name,
                         "vehicle_labels_coco": VEHICLE_LABELS, "score_min": SCORE_MIN, "match_iou": MATCH_IOU,
                         "semantic_reference": "Mask2Former labels of the original image"},
              "generation_seconds_mean": {v: (statistics.fmean(s) if s else None) for v, s in gen_seconds.items()},
              "summary": summary, "paired_b_minus_a": {k: paired_diff(rows, k) for k in PAIRED}, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    for v in VARIANTS:
        s = summary[v]
        log(f"{v}: mIoU {s['miou']:.3f}, sky {s['iou_sky']}, vehicle count MAE {s['count_abs_err']:.2f}, "
            f"recall {s['recall_pooled']:.3f}, precision {s['precision_pooled']:.3f}")
    log(f"DONE; wrote {args.out}")


if __name__ == "__main__":
    main()
