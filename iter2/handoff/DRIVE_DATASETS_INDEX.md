# Datasets (CSCI 408, Group 22): index

Updated 22 Nov 2026.
- **Dataset tools** (CARLA generators, real-world frame extraction and sync): GitHub `mrbqble/csci408-semantic-knowledge-exchange`, folders `carla/` and `tools/carla_multicam_kit/`.
- **How the datasets are used** in the project: `iter2/report_kit/1_datasets.md` in the repository.

| Folder | Content | Notes |
|---|---|---|
| `Simulated/carla_dataset_v1` | First CARLA prototype (107 files) | Early test |
| `Simulated/carla_dataset_v2_low2m_3to6cams_hd` | 112 cases, 3-6 cameras, 1920x1080, generator v2 (seed 11) | October pilot experiments |
| `Simulated/carla_dataset_v3_ids` | **112 cases** (28 each with 3, 4, 5 and 6 cameras), 1920x1080, ground-truth objects per camera, generator v3 (seed 21) | **Main simulated evaluation set.** README inside; grouped by camera count |
| `Simulated/carla_dataset_v4_train` | 224 cases, 3-6 cameras, generator v3 (seed 31) | Training data for possible fine-tuning (not used). Added 22 Nov |
| `Real-world/V1` | Astana, 3 phones (cam1 iPhone 16 Pro Max, cam2 Android, cam3 iPhone 16 Pro), takes 1-3. `cases_1to3phones` = synchronised cases grouped by how many phones are in sync; manifests (`frames.csv`, `slots.csv`, `cases_all_slots.csv`, `phone_sync_manifest.json`, `dataset_manifest.json`), README | **The evaluation's "core" cases** (366 three-phone triplets, of which every 6th, 61 in total, is evaluated) are byte-identical files inside `cases_1to3phones`. `core_to_cases_1to3phones.csv` maps every core case and camera to its file. Added 22 Nov |
| `Real-world/V1/_work`, `Real-world/V2/_work` | Thumbnails used for audio/visual phone synchronisation | Added 22 Nov |
| `Real-world/V2` | Second real-world capture (takes 4-8), same structure as V1 | Not used in the evaluation so far |
| `Real-world/Video` | Raw phone videos, one folder per recording session | Source of every real-world frame |
| `_development_tests` | Small generator and extraction smoke tests (CARLA and real-world) | Added 22 Nov; development history only |

**Not on the Drive:**
- **Cityscapes:** the licence forbids redistribution; download it from cityscapes-dataset.com. The 100 images used are listed in the repository: `iter1/results/iteration1_palette_eval_100.json`, and `iter2/report_kit/1_datasets.md`.
- **Extracted frames of every take** (`take1` ... `take7_8`, 58 GB on the laptop): reproducible from `Real-world/Video` with `extract_real_world.py` / `extract_real_world_v2.py`. Whether to upload them is pending a decision.

**Privacy:** the real-world data shows faces and licence plates. Internal use only.
