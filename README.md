# Semantic Knowledge Exchange for Distributed Image Classification in IoT Networks

CSCI 408 Senior Project I — Nazarbayev University
Adviser: Prof. Dimitrios Zorbas · Type: R&D · Complexity: Highest

**Team:** Bibol Assetbek · Temirshin Kantemirov · Yernur Kenzhaly · Zhengis Kosher

The registered title is kept; the direction changed at the 14 September adviser meeting.

> **Latest work (Nov 2026):** iteration 2, the multi-camera receiver and its VLM-judge evaluation, is in [`iter2/`](iter2/). Start with [`iter2/report_kit/README.md`](iter2/report_kit/README.md) for the numbers, figures and tables, and [`iter2/VLM_FINDINGS.md`](iter2/VLM_FINDINGS.md) for the full log. Step-by-step examples are in [`iter2/fusion_demo/`](iter2/fusion_demo/).

---

## Current direction

Several roadside cameras watch the same intersection from different angles. Each
runs the sender from the adviser's MMSD paper and transmits compact semantic
components (a segmentation map, an edge map and a caption) instead of video. A
receiver fuses the components from K cameras and rebuilds a reference camera's
view. The reconstruction is judged on vehicle counts and positions; how
components are allocated across cameras is a study variable, and energy is
modelled per camera. The environment is fully simulated: no physical IoT hardware.

## Relationship to prior work

> D. Assylbek, N. Aitymbetov, M. Ristin, D. Zorbas, "Efficient semantic image
> communication for traffic monitoring at the edge," *Internet of Things*,
> vol. 39, 102029, 2026. doi:10.1016/j.iot.2026.102029

| | MMSD (that paper) | This project |
|---|---|---|
| Source cameras | one | K, with overlapping views |
| Each camera sends | segmentation, edges, caption | the same components; the allocation per camera varies |
| Receiver | Stable Diffusion + two ControlNets rebuild the same view | rebuilds a reference view from K cameras |
| Evaluation | VLM judge, human preference | counts and positions, payload, per-camera energy |

## Iteration 1 (28 Sep – 11 Oct): the MMSD sender

`mmsd_sender.py` reproduces the paper's sender (Sec. 3) with the settings of the
seed authors' own pipeline code (provided by the authors in October 2026; not
included in this repository):

- segmentation: Mask2Former Swin-Large (`facebook/mask2former-swin-large-cityscapes-semantic`),
  Cityscapes-palette map, nearest-neighbour downsampled to 1024×512, lossless WebP at quality 100
- edges: OpenCV Canny 100/200 on the full-resolution grayscale image, lossless WebP at quality 100
- caption: BLIP (base) on a 384×384 resize, default generation

On the first 10 Cityscapes val images, every segmentation map, edge map and
caption is byte-for-byte the same size as the authors' scripts produce. The
authors also caption with Gemma 3n, a gated model that is not set up here.

### Cityscapes val, 500 images (OMEN, RTX 3070 Laptop GPU)

| Component | This repo | Paper (Table 2) |
|---|---|---|
| Segmentation map | 4.14 KB | 3.96 KB |
| Edge map | 21.91 KB | 18.41 KB |
| Caption | 38 B | 57 B |
| **Total** | **26.09 KB** (1.13% of the 2.36 MB PNG; 11.1% of a q85 JPEG) | **22.42 KB** (0.96% of 2.28 MB) |
| Edge share of payload | 84.0% | 82% |

The paper's 500 test images were randomly sampled from Cityscapes, while this
run uses the 500 val images, so the numbers are not expected to match exactly.
The edge map differs most because edge density depends on the scene. Encoder
effort is not the cause: lossless WebP at quality 80 and 100 gives practically
the same edge maps.

Encoding of the same maps:

| Encoding | Cityscapes seg | Cityscapes edges | COCO seg | COCO edges |
|---|---|---|---|---|
| WebP lossy, quality 80 | 13.78 KB | 97.00 KB | 16.05 KB | 66.19 KB |
| WebP lossy, quality 50 | 9.64 KB | 82.30 KB | 11.51 KB | 56.10 KB |
| **WebP lossless, quality 100 (default)** | **4.14 KB** | **21.91 KB** | **3.78 KB** | **13.74 KB** |
| PNG (September probe) | 5.67 KB | 26.68 KB | 5.67 KB | 14.82 KB |

`canny_sweep.py` measures the edge map under other Canny settings (run on 9 Oct
with WebP quality 80): 50/150 gives 34.92 KB, 100/200 22.01 KB, 150/250 14.63 KB.

