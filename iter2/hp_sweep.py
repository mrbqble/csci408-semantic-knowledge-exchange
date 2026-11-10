#!/usr/bin/env python3
"""One-at-a-time sweep of receiver hyperparameters on CARLA v3 (prompt_only, cases 1-24), then a hold-out check of the best one.

Each configuration changes ONE thing from the defaults (guidance 7.5, 20 steps, ControlNet scales 1.0/1.0 on all steps, no negative prompt):
  g4, g12                guidance scale 4 and 12
  steps40                40 denoising steps
  seg1.5                 segmentation-ControlNet strength 1.5
  c0.7_seg1.5            canny 0.7, segmentation 1.5
  ctrl_end0.8            ControlNets switched off for the last 20% of the steps
  neg                    negative prompt "blurry, low quality, deformed, cartoon, merged cars"
Every configuration is scored with gt_eval.py against the CARLA ground truth (recall at IoU 0.5 and by size, precision, cars MAE, paired change
in per-case recall vs the default run, which is results/v3/analysis/prompt_only). Seven configurations are compared, so the best of them on
24 cases is optimistic: the best one (if it beats the default by >= 0.02 recall) is rerun on cases 25-60, which were not used to pick it.

Usage: python hp_sweep.py
"""
import json
import subprocess
import sys
from pathlib import Path

import paths

PY = sys.executable
V3 = str(paths.CARLA_V3)
SWEEP_CASES, HOLD_CASES = "1-24", "25-60"
CONFIGS = {
    "g4": ["--guidance", "4.0"],
    "g12": ["--guidance", "12.0"],
    "steps40": ["--steps", "40"],
    "seg1.5": ["--cn-scales", "1.0,1.5"],
    "c0.7_seg1.5": ["--cn-scales", "0.7,1.5"],
    "ctrl_end0.8": ["--control-end", "0.8"],
    "neg": ["--negative-prompt", "blurry, low quality, deformed, cartoon, merged cars"],
}
DEFAULT = "results/v3/analysis/prompt_only"


def run(cmd, log):
    print(" ".join(cmd[:4]), "...", flush=True)
    with open(log, "a") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=False)


def generate_and_analyse(name, extra, cases):
    out = Path("results/hp") / name
    if not (out / "analysis" / "prompt_only" / f"case{cases.split('-')[-1]}.json").exists():
        run([PY, "-u", "coordinator.py", "--payloads", "data/v3_payloads", "--out", str(out), "--variants", "prompt_only", "--cases", cases, "--palette", "cs"] + extra,
            "jobs/hp_sweep_detail.log")
        run([PY, "-u", "analysis.py", "--out", str(out), "--dataset", V3, "--payloads", "data/v3_payloads", "--variants", "prompt_only", "--cases", cases, "--no-overlays"],
            "jobs/hp_sweep_detail.log")
    return f"{out}/analysis/prompt_only"


def gt_eval(runs, cases, out_json):
    p = subprocess.run([PY, "gt_eval.py", "--cases", cases, "--out", out_json] + runs, capture_output=True, text=True)
    print(p.stdout + p.stderr, flush=True)
    return json.loads(Path(out_json).read_text())


def main():
    Path("results/hp").mkdir(parents=True, exist_ok=True)
    folders = {name: generate_and_analyse(name, extra, SWEEP_CASES) for name, extra in CONFIGS.items()}
    print(f"\n=== sweep on cases {SWEEP_CASES} (7 configurations vs the default) ===", flush=True)
    summary = gt_eval([f"default={DEFAULT}"] + [f"{n}={f}" for n, f in folders.items()], SWEEP_CASES, "results/hp/sweep_summary.json")
    best = max(CONFIGS, key=lambda n: summary[n]["recall5"])
    gain = summary[best]["recall5"] - summary["default"]["recall5"]
    print(f"\nbest on the sweep cases: {best} (recall@.5 {summary[best]['recall5']:.3f} vs default {summary['default']['recall5']:.3f}, +{gain:.3f})", flush=True)
    if gain < 0.02:
        print("no configuration beats the default by >= 0.02 recall: no hold-out run", flush=True)
        return
    print(f"\n=== hold-out: default vs {best} on cases {HOLD_CASES} (not used to pick it) ===", flush=True)
    hold = generate_and_analyse(best + "_holdout", CONFIGS[best], HOLD_CASES)
    gt_eval([f"default={DEFAULT}", f"{best}={hold}"], HOLD_CASES, "results/hp/holdout_summary.json")


if __name__ == "__main__":
    main()
