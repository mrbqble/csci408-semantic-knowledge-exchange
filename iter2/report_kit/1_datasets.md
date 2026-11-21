# 1. Datasets

All evaluation uses the main camera, cam1, of each case. A case is one moment seen by several cameras at once.

## 1.1 Overview

| Dataset | Used for | Cases | Cameras per case | Photos | Resolution |
|---|---|---|---|---|---|
| **CARLA v3** (`carla_dataset_v3_ids`) | Main simulated evaluation | 112 | 3, 4, 5 or 6 (28 cases each) | 504 | 1920x1080 JPEG |
| **Real-world Astana** (`real_world_astana_3phones_sync_v1`) | Main real-world evaluation | 61 evaluated, from 366 synchronised triplets | 3 phones | 183 evaluated (1,098 in all triplets) | 1920x1080 PNG |
| **Cityscapes** (validation split) | Checking our reproduction of the seed paper on its own kind of data | 100 | 1 | 100 | 2048x1024 PNG |
| CARLA v2 (`carla_dataset_v2_low2m_3to6cams_hd`) | October pilot runs (detector era) | 112 | 3-6 | 504 | 1920x1080 |
| CARLA v4 (`carla_dataset_v4_train`) | Prepared as training data; not used, since training was put on hold | 224 | 3-6 | about 1,000 | 1920x1080 |

## 1.2 CARLA v3: simulated junctions

- **Simulator:** CARLA 0.9.16 (Unreal Engine 4), map Town10HD_Opt. Generator: `../carla/generate_cases_v3.py`, seed 21. Cases 23 and 72 failed and were regenerated with seed 25 at another junction.
- **A case:** 3-6 cameras placed around one junction, all capturing the same simulation tick, under varied weather (e.g. CloudyNoon, SoftRainNoon, WetCloudySunset).
- **Per camera:** the photo (`caseK/camJ.jpg`) plus the ground-truth objects visible to it: id, kind, visible pixels, depth, bounding box and world position. There are 13,975 objects across the dataset. `manifest.json` lists every case with its number of cameras, weather and object counts.
- **Ground truth:** used for the detector-era metrics in October. The VLM judge does not use it; it compares images.

**Where:**
- Team Drive: `uni/04/01/CSCI 408/Senior Project Work/Datasets/Simulated/carla_dataset_v3_ids/`, grouped as `3_cameras` ... `6_cameras`, with a README describing the fields.
- OMEN: `C:\carla_multicam_kit\output\carla_dataset_v3_ids`.

## 1.3 Real-world Astana: three phones

- **Recording:** three phones filmed the same road scenes in Astana: cam1 iPhone 16 Pro Max (main), cam2 Android, cam3 iPhone 16 Pro. There were 3 takes and 7,883 frames at 1920x1080.
- **Synchronisation:** by the audio track, accurate to about 0.1-0.25 s. That yields 366 core cases where all three phones are synchronised (`core/caseK/cam1.png ... cam3.png`).
- **Evaluation subset:** 61 cases, every 6th core case (case 1, 7, 13, ..., 361). Consecutive core cases are near-duplicate frames, and every 6th keeps the set diverse.
- **Scenes:** dense, with about 11.5 cars per main-camera photo on average (the October detector count on the originals) and up to about 20, many of them parked and distant. That makes "same number of cars" a strict test.
- **Privacy:** faces and licence plates are visible. For the course report and internal use only.

**Where:**
- Team Drive: `.../Datasets/Real-world/real_world_astana_3phones_sync_v1/`, with `cases_1to3phones` grouped by camera count and a copy of the core triplets in `core_synced_triplets_v1`.
- OMEN: `C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core`.

## 1.4 Cityscapes: the seed paper's kind of data

- **Images:** 100 validation images, every 5th of the 500. The list is in `../../iter1/results/iteration1_palette_eval_100.json`.
- **Single camera only.** Used to check whether our implementation of the seed paper reproduces its VLM-judge figure.
- **Licence:** Cityscapes requires registration and may not be redistributed, so the images are not in the repo or on the Drive.

**Where on the OMEN:**
- `iter1/data/cityscapes_val`.
- `iter2/data/cs_cases/caseK/cam1.png`: hard links in our case layout; `mapping.json` maps case to image.

## 1.5 Splits used for tuning

Strength and IP-Adapter scale were chosen on a tuning half and reported on a held-out half (`../tune_select.py`):

| Half | CARLA v3 | Real-world |
|---|---|---|
| Tuning | cases 1-56 | the first 30 of the 61 (cases 1-175) |
| Held-out | cases 57-112 | the last 31 (cases 181-361) |

## 1.6 Derived data on the OMEN (not in git, rebuildable with `2_pipeline.md`)

| Folder (`iter2/`) | Content |
|---|---|
| `data/v3_payloads`, `data/rw_core_payloads` | Payloads at the seed paper's settings: segmentation map at half resolution (1024x576), edge map at full resolution, caption |
| `data/v3_native`, `data/rw_native` | Payloads at 896x512 (map and edges at that size); used for the 896x512 supporting reconstructions |
| `data/cs_payloads` | Cityscapes payloads with the segmenter at full size (1024x2048) |
| `results/<set>_paper/k1/caseK_camJ.png` | Single-camera reconstruction of every camera at the paper's settings (1920x1088) |
| `results/<set>_support/k1/` | Single-camera reconstructions at 896x512 (the recommended supports) |
| `results/<set>_fuse/{fuse,fuse_noip}/` | Damir's fusion with 896x512 supports, and its no-IP-Adapter control |
| `results/<set>_fuseF_st*/` | Fusion with full-resolution supports, and the tuning variants |
| `results/vlm/*.jsonl` | Every judge answer, with its full text (**in git**) |

`<set>` is `v3` (CARLA) or `rw` (real-world).
