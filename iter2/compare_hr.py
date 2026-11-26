import json, statistics, numpy as np
from pathlib import Path
CASES = [f"case{i}" for i in range(1, 113)]
roots = {"1024x576 (default)": Path("results/carla_v2"), "1280x704": Path("results/carla_v2_hr")}
def load(root):
    out = {}
    for c in CASES:
        f = root / "analysis" / "prompt_only" / f"{c}.json"
        if f.exists(): out[c] = json.loads(f.read_text())
    return out
data = {k: load(r) for k, r in roots.items()}
base = data["1024x576 (default)"]
def boot(d):
    d = np.array(d, float); rng = np.random.default_rng(0)
    b = rng.choice(d, size=(2000, len(d))).mean(axis=1); return float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
print(f"prompt_only, cases with results in both: {len(set(data['1280x704']) & set(base))}")
print(f"{'config':20}{'n':>4}{'cars':>7}{'MAE':>6}{'bias':>6}{'v.rec':>7}{'v.prec':>7}{'p.rec':>7}{'s/img':>7}   paired dMAE vs 1024x576 [95% CI]")
for k, d in data.items():
    if not d: print(k, "no results"); continue
    cars = [r["counts"]["cars_4wheel"] for r in d.values()]; gt = [r["gt"]["cars_4wheel"] for r in d.values()]; err = [c - g for c, g in zip(cars, gt)]
    pair = ""
    if k != "1024x576 (default)":
        common = [c for c in d if c in base]
        m, lo, hi = boot([abs(d[c]["counts"]["cars_4wheel"] - d[c]["gt"]["cars_4wheel"]) - abs(base[c]["counts"]["cars_4wheel"] - base[c]["gt"]["cars_4wheel"]) for c in common])
        pair = f"{m:+.2f} [{lo:+.2f},{hi:+.2f}]"
    f = lambda key: statistics.fmean(r[key] for r in d.values() if r.get(key) is not None)
    print(f"{k:20}{len(d):4}{statistics.fmean(cars):7.2f}{statistics.fmean(abs(e) for e in err):6.2f}{statistics.fmean(err):6.2f}{f('vehicle_recall'):7.2f}{f('vehicle_precision'):7.2f}{f('person_recall'):7.2f}{f('seconds'):7.1f}   {pair}")
