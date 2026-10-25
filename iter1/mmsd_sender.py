#!/usr/bin/env python3
"""MMSD sender: the per-camera semantic extraction pipeline (Iteration 1).

Reproduces the sender side of MMSD from Assylbek, Aitymbetov, Ristin and Zorbas,
"Efficient semantic image communication for traffic monitoring at the edge",
Internet of Things 39 (2026) 102029, Sec. 3:

  segmentation  Mask2Former Swin-Large (Cityscapes classes); Cityscapes-palette
                map, nearest-neighbour downsampled to 1024x512, lossless WebP
  edges         grayscale image -> Canny 100/200; original resolution, lossless WebP
  caption       BLIP (base) on a 384x384 resize, default generation; UTF-8 text

In our multi-camera design every camera runs this sender unchanged, so K = 1 is
the paper's own setting and the single-view baseline.

The settings follow the seed authors' own pipeline code (their component
generation and compression scripts, provided by the authors in October 2026):
WebP is lossless at quality 100 (maximum effort), Canny uses OpenCV 100/200 on
the full-resolution grayscale image. Two deliberate differences:
  * The authors resize every input to 2048x1024 first; this script keeps the
    native resolution (identical for Cityscapes, which is 2048x1024).
  * The authors also caption with Gemma 3n (google/gemma-3n-e2b-it, a gated
    model); it is not implemented here.
SegFormer-B2 (the segmentation model of the paper's SAMR method) remains
available with --seg-model nvidia/segformer-b2-finetuned-cityscapes-1024-1024.

Usage
  python mmsd_sender.py --images data/coco_urban --out results/iteration1_mmsd_coco_urban.json
Writes one JSON file with bytes and milliseconds per component for every image,
a summary, and the run configuration. --save-components DIR also writes the
transmitted files themselves (seg .webp, edge .webp, caption .txt).
"""

import argparse
import io
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np
from PIL import Image

SEG_MODEL = "facebook/mask2former-swin-large-cityscapes-semantic"   # as in the authors' code
CAP_MODEL = "Salesforce/blip-image-captioning-base"
SEG_SIZE = (1024, 512)              # (width, height) of the transmitted map, as in the paper
CANNY_LOW, CANNY_HIGH = 100, 200    # as in the authors' code (the paper: "default threshold settings")
WEBP_LOSSLESS = True                # as in the authors' code
WEBP_QUALITY = 100                  # as in the authors' code; compression effort when lossless
CAPTION_INPUT_SIZE = (384, 384)     # the authors resize to 384x384 before BLIP
JPEG_BASELINE_QUALITY = 85          # same baseline as the September feasibility probe

# Seed paper, Table 2 (Cityscapes, 2048x1024, mean over 500 images), for comparison.
SEED_TABLE2 = {"seg_kb": 3.96, "edge_kb": 18.41, "caption_b": 57, "total_kb": 22.42, "original_mb": 2.28}

# Cityscapes 19-class colours in trainId order (official cityscapesScripts palette).
CITYSCAPES_PALETTE = np.array([
    (128, 64, 128), (244, 35, 232), (70, 70, 70), (102, 102, 156), (190, 153, 153),
    (153, 153, 153), (250, 170, 30), (220, 220, 0), (107, 142, 35), (152, 251, 152),
    (70, 130, 180), (220, 20, 60), (255, 0, 0), (0, 0, 142), (0, 0, 70),
    (0, 60, 100), (0, 80, 100), (0, 0, 230), (119, 11, 32)], dtype=np.uint8)


# ---------------------------------------------------------------- encoders
def _webp(img, quality, lossless):
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, lossless=lossless)
    return buf.getvalue()


def colourise(label_map):
    """Class-index map (H, W) -> RGB colour-coded map (H, W, 3)."""
    return CITYSCAPES_PALETTE[np.clip(label_map, 0, len(CITYSCAPES_PALETTE) - 1)]


def encode_segmentation(label_map, size=SEG_SIZE, quality=WEBP_QUALITY, lossless=WEBP_LOSSLESS):
    """Colour-coded map, nearest-neighbour downsampled to `size`, WebP."""
    img = Image.fromarray(colourise(label_map), mode="RGB").resize(size, Image.NEAREST)
    return _webp(img, quality, lossless)


def canny_edges(rgb, low=CANNY_LOW, high=CANNY_HIGH):
    import cv2
    gray = cv2.cvtColor(np.asarray(rgb.convert("RGB")), cv2.COLOR_RGB2GRAY)
    return cv2.Canny(gray, low, high)