Sender time per frame on Cityscapes: on the RTX 3070 GPU, segmentation 117 ms,
map encoding 59 ms, edges 67 ms, caption 291 ms. On the OMEN CPU with 4 threads
(25 images), segmentation 2.06 s and caption 1.00 s, about 3.2 s per frame in
total, against the paper's 15.46 s on a Raspberry Pi 5.

### COCO street scenes, 25 images (mean 590×458)

17.55 KB per frame (segmentation 3.78 KB, edges 13.74 KB, caption 34 B): 9.6% of
the source files and 21.8% of a q85 JPEG; edges are 78.3% of the payload.

### Receiver smoke test (Gate 1 of the fusion plan)

`receiver_smoke_test.py` rebuilds images from the saved components with the
authors' receiver settings: Stable Diffusion 1.5 (`runwayml/stable-diffusion-v1-5`,
fp16) with `lllyasviel/sd-controlnet-canny` and `sd-controlnet-seg`, UniPC,
20 steps, guidance 7.5, seed 42, at 2048×1024. On the RTX 3070 Laptop GPU (8 GB)
the whole pipeline stays on the GPU with VAE tiling: 79.9 s per image and 4.9 GB
peak memory over 5 Cityscapes images, against the paper's 14.47 s on an RTX 5080
and the authors' estimate of about 16 GB.

### Palette test: ADE20K colours for the segmentation ControlNet

The authors colour the segmentation map with the Cityscapes palette, while
`sd-controlnet-seg` was trained on ADE20K-palette maps. `palette_test.py` rebuilds
the same 5 Cityscapes images with the colours remapped to ADE20K (Cityscapes
"train" maps to bus), with and without the edge ControlNet, and scores each
reconstruction by re-segmenting it with Mask2Former and comparing with the
original's labels (IoU per class):

| Variant (5 images) | Pixel acc. | mIoU | Sky | Vegetation | Sidewalk | Car | Person |
|---|---|---|---|---|---|---|---|
| A: Cityscapes colours, edges + seg (authors) | 0.856 | 0.320 | 0.00 | 0.53 | 0.04 | 0.82 | 0.19 |
| B: ADE20K colours, edges + seg | 0.889 | 0.421 | 0.88 | 0.83 | 0.33 | 0.85 | 0.08 |
| C: Cityscapes colours, seg only | 0.398 | 0.081 | 0.00 | 0.00 | 0.02 | 0.43 | 0.00 |
| D: ADE20K colours, seg only | 0.852 | 0.303 | 0.68 | 0.66 | 0.21 | 0.67 | 0.00 |

With the authors' colours the receiver never renders sky, and without edges it
collapses (C), as in the paper's no-edge ablation. ADE20K colours bring sky and
vegetation back and make segmentation-only reconstructions usable (D), but the
vehicles in D are unreliable (duplicated or added cars) and people get worse.
Five images, one seed and a Mask2Former-based score: an indication, not a result.

### Palette evaluation on 100 images

`palette_eval.py` repeats A vs B on 100 Cityscapes val images (every 5th) and adds
vehicle metrics from torchvision's COCO Faster R-CNN (cars, motorcycles, buses,
trucks; score >= 0.5; position match at IoU >= 0.5). Paired B - A differences
with 95% bootstrap intervals:

| Metric | A (authors) | B (ADE20K) | B - A [95% CI] |
|---|---|---|---|
| mIoU (re-segmentation) | 0.308 | 0.380 | +0.073 [+0.058, +0.089] |
| Sky IoU | 0.20 | 0.69 | +0.49 [+0.41, +0.58] |
| Building / vegetation IoU | 0.57 / 0.68 | 0.68 / 0.80 | +0.11 / +0.11 |
| Car IoU | 0.62 | 0.69 | +0.07 [+0.03, +0.11] |
| Vehicle count error per image | 3.98 | 3.69 | -0.29 [-1.03, +0.41] |
| Vehicle recall (position match) | 0.65 | 0.66 | +0.03 [+0.00, +0.06] |
| Colourfulness (originals 14.9) | 12.7 | 11.1 | -1.5 [-2.7, -0.5] |

ADE20K colours improve scene semantics; vehicle counts do not change
significantly, and both receivers match only about two thirds of the original
vehicles in position.

### Segmenter input resolution

