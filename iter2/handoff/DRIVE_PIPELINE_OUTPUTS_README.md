# Pipeline Outputs (CSCI 408, Group 22)

Saved results of every step of the pipeline, copied from the HP OMEN laptop on 22 Nov 2026.
- **Code** that produced them: GitHub `mrbqble/csci408-semantic-knowledge-exchange`, branch `iter2-multicam`.
- **Documentation:** `iter2/report_kit/` and `iter2/handoff/00_START_HERE.md` in the repository.
- **Judge answers** (text): in the repository at `iter2/results/vlm/`. They are also included under `iteration2/results/vlm/` here.

## Kept on the OMEN laptop only (Drive storage quota, 22 Nov 2026)

The Drive ran out of space, so these outputs were removed from the Drive and stay on the laptop, next to the code that produced them (`C:\Users\mrbqble\Desktop\csci408-probe\`).
- They can be regenerated with the repository code.
- Their numbers (judge answers, per-image JSON, CSV) are in GitHub.

| Removed from the Drive | Where it stays on the laptop |
|---|---|
| `iteration1/` (results, payloads, authors' code check) | `iter1/results`, `iter1/data/components_*`, `iter1/authors_check` |
| `iteration2/training_crops.zip` | `iter2/_scratch/training_crops.zip` |
| Full-resolution supports and tuning: `<set>_fuseF_st0.3/0.4/0.5/0.6` | `iter2/results/` |
| Earlier judged receivers: `v3`, `rw_core`, `*_native_ade`, `*_native_cs`, `*_ade`, `*_native_ade_cn`, `*_cn07_15`, `cs_paper` | `iter2/results/` |
| Detector-era experiments: `carla_v2*`, `pilot_*`, `hp`, `tune_c*`, `refine`, `v3_2048`, `geofuse_*`, `v3_geofuse`, `*smoke*` | `iter2/results/` |

Still on the Drive: the main results (`<set>_paper`, `<set>_support`, `<set>_fuse`), all payloads, the fusion demo, the judge answers and the report zips.

## Layout

| Folder | Pipeline step | Repository equivalent |
|---|---|---|
| `iteration1/results/` | Iteration 1 (Oct): our reproduction of the seed paper's receiver on 100 Cityscapes images (`palette100`: authors' settings and ADE20K palette, 2048x1024), receiver smoke tests | `iter1/results/` |
| `iteration1/payloads/` | Iteration 1 payloads (segmentation map, edge map, caption) of the Cityscapes images. **Raw Cityscapes images are not included** (licence) | `iter1/data/components_*` |
| `iteration2/payloads/` | Step 1, sender: one payload per camera photo | `iter2/data/` |
| `iteration2/results/` | Steps 2-4, receiver: reconstructions, fusion, controls, evaluation outputs | `iter2/results/` |
| `iteration2/training_crops.zip` | Training data prepared for possible ControlNet fine-tuning (not used; training on hold) | `iter2/data/train_crops/` |
| `iteration2/fusion_demo/` | Damir's pipeline on one real-world and one CARLA case, every intermediate image (PNG) | `iter2/fusion_demo/` |
| `reports/` | Zips sent to the team: report hand-off package (22 Nov), report kit (21 Nov), results pack (19 Nov) | `iter2/report_kit/`, `iter2/handoff/` |

## Payload folders (`iteration2/payloads/`)

Each case folder holds `camJ_seg.webp`, `camJ_edge.webp`, `camJ_caption.txt` and `camJ_meta.json` (sizes, timings).

| Folder | Dataset | Settings |
|---|---|---|
| `v3_payloads` | CARLA v3, 112 cases | Seed paper's payload: map at half resolution (1024x576), edges at full resolution |
| `v3_native` | CARLA v3 | 896x512 payload (map and edges at 896x512) |
| `rw_core_payloads` | Real-world, the 61 evaluated cases | Seed paper's payload |
| `rw_core_all_payloads` | Real-world, all 366 core cases | Seed paper's payload |
| `rw_native` | Real-world, 61 cases | 896x512 payload |
| `carla_v2_payloads`, `v4_payloads`, `v3_smoke_payloads` | CARLA v2, v4, smoke test | Seed paper's payload |
| `cs_payloads` | Cityscapes, 100 images | Segmenter at full size (1024x2048) |

## Result folders (`iteration2/results/`), the important ones

`<set>` is `v3` (CARLA v3) or `rw` (real-world). PNG images come with one JSON each (settings, seconds).

| Folder | What it is |
|---|---|
| `<set>_paper/k1/caseK_camJ.png` | Single-camera reconstruction of **every** camera at the paper's settings (1920x1088). cam1 = the single-camera MMSD baseline |
| `<set>_paper/prompt_only/` | Multi-camera, captions only (paper settings) |
| `<set>_support/k1/` | Single-camera reconstructions at 896x512 (supporting views in the final configuration) |
| `<set>_fuse/fuse/` | **Damir's fusion, final configuration** (strength 0.5, IP scale 1.0, 896x512 supports) |
| `<set>_fuse/fuse_noip/` | Control: the same img2img pass without the IP-Adapter |
| `<set>_fuseF_st0.5/fuse/` | Fusion with full-resolution supports (ablation) |
| `<set>_fuseF_st0.3`, `_st0.4`, `_st0.6`, `_st0.5/fuse_s0.5`, `fuse_s0.75` | Tuning of strength and IP-Adapter scale |
| `v3`, `rw_core` | The first receiver (1024x576, Oct-Nov) |
| `v3_native_ade`, `rw_native_ade`, `*_native_cs`, `*_ade`, `*_native_ade_cn` | Damir's two receiver fixes (working resolution, ADE20K palette) and combinations |
| `cs_paper` | Cityscapes rerun with the full-size segmenter |
| `v3_cn07_15`, `rw_cn07_15` | ControlNet scales canny 0.7 / seg 1.5 (1024x576) |
| `carla_v2`, `carla_v2_hr`, `pilot_cs`, `pilot_ade`, `hp`, `tune_c*`, `refine`, `v3_2048`, `geofuse_*`, `v3_geofuse`, `smoke`, `v3_smoke*` | October-November experiments evaluated with an object detector (CARLA v2 pilot, hyperparameter sweeps, window refinement, 2048x1152 generation, ground-plane fusion); superseded by the VLM judge |
| `vlm/` | VLM-judge answers, one `.jsonl` per setup (same files as in the repository) |

## Notes

- **Real-world images** show faces and licence plates: internal use only.
- **Cityscapes:** only derived outputs (payloads, reconstructions) are here, not the original images.
- **Real-world `core` case numbers** used in the evaluation are mapped to the dataset files in `Materials/Datasets/Real-world/V1/core_to_cases_1to3phones.csv`.