def encode_edges(edge_map, quality=WEBP_QUALITY, lossless=WEBP_LOSSLESS):
    """0-255 edge intensities at the original resolution, WebP."""
    return _webp(Image.fromarray(edge_map.astype(np.uint8), mode="L"), quality, lossless)


def encode_jpeg(rgb, quality=JPEG_BASELINE_QUALITY):
    buf = io.BytesIO()
    rgb.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# ---------------------------------------------------------------- models
def pick_device(name="auto"):
    import torch
    if name != "auto":
        return name
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def parse_size(text):
    """'1024x2048' -> (1024, 2048), i.e. (height, width)."""
    h, w = (int(v) for v in text.lower().split("x"))
    if h <= 0 or w <= 0:
        raise ValueError(text)
    return h, w


def _sync(device):
    import torch
    if device == "cuda":
        torch.cuda.synchronize()
    elif device == "mps":
        torch.mps.synchronize()


class Segmenter:
    """Cityscapes semantic segmentation: Mask2Former (default) or SegFormer.

    input_size=(height, width) overrides the image processor's resize. Without it
    the processor default applies: in transformers 5.17 Mask2Former's processor
    squashes every input to 384x384 (62.6 vs 82.0 mIoU at 1024x2048 on Cityscapes
    val, see segmenter_resolution_test.py).
    """

    def __init__(self, device, model_id=None, input_size=None):
        self.device = device
        self.model_id = model_id or SEG_MODEL
        self.input_size = input_size
        self.segformer = "segformer" in self.model_id.lower()
        if self.segformer:
            from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor
            self.proc = SegformerImageProcessor.from_pretrained(self.model_id)
            self.model = SegformerForSemanticSegmentation.from_pretrained(self.model_id).to(device).eval()
        else:
            from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
            self.proc = AutoImageProcessor.from_pretrained(self.model_id)
            self.model = Mask2FormerForUniversalSegmentation.from_pretrained(self.model_id).to(device).eval()

    def __call__(self, rgb):
        import torch
        size = {"size": {"height": self.input_size[0], "width": self.input_size[1]}} if self.input_size else {}
        inputs = self.proc(images=rgb, return_tensors="pt", **size).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        if self.segformer:
            logits = torch.nn.functional.interpolate(
                outputs.logits, size=(rgb.height, rgb.width), mode="bilinear", align_corners=False)
            return logits.argmax(1)[0].to("cpu").numpy().astype(np.uint8)
        labels = self.proc.post_process_semantic_segmentation(outputs, target_sizes=[(rgb.height, rgb.width)])[0]
        return labels.to("cpu").numpy().astype(np.uint8)


