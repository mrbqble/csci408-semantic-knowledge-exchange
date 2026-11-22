#!/usr/bin/env python3
"""
Real-world multi-phone dataset: every frame of every clip, colour-correct, on one shared timeline per take.

Source: three phones filming each of three takes (case 1..3). Clip start offsets within a take come from file metadata
refined by audio alignment (accuracy about 0.1-0.25 s; see phone_sync_manifest.json).

Output (PNG, lossless, 1920x1080, SDR BT.709, no EXIF/GPS):
    <out>/take1/cam1_iphone16promax/000000.png ...     file name = slot on the take timeline (30 slots per second)
    <out>/take1/cam2_android/...                        the same slot number in different cameras = same moment
    <out>/take1/cam3_iphone16pro/...
    <out>/frames.csv      one row per image: take, camera, slot, time, source clip and time, sharpness, soft flag
    <out>/slots.csv       one row per slot: which cameras have a frame (sync_level 1-3), distinct flag, core case
    <out>/core/caseK/cam1.png cam2.png cam3.png   curated synchronised triplets: all three cameras sharp and the scene
                                                  changed since the previous kept triplet (same layout as the CARLA datasets)
    <out>/README.txt, <out>/phone_sync_manifest.json

Colour: the six iPhone clips are HLG HDR (BT.2020, 10-bit) and are tone-mapped to SDR (zscale + tonemap hable) in
float before 8-bit conversion; Android clips are SDR BT.709. IMG_3231 has a stale rotation tag, so rotation tags are
ignored for every clip (-noautorotate).

Needs ffmpeg and ffprobe (with the zscale filter). Example:
    python extract_real_world.py --src "<...>\\Real-world" --out C:\\carla_multicam_kit\\output\\real_world_astana_3phones_sync_v1 --ffmpeg C:\\CARLA\\tools\\ffmpeg\\bin
"""

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

GRID = 30  # slots per second on the take timeline
W, H = 1920, 1080
CAMS = {"cam1": "iphone16promax", "cam2": "android", "cam3": "iphone16pro"}

# take -> camera -> (relative path under --src, device, clip start in seconds relative to the take's reference clip)
TAKES = {
    "take1": {"cam1": ("case 1/IMG_7360.MOV", "iPhone 16 Pro Max", 0.0),
              "cam2": ("case 1/VID_20261022_131911.mp4", "Android phone", 1.403),
              "cam3": ("case 1/IMG_3230.MOV", "iPhone 16 Pro", 5.790)},
    "take2": {"cam1": ("case 2/IMG_7361.MOV", "iPhone 16 Pro Max", 0.0),
              "cam2": ("case 2/VID_20261022_132042.mp4", "Android phone", 5.580),
              "cam3": ("case 2/IMG_3231.MOV", "iPhone 16 Pro", 7.535)},
    "take3": {"cam1": ("case 3/IMG_7362.MOV", "iPhone 16 Pro Max", 0.0),
              "cam2": ("case 3/VID_20261022_132502.mp4", "Android phone", -18.412),
              "cam3": ("case 3/IMG_3232.MOV", "iPhone 16 Pro", -19.990)},
}

HDR_CHAIN = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
             "zscale=t=bt709,format=gbrp,format=rgb24")
SDR_CHAIN = "scale=in_range=auto:out_range=full:flags=bicubic+accurate_rnd+full_chroma_int,format=rgb24"


def probe(ffprobe, path):
    j = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,color_transfer,color_space,pix_fmt,nb_frames:format=duration",
                                   "-of", "json", path], capture_output=True, text=True, check=True).stdout)
    pk = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                         "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.split()
    pts = sorted(float(x) for x in pk if x.strip())
    s = j["streams"][0]
    return {"w": s["width"], "h": s["height"], "hdr": s.get("color_transfer") == "arib-std-b67", "pts": pts,
            "trc": s.get("color_transfer"), "pix_fmt": s.get("pix_fmt"), "duration": float(j["format"]["duration"])}


