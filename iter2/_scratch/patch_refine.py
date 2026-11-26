from pathlib import Path

# ---------------------------------------------------------------- coordinator.py: prompt_refine
p = Path("coordinator.py")
t = p.read_text(encoding="utf-8")


def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70])
    t = t.replace(old, new)


HELPERS = '''# ---------------------------------------------------------------- small-vehicle refinement (prompt_refine)
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


'''
rep("def parse_variant(spec):", HELPERS + "def parse_variant(spec):")
rep('if name not in ("k1", "prompt_only", "prompt_shuffled", "ipa_seg", "ipa_recon"):',
    'if name not in ("k1", "prompt_only", "prompt_shuffled", "prompt_refine", "ipa_seg", "ipa_recon"):')

BRANCH = '''                continue
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
'''
rep('''                continue
            if (out_dir / f"{case}.json").exists():
                continue
            prompt = fuse_prompt([ref.caption] + [p.caption for p in others])
''', BRANCH)
rep("The architecture document does not say what image the IP-Adapter receives",
    "  prompt_refine  the prompt_only master view with its small vehicles (blob area >= 12 px, box side <= 48 px in Rec1's\n"
    "               segmentation map) redrawn: 128x128 windows (max 8) upscaled 4x, SD + the same ControlNets in img2img mode\n"
    "               (strength 0.5), downscaled and pasted back with a feathered mask\n"
    "The architecture document does not say what image the IP-Adapter receives")
p.write_text(t, encoding="utf-8")
print("coordinator.py patched")

# ---------------------------------------------------------------- analysis.py: separate output folder
p = Path("analysis.py")
t = p.read_text(encoding="utf-8")
rep('    ap.add_argument("--no-overlays", action="store_true")\n',
    '    ap.add_argument("--no-overlays", action="store_true")\n    ap.add_argument("--analysis-dir", type=Path, default=None, help="write the analysis here instead of <out>/analysis")\n')
rep('ana = args.out / "analysis"', 'ana = args.analysis_dir or args.out / "analysis"')
p.write_text(t, encoding="utf-8")
print("analysis.py patched")
