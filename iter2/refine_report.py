#!/usr/bin/env python3
"""Compile iter2/REFINE_REPORT.md: `prompt_refine` vs `prompt_only` on the 20 selected small-car images.

Recall and precision are against the detector on the original photo (`oracle_gen`), Hungarian matching at IoU >= 0.5 over the
vehicle classes (car, truck, bus, motorcycle), pooled over the cases of a dataset; bins are by the side length of the oracle box
in the master view (as in sizebins.py). The cases were chosen because they contain many small cars.

Usage (after coordinator.py --variants prompt_refine and analysis.py --analysis-dir ... have run):
    python refine_report.py
"""
import json
import statistics
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment

import paths
from analysis import FOUR_WHEEL, box_iou, find_original, paired_boot

VEH = FOUR_WHEEL + ("motorcycle",)
MATCH_IOU = 0.5
BINS = [(0, 24, "<24 px"), (24, 48, "24-48 px"), (48, 120, "48-120 px"), (120, 1e9, ">120 px")]
SMALL_MAX = 48
DATASETS = {
    "CARLA v3": dict(run=Path("results/v3"), ana=Path("results/refine/analysis_v3"), data=paths.CARLA_V3, has_gt=True,
                     cases=[112, 106, 69, 91, 88, 42, 52, 59, 89, 101]),
    "Real-world": dict(run=Path("results/rw_core"), ana=Path("results/refine/analysis_rw"), data=paths.REAL_WORLD_CORE, has_gt=False,
                       cases=[25, 7, 19, 1, 13, 235, 241, 217, 223, 277]),
}
VARIANTS = ("prompt_only", "prompt_refine")
FIG_DIR = Path("refine_figures")


def side(b):
    return ((b[2] - b[0]) * (b[3] - b[1])) ** 0.5


def vboxes(row):
    return [d["bbox_master_px"] for d in row["detections"] if d["class"] in VEH]


def match_flags(ob, vb):
    """Hungarian match of oracle boxes to variant boxes; returns a hit flag per oracle box and the number of matched pairs."""
    hit = np.zeros(len(ob), bool)
    if ob and vb:
        iou = box_iou(np.array(ob, float), np.array(vb, float))
        r, c = linear_sum_assignment(-iou)
        for i, j in zip(r, c):
            if iou[i, j] >= MATCH_IOU:
                hit[i] = True
    return hit


def load(ds, variant, case):
    return json.loads((ds["ana"] / variant / f"case{case}.json").read_text())


def collect(ds):
    """Per variant: pooled bin counts, per-case recall, precision, MAE, seconds."""
    out = {v: {"bins": {b[2]: [0, 0] for b in BINS}, "matched": 0, "pred": 0, "oracle": 0, "recall_case": [], "small_case": [],
               "err": [], "sec": []} for v in VARIANTS}
    for case in ds["cases"]:
        orc = load(ds, "oracle_gen", case)
        ob = vboxes(orc)
        for v in VARIANTS:
            row = load(ds, v, case)
            vb = vboxes(row)
            hit = match_flags(ob, vb)
            o = out[v]
            for i, b in enumerate(ob):
                for lo, hi, name in BINS:
                    if lo <= side(b) < hi:
                        o["bins"][name][0] += 1
                        o["bins"][name][1] += int(hit[i])
            o["matched"] += int(hit.sum()); o["pred"] += len(vb); o["oracle"] += len(ob)
            o["recall_case"].append(hit.mean() if len(ob) else None)
            small = [i for i, b in enumerate(ob) if side(b) < SMALL_MAX]
            o["small_case"].append(float(hit[small].mean()) if small else None)
            if ds["has_gt"] and row.get("gt"):
                o["err"].append(abs(row["counts"]["cars_4wheel"] - row["gt"]["cars_4wheel"]))
            o["sec"].append(row.get("seconds"))
    return out


def rate(h, n):
    return f"{h / n:.2f}" if n else "-"


def paired(a, b):
    """Mean of (b - a) over the cases where both exist, with the 95% bootstrap CI from analysis.paired_boot."""
    return paired_boot(a, b)


