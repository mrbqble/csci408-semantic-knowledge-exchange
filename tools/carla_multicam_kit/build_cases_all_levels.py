#!/usr/bin/env python3
"""
Build case folders for ALL sync levels (1, 2 or 3 phones filming) from an extracted real-world dataset.

Reads frames.csv and slots.csv of the dataset (made by extract_real_world.py) and writes

    <root>/cases_1to3phones/caseK/camJ.png   the phones that were filming at that moment (cam1 = iPhone 16 Pro Max,
                                              cam2 = Android, cam3 = iPhone 16 Pro; a phone keeps its camera number, so a
                                              two-phone case may hold cam1+cam3 and be missing cam2)
    <root>/cases_1to3phones/index.csv        case, take, slot, time_s, n_cameras, cameras
    <root>/cases_all_slots.csv               every moment of every take (all 3,274 slots): cameras present, distinct flag,
                                              soft flag, case number if curated, and the file of each camera

A moment becomes a case when the scene changed since the previous kept moment (the 'distinct' flag of slots.csv) and none
of its frames is soft. Cases are numbered by take and time. Image files are copied (not linked).

    python build_cases_all_levels.py --root <dataset folder>
"""
import argparse
import csv
import os
import shutil
from collections import Counter

ORDER = {"take1": 0, "take2": 1, "take3": 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    root = a.root
    out = os.path.join(root, "cases_1to3phones")
    if os.path.isdir(out) and os.listdir(out):
        raise SystemExit(f"{out} already exists and is not empty; remove it first")

    files = {}
    with open(os.path.join(root, "frames.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            files[(r["take"], r["camera"], int(r["slot"]))] = r["file"]
    with open(os.path.join(root, "slots.csv"), newline="", encoding="utf-8") as f:
        slots = list(csv.DictReader(f))
    slots.sort(key=lambda r: (ORDER[r["take"]], int(r["slot"])))

    os.makedirs(out, exist_ok=True)
    n = 0
    all_rows, index_rows = [], []
    per = Counter()
    for r in slots:
        cams = r["cameras"].split(",")
        s = int(r["slot"])
        selected = int(r["distinct"]) == 1 and int(r["any_soft"]) == 0
        case = ""
        if selected:
            n += 1
            case = n
            d = os.path.join(out, f"case{n}")
            os.makedirs(d)
            for c in cams:
                shutil.copy2(os.path.join(root, files[(r["take"], c, s)]), os.path.join(d, f"{c}.png"))
            index_rows.append([n, r["take"], s, r["time_s"], len(cams), "+".join(cams)])
            per[(r["take"], len(cams))] += 1
        all_rows.append([r["take"], s, r["time_s"], len(cams), "+".join(cams), r["distinct"], r["any_soft"], case]
                        + [files.get((r["take"], c, s), "") for c in ("cam1", "cam2", "cam3")])
    with open(os.path.join(out, "index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "take", "slot", "time_s", "n_cameras", "cameras"])
        w.writerows(index_rows)
    with open(os.path.join(root, "cases_all_slots.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["take", "slot", "time_s", "n_cameras", "cameras", "distinct", "any_soft", "case", "cam1_file", "cam2_file", "cam3_file"])
        w.writerows(all_rows)

    lines = ["", "Cases for every sync level (added by build_cases_all_levels.py)",
             "  cases_1to3phones/caseK/camJ.png   one case per distinct moment, from 1 phone filming up to all 3; a phone keeps its camera number",
             "                                    (a two-phone case can be cam1+cam3 and lack cam2). cases_1to3phones/index.csv lists case, take, slot, time, cameras.",
             "  cases_all_slots.csv               all 3,274 moments of all takes with cameras present, distinct flag, soft flag, case number and file per camera.",
             "  A moment is a case when the scene changed since the previous kept moment and none of its frames is soft."]
    tot = Counter()
    for (t, k), v in sorted(per.items()):
        tot[k] += v
    lines.append("  Cases by number of phones: " + ", ".join(f"{k} phone(s): {tot[k]}" for k in (1, 2, 3)) + f" (total {n}; images {sum(k * v for k, v in tot.items())}).")
    with open(os.path.join(root, "README.txt"), "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("cases:", n, "| by phones:", dict(sorted(tot.items())), "| images:", sum(k * v for k, v in tot.items()))
    for t in ("take1", "take2", "take3"):
        print(t, {k: per[(t, k)] for k in (1, 2, 3)})


if __name__ == "__main__":
    main()