In transformers 5.17, Mask2Former's image processor resizes every input to a
384x384 square by default, so `mmsd_sender.py` (and the authors' code in this
environment) segments a squashed copy of the 2048x1024 frame.
`segmenter_resolution_test.py` scores the same model against Cityscapes ground
truth (50 val images) at explicit input sizes:

| Processor input | mIoU | Pixel acc. | Pole | Person | Time (RTX 3070) |
|---|---|---|---|---|---|
| 384x384 (default) | 62.6 | 92.7 | 35 | 68 | 0.18 s |
| 512x1024 | 77.9 | 95.9 | 60 | 83 | 0.32 s |
| 1024x2048 | 82.0 | 96.6 | 67 | 88 | 1.00 s |

At full resolution the model reaches the published 83.3, so the weights load
correctly (`segmenter_gt_check.py` gives 68.0 mIoU on all 500 val images at the
default size). Which resolution the authors' environment used is open. The
palette evaluation used the default for both variants, so its comparison holds,
but its absolute IoUs are lower than a full-resolution judge would give. Both
scripts expect the Cityscapes zips one folder up, as on the OMEN.

### Segmenter input size: payload and time

`mmsd_sender.py --seg-input-size HxW` sets the segmenter's input size (default:
the processor's own 384x384). Same 100 Cityscapes val images on the GPU; the CPU
columns use 25 of them on the OMEN CPU with 4 threads:

| Segmenter input | mIoU vs GT (50 images) | Seg map | Total payload | GPU seg | CPU seg | CPU sender total |
|---|---|---|---|---|---|---|
| 384x384 (default) | 62.6 | 4.24 KB | 27.05 KB | 117 ms | 2.08 s | 3.17 s |
| 512x1024 | 77.9 | 5.06 KB | 27.88 KB | 273 ms | 6.83 s | 7.92 s |
| 1024x2048 | 82.0 | 5.52 KB | 28.34 KB | 986 ms | 26.16 s | 27.22 s |

The payload grows little because the edge map dominates it; the segmentation map
grows by 19% and 30%. Sender time on CPU grows 2.5x at 512x1024 and 8.6x at full
resolution.

### Settings for the project experiments (decision of 12 Oct 2026)

- **Reproduction baseline** (comparisons with the seed paper): the authors'
  configuration with the processor's default segmenter input (384x384 in
  transformers 5.17), until the authors confirm their environment.
- **Operating point for all project experiments** (fusion, allocation, energy):
  `--seg-input-size 512x1024` (`mmsd_sender.OPERATING_SEG_INPUT_SIZE`).
- **Sensitivity**: results reported at 384x384, 512x1024 and 1024x2048.
- **Evaluation**: the Mask2Former re-segmentation judge runs at full resolution
  (1024x2048).

Reproduce:

```bash
scripts/iteration1.sh     # unit tests, COCO download, measurement; Cityscapes and receiver commands inside
```

Results: `results/iteration1_*.json`.

## Branches and versions

Each version of the work is kept on its own branch; `main` holds both iterations together.