def fmt_pair(p):
    if p is None:
        return "n/a"
    lo, hi = p["ci95"]
    verdict = "CI crosses zero" if lo <= 0 <= hi else ("CI above zero" if lo > 0 else "CI below zero")
    return f"{p['mean_diff']:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}; n={p['n']}; {verdict})"


def refine_meta(ds):
    metas = [json.loads((ds["run"] / "prompt_refine" / f"case{c}.json").read_text()) for c in ds["cases"]]
    return metas


def figure(name, ds, metas):
    """original | prompt_only | prompt_refine for the first case that had a refined window, plus 4x zoom of its first window."""
    for case, meta in zip(ds["cases"], metas):
        wins = [w for w in meta["refine"]["windows"] if "error" not in w]
        if wins:
            break
    else:
        return None, None
    ref = meta["reference"]
    size = tuple(meta["size"])
    orig = Image.open(find_original(ds["data"], f"case{case}", ref)).convert("RGB").resize(size, Image.LANCZOS)
    a = Image.open(ds["run"] / "prompt_only" / f"case{case}.png").convert("RGB")
    b = Image.open(ds["run"] / "prompt_refine" / f"case{case}.png").convert("RGB")
    W, H = 768, 432
    w0 = wins[0]
    box = (w0["x0"], w0["y0"], w0["x0"] + 128, w0["y0"] + 128)
    Z = 512
    sheet = Image.new("RGB", (3 * W, H + Z + 40), "white")
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate((("original photo", orig), ("prompt_only", a), ("prompt_refine", b))):
        sheet.paste(im.resize((W, H), Image.LANCZOS), (i * W, 0))
        d.rectangle([i * W, 0, i * W + 170, 16], fill="black"); d.text((i * W + 4, 3), f"{name} case{case}: {label}", fill="white")
        x = i * W + (W - Z) // 2
        sheet.paste(im.crop(box).resize((Z, Z), Image.BICUBIC), (x, H + 30))
        d.text((x, H + 12), f"{label}: window at ({box[0]},{box[1]}), 128 px shown 4x", fill="black")
        s = W / size[0]                        # mark the window on the top row
        d.rectangle([i * W + box[0] * s, box[1] * s, i * W + box[2] * s, box[3] * s], outline=(255, 255, 0), width=1)
    FIG_DIR.mkdir(exist_ok=True)
    path = FIG_DIR / f"refine_{name.lower().replace(' ', '_').replace('-', '_')}.jpg"
    sheet.save(path, quality=90)
    return path, case


