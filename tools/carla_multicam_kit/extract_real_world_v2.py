#!/usr/bin/env python3
"""
Real-world multi-phone dataset, batch 2: every frame of every clip, colour-correct, on one shared timeline per take.

Generalises extract_real_world.py: takes and clip offsets come from a JSON file (--takes), a camera may have several clips
inside one take (a phone that stopped and restarted), long clips are split into chunks so all CPU cores stay busy, and the
slot of every frame is computed before extraction.

Output (PNG, lossless, 1920x1080, SDR BT.709, no EXIF/GPS):
    <out>/<take>/camX_<phone>/SSSSSS.png     SSSSSS = slot on the take timeline (30 per second from the take's earliest clip)
    <out>/frames.csv   one row per image: take, camera, device, source_case, slot, time, clip, clip_index, clip frame/time, sharpness, soft flag, luma, file
    <out>/slots.csv    one row per slot: sync_level (number of cameras with a frame), cameras, distinct flag, core_case, any_soft, source_cases
    <out>/dataset_manifest.json, <out>/README.txt, <out>/_work/thumbs_*.npy  (for --reselect)
No core/ folder is written (the all-levels case builder, build_cases_grouped.py, makes the case folders).

Colour: iPhone clips are HLG HDR (BT.2020, 10-bit) tone-mapped to SDR in float (zscale + tonemap hable, desat 0); Android clips
are SDR BT.709. Rotation tags are ignored for every clip.

    python extract_real_world_v2.py --src "<...>\\Real-world\\Video" --takes takes_v2.json --out <folder> --ffmpeg C:\\CARLA\\tools\\ffmpeg\\bin
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

GRID = 30
W, H = 1920, 1080
HDR_CHAIN = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
             "zscale=t=bt709,format=gbrp,format=rgb24")
SDR_CHAIN = "scale=in_range=auto:out_range=full:flags=bicubic+accurate_rnd+full_chroma_int,format=rgb24"


def probe(ffprobe, path):
    j = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,color_transfer,pix_fmt:format=duration", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    pk = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                         "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.split()
    s = j["streams"][0]
    return {"w": s["width"], "h": s["height"], "hdr": s.get("color_transfer") == "arib-std-b67", "trc": s.get("color_transfer"),
            "pts": sorted(float(x) for x in pk if x.strip())}


def assign_slots(pts, start_s):
    """slot = floor(t*30+0.5); a frame that falls into an already used slot is pushed to the next one (never overwrites)."""
    out, prev = [], None
    for p in pts:
        s = int(math.floor((start_s + p) * GRID + 0.5))
        if prev is not None and s <= prev:
            s = prev + 1
        prev = s
        out.append(s)
    return out


def gray_small(arr):
    a = arr.reshape(H // 4, 4, W // 4, 4, 3).astype(np.float32).mean(axis=(1, 3))
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def lap_var(g):
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def extract_chunk(job):
    ffmpeg, path, hdr, out_dir, pts, slots, k0, k1, compress = job
    chain = HDR_CHAIN if hdr else SDR_CHAIN
    vf = f"select=between(n\\,{k0}\\,{k1 - 1})," + chain
    cmd = [ffmpeg, "-v", "error", "-threads", "2", "-noautorotate", "-i", path, "-an", "-sn", "-dn", "-vf", vf,
           "-fps_mode", "passthrough", "-frames:v", str(k1 - k0), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    os.makedirs(out_dir, exist_ok=True)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3 * 2)
    recs, thumbs, k = [], [], k0
    fsize = W * H * 3
    t0 = time.time()
    while k < k1:
        buf = p.stdout.read(fsize)
        if len(buf) < fsize:
            break
        arr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        name = f"{slots[k]:06d}.png"
        Image.fromarray(arr).save(os.path.join(out_dir, name), format="PNG", compress_level=compress)
        g = gray_small(arr)
        recs.append({"k": k, "pts": pts[k], "slot": slots[k], "file": name, "lap": lap_var(g), "luma": float(g.mean())})
        thumbs.append(g.reshape(90, 3, 160, 3).mean(axis=(1, 3)).astype(np.uint8))
        k += 1
    p.kill()
    p.wait()
    return {"k0": k0, "records": recs, "thumbs": np.array(thumbs), "secs": round(time.time() - t0, 1)}


def build_slots(a, takes, merged, thumbs_of):
    """slots.csv rows, distinct flags, core numbering. merged[(take, cam)] = list of records (sorted by slot), each with clip key and k."""
    rows, stats, n_core = [], {"takes": {}}, 0
    for t in takes:
        cams = sorted(c for (tt, c) in merged if tt == t)
        by = {c: {r["slot"]: r for r in merged[(t, c)]} for c in cams}
        slots = sorted(set().union(*[set(d) for d in by.values()]))
        last, kept_all, kept_full = {}, 0, 0
        last_slot = -10 ** 9
        counts = {1: 0, 2: 0, 3: 0}
        for s in slots:
            present = [c for c in cams if s in by[c]]
            level = len(present)
            th = {c: thumbs_of[by[c][s]["clipkey"]][by[c][s]["k"]].astype(np.float32) for c in present}
            changed = any(c not in last or np.abs(th[c] - last[c]).mean() > a.distinct for c in present)
            candidate = changed and (level < len(cams) or s % 3 == 0) and s - last_slot >= a.min_gap  # full-camera moments are judged on a 10 per second grid; min_gap spaces moving-camera footage
            soft_any = any(by[c][s]["soft"] for c in present)
            core_no = ""
            if candidate:
                for c in present:
                    last[c] = th[c]
                kept_all += 1
                last_slot = s
                if level == len(cams) and not soft_any:
                    n_core += 1
                    kept_full += 1
                    core_no = n_core
            counts[level] = counts.get(level, 0) + 1
            rows.append([t, s, round(s / GRID, 3), level, ",".join(present), int(candidate), core_no, int(soft_any),
                         ",".join(sorted({str(by[c][s]["source_case"]) for c in present}))])
        stats["takes"][t] = {"slots": len(slots), "sync3": counts.get(3, 0), "sync2": counts.get(2, 0), "sync1": counts.get(1, 0), "distinct_slots": kept_all, "full_camera_distinct": kept_full}
    with open(os.path.join(a.out, "slots.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "slot", "time_s", "sync_level", "cameras", "distinct", "core_case", "any_soft", "source_cases"])
        w.writerows(rows)
    return stats, rows


def write_readme(out, st, spec, a):
    lines = ["Real-world multi-phone dataset, batch 2 (3 phones, Astana, 7 Nov 2026), every frame, shared timeline per take", "=" * 100,
             f"{st['images']} images (1920x1080 PNG, lossless, SDR BT.709, no EXIF/GPS).", "",
             "Layout", "  takeT/camX_<phone>/SSSSSS.png   SSSSSS = slot on the take timeline, 30 slots per second from the take's earliest clip;",
             "                                  the same slot number in different cameras of a take = the same moment (within the alignment accuracy below).",
             "  frames.csv   one row per image (take, camera, device, source_case, slot, time, clip, clip_index, clip frame/time, sharpness, soft flag, luma, file)",
             "  slots.csv    one row per slot: sync_level = number of cameras with a frame, cameras, distinct flag, core_case, any_soft, source_cases",
             "  dataset_manifest.json   clips, offsets, sync method and confidence per take, counts", "",
             "Cameras: cam1 = iPhone 16 Pro Max, cam2 = Android phone, cam3 = iPhone 16 Pro (same in every take).", "",
             "Takes (the user's case folders): take4 = case 4 (14:18), take5 = case 5 (14:20-21), take6 = case 6 (14:23-24),",
             "take7_8 = cases 7 and 8 as ONE continuous timeline (14:30:55-14:33:22): the iPhone 16 Pro Max recorded IMG_7387 (in folder case 7) without",
             "stopping across both cases, the iPhone 16 Pro and the Android phone each stopped and restarted (case 8's clips), and case 8's Android clip overlaps",
             "case 7's iPhone 16 Pro clip in time. A camera therefore has two clips in take7_8; source_case in frames.csv/slots.csv tells which folder a clip came from.", "",
             "Synchronisation (accuracy differs per take, see dataset_manifest.json):"]
    for t, v in spec["takes"].items():
        s = v["sync"]
        lines.append(f"  {t}: {s['confidence'].upper()} - {s['method']}; uncertainty about {s['uncertainty_s']} s. {s.get('note', '')}")
    lines += ["", "Colour: iPhone clips are HLG HDR (BT.2020, 10-bit): tone-mapped to SDR in float (zscale + tonemap hable, desat 0), then 8-bit. Android clips are SDR BT.709. Rotation tags are ignored.",
              f"Soft frames (sharpness below {a.soft} of the clip median) are flagged, not removed: {st['soft']} images.",
              f"Distinct moments (slots.csv 'distinct'): the scene changed by more than {a.distinct}/255 (mean absolute difference on 160x90 thumbnails) against the last kept moment of that camera and at least {a.min_gap} slots ({a.min_gap / 30:.2f} s) passed since the previous kept moment of the take; the phones are handheld and move, so without the spacing almost every frame counts as new.",
              "Faces and licence plates are visible: keep the dataset internal or blur before sharing.", "",
              "Per take (slots; sync_level 3 / 2 / 1; distinct slots):"]
    for t, v in st["takes"].items():
        lines.append(f"  {t}: {v['slots']} slots; {v['sync3']} / {v['sync2']} / {v['sync1']}; {v['distinct_slots']} distinct")
    open(os.path.join(out, "README.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--takes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg", default="")
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0, help="debug: frames per clip")
    ap.add_argument("--chunk", type=int, default=1000, help="split clips longer than this many frames into chunks for parallel work")
    ap.add_argument("--png-level", type=int, default=3)
    ap.add_argument("--distinct", type=float, default=6.0)
    ap.add_argument("--soft", type=float, default=0.5)
    ap.add_argument("--min-gap", type=int, default=0, help="minimum slots between kept distinct moments of a take (handheld footage changes constantly)")
    ap.add_argument("--reselect", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.takes, encoding="utf-8"))
    CAMS = spec["cameras"]
    exe = ".exe" if os.name == "nt" else ""
    ffmpeg = os.path.join(a.ffmpeg, "ffmpeg" + exe) if a.ffmpeg else "ffmpeg"
    ffprobe = os.path.join(a.ffmpeg, "ffprobe" + exe) if a.ffmpeg else "ffprobe"
    takes = [t for t in spec["takes"] if not a.only or t in a.only.split(",")]
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(os.path.join(a.out, "_work"), exist_ok=True)

    # clips, probes, slots
    clips = {}   # clipkey -> meta
    for t in takes:
        t0 = min(c["start_s"] for cl in spec["takes"][t]["clips"].values() for c in cl)
        for cam, cl in spec["takes"][t]["clips"].items():
            used = set()
            for ci, c in enumerate(cl):
                key = (t, cam, ci)
                path = os.path.join(a.src, *c["path"].split("/"))
                if not os.path.exists(path):
                    sys.exit(f"missing: {path}")
                clips[key] = {"take": t, "cam": cam, "ci": ci, "path": path, "rel": c["path"], "device": c["device"], "source_case": c["source_case"], "start_s": c["start_s"] - t0,
                              "dir": os.path.join(a.out, t, f"{cam}_{CAMS[cam]}")}
    if not a.reselect:
        for key, m in clips.items():
            info = probe(ffprobe, m["path"])
            if (info["w"], info["h"]) != (W, H):
                sys.exit(f"{m['path']}: unexpected size {info['w']}x{info['h']}")
            m["hdr"], m["trc"], m["pts"] = info["hdr"], info["trc"], info["pts"]
            m["slots"] = assign_slots(info["pts"], m["start_s"])
        for t in takes:
            for cam in spec["takes"][t]["clips"]:
                seen = {}
                for key, m in clips.items():
                    if key[0] == t and key[1] == cam:
                        for s in m["slots"]:
                            if s in seen:
                                sys.exit(f"{t}/{cam}: clips {seen[s]} and {key[2]} both use slot {s}; their time ranges overlap")
                            seen[s] = key[2]

    t_start = time.time()
    if a.reselect:
        rows = list(csv.DictReader(open(os.path.join(a.out, "frames.csv"), newline="", encoding="utf-8")))
        merged, thumbs_of = {}, {}
        for key in clips:
            thumbs_of[key] = np.load(os.path.join(a.out, "_work", f"thumbs_{key[0]}_{key[1]}_{key[2]}.npy"))
        for r in rows:
            if r["take"] not in takes:
                continue
            key = (r["take"], r["camera"], int(r["clip_index"]))
            merged.setdefault((r["take"], r["camera"]), []).append({"slot": int(r["slot"]), "k": int(r["clip_frame"]), "clipkey": key, "soft": bool(int(r["soft"])), "source_case": r["source_case"]})
        for v in merged.values():
            v.sort(key=lambda r: r["slot"])
        stats, slot_rows = build_slots(a, takes, merged, thumbs_of)
        stats["images"] = len(rows); stats["soft"] = sum(1 for r in rows if r["soft"] == "1")
        write_readme(a.out, stats, spec, a)
        print(json.dumps(stats, indent=1))
        return

    # chunk jobs
    jobs, owner = [], []
    for key, m in clips.items():
        n = len(m["pts"])
        if a.limit:
            n = min(n, a.limit)
        step = a.chunk if n > a.chunk * 1.2 else n
        for k0 in range(0, n, step):
            k1 = min(n, k0 + step)
            jobs.append((ffmpeg, m["path"], m["hdr"], m["dir"], m["pts"], m["slots"], k0, k1, a.png_level))
            owner.append(key)
    print(f"{len(clips)} clips, {sum(len(m['pts']) for m in clips.values())} frames, {len(jobs)} chunks, {a.workers} workers", flush=True)
    chunks = {key: [] for key in clips}
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, (key, res) in enumerate(zip(owner, ex.map(extract_chunk, jobs))):
            chunks[key].append(res)
            print(f"  [{i + 1}/{len(jobs)}] {key[0]}/{key[1]} clip {key[2]} frames {res['k0']}..{res['k0'] + len(res['records']) - 1} in {res['secs']} s", flush=True)

    merged, thumbs_of, table = {}, {}, []
    for key, m in clips.items():
        cs = sorted(chunks[key], key=lambda c: c["k0"])
        recs = [r for c in cs for r in c["records"]]
        th = np.concatenate([c["thumbs"] for c in cs]) if recs else np.zeros((0, 90, 160), np.uint8)
        expect = min(len(m["pts"]), a.limit) if a.limit else len(m["pts"])
        if len(recs) != expect:
            print(f"WARNING {key}: {len(recs)} frames decoded, {expect} packets", flush=True)
        np.save(os.path.join(a.out, "_work", f"thumbs_{key[0]}_{key[1]}_{key[2]}.npy"), th)
        thumbs_of[key] = th
        med = float(np.median([r["lap"] for r in recs])) if recs else 1.0
        m["n_frames"] = len(recs)
        for r in recs:
            r["rel_sharp"] = r["lap"] / med if med else 1.0
            r["soft"] = r["rel_sharp"] < a.soft
            r["clipkey"] = key
            r["source_case"] = m["source_case"]
            merged.setdefault((key[0], key[1]), []).append(r)
            table.append([key[0], key[1], m["device"], m["source_case"], r["slot"], round(r["slot"] / GRID, 3), m["rel"], key[2], r["k"], round(r["pts"], 4),
                          f"{r['rel_sharp']:.3f}", int(r["soft"]), round(r["luma"], 1), os.path.join(key[0], f"{key[1]}_{CAMS[key[1]]}", r["file"])])
    for v in merged.values():
        v.sort(key=lambda r: r["slot"])
    with open(os.path.join(a.out, "frames.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "camera", "device", "source_case", "slot", "time_s", "clip", "clip_index", "clip_frame", "clip_time_s", "rel_sharpness", "soft", "mean_luma", "file"])
        w.writerows(table)
    stats, slot_rows = build_slots(a, takes, merged, thumbs_of)
    stats["images"] = len(table); stats["soft"] = sum(1 for r in table if r[11] == 1); stats["seconds"] = round(time.time() - t_start, 1)
    manifest = {"cameras": CAMS, "grid_slots_per_second": GRID, "stats": stats,
                "takes": {t: {"label": spec["takes"][t]["label"], "sync": spec["takes"][t]["sync"],
                              "clips": [{"camera": k[1], "clip_index": k[2], "clip": m["rel"], "device": m["device"], "source_case": m["source_case"], "start_on_take_timeline_s": round(m["start_s"], 3),
                                         "frames": m["n_frames"], "hdr_tone_mapped": m["hdr"]} for k, m in clips.items() if k[0] == t]} for t in takes},
                "colour": "iPhone clips HLG HDR tone-mapped to SDR BT.709 (zscale+tonemap hable, desat 0); Android clips SDR BT.709; rotation tags ignored"}
    json.dump(manifest, open(os.path.join(a.out, "dataset_manifest.json"), "w"), indent=1)
    write_readme(a.out, stats, spec, a)
    print(json.dumps(stats, indent=1), flush=True)


if __name__ == "__main__":
    main()
