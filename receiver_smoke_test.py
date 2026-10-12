#!/usr/bin/env python3
"""Receiver smoke test (Gate 1 of the fusion plan): the K = 1 MMSD receiver on our GPU.

Rebuilds images from the components written by `mmsd_sender.py --save-components`
with the receiver settings of the seed authors' pipeline code: Stable Diffusion 1.5
with two ControlNets (lllyasviel/sd-controlnet-canny, then sd-controlnet-seg), UniPC
scheduler, 20 steps, guidance 7.5, seed 42, generated at 2048x1024, BLIP caption as
the prompt, default conditioning scales, no negative prompt.

The authors' README asks for about 16 GB of GPU memory. This script first tries the
whole pipeline on the GPU (fp16, VAE tiling); if that runs out of memory it retries
with model CPU offload, and it records which mode worked, the time per image and the
peak GPU memory.

Usage
  python receiver_smoke_test.py --components data/components_m2f --limit 5 \
      --out results/iteration1_receiver_smoke_test.json --save-dir results/receiver_smoke
"""
import argparse
import json
import platform
import time
from pathlib import Path

from PIL import Image

SD_MODELS = ["runwayml/stable-diffusion-v1-5",                  # the authors' id
             "stable-diffusion-v1-5/stable-diffusion-v1-5"]     # official mirror, same weights
CN_EDGE = "lllyasviel/sd-controlnet-canny"
CN_SEG = "lllyasviel/sd-controlnet-seg"
TARGET_SIZE = (2048, 1024)   # (width, height)
STEPS, GUIDANCE, SEED = 20, 7.5, 42


def load_pipeline(offload):
    import torch
    from diffusers import ControlNetModel, StableDiffusionControlNetPipeline, UniPCMultistepScheduler
    cns = [ControlNetModel.from_pretrained(m, torch_dtype=torch.float16) for m in (CN_EDGE, CN_SEG)]
    last_err = None
    for sd in SD_MODELS:
        try:
            pipe = StableDiffusionControlNetPipeline.from_pretrained(
                sd, controlnet=cns, safety_checker=None, torch_dtype=torch.float16, variant="fp16")
            break
        except Exception as e:            # the runwayml repository may no longer be served
            last_err = e
            print(f"could not load {sd}: {type(e).__name__}: {str(e)[:120]}", flush=True)
    else:
        raise last_err
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.vae.enable_tiling()          # pipeline-level enable_vae_tiling() is gone in diffusers 0.41
    if offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe, sd


def load_components(comp_dir, stem):
    seg = Image.open(comp_dir / f"{stem}_seg.webp").convert("RGB").resize(TARGET_SIZE, Image.NEAREST)
    edge = Image.open(comp_dir / f"{stem}_edge.webp").convert("RGB")
    if edge.size != TARGET_SIZE:
        edge = edge.resize(TARGET_SIZE, Image.LANCZOS)
    caption = (comp_dir / f"{stem}_caption.txt").read_text(encoding="utf-8").strip()
    return seg, edge, caption


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--components", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--save-dir", type=Path, default=None)
    args = ap.parse_args()

    import diffusers
    import torch
    stems = sorted(p.name[: -len("_seg.webp")] for p in args.components.glob("*_seg.webp"))[: args.limit]
    if not stems:
        raise SystemExit(f"no components in {args.components}")
    if args.save_dir:
        args.save_dir.mkdir(parents=True, exist_ok=True)

    rows, mode, pipe, sd_id, load_s = [], None, None, None, None
    for offload in (False, True):
        try:
            torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
            t = time.perf_counter()
            pipe, sd_id = load_pipeline(offload)
            load_s = time.perf_counter() - t
            mode = "model_cpu_offload" if offload else "gpu_resident"
            rows = []
            for i, stem in enumerate(stems):
                seg, edge, caption = load_components(args.components, stem)
                torch.cuda.synchronize(); t = time.perf_counter()
                img = pipe(prompt=caption, image=[edge, seg], num_inference_steps=STEPS,
                           guidance_scale=GUIDANCE, height=TARGET_SIZE[1], width=TARGET_SIZE[0],
                           generator=torch.Generator(device="cpu" if offload else "cuda").manual_seed(SEED)).images[0]
                torch.cuda.synchronize()
                rows.append({"stem": stem, "caption": caption, "seconds": time.perf_counter() - t,
                             "peak_gpu_mb": torch.cuda.max_memory_allocated() / 2**20})
                if args.save_dir:
                    img.save(args.save_dir / f"{stem}_blip_reconstructed.png")
                print(f"[{i + 1}/{len(stems)}] {stem}: {rows[-1]['seconds']:.1f} s, "
                      f"peak {rows[-1]['peak_gpu_mb']:.0f} MB ({mode})", flush=True)
            break
        except torch.OutOfMemoryError as e:
            print(f"out of memory in {'offload' if offload else 'GPU-resident'} mode: {str(e)[:160]}", flush=True)
            del pipe
            pipe = None
            if offload:
                raise

    timed = rows[1:] or rows          # the first image includes CUDA warm-up
    result = {"config": {"sd_model": sd_id, "controlnets": [CN_EDGE, CN_SEG], "scheduler": "UniPC",
                         "steps": STEPS, "guidance": GUIDANCE, "seed": SEED, "size": TARGET_SIZE,
                         "mode": mode, "vae_tiling": True, "gpu": torch.cuda.get_device_name(0),
                         "torch": torch.__version__, "diffusers": diffusers.__version__,
                         "platform": platform.platform()},
              "load_seconds": load_s,
              "mean_seconds_excluding_first": sum(r["seconds"] for r in timed) / len(timed),
              "peak_gpu_mb": max(r["peak_gpu_mb"] for r in rows),
              "seed_paper_rtx5080_seconds": 14.47,
              "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    print(f"mode {mode}; {result['mean_seconds_excluding_first']:.1f} s per image; "
          f"peak {result['peak_gpu_mb']:.0f} MB; wrote {args.out}")


if __name__ == "__main__":
    main()
