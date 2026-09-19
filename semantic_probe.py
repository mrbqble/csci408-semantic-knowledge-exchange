#!/usr/bin/env python3
"""CSCI 408 feasibility probe - semantic component payload vs. compute cost.

Answers: for our pipeline, does COMMUNICATION or DEVICE COMPUTE dominate?

PORTABLE (feeds the simulator directly):
  - payload bytes per semantic component vs. raw JPEG baseline
  - params / FLOPs per extractor model
SEMI-PORTABLE:
  - CPU-only, thread-capped latency (rough edge proxy)
NOT PORTABLE:
  - GPU latency. An RTX 3070 is ~250x a Raspberry Pi 5. Never cite as device latency.

Pi 5 anchors from Assylbek, Aitymbetov, Ristin & Zorbas, Internet of Things 39
(2026) 102029: segmentation 8.35 s, masking 0.08 s, JPEG 0.16 s, peak ~496 MB.
"""

import argparse
import io
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image

PI5_SEG_SECONDS = 8.35  # anchor from Zorbas et al. 2026


def encode_segmentation(label_map):
    """Class-index map as palettised PNG. Cityscapes has 19 eval classes so
    8-bit indices suffice. Mode 'P' keeps it single-channel: saving an RGB
    colourised version would triple the payload and misrepresent a real node."""
    img = Image.fromarray(label_map.astype(np.uint8), mode="P")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def encode_edges(edge_map):
    """Canny output as 1-bit PNG. Binary, so mode '1' not 'L'."""
    img = Image.fromarray((edge_map > 0).astype(np.uint8) * 255, mode="L").convert("1")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def encode_caption(text):
    return text.encode("utf-8")


