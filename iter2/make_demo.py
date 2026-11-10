#!/usr/bin/env python3
"""Build iter2/demo/: before/after examples for presenting the receiver (original photo -> payload -> reconstruction).

Case selection is a fixed rule, not hand-picking: cases are sorted by the default receiver's per-case vehicle recall and taken at evenly spaced
quantiles (worst to best), 10 from CARLA v3 (recall against the ground truth) and 8 from the real-world set (recall against the detector on the
original photo, as there is no ground truth). For every case:
  original_cam1.jpg            Rec1 photo at 1024x576
  payload_seg.webp, payload_edge.webp, payload_caption.txt   what Rec1 actually transmits (copied unchanged)
  recon_default.jpg            master view, default receiver (ControlNet canny 1.0 / seg 1.0)
  recon_cn07_15.jpg            master view, ControlNet canny 0.7 / seg 1.5
  panel.jpg                    the above side by side with boxes: ground truth (CARLA) or detector-on-original (real) on the photo,
                               detector boxes on the reconstructions, and the numbers
  case.json                    the numbers
plus demo/README.md with one table row and the panel for every case.
Usage: python make_demo.py
"""
import json
import shutil
from pathlib import Path

import numpy as np
import textwrap

from PIL import Image, ImageDraw, ImageFont

import paths
from gt_eval import gt_boxes, hits

OUT = Path("demo")
W, H = 1024, 576
VEH = ("car", "truck", "bus")
COL = {"gt": (0, 255, 0), "det": (255, 220, 0)}
TW, TH = 512, 288                      # panel tile size
try:
    FONT = ImageFont.truetype("arial.ttf", 13)
except OSError:
    FONT = ImageFont.load_default()
SETS = {
    "carla_v3": dict(data=paths.CARLA_V3, pay=Path("data/v3_payloads"), default=Path("results/v3"), new=Path("results/v3_cn07_15"), n=10,
                     cases=list(range(1, 113)), gt=True),
    "real_world": dict(data=paths.REAL_WORLD_CORE, pay=Path("data/rw_core_payloads"), default=Path("results/rw_core"), new=Path("results/rw_cn07_15"), n=8,
                       cases=[1 + 6 * i for i in range(61)], gt=False),
}


def det_boxes(row):
    sc = W / row["master_size"][0]
    return [[v * sc for v in d["bbox_master_px"]] for d in row["detections"] if d["class"] in VEH]


def per_case_recall(s, manifest_cases, case):
    row = json.loads((s["default"] / "analysis" / "prompt_only" / f"case{case}.json").read_text())
    ref = gt_boxes(manifest_cases[case]) if s["gt"] else det_boxes(json.loads((s["default"] / "analysis" / "oracle_gen" / f"case{case}.json").read_text()))
    return float(hits(ref, det_boxes(row), 0.5).mean()) if ref else None


def pick(values, n):
    """Indices at evenly spaced quantiles of the sorted values (worst to best), unique."""
    order = [c for c, v in sorted(values.items(), key=lambda kv: (kv[1], kv[0]))]
    idx = sorted({round(q * (len(order) - 1)) for q in np.linspace(0.03, 0.97, n)})
    return [order[i] for i in idx]


