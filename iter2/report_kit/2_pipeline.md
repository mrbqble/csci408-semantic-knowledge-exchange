# 2. Pipeline

Code is in `iter2/` on branch `iter2-multicam` (PR #34). Machine: HP OMEN laptop, RTX 3070 8 GB, Python 3.14, torch 2.14 (CUDA 13.0), diffusers 0.41, transformers 5.17.

## 2.1 Sender (every camera)

`payloads.py` produces the seed paper's three-element payload for each camera photo:

| Element | Model / method | Sent as |
|---|---|---|
| Segmentation map | Mask2Former Swin-Large, Cityscapes semantic (`facebook/mask2former-swin-large-cityscapes-semantic`), input 512x1024 | Lossless WebP, Cityscapes colours, half resolution (1024x576 for 1920x1080 photos) |
| Edge map | Canny (thresholds 100 / 200) on the full-resolution photo | WebP, full resolution |
| Caption | BLIP base (`Salesforce/blip-image-captioning-base`) | UTF-8 text, about 40 bytes |

- **Size per camera photo** (`../PAYLOAD_SIZES.md`, `tables/payload_sizes_kb.csv`): 56.2 KB on CARLA and 50.7 KB on real-world. The edge map is about 91% of it.
- **The `--work-size 896x512` option** makes the map and edges at 896x512 instead: 20.8 KB and 16.3 KB.

## 2.2 Receivers

All receivers use Stable Diffusion 1.5 (`runwayml/stable-diffusion-v1-5`) with two ControlNets: `lllyasviel/sd-controlnet-canny` on the edge map and `lllyasviel/sd-controlnet-seg` on the segmentation map. The common settings are:
- UniPC scheduler, 20 steps, guidance 7.5, seed 42, ControlNet scales 1.0 / 1.0;
- generation at the photo's resolution, 1920x1088 (the nearest size Stable Diffusion accepts);
- the edge map is area-resampled to that size and thresholded at 40.

Code: `coordinator.py`; the variant names are in brackets.

**A. Single-camera MMSD, the seed paper's method (`k1`).** The main camera's own segmentation and edge maps go on the ControlNets, and its own caption is the prompt. This is the baseline.

**B. Multi-camera, captions only (`prompt_only`, our earlier approach).** As A, but the prompt is the global caption: the distinct captions of all cameras, main first, joined with commas. The other cameras contribute only text.

**C. Damir's fusion (`fuse`), from his diagram of 17 Nov 2026:**
1. Every camera is reconstructed from its own payload with A. Supporting cameras: at 896x512 from their 896x512 payload (recommended), or at full resolution (ablation).
2. The main camera's reconstruction is the starting image of an img2img pass (`StableDiffusionControlNetImg2ImgPipeline`) with **strength 0.5**: half the noise schedule is added, then denoised again.
3. In that pass:
   - the ControlNets get the main camera's segmentation and edge maps;
   - the **IP-Adapter** (`h94/IP-Adapter`, `ip-adapter_sd15.bin`, **scale 1.0**) gets the supporting cameras' reconstructions, combined as the mean of their CLIP image embeddings;
   - the prompt is the global caption.
4. **Control (`fuse_noip`):** the same pass without the IP-Adapter. It separates the effect of the other cameras from the effect of the second pass itself.

`fusion_demo.py --dataset rw --case 1` runs C for one case and saves every intermediate. The figures in `figures/fig07`, `fig08` and `../fusion_demo/` were made this way.

**Timing on the RTX 3070 laptop:**
- reconstruction at 1920x1088: about 74 s;
- reconstruction at 896x512: about 8 s;
- fusion pass: about 39 s (10 of the 20 steps run at strength 0.5).

## 2.3 Evaluation: VLM judge

`vlm_judge.py` uses Damir's `batch_evaluation.py` unchanged in substance:
- **Model:** `gemma-4-31b-it` through the Gemini API (a Google AI Studio key in `GEMINI_API_KEY`).
- **Prompts and score parsing:** copied verbatim from his script.
- **Per pair:** the original main-camera photo and its reconstruction are uploaded, then two separate requests are made. Are the car **numbers** preserved, and are the car **positions** preserved, each scored 1 or 0. The questions concern only cars (their number and positions), not the rest of the scene.
- **Joint:** both scores are 1. Joint success is the main metric.
- **Calibration:** the original photo judged against itself scores 100% on both datasets (173 of 173), so every "not preserved" verdict is a real difference.
- **Running it:** resumable, 4 parallel workers, retries, and an automatic wait during API outages. The API was often overloaded (`503 high demand`), with throughput between 25 and 80 pairs an hour.
- **Raw answers,** including the judge's full explanation: `../results/vlm/<setup>.jsonl`. `python vlm_judge.py --report` rebuilds `../VLM_JUDGE_REPORT.md`.

**Statistics:**
- 95% Wilson intervals for rates.
- Paired comparisons on the same cases: exact McNemar test on the joint score. "31 better / 16 worse" means 31 cases succeed only with the first receiver and 16 only with the second.
- Each pair was judged once.

## 2.4 Reproducing the main results

Run from `iter2/` with the project venv. Each step skips work that is already done.

```
# 1. payloads (paper settings, and 896x512 for the supporting cameras)
python payloads.py --dataset <dataset folder> --out data/<set>_payloads
python payloads.py --dataset <dataset folder> --out data/<set>_native --work-size 896x512
# 2. single-camera reconstruction of every camera (paper settings) = receiver A
python coordinator.py --payloads data/<set>_payloads --out results/<set>_paper --variants k1 --k1-cams all --size 1920x1088 --palette cs
# 3. supporting reconstructions at 896x512
python coordinator.py --payloads data/<set>_native --out results/<set>_support --variants k1 --k1-cams all --size 896x512 --palette cs
# 4. Damir's fusion and its control
python coordinator.py --payloads data/<set>_payloads --out results/<set>_fuse --variants fuse,fuse_noip --size 1920x1088 --palette cs \
    --fuse-main results/<set>_paper/k1 --fuse-support results/<set>_support/k1
# 5. judge, report, report-kit figures and tables
python vlm_judge.py --runs fusion --workers 4
python vlm_judge.py --report
python make_report_kit.py
```

Receiver B is `--variants prompt_only` in step 2. Full-resolution supports use `--fuse-support results/<set>_paper/k1` in step 4.

## 2.5 Code map

| File | Role |
|---|---|
| `payloads.py` | Sender: payload per camera |
| `coordinator.py` | Receivers A, B, C and older variants (`ipa_seg`, `ipa_recon`, `prompt_refine`) |
| `vlm_judge.py` | VLM judge, all setups, `--report` |
| `fusion_demo.py` | One case through Damir's pipeline, with every intermediate |
| `tune_select.py` | Tuning selection on the tuning half, confirmation on the held-out half |
| `make_report_kit.py` | Figures and CSV tables of this kit |
| `make_share_pack.py` | Smaller results pack for chats (`../results_share`) |
| `payload_sizes.py` | Payload size per element |
| `paths.py` | Dataset locations (can be overridden with `CSCI408_CARLA_V3`, `CSCI408_REAL_WORLD`, ...) |
| `carla/` (top of the repository) | CARLA case generators (v2, v3) |
| `analysis.py`, `gt_eval.py`, `compare_runs.py`, ... | Detector-based evaluation from October; superseded by the judge |
