#!/usr/bin/env python3
"""
Case folders for ALL sync levels, grouped by number of cameras, for a dataset made by extract_real_world_v2.py.

A moment becomes a case when the scene changed since the previous kept moment (the 'distinct' flag of slots.csv) and none of
its frames is soft. Cases are numbered by take and time. Image files are copied.

    <root>/cases_1to3phones/<N>_camera(s)/caseK/camJ.png   the phones that were filming (a phone keeps its camera number, so a
                                                            two-phone case may hold cam1+cam3 and lack cam2)
    <root>/cases_1to3phones/index.csv    case, take, slot, time_s, n_cameras, cameras, group, path, source_cases, sync_confidence
    <root>/cases_all_slots.csv           every moment of every take with cameras present, flags, case number, files, case_folder, sync_confidence

    python build_cases_grouped.py --root <dataset folder>
"""
import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter


def take_key(t):
    m = re.search(r"\d+", t)
    return (int(m.group()) if m else 0, t)


def group_name(n):
    return f"{n}_camera" if n == 1 else f"{n}_cameras"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    root = a.root
    out = os.path.join(root, "cases_1to3phones")
    if os.path.isdir(out) and os.listdir(out):
        raise SystemExit(f"{out} already exists and is not empty; remove it first")
    manifest = json.load(open(os.path.join(root, "dataset_manifest.json"), encoding="utf-8"))
    conf = {t: v["sync"]["confidence"] for t, v in manifest["takes"].items()}
    files = {}
    with open(os.path.join(root, "frames.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            files[(r["take"], r["camera"], int(r["slot"]))] = r["file"]
    with open(os.path.join(root, "slots.csv"), newline="", encoding="utf-8") as f:
        slots = list(csv.DictReader(f))
    slots.sort(key=lambda r: (take_key(r["take"]), int(r["slot"])))

    os.makedirs(out, exist_ok=True)
    n = 0
    all_rows, index_rows = [], []
    per = Counter()
    for r in slots:
        cams = r["cameras"].split(",")
        s = int(r["slot"])
        selected = int(r["distinct"]) == 1 and int(r["any_soft"]) == 0
        case, folder = "", ""
        if selected:
            n += 1
            case = n
            g = group_name(len(cams))
            d = os.path.join(out, g, f"case{n}")
            os.makedirs(d)
            for c in cams:
                shutil.copy2(os.path.join(root, files[(r["take"], c, s)]), os.path.join(d, f"{c}.png"))
            folder = f"cases_1to3phones/{g}/case{n}"
            index_rows.append([n, r["take"], s, r["time_s"], len(cams), "+".join(cams), g, f"{g}/case{n}", r["source_cases"], conf[r["take"]]])
            per[(r["take"], len(cams))] += 1
        all_rows.append([r["take"], s, r["time_s"], len(cams), "+".join(cams), r["distinct"], r["any_soft"], case]
                        + [files.get((r["take"], c, s), "") for c in ("cam1", "cam2", "cam3")] + [folder, r["source_cases"], conf[r["take"]]])
    with open(os.path.join(out, "index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "take", "slot", "time_s", "n_cameras", "cameras", "group", "path", "source_cases", "sync_confidence"])
        w.writerows(index_rows)
    with open(os.path.join(root, "cases_all_slots.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "slot", "time_s", "n_cameras", "cameras", "distinct", "any_soft", "case", "cam1_file", "cam2_file", "cam3_file", "case_folder", "source_cases", "sync_confidence"])
        w.writerows(all_rows)

    tot = Counter()
    for (t, k), v in per.items():
        tot[k] += v
    lines = ["", "Cases for every sync level, grouped by number of cameras (build_cases_grouped.py)",
             "  cases_1to3phones/<N>_camera(s)/caseK/camJ.png   one case per distinct moment, from 1 phone filming up to all 3; a phone keeps its camera number",
             "                                    (a two-phone case can be cam1+cam3 and lack cam2). index.csv: case, take, slot, time, cameras, group, path, source_cases, sync_confidence.",
             "  cases_all_slots.csv               all moments of all takes with cameras present, distinct flag, soft flag, case number, file per camera, case_folder, sync_confidence.",
             "  A moment is a case when the scene changed since the previous kept moment and none of its frames is soft.",
             "  sync_confidence (high / medium / low) is the alignment quality of the take; filter on it before using multi-camera cases for anything that needs exact timing.",
             "  Cases by number of phones: " + ", ".join(f"{k} phone(s): {tot[k]}" for k in (1, 2, 3)) + f" (total {n}; images {sum(k * v for k, v in tot.items())})."]
    with open(os.path.join(root, "README.txt"), "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("cases:", n, "| by phones:", dict(sorted(tot.items())), "| images:", sum(k * v for k, v in tot.items()))
    for t in sorted({k[0] for k in per}, key=take_key):
        print(" ", t, "(sync %s):" % conf[t], {k: per[(t, k)] for k in (1, 2, 3)})


if __name__ == "__main__":
    main()