def draw(img, boxes, colour, label):
    """Tile at panel size: boxes scaled from the 1024x576 frame, label drawn at the final size so it stays readable."""
    im = img.resize((TW, TH), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    s = TW / W
    for b in boxes:
        d.rectangle([v * s for v in b], outline=colour, width=2)
    d.rectangle([0, 0, d.textlength(label, font=FONT) + 10, 18], fill="black")
    d.text((5, 2), label, fill="white", font=FONT)
    return im


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    manifest = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    mcases = {c["case"]: c for c in manifest["cases"]}
    rows_md = []
    for set_name, s in SETS.items():
        rec = {c: per_case_recall(s, mcases, c) for c in s["cases"]
               if (s["default"] / "analysis" / "prompt_only" / f"case{c}.json").exists() and (s["new"] / "analysis" / "prompt_only" / f"case{c}.json").exists()}
        rec = {c: v for c, v in rec.items() if v is not None}
        for case in pick(rec, s["n"]):
            name = f"case{case}"
            d = OUT / f"{set_name}_{name}"
            d.mkdir()
            ref_row = json.loads((s["default"] / "analysis" / "prompt_only" / f"{name}.json").read_text())
            new_row = json.loads((s["new"] / "analysis" / "prompt_only" / f"{name}.json").read_text())
            orc_row = json.loads((s["default"] / "analysis" / "oracle_gen" / f"{name}.json").read_text())
            cam = ref_row["reference"]
            src = next(p for p in (s["data"] / name).iterdir() if p.stem == cam)
            orig = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
            a = Image.open(s["default"] / "prompt_only" / f"{name}.png").convert("RGB")
            b = Image.open(s["new"] / "prompt_only" / f"{name}.png").convert("RGB")
            orig.save(d / "original_cam1.jpg", quality=90); a.save(d / "recon_default.jpg", quality=90); b.save(d / "recon_cn07_15.jpg", quality=90)
            for suffix, target in (("seg.webp", "payload_seg.webp"), ("edge.webp", "payload_edge.webp"), ("caption.txt", "payload_caption.txt")):
                shutil.copy(s["pay"] / name / f"{cam}_{suffix}", d / target)
            payload_kb = sum((s["pay"] / name / f"{cam}_{x}").stat().st_size for x in ("seg.webp", "edge.webp", "caption.txt")) / 1024
            da, db = det_boxes(ref_row), det_boxes(new_row)
            if s["gt"]:
                ref = gt_boxes(mcases[case])
                ref_label, n_ref = "ground truth", int(mcases[case]["cameras"][0]["counts"]["cars"])
                ra, rb = float(hits(ref, da, 0.5).mean()), float(hits(ref, db, 0.5).mean())
                extra = f"{mcases[case]['n_cameras']} cameras, {mcases[case]['weather']}"
            else:
                ref = [[v for v in x] for x in det_boxes(orc_row)]
                ref_label, n_ref = "detector on original", len(ref)
                ra, rb = (float(hits(ref, da, 0.5).mean()), float(hits(ref, db, 0.5).mean())) if ref else (None, None)
                extra = f"{len(list((s['pay'] / name).glob('cam*_meta.json')))} phones"
            caption = (s["pay"] / name / f"{cam}_caption.txt").read_text(encoding="utf-8").strip()
            seg = Image.open(s["pay"] / name / f"{cam}_seg.webp").convert("RGB").resize((W, H), Image.NEAREST)
            edge = Image.open(s["pay"] / name / f"{cam}_edge.webp").convert("RGB").resize((W, H), Image.BILINEAR)
            tiles = [draw(orig, ref, COL["gt"], f"original Rec1 + {ref_label}: {len(ref)} vehicles"),
                     draw(seg, [], None, "payload: segmentation map (1024x576)"),
                     draw(edge, [], None, "payload: edge map (full resolution)"),
                     draw(a, da, COL["det"], f"default receiver: {len(da)} detected, recall {ra:.2f}" if ra is not None else "default receiver"),
                     draw(b, db, COL["det"], f"canny 0.7 / seg 1.5: {len(db)} detected, recall {rb:.2f}" if rb is not None else "canny 0.7 / seg 1.5")]
            info = Image.new("RGB", (TW, TH), "white")
            di = ImageDraw.Draw(info)
            lines = [f"{set_name} {name} ({extra})", f"Rec1 caption: {caption}", f"payload of Rec1: {payload_kb:.1f} KB "
                     f"(photo {src.stat().st_size / 1024:.0f} KB)", f"vehicles ({ref_label}): {len(ref)}",
                     f"default receiver: {len(da)} detected, recall {ra:.2f}" if ra is not None else "", f"canny 0.7 / seg 1.5: {len(db)} detected, recall {rb:.2f}" if rb is not None else "",
                     "recall = share of reference vehicles matched by a detection at IoU >= 0.5", "green = reference boxes, yellow = detections"]
            y = 12
            for t in (l for l in lines if l):
                for part in textwrap.wrap(t, 72):
                    di.text((12, y), part, fill="black", font=FONT)
                    y += 18
                y += 4
            tiles.append(info)
            panel = Image.new("RGB", (3 * TW, 2 * TH), "white")
            for i, t in enumerate(tiles):
                panel.paste(t, ((i % 3) * TW, (i // 3) * TH))
            panel.save(d / "panel.jpg", quality=85)
            info_json = {"set": set_name, "case": name, "reference_camera": cam, "reference": ref_label, "n_reference_vehicles": len(ref),
                         "detected_default": len(da), "detected_cn07_15": len(db), "recall_default": ra, "recall_cn07_15": rb, "payload_kb": payload_kb,
                         "photo_kb": src.stat().st_size / 1024, "caption": caption, "details": extra}
            (d / "case.json").write_text(json.dumps(info_json, indent=1))
            rows_md.append((set_name, name, extra, ref_label, len(ref), len(da), len(db), ra, rb))
            print(set_name, name, f"ref {len(ref)}, default {len(da)} ({ra:.2f}), new {len(db)} ({rb:.2f})", flush=True)
    md = ["# Before / after examples\n",
          "Cases were chosen by a fixed rule, not by eye: sorted by the default receiver's per-case vehicle recall and taken at evenly spaced quantiles, "
          "so the set runs from the worst to the best cases. CARLA v3 recall is against the ground truth (vehicles visible from Rec1 with >= 80 px at 960x540); "
          "real-world recall is against the detector on the original photo, as those photos have no ground truth. A vehicle counts as recovered when a detection "
          "on the reconstruction overlaps it with IoU >= 0.5.\n",
          "Each folder holds the original Rec1 photo, the three payload files Rec1 transmits, both reconstructions and `case.json`.\n",
          "| set | case | details | reference | vehicles | detected (default) | detected (canny 0.7 / seg 1.5) | recall (default) | recall (canny 0.7 / seg 1.5) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for set_name, name, extra, ref_label, n_ref, nda, ndb, ra, rb in rows_md:
        md.append(f"| {set_name} | [{name}]({set_name}_{name}/) | {extra} | {ref_label} | {n_ref} | {nda} | {ndb} | {ra:.2f} | {rb:.2f} |")
    md.append("")
    for set_name, name, *_ in rows_md:
        md.append(f"### {set_name} {name}\n\n![{set_name} {name}]({set_name}_{name}/panel.jpg)\n")
    (OUT / "README.md").write_text("\n".join(md), encoding="utf-8")
    print("wrote demo/README.md with", len(rows_md), "cases")


if __name__ == "__main__":
    main()
