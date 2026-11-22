#!/usr/bin/env python3
"""
Group the case folders of the Drive datasets by number of cameras (in place, folders are moved, nothing is copied or deleted).

    <dataset>/caseK/...   ->   <dataset>/<N>_camera(s)/caseK/...

Case numbers do not change. The index / manifest of each dataset is updated so every path still resolves.
Run with --dry-run first.
"""
import csv, json, os, re, shutil, sys
from collections import Counter, defaultdict

BASE = r"C:\Users\mrbqble\My Drive (bibol.assetbek@nu.edu.kz)\uni\04\01\CSCI 408\Senior Project Work\Datasets"
DATASETS = {
    "CARLA v3": (os.path.join(BASE, "Simulated", "carla_dataset_v3_ids"), (".jpg",), "manifest"),
}
DRY = "--dry-run" in sys.argv


def group_name(n):
    return f"{n}_camera" if n == 1 else f"{n}_cameras"


def images(d, exts):
    return [f for f in os.listdir(d) if os.path.splitext(f)[1].lower() in exts]


def main():
    summary = {}
    for label, (root, exts, kind) in DATASETS.items():
        if not os.path.isdir(root):
            print(f"[{label}] MISSING: {root}")
            return 1
        cases = sorted([d for d in os.listdir(root) if re.fullmatch(r"case\d+", d) and os.path.isdir(os.path.join(root, d))], key=lambda x: int(x[4:]))
        if not cases:
            print(f"[{label}] no flat case folders (already grouped?): {sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))}")
            continue
        counts = {c: len(images(os.path.join(root, c), exts)) for c in cases}
        # cross-check with the dataset's own metadata
        expect = {}
        if kind == "index_csv":
            for r in csv.DictReader(open(os.path.join(root, "index.csv"), newline="", encoding="utf-8")):
                expect["case" + r["case"]] = int(r["n_cameras"])
        else:
            m = json.load(open(os.path.join(root, "manifest.json"), encoding="utf-8"))
            for e in m["cases"]:
                expect[e["folder"]] = int(e["n_cameras"])
        bad = [(c, counts[c], expect.get(c)) for c in cases if expect.get(c) != counts[c]]
        if bad or set(expect) != set(cases):
            print(f"[{label}] METADATA MISMATCH, not touching this dataset: {bad[:5]} | cases only in metadata: {sorted(set(expect) - set(cases))[:5]}")
            return 1
        tot_files = sum(counts.values())
        tot_bytes = sum(os.path.getsize(os.path.join(root, c, f)) for c in cases for f in images(os.path.join(root, c), exts))
        by = defaultdict(list)
        for c in cases:
            by[counts[c]].append(c)
        print(f"[{label}] {len(cases)} cases, {tot_files} images, {tot_bytes:,} bytes -> " + ", ".join(f"{group_name(n)}: {len(v)} cases" for n, v in sorted(by.items())))
        summary[label] = (root, exts, kind, by, tot_files, tot_bytes)
    if DRY:
        print("dry run only, nothing moved")
        return 0

    for label, (root, exts, kind, by, tot_files, tot_bytes) in summary.items():
        for n, cs in sorted(by.items()):
            g = os.path.join(root, group_name(n))
            os.makedirs(g, exist_ok=True)
            for c in cs:
                shutil.move(os.path.join(root, c), os.path.join(g, c))
        where = {c: group_name(n) for n, cs in by.items() for c in cs}
        if kind == "index_csv":
            p = os.path.join(root, "index.csv")
            rows = list(csv.DictReader(open(p, newline="", encoding="utf-8")))
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["case", "take", "slot", "time_s", "n_cameras", "cameras", "group", "path"])
                for r in rows:
                    g = where["case" + r["case"]]
                    w.writerow([r["case"], r["take"], r["slot"], r["time_s"], r["n_cameras"], r["cameras"], g, f"{g}/case{r['case']}"])
            p2 = os.path.join(os.path.dirname(root), "cases_all_slots.csv")
            rows2 = list(csv.DictReader(open(p2, newline="", encoding="utf-8")))
            cols = list(rows2[0].keys()) + (["case_folder"] if "case_folder" not in rows2[0] else [])
            with open(p2, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for r in rows2:
                    r["case_folder"] = f"cases_1to3phones/{where['case' + r['case']]}/case{r['case']}" if r["case"] else ""
                    w.writerow(r)
            readme = os.path.join(os.path.dirname(root), "README.txt")
            what = "phones"
        else:
            p = os.path.join(root, "manifest.json")
            m = json.load(open(p, encoding="utf-8"))
            for e in m["cases"]:
                e["folder"] = f"{where[e['folder']]}/{e['folder']}"
            m["layout"] = "cases are grouped in folders by number of cameras: <N>_camera(s)/caseK/camJ.jpg; every case's 'folder' is relative to the dataset root"
            json.dump(m, open(p, "w", encoding="utf-8"), indent=2)
            readme = os.path.join(root, "README.txt")
            what = "cameras"
        lines = ["", "Layout update (25 Oct 2026): cases are grouped by number of " + what,
                 "  " + ", ".join(f"{group_name(n)}/ ({len(cs)} cases of {n} image{'s' if n > 1 else ''})" for n, cs in sorted(by.items())),
                 "  Case numbers did not change; a case is now <group>/caseK/ instead of caseK/. " +
                 ("index.csv has new columns group and path; cases_all_slots.csv has a new column case_folder." if kind == "index_csv" else "manifest.json 'folder' entries now include the group folder.")]
        if kind == "index_csv":
            lines.append("  The scripts mentioned above (extract_real_world.py, build_cases_all_levels.py, verify_rw.py) are no longer in this copy; they live on the OMEN in C:\\carla_multicam_kit and C:\\CARLA\\jobs.")
        with open(readme, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[{label}] moved and metadata updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