class Captioner:
    def __init__(self, device):
        from transformers import BlipForConditionalGeneration, BlipProcessor
        self.device = device
        self.proc = BlipProcessor.from_pretrained(CAP_MODEL)
        self.model = BlipForConditionalGeneration.from_pretrained(CAP_MODEL).to(device).eval()

    def __call__(self, rgb):
        import torch
        inputs = self.proc(rgb.resize(CAPTION_INPUT_SIZE), return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model.generate(**inputs)          # default generation, as in the authors' code
        return self.proc.decode(out[0], skip_special_tokens=True).strip()


# ---------------------------------------------------------------- measurement
def measure_image(path, seg, cap, device, quality=WEBP_QUALITY, lossless=WEBP_LOSSLESS, save_dir=None):
    rgb = Image.open(path).convert("RGB")
    row = {"file": path.name, "w": rgb.width, "h": rgb.height, "file_b": path.stat().st_size}
    row["jpeg_b"] = len(encode_jpeg(rgb))

    t = time.perf_counter(); labels = seg(rgb); _sync(device); row["seg_infer_ms"] = 1e3 * (time.perf_counter() - t)
    t = time.perf_counter(); seg_b = encode_segmentation(labels, quality=quality, lossless=lossless); row["seg_encode_ms"] = 1e3 * (time.perf_counter() - t)
    t = time.perf_counter(); edges = canny_edges(rgb); edge_b = encode_edges(edges, quality=quality, lossless=lossless); row["edge_ms"] = 1e3 * (time.perf_counter() - t)
    t = time.perf_counter(); text = cap(rgb); _sync(device); row["caption_ms"] = 1e3 * (time.perf_counter() - t)
    cap_b = text.encode("utf-8")

    row.update(seg_b=len(seg_b), edge_b=len(edge_b), caption_b=len(cap_b), caption=text,
               total_b=len(seg_b) + len(edge_b) + len(cap_b),
               edge_pixel_share=float((edges > 0).mean()))
    if save_dir:
        stem = path.stem
        (save_dir / f"{stem}_seg.webp").write_bytes(seg_b)
        (save_dir / f"{stem}_edge.webp").write_bytes(edge_b)
        (save_dir / f"{stem}_caption.txt").write_bytes(cap_b)
    return row


def summarise(rows):
    """Mean and standard deviation of every numeric field, plus payload shares."""
    keys = [k for k in rows[0] if isinstance(rows[0][k], (int, float))]
    out = {}
    for k in keys:
        vals = [r[k] for r in rows]
        out[k] = {"mean": statistics.fmean(vals), "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0}
    total = out["total_b"]["mean"]
    out["share_of_payload"] = {c: out[f"{c}_b"]["mean"] / total for c in ("seg", "edge", "caption")}
    out["payload_vs_file"] = total / out["file_b"]["mean"]
    out["payload_vs_jpeg"] = total / out["jpeg_b"]["mean"]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = library default)")
    ap.add_argument("--webp-quality", type=int, default=WEBP_QUALITY)
    ap.add_argument("--webp-lossy", action="store_true", help="lossy WebP instead of the default lossless")
    ap.add_argument("--warmup", type=int, default=1, help="untimed passes before measuring")
    ap.add_argument("--save-components", type=Path, default=None)
    ap.add_argument("--seg-model", default=SEG_MODEL, help="Hugging Face id; a SegFormer id selects the SAMR model")
    ap.add_argument("--seg-input-size", type=parse_size, default=None,
                    help="HxW segmenter input, e.g. 1024x2048 (default: the processor's own resize, 384x384 in transformers 5.17)")
    ap.add_argument("--step", type=int, default=1, help="take every n-th image of the sorted set")
    args = ap.parse_args()

    import torch
    import transformers
    if args.threads:
        torch.set_num_threads(args.threads)
    device = pick_device(args.device)
    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    files = files[:: args.step]
    if args.limit:
        files = files[: args.limit]
    if not files:
        raise SystemExit(f"no images in {args.images}")
    if args.save_components:
        args.save_components.mkdir(parents=True, exist_ok=True)

    seg, cap = Segmenter(device, args.seg_model, args.seg_input_size), Captioner(device)
    for _ in range(args.warmup):
        measure_image(files[0], seg, cap, device, args.webp_quality, not args.webp_lossy)

    rows = []
    for i, f in enumerate(files, 1):
        rows.append(measure_image(f, seg, cap, device, args.webp_quality, not args.webp_lossy, args.save_components))
        r = rows[-1]
        print(f"[{i}/{len(files)}] {f.name}: seg {r['seg_b']} B, edge {r['edge_b']} B, "
              f"caption {r['caption_b']} B | {r['seg_infer_ms']:.0f}/{r['edge_ms']:.0f}/{r['caption_ms']:.0f} ms", flush=True)

    result = {
        "config": {"images": str(args.images), "n": len(rows), "device": device,
                   "threads": torch.get_num_threads(), "seg_model": seg.model_id, "cap_model": CAP_MODEL,
                   "seg_size": SEG_SIZE, "step": args.step,
                   "seg_input_size": list(args.seg_input_size) if args.seg_input_size else "processor default (384x384 in transformers 5.17)", "webp_lossless": not args.webp_lossy, "webp_quality": args.webp_quality,
                   "canny": [CANNY_LOW, CANNY_HIGH], "jpeg_baseline_quality": JPEG_BASELINE_QUALITY,
                   "torch": torch.__version__, "transformers": transformers.__version__,
                   "platform": platform.platform(), "machine": platform.machine()},
        "seed_table2": SEED_TABLE2,
        "summary": summarise(rows),
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    s = result["summary"]
    print(f"\nmean payload {s['total_b']['mean']/1024:.2f} KB "
          f"(seg {s['seg_b']['mean']/1024:.2f} KB, edge {s['edge_b']['mean']/1024:.2f} KB, "
          f"caption {s['caption_b']['mean']:.0f} B) = {100*s['payload_vs_file']:.2f}% of the source files; "
          f"edges are {100*s['share_of_payload']['edge']:.1f}% of the payload")
    print(f"seed paper (Cityscapes 2048x1024): {SEED_TABLE2}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
