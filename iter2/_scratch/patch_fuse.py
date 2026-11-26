from pathlib import Path
p = Path("coordinator.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("DEFAULT_IP_SCALE = 0.5\n", "DEFAULT_IP_SCALE = 0.5\nFUSE_IP_SCALE, FUSE_STRENGTH = 1.0, 0.5            # Damir's fusion: IP-Adapter at the library default, img2img strength 0.5\n")
rep("def parse_variant(spec):", '''def fuse_i2i(coord, init, edge, seg, prompt, embed, ip_scale, strength):
    """Damir's fusion (17 Nov 2026): img2img from the main camera's reconstruction (noise added by `strength`), the main camera's edge and
    segmentation maps on the ControlNets, the supporting cameras' reconstructions on the IP-Adapter (mean CLIP image embedding), global caption.
    embed=None or ip_scale=0 runs the same pass without the IP-Adapter (the control)."""
    from diffusers import StableDiffusionControlNetImg2ImgPipeline
    torch = coord.torch
    if not hasattr(coord, "i2i"):
        coord.i2i = StableDiffusionControlNetImg2ImgPipeline(**coord.pipe.components, requires_safety_checker=False)
    dtype = coord.pipe.dtype
    pos = embed.to("cuda", dtype) if embed is not None else torch.zeros(1, coord.embed_dim, device="cuda", dtype=dtype)
    embeds = torch.stack([torch.zeros_like(pos), pos])
    coord.pipe.set_ip_adapter_scale(float(ip_scale if embed is not None else 0.0))
    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); t0 = time.perf_counter()
    img = coord.i2i(prompt=prompt, image=init, control_image=[edge, seg], strength=strength, num_inference_steps=coord.steps,
                    guidance_scale=coord.guidance, controlnet_conditioning_scale=list(coord.cn_scales), control_guidance_end=coord.control_end,
                    ip_adapter_image_embeds=[embeds], generator=torch.Generator(device="cuda").manual_seed(coord.seed)).images[0]
    torch.cuda.synchronize()
    return img, time.perf_counter() - t0, torch.cuda.max_memory_allocated() / 2**20


def parse_variant(spec):''')
rep('''    scale = float(scale) if scale else (DEFAULT_IP_SCALE if name.startswith("ipa") else 0.0)
    if name not in ("k1", "prompt_only", "prompt_shuffled", "prompt_refine", "ipa_seg", "ipa_recon"):
        raise SystemExit(f"unknown variant {spec}")
    return name, scale, (name if scale == DEFAULT_IP_SCALE or not name.startswith("ipa") else f"{name}_s{scale:g}")''',
'''    default = FUSE_IP_SCALE if name == "fuse" else (DEFAULT_IP_SCALE if name.startswith("ipa") else 0.0)
    scale = float(scale) if scale else default
    if name not in ("k1", "prompt_only", "prompt_shuffled", "prompt_refine", "ipa_seg", "ipa_recon", "fuse", "fuse_noip"):
        raise SystemExit(f"unknown variant {spec}")
    if name == "fuse":
        return name, scale, (name if scale == FUSE_IP_SCALE else f"fuse_s{scale:g}")
    return name, scale, (name if scale == DEFAULT_IP_SCALE or not name.startswith("ipa") else f"{name}_s{scale:g}")''')
rep('    ap.add_argument("--negative-prompt", default=None)\n', '''    ap.add_argument("--negative-prompt", default=None)
    ap.add_argument("--fuse-main", type=Path, default=None, help="fuse / fuse_noip: folder with the main reconstructions caseK_camJ.png")
    ap.add_argument("--fuse-support", type=Path, default=None, help="fuse: folder with the supporting cameras' reconstructions caseK_camJ.png")
    ap.add_argument("--fuse-strength", type=float, default=FUSE_STRENGTH, help="img2img strength of the fusion pass")
''')
rep('''            if name == "prompt_refine":\n''', '''            if name in ("fuse", "fuse_noip"):
                if (out_dir / f"{case}.json").exists():
                    continue
                if args.fuse_main is None or (name == "fuse" and args.fuse_support is None):
                    raise SystemExit("fuse needs --fuse-main and --fuse-support (fuse_noip needs --fuse-main)")
                main_path = args.fuse_main / f"{case}_{ref.cam}.png"
                sup_paths = [args.fuse_support / f"{case}_{p.cam}.png" for p in others] if name == "fuse" else []
                missing = [str(q) for q in [main_path] + sup_paths if not q.exists()]
                if missing:
                    print(f"[{ci}/{len(cases)}] {case} {dirname}: skipped, missing {missing[:3]}", flush=True)
                    continue
                init = Image.open(main_path).convert("RGB")
                if init.size != coord.size:
                    init = init.resize(coord.size, Image.LANCZOS)
                edge, seg = coord.conditions(ref)
                prompt = fuse_prompt([ref.caption] + [p.caption for p in others])
                embed = coord.image_embedding([Image.open(q).convert("RGB") for q in sup_paths]) if sup_paths else None
                img, sec, mem = fuse_i2i(coord, init, edge, seg, prompt, embed, scale if name == "fuse" else 0.0, args.fuse_strength)
                img.save(out_dir / f"{case}.png")
                (out_dir / f"{case}.json").write_text(json.dumps(
                    {"case": case, "variant": name, "reference": ref.cam, "supporting": [p.cam for p in others], "timestamp": ref.timestamp,
                     "prompt": prompt, "main_reconstruction": str(main_path), "supporting_reconstructions": [str(q) for q in sup_paths],
                     "ip_adapter_scale": scale if (name == "fuse" and embed is not None) else 0.0, "strength": args.fuse_strength,
                     "seconds": sec, "peak_gpu_mb": mem, "size": [w, h], "palette": args.palette, "seed": coord.seed, "steps": coord.steps,
                     "guidance": coord.guidance, "cn_scales": list(coord.cn_scales)}, indent=1))
                print(f"[{ci}/{len(cases)}] {case} {dirname} (main {ref.cam}, {len(sup_paths)} supporting reconstructions): {sec:.1f} s, peak {mem:.0f} MB", flush=True)
                continue
            if name == "prompt_refine":\n''')
p.write_text(t, encoding="utf-8"); print("coordinator: fuse / fuse_noip added")
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
rep('''    "v3_identity":''', '''    "rw_fuse":             ("rw", "results/rw_fuse/fuse/case{c}.png", "Damir's fusion: img2img from the main reconstruction (paper settings, strength 0.5), main seg+edge on the ControlNets, supporting reconstructions on the IP-Adapter (scale 1.0), global caption"),
    "rw_fuse_noip":        ("rw", "results/rw_fuse/fuse_noip/case{c}.png", "control: the same img2img pass without the IP-Adapter"),
    "v3_fuse":             ("v3", "results/v3_fuse/fuse/case{c}.png", "Damir's fusion (as rw_fuse)"),
    "v3_fuse_noip":        ("v3", "results/v3_fuse/fuse_noip/case{c}.png", "control: the same img2img pass without the IP-Adapter"),
    "v3_identity":''')
rep('''GROUPS["cs_rerun"] = ["cs2_paper_seg1024"]''', '''GROUPS["cs_rerun"] = ["cs2_paper_seg1024"]
GROUPS["fusion"] = ["rw_fuse", "rw_fuse_noip", "v3_fuse", "v3_fuse_noip"]''')
rep('''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"]''',
    '''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"] + GROUPS["fusion"]''')
rep('''    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),''', '''    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),
    ("fuse", "paper_k1", "Damir's fusion vs the main reconstruction (his single-camera MMSD at paper settings)"),
    ("fuse", "fuse_noip", "supporting reconstructions through the IP-Adapter vs re-denoising only"),
    ("fuse_noip", "paper_k1", "re-denoising the main reconstruction alone (img2img, no IP-Adapter)"),''')
p.write_text(t, encoding="utf-8"); print("vlm_judge: fusion setups added")
