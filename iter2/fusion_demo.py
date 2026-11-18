#!/usr/bin/env python3
"""Damir's multi-camera pipeline (diagram of 17 Nov 2026), end to end for one case, with every intermediate saved for presentation.

Sender side, every device: payload = segmentation map + edge map + caption (payloads.py, the seed paper's three elements; map at half resolution,
edges at full resolution). The payloads are read from the payload folder of the dataset.
Receiver side:
  1. reconstruct EVERY device from its own payload: single-camera MMSD (SD 1.5 + ControlNet canny + seg, its own caption), at the photo's resolution
  2. choose the main reconstruction (cam1, the dataset's main camera) and take its segmentation and edge maps
  3. global caption from all devices' captions
  4. SD 1.5 img2img: start from the main reconstruction with noise added (strength 0.5), ControlNets on the main segmentation + edge maps,
     IP-Adapter on the other devices' reconstructions, global caption as prompt  ->  final reconstruction
     (Damir's code: pipe(prompt=global_caption, image=main_recon, control_image=[main_edge, main_seg], ip_adapter_image=supporting_views, strength=0.5))
  5. control: the same img2img pass without the IP-Adapter, to see what the supporting views change
Several supporting views are combined by averaging their CLIP image embeddings (one IP-Adapter cannot take a list of images directly in diffusers).

Output: fusion_demo/<dataset>_caseK/ with originals, payload files, every reconstruction, the final image, the control, pipeline.jpg (a figure laid
out like the diagram) and settings.json.
Usage: python fusion_demo.py --dataset rw --case 1
"""
import argparse
import json
import shutil
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import paths
from coordinator import Coordinator, collect_case, fuse_i2i, fuse_prompt

SETS = {"rw": (Path("data/rw_core_payloads"), paths.REAL_WORLD_CORE), "v3": (Path("data/v3_payloads"), paths.CARLA_V3)}
SIZE = (1920, 1088)                      # the photo's resolution (multiple of 64), as in the seed paper's reconstruction
STRENGTH, IP_SCALE = 0.5, 1.0
try:
    FONT = ImageFont.truetype("arial.ttf", 15)
    FONT_B = ImageFont.truetype("arialbd.ttf", 18)
except OSError:
    FONT = FONT_B = ImageFont.load_default()


def photo_of(root, case, cam):
    return next(p for p in (root / case).iterdir() if p.stem == cam)


def tile(img, w, h, label, highlight=False):
    t = img.convert("RGB").resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(t)
    d.rectangle([0, 0, d.textlength(label, font=FONT) + 10, 20], fill="black")
    d.text((5, 2), label, fill="white", font=FONT)
    if highlight:
        d.rectangle([0, 0, w - 1, h - 1], outline=(220, 30, 30), width=4)
    return t


