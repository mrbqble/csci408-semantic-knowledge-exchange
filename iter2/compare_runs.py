#!/usr/bin/env python3
"""Compare two runs of the same cases against the detector on the original photo (works without ground truth, e.g. the real-world set).

Both analysis folders must hold <variant>/caseK.json and oracle_gen/caseK.json (analysis.py output). Vehicles = car, truck, bus, motorcycle;
Hungarian matching at IoU >= 0.5; pooled recall by oracle-box size, precision, and the paired change in per-case recall (b minus a) with a
95% bootstrap CI over cases (analysis.paired_boot).
Usage: python compare_runs.py --a results/rw_core/analysis --b results/rw_cn07_15/analysis --cases 1,7,13 --names default,new
"""
import argparse
import json
from pathlib import Path

import numpy as np

from analysis import paired_boot
from refine_report import BINS, SMALL_MAX, match_flags, side, vboxes


def parse_cases(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--a", required=True, type=Path)
    ap.add_argument("--b", required=True, type=Path)
    ap.add_argument("--variant", default="prompt_only")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--names", default="a,b")
    args = ap.parse_args()
    na, nb = args.names.split(",")
    stats = {n: {"bins": {b[2]: [0, 0] for b in BINS}, "m": 0, "p": 0, "o": 0, "rc": [], "sc": [], "sec": []} for n in (na, nb)}
    for c in parse_cases(args.cases):
        fa = args.a / args.variant / f"case{c}.json"
        fb = args.b / args.variant / f"case{c}.json"
        if not (fa.exists() and fb.exists()):
            continue
        ob = vboxes(json.loads((args.a / "oracle_gen" / f"case{c}.json").read_text()))
        for name, f in ((na, fa), (nb, fb)):
            row = json.loads(f.read_text())
            vb = vboxes(row)
            hit = match_flags(ob, vb)
            s = stats[name]
            for i, b in enumerate(ob):
                for lo, hi, bn in BINS:
                    if lo <= side(b) < hi:
                        s["bins"][bn][0] += 1; s["bins"][bn][1] += int(hit[i])
            s["m"] += int(hit.sum()); s["p"] += len(vb); s["o"] += len(ob)
            s["rc"].append(float(hit.mean()) if ob else None)
            small = [i for i, b in enumerate(ob) if side(b) < SMALL_MAX]
            s["sc"].append(float(hit[small].mean()) if small else None)
            if row.get("seconds") is not None:
                s["sec"].append(row["seconds"])
    print(f"{'run':16}{'cases':>6}{'oracle veh':>11}" + "".join(f"{b[2]:>10}" for b in BINS) + f"{'recall':>8}{'prec':>7}{'s/img':>7}")
    for name, s in stats.items():
        print(f"{name:16}{len(s['rc']):6}{s['o']:11}" + "".join(f"{s['bins'][b[2]][1] / max(s['bins'][b[2]][0], 1):10.2f}" for b in BINS) +
              f"{s['m'] / max(s['o'], 1):8.3f}{s['m'] / max(s['p'], 1):7.2f}{(np.mean(s['sec']) if s['sec'] else float('nan')):7.1f}")
    for key, label in (("rc", "all vehicles"), ("sc", "vehicles < 48 px")):
        pairs = [(x, y) for x, y in zip(stats[na][key], stats[nb][key]) if x is not None and y is not None]
        p = paired_boot([x for x, _ in pairs], [y for _, y in pairs])
        if p:
            lo, hi = p["ci95"]
            flag = "CI above zero" if lo > 0 else ("CI below zero" if hi < 0 else "CI crosses zero")
            print(f"paired change in per-case recall, {label}, {nb} minus {na}: {p['mean_diff']:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}; n={p['n']}; {flag})")


if __name__ == "__main__":
    main()
