# prompt_refine: redrawing small cars at 4x

`prompt_refine` takes the `prompt_only` master view, finds the small vehicles in Rec1's received segmentation map (blob area >= 12 px, box side <= 48 px), groups them into at most 8 windows of 128x128 px, redraws each window 4x upscaled with Stable Diffusion 1.5 + the same two ControlNets in img2img mode (strength 0.5, 20 steps, guidance 7.5, seed 42 + window index, fixed prompt "cars on a city street, realistic photo, sharp"), downscales it and pastes it back with a feathered mask.

**The 20 images were chosen because they contain many small cars, which favours the method.** 10 CARLA v3 cases (112, 106, 69, 91, 88, 42, 52, 59, 89, 101) and 10 real-world cases (25, 7, 19, 1, 13, 235, 241, 217, 223, 277). They are not a random sample, so the numbers say what the method can do where it should help, not what it does on average.

## Results

Recall and precision are against the detector on the original photo (`oracle_gen`), Hungarian matching at IoU >= 0.5, pooled over the 10 cases of each dataset. Bins are by the side length of the oracle box in the 1024x576 master view. Cars MAE is against the manifest ground truth (cars, trucks, buses visible from Rec1); real-world has no ground truth. s/img is generation time for the whole master view (for `prompt_refine`: `prompt_only` time plus refinement).

| dataset | variant | vehicle recall <24 px | 24-48 px | 48-120 px | >120 px | vehicle recall all | vehicle precision | cars MAE vs GT | s/img |
|---|---|---|---|---|---|---|---|---|---|
| CARLA v3 | prompt_only | 0.14 | 0.35 | 0.77 | 1.00 | 0.43 | 0.67 | 5.30 | 10.7 |
| CARLA v3 | prompt_refine | 0.14 | 0.40 | 0.80 | 1.00 | 0.47 | 0.64 | 4.00 | 17.0 |
| Real-world | prompt_only | 0.32 | 0.29 | 0.88 | 1.00 | 0.49 | 0.73 | - | 10.5 |
| Real-world | prompt_refine | 0.40 | 0.31 | 0.90 | 1.00 | 0.53 | 0.75 | - | 13.6 |

- CARLA v3: oracle vehicles per bin <24 px n=22, 24-48 px n=72, 48-120 px n=30, >120 px n=5; 129 in total, `prompt_only` returns 83 vehicle boxes, `prompt_refine` 96.
- Real-world: oracle vehicles per bin <24 px n=50, 24-48 px n=90, 48-120 px n=49, >120 px n=16; 205 in total, `prompt_only` returns 138 vehicle boxes, `prompt_refine` 144.

## Paired change, `prompt_refine` minus `prompt_only` (per-case recall, 95% bootstrap CI over cases)

| subset | all vehicles | vehicles < 48 px |
|---|---|---|
| CARLA v3 | +0.036 (95% CI -0.017 to +0.096; n=10; CI crosses zero) | +0.044 (95% CI -0.011 to +0.115; n=10; CI crosses zero) |
| Real-world | +0.030 (95% CI +0.009 to +0.058; n=10; CI above zero) | +0.036 (95% CI +0.000 to +0.076; n=10; CI crosses zero) |
| both datasets | +0.033 (95% CI +0.003 to +0.068; n=20; CI above zero) | +0.040 (95% CI +0.006 to +0.082; n=20; CI above zero) |

Per-case recall is matched oracle vehicles over oracle vehicles in the case (cases without oracle vehicles in the subset are dropped). With 10 cases per dataset the intervals are wide.

## What the refinement did

| dataset | cases | small blobs found (per case) | windows (per case) | blobs not covered by the 8 windows | window failures | refinement s/img |
|---|---|---|---|---|---|---|
| CARLA v3 | 10 | 4.3 | 2.8 | 0 | 0 | 6.3 |
| Real-world | 10 | 2.5 | 1.4 | 0 | 0 | 3.1 |

Window failures: none.

## Side by side

- CARLA v3, case 112 (the first case in the list with a refined window; not picked for its effect): `refine_figures\refine_carla_v3.jpg`
- Real-world, case 25 (the first case in the list with a refined window; not picked for its effect): `refine_figures\refine_real_world.jpg`

Top row: original photo, `prompt_only`, `prompt_refine` at 1024x576 with the first window outlined in yellow; bottom row: that 128x128 window shown 4x.

## Conclusion

- **The gain is small and not established.** Pooled over the 20 images, vehicle recall rises by +0.033 (95% CI +0.003 to +0.068) and recall for vehicles under 48 px by +0.040 (+0.006 to +0.082), but the lower bounds are barely above zero, six intervals were examined without correction, and the images were chosen to favour the method. Per dataset the CARLA v3 intervals cross zero (+0.036, -0.017 to +0.096), and only the real-world all-vehicle interval excludes it.
- **Where it moves:** 24-48 px vehicles in CARLA (0.35 to 0.40) and <24 px vehicles in the real-world cases (0.32 to 0.40); CARLA <24 px stays at 0.14. After refinement no size bin gets above 0.40 for vehicles under 48 px, so most small vehicles are still lost.
- **Cost:** precision falls on CARLA (0.67 to 0.64: 13 more boxes returned for about 5 more matches) and rises slightly on real-world (0.73 to 0.75); +6.3 s per image on CARLA, +3.1 s on real-world. The CARLA cars MAE drop (5.30 to 4.00) is descriptive only: 10 cases, no test.
- **Coverage:** the blob rule found about 4.3 (CARLA) and 2.5 (real-world) small blobs per case, 43 and 25 blobs against 94 and 140 small vehicles in the detector's view, so merged blobs are never addressed; two real-world cases (1, 19) had no small blob and were unchanged. In the CARLA figure (case 112) the small background vehicles inside the window are missing in both versions and the visible change is a smoother large car; in the real-world figure (case 25) the refined window shows smoother, more car-shaped vehicles than the high-contrast blobs of `prompt_only`.
- **A fair test** needs random cases: all 112 CARLA v3 and 61 real-world cases would add about 15 minutes of refinement on top of the stored base images.
