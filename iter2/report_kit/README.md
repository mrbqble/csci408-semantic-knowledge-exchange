# CSCI 408 Group 22: report kit (state of 21 Nov 2026)

**What this is:** everything needed to write the final report on the multi-camera semantic image exchange, with no need to rerun anything. It contains datasets, pipeline, evaluation, findings, figures and tables. Every number below comes from `tables/all_setups.csv` and `tables/paired_tests.csv`, which are generated directly from the VLM judge's raw answers (`../results/vlm/*.jsonl`) by `../make_report_kit.py`.

| File | Read it for |
|---|---|
| `1_datasets.md` | The four datasets: how they were made, structure, the case lists we evaluate on, where they are stored |
| `2_pipeline.md` | Sender, the three receivers, the VLM judge, statistics, code map, commands to reproduce |
| `3_findings.md` | What we found, in order, with numbers, limitations and what is superseded |
| `figures/` | Report-ready figures (list below) |
| `tables/` | CSV tables, the single source for numbers in the report |

## The project in five sentences

1. Several roadside cameras observe the same scene. Instead of photos, each sends a small semantic payload: a segmentation map, an edge map and a caption, about 16-56 KB against a 376-531 KB JPEG.
2. The seed paper (Assylbek et al., *Internet of Things* 39, 2026, "MMSD") reconstructs a single camera's view from its own payload with Stable Diffusion 1.5 and two ControlNets.
3. Our question is whether payloads from *other* cameras of the same scene can make the main camera's reconstruction more faithful.
4. The evaluation metric, required by Damir, is a VLM judge (Gemma 4, 31B). It compares the original and the reconstructed main-camera photo and answers yes/no to two questions: are the car numbers preserved, and are the car positions preserved. "Joint" means both are yes.
5. Damir's fusion pipeline is the first multi-camera receiver that beats the single-camera MMSD under this judge. It works by reconstructing every camera, then refining the main reconstruction (img2img) with the other reconstructions through an IP-Adapter.

## Numbers to cite (joint success, VLM judge)

| Receiver | CARLA v3 (112 cases) | Real-world Astana (61 cases) |
|---|---|---|
| Single-camera MMSD, the seed paper's method at its own settings | 56.2% | 75.4% |
| Multi-camera, other cameras' captions only (our earlier approach) | 50.0% | 73.8% |
| **Damir's fusion, supporting reconstructions at 896x512 (recommended)** | **69.6%** | **80.3%** |
| Damir's fusion, supporting reconstructions at full resolution (ablation) | 59.8% | 85.2% |
| Original photo judged against itself (judge calibration) | 100% | 100% |

- **Fusion (896x512 supports) vs single camera:** CARLA +13.4 points (31 cases better, 16 worse; McNemar p = 0.040); real-world +4.9 points (7 / 4, p = 0.55).
- **What the other cameras add,** measured as fusion vs the same pass without the IP-Adapter: CARLA +8.0 (p = 0.16), real-world +16.4 (p = 0.021).
- **Tuning:** strength 0.4-0.6 and IP-Adapter scale 0.75-1.0 perform alike. Damir's values (strength 0.5, scale 1.0) are kept.
- **Payload per camera:** 50.7-56.2 KB at the paper's settings, of which the edge map is about 91%. At 896x512 it is 16.3-20.8 KB.
- **Seed paper's own figure (86-87%):** not comparable. It was produced by an older Gemma judge that is no longer available. Our reproduction on the paper's Cityscapes images scores 41% with the current judge.

## Figures

| File | Shows | Suggested use in the report |
|---|---|---|
| `fig01_main_results.png` | Joint success of the five main receivers, both datasets, 95% intervals | Main result |
| `fig02_receiver_evolution.png` | How each receiver change moved the score | Narrative / iterations |
| `fig03_paired_tests.png` | All paired comparisons (McNemar) | Statistics / appendix |
| `fig04_tuning.png` | Strength and IP-Adapter scale tuning | Ablation |
| `fig05_support_resolution_by_cameras.png` | 896x512 vs full-resolution supports by number of cameras | Ablation |
| `fig06_payload_sizes.png` | Payload size per element | Communication cost |
| `fig07_pipeline_real_world_case1.jpg`, `fig08_pipeline_carla_case10.jpg` | The whole pipeline step by step on one case each | Method |
| `fig09`-`fig11` (examples) | Cases the fusion fixes and breaks (first cases by number, not hand-picked) | Qualitative results |

The real-world photos show faces and licence plates. Use them in the course report and internal slides only, not in anything public.

## Older documents

`../FINDINGS.md`, `../REPORT.md` and `../STATUS_2026-11-11.md` describe the October work, which was evaluated with an object detector. Damir asked us to drop detector-based evaluation (13 Nov), so their numbers are superseded by the VLM judge. Their qualitative lessons are summarised in `3_findings.md`. The most detailed running log of the VLM-judge work is `../VLM_FINDINGS.md`.

## Team

Bibol Assetbek, Yernur Kenzhaly, Zhengis Kosher, Temirshin Kantemirov. Adviser: Prof. Dimitrios Zorbas. Lab: Damir Assylbek, first author of the seed paper; he proposed the evaluation protocol and the fusion architecture.
