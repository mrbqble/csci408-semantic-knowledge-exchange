from pathlib import Path
p = Path("VLM_FINDINGS.md"); t = p.read_text(encoding="utf-8")
anchor = "## Update 19 Nov: Damir's multi-camera fusion beats his single-camera MMSD"
assert t.count(anchor) == 1
new = """## Update 21 Nov: full-resolution supporting reconstructions and parameter tuning (Damir's answers of 19 Nov)

**Supporting-reconstruction resolution.** Fusion at strength 0.5 and IP scale 1.0, all cases:

| Joint success | Real-world (61) | CARLA (112) | Both (173) |
|---|---|---|---|
| Single-camera MMSD | 75.4% | 56.2% | 109 |
| Fusion, supports at 896x512 | 80.3% | **69.6%** | **127** |
| Fusion, supports at full resolution (paper settings) | **85.2%** | 59.8% | 119 |
| Full resolution vs 896x512 (McNemar) | +4.9 pts (5 / 2, p = 0.45) | -9.8 pts (11 / 22, p = 0.080) | |

- **Full-resolution supports help on real photos and hurt on CARLA.** Over both datasets, the 896x512 supports are better, and they cost about 9 times less GPU time per supporting view (about 8 s against 74 s).
- **The number of views does not explain it.** On CARLA, split by camera count, the full-resolution penalty is -6, -1, -1 and -3 joint successes for 2, 3, 4 and 5 supporting views. The largest penalty comes with 2 supporting views, the same count as real-world, where full resolution helps. The difference is between the datasets, synthetic against real; we cannot separate the reasons with these two datasets.

**Parameter tuning** (`TUNING_RESULTS.md`, `tune_select.py`). The rule was fixed in advance: pick the setting on a tuning half (CARLA 1-56 plus the first 30 real-world cases), then report it on the held-out half.

| Setting (full-resolution supports) | strength 0.5, IP 1.0 | strength 0.3 | strength 0.4 | strength 0.6 | IP 0.5 | IP 0.75 |
|---|---|---|---|---|---|---|
| Joint successes, tuning half (85 cases) | 61 | 56 | **62** | 61 | 58 | 61 |

- **The winner by the rule is strength 0.4, by a single case.** On the held-out half it does not hold up: +3.6 pts on CARLA (8 / 6, p = 0.79) and -16.1 pts on real-world (1 / 6, p = 0.13) against strength 0.5.
- **Strength 0.4-0.6 and IP scale 0.75-1.0 perform alike;** only strength 0.3 and IP scale 0.5 are clearly lower. Damir's values, strength 0.5 and IP scale 1.0, sit in a flat optimum, so we keep them.

**Recommended configuration for the final report:** Damir's fusion at strength 0.5 and IP scale 1.0, with supporting reconstructions at 896x512 (127 of 173 joint successes, against 109 for the single-camera MMSD). Full-resolution supports are reported as an ablation, because they are the best option on real photos.

"""
t = t.replace(anchor, new + anchor)
t = t.replace("# VLM-judge evaluation (Damir's requirement), 13-19 Nov 2026\n", "# VLM-judge evaluation (Damir's requirement), 13-21 Nov 2026\n")
p.write_text(t, encoding="utf-8"); print("findings updated")
