# Semantic Knowledge Exchange for Distributed Image Classification in IoT Networks

CSCI 408 Senior Project I — Nazarbayev University
Adviser: Prof. Dimitrios Zorbas · Type: R&D · Complexity: Highest

**Team:** Bibol Assetbek · Temirshin Kantemirov · Yernur Kenzhaly · Zhengis Kosher

> **Latest work (Nov 2026):** iteration 2, the multi-camera receiver with its evaluation, is in [`iter2/`](iter2/). Start with [`iter2/STATUS_2026-11-11.md`](iter2/STATUS_2026-11-11.md); before/after examples are in [`iter2/demo/`](iter2/demo/).

---

## Problem

Multiple IoT nodes classify a scene collaboratively by exchanging compact
*semantic knowledge* instead of raw images or large feature tensors. Each node
extracts a **different** semantic component — segmentation, edges, caption — and
sends only that to an edge coordinator, which aggregates the partial components
and produces the classification directly, without reconstructing the image.

Evaluated against a centralized image classifier on six metrics: classification
accuracy, transmitted data size, communication latency, per-device processing
time, end-to-end inference time, energy consumption.

Environment is **fully simulated** — no physical IoT hardware.

## Relationship to prior work

Direct extension of the adviser's own paper:

> D. Assylbek, N. Aitymbetov, M. Ristin, D. Zorbas, "Efficient semantic image
> communication for traffic monitoring at the edge," *Internet of Things*,
> vol. 39, 102029, 2026. doi:10.1016/j.iot.2026.102029

| | MMSD (that paper) | This project |
|---|---|---|
| Source nodes | one | **multiple** |
| Each node sends | all components | **one different component each** |
| Receiver task | reconstruct the image | **classify directly** |
| Reconstruction | Stable Diffusion + dual ControlNet | **none** |

## Repository layout

```
semantic_probe.py     feasibility probe: payload + latency per component
pick_urban.py         select street scenes from COCO val2017 via annotations
prep_cityscapes.py    extract Cityscapes val subset, run probe at 2048x1024
seg_fullres.py        segmentation payload at several transmit resolutions
par_download.py       parallel segmented downloader (Cityscapes throttles
                      ~0.5 MB/s per connection; 8 connections give ~5.7x)
verify_md5.py         checksum a downloaded package against the published md5
probe_*.json          measured results (tracked; the report depends on them)
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

PyTorch must come from the CUDA index, not plain PyPI:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
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

**COCO val2017** (no registration; used only for the initial probe)

```bash
curl -O http://images.cocodataset.org/zips/val2017.zip
curl -O http://images.cocodataset.org/annotations/annotations_trainval2017.zip
python pick_urban.py
```

## Results so far

Measured on 25 Cityscapes val images at 2048×1024, CPU-only, 4 threads:

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

### Known issues with these numbers

1. **Baseline mismatch vs. the seed paper.** The paper measures against the
   2.28 MB lossless PNG and reports 111× compression. We measure against a
   261 KB JPEG. The same payload is ~11× against JPEG. Report both, state which.
2. **PNG vs. WebP.** The paper uses WebP and gets 18.41 KB for the edge map
   where our 1-bit PNG takes 31.0 KB. Switching encoders should cut ~40%.
3. **Upsampling artifacts.** Our model prediction upsampled to 2048×1024 is
   3,530 B, nearly 3× the hand-annotated ground truth at 1,249 B — ragged
   bilinear boundaries compress badly. Boundary smoothing is likely free gain.

## Open questions for the adviser

- Are edge maps needed when classifying rather than reconstructing? (Their
  Table 7 ablation shows edges are essential for *reconstruction* — joint score
  falls 86.9% → 24.2% without them. Classification may differ.)
- How should the coordinator aggregate heterogeneous components — late fusion
  of per-component classifiers, or a single multi-modal encoder?
- Which network simulator, which radio, which energy model?

## Real-world photos

The real-world (Astana) photos and every image made from them were removed from this public repository on 27 Nov 2026: they show faces and licence plates, which will be blurred before any publication. The code, the judge answers and the CARLA examples stay here; the real-world images are on the team Google Drive (NU accounts only), `Materials/Pipeline Outputs/repo_real_world_images/`.
