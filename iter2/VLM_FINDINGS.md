# VLM-judge evaluation (Damir's requirement), 13-14 Nov 2026

**Judge:** `gemma-4-31b-it` through the Gemini API. Prompts, score parsing and model are unchanged from Damir's `batch_evaluation.py` (`vlm_judge.py`).

**What is judged:** every pair is the original photo of the reference camera (cam1) and its reconstruction. Each pair gets two separate yes/no requests: are the car numbers preserved, and are the car positions preserved. Joint means both are yes.

**Coverage:** all 2,276 pairs over 26 setups. `VLM_JUDGE_REPORT.md` holds the full table with 95% intervals and every paired test. Raw answers are in `results/vlm/*.jsonl`.

## 0. Headline (14 Nov): Damir's method at its own settings, on our data

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

## 1. The judge is consistent

The original photo judged against itself scores 100% on both questions: 112 of 112 CARLA pairs and 61 of 61 real-world pairs. A "not preserved" verdict therefore reflects a real difference in the reconstruction, not noise from the judge.

## 2. Our implementation of the seed receiver does not reach the paper's figure, even on the paper's kind of data

| Cityscapes, 100 images (iteration 1, single camera, 2048x1024) | Numbers | Positions | Joint |
|---|---|---|---|
| Authors' settings (Cityscapes palette) | 44.0% | 77.0% | 41.0% [32-51] |
| Same with the ADE20K palette | 42.0% | 82.0% | 41.0% [32-51] |
| Seed paper, Table 6 (MMSD single camera) | 86.9-88.9% | 94.4-97.6% | 86.1-86.9% |

- With the same judge, our reproduction of the seed method scores 41%, not about 86%. The low scores on our own datasets are therefore not caused by those datasets.
- **Likely causes:** the receiver weights (Damir: the paper's ControlNet "is trained with a different palette", while we use the public `lllyasviel` ControlNets trained on ADE20K images), the judge version, or the evaluation images.
- **Why pairs fail:** in the judge's explanations, reconstructions both drop distant cars and invent new ones.

## 3. Our datasets (joint success; numbers preserved in brackets)

| Setup | CARLA v3 (112) | Real-world (61) |
|---|---|---|
| Current receiver: 1024x576, Cityscapes palette, all cameras' captions | 36.6% (36.6) | 27.9% (27.9) |
| Same, reference camera only | 33.0% (33.9) | 26.2% (26.2) |
| Working resolution only (896x512, edges at that size) | 37.5% (39.3) | 44.3% (44.3) |
| ADE20K palette only | 37.5% (38.4) | 29.5% (29.5) |
| Both of Damir's fixes | 43.8% (46.4) | 45.9% (47.5) |
| Both fixes, reference camera only | 46.4% (49.1) | 54.1% (54.1) |
| ControlNet canny 0.7 / seg 1.5 only | 49.1% (50.9) | 34.4% (34.4) |
| Both fixes + canny 0.7 / seg 1.5 | 43.8% (43.8) | 50.8% (50.8) |
| **Both fixes + canny 0.7 / seg 1.5, reference camera only** | **52.7% (55.4)** | **57.4% (57.4)** |

Positions are preserved in 87-97% of the pairs in every setup, close to the paper. The failures are almost all about car numbers.

## 4. What changes the score (paired tests on the joint score, McNemar)

| Change | CARLA v3 | Real-world |
|---|---|---|
| Both fixes vs current receiver | +7.1 pts (p = 0.27) | **+18.0 pts (p = 0.019)** |
| Working resolution alone | +0.9 pts (p = 1.0) | **+16.4 pts (p = 0.031)** |
| ADE20K palette alone | +0.9 pts (p = 1.0) | +1.6 pts (p = 1.0) |
| Canny 0.7 / seg 1.5 alone | **+12.5 pts (p = 0.016)** | +6.6 pts (p = 0.34) |
| Canny 0.7 / seg 1.5 on top of both fixes | +0.0 pts | +4.9 pts (p = 0.63) |
| All cameras' captions vs reference camera only, current receiver | +3.6 pts (p = 0.59) | +1.6 pts (p = 1.0) |
| Same, with both fixes | -2.7 pts (p = 0.74) | -8.2 pts (p = 0.18) |
| Same, with both fixes + canny 0.7 / seg 1.5 | -8.9 pts (p = 0.16) | -6.6 pts (p = 0.50) |

- **Damir's resolution point is what matters on real photos** (+16 to +18 points). On CARLA, the ControlNet strengths matter instead (+12.5).
- **The palette point changes nothing** on any dataset, including Cityscapes.
- **Multi-camera captions never help in this metric.** With the fixes, the reference camera alone tends to score higher, though no difference is significant. The current receiver uses the other cameras only through their captions; under the judge, that brings no benefit.

## 5. Payload

Per camera photo (`PAYLOAD_SIZES.md`):
- The working-resolution payload is 20.8 KB on CARLA and 16.3 KB on real-world, against 56.2 KB and 50.7 KB for the current one.
- That is 3.9-4.3% of the photo saved as JPEG at quality 90.
- The edge map is most of it: 91% of the current payload.

## 6. Open questions for Damir

1. Which ControlNet weights did the paper use: the public ones, or ones the authors trained (and on which palette)? Can we use them?
2. Which judge model and version produced Table 6, and on which images?
3. Could he share about 50 of the paper's own original/reconstruction pairs? If our judge gives them about 86%, the judge matches and the receiver is the gap. If not, the judge differs.

Until these are answered, the 80-85% target cannot be compared like for like. On our data, Damir's method at its own settings reaches 56% (CARLA) and 75% (real-world) joint; our multi-camera captions at the same settings reach 50% and 74%, and in no setting do they beat the reference camera alone.