def encode_jpeg_baseline(img, quality=85):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def model_flops(model, sample_input):
    try:
        from fvcore.nn import FlopCountAnalysis
        fca = FlopCountAnalysis(model, sample_input)
        fca.unsupported_ops_warnings(False)
        fca.uncalled_modules_warnings(False)
        return fca.total()
    except Exception as e:
        print(f"  [warn] FLOP count unavailable: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--threads", type=int, default=4,
                    help="CPU thread cap; 4 matches Pi 5 core count")
    ap.add_argument("--out", default="probe_results.json")
    args = ap.parse_args()

    import torch
    import cv2
    from transformers import (
        SegformerForSemanticSegmentation, SegformerImageProcessor,
        BlipForConditionalGeneration, BlipProcessor,
    )

    if args.device == "cpu":
        torch.set_num_threads(args.threads)
        print(f"CPU mode, {args.threads} threads (edge proxy - still NOT a Pi 5)")
    else:
        print("CUDA mode - timings NOT valid device latency, planning only")
    device = torch.device(args.device)

    print("\nLoading models (first run downloads weights)...")
    seg_name = "nvidia/segformer-b0-finetuned-cityscapes-1024-1024"
    seg_proc = SegformerImageProcessor.from_pretrained(seg_name)
    seg_model = SegformerForSemanticSegmentation.from_pretrained(seg_name).to(device).eval()

    cap_name = "Salesforce/blip-image-captioning-base"
    cap_proc = BlipProcessor.from_pretrained(cap_name)
    cap_model = BlipForConditionalGeneration.from_pretrained(cap_name).to(device).eval()

    print("\nModel cost (portable across device classes):")
    seg_params = sum(p.numel() for p in seg_model.parameters())
    cap_params = sum(p.numel() for p in cap_model.parameters())
    dummy = torch.randn(1, 3, 512, 1024).to(device)
    seg_flops = model_flops(seg_model, (dummy,))
    print(f"  segformer_b0  {seg_params/1e6:7.1f}M params  "
          f"{(f'{seg_flops/1e9:.1f} GFLOPs @512x1024' if seg_flops else 'FLOPs n/a')}")
    print(f"  blip_base     {cap_params/1e6:7.1f}M params  (generative loop)")

    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    paths = sorted(p for p in Path(args.images).rglob("*")
                   if p.suffix.lower() in exts)[:args.limit]
    if not paths:
        raise SystemExit(f"No images found in {args.images}")
    print(f"\nProcessing {len(paths)} images...\n")

    rows = []
    for i, path in enumerate(paths, 1):
        img = Image.open(path).convert("RGB")
        row = {"file": path.name, "w": img.width, "h": img.height,
               "px": img.width * img.height}

        t0 = time.perf_counter()
        jpeg_bytes = encode_jpeg_baseline(img)
        row["jpeg_t"] = time.perf_counter() - t0
        row["jpeg_b"] = len(jpeg_bytes)

        t0 = time.perf_counter()
        inputs = seg_proc(images=img, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = seg_model(**inputs).logits
        if args.device == "cuda":
            torch.cuda.synchronize()
        labels = logits.argmax(dim=1)[0].cpu().numpy()
        row["seg_t"] = time.perf_counter() - t0
        row["seg_b"] = len(encode_segmentation(labels))

        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        t0 = time.perf_counter()
        edges = cv2.Canny(gray, 100, 200)
        row["edge_t"] = time.perf_counter() - t0
        row["edge_b"] = len(encode_edges(edges))

        t0 = time.perf_counter()
        cin = cap_proc(img, return_tensors="pt").to(device)
        with torch.no_grad():
            out = cap_model.generate(**cin, max_new_tokens=30)
        if args.device == "cuda":
            torch.cuda.synchronize()
        caption = cap_proc.decode(out[0], skip_special_tokens=True)
        row["cap_t"] = time.perf_counter() - t0
        row["cap_b"] = len(encode_caption(caption))
        row["caption"] = caption

        row["total_semantic_b"] = row["seg_b"] + row["edge_b"] + row["cap_b"]
        row["reduction_pct"] = 100 * (1 - row["total_semantic_b"] / row["jpeg_b"])
        rows.append(row)

        print(f"[{i:2d}/{len(paths)}] {path.name[:24]:24s} {row['w']}x{row['h']:<5} "
              f"jpeg {row['jpeg_b']/1024:6.1f}KB -> sem {row['total_semantic_b']/1024:5.1f}KB "
              f"({row['reduction_pct']:5.1f}% less)")

    def mean(k):
        return sum(r[k] for r in rows) / len(rows)

    mp = mean("px") / 1e6
    print("\n" + "=" * 70)
    print(f"PAYLOAD  (portable, exact)   mean resolution {mp:.2f} MP")
    print("=" * 70)
    print(f"  JPEG baseline (whole image) {mean('jpeg_b')/1024:10.1f} KB")
    print(f"  Segmentation map            {mean('seg_b')/1024:10.1f} KB")
    print(f"  Edge map                    {mean('edge_b')/1024:10.1f} KB")
    print(f"  Caption                     {mean('cap_b'):10.0f} B")
    print(f"  All three combined          {mean('total_semantic_b')/1024:10.1f} KB")
    print(f"  Reduction vs. baseline      {mean('reduction_pct'):10.1f} %")

    lat_label = f"{args.device}" + (f" ({args.threads} thr)" if args.device == "cpu" else "")
    print(f"\n{'=' * 70}")
    print(f"LATENCY on {lat_label}  -- NOT device latency")
    print("=" * 70)
    print(f"  Segmentation                {mean('seg_t'):10.3f} s")
    print(f"  Canny edges                 {mean('edge_t'):10.3f} s")
    print(f"  Captioning                  {mean('cap_t'):10.3f} s")
    print(f"  JPEG encode                 {mean('jpeg_t'):10.3f} s")

    compute = mean("seg_t") + mean("edge_t") + mean("cap_t")
    sem_kb = mean("total_semantic_b") / 1024
    base_kb = mean("jpeg_b") / 1024

    print(f"\n{'=' * 70}")
    print("THE ANSWER: compute vs. communication")
    print("=" * 70)
    print(f"  Compute, this machine       {compute:10.3f} s")
    print(f"  Compute, Pi 5 anchor        {PI5_SEG_SECONDS:10.3f} s  (segmentation alone)")
    print()
    for name, kbps in [("WiFi   ~10 Mbps", 10000), ("BLE     ~100 kbps", 100),
                       ("LoRa      ~5 kbps", 5)]:
        tx = (sem_kb * 8) / kbps
        bs = (base_kb * 8) / kbps
        print(f"  TX @ {name:18s} {tx:8.3f} s   (baseline {bs:9.3f} s)")

    print(f"\n  Read it this way: if TX time exceeds compute time, communication")
    print(f"  dominates and the modelled compute term matters less. If the Pi 5")
    print(f"  anchor ({PI5_SEG_SECONDS} s) exceeds TX time, compute dominates and the")
    print(f"  compute model becomes the weakest link in the methodology.")

    with open(args.out, "w") as f:
        json.dump({"config": vars(args),
                   "model_params": {"segformer_b0": seg_params, "blip_base": cap_params},
                   "segformer_flops_512x1024": seg_flops,
                   "rows": rows}, f, indent=2)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
