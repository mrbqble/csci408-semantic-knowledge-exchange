#!/usr/bin/env python3
"""Tuning of Damir's fusion (20 Nov 2026), selection rule fixed before any tuning result existed:
  - candidates: strength 0.3 / 0.4 / 0.5 / 0.6 at IP scale 1.0, and IP scale 0.5 / 0.75 at strength 0.5 (full-resolution supports)
  - tuning half: CARLA cases 1-56 + the first 30 real-world cases; held-out half: CARLA 57-112 + the last 31 real-world cases
  - winner = most joint successes on the tuning half (both datasets together); the current setting (0.5, 1.0) is replaced only if beaten
  - the winner is generated and judged on the held-out half; it is reported there against the current setting and the single camera
Writes TUNING_RESULTS.md and jobs/tune_winner.json.
"""
import json
import subprocess
import sys
from pathlib import Path

from scipy.stats import binom

PY = sys.executable
TUNE = {"v3": list(range(1, 57)), "rw": [1 + 6 * k for k in range(30)]}
HOLD = {"v3": list(range(57, 113)), "rw": [1 + 6 * k for k in range(30, 61)]}
PAY = {"v3": "data/v3_payloads", "rw": "data/rw_core_payloads"}
CANDS = {"st0.5_ip1.0": ("fuseF", 0.5, 1.0), "st0.3": ("fuseF_st0.3", 0.3, 1.0), "st0.4": ("fuseF_st0.4", 0.4, 1.0),
         "st0.6": ("fuseF_st0.6", 0.6, 1.0), "ip0.5": ("fuseF_ip0.5", 0.5, 0.5), "ip0.75": ("fuseF_ip0.75", 0.5, 0.75)}
DEFAULT = "st0.5_ip1.0"


def load(run):
    out, f = {}, Path(f"results/vlm/{run}.jsonl")
    if f.exists():
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
                out[r["case"]] = r["numbers"]["score"] * r["positions"]["score"]
    return out


def mcnemar(a, b, cases):
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))


def run(cmd):
    print(">", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=False)


def main():
    lines = ["# Tuning of Damir's fusion (strength, IP-Adapter scale)", "",
             "Selection rule fixed in advance: the winner is the setting with the most joint successes on the tuning half (CARLA 1-56 plus the first 30",
             "real-world cases). The current setting (strength 0.5, IP scale 1.0) is replaced only if beaten. The winner is then reported on the held-out half only.", "",
             "## Tuning half", "", "| Setting | strength | IP scale | CARLA joint | Real-world joint | Total |", "|---|---|---|---|---|---|"]
    scores = {}
    data = {k: {ds: load(f"{ds}_{run_}") for ds in ("v3", "rw")} for k, (run_, _, _) in CANDS.items()}
    common = {ds: [c for c in TUNE[ds] if all(c in data[k][ds] for k in CANDS)] for ds in ("v3", "rw")}
    for k, (run_, st, ip) in CANDS.items():
        v = sum(data[k]["v3"][c] for c in common["v3"]); r = sum(data[k]["rw"][c] for c in common["rw"])
        scores[k] = v + r
        lines.append(f"| {k} | {st} | {ip} | {v}/{len(common['v3'])} | {r}/{len(common['rw'])} | {v + r} |")
    best = max(scores.values())
    winner = DEFAULT if scores[DEFAULT] == best else max((k for k in CANDS if k != DEFAULT), key=lambda k: scores[k])
    lines += ["", f"Common judged cases: CARLA {len(common['v3'])}/56, real-world {len(common['rw'])}/30. **Winner: {winner}**"
              + (" (the current setting, so nothing to confirm)" if winner == DEFAULT else "") + "."]
    Path("jobs/tune_winner.json").write_text(json.dumps({"winner": winner, "scores": scores, "common": {d: len(c) for d, c in common.items()}}, indent=1))
    if winner != DEFAULT:
        run_, st, ip = CANDS[winner]
        for ds in ("v3", "rw"):
            out = f"results/{ds}_fuseF_st{st:g}" if ip == 1.0 else f"results/{ds}_fuseF_st0.5"
            variant = "fuse" if ip == 1.0 else f"fuse@{ip:g}"
            run([PY, "-u", "coordinator.py", "--payloads", PAY[ds], "--out", out, "--variants", variant, "--size", "1920x1088", "--palette", "cs",
                 "--fuse-strength", f"{st:g}", "--fuse-main", f"results/{ds}_paper/k1", "--fuse-support", f"results/{ds}_paper/k1",
                 "--cases", ",".join(map(str, HOLD[ds]))])
        for _ in range(3):
            run([PY, "-u", "vlm_judge.py", "--runs", f"v3_{run_},rw_{run_}", "--workers", "4"])
        lines += ["", "## Held-out half", "", "| Comparison (joint score, McNemar) | CARLA 57-112 | Real-world, last 31 |", "|---|---|---|"]
        rows = {}
        for ds in ("v3", "rw"):
            w_, d_, s_, h_ = load(f"{ds}_{run_}"), load(f"{ds}_fuseF"), load(f"{ds}_paper_k1"), load(f"{ds}_fuse")
            cases = [c for c in HOLD[ds] if c in w_ and c in d_ and c in s_ and c in h_]
            n = max(len(cases), 1)
            rows.setdefault("joint success", []).append(f"winner {100*sum(w_[c] for c in cases)/n:.1f}%, current {100*sum(d_[c] for c in cases)/n:.1f}%, "
                                                        f"896x512-support fusion {100*sum(h_[c] for c in cases)/n:.1f}%, "
                                                        f"single camera {100*sum(s_[c] for c in cases)/n:.1f}% (n = {len(cases)})")
            for key, (a, b) in {"winner vs current setting": (w_, d_), "winner vs single-camera MMSD": (w_, s_),
                                "current setting vs single-camera MMSD": (d_, s_), "winner vs fusion with 896x512 supports": (w_, h_)}.items():
                w, l, p = mcnemar(a, b, cases)
                rows.setdefault(key, []).append(f"{100*(w-l)/n:+.1f} pts ({w}/{l}, p = {p:.3f})")
        for key, vals in rows.items():
            lines.append(f"| {key} | {vals[0]} | {vals[1]} |")
    Path("TUNING_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)
    print("TUNE_SELECT_DONE", flush=True)


if __name__ == "__main__":
    main()
