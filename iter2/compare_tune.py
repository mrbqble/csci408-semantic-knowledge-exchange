import json, statistics, numpy as np
from pathlib import Path
CASES = [f"case{i}" for i in range(1, 25)]
roots = {"base 1024x576 canny1.0": Path("results/carla_v2"), "canny0.5 1024x576": Path("results/tune_c05"), "canny0.0 (seg only) 1024x576": Path("results/tune_c00"),
         "canny0.5 1280x704": Path("results/tune_c05_hr"), "canny1.0 1280x704": Path("results/tune_c10_hr")}
def load(root):
    out = {}
    for c in CASES:
        f = root / "analysis" / "prompt_only" / f"{c}.json"
        if f.exists():
            out[c] = json.loads(f.read_text())
    return out
data = {k: load(r) for k, r in roots.items()}
base = data["base 1024x576 canny1.0"]
def boot(d):
    d = np.array(d, float); rng = np.random.default_rng(0)
    b = rng.choice(d, size=(2000, len(d))).mean(axis=1); return float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
print(f"{'config':32}{'n':>3}{'cars':>7}{'MAE':>6}{'bias':>6}{'v.rec':>7}{'v.prec':>7}{'p.rec':>7}{'peds':>6}{'s/img':>7}{'peakMB':>8}   paired dMAE vs base")
for k, d in data.items():
    if not d: print(k, "no results yet"); continue
    cars = [r["counts"]["cars_4wheel"] for r in d.values()]; gt = [r["gt"]["cars_4wheel"] for r in d.values()]
    err = [c - g for c, g in zip(cars, gt)]
    sec = [r.get("seconds") for r in d.values() if r.get("seconds")]
    root = roots[k]; pk = [json.loads((root / "prompt_only" / f"{c}.json").read_text())["peak_gpu_mb"] for c in d]
    pair = ""
    if k != "base 1024x576 canny1.0":
        common = [c for c in d if c in base]
        m, lo, hi = boot([abs(d[c]["counts"]["cars_4wheel"] - d[c]["gt"]["cars_4wheel"]) - abs(base[c]["counts"]["cars_4wheel"] - base[c]["gt"]["cars_4wheel"]) for c in common])
        pair = f"{m:+.2f} [{lo:+.2f},{hi:+.2f}]"
    f = lambda key: statistics.fmean(r[key] for r in d.values() if r.get(key) is not None)
    print(f"{k:32}{len(d):3}{statistics.fmean(cars):7.2f}{statistics.fmean(abs(e) for e in err):6.2f}{statistics.fmean(err):6.2f}{f('vehicle_recall'):7.2f}{f('vehicle_precision'):7.2f}{f('person_recall'):7.2f}{statistics.fmean(r['counts']['pedestrians'] for r in d.values()):6.2f}{statistics.fmean(sec) if sec else 0:7.1f}{max(pk):8.0f}   {pair}")
print("GT mean cars", statistics.fmean(r["gt"]["cars_4wheel"] for r in base.values()))