def gray_small(arr):
    """480x270 gray from a 1080p RGB frame (4x4 box average)."""
    a = arr.reshape(H // 4, 4, W // 4, 4, 3).astype(np.float32).mean(axis=(1, 3))
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def lap_var(g):
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def extract_clip(job):
    ffmpeg, ffprobe, path, out_dir, start_s, limit, compress = job
    info = probe(ffprobe, path)
    if (info["w"], info["h"]) != (W, H):
        raise RuntimeError(f"{path}: unexpected size {info['w']}x{info['h']}")
    vf = HDR_CHAIN if info["hdr"] else SDR_CHAIN
    cmd = [ffmpeg, "-v", "error", "-threads", "2", "-noautorotate", "-i", path, "-an", "-sn", "-dn", "-vf", vf,
           "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    os.makedirs(out_dir, exist_ok=True)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3 * 2)
    recs, thumbs, k = [], [], 0
    prev_slot = None
    fsize = W * H * 3
    t0 = time.time()
    while True:
        buf = p.stdout.read(fsize)
        if len(buf) < fsize:
            break
        if limit and k >= limit:
            break
        arr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        pts = info["pts"][k] if k < len(info["pts"]) else k / 30.0
        slot = int(math.floor((start_s + pts) * GRID + 0.5))
        if prev_slot is not None and slot <= prev_slot:  # frame period close to the slot period: two frames fell into one slot; push the later one to the next slot, never overwrite
            slot = prev_slot + 1
        prev_slot = slot
        name = f"{slot:06d}.png"
        Image.fromarray(arr).save(os.path.join(out_dir, name), format="PNG", compress_level=compress)
        g = gray_small(arr)
        recs.append({"k": k, "pts": pts, "slot": slot, "file": name, "lap": lap_var(g), "luma": float(g.mean())})
        thumbs.append(g.reshape(90, 3, 160, 3).mean(axis=(1, 3)).astype(np.uint8))
        k += 1
    if limit:
        p.kill()
    p.wait()
    return {"path": path, "hdr": info["hdr"], "trc": info["trc"], "n_packets": len(info["pts"]), "n_frames": k,
            "records": recs, "thumbs": np.array(thumbs), "secs": round(time.time() - t0, 1)}


def write_readme(out, st, a):
    tk = st["takes"]
    lines = [
        "Real-world multi-phone dataset (3 phones x 3 takes, Astana), every frame, shared timeline per take",
        "=" * 80,
        f"{st['images']} images (1920x1080 PNG, lossless, SDR BT.709, no EXIF/GPS); {st['core_cases']} curated synchronised triplets in core/.",
        "",
        "Layout",
        "  takeT/camX_<phone>/SSSSSS.png   SSSSSS = slot on the take timeline, 30 slots per second from the take's earliest clip.",
        "                                  The same slot number in different cameras of a take = the same moment (within the alignment accuracy).",
        "  frames.csv                      one row per image (take, camera, slot, time, source clip/time, relative sharpness, soft flag, mean luma)",
        "  slots.csv                       one row per slot: sync_level = number of cameras with a frame (3 = all phones filming), distinct flag, core case",
        "  core/caseK/cam1.png cam2.png cam3.png   curated triplets (all three cameras sharp and the scene changed since the previous kept triplet);",
        "                                  same layout as the CARLA datasets. core/index.csv maps case K to take and slot.",
        "  dataset_manifest.json, phone_sync_manifest.json   clip offsets, alignment details, counts",
        "",
        "Cameras: cam1 = iPhone 16 Pro Max, cam2 = Android phone, cam3 = iPhone 16 Pro (same in every take). Takes: take1 = case 1 (13:19), take2 = case 2 (13:20-21), take3 = case 3 (13:25).",
        "",
        "Synchronisation: clip start offsets come from file metadata (iPhone created/modified = start/end; Android end time) refined by audio alignment",
        "(GCC-PHAT restricted to the metadata-feasible window). Accuracy about 0.1-0.25 s: NOT frame-exact. A car at 10 m/s moves 1-2.5 m in that time.",
        "",
        "Colour: iPhone clips are HLG HDR (BT.2020, 10-bit): tone-mapped to SDR in float (zscale + tonemap hable, desat 0), then 8-bit. Android clips are SDR BT.709.",
        "IMG_3231 carries a stale rotation tag; rotation tags are ignored for all clips (all frames are upright landscape).",
        f"Soft frames (sharpness below {a.soft} of the clip median) are flagged, not removed: {st['soft']} images.",
        "Faces and licence plates are visible in the frames (Takes 2 and 3 especially): keep the dataset internal or blur before sharing.",
        "",
        "Per take (slots; sync_level 3 / 2 / 1; distinct slots; core triplets):",
    ]
    for t, v in tk.items():
        lines.append(f"  {t}: {v['slots']} slots; {v['sync3']} / {v['sync2']} / {v['sync1']}; {v['distinct_slots']} distinct; {v['core_triplets']} core triplets")
    open(os.path.join(out, "README.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def build_slots_and_core(a, takes, meta, results):
    """slots.csv, distinct flags and the core triplets from per-clip records and thumbnails."""
    if os.path.isdir(os.path.join(a.out, "core")):
        shutil.rmtree(os.path.join(a.out, "core"))
    slot_rows, core, n_core = [], [], 0
    stats = {"images": sum(len(r["records"]) for r in results.values()), "soft": sum(1 for r in results.values() for x in r["records"] if x["soft"]), "takes": {}}
    for t in takes:
        by = {cam: {r["slot"]: (r, i) for i, r in enumerate(results[(t, cam)]["records"])} for cam in TAKES[t]}
        slots = sorted(set().union(*[set(d) for d in by.values()]))
        last = {}
        kept_all, kept_triple = 0, 0
        for s in slots:
            present = [c for c in by if s in by[c]]
            level = len(present)
            changed = any(c not in last or np.abs(results[(t, c)]["thumbs"][by[c][s][1]].astype(np.float32) - last[c]).mean() > a.distinct for c in present)
            candidate = changed and (level < 3 or s % 3 == 0)  # triplets are judged on a 10 per second grid
            soft_any = any(by[c][s][0]["soft"] for c in present)
            is_core = False
            if candidate:
                for c in present:
                    last[c] = results[(t, c)]["thumbs"][by[c][s][1]].astype(np.float32)
                kept_all += 1
                if level == 3 and not soft_any:
                    n_core += 1
                    kept_triple += 1
                    is_core = True
                    core.append((n_core, t, s, {c: os.path.join(meta[(t, c)]["dir"], by[c][s][0]["file"]) for c in by}))
            slot_rows.append([t, s, round(s / GRID, 3), level, ",".join(present), int(candidate), n_core if is_core else "", int(soft_any)])
        stats["takes"][t] = {"slots": len(slots), "sync3": sum(1 for r in slot_rows if r[0] == t and r[3] == 3), "sync2": sum(1 for r in slot_rows if r[0] == t and r[3] == 2),
                              "sync1": sum(1 for r in slot_rows if r[0] == t and r[3] == 1), "distinct_slots": kept_all, "core_triplets": kept_triple}
    with open(os.path.join(a.out, "slots.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "slot", "time_s", "sync_level", "cameras", "distinct", "core_case", "any_soft"])
        w.writerows(slot_rows)
    for n, t, s, files in core:
        d = os.path.join(a.out, "core", f"case{n}")
        os.makedirs(d, exist_ok=True)
        for c, rel in files.items():
            shutil.copy2(os.path.join(a.out, rel), os.path.join(d, f"{c}.png"))
    os.makedirs(os.path.join(a.out, "core"), exist_ok=True)
    with open(os.path.join(a.out, "core", "index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "take", "slot", "time_s"])
        for n, t, s_, _ in core:
            w.writerow([n, t, s_, round(s_ / GRID, 3)])
    return stats, core, slot_rows


def load_results(out, meta):
    """Rebuild per-clip records from frames.csv and the saved thumbnails (for --reselect)."""
    res = {}
    with open(os.path.join(out, "frames.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["take"], row["camera"])
            res.setdefault(key, {"records": []})["records"].append({
                "k": int(row["clip_frame"]), "pts": float(row["clip_time_s"]), "slot": int(row["slot"]), "file": os.path.basename(row["file"]),
                "rel_sharp": float(row["rel_sharpness"]), "soft": bool(int(row["soft"])), "luma": float(row["mean_luma"])})
    for key, v in res.items():
        v["records"].sort(key=lambda r: r["k"])
        v["thumbs"] = np.load(os.path.join(out, "_work", f"thumbs_{key[0]}_{key[1]}.npy"))
    return {k: v for k, v in res.items() if k in meta}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg", default="", help="folder with ffmpeg and ffprobe (default: PATH)")
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--only", default="", help="comma list of takes, e.g. take1,take3")
    ap.add_argument("--limit", type=int, default=0, help="debug: frames per clip")
    ap.add_argument("--png-level", type=int, default=3, help="PNG compression 0-9 (lossless at any level)")
    ap.add_argument("--distinct", type=float, default=6.0, help="mean abs difference (0-255, 160x90) to count as changed")
    ap.add_argument("--soft", type=float, default=0.5, help="relative sharpness below this share of the clip median = soft")
    ap.add_argument("--reselect", action="store_true", help="no extraction: rebuild slots.csv and core/ from the saved thumbnails with the current --distinct")
    a = ap.parse_args()
    exe = ".exe" if os.name == "nt" else ""
    ffmpeg = os.path.join(a.ffmpeg, "ffmpeg" + exe) if a.ffmpeg else "ffmpeg"
    ffprobe = os.path.join(a.ffmpeg, "ffprobe" + exe) if a.ffmpeg else "ffprobe"
    takes = [t for t in TAKES if not a.only or t in a.only.split(",")]
    os.makedirs(a.out, exist_ok=True)

    # take timeline starts at the earliest clip of the take
    jobs, meta = [], {}
    for t in takes:
        t0 = min(v[2] for v in TAKES[t].values())
        for cam, (rel, dev, off) in TAKES[t].items():
            path = os.path.join(a.src, *rel.split("/"))
            if not os.path.exists(path):
                sys.exit(f"missing: {path}")
            out_dir = os.path.join(a.out, t, f"{cam}_{CAMS[cam]}")
            jobs.append((ffmpeg, ffprobe, path, out_dir, off - t0, a.limit, a.png_level))
            meta[(t, cam)] = {"device": dev, "clip": rel, "start_on_take_timeline_s": round(off - t0, 3), "dir": os.path.relpath(out_dir, a.out)}
    t_start = time.time()
    if a.reselect:
        results = load_results(a.out, meta)
        stats, core, slot_rows = build_slots_and_core(a, takes, meta, results)
        stats["core_cases"] = len(core)
        write_readme(a.out, stats, a)
        print(json.dumps(stats, indent=1), flush=True)
        return
    keys = list(meta)
    print(f"extracting {len(jobs)} clips with {a.workers} workers ...", flush=True)
    results = {}
    os.makedirs(os.path.join(a.out, "_work"), exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for key, res in zip(keys, ex.map(extract_clip, jobs)):
            results[key] = res
            np.save(os.path.join(a.out, "_work", f"thumbs_{key[0]}_{key[1]}.npy"), res["thumbs"])
            print(f"  {key[0]}/{key[1]}: {res['n_frames']} frames ({'HDR tone-mapped' if res['hdr'] else 'SDR'}) in {res['secs']} s, packets {res['n_packets']}", flush=True)

    # sharpness / soft flags per clip, per-image table
    rows = []
    for (t, cam), res in results.items():
        med = float(np.median([r["lap"] for r in res["records"]]))
        for r in res["records"]:
            r["rel_sharp"] = r["lap"] / med if med else 1.0
            r["soft"] = r["rel_sharp"] < a.soft
            rows.append([t, cam, meta[(t, cam)]["device"], r["slot"], round(r["slot"] / GRID, 3), meta[(t, cam)]["clip"], r["k"], round(r["pts"], 4),
                         f"{r['rel_sharp']:.3f}", int(r["soft"]), round(r["luma"], 1), os.path.join(meta[(t, cam)]["dir"], r["file"])])
    with open(os.path.join(a.out, "frames.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "camera", "device", "slot", "time_s", "clip", "clip_frame", "clip_time_s", "rel_sharpness", "soft", "mean_luma", "file"])
        w.writerows(rows)

    stats, core, slot_rows = build_slots_and_core(a, takes, meta, results)
    stats["core_cases"] = len(core)
    stats["seconds"] = round(time.time() - t_start, 1)
    manifest = {"cameras": {c: CAMS[c] for c in CAMS}, "grid_slots_per_second": GRID, "clips": {f"{t}/{c}": v for (t, c), v in meta.items()}, "stats": stats,
                "colour": "iPhone clips HLG HDR tone-mapped to SDR BT.709 (zscale+tonemap hable, desat 0); Android clips SDR BT.709; rotation tags ignored",
                "alignment_accuracy_s": "about 0.1-0.25 (audio-refined; not frame-exact)"}
    json.dump(manifest, open(os.path.join(a.out, "dataset_manifest.json"), "w"), indent=1)
    write_readme(a.out, stats, a)
    print(json.dumps(stats, indent=1), flush=True)


if __name__ == "__main__":
    main()