def main():
    lines = ["# prompt_refine: redrawing small cars at 4x\n",
             "`prompt_refine` takes the `prompt_only` master view, finds the small vehicles in Rec1's received segmentation map "
             "(blob area >= 12 px, box side <= 48 px), groups them into at most 8 windows of 128x128 px, redraws each window "
             "4x upscaled with Stable Diffusion 1.5 + the same two ControlNets in img2img mode (strength 0.5, 20 steps, guidance 7.5, "
             "seed 42 + window index, fixed prompt \"cars on a city street, realistic photo, sharp\"), downscales it and pastes it back with a feathered mask.\n",
             "**The 20 images were chosen because they contain many small cars, which favours the method.** "
             "10 CARLA v3 cases (112, 106, 69, 91, 88, 42, 52, 59, 89, 101) and 10 real-world cases (25, 7, 19, 1, 13, 235, 241, 217, 223, 277). "
             "They are not a random sample, so the numbers say what the method can do where it should help, not what it does on average.\n"]
    results, metas_all = {}, {}
    for name, ds in DATASETS.items():
        results[name] = collect(ds)
        metas_all[name] = refine_meta(ds)

    lines += ["## Results\n",
              "Recall and precision are against the detector on the original photo (`oracle_gen`), Hungarian matching at IoU >= 0.5, pooled over the 10 cases of each dataset. "
              "Bins are by the side length of the oracle box in the 1024x576 master view. Cars MAE is against the manifest ground truth (cars, trucks, buses visible from Rec1); real-world has no ground truth. "
              "s/img is generation time for the whole master view (for `prompt_refine`: `prompt_only` time plus refinement).\n",
              "| dataset | variant | vehicle recall <24 px | 24-48 px | 48-120 px | >120 px | vehicle recall all | vehicle precision | cars MAE vs GT | s/img |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for name, res in results.items():
        for v in VARIANTS:
            o = res[v]
            mae = f"{statistics.fmean(o['err']):.2f}" if o["err"] else "-"
            sec = statistics.fmean(s for s in o["sec"] if s is not None)
            cells = [rate(o["bins"][b[2]][1], o["bins"][b[2]][0]) for b in BINS]
            lines.append(f"| {name} | {v} | " + " | ".join(cells) + f" | {rate(o['matched'], o['oracle'])} | {rate(o['matched'], o['pred'])} | {mae} | {sec:.1f} |")
    lines.append("")
    for name, res in results.items():
        n = {b[2]: res['prompt_only']['bins'][b[2]][0] for b in BINS}
        lines.append(f"- {name}: oracle vehicles per bin " + ", ".join(f"{k} n={v}" for k, v in n.items()) + f"; {res['prompt_only']['oracle']} in total, "
                     f"`prompt_only` returns {res['prompt_only']['pred']} vehicle boxes, `prompt_refine` {res['prompt_refine']['pred']}.")
    lines.append("")

    lines += ["## Paired change, `prompt_refine` minus `prompt_only` (per-case recall, 95% bootstrap CI over cases)\n",
              "| subset | all vehicles | vehicles < 48 px |", "|---|---|---|"]
    pool_all, pool_small = ([], []), ([], [])
    for name, res in results.items():
        a, b = res["prompt_only"], res["prompt_refine"]
        pa = [(x, y) for x, y in zip(a["recall_case"], b["recall_case"]) if x is not None and y is not None]
        ps = [(x, y) for x, y in zip(a["small_case"], b["small_case"]) if x is not None and y is not None]
        for x, y in pa: pool_all[0].append(x); pool_all[1].append(y)
        for x, y in ps: pool_small[0].append(x); pool_small[1].append(y)
        lines.append(f"| {name} | {fmt_pair(paired([x for x, _ in pa], [y for _, y in pa]))} | {fmt_pair(paired([x for x, _ in ps], [y for _, y in ps]))} |")
    lines.append(f"| both datasets | {fmt_pair(paired(*pool_all))} | {fmt_pair(paired(*pool_small))} |\n")
    lines.append("Per-case recall is matched oracle vehicles over oracle vehicles in the case (cases without oracle vehicles in the subset are dropped). "
                 "With 10 cases per dataset the intervals are wide.\n")

    lines += ["## What the refinement did\n", "| dataset | cases | small blobs found (per case) | windows (per case) | blobs not covered by the 8 windows | window failures | refinement s/img |", "|---|---|---|---|---|---|---|"]
    for name, metas in metas_all.items():
        r = [m["refine"] for m in metas]
        lines.append(f"| {name} | {len(r)} | {statistics.fmean(x['n_small_blobs'] for x in r):.1f} | {statistics.fmean(x['n_windows'] for x in r):.1f} | "
                     f"{sum(x['uncovered_blobs'] for x in r)} | {sum(len(x['failures']) for x in r)} | {statistics.fmean(m['refine_seconds'] for m in metas):.1f} |")
    fails = [(n, m["case"], f) for n, ms_ in metas_all.items() for m in ms_ for f in m["refine"]["failures"]]
    lines.append("")
    lines.append("Window failures: " + ("none." if not fails else "; ".join(f"{n} {c}: {f}" for n, c, f in fails)))
    lines.append("")

    lines.append("## Side by side\n")
    for name, ds in DATASETS.items():
        path, case = figure(name, ds, metas_all[name])
        lines.append(f"- {name}, case {case} (the first case in the list with a refined window; not picked for its effect): `{path}`" if path else f"- {name}: no refined window to show.")
    lines.append("\nTop row: original photo, `prompt_only`, `prompt_refine` at 1024x576 with the first window outlined in yellow; bottom row: that 128x128 window shown 4x.\n")
    concl = Path("refine_conclusion.md")
    lines.append("## Conclusion\n\n" + (concl.read_text(encoding="utf-8-sig").strip() if concl.exists() else "<!--CONCLUSION-->") + "\n")
    Path("REFINE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote REFINE_REPORT.md,", len(lines), "lines")


if __name__ == "__main__":
    main()
