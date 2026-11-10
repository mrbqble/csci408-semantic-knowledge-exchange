#!/usr/bin/env python3
"""Coordinator (Iteration 2): aggregate the payloads of one moment and rebuild the master view.

Follows the architecture of the Requirements & Design document (UC-2, UC-3):
  1. collect the K payloads of a case (camera id, timestamp, segmentation map, edge map, caption)
  2. pick the primary reference camera Rec1; the others are supporting views Rec2..RecN
  3. Rec1 segmentation + edge map -> two ControlNets (spatial / geometry anchors, as the seed
     paper's receiver: sd-controlnet-canny then sd-controlnet-seg)
  4. supporting views -> IP-Adapter (CLIP image embedding, averaged over the supporting cameras)
  5. captions of all cameras -> one global text prompt
  6. Stable Diffusion 1.5 (UniPC, 20 steps, guidance 7.5, seed 42) generates the master view

Variants (name[@ip_adapter_scale]); every variant uses the same seed and the same Rec1 anchors,
so differences between variants come from what the supporting cameras contribute:
  k1           Rec1 only, Rec1 caption, no IP-Adapter: the single-view MMSD baseline
  prompt_only  Rec1 anchors + fused caption of all cameras, no IP-Adapter
  ipa_seg      prompt_only + IP-Adapter on the supporting cameras' received segmentation maps
  ipa_recon    prompt_only + IP-Adapter on the supporting cameras' own single-view (k1)
               reconstructions: needs `k1` runs for those cameras (--k1-cams all)
  prompt_refine  the prompt_only master view with its small vehicles (blob area >= 12 px, box side <= 48 px in Rec1's
               segmentation map) redrawn: 128x128 windows (max 8) upscaled 4x, SD + the same ControlNets in img2img mode
               (strength 0.5), downscaled and pasted back with a feathered mask
The architecture document does not say what image the IP-Adapter receives for a supporting
camera (only segmentation/edge/caption are transmitted); ipa_seg and ipa_recon are the two
readings that use nothing but the payloads.

Outputs: <out>/<variant>/caseK.png + caseK.json (prompt, reference camera, seconds, peak memory);
k1 writes <out>/k1/caseK_camJ.png.

Usage
  python coordinator.py --payloads data/carla_v2_payloads --out results/carla_v2 --variants k1,prompt_only,ipa_seg
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "iter1"))
import mmsd_sender as ms  # noqa: E402
import palette_test as pt  # noqa: E402
import receiver_smoke_test as rx  # noqa: E402

IP_ADAPTER = ("h94/IP-Adapter", "models", "ip-adapter_sd15.bin")
GEN_SIZE = (1024, 576)               # (width, height) of the master view; multiple of 64
DEFAULT_IP_SCALE = 0.5
VEHICLE_TRAIN_IDS = (13, 14, 15, 16, 17, 18)     # car, truck, bus, train, motorcycle, bicycle


# ---------------------------------------------------------------- payload handling
class Payload:
    def __init__(self, case_dir, cam):
        self.cam = cam
        self.index = int(cam[3:])
        meta = json.loads((case_dir / f"{cam}_meta.json").read_text())
        self.timestamp = meta.get("timestamp")
        self.orig_size = (meta["w"], meta["h"])
        self.seg = Image.open(case_dir / f"{cam}_seg.webp").convert("RGB")      # Cityscapes palette
        self.edge = Image.open(case_dir / f"{cam}_edge.webp").convert("L")
        self.caption = (case_dir / f"{cam}_caption.txt").read_text(encoding="utf-8").strip()

    def vehicle_pixels(self):
        arr = np.asarray(self.seg)
        key = (arr[..., 0].astype(np.int32) << 16) | (arr[..., 1].astype(np.int32) << 8) | arr[..., 2]
        total = 0
        for tid in VEHICLE_TRAIN_IDS:
            c = ms.CITYSCAPES_PALETTE[tid]
            total += int((key == ((int(c[0]) << 16) | (int(c[1]) << 8) | int(c[2]))).sum())
        return total


def collect_case(payload_dir, case):
    """UC-2 aggregation: all payloads of one case, ordered by camera id. Every camera reports
    (no timeout, no loss), so the set is complete by construction."""
    case_dir = payload_dir / case
    cams = sorted((p.name[: -len("_meta.json")] for p in case_dir.glob("cam*_meta.json")), key=lambda c: int(c[3:]))
    return [Payload(case_dir, c) for c in cams]


def choose_reference(payloads, policy):
    if policy == "first":
        return payloads[0]
    if policy == "max_vehicle_area":
        return max(payloads, key=lambda p: p.vehicle_pixels())
    raise ValueError(policy)


def fuse_prompt(captions):
    """Global prompt: the distinct captions of all cameras, Rec1 first."""
    seen, parts = set(), []
    for c in captions:
        k = c.strip().lower().rstrip(".")
        if k and k not in seen:
            seen.add(k)
            parts.append(c.strip().rstrip("."))
    return ", ".join(parts)


def seg_condition(seg_rgb, size, palette):
    img = pt.cs_rgb_to_ade_rgb(seg_rgb) if palette == "ade" else seg_rgb
    return img if img.size == size else img.resize(size, Image.NEAREST)


def edge_condition(edge_l, size, thr=40):
    """Full-resolution Canny map -> generation size. Area resampling then a threshold keeps the
    1 px lines visible instead of fading them (plain bilinear/Lanczos at 1.9x halves their intensity)."""
    arr = np.asarray(edge_l)
    if arr.shape[::-1] != size:
        arr = cv2.resize(arr, size, interpolation=cv2.INTER_AREA)
        arr = np.where(arr > thr, 255, 0).astype(np.uint8)
    return Image.fromarray(arr, "L").convert("RGB")


# ---------------------------------------------------------------- generation
class Coordinator:
    def __init__(self, size=GEN_SIZE, palette="cs", steps=rx.STEPS, guidance=rx.GUIDANCE, seed=rx.SEED,
                 cn_scales=(1.0, 1.0), edge_thr=40, control_end=1.0, negative_prompt=None):
        import torch
        from diffusers import ControlNetModel, StableDiffusionControlNetPipeline, UniPCMultistepScheduler
        self.torch, self.size, self.palette = torch, size, palette
        self.steps, self.guidance, self.seed = steps, guidance, seed
        self.control_end, self.negative_prompt = control_end, negative_prompt       # ControlNet off after this fraction of the steps; negative prompt
        self.cn_scales, self.edge_thr = tuple(cn_scales), edge_thr      # ControlNet scales (canny, seg); edge binarisation
        cns = [ControlNetModel.from_pretrained(m, torch_dtype=torch.float16) for m in (rx.CN_EDGE, rx.CN_SEG)]
        for sd in rx.SD_MODELS:
            try:
                self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
                    sd, controlnet=cns, safety_checker=None, torch_dtype=torch.float16, variant="fp16")
                self.sd_id = sd
                break
            except Exception as e:
                print(f"could not load {sd}: {type(e).__name__}: {str(e)[:100]}", flush=True)
        else:
            raise RuntimeError("no Stable Diffusion 1.5 repository available")
        self.pipe.scheduler = UniPCMultistepScheduler.from_config(self.pipe.scheduler.config)
        self.pipe.vae.enable_tiling()
        repo, sub, weight = IP_ADAPTER
        self.pipe.load_ip_adapter(repo, subfolder=sub, weight_name=weight)
        self.pipe.to("cuda")
        self.embed_dim = self.pipe.image_encoder.config.projection_dim

    def image_embedding(self, images):
        """Mean CLIP image embedding of the supporting views (the IP-Adapter multi-image prompt)."""
        torch = self.torch
        with torch.no_grad():
            emb, _ = self.pipe.encode_image(list(images), "cuda", 1)
        return emb.mean(dim=0, keepdim=True)                           # (1, D)

    def generate(self, edge, seg, prompt, embed=None, ip_scale=0.0):
        """One SD1.5 + 2 ControlNet + IP-Adapter pass. embed=None or ip_scale=0 switches the adapter off."""
        torch = self.torch
        dtype = self.pipe.dtype
        pos = embed.to("cuda", dtype) if embed is not None else torch.zeros(1, self.embed_dim, device="cuda", dtype=dtype)
        embeds = torch.stack([torch.zeros_like(pos), pos])              # (2, 1, D): negative, positive
        self.pipe.set_ip_adapter_scale(float(ip_scale if embed is not None else 0.0))
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); t = time.perf_counter()
        img = self.pipe(prompt=prompt, image=[edge, seg], ip_adapter_image_embeds=[embeds],
                        num_inference_steps=self.steps, guidance_scale=self.guidance,
                        controlnet_conditioning_scale=list(self.cn_scales), control_guidance_end=self.control_end,
                        **({"negative_prompt": self.negative_prompt} if self.negative_prompt else {}),
                        height=self.size[1], width=self.size[0],
                        generator=torch.Generator(device="cuda").manual_seed(self.seed)).images[0]
        torch.cuda.synchronize()
        return img, time.perf_counter() - t, torch.cuda.max_memory_allocated() / 2**20

    def conditions(self, p):
        return edge_condition(p.edge, self.size, self.edge_thr), seg_condition(p.seg, self.size, self.palette)


# ---------------------------------------------------------------- small-vehicle refinement (prompt_refine)
REFINE_WIN, REFINE_UP, REFINE_MAX_WINDOWS = 128, 4, 8     # window (px of the master view), upscale factor, windows per image
REFINE_MIN_AREA, REFINE_MAX_SIDE = 12, 48                 # small vehicle: blob area >= 12 px, box side <= 48 px
REFINE_STRENGTH, REFINE_FEATHER = 0.5, 12                 # img2img strength, feather width of the paste mask (px)
REFINE_PROMPT = "cars on a city street, realistic photo, sharp"
REFINE_NEGATIVE = "blurry, deformed, cartoon"


def small_vehicle_components(seg_rgb, size):
    """Vehicle blobs of the received segmentation map (at the master-view size) that are small."""
    img = seg_rgb if seg_rgb.size == size else seg_rgb.resize(size, Image.NEAREST)
    a = np.asarray(img).astype(np.int64)
    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    keys = [(int(ms.CITYSCAPES_PALETTE[t][0]) << 16) | (int(ms.CITYSCAPES_PALETTE[t][1]) << 8) | int(ms.CITYSCAPES_PALETTE[t][2])
            for t in VEHICLE_TRAIN_IDS]
    mask = np.isin(key, keys).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    comps = []
    for i in range(1, n):
        x, y, bw, bh, area = (int(v) for v in st[i])
        if area >= REFINE_MIN_AREA and max(bw, bh) <= REFINE_MAX_SIDE:
            comps.append({"box": (x, y, x + bw, y + bh), "area": area})
    return comps


def group_windows(comps, size, win=REFINE_WIN, max_windows=REFINE_MAX_WINDOWS):
    """Greedy cover: repeatedly take the win x win window (clamped to the image) that fully contains the most
    still-uncovered blobs (ties: larger total area). Returns the windows and the blobs left uncovered."""
    W, H = size
    left, windows = list(comps), []
    while left and len(windows) < max_windows:
        best = None
        for c in left:
            cx, cy = (c["box"][0] + c["box"][2]) // 2, (c["box"][1] + c["box"][3]) // 2
            x0 = int(min(max(cx - win // 2, 0), W - win))
            y0 = int(min(max(cy - win // 2, 0), H - win))
            inside = [d for d in left if d["box"][0] >= x0 and d["box"][1] >= y0 and d["box"][2] <= x0 + win and d["box"][3] <= y0 + win]
            score = (len(inside), sum(d["area"] for d in inside))
            if best is None or score > best[0]:
                best = (score, x0, y0, inside)
        _, x0, y0, inside = best
        windows.append({"x0": x0, "y0": y0, "n_blobs": len(inside), "blob_areas": [d["area"] for d in inside]})
        left = [d for d in left if d not in inside]
    return windows, left


def edge_window(edge_l, x0, y0, size, thr, win=REFINE_WIN, up=REFINE_UP):
    """The window of the full-resolution edge payload, area-resampled to win*up px and binarised like edge_condition."""
    sx, sy = edge_l.width / size[0], edge_l.height / size[1]
    crop = np.asarray(edge_l.crop((int(round(x0 * sx)), int(round(y0 * sy)), int(round((x0 + win) * sx)), int(round((y0 + win) * sy)))))
    arr = cv2.resize(crop, (win * up, win * up), interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.where(arr > thr, 255, 0).astype(np.uint8), "L").convert("RGB")


def feather_mask(win=REFINE_WIN, feather=REFINE_FEATHER):
    ramp = np.minimum(np.arange(win) + 1, np.arange(win)[::-1] + 1).astype(np.float32) / feather
    return np.clip(np.minimum(ramp[:, None], ramp[None, :]), 0.0, 1.0)


def refine_small(coord, base, ref):
    """Redraw the small vehicles of `base` window by window: 4x upscale, SD + the same ControlNets in img2img mode,
    downscale, paste back with a feathered mask. Returns the refined image and a record of what was done."""
    from diffusers import StableDiffusionControlNetImg2ImgPipeline
    torch = coord.torch
    if not hasattr(coord, "i2i"):
        coord.i2i = StableDiffusionControlNetImg2ImgPipeline(**coord.pipe.components, requires_safety_checker=False)
    comps = small_vehicle_components(ref.seg, coord.size)
    windows, left = group_windows(comps, coord.size)
    seg_full = seg_condition(ref.seg, coord.size, coord.palette)
    out = np.asarray(base.convert("RGB")).astype(np.float32)
    mask = feather_mask()[:, :, None]
    up = REFINE_WIN * REFINE_UP
    dtype = coord.pipe.dtype
    embeds = torch.zeros(2, 1, coord.embed_dim, device="cuda", dtype=dtype)     # IP-Adapter off, as in generate()
    coord.pipe.set_ip_adapter_scale(0.0)
    info = {"n_small_blobs": len(comps), "n_windows": len(windows), "uncovered_blobs": len(left), "windows": [], "failures": [], "seconds": 0.0}
    for wi, win in enumerate(windows):
        x0, y0 = win["x0"], win["y0"]
        box = (x0, y0, x0 + REFINE_WIN, y0 + REFINE_WIN)
        rec = dict(win, index=wi)
        try:
            init = base.convert("RGB").crop(box).resize((up, up), Image.BICUBIC)
            seg_crop = seg_full.crop(box).resize((up, up), Image.NEAREST)
            edge_crop = edge_window(ref.edge, x0, y0, coord.size, coord.edge_thr)
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            res = coord.i2i(prompt=REFINE_PROMPT, negative_prompt=REFINE_NEGATIVE, image=init, control_image=[edge_crop, seg_crop],
                            strength=REFINE_STRENGTH, num_inference_steps=coord.steps, guidance_scale=coord.guidance,
                            controlnet_conditioning_scale=list(coord.cn_scales), ip_adapter_image_embeds=[embeds],
                            generator=torch.Generator(device="cuda").manual_seed(coord.seed + wi)).images[0]
            torch.cuda.synchronize()
            rec["seconds"] = time.perf_counter() - t0
            patch = np.asarray(res.convert("RGB").resize((REFINE_WIN, REFINE_WIN), Image.LANCZOS)).astype(np.float32)
            out[y0:y0 + REFINE_WIN, x0:x0 + REFINE_WIN] = out[y0:y0 + REFINE_WIN, x0:x0 + REFINE_WIN] * (1 - mask) + patch * mask
            info["seconds"] += rec["seconds"]
        except Exception as e:                      # report, keep the base pixels of this window
            rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            info["failures"].append(rec["error"])
            torch.cuda.empty_cache()
        info["windows"].append(rec)
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)), info


def parse_variant(spec):
    name, _, scale = spec.partition("@")
    scale = float(scale) if scale else (DEFAULT_IP_SCALE if name.startswith("ipa") else 0.0)
    if name not in ("k1", "prompt_only", "prompt_shuffled", "prompt_refine", "ipa_seg", "ipa_recon"):
        raise SystemExit(f"unknown variant {spec}")
    return name, scale, (name if scale == DEFAULT_IP_SCALE or not name.startswith("ipa") else f"{name}_s{scale:g}")


def parse_cases(text, payload_dir):
    avail = sorted((p.name for p in payload_dir.iterdir() if p.is_dir() and p.name.startswith("case")),
                   key=lambda c: int(c[4:]))
    if not text:
        return avail
    want = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        want.update(range(int(a), int(b or a) + 1))
    return [c for c in avail if int(c[4:]) in want]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--payloads", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--variants", default="k1,prompt_only,ipa_seg")
    ap.add_argument("--cases", default="", help="e.g. 1-20,25 (default: all with payloads)")
    ap.add_argument("--ref-policy", default="first", choices=["first", "max_vehicle_area"])
    ap.add_argument("--k1-cams", default="ref", choices=["ref", "all"], help="k1: only Rec1, or every camera (needed by ipa_recon)")
    ap.add_argument("--palette", default="cs", choices=["cs", "ade"], help="cs = the authors' receiver; ade = ADE20K recolour")
    ap.add_argument("--size", default=f"{GEN_SIZE[0]}x{GEN_SIZE[1]}", help="master view WxH")
    ap.add_argument("--cn-scales", default="1.0,1.0", help="ControlNet conditioning scales canny,seg (the authors use 1,1)")
    ap.add_argument("--edge-thr", type=int, default=40, help="threshold when binarising the area-resampled edge map")
    ap.add_argument("--steps", type=int, default=rx.STEPS, help="denoising steps (default: the authors' receiver)")
    ap.add_argument("--guidance", type=float, default=rx.GUIDANCE, help="classifier-free guidance scale")
    ap.add_argument("--control-end", type=float, default=1.0, help="ControlNets act on this fraction of the steps (1.0 = all)")
    ap.add_argument("--negative-prompt", default=None)
    args = ap.parse_args()
    if sys.platform == "win32":      # keep the laptop awake during long runs
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

    w, h = (int(v) for v in args.size.lower().split("x"))
    variants = [parse_variant(v) for v in args.variants.split(",")]
    cases = parse_cases(args.cases, args.payloads)
    cn_scales = tuple(float(v) for v in args.cn_scales.split(","))
    coord = Coordinator((w, h), args.palette, steps=args.steps, guidance=args.guidance, cn_scales=cn_scales, edge_thr=args.edge_thr,
                        control_end=args.control_end, negative_prompt=args.negative_prompt)
    print(f"{len(cases)} cases, variants {[v[2] for v in variants]}, size {w}x{h}, palette {args.palette}, "
          f"ref policy {args.ref_policy}, SD {coord.sd_id}", flush=True)

    for ci, case in enumerate(cases, 1):
        payloads = collect_case(args.payloads, case)
        ref = choose_reference(payloads, args.ref_policy)
        others = [p for p in payloads if p is not ref]
        for name, scale, dirname in variants:
            out_dir = args.out / dirname
            out_dir.mkdir(parents=True, exist_ok=True)
            if name == "k1":
                for p in (payloads if args.k1_cams == "all" else [ref]):
                    stem = f"{case}_{p.cam}"
                    if (out_dir / f"{stem}.json").exists():
                        continue
                    edge, seg = coord.conditions(p)
                    img, sec, mem = coord.generate(edge, seg, p.caption)
                    img.save(out_dir / f"{stem}.png")
                    (out_dir / f"{stem}.json").write_text(json.dumps(
                        {"case": case, "reference": p.cam, "prompt": p.caption, "seconds": sec, "peak_gpu_mb": mem,
                         "timestamp": p.timestamp, "size": [w, h], "palette": args.palette,
                         "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr}, indent=1))
                    print(f"[{ci}/{len(cases)}] {case} k1 {p.cam}: {sec:.1f} s, peak {mem:.0f} MB", flush=True)
                continue
            if name == "prompt_refine":
                # base = the existing prompt_only master view (else generated exactly like prompt_only), then small cars are redrawn
                if (out_dir / f"{case}.json").exists():
                    continue
                base_dir = args.out / "prompt_only"
                if (base_dir / f"{case}.png").exists() and (base_dir / f"{case}.json").exists():
                    base = Image.open(base_dir / f"{case}.png").convert("RGB")
                    meta = json.loads((base_dir / f"{case}.json").read_text())
                    base_src = "existing prompt_only result"
                else:
                    prompt = fuse_prompt([ref.caption] + [p.caption for p in others])
                    edge, seg = coord.conditions(ref)
                    base, sec, mem = coord.generate(edge, seg, prompt, None, 0.0)
                    meta = {"case": case, "variant": "prompt_only", "ip_adapter_scale": 0.0, "ip_adapter_source": "none",
                            "reference": ref.cam, "supporting": [p.cam for p in others], "timestamp": ref.timestamp, "prompt": prompt,
                            "seconds": sec, "peak_gpu_mb": mem, "size": [w, h], "palette": args.palette, "ref_policy": args.ref_policy,
                            "seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": None,
                            "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr}
                    base_src = "generated here like prompt_only (not saved as prompt_only)"
                refined, info = refine_small(coord, base, ref)
                refined.save(out_dir / f"{case}.png")
                meta = dict(meta, variant="prompt_refine", base=base_src, base_seconds=meta["seconds"],
                            seconds=meta["seconds"] + info["seconds"], refine_seconds=info["seconds"], refine=info,
                            refine_settings={"window": REFINE_WIN, "upscale": REFINE_UP, "strength": REFINE_STRENGTH, "feather_px": REFINE_FEATHER,
                                             "max_windows": REFINE_MAX_WINDOWS, "min_area": REFINE_MIN_AREA, "max_side": REFINE_MAX_SIDE,
                                             "prompt": REFINE_PROMPT, "negative_prompt": REFINE_NEGATIVE, "seed": f"{coord.seed} + window index"})
                (out_dir / f"{case}.json").write_text(json.dumps(meta, indent=1))
                print(f"[{ci}/{len(cases)}] {case} prompt_refine: {info['n_small_blobs']} small blobs, {info['n_windows']} windows "
                      f"({info['uncovered_blobs']} uncovered), {len(info['failures'])} failures, {info['seconds']:.1f} s refine", flush=True)
                continue
            if (out_dir / f"{case}.json").exists():
                continue
            prompt = fuse_prompt([ref.caption] + [p.caption for p in others])
            donor = None
            if name == "prompt_shuffled":      # control: Rec1 caption + captions of the NEXT case's supporting cameras
                donor = cases[ci % len(cases)]
                d_pay = collect_case(args.payloads, donor)
                d_ref = choose_reference(d_pay, args.ref_policy)
                prompt = fuse_prompt([ref.caption] + [p.caption for p in d_pay if p is not d_ref])
            edge, seg = coord.conditions(ref)
            embed, src = None, "none"
            if name == "ipa_seg" and others:
                embed = coord.image_embedding([seg_condition(p.seg, coord.size, args.palette) for p in others])
                src = "support segmentation maps"
            elif name == "ipa_recon" and others:
                k1_dir = args.out / "k1"
                miss = [p.cam for p in others if not (k1_dir / f"{case}_{p.cam}.png").exists()]
                if miss:
                    raise SystemExit(f"ipa_recon needs k1 reconstructions of {miss} for {case}; run k1 with --k1-cams all first")
                embed = coord.image_embedding([Image.open(k1_dir / f"{case}_{p.cam}.png").convert("RGB") for p in others])
                src = "support k1 reconstructions"
            img, sec, mem = coord.generate(edge, seg, prompt, embed, scale)
            img.save(out_dir / f"{case}.png")
            (out_dir / f"{case}.json").write_text(json.dumps(
                {"case": case, "variant": name, "ip_adapter_scale": scale if embed is not None else 0.0,
                 "ip_adapter_source": src, "reference": ref.cam, "supporting": [p.cam for p in others],
                 "timestamp": ref.timestamp, "prompt": prompt, "seconds": sec, "peak_gpu_mb": mem,
                 "size": [w, h], "palette": args.palette, "ref_policy": args.ref_policy,
                 "seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": donor,
                 "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr, "control_end": coord.control_end,
                 "negative_prompt": coord.negative_prompt}, indent=1))
            print(f"[{ci}/{len(cases)}] {case} {dirname} (ref {ref.cam}, {len(others)} supporting): "
                  f"{sec:.1f} s, peak {mem:.0f} MB | {prompt}", flush=True)
    print("COORDINATOR_DONE", flush=True)


if __name__ == "__main__":
    main()