def figure(out, cams, main_cam, caption, captions):
    W, H, PAD = 384, 216, 12
    n = len(cams)
    cols = max(n, 4)
    rows_y = [60, 60 + H + 40, 60 + 2 * (H + 40), 60 + 3 * (H + 40)]
    sheet = Image.new("RGB", (PAD + cols * (W + PAD), rows_y[3] + H + 120), "white")
    d = ImageDraw.Draw(sheet)
    titles = ["Sender side: original photo of each device", "Payload of each device (segmentation map shown; plus edge map and caption)",
              "Receiver step 1: reconstruction of each device from its own payload (main = red frame)",
              "Receiver step 2: fusion in SD 1.5 img2img (main reconstruction + noise, ControlNet on main seg/edge, IP-Adapter on the others)"]
    for r, y in enumerate(rows_y):
        d.text((PAD, y - 26), titles[r], fill="black", font=FONT_B)
    for i, cam in enumerate(cams):
        x = PAD + i * (W + PAD)
        sheet.paste(tile(Image.open(out / f"original_{cam}.jpg"), W, H, f"device {cam}" + (" (main)" if cam == main_cam else "")), (x, rows_y[0]))
        sheet.paste(tile(Image.open(out / f"payload_{cam}_seg.webp"), W, H, f"{cam}: segmentation map"), (x, rows_y[1]))
        sheet.paste(tile(Image.open(out / f"reconstruction_{cam}.png"), W, H, f"reconstruction {cam}", cam == main_cam), (x, rows_y[2]))
    last = [("main edge map -> ControlNet", Image.open(out / f"payload_{main_cam}_edge.webp")),
            ("main segmentation map -> ControlNet", Image.open(out / f"payload_{main_cam}_seg.webp")),
            ("FINAL reconstruction", Image.open(out / "final_reconstruction.png")),
            ("control: same pass, no IP-Adapter", Image.open(out / "control_no_ip_adapter.png"))]
    for i, (label, im) in enumerate(last):
        sheet.paste(tile(im, W, H, label, label.startswith("FINAL")), (PAD + i * (W + PAD), rows_y[3]))
    y = rows_y[3] + H + 14
    for line in textwrap.wrap("Global caption (all devices): " + caption, 170):
        d.text((PAD, y), line, fill="black", font=FONT); y += 20
    sheet.save(out / "pipeline.jpg", quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", choices=list(SETS), required=True)
    ap.add_argument("--case", type=int, required=True)
    args = ap.parse_args()
    pay_dir, photo_root = SETS[args.dataset]
    case = f"case{args.case}"
    out = Path("fusion_demo") / f"{args.dataset}_{case}"
    out.mkdir(parents=True, exist_ok=True)
    payloads = collect_case(pay_dir, case)
    main_p, others = payloads[0], payloads[1:]
    coord = Coordinator(SIZE, "cs")
    timings = {}
    for p in payloads:                                         # sender side: originals and payload files
        Image.open(photo_of(photo_root, case, p.cam)).convert("RGB").save(out / f"original_{p.cam}.jpg", quality=92)
        for suffix in ("seg.webp", "edge.webp", "caption.txt"):
            shutil.copy(pay_dir / case / f"{p.cam}_{suffix}", out / f"payload_{p.cam}_{suffix.replace('.txt', '.txt')}")
    recon = {}
    for p in payloads:                                         # receiver step 1: every device from its own payload
        f = out / f"reconstruction_{p.cam}.png"
        if not f.exists():
            edge, seg = coord.conditions(p)
            img, sec, _ = coord.generate(edge, seg, p.caption)
            img.save(f); timings[f"reconstruction_{p.cam}_s"] = sec
            print(f"reconstruction {p.cam}: {sec:.1f} s", flush=True)
        recon[p.cam] = Image.open(f).convert("RGB")
    caption = fuse_prompt([main_p.caption] + [p.caption for p in others])        # global caption
    edge, seg = coord.conditions(main_p)                                           # step 2: main seg + edge maps
    embed = coord.image_embedding([recon[p.cam] for p in others]) if others else None
    final, sec, mem = fuse_i2i(coord, recon[main_p.cam], edge, seg, caption, embed, IP_SCALE, STRENGTH)
    final.save(out / "final_reconstruction.png"); timings["fusion_s"] = sec
    control, sec2, _ = fuse_i2i(coord, recon[main_p.cam], edge, seg, caption, None, 0.0, STRENGTH)
    control.save(out / "control_no_ip_adapter.png"); timings["control_s"] = sec2
    print(f"fusion: {sec:.1f} s (peak {mem:.0f} MB), control: {sec2:.1f} s", flush=True)
    (out / "settings.json").write_text(json.dumps({
        "dataset": args.dataset, "case": case, "devices": [p.cam for p in payloads], "main_device": main_p.cam,
        "captions": {p.cam: p.caption for p in payloads}, "global_caption": caption, "size": list(SIZE), "palette": "Cityscapes",
        "reconstruction": "single-camera MMSD per device: SD 1.5 + ControlNet canny + seg (lllyasviel sd15), UniPC 20 steps, guidance 7.5, seed 42",
        "fusion": {"pipeline": "StableDiffusionControlNetImg2ImgPipeline (same SD 1.5 and ControlNets)", "strength": STRENGTH,
                   "control_image": ["main edge map", "main segmentation map"], "ip_adapter": "h94/IP-Adapter ip-adapter_sd15",
                   "ip_adapter_scale": IP_SCALE, "ip_adapter_input": "mean CLIP image embedding of the other devices' reconstructions",
                   "prompt": "global caption"}, "timings_s": timings}, indent=1))
    figure(out, [p.cam for p in payloads], main_p.cam, caption, None)
    print("wrote", out / "pipeline.jpg", flush=True)


if __name__ == "__main__":
    main()
