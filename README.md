# Semantic Knowledge Exchange for Distributed Image Classification in IoT Networks

CSCI 408 Senior Project I — Nazarbayev University
Adviser: Prof. Dimitrios Zorbas · Type: R&D · Complexity: Highest

**Team:** Bibol Assetbek · Temirshin Kantemirov · Yernur Kenzhaly · Zhengis Kosher

The registered title is kept; the direction changed at the 14 September adviser meeting.

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

`mmsd_sender.py` reproduces the paper's sender (Sec. 3) and measures every component:

- segmentation: SegFormer-B2 (Cityscapes classes), colour-coded map downsampled to 1024×512, WebP
- edges: Canny on the grayscale image at full resolution, WebP
- caption: BLIP (base)

The paper leaves two settings open; both are recorded in the code. Canny
thresholds are 100/200 (OpenCV has no defaults). The WebP mode is settled by
`encoding_ablation.py`: lossless WebP reproduces the paper's segmentation-map
size, lossy WebP does not.

| Encoding of the same maps (25 COCO street scenes) | Segmentation map | Edge map |
|---|---|---|
| WebP lossy, quality 80 | 17.56 KB | 66.19 KB |
| WebP lossy, quality 50 | 12.48 KB | 56.10 KB |
| **WebP lossless (default)** | **4.40 KB** | **13.74 KB** |
| PNG (September probe) | 6.31 KB | 14.82 KB |

Measured payload with lossless WebP:

| Component | This repo (25 COCO street scenes, mean 590×458) | Paper (Cityscapes, 2048×1024) |
|---|---|---|
| Segmentation map | 4.40 KB | 3.96 KB |
| Edge map | 13.74 KB | 18.41 KB |
| Caption | 35 B | 57 B |
| **Total** | **18.17 KB** | **22.42 KB** |
| Edge share of payload | 75.6% | 82% |

The payload is 9.9% of the COCO source files and 22.6% of a quality-85 JPEG of
the same frame. Edges dominate the payload in both datasets, which is why the
allocation of components across cameras matters.

Sender time per frame on an Apple M4 GPU (MPS): segmentation 96 ms, map encoding
15 ms, edges 8 ms, caption 187 ms. These are workstation numbers; the paper's
Raspberry Pi 5 figures (segmentation 8.35 s, caption 7.07 s) remain the device reference.

Reproduce:

```bash
scripts/iteration1.sh     # unit tests, image download, measurement
python encoding_ablation.py --images data/coco_urban --out results/iteration1_encoding_ablation_coco_urban.json
```

Results: `results/iteration1_mmsd_coco_urban.json`,
`results/iteration1_encoding_ablation_coco_urban.json`.

Still open: the same run on Cityscapes (the paper's dataset), which needs the
registered download stored on the OMEN.

## Repository layout

```
mmsd_sender.py          Iteration 1: MMSD sender (segmentation, edges, caption) + measurement
encoding_ablation.py    Iteration 1: WebP and PNG encodings of the same maps
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
