#!/usr/bin/env python3
"""Damir's scenario (23 Nov): cars parked along the sides of the street, the rear (distant) ones poorly visible.
Finds such cases in both datasets, compares baseline (single-camera MMSD) and fusion on them, and makes example sheets with
zoomed crops of the distant area. Usage: python parked_rows.py <out_dir>
"""
import csv
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from scipy.stats import binom

import paths

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
DS = {"v3": (paths.CARLA_V3, ".jpg", "results/v3/analysis/oracle_full", range(1, 113), "CARLA v3"),
      "rw": (paths.REAL_WORLD_CORE, ".png", "results/rw_core/analysis/oracle_full", [1 + 6 * k for k in range(61)], "Real-world")}
PARKED = re.compile(r"\bpark(ed|ing)?\b", re.I)
DISTANT = re.compile(r"\b(distance|distant|far|farther|further|background|behind|partially|obscured|occluded|hidden|barely|blurr?y|small)\b", re.I)
VEH = {"car", "bus", "truck"}
try:
    F, FB, FS = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 24), ImageFont.truetype("arial.ttf", 16)
except OSError:
    F = FB = FS = ImageFont.load_default()


def judge(run):
    out = {}
    for line in open(f"results/vlm/{run}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
            out[r["case"]] = r
    return out


def ok(r):
    return r["numbers"]["score"] * r["positions"]["score"]


def vehicles(root, c):
    f = Path(root) / f"case{c}.json"
    if not f.exists():
        return [], (1920, 1080)
    d = json.loads(f.read_text())
    return [x["bbox_reference_px"] for x in d["detections"] if x["class"] in VEH and x.get("score", 1) >= 0.5], (1920, 1080)


def mcnemar(a, b, cases):
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))


def distant_crop(boxes, W=1920, H=1080):
    """Region around the small (distant) vehicles, widened to 16:9."""
    small = [b for b in boxes if (b[3] - b[1]) < 0.06 * H]
    if not small:
        return None
    x1, y1 = min(b[0] for b in small), min(b[1] for b in small)
    x2, y2 = max(b[2] for b in small), max(b[3] for b in small)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    w = max(x2 - x1 + 120, 480); h = w * 9 / 16
    if h < (y2 - y1) + 80:
        h = (y2 - y1) + 80; w = h * 16 / 9
    w, h = min(w, W), min(h, H)
    x1, y1 = min(max(0, cx - w / 2), W - w), min(max(0, cy - h / 2), H - h)
    return (x1 / W, y1 / H, (x1 + w) / W, (y1 + h) / H)


def crop_rel(im, rel):
    W, H = im.size
    return im.crop((int(rel[0] * W), int(rel[1] * H), int(rel[2] * W), int(rel[3] * H)))


def sheet(ds, c, S, Fz, rel, out):
    root, ext, _, _, name = DS[ds]
    imgs = [Image.open(root / f"case{c}" / f"cam1{ext}").convert("RGB"), Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png").convert("RGB"),
            Image.open(f"results/{ds}_fuse/fuse/case{c}.png").convert("RGB")]
    labs = [("Original (main camera)", None), ("Baseline: single-camera MMSD", S), ("Ours: multi-camera fusion", Fz)]
    W, H, P = 640, 360, 12
    sh = Image.new("RGB", (3 * W + 4 * P, 56 + 2 * (H + 70) + 110), "white"); d = ImageDraw.Draw(sh)
    d.text((P, 14), f"{name} case {c}: cars parked along the street, distant cars hard to see", fill="black", font=FB)
    for i, (im, (lab, r)) in enumerate(zip(imgs, labs)):
        x = P + i * (W + P)
        sh.paste(im.resize((W, H), Image.LANCZOS), (x, 56))
        d.text((x, 56 + H + 6), lab, fill="black", font=F)
        if r is not None:
            d.text((x, 56 + H + 34), f"count {'OK' if r['numbers']['score'] else 'WRONG'}, positions {'OK' if r['positions']['score'] else 'WRONG'}",
                   fill=(0, 120, 0) if ok(r) else (190, 0, 0), font=F)
        if rel:
            cr = crop_rel(im, rel).resize((W, H), Image.LANCZOS)
            y = 56 + H + 70
            sh.paste(cr, (x, y)); d.text((x, y + H + 6), "zoom: distant parked cars", fill="black", font=FS)
            if i == 0:
                bx = [rel[0] * W, rel[1] * H, rel[2] * W, rel[3] * H]
                ImageDraw.Draw(sh).rectangle([x + bx[0], 56 + bx[1], x + bx[2], 56 + bx[3]], outline=(255, 200, 0), width=3)
    y = 56 + 2 * (H + 70) + 4
    for who, r in (("Judge on the baseline: ", S), ("Judge on the fusion: ", Fz)):
        d.text((P, y), (who + " ".join(r["numbers"]["text"].split()))[:230], fill="black", font=FS); y += 24
    sh.save(out / f"{'carla' if ds == 'v3' else 'real_world'}_case{c:03d}_parked_rows.jpg", quality=88)


def main():
    rows, summary = [], []
    for ds in ("v3", "rw"):
        root, ext, oracle, cases, name = DS[ds]
        S, Fz = judge(f"{ds}_paper_k1"), judge(f"{ds}_fuse")
        cat = []
        for c in cases:
            if c not in S or c not in Fz:
                continue
            text = S[c]["numbers"]["text"] + " " + S[c]["positions"]["text"]
            boxes, _ = vehicles(oracle, c)
            n_small = sum(1 for b in boxes if (b[3] - b[1]) < 0.06 * 1080)
            if PARKED.search(text) and DISTANT.search(text) and len(boxes) >= 4 and n_small >= 2:
                cat.append(c)
                rows.append({"dataset": name, "case": c, "vehicles_detected": len(boxes), "small_distant_vehicles": n_small,
                             "baseline_joint": ok(S[c]), "fusion_joint": ok(Fz[c])})
        a = {c: ok(Fz[c]) for c in cat}; b = {c: ok(S[c]) for c in cat}
        w, l, p = mcnemar(a, b, cat)
        summary.append((name, len(cat), sum(b.values()), sum(a.values()), w, l, p))
        for c in cat:
            if ok(Fz[c]) and not ok(S[c]):
                sheet(ds, c, S[c], Fz[c], distant_crop(vehicles(oracle, c)[0]), OUT)
    with open(OUT / "parked_rows_cases.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    lines = ["Damir's scenario: cars parked along the sides of the street, the distant ones hard to see.",
             "Selection (automatic, no hand-picking): the judge's description of the original mentions parked cars AND distant/partly hidden/small ones,",
             "and the detector finds at least 4 vehicles on the original, at least 2 of them small (< 6% of the image height).", ""]
    for name, n, sb, sf, w, l, p in summary:
        lines.append(f"{name}: {n} such cases. Baseline passes {sb} ({100*sb/max(n,1):.0f}%), fusion passes {sf} ({100*sf/max(n,1):.0f}%); "
                     f"fusion better in {w}, worse in {l} (McNemar p = {p:.3f}).")
    lines += ["", "Images: every such case where the fusion passes and the baseline fails, with zoomed crops of the distant parked cars.",
              "Caveat: the judge sometimes counts the same original differently in two requests, so single cases can partly reflect judge noise."]
    (OUT / "README.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
