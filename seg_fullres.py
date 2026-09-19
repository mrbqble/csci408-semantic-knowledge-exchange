#!/usr/bin/env python3
"""Re-measure segmentation payload with logits upsampled to native resolution.

The original probe saved argmax of the raw logits (128x128 for SegFormer-B0),
which is not comparable against a full-resolution JPEG baseline. Standard
SegFormer post-processing bilinearly upsamples logits to the input size first;
that is what a real node would transmit if the coordinator needs a map aligned
to the scene.

Reports both, so the difference is explicit.
"""
import io
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

NAME = "nvidia/segformer-b0-finetuned-cityscapes-1024-1024"
torch.set_num_threads(4)


def png_bytes(label_map):
    buf = io.BytesIO()
    Image.fromarray(label_map.astype(np.uint8), mode="P").save(
        buf, format="PNG", optimize=True)
    return len(buf.getvalue())


proc = SegformerImageProcessor.from_pretrained(NAME)
model = SegformerForSemanticSegmentation.from_pretrained(NAME).eval()

paths = sorted(Path("images_cityscapes").glob("*.png"))[:25]
raw, full, half, times = [], [], [], []

for p in paths:
    img = Image.open(p).convert("RGB")
    W, H = img.size
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(**proc(images=img, return_tensors="pt")).logits
    # native resolution, standard post-processing
    up = F.interpolate(logits, size=(H, W), mode="bilinear", align_corners=False)
    lab_full = up.argmax(dim=1)[0].numpy()
    times.append(time.perf_counter() - t0)
    # half resolution, a plausible transmit compromise
    up2 = F.interpolate(logits, size=(H // 2, W // 2), mode="bilinear",
                        align_corners=False)
    raw.append(png_bytes(logits.argmax(dim=1)[0].numpy()))
    full.append(png_bytes(lab_full))
    half.append(png_bytes(up2.argmax(dim=1)[0].numpy()))

mean = lambda v: sum(v) / len(v)
JPEG = 260768   # measured baseline at 2048x1024
CAP = 40
EDGE = 31783

print(f"\n{len(paths)} Cityscapes val images at 2048x1024\n")
print(f"{'segmentation map':28s}{'bytes':>10s}{'+caption':>12s}{'reduction':>12s}")
for lbl, v in [("raw logits (128x128)", mean(raw)),
               ("upsampled 1024x512", mean(half)),
               ("upsampled 2048x1024", mean(full))]:
    tot = v + CAP
    print(f"  {lbl:26s}{v:10.0f}{tot:12.0f}{100*(1-tot/JPEG):11.2f}%")
print(f"\n  ground truth 2048x1024 (measured earlier): 1249 B"
      f"  -> {100*(1-(1249+CAP)/JPEG):.2f}%")
print(f"\nall three components, using full-res prediction:")
tot3 = mean(full) + CAP + EDGE
print(f"  {tot3:.0f} B -> {100*(1-tot3/JPEG):.2f}% reduction, "
      f"edge is {100*EDGE/tot3:.1f}% of payload")
print(f"\nsegmentation latency (4 threads): {mean(times):.3f} s")
