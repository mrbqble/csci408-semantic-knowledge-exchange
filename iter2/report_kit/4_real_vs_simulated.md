# 4. Why the real-world success rate is higher than on CARLA

Single-camera MMSD at the paper's settings scores **75.4%** joint on real-world photos and **56.2%** on CARLA v3. Damir's fusion scores **80.3%** and **69.6%**. The analysis below tests the obvious explanations first, using data we already had:
- a detector run on the original photos and on the reconstructions, used here as a **diagnostic only**, not as the evaluation metric;
- the judge's own wording;
- CARLA's weather metadata.

Script: `../real_vs_sim.py` plus the checks it summarises. Tables: `tables/real_vs_sim_*.csv`.

## 4.1 What does NOT explain it

| Hypothesis | Evidence | Verdict |
|---|---|---|
| Real-world scenes are easier (fewer, larger, separated cars) | Same detector on the original main-camera photos: real-world has **more** vehicles per photo (mean 11.7 vs 7.4; median 13 vs 7), **more** overlapping vehicles (63% vs 40%) and about the same share of small vehicles (20% vs 24%) | No. Real-world scenes are harder by every crowding measure |
| CARLA weather (rain, wet roads, sunset) | CARLA success by weather: clear noon 47%, wet noon 68%, soft rain 58%, cloudy 63%, sunsets 50%. There is no weather pattern | No |
| The judge is more lenient on real photos | Approximate wording ("about 12-13 cars") is equally common (18% vs 20% of answers) and comes with *lower* success, not higher. With the earlier 1024x576 receiver, the judge reacted the same way on both datasets to the same share of lost cars | No |

**What failures look like:** where the judge stated both counts, a failed count is almost always a **missing** car. The reconstruction had fewer cars in 18 of 20 such CARLA failures and 5 of 8 real-world ones.

## 4.2 What does explain it: at the photo's resolution, real-world reconstructions keep more cars

Share of the vehicles detected on the original photo that are still detected in the single-camera reconstruction (IoU >= 0.3; sizes relative to image height):

| Vehicles | CARLA, 1024x576 receiver | Real-world, 1024x576 | CARLA, paper settings (1920x1088) | Real-world, paper settings |
|---|---|---|---|---|
| All | 61.3% | 52.8% | 66.3% | **79.7%** |
| Grouped (overlapping another), medium size | 60.2% | 25.3% | 63.2% | **78.7%** |
| Small | 26.1% | 31.5% | 45.3% | **64.6%** |
| Large | 89.8% | 88.4% | 85.4% | 90.4% |

- **The ranking flips with resolution.** With the first 1024x576 receiver, real-world reconstructions lost *more* cars than CARLA and scored lower under the judge too: 26.2% vs 33.0% single-camera.
- **At the photo's own resolution the real-world rows are rescued.** Medium cars standing in rows went from 25% to 79% kept, and small cars from 32% to 65%. CARLA gained much less.
- **The score change follows the same pattern:** going from 1024x576 to paper settings is worth **+49 points** on real-world and **+23 points** on CARLA (judge, single camera).

**Why real-world benefits more: the edge map carries more information about real cars.** In the transmitted full-resolution edge maps, edge pixels make up **19.8%** of real-world vehicle areas, against **12.8%** for CARLA's rendered vehicles (7.8% vs 5.7% elsewhere in the image).
- Real cars have reflections, panel lines, wheels and textures. CARLA's rendered cars have smooth, simplified materials.
- At full resolution these outlines reach the edge ControlNet and pin each car down.
- At 1024x576 the dense outlines of cars in rows were squeezed into hatching, which is why real-world rows suffered most at that size.

**A likely contributing factor (not measured):** every model in the pipeline was trained on real photographs: Stable Diffusion 1.5, both ControlNets, Mask2Former (Cityscapes) and BLIP. CARLA renderings are outside their training distribution.

## 4.3 Caveats

- **Judge counting noise.** The judge counts the same original photo differently in different requests. Where both answers could be parsed, its stated count of the original differs between the baseline pair and the fusion pair in **28%** of CARLA cases and **59%** of real-world cases. Dense real-world scenes are counted least consistently.
  - Random noise of this kind produces wins and losses for both receivers. The paired McNemar test accounts for that, so the CARLA fusion gain (31 vs 16, p = 0.04) holds.
  - Single real-world differences should be read with care.
  - Repeated judging (several runs per pair, majority vote) would reduce this noise; it is a spring plan.
- **The detector is a diagnostic here.** It is the same detector on both datasets, used to explain the judge's results, not as the evaluation metric (Damir's protocol is the VLM judge).
- **The two datasets differ in more than realism.** The real-world set has 61 frames from three recordings of similar streets: rows of parked cars along a road, seen from the roadside. CARLA has 112 separate junction scenes with crossing traffic and pedestrians, in six weathers. Position failures are more common on CARLA (11.6% vs 4.9%), consistent with its more varied layouts.
