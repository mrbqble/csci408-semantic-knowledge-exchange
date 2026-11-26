#!/usr/bin/env python3
"""(1) Images for Damir: cases where multi-camera fusion fixes a single-camera failure (original | baseline | fusion).
(2) Step-by-step pipeline figures for the report, one real-world and one simulated case (Prof. Zorbas's request).
Usage: python make_deliverables.py <damir_out_dir>
"""
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import paths

DAMIR_OUT = Path(sys.argv[1])
STEPS_OUT = Path("report_kit/figures/pipeline_steps")
DS = {"v3": {"photos": paths.CARLA_V3, "ext": ".jpg", "pay": "data/v3_payloads", "native": "data/v3_native", "label": "CARLA v3 (simulated)"},
      "rw": {"photos": paths.REAL_WORLD_CORE, "ext": ".png", "pay": "data/rw_core_payloads", "native": "data/rw_native", "label": "Real-world, Astana"}}
RW_CASES = [1 + 6 * k for k in range(61)]
try:
    F, FB, FS = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 24), ImageFont.truetype("arial.ttf", 16)
except OSError:
    F = FB = FS = ImageFont.load_default()


def judge(run):
    out = {}
    for line in open(f"results/vlm/{run}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
            out[r["case"]] = r
    return out


def ok(r):
    return r["numbers"]["score"] * r["positions"]["score"] == 1


def verdict(r):
    return f"count {'OK' if r['numbers']['score'] else 'WRONG'}, positions {'OK' if r['positions']['score'] else 'WRONG'}"


def cams(ds, c):
    return sorted(p.stem for p in (DS[ds]["photos"] / f"case{c}").iterdir() if p.stem.startswith("cam") and p.suffix == DS[ds]["ext"])


def photo(ds, c, cam):
    return Image.open(DS[ds]["photos"] / f"case{c}" / f"{cam}{DS[ds]['ext']}").convert("RGB")


def fit(im, w, h):
    return im.convert("RGB").resize((w, h), Image.LANCZOS)


def label(d, xy, text, font=F, fill="black", bg=None):
    if bg:
        x, y = xy; d.rectangle([x - 4, y - 2, x + d.textlength(text, font=font) + 4, y + font.size + 4], fill=bg)
    d.text(xy, text, fill=fill, font=font)


def wrap(d, x, y, text, width_chars, font=FS, fill="black", line_h=20):
    for line in textwrap.wrap(text, width_chars):
        d.text((x, y), line, fill=fill, font=font); y += line_h
    return y


# ---------------------------------------------------------------------------------------------------- (1) Damir
def damir_case(ds, c, S, Fz, out):
    W, H, PAD = 640, 360, 12
    others = [cam for cam in cams(ds, c) if cam != "cam1"]
    sw = (3 * W + 2 * PAD - (len(others) - 1) * PAD) // max(len(others), 1)
    sw = min(sw, W); sh = int(sw * 9 / 16)
    sheet = Image.new("RGB", (3 * W + 4 * PAD, 60 + H + 70 + 40 + sh + 120), "white")
    d = ImageDraw.Draw(sheet)
    label(d, (PAD, 14), f"{DS[ds]['label']}, case {c}: multi-camera fusion fixes a failure of the single-camera baseline", FB)
    tiles = [(photo(ds, c, "cam1"), "Original (main camera)", None),
             (Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png"), "Baseline: single-camera MMSD", S),
             (Image.open(f"results/{ds}_fuse/fuse/case{c}.png"), f"Ours: multi-camera fusion ({len(others)} other cameras)", Fz)]
    for i, (im, lab, r) in enumerate(tiles):
        x = PAD + i * (W + PAD)
        sheet.paste(fit(im, W, H), (x, 60))
        label(d, (x, 60 + H + 8), lab, F)
        if r is not None:
            label(d, (x, 60 + H + 36), "VLM judge: " + verdict(r), F, fill=(0, 120, 0) if ok(r) else (190, 0, 0))
    y = 60 + H + 80
    label(d, (PAD, y), "Other cameras of the same scene (their payloads feed the fusion):", F)
    for i, cam in enumerate(others):
        sheet.paste(fit(photo(ds, c, cam), sw, sh), (PAD + i * (sw + PAD), y + 30))
        label(d, (PAD + i * (sw + PAD) + 6, y + 34), cam, FS, fill="white", bg="black")
    y = y + 30 + sh + 10
    y = wrap(d, PAD, y, "Judge on the baseline: " + " ".join(S["numbers"]["text"].split())[:330], 190)
    wrap(d, PAD, y + 4, "Judge on the fusion: " + " ".join(Fz["numbers"]["text"].split())[:330], 190)
    sheet.save(out / f"{'carla' if ds == 'v3' else 'real_world'}_case{c:03d}.jpg", quality=88)


def damir():
    DAMIR_OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for ds in ("v3", "rw"):
        S, Fz = judge(f"{ds}_paper_k1"), judge(f"{ds}_fuse")
        cases = range(1, 113) if ds == "v3" else RW_CASES
        fixed = [c for c in cases if c in S and c in Fz and not ok(S[c]) and ok(Fz[c])]
        for c in fixed:
            damir_case(ds, c, S[c], Fz[c], DAMIR_OUT)
            index.append(f"{DS[ds]['label']}, case {c}: {len(cams(ds, c))} cameras")
        print(ds, "fixed cases:", len(fixed))
    (DAMIR_OUT / "README.txt").write_text(
        "Cases where the multi-camera fusion (Damir's pipeline: img2img from the main reconstruction, strength 0.5; ControlNets on the main camera's\n"
        "segmentation and edge maps; IP-Adapter on the other cameras' reconstructions; global caption) passes the VLM judge (car count and positions)\n"
        "while the single-camera MMSD baseline fails. All such cases are included (31 CARLA v3, 7 real-world), not a selection.\n"
        "Each image: original | baseline | fusion, the other cameras' photos, and the judge's answers. Real-world photos: internal use only.\n\n"
        + "\n".join(index) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------------- (2) step figures
def noised_main(ds, c):
    """The fusion's starting point: the main reconstruction after noise is added at strength 0.5 (same pipeline, seed 42)."""
    import torch
    from coordinator import Coordinator, fuse_i2i  # noqa: F401  (fuse_i2i builds coord.i2i)
    from diffusers import StableDiffusionControlNetImg2ImgPipeline
    global COORD
    if "COORD" not in globals():
        COORD = Coordinator((1920, 1088), "cs")
        COORD.i2i = StableDiffusionControlNetImg2ImgPipeline(**COORD.pipe.components, requires_safety_checker=False)
    pipe = COORD.i2i
    init = Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png").convert("RGB")
    with torch.no_grad():
        pipe.scheduler.set_timesteps(20, device="cuda")
        timesteps, _ = pipe.get_timesteps(20, 0.5, "cuda")
        image = pipe.image_processor.preprocess(init).to("cuda", pipe.dtype)
        lat = pipe.prepare_latents(image, timesteps[:1], 1, 1, pipe.dtype, "cuda", torch.Generator(device="cuda").manual_seed(42))
        dec = pipe.vae.decode(lat / pipe.vae.config.scaling_factor, return_dict=False)[0]
    return pipe.image_processor.postprocess(dec, output_type="pil")[0]


def grid(items, cols, w, h, title, sub=None, caption_h=34):
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 12) + 12, 70 + (30 if sub else 0) + rows * (h + caption_h + 12)), "white")
    d = ImageDraw.Draw(sheet)
    label(d, (12, 14), title, FB)
    y0 = 56
    if sub:
        label(d, (12, 52), sub, FS); y0 = 84
    for i, (im, lab) in enumerate(items):
        x, y = 12 + (i % cols) * (w + 12), y0 + (i // cols) * (h + caption_h + 12)
        sheet.paste(fit(im, w, h), (x, y)); label(d, (x, y + h + 6), lab, FS)
    return sheet


def steps(ds, c, why):
    out = STEPS_OUT / f"{ds}_case{c}"; out.mkdir(parents=True, exist_ok=True)
    cl = cams(ds, c); others = [x for x in cl if x != "cam1"]
    S, Fz, Ctl = judge(f"{ds}_paper_k1")[c], judge(f"{ds}_fuse")[c], judge(f"{ds}_fuse_noip")[c]
    meta = {}
    for cam in cl:
        base = Path(DS[ds]["pay"]) / f"case{c}"
        sz = {k: (base / f"{cam}_{suf}").stat().st_size for k, suf in (("seg_b", "seg.webp"), ("edge_b", "edge.webp"), ("caption_b", "caption.txt"))}
        sz["total_b"] = sum(sz.values()); meta[cam] = sz
    caps = {cam: (Path(DS[ds]["pay"]) / f"case{c}" / f"{cam}_caption.txt").read_text(encoding="utf-8").strip() for cam in cl}
    head = f"{DS[ds]['label']}, case {c} ({len(cl)} cameras)"
    # step 1: inputs
    grid([(photo(ds, c, cam), cam + (" (main camera)" if cam == "cam1" else "")) for cam in cl], 2 if len(cl) == 4 else 3, 640, 360,
         f"Step 1 - Input: each camera photographs the same scene. {head}").save(out / "step1_input_photos.jpg", quality=88)
    # step 2: sender payload
    W, H = 512, 288
    sheet = Image.new("RGB", (3 * (W + 12) + 12 + 380, 70 + len(cl) * (H + 46)), "white"); d = ImageDraw.Draw(sheet)
    label(d, (12, 14), f"Step 2 - Sender: each camera sends a segmentation map, an edge map and a caption. {head}", FB)
    for i, cam in enumerate(cl):
        y = 64 + i * (H + 46)
        tiles = [(photo(ds, c, cam), f"{cam}: photo (not sent)"),
                 (Image.open(Path(DS[ds]["pay"]) / f"case{c}" / f"{cam}_seg.webp"), f"segmentation map {meta[cam].get('seg_b', 0)/1024:.1f} KB"),
                 (Image.open(Path(DS[ds]["pay"]) / f"case{c}" / f"{cam}_edge.webp"), f"edge map {meta[cam].get('edge_b', 0)/1024:.1f} KB")]
        for j, (im, lab) in enumerate(tiles):
            sheet.paste(fit(im, W, H), (12 + j * (W + 12), y)); label(d, (12 + j * (W + 12), y + H + 4), lab, FS)
        wrap(d, 12 + 3 * (W + 12), y + 10, f"caption ({meta[cam].get('caption_b', len(caps[cam]))} B): \"{caps[cam]}\"", 34)
        wrap(d, 12 + 3 * (W + 12), y + 120, f"payload total {meta[cam].get('total_b', 0)/1024:.1f} KB", 34)
    sheet.save(out / "step2_sender_payloads.jpg", quality=88)
    # step 3: per-camera reconstruction
    items = [(Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png"), "cam1: main reconstruction (1920x1088) = single-camera baseline")]
    items += [(Image.open(f"results/{ds}_support/k1/case{c}_{cam}.png"), f"{cam}: supporting reconstruction (896x512)") for cam in others]
    grid(items, 2 if len(items) == 4 else 3, 640, 360, f"Step 3 - Receiver: every camera is reconstructed from its own payload (SD 1.5 + ControlNets). {head}").save(out / "step3_per_camera_reconstructions.jpg", quality=88)
    # step 4: fusion inputs
    noisy = noised_main(ds, c)
    noisy.save(out / "step4_main_reconstruction_with_noise.png")
    gcap = ", ".join(dict.fromkeys(caps[cam] for cam in ["cam1"] + others))
    items = [(Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png"), "main reconstruction"),
             (noisy, "main reconstruction + noise (img2img, strength 0.5)"),
             (Image.open(Path(DS[ds]["pay"]) / f"case{c}" / "cam1_edge.webp"), "ControlNet input 1: main edge map"),
             (Image.open(Path(DS[ds]["pay"]) / f"case{c}" / "cam1_seg.webp"), "ControlNet input 2: main segmentation map")]
    items += [(Image.open(f"results/{ds}_support/k1/case{c}_{cam}.png"), f"IP-Adapter input: {cam} reconstruction") for cam in others]
    sheet = grid(items, 4 if len(items) >= 7 else 3, 480, 270, f"Step 4 - Fusion inputs to Stable Diffusion 1.5. {head}", sub="Prompt (global caption of all cameras): " + gcap[:170])
    sheet.save(out / "step4_fusion_inputs.jpg", quality=88)
    # step 5: output and evaluation
    W, H = 640, 360
    sheet = Image.new("RGB", (4 * (W + 12) + 12, 70 + H + 90 + 150), "white"); d = ImageDraw.Draw(sheet)
    label(d, (12, 14), f"Step 5 - Output and evaluation (VLM judge on the main camera's view). {head}", FB)
    tiles = [(photo(ds, c, "cam1"), "original (main camera)", None), (Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png"), "single-camera baseline", S),
             (Image.open(f"results/{ds}_fuse/fuse_noip/case{c}.png"), "control: same pass, no IP-Adapter", Ctl),
             (Image.open(f"results/{ds}_fuse/fuse/case{c}.png"), "multi-camera fusion (final)", Fz)]
    for i, (im, lab, r) in enumerate(tiles):
        x = 12 + i * (W + 12); sheet.paste(fit(im, W, H), (x, 64)); label(d, (x, 64 + H + 6), lab, F)
        if r is not None:
            label(d, (x, 64 + H + 34), verdict(r), F, fill=(0, 120, 0) if ok(r) else (190, 0, 0))
    y = 64 + H + 76
    y = wrap(d, 12, y, "Judge on the baseline: " + " ".join(S["numbers"]["text"].split())[:300], 240)
    wrap(d, 12, y + 4, "Judge on the fusion: " + " ".join(Fz["numbers"]["text"].split())[:300], 240)
    sheet.save(out / "step5_output_and_evaluation.jpg", quality=88)
    (out / "README.txt").write_text(f"{head}. Chosen as: {why}.\nStep 1 input photos; step 2 payload per camera (sizes from the payload metadata); step 3 per-camera "
                                    f"reconstructions; step 4 fusion inputs (main reconstruction, the same with noise at strength 0.5, ControlNet maps, IP-Adapter images, "
                                    f"global caption); step 5 output and judge verdicts.\nGlobal caption: {gcap}\n", encoding="utf-8")
    print("steps done:", out)


def main():
    damir()
    nc = {int(str(x["case"]).replace("case", "")): x["n_cameras"] for x in json.loads((paths.CARLA_V3 / "manifest.json").read_text())["cases"]}
    Sv, Fv = judge("v3_paper_k1"), judge("v3_fuse")
    v3_case = next(c for c in range(1, 113) if nc.get(c) == 4 and not ok(Sv[c]) and ok(Fv[c]))
    Sr, Fr = judge("rw_paper_k1"), judge("rw_fuse")
    rw_case = next(c for c in RW_CASES if not ok(Sr[c]) and ok(Fr[c]))
    steps("v3", v3_case, "the first 4-camera CARLA case where the fusion fixes a failure of the single-camera baseline")
    steps("rw", rw_case, "the first real-world case where the fusion fixes a failure of the single-camera baseline")
    print("DELIVERABLES_DONE")


if __name__ == "__main__":
    main()
