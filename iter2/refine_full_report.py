#!/usr/bin/env python3
"""Random-sample test of prompt_refine: every v3 case (112) and every evaluated real-world case (61), not the 20 hand-picked ones.

Same definitions as refine_report.py (recall/precision against the detector on the original photo, by oracle-box size; per-case paired change with a
95% bootstrap CI over cases). Decision rule fixed in advance: keep prompt_refine in the pipeline only if the pooled gain in all-vehicle recall over
both datasets is >= +0.05 and its 95% CI lies above zero; otherwise drop it from the default pipeline (it stays in the repo as an experiment).
Usage: python refine_full_report.py   -> REFINE_FULL_REPORT.md
"""
import statistics
from pathlib import Path

import refine_report as rr

DS = {"CARLA v3 (all 112 cases)": dict(ana=Path("results/refine/analysis_v3_all"), has_gt=True, cases=list(range(1, 113))),
      "Real-world (all 61 evaluated cases)": dict(ana=Path("results/refine/analysis_rw_all"), has_gt=False, cases=[1 + 6 * i for i in range(61)])}
RUN = {"CARLA v3 (all 112 cases)": Path("results/v3"), "Real-world (all 61 evaluated cases)": Path("results/rw_core")}


def main():
    res = {n: rr.collect(d) for n, d in DS.items()}
    lines = ["# prompt_refine on every case (random-sample test)\n",
             "All 112 CARLA v3 cases and all 61 evaluated real-world cases; no case selection. Definitions as in `REFINE_REPORT.md`: recall/precision against the "
             "detector on the original photo, Hungarian matching at IoU >= 0.5, pooled; bins by oracle-box side in the 1024x576 view; paired change = "
             "`prompt_refine` minus `prompt_only` per-case recall with a 95% bootstrap CI over cases.\n",
             "| dataset | variant | recall <24 px | 24-48 px | 48-120 px | >120 px | recall all | precision | cars MAE vs GT | s/img |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in res.items():
        for v in rr.VARIANTS:
            o = r[v]
            mae = f"{statistics.fmean(o['err']):.2f}" if o["err"] else "-"
            sec = statistics.fmean(s for s in o["sec"] if s is not None)
            cells = [rr.rate(o["bins"][b[2]][1], o["bins"][b[2]][0]) for b in rr.BINS]
            lines.append(f"| {n} | {v} | " + " | ".join(cells) + f" | {rr.rate(o['matched'], o['oracle'])} | {rr.rate(o['matched'], o['pred'])} | {mae} | {sec:.1f} |")
    lines += ["", "## Paired change in per-case recall\n", "| subset | all vehicles | vehicles < 48 px |", "|---|---|---|"]
    pa, ps = ([], []), ([], [])
    for n, r in res.items():
        a, b = r["prompt_only"], r["prompt_refine"]
        x1 = [(x, y) for x, y in zip(a["recall_case"], b["recall_case"]) if x is not None and y is not None]
        x2 = [(x, y) for x, y in zip(a["small_case"], b["small_case"]) if x is not None and y is not None]
        for x, y in x1: pa[0].append(x); pa[1].append(y)
        for x, y in x2: ps[0].append(x); ps[1].append(y)
        lines.append(f"| {n} | {rr.fmt_pair(rr.paired([x for x, _ in x1], [y for _, y in x1]))} | {rr.fmt_pair(rr.paired([x for x, _ in x2], [y for _, y in x2]))} |")
    pooled = rr.paired(*pa)
    lines.append(f"| both datasets | {rr.fmt_pair(pooled)} | {rr.fmt_pair(rr.paired(*ps))} |\n")
    keep = bool(pooled) and pooled["mean_diff"] >= 0.05 and pooled["ci95"][0] > 0
    lines.append("## Decision (rule fixed in advance)\n")
    lines.append(f"Pooled all-vehicle gain {pooled['mean_diff']:+.3f} (95% CI {pooled['ci95'][0]:+.3f} to {pooled['ci95'][1]:+.3f}). Rule: keep only if the gain is >= +0.05 with the CI above zero. "
                 f"**Result: {'keep' if keep else 'drop from the default pipeline'}.**\n")
    Path("REFINE_FULL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
