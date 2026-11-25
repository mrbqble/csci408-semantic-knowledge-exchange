#!/usr/bin/env python3
"""Why is the VLM-judge success rate higher on the real-world set than on CARLA v3? Evidence from data we already have:
detector statistics on the ORIGINAL main-camera photos (same detector for both datasets), the judge's own car counts,
which criterion fails, and CARLA weather. Writes report_kit/tables/real_vs_sim_*.csv and prints a summary.
"""
import csv
import json
import re
import statistics as st
from pathlib import Path

import paths

RW_CASES = [1 + 6 * k for k in range(61)]
CASES = {"v3": list(range(1, 113)), "rw": RW_CASES}
ORACLE = {"v3": Path("results/v3/analysis/oracle_full"), "rw": Path("results/rw_core/analysis/oracle_full")}
VEH = {"car", "bus", "truck"}
OUT = Path("report_kit/tables"); OUT.mkdir(parents=True, exist_ok=True)


def judge(run):
    out = {}
    for line in open(f"results/vlm/{run}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
            out[r["case"]] = r
    return out


def judge_count(text):
    """First car count the judge states for the ORIGINAL image ('contains approximately 12-13 cars' -> 12.5)."""
    m = re.search(r"original image (?:contains|has|shows|features)[^.]*?(\d+)(?:\s*(?:-|to|–)\s*(\d+))?\s+(?:\w+\s+){0,3}(?:cars|vehicles)", text, re.I)
    if not m:
        return None
    a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
    return (a + b) / 2


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def detector_stats(ds):
    rows = []
    for c in CASES[ds]:
        f = ORACLE[ds] / f"case{c}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        W = d.get("reference_size", [1920, 1080])[0] if isinstance(d.get("reference_size"), list) else 1920
        boxes = [x["bbox_reference_px"] for x in d["detections"] if x["class"] in VEH and x.get("score", 1) >= 0.5]
        heights = [b[3] - b[1] for b in boxes]
        overl = sum(1 for i in range(len(boxes)) for j in range(len(boxes)) if i != j and iou(boxes[i], boxes[j]) > 0.1)
        rows.append({"case": c, "vehicles": len(boxes), "small_lt_40px_tall": sum(1 for h in heights if h < 40),
                     "median_height_px": st.median(heights) if heights else 0, "vehicles_overlapping_another": len({i for i in range(len(boxes)) for j in range(len(boxes)) if i != j and iou(boxes[i], boxes[j]) > 0.1})})
    return rows


def main():
    summary = {}
    for ds in ("v3", "rw"):
        S, F = judge(f"{ds}_paper_k1"), judge(f"{ds}_fuse")
        det = {r["case"]: r for r in detector_stats(ds)}
        cases = [c for c in CASES[ds] if c in S]
        jc = {c: judge_count(S[c]["numbers"]["text"]) for c in cases}
        n = len(cases)
        fail_num = sum(1 for c in cases if S[c]["numbers"]["score"] == 0)
        fail_pos = sum(1 for c in cases if S[c]["positions"]["score"] == 0)
        joint = sum(S[c]["numbers"]["score"] * S[c]["positions"]["score"] for c in cases)
        dv = [det[c] for c in cases if c in det]
        tot_veh = sum(r["vehicles"] for r in dv)
        summary[ds] = {
            "cases": n, "single_camera_joint": f"{100*joint/n:.1f}%", "fails_numbers": f"{100*fail_num/n:.1f}%", "fails_positions": f"{100*fail_pos/n:.1f}%",
            "detector_vehicles_per_photo_mean": round(st.mean(r["vehicles"] for r in dv), 1) if dv else None,
            "detector_vehicles_per_photo_median": st.median(r["vehicles"] for r in dv) if dv else None,
            "share_small_vehicles_lt40px": f"{100*sum(r['small_lt_40px_tall'] for r in dv)/max(tot_veh,1):.1f}%",
            "share_vehicles_overlapping_another": f"{100*sum(r['vehicles_overlapping_another'] for r in dv)/max(tot_veh,1):.1f}%",
            "median_vehicle_height_px": st.median([r["median_height_px"] for r in dv if r["vehicles"]]) if dv else None,
            "judge_parsed_counts": sum(1 for v in jc.values() if v is not None),
            "judge_count_median": st.median([v for v in jc.values() if v is not None]),
        }
        # success by judge count bin
        bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 99)]
        with open(OUT / f"real_vs_sim_success_by_count_{ds}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["judge_count_bin", "cases", "single_joint_pct", "fusion_joint_pct"])
            for lo, hi in bins:
                cs = [c for c in cases if jc[c] is not None and lo <= jc[c] < hi]
                if cs:
                    sj = 100 * sum(S[c]["numbers"]["score"] * S[c]["positions"]["score"] for c in cs) / len(cs)
                    fj = 100 * sum(F[c]["numbers"]["score"] * F[c]["positions"]["score"] for c in cs if c in F) / len(cs)
                    w.writerow([f"{lo}-{hi - 1 if hi < 99 else '+'}", len(cs), round(sj, 1), round(fj, 1)])
                    print(f"{ds} judge count {lo:>2}-{hi-1 if hi < 99 else '+':>2}: {len(cs):3} cases, single {sj:5.1f}%, fusion {fj:5.1f}%")
    if True:  # CARLA weather
        m = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
        weather = {int(str(c["case"]).replace("case", "")): c.get("weather", "?") for c in m["cases"]}
        S, F = judge("v3_paper_k1"), judge("v3_fuse")
        groups = {}
        for c in S:
            groups.setdefault(weather.get(c, "?"), []).append(c)
        with open(OUT / "real_vs_sim_carla_weather.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["weather", "cases", "single_joint_pct", "fusion_joint_pct"])
            for wname, cs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
                sj = 100 * sum(S[c]["numbers"]["score"] * S[c]["positions"]["score"] for c in cs) / len(cs)
                fj = 100 * sum(F[c]["numbers"]["score"] * F[c]["positions"]["score"] for c in cs) / len(cs)
                w.writerow([wname, len(cs), round(sj, 1), round(fj, 1)])
                print(f"CARLA weather {wname:20} {len(cs):3} cases, single {sj:5.1f}%, fusion {fj:5.1f}%")
    with open(OUT / "real_vs_sim_summary.csv", "w", newline="", encoding="utf-8") as fh:
        keys = list(summary["v3"].keys())
        w = csv.writer(fh); w.writerow(["metric", "CARLA v3", "Real-world"])
        for k in keys:
            w.writerow([k, summary["v3"][k], summary["rw"][k]])
    for k in summary["v3"]:
        print(f"{k:40} CARLA {str(summary['v3'][k]):>8}   real-world {str(summary['rw'][k]):>8}")


if __name__ == "__main__":
    main()