| Branch | Contents |
|---|---|
| `main` | Iteration 1 and iteration 2 (iteration 2 merged through PR #34) |
| `iteration-1-final` | Iteration 1 as merged on 12 Oct 2026 (PRs #27–#33), kept unchanged |
| `iteration-1/*`, `settings/operating-point` | The individual iteration 1 pull requests |
| `iter2-multicam` | Iteration 2: multi-camera receiver, dataset tooling, VLM-judge evaluation, report kit (PR #34) |

## Iteration 2 (12 Oct – 26 Nov): the multi-camera receiver

Every camera sends the unchanged MMSD payload (segmentation map, edge map, caption). The receiver reconstructs each camera from its own payload, then refines the main camera's reconstruction in a second Stable Diffusion 1.5 img2img pass (strength 0.5): ControlNets on the main camera's maps, an IP-Adapter on the other cameras' reconstructions, and a caption merged from all cameras. The fusion design was proposed by D. Assylbek. A VLM judge (gemma-4-31b-it) decides whether car numbers and car positions are preserved.

| Joint success (numbers and positions) | CARLA v3, 112 cases | Real-world (Astana), 61 cases |
|---|---|---|
| Single-camera MMSD | 56.2% | 75.4% |
| Multi-camera fusion | 69.6% (McNemar p = 0.040) | 80.3% (p = 0.55) |

Datasets and image outputs are on the team Google Drive; [`iter2/handoff/`](iter2/handoff/) indexes them.

## Repository layout

```
iter2/                  Iteration 2: multi-camera receiver, VLM judge, findings, report kit
iter1/                  Iteration 1 scripts and result summaries added in November
tools/carla_multicam_kit/  CARLA multi-camera generators; real-world frame extraction and sync
netsim/                 Network-emulation prototype (gRPC, Docker, tc/netem), October
setup_project.py, share_project.py, clear_tasks.py  GitHub Projects board scripts (September)
mmsd_sender.py          Iteration 1: MMSD sender (segmentation, edges, caption) + measurement
encoding_ablation.py    Iteration 1: WebP and PNG encodings of the same maps
canny_sweep.py          Iteration 1: edge-map size under several Canny settings
receiver_smoke_test.py  Iteration 1: K = 1 receiver on our GPU (Gate 1)
palette_test.py         Iteration 1: Cityscapes vs ADE20K colours for the segmentation ControlNet
palette_eval.py         Iteration 1: the same on 100 images, with vehicle counts
segmenter_*.py          Iteration 1: Mask2Former vs Cityscapes ground truth, by input resolution
fetch_coco_urban.py     download the 25 COCO street scenes listed in probe_urban.json
scripts/iteration1.sh   one-command reproduction of the Iteration 1 measurement
tests/                  unit tests for the encoders (python -m pytest -q tests)
results/                Iteration 1 measurements (tracked)
semantic_probe.py       September feasibility probe: payload + latency per component
pick_urban.py           select street scenes from COCO val2017 via annotations
prep_cityscapes.py      extract Cityscapes val subset, run probe at 2048x1024
seg_fullres.py          segmentation payload at several transmit resolutions
par_download.py         parallel segmented downloader (Cityscapes throttles
                        ~0.5 MB/s per connection; 8 connections give ~5.7x)
verify_md5.py           checksum a downloaded package against the published md5
probe_*.json            September probe results (tracked)
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins the CUDA build used on the OMEN, where PyTorch must come
from the CUDA index, not plain PyPI:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

On macOS (Apple silicon), install from PyPI instead; the GPU is used through MPS:

```bash
pip install torch torchvision transformers pillow opencv-python-headless numpy pytest
```

## Data — not in this repository

Datasets are gitignored. Reproduce them:

**Cityscapes** (requires a registered academic account at
cityscapes-dataset.com; approval is manual and can take days)

```bash
pip install cityscapesScripts
csDownload -d . gtFine_trainvaltest.zip        # 241 MB
csDownload -d . -r leftImg8bit_trainvaltest.zip # 11 GB, ~1 h at 8 connections
python prep_cityscapes.py
```

**COCO val2017** (no registration). Iteration 1 needs only the 25 street scenes:

```bash
python fetch_coco_urban.py        # 25 images, ~4.7 MB
```

The full set, used by the September probe:

```bash
curl -O http://images.cocodataset.org/zips/val2017.zip
curl -O http://images.cocodataset.org/annotations/annotations_trainval2017.zip
python pick_urban.py
```

## September feasibility probe (superseded by Iteration 1)

Measured on 25 Cityscapes val images at 2048×1024, CPU-only, 4 threads, with
SegFormer-B0 and PNG encodings:

| Component | Payload | Share |
|---|---|---|
| Segmentation (upsampled to native) | 3,530 B | 10.0% |
| Edge map (Canny, 1-bit PNG) | 31,783 B | **89.9%** |
| Caption (BLIP) | 40 B | 0.1% |
| JPEG baseline (q85) | 260,768 B | — |

- Segmentation + caption alone → **98.63% reduction**
- All three components → **86.44% reduction**
- Captioning dominates compute (~83%); compute is **resolution-independent**
  because both extractors resize inputs to fixed dimensions

Notes that still apply:

1. **Baseline.** The paper measures against the 2.28 MB lossless PNG and reports
   111× compression; a JPEG baseline gives a much smaller ratio. Report both and
   state which.
2. **Upsampling artifacts.** A model prediction upsampled to 2048×1024 compressed
   to nearly 3× the hand-annotated ground truth (3,530 B vs 1,249 B); ragged
   bilinear boundaries compress badly.

The PNG-versus-WebP question raised here is settled by the Iteration 1 ablation
above (lossless WebP).

## Real-world photos

The real-world (Astana) photos and every image made from them were removed from this public repository on 27 Nov 2026: they show faces and licence plates, which will be blurred before any publication. The code, the judge answers and the CARLA examples stay here; the real-world images are on the team Google Drive (NU accounts only), `Materials/Pipeline Outputs/repo_real_world_images/`.
