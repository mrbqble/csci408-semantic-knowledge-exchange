#!/usr/bin/env python3
"""Build the training crops for fine-tuning the receiver's ControlNets (the training itself is not run here; it needs a larger GPU).

Sources and splits (decided before looking at any result):
  CARLA v2 (112 cases) and CARLA v4 (new, ~224 cases)   train, except cases with number % 10 == 0 -> val
  real-world core cases (all 366, payloads made from the phone photos)   the 61 cases of the test run (cases 1, 7, 13, ...) are HELD OUT and not cropped;
                                                           of the rest, case number % 10 == 0 -> val, the others train
  CARLA v3 (112 cases)                                     test set, never used for training
Every photo gives 4 crops of 512x512 at the working scale of the receiver (the photo, the transmitted segmentation map and the edge map all in the
1024x576 frame, so a small car stays small): 2 centred on a random small vehicle blob of the segmentation map (when the photo has one), 2 at random.
Each crop is written as <id>_image.jpg, <id>_seg.png, <id>_edge.png plus one line in metadata.jsonl (paths, BLIP caption, source, case, camera, crop
corner, number of small vehicle blobs inside). The ground-truth-free training signal comes from the payloads themselves: the sender's maps are the
conditioning, the photo is the target.

Usage: python training_prep.py        (needs data/carla_v2_payloads, data/v4_payloads, data/rw_core_all_payloads)
"""
import json
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from coordinator import small_vehicle_components

OUT = Path("data/train_crops")
W, H, C = 1024, 576, 512
CROPS_PER_PHOTO = 4
SOURCES = [("carla_v2", Path("data/carla_v2_payloads")), ("carla_v4", Path("data/v4_payloads")), ("real_world", Path("data/rw_core_all_payloads"))]
REAL_TEST = {1 + 6 * i for i in range(61)}


def split_of(source, case_no):
    if source == "real_world" and case_no in REAL_TEST:
        return None                                  # held out
    return "val" if case_no % 10 == 0 else "train"


def edge_condition(edge_l):
    arr = cv2.resize(np.asarray(edge_l), (W, H), interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.where(arr > 40, 255, 0).astype(np.uint8), "L")


def main():
    rng = random.Random(0)
    summary = {"splits": {}, "held_out_real_cases": len(REAL_TEST), "test_set": "CARLA v3 (never cropped)"}
    meta = {"train": [], "val": []}
    for source, pdir in SOURCES:
        if not pdir.exists():
            print(f"{source}: no payloads at {pdir}, skipped", flush=True)
            continue
        cases = sorted((p for p in pdir.iterdir() if p.is_dir() and p.name.startswith("case")), key=lambda p: int(p.name[4:]))
        n_photos = 0
        for cdir in cases:
            sp = split_of(source, int(cdir.name[4:]))
            if sp is None:
                continue
            for mf in sorted(cdir.glob("cam*_meta.json")):
                cam = mf.name[: -len("_meta.json")]
                info = json.loads(mf.read_text())
                photo = Path(info["source"])
                if not photo.exists():
                    continue
                img = Image.open(photo).convert("RGB").resize((W, H), Image.LANCZOS)
                seg = Image.open(cdir / f"{cam}_seg.webp").convert("RGB")
                seg = seg if seg.size == (W, H) else seg.resize((W, H), Image.NEAREST)
                edge = edge_condition(Image.open(cdir / f"{cam}_edge.webp").convert("L"))
                caption = (cdir / f"{cam}_caption.txt").read_text(encoding="utf-8").strip()
                blobs = small_vehicle_components(seg, (W, H))
                centres = [((b["box"][0] + b["box"][2]) // 2, (b["box"][1] + b["box"][3]) // 2) for b in blobs]
                rng.shuffle(centres)
                for k in range(CROPS_PER_PHOTO):
                    if k < 2 and k < len(centres):
                        cx, cy = centres[k]
                        x0, y0 = min(max(cx - C // 2, 0), W - C), min(max(cy - C // 2, 0), H - C)
                    else:
                        x0, y0 = rng.randint(0, W - C), rng.randint(0, H - C)
                    box = (x0, y0, x0 + C, y0 + C)
                    cid = f"{source}_{cdir.name}_{cam}_{k}"
                    d = OUT / sp
                    d.mkdir(parents=True, exist_ok=True)
                    img.crop(box).save(d / f"{cid}_image.jpg", quality=95)
                    seg.crop(box).save(d / f"{cid}_seg.png")
                    edge.crop(box).save(d / f"{cid}_edge.png")
                    inside = sum(1 for b in blobs if b["box"][0] >= x0 and b["box"][1] >= y0 and b["box"][2] <= x0 + C and b["box"][3] <= y0 + C)
                    meta[sp].append({"image": f"{sp}/{cid}_image.jpg", "conditioning_seg": f"{sp}/{cid}_seg.png", "conditioning_edge": f"{sp}/{cid}_edge.png",
                                     "text": caption, "source": source, "case": cdir.name, "cam": cam, "x0": x0, "y0": y0, "small_vehicle_blobs": inside})
                n_photos += 1
        summary["splits"].setdefault(source, {})["photos_cropped"] = n_photos
        print(f"{source}: {n_photos} photos cropped", flush=True)
    for sp, rows in meta.items():
        if rows:
            (OUT / sp / "metadata.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    summary["crops"] = {sp: len(r) for sp, r in meta.items()}
    summary["crops_by_source"] = {sp: {s: sum(1 for r in rows if r["source"] == s) for s in {r["source"] for r in rows}} for sp, rows in meta.items()}
    summary["crops_with_small_vehicles"] = {sp: sum(1 for r in rows if r["small_vehicle_blobs"] > 0) for sp, rows in meta.items()}
    Path("results").mkdir(exist_ok=True)
    Path("results/training_split.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
