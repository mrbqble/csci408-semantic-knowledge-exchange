#!/usr/bin/env python3
"""Payload size per element (Damir, 11 Nov 2026): segmentation map, edge map and caption, per camera photo.

Reads payload_index.json of every payload folder listed in SETS (written by payloads.py) and reports, per element, the mean / median / min / max size
and its share of the payload, next to the photo: as stored (CARLA JPEG, real-world PNG) and re-encoded as JPEG quality 90 at full resolution, which is
the fairer comparison. Writes PAYLOAD_SIZES.md and results/payload_sizes.json.
Usage: python payload_sizes.py
"""
import io
import json
import statistics
from pathlib import Path

from PIL import Image

SETS = [
    ("CARLA v3, current payload (map 1024x576, edges at full resolution)", Path("data/v3_payloads")),
    ("CARLA v3, working-size payload (map and edges at 896x512)", Path("data/v3_native")),
    ("Real-world (61 evaluated cases), current payload", Path("data/rw_core_payloads")),
    ("Real-world (61 evaluated cases), working-size payload", Path("data/rw_native")),
    ("Real-world, all 366 core cases, current payload", Path("data/rw_core_all_payloads")),
    ("CARLA v2, current payload", Path("data/carla_v2_payloads")),
]
ELEMENTS = [("segmentation map", "seg_b"), ("edge map", "edge_b"), ("caption", "caption_b"), ("payload total", "total_b")]


def kb(v):
    return v / 1024


def jpeg_size(path, cache={}):
    if path not in cache:
        buf = io.BytesIO()
        Image.open(path).convert("RGB").save(buf, format="JPEG", quality=90)
        cache[path] = buf.tell()
    return cache[path]


def main():
    out, md = {}, ["# Payload size per element\n",
                   "Per camera photo. The caption is UTF-8 text; the segmentation map is lossless WebP; the edge map is WebP (`payloads.py`). "
                   "'Photo as JPEG q90' re-encodes the original photo at full resolution, the fairer comparison for the PNG real-world photos.\n"]
    for label, folder in SETS:
        f = folder / "payload_index.json"
        if not f.exists():
            md.append(f"## {label}\n\n_not generated yet_\n")
            continue
        rows = list(json.loads(f.read_text()).values())
        photo = [r["file_b"] for r in rows]
        jpg = [jpeg_size(r["source"]) for r in rows if Path(r["source"]).exists()]
        tot = statistics.fmean(r["total_b"] for r in rows)
        md += [f"## {label}\n", f"{len(rows)} photos ({rows[0]['w']}x{rows[0]['h']}).\n",
               "| element | mean KB | median KB | min KB | max KB | share of payload |", "|---|---|---|---|---|---|"]
        stats = {}
        for name, key in ELEMENTS:
            v = [r[key] for r in rows]
            stats[name] = {"mean": statistics.fmean(v), "median": statistics.median(v), "min": min(v), "max": max(v)}
            share = f"{100 * statistics.fmean(v) / tot:.1f}%" if key != "total_b" else "100%"
            md.append(f"| {name} | {kb(statistics.fmean(v)):.2f} | {kb(statistics.median(v)):.2f} | {kb(min(v)):.2f} | {kb(max(v)):.2f} | {share} |")
        md.append(f"| photo as stored | {kb(statistics.fmean(photo)):.1f} | {kb(statistics.median(photo)):.1f} | {kb(min(photo)):.1f} | {kb(max(photo)):.1f} | payload = "
                  f"{100 * tot / statistics.fmean(photo):.1f}% of it |")
        if jpg:
            md.append(f"| photo as JPEG q90 | {kb(statistics.fmean(jpg)):.1f} | {kb(statistics.median(jpg)):.1f} | {kb(min(jpg)):.1f} | {kb(max(jpg)):.1f} | payload = "
                      f"{100 * tot / statistics.fmean(jpg):.1f}% of it |")
        md.append("")
        out[label] = {"photos": len(rows), "elements": stats, "photo_stored_mean": statistics.fmean(photo),
                      "photo_jpeg90_mean": statistics.fmean(jpg) if jpg else None}
    Path("PAYLOAD_SIZES.md").write_text("\n".join(md), encoding="utf-8")
    Path("results").mkdir(exist_ok=True)
    Path("results/payload_sizes.json").write_text(json.dumps(out, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    main()
