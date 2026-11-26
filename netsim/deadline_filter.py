#!/usr/bin/env python3
"""Turn a run's raw arrival log into the on-time payload tree that coordinator.py consumes.

Virtual time (agreed default): the transfer inside the containers is real and measured
(transfer_s in arrival_log.jsonl); the node's compute time is modelled and added here:
    arrival_virtual_s = PI5_COMPUTE_S + transfer_s        (measured from the moment of capture)
A payload is on time when arrival_virtual_s <= deadline_s. Late and lost payloads are simply absent
from received_ontime/, in the same layout as iter2/data/carla_v2_payloads, so
    python iter2/coordinator.py --payloads <run>/received_ontime --out ...
fuses whatever arrived (a case without any on-time camera has no folder and is skipped).

PI5_COMPUTE_S: the paper's Pi 5 timings as quoted in the kickoff (Risk 1): segmentation 8.35 s,
Canny 0.02 s, captioning 7.07 s, i.e. all three components run on every node.
deadline_s is a PLACEHOLDER (default 25 s); the team has not set one.

Outputs in the run folder: received_ontime/, summary.json, cases.csv.
"""
import argparse
import csv
import json
import shutil
import statistics as st
from pathlib import Path

PI5_COMPUTE_PARTS_S = {"segmentation": 8.35, "canny": 0.02, "caption": 7.07}
PI5_COMPUTE_S = sum(PI5_COMPUTE_PARTS_S.values())
DEFAULT_DEADLINE_S = 25.0
SUFFIXES = ("_seg.webp", "_edge.webp", "_caption.txt", "_meta.json")


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))] if xs else None


def process(run_dir, deadline_s=DEFAULT_DEADLINE_S, pi_s=PI5_COMPUTE_S):
    run = Path(run_dir)
    plan = json.loads((run / "plan.json").read_text())
    log_path = run / "arrival_log.jsonl"
    recs = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[(r["case"], r["cam"])] = r                      # last write wins
    out = run / "received_ontime"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    rows = []
    for case in plan["cases"]:
        expected = plan["cams"][case]
        got = [recs[(case, c)] for c in expected if (case, c) in recs]
        for r in got:
            r["arrival_virtual_s"] = pi_s + r["transfer_s"]
            r["on_time"] = r["arrival_virtual_s"] <= deadline_s
            if r["on_time"]:
                (out / case).mkdir(exist_ok=True)
                for suf in SUFFIXES:
                    shutil.copy2(run / "received" / case / f"{r['cam']}{suf}", out / case / f"{r['cam']}{suf}")
        ontime = [r for r in got if r["on_time"]]
        rows.append({"case": case, "expected_k": len(expected), "received_k": len(got), "ontime_k": len(ontime),
                     "ontime_cams": " ".join(r["cam"] for r in sorted(ontime, key=lambda r: int(r["cam"][3:]))),
                     "wire_bytes": sum(r["wire_bytes"] for r in got),
                     "max_transfer_s": round(max((r["transfer_s"] for r in got), default=0), 3),
                     "max_arrival_virtual_s": round(max((r["arrival_virtual_s"] for r in got), default=0), 3)})
    allr = list(recs.values())
    tr = [r["transfer_s"] for r in allr]
    summary = {
        "deadline_s": deadline_s, "pi_compute_s": round(pi_s, 3),
        "cases": len(rows), "payloads_expected": sum(r["expected_k"] for r in rows),
        "payloads_received": len(allr), "payloads_ontime": sum(r["ontime_k"] for r in rows),
        "cases_with_all_cameras_ontime": sum(r["ontime_k"] == r["expected_k"] for r in rows),
        "cases_with_no_camera_ontime": sum(r["ontime_k"] == 0 for r in rows),
        "transfer_s": {"mean": round(st.mean(tr), 3), "median": round(st.median(tr), 3),
                       "p95": round(pct(tr, 0.95), 3), "max": round(max(tr), 3)} if tr else None,
        "wire_bytes_total": sum(r["wire_bytes"] for r in allr),
        "case_completion_s_mean": round(st.mean(r["max_transfer_s"] for r in rows), 3) if rows else None,
    }
    ing = run / "ingest_summary.json"
    if ing.exists():
        summary["ingest"] = json.loads(ing.read_text())
    (run / "summary.json").write_text(json.dumps(summary, indent=1))
    with open(run / "cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["case"])
        w.writeheader()
        w.writerows(rows)
    return summary, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--deadline", type=float, default=DEFAULT_DEADLINE_S, help="seconds after capture (virtual)")
    ap.add_argument("--pi-compute-s", type=float, default=PI5_COMPUTE_S)
    a = ap.parse_args()
    s, _ = process(a.run, a.deadline, a.pi_compute_s)
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()