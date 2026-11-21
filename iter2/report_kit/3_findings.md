# 3. Findings

All numbers are joint success under the VLM judge unless stated otherwise: car numbers and car positions both preserved in the main camera's view. CARLA means CARLA v3 (112 cases); real-world means Astana (61 cases). The source tables are `tables/all_setups.csv` and `tables/paired_tests.csv`.

## 3.1 How the work went

| Period | What happened |
|---|---|
| Iteration 1 (Oct) | We reproduced the seed paper's sender and receiver on Cityscapes. Pitfall found: `transformers` silently squashes every image to 384x384 before segmenting, which costs about 19 mIoU points (62.6 vs 82.0), so the sender's segmenter input is fixed at 512x1024. |
| Iteration 2, detector era (Oct to 11 Nov) | We built the multi-camera datasets (CARLA v2/v3/v4, real-world Astana) and the first multi-camera receiver, which added the other cameras' captions. Evaluation was per-car recall from an object detector. |
| VLM judge (12-15 Nov) | Damir made the VLM judge the required metric. We judged every receiver variant, Damir's two receiver fixes, and the seed paper's method at its own settings. |
| Damir's fusion (17-19 Nov) | We implemented Damir's architecture: reconstruct every camera, then refine the main one with img2img plus an IP-Adapter on the others. It is the first multi-camera receiver that beats the single camera. |
| Ablations (19-21 Nov) | Full-resolution supporting reconstructions, and tuning of strength and IP-Adapter scale (Damir's requests). |

**Lessons from the detector era** (numbers superseded; qualitative points still hold):
- Small and distant cars are mostly lost during **generation**, not in the payload. On CARLA v2 the segmentation map contained 96% of the vehicles a detector finds on the original photo.
- Adding a sender-side vehicle list (Faster R-CNN, 68 B per photo) raised recall a lot. Damir decided (11-12 Nov) to keep the seed paper's three-element payload, so it was dropped.
- The first captions-only multi-camera receiver gained a little, but a control with shuffled captions gained as much. That was the first sign that captions carry little scene-specific information.

## 3.2 Judge calibration and the seed paper's figure

- **The judge is consistent.** The original photo judged against itself scores 100% on CARLA (112 of 112) and on real-world (61 of 61).
- **Our implementation of the seed paper scores 41.0%** on 100 Cityscapes images, against the paper's 86.1-86.9% (Table 6). The figure does not change with the ADE20K palette (41.0%) or with the segmenter at full size (41.0%).
- **Damir's explanation:** the paper used an older Gemma judge that is no longer available. Our numbers therefore cannot be compared with the paper's in absolute terms. Every comparison below is made under the same judge, on the same cases.

## 3.3 Single-camera and captions-only receivers

| Receiver | CARLA | Real-world |
|---|---|---|
| First receiver: 1024x576, Cityscapes palette, all captions | 36.6% | 27.9% |
| + working resolution only (896x512, edges at that size; Damir's point 1) | 37.5% | 44.3% |
| + ADE20K palette only (Damir's point 2) | 37.5% | 29.5% |
| + both fixes | 43.8% | 45.9% |
| **Seed paper's settings** (photo resolution 1920x1088), single camera | **56.2%** | **75.4%** |
| Seed paper's settings, captions of all cameras | 50.0% | 73.8% |

- **Generation at the photo's own resolution, as the paper does, is the best single-camera setting.**
- **Working resolution** helps over 1024x576 on real photos (+16.4 points, p = 0.031) but stays well below the paper's settings.
- **A likely reason 1024x576 fails** (not isolated): the full-resolution edge map is squeezed to half size, so its lines crowd into hatching.
- **The ADE20K palette changes nothing** (+0.9 points on CARLA, +1.6 on real-world, both p = 1.0).
- **Captions from the other cameras never help:** -6.2 points on CARLA (p = 0.30), -1.6 on real-world (p = 1.0).
- **Positions are preserved in 87-97% of pairs in every setting.** The failures are almost all about car numbers: distant cars dropped or invented.

## 3.4 Main result: Damir's fusion

| Receiver | CARLA (numbers / positions / joint) | Real-world (numbers / positions / joint) |
|---|---|---|
| Single-camera MMSD (paper settings) | 57.1 / 88.4 / 56.2% | 77.0 / 95.1 / 75.4% |
| Control: img2img second pass, no IP-Adapter | 63.4 / 92.9 / 61.6% | 63.9 / 93.4 / 63.9% |
| **Damir's fusion, supports 896x512** | 69.6 / 93.8 / **69.6%** | 80.3 / 96.7 / **80.3%** |

| Paired test (McNemar, joint) | CARLA | Real-world |
|---|---|---|
| Fusion vs single-camera MMSD | **+13.4 pts** (31 better / 16 worse, p = 0.040) | +4.9 pts (7 / 4, p = 0.55) |
| Fusion vs control (what the other cameras add) | +8.0 pts (21 / 12, p = 0.16) | **+16.4 pts** (13 / 3, p = 0.021) |
| Control vs single camera (the second pass alone) | +5.4 pts (19 / 13, p = 0.38) | -11.5 pts (4 / 11, p = 0.12) |
| Fusion vs captions-only multi-camera | **+19.6 pts** (35 / 13, p = 0.002) | +6.6 pts (12 / 8, p = 0.50) |

- **The first multi-camera receiver that beats the single camera under the judge.** The gain is significant on CARLA and points the same way on real-world.
- **The other cameras' views always help.** On real-world, the second pass alone loses cars, and the IP-Adapter with the other views more than recovers them.
- **Trade-off.** On CARLA the fusion fixes 31 of the 49 cases the single camera fails and breaks 16 of the 63 it passes. On real-world it fixes 7 of 15 and breaks 4 of 46.

## 3.5 Ablations

**Supporting-reconstruction resolution** (fusion at strength 0.5, IP scale 1.0):

| Supports | CARLA | Real-world | Both (joint successes out of 173) |
|---|---|---|---|
| 896x512 (recommended) | **69.6%** | 80.3% | **127** |
| Full resolution, paper settings | 59.8% | **85.2%** | 119 |

- **Full resolution helps on real photos** (+4.9 points, p = 0.45) **and hurts on CARLA** (-9.8 points, p = 0.080).
- **The number of views does not explain it.** On CARLA, split by camera count, the penalty is -6, -1, -1 and -3 joint successes for 2, 3, 4 and 5 supporting views. The largest penalty is at 2 supporting views, as on real-world, where full resolution helps. The split follows the dataset (synthetic against real); two datasets cannot tell us why (`fig05`).

**Tuning** (full-resolution supports; rule fixed in advance: choose on the tuning half, report on the held-out half):

| Setting | Strength 0.5, IP 1.0 | Strength 0.3 | Strength 0.4 | Strength 0.6 | IP 0.5 | IP 0.75 |
|---|---|---|---|---|---|---|
| Joint successes, tuning half (85 cases) | 61 | 56 | 62 | 61 | 58 | 61 |

- **Strength 0.4 wins the tuning half by one case but does not hold on the held-out half:** CARLA +3.6 points (p = 0.79), real-world -16.1 (p = 0.13).
- **The optimum is flat** between strength 0.4 and 0.6 and IP scale 0.75 and 1.0, so Damir's values stay.

## 3.6 Payload size

| Per camera photo | Segmentation map | Edge map | Caption | Total | Share of a JPEG (q90) |
|---|---|---|---|---|---|
| CARLA, paper payload | 5.05 KB | 51.07 KB | 0.04 KB | 56.2 KB | 10.6% |
| Real-world, paper payload | 4.03 KB | 46.62 KB | 0.04 KB | 50.7 KB | 13.5% |
| CARLA, 896x512 payload | 4.36 KB | 16.44 KB | 0.04 KB | 20.8 KB | 3.9% |
| Real-world, 896x512 payload | 3.48 KB | 12.73 KB | 0.04 KB | 16.3 KB | 4.3% |

In the recommended configuration, the main camera's reconstruction uses the paper payload and the supporting reconstructions use the 896x512 payload. If the main camera were known in advance, supporting cameras could send the smaller payload. We did not test that as a deployment.

**Receiver compute** on the RTX 3070 laptop, for a 3-camera case: about 74 s for the main reconstruction, 2 x 8 s for the supporting ones and 39 s for the fusion pass, about 130 s in total, against 74 s for the single camera.

## 3.7 Limitations

1. **The judge.** Each pair was judged once by one model through a public API (`gemma-4-31b-it`). Its version may change and it differs from the paper's judge. The calibration (100% on identical images) shows it is consistent, not that it agrees with people.
2. **Strict criterion.** "Same number of cars" is strict in dense real-world scenes; one missed distant car fails a pair.
3. **Small real-world set.** With 61 cases, real-world differences under about 15 points are not significant.
4. **Two datasets only,** so the synthetic-vs-real difference in support resolution cannot be explained.
5. **Fixed main camera** (cam1). We did not study which camera to choose as main.
6. **No fine-tuning.** Training data was prepared (8,620 crops) but training was put on hold.

## 3.8 Recommended configuration for the report

Damir's fusion at strength 0.5 and IP-Adapter scale 1.0, with supporting reconstructions at 896x512:
- CARLA 69.6% against 56.2% for the single-camera MMSD (+13.4 points, p = 0.040);
- real-world 80.3% against 75.4%.

Full-resolution supports go in as an ablation (real-world 85.2%). The tuning shows the setting is robust.
