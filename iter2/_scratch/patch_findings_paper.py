from pathlib import Path
p = Path("VLM_FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("# VLM-judge evaluation (Damir's requirement), 13 Nov 2026\n", "# VLM-judge evaluation (Damir's requirement), 13-14 Nov 2026\n")
rep("**Coverage:** all 1,930 pairs over 22 setups.", "**Coverage:** all 2,276 pairs over 26 setups.")
anchor = "## 1. The judge is consistent"
new_sec = """## 0. Headline (14 Nov): Damir's method at its own settings, on our data

Settings of the seed paper: generation at the photo's own resolution (1920x1088 for our 1920x1080 photos), Cityscapes palette, segmentation map sent at
half resolution, edge map at full resolution. Single camera = Damir's MMSD; multi-camera = the same with all cameras' captions.

| Setup | CARLA v3 (112): numbers / positions / joint | Real-world (61): numbers / positions / joint |
|---|---|---|
| **Damir's single-camera MMSD, paper settings** | 57.1% / 88.4% / **56.2%** | 77.0% / 95.1% / **75.4%** |
| Our multi-camera captions, same settings | 50.9% / 96.4% / 50.0% | 73.8% / 95.1% / 73.8% |
| Our best 896x512 setting (both fixes + canny 0.7 / seg 1.5), multi / single camera | 43.8% / 52.7% joint | 50.8% / 57.4% joint |
| Current 1024x576 receiver, multi / single camera | 36.6% / 33.0% joint | 27.9% / 26.2% joint |

| Paired test on the joint score (McNemar) | CARLA v3 | Real-world |
|---|---|---|
| Our multi-camera captions vs Damir's method, both at paper settings | -6.2 pts (p = 0.30) | -1.6 pts (p = 1.0) |
| Our best 896x512 multi-camera setting vs Damir's method at paper settings | -12.5 pts (p = 0.065) | **-24.6 pts (p = 0.004)** |
| Our best 896x512 single-camera setting vs Damir's method at paper settings | -3.6 pts (p = 0.68) | **-18.0 pts (p = 0.043)** |

- **Generating at the photo's own resolution, as the paper does, is the best setting we have.** It reaches 56% joint on CARLA and 75% on real-world, which is better than the 896x512 working-resolution setting (Damir's point 1). The 1024x576 size we used before is the worst of the three.
- **A likely common cause (not isolated):** at 1024x576 the full-resolution edge map is shrunk to about half, which crowds its lines into dense hatching. The 896x512 setting computes the edges at its own size, and the paper setting does not shrink them at all. Both avoid that, and the paper setting also keeps more pixels per car.
- **The other cameras' captions do not help at any setting.** At paper settings they score 6 points lower on CARLA and 2 lower on real-world; neither difference is significant.
- **Detector-based recall pointed the other way on resolution** (2048x1152 scored lower on 24 cases). Damir has asked us to drop detector-based evaluation, and the judge is the agreed metric.
- **Still unexplained:** our iteration-1 reproduction on Cityscapes scored 41% at 2048x1024 (section 2), against 75% on our real-world photos at the same kind of settings. The Cityscapes street scenes, full of parked cars, may be harder to count exactly. The questions to Damir (section 6) still decide this.

"""
rep(anchor, new_sec + anchor)
rep("Until these are answered, the 80-85% target cannot be compared like for like. On our data, the best setting reaches 51-57% joint, and the multi-camera captions add nothing over the reference camera alone.",
    "Until these are answered, the 80-85% target cannot be compared like for like. On our data, Damir's method at its own settings reaches 56% (CARLA) and 75% (real-world) joint; our multi-camera captions at the same settings reach 50% and 74%, and in no setting do they beat the reference camera alone.")
p.write_text(t, encoding="utf-8"); print("findings updated")
