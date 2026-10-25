#!/usr/bin/env python3
"""Palette test: does the segmentation ControlNet need ADE20K colours? (Iteration 1)

The seed authors colour the segmentation map with the Cityscapes palette, but
lllyasviel/sd-controlnet-seg was trained on ADE20K-palette images, and no
class colour matches. This script rebuilds the same images four ways:

  A  Cityscapes palette, edges + segmentation   (the authors' receiver; from receiver_smoke_test.py)
  B  ADE20K palette,     edges + segmentation
  C  Cityscapes palette, segmentation only       (edge ControlNet scale 0, = the paper's no-edge ablation)
  D  ADE20K palette,     segmentation only

and scores each reconstruction against the original image:
  * semantic fidelity: Mask2Former labels of the reconstruction vs those of the
    original (pixel accuracy, mIoU over classes present in the original, and
    IoU for road, sidewalk, building, vegetation, sky, person, car);
  * colourfulness (Hasler and Suesstrunk, 2003) of original and reconstruction.

Receiver settings as in receiver_smoke_test.py (authors' settings). ADE20K
colours come from the ADE20K palette used for ControlNet's segmentation
annotator (wall 120,120,120; building 180,120,120; sky 6,230,230; ...), checked
against the palette in the sd-controlnet-seg model card. ADE20K has no train
class, so Cityscapes "train" maps to bus.

Usage
  python palette_test.py --components data/components_m2f --originals data/cityscapes_val \
      --baseline results/receiver_smoke --limit 5 --out results/iteration1_palette_test.json \
      --save-dir results/palette_test
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
from PIL import Image

import mmsd_sender as ms
import receiver_smoke_test as rx

# Cityscapes trainId -> ADE20K class colour
CS_TO_ADE = {
    0: (140, 140, 140),   # road -> road
    1: (235, 255, 7),     # sidewalk -> sidewalk
    2: (180, 120, 120),   # building -> building
    3: (120, 120, 120),   # wall -> wall
    4: (255, 184, 6),     # fence -> fence
    5: (51, 0, 255),      # pole -> pole
    6: (41, 0, 255),      # traffic light -> traffic light
    7: (255, 5, 153),     # traffic sign -> signboard
    8: (4, 200, 3),       # vegetation -> tree
    9: (4, 250, 7),       # terrain -> grass
    10: (6, 230, 230),    # sky -> sky
    11: (150, 5, 61),     # person -> person
    12: (150, 5, 61),     # rider -> person
    13: (0, 102, 200),    # car -> car
    14: (255, 0, 20),     # truck -> truck
    15: (255, 0, 245),    # bus -> bus
    16: (255, 0, 245),    # train -> bus (no train class in ADE20K)
    17: (163, 0, 255),    # motorcycle -> minibike
    18: (255, 245, 0),    # bicycle -> bicycle
}
KEY_CLASSES = {"road": 0, "sidewalk": 1, "building": 2, "vegetation": 8, "sky": 10, "person": 11, "car": 13}
VARIANTS = {"B_ade_full": ("ade", [1.0, 1.0]), "C_cs_segonly": ("cs", [0.0, 1.0]), "D_ade_segonly": ("ade", [0.0, 1.0])}


def cs_rgb_to_ade_rgb(seg_rgb):
    """Cityscapes-palette RGB map -> ADE20K-palette RGB map (unknown colours, e.g. black, kept)."""
    arr = np.asarray(seg_rgb.convert("RGB"))
    key = (arr[..., 0].astype(np.int32) << 16) | (arr[..., 1].astype(np.int32) << 8) | arr[..., 2]
    out = arr.copy()
    for tid, cs in enumerate(ms.CITYSCAPES_PALETTE):
        mask = key == ((int(cs[0]) << 16) | (int(cs[1]) << 8) | int(cs[2]))
        out[mask] = CS_TO_ADE[tid]
    return Image.fromarray(out, "RGB")


def colourfulness(img):
    a = np.asarray(img.convert("RGB")).astype(np.float64)
    rg = a[..., 0] - a[..., 1]
    yb = 0.5 * (a[..., 0] + a[..., 1]) - a[..., 2]
    return float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()))


def fidelity(ref, rec):
    out = {"pixel_acc": float((ref == rec).mean())}
    ious = {}
    for c in np.unique(ref):
        if c > 18:
            continue
        inter = np.logical_and(ref == c, rec == c).sum()
        union = np.logical_or(ref == c, rec == c).sum()
        ious[int(c)] = float(inter / union)
    out["miou"] = float(np.mean(list(ious.values())))
    for name, c in KEY_CLASSES.items():
        out[f"iou_{name}"] = ious.get(c)          # None when the class is absent from the original
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--components", required=True, type=Path)
    ap.add_argument("--originals", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path, help="folder with variant A images from receiver_smoke_test.py")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--save-dir", required=True, type=Path)
    args = ap.parse_args()

    import torch
    stems = sorted(p.name[: -len("_seg.webp")] for p in args.components.glob("*_seg.webp"))[: args.limit]
    for v in VARIANTS:
        (args.save_dir / v).mkdir(parents=True, exist_ok=True)

    # ---- generation (B, C, D); A comes from the baseline folder
    pipe, sd_id = rx.load_pipeline(offload=False)
    gen_seconds = {v: [] for v in VARIANTS}
    for v, (palette, scales) in VARIANTS.items():
        for stem in stems:
            seg, edge, caption = rx.load_components(args.components, stem)
            if palette == "ade":
                seg = cs_rgb_to_ade_rgb(seg)
            torch.cuda.synchronize(); t = time.perf_counter()
            img = pipe(prompt=caption, image=[edge, seg], num_inference_steps=rx.STEPS, guidance_scale=rx.GUIDANCE,
                       height=rx.TARGET_SIZE[1], width=rx.TARGET_SIZE[0], controlnet_conditioning_scale=scales,
                       generator=torch.Generator(device="cuda").manual_seed(rx.SEED)).images[0]
            torch.cuda.synchronize(); gen_seconds[v].append(time.perf_counter() - t)
            img.save(args.save_dir / v / f"{stem}.png")
            print(f"{v} {stem}: {gen_seconds[v][-1]:.1f} s", flush=True)
    del pipe
    torch.cuda.empty_cache()

    # ---- evaluation
    seg_model = ms.Segmenter("cuda")
    folders = {"A_cs_full": args.baseline, **{v: args.save_dir / v for v in VARIANTS}}
    rows = []
    for stem in stems:
        orig = Image.open(args.originals / f"{stem}.png").convert("RGB")
        ref = seg_model(orig)
        row = {"stem": stem, "colourfulness_original": colourfulness(orig)}
        for v, folder in folders.items():
            path = folder / (f"{stem}_blip_reconstructed.png" if v == "A_cs_full" else f"{stem}.png")
            rec_img = Image.open(path).convert("RGB")
            if rec_img.size != orig.size:
                rec_img = rec_img.resize(orig.size, Image.LANCZOS)
            row[v] = {**fidelity(ref, seg_model(rec_img)), "colourfulness": colourfulness(rec_img)}
        rows.append(row)
        print(f"{stem}: " + ", ".join(f"{v} mIoU {row[v]['miou']:.3f}" for v in folders), flush=True)

    def mean_of(v, k):
        vals = [r[v][k] for r in rows if r[v][k] is not None]
        return statistics.fmean(vals) if vals else None

    metrics = ["pixel_acc", "miou", *[f"iou_{n}" for n in KEY_CLASSES], "colourfulness"]
    summary = {v: {k: mean_of(v, k) for k in metrics} for v in folders}
    summary["original"] = {"colourfulness": statistics.fmean(r["colourfulness_original"] for r in rows)}
    result = {"config": {"n": len(stems), "sd_model": sd_id, "receiver": "authors' settings (see receiver_smoke_test.py)",
                         "variants": {"A_cs_full": "Cityscapes palette, edges + segmentation",
                                      **{v: f"{p} palette, controlnet scales {s} (edge, seg)" for v, (p, s) in VARIANTS.items()}},
                         "reference": "Mask2Former labels of the original image", "cs_to_ade": CS_TO_ADE},
              "generation_seconds_mean": {v: statistics.fmean(s) for v, s in gen_seconds.items()},
              "summary": summary, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))

    # ---- contact sheet: original | A | B | C | D
    w, h, g = 384, 192, 6
    sheet = Image.new("RGB", (5 * w + 4 * g, len(stems) * (h + g) - g), "white")
    for i, stem in enumerate(stems):
        imgs = [Image.open(args.originals / f"{stem}.png")]
        imgs += [Image.open(folders["A_cs_full"] / f"{stem}_blip_reconstructed.png")]
        imgs += [Image.open(folders[v] / f"{stem}.png") for v in VARIANTS]
        for j, im in enumerate(imgs):
            sheet.paste(im.convert("RGB").resize((w, h), Image.LANCZOS), (j * (w + g), i * (h + g)))
    sheet.save(args.save_dir / "compare.jpg", quality=85)
    for v in folders:
        s = summary[v]
        print(f"{v:14s} pixel acc {s['pixel_acc']:.3f}  mIoU {s['miou']:.3f}  sky {s['iou_sky']}  vegetation {s['iou_vegetation']}  colourfulness {s['colourfulness']:.1f}")
    print(f"original colourfulness {summary['original']['colourfulness']:.1f}; wrote {args.out}")


if __name__ == "__main__":
    main()
