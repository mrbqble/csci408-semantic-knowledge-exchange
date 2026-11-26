#!/usr/bin/env python3
"""Stage-by-stage process diagrams of the multi-camera MMSD reconstruction (one per case), vertical layout:
cameras + raw photos -> payload per device -> reconstruction of each device -> fusion conditions (ControlNet on the main maps,
img2img noise on the main reconstruction, IP-Adapter on the supporting reconstructions) -> final reconstruction of the main camera.
Usage: python make_process_diagrams.py <out_dir>
"""
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import paths

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
CASES = [("rw", 1, "parked cars along a road"), ("rw", 169, "bus close-up at a stop"), ("rw", 349, "crosswalk intersection"),
         ("v3", 37, "empty junction"), ("v3", 72, "seaside road at sunset"), ("v3", 12, "wide junction")]
DS = {"v3": (paths.CARLA_V3, ".jpg", "data/v3_payloads", "data/v3_native", "CARLA simulator (v3)"),
      "rw": (paths.REAL_WORLD_CORE, ".png", "data/rw_core_payloads", "data/rw_native", "Real world (Astana, 3 phones)")}


def font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


T, TB, H1, H2, TX, TS = font("arialbd.ttf", 44), font("arialbd.ttf", 30), font("arialbd.ttf", 26), font("arialbd.ttf", 22), font("arial.ttf", 21), font("arial.ttf", 18)
INK, GREY, MAIN_C, SUP_C = (25, 25, 25), (110, 110, 110), (192, 57, 43), (52, 101, 164)
BANDS = [(247, 247, 247), (255, 255, 255)]

W = 2600; LBL_W = 330; X0 = 360; MAIN_W = 780; SEP_X = X0 + MAIN_W + 45; SUP_X0 = SEP_X + 45; SUP_TOT = W - 40 - SUP_X0


def img(path, w, h):
    return Image.open(path).convert("RGB").resize((int(w), int(h)), Image.LANCZOS)


def arrow(d, p1, p2, color=INK, width=4, head=16):
    import math
    d.line([p1, p2], fill=color, width=width)
    a = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    l, r = (p2[0] - head * math.cos(a - 0.45), p2[1] - head * math.sin(a - 0.45)), (p2[0] - head * math.cos(a + 0.45), p2[1] - head * math.sin(a + 0.45))
    d.polygon([p2, l, r], fill=color)


def elbow(d, pts, color=INK, width=4):
    for a, b in zip(pts[:-2], pts[1:-1]):
        d.line([a, b], fill=color, width=width)
    arrow(d, pts[-2], pts[-1], color, width)


def rbox(d, rect, fill, outline, width=3, r=18):
    d.rounded_rectangle(rect, radius=r, fill=fill, outline=outline, width=width)


def ctext(d, cx, y, text, f, fill=INK):
    w = d.textlength(text, font=f); d.text((cx - w / 2, y), text, font=f, fill=fill)


def dashed_v(d, x, y1, y2, color=GREY, dash=18, gap=12, width=3):
    y = y1
    while y < y2:
        d.line([(x, y), (x, min(y + dash, y2))], fill=color, width=width); y += dash + gap


def caption_of(pay, c, cam):
    return (Path(pay) / f"case{c}" / f"{cam}_caption.txt").read_text(encoding="utf-8").strip()


def diagram(ds, c, scene):
    root, ext, pay_main, pay_sup, ds_name = DS[ds]
    cams = sorted(p.stem for p in (root / f"case{c}").iterdir() if p.stem.startswith("cam") and p.suffix == ext)
    sups = [x for x in cams if x != "cam1"]; k = len(sups); gap = 22
    sw = min(560, (SUP_TOT - (k - 1) * gap) / k); sh = sw * 9 / 16
    sx = [SUP_X0 + (SUP_TOT - (k * sw + (k - 1) * gap)) / 2 + i * (sw + gap) for i in range(k)]
    mw, mh = MAIN_W, MAIN_W * 9 / 16
    side = k <= 3                                   # supporting payload: seg and edge side by side (else stacked)
    pw = (sw - 10) / 2 if side else sw; ph = pw * 9 / 16
    # vertical layout
    y_title = 30
    rows = {}
    y = 150
    rows["A"] = (y, y + 70 + 20 + max(mh, sh) + 40); y = rows["A"][1]
    pay_h = max(208 + 40 + 60, (ph + 30) * (1 if side else 2) + 60)
    rows["B"] = (y, y + 60 + pay_h); y = rows["B"][1]
    rows["C"] = (y, y + 70 + max(mh, sh) + 50); y = rows["C"][1]
    rows["D"] = (y, y + 380); y = rows["D"][1]
    fw = 1150; fh = fw * 9 / 16
    rows["E"] = (y, y + 120 + fh + 70); y = rows["E"][1]
    H = int(y + 150)
    sheet = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(sheet)
    labels = {"A": ("1  Cameras and raw photos", "Several cameras photograph the same scene at the same moment. Cam1 is the main / reference camera."),
              "B": ("2  Sender: payload per device", "Each device sends a segmentation map, an edge map and a short caption instead of the photo."),
              "C": ("3  Receiver step 1: reconstruction of each device", "Each device's view is rebuilt from its own payload (single-camera MMSD: Stable Diffusion 1.5 + 2 ControlNets)."),
              "D": ("4  Receiver step 2: fusion conditions", "ControlNet keeps the main view's layout; img2img noise is added to the main reconstruction only; the supporting reconstructions enter through the IP-Adapter."),
              "E": ("5  Final reconstruction", "One Stable Diffusion 1.5 img2img pass combines everything into the main camera's final image.")}
    for i, key in enumerate("ABCDE"):
        y1, y2 = rows[key]
        d.rectangle([0, y1, W, y2], fill=BANDS[i % 2])
        d.line([(0, y1), (W, y1)], fill=(215, 215, 215), width=2)
        name, expl = labels[key]
        d.text((28, y1 + 22), name.split("  ")[0], font=font("arialbd.ttf", 54), fill=MAIN_C)
        yy = y1 + 28
        for line in textwrap.wrap(name.split("  ")[1], 20):
            d.text((90, yy), line, font=H2, fill=INK); yy += 28
        yy = max(yy + 10, y1 + 96)                   # explanation always starts below the big stage number
        for line in textwrap.wrap(expl, 30):
            d.text((28, yy), line, font=TS, fill=GREY); yy += 23
    d.line([(LBL_W, 140), (LBL_W, rows["E"][1])], fill=(215, 215, 215), width=2)
    # title
    d.text((28, y_title), f"Multi-camera MMSD reconstruction, stage by stage: {ds_name}, case {c}", font=T, fill=INK)
    d.text((30, y_title + 62), f"{len(cams)} cameras ({scene}). Main / reference camera: cam1. Supporting cameras: {', '.join(sups)}.", font=TX, fill=GREY)
    # dashed separator and column headers
    dashed_v(d, SEP_X, rows["A"][0] + 10, rows["D"][0] + 250)
    ctext(d, X0 + mw / 2, rows["A"][0] + 8, "MAIN / REFERENCE CAMERA", H2, MAIN_C)
    ctext(d, SUP_X0 + SUP_TOT / 2, rows["A"][0] + 8, "SUPPORTING CAMERAS (same steps for each)", H2, SUP_C)
    # stage A: camera boxes + photos
    ya = rows["A"][0] + 44
    def cam_box(cx, name, color, wbox):
        rbox(d, [cx - wbox / 2, ya, cx + wbox / 2, ya + 44], (255, 255, 255), color, 3, 12); ctext(d, cx, ya + 9, name, H2, color)
    cam_box(X0 + mw / 2, "Cam1 (main / reference)", MAIN_C, 360)
    for i, cam in enumerate(sups):
        cam_box(sx[i] + sw / 2, cam.capitalize(), SUP_C, min(200, sw - 10))
    yp = ya + 70
    sheet.paste(img(root / f"case{c}" / f"cam1{ext}", mw, mh), (X0, int(yp)))
    d.rectangle([X0, yp, X0 + mw, yp + mh], outline=MAIN_C, width=4)
    for i, cam in enumerate(sups):
        sheet.paste(img(root / f"case{c}" / f"{cam}{ext}", sw, sh), (int(sx[i]), int(yp)))
    d.text((X0, yp + mh + 6), "raw photo (never transmitted)", font=TS, fill=GREY)
    # stage B: payloads
    yb = rows["B"][0] + 50
    arrow(d, (X0 + mw / 2, yp + mh + 30), (X0 + mw / 2, yb - 6))
    for i in range(k):
        arrow(d, (sx[i] + sw / 2, yp + sh + 8), (sx[i] + sw / 2, yb - 6), SUP_C)
    tw = (mw - 20) / 2; th = tw * 9 / 16
    sheet.paste(img(Path(pay_main) / f"case{c}" / "cam1_seg.webp", tw, th), (X0, int(yb)))
    sheet.paste(img(Path(pay_main) / f"case{c}" / "cam1_edge.webp", tw, th), (int(X0 + tw + 20), int(yb)))
    d.text((X0, yb + th + 6), "segmentation map", font=TX, fill=INK); d.text((X0 + tw + 20, yb + th + 6), "edge map", font=TX, fill=INK)
    cap = caption_of(pay_main, c, "cam1")
    rbox(d, [X0, yb + th + 40, X0 + mw, yb + th + 40 + 50], (255, 255, 255), (200, 200, 200), 2, 10)
    d.text((X0 + 12, yb + th + 52), ("+ caption (text): \"" + cap + "\"")[:75], font=TS, fill=GREY)
    for i, cam in enumerate(sups):
        if side:
            sheet.paste(img(Path(pay_sup) / f"case{c}" / f"{cam}_seg.webp", pw, ph), (int(sx[i]), int(yb)))
            sheet.paste(img(Path(pay_sup) / f"case{c}" / f"{cam}_edge.webp", pw, ph), (int(sx[i] + pw + 10), int(yb)))
            d.text((sx[i], yb + ph + 4), "seg", font=TS, fill=INK); d.text((sx[i] + pw + 10, yb + ph + 4), "edge", font=TS, fill=INK)
            yc = yb + ph + 30
        else:
            sheet.paste(img(Path(pay_sup) / f"case{c}" / f"{cam}_seg.webp", pw, ph), (int(sx[i]), int(yb)))
            sheet.paste(img(Path(pay_sup) / f"case{c}" / f"{cam}_edge.webp", pw, ph), (int(sx[i]), int(yb + ph + 26)))
            d.text((sx[i], yb + ph + 2), "seg", font=TS, fill=INK); d.text((sx[i], yb + 2 * ph + 28), "edge", font=TS, fill=INK)
            yc = yb + 2 * ph + 52
        d.text((sx[i], yc), "+ caption", font=TS, fill=GREY)
    # stage C: reconstruction of each device
    yc0 = rows["C"][0] + 50
    arrow(d, (X0 + mw / 2, yb + th + 96), (X0 + mw / 2, yc0 - 6))
    for i in range(k):
        bottom = yb + (ph + 56 if side else 2 * ph + 80)
        arrow(d, (sx[i] + sw / 2, bottom), (sx[i] + sw / 2, yc0 - 6), SUP_C)
    sheet.paste(img(f"results/{ds}_paper/k1/case{c}_cam1.png", mw, mh), (X0, int(yc0)))
    d.rectangle([X0, yc0, X0 + mw, yc0 + mh], outline=MAIN_C, width=4)
    d.text((X0, yc0 + mh + 6), "main reconstruction (= single-camera baseline)", font=TX, fill=INK)
    for i, cam in enumerate(sups):
        sheet.paste(img(f"results/{ds}_support/k1/case{c}_{cam}.png", sw, sh), (int(sx[i]), int(yc0)))
        d.text((sx[i], yc0 + sh + 4), f"{cam} reconstruction", font=TS, fill=INK)
    # stage D: fusion conditions
    yd = rows["D"][0] + 40
    cn = [X0, yd, X0 + 500, yd + 290]
    rbox(d, cn, (232, 241, 251), SUP_C, 3)
    ctext(d, (cn[0] + cn[2]) / 2, yd + 12, "ControlNet", H1, SUP_C)
    ctext(d, (cn[0] + cn[2]) / 2, yd + 46, "main segmentation map + main edge map", TS, INK)
    iw = 225; ih = iw * 9 / 16
    sheet.paste(img(Path(pay_main) / f"case{c}" / "cam1_seg.webp", iw, ih), (int(cn[0] + 18), int(yd + 82)))
    sheet.paste(img(Path(pay_main) / f"case{c}" / "cam1_edge.webp", iw, ih), (int(cn[0] + 30 + iw), int(yd + 82)))
    d.text((cn[0] + 18, yd + 82 + ih + 6), "segmentation", font=TS, fill=INK); d.text((cn[0] + 30 + iw, yd + 82 + ih + 6), "edge", font=TS, fill=INK)
    nz = [X0 + 530, yd + 60, X0 + mw, yd + 230]
    rbox(d, nz, (255, 244, 224), (196, 120, 20), 3)
    ctext(d, (nz[0] + nz[2]) / 2, nz[1] + 22, "img2img noise", H1, (160, 90, 0))
    ctext(d, (nz[0] + nz[2]) / 2, nz[1] + 62, "strength 0.5", TX, INK)
    ctext(d, (nz[0] + nz[2]) / 2, nz[1] + 96, "added to the main", TS, INK)
    ctext(d, (nz[0] + nz[2]) / 2, nz[1] + 120, "reconstruction only", TS, INK)
    # arrows into stage D
    elbow(d, [(X0 + mw - 60, yc0 + mh + 34), (X0 + mw - 60, yd + 30), ((nz[0] + nz[2]) / 2, yd + 30), ((nz[0] + nz[2]) / 2, nz[1] - 4)], (196, 120, 20))
    elbow(d, [(X0 - 22, yb + th / 2), (X0 - 22, yd + 140), (cn[0] - 4, yd + 140)], SUP_C)
    d.text((X0 - 18, yb + th + 100), "", font=TS)
    ip = [SUP_X0 + SUP_TOT / 2 - 230, yd + 70, SUP_X0 + SUP_TOT / 2 + 230, yd + 210]
    rbox(d, ip, (236, 247, 236), (46, 125, 50), 3)
    ctext(d, (ip[0] + ip[2]) / 2, ip[1] + 26, "IP-Adapter", H1, (46, 125, 50))
    ctext(d, (ip[0] + ip[2]) / 2, ip[1] + 68, "the supporting reconstructions", TS, INK)
    ctext(d, (ip[0] + ip[2]) / 2, ip[1] + 92, "(mean of their image embeddings)", TS, GREY)
    for i in range(k):
        arrow(d, (sx[i] + sw / 2, yc0 + sh + 30), ((ip[0] + ip[2]) / 2 + (i - (k - 1) / 2) * 60, ip[1] - 4), (46, 125, 50))
    # stage E: final reconstruction
    ye = rows["E"][0] + 40
    fx = X0 + (W - 40 - X0 - fw) / 2
    fb = [fx - 30, ye, fx + fw + 30, ye + 90 + fh + 20]
    rbox(d, fb, (253, 242, 242), MAIN_C, 4)
    ctext(d, (fb[0] + fb[2]) / 2, ye + 12, "Final reconstruction of the main / reference camera", TB, MAIN_C)
    ctext(d, (fb[0] + fb[2]) / 2, ye + 54, "Stable Diffusion 1.5 img2img: noised main reconstruction + ControlNet + IP-Adapter, prompt = global caption of all cameras", TS, INK)
    sheet.paste(img(f"results/{ds}_fuse/fuse/case{c}.png", fw, fh), (int(fx), int(ye + 90)))
    for src in (((cn[0] + cn[2]) / 2, cn[3]), ((nz[0] + nz[2]) / 2, nz[3]), ((ip[0] + ip[2]) / 2, ip[3])):
        arrow(d, (src[0], src[1] + 4), ((fb[0] + fb[2]) / 2 + (src[0] - (fb[0] + fb[2]) / 2) * 0.35, ye - 6), INK, 5, 20)
    # footer
    gcap = ", ".join(dict.fromkeys(caption_of(pay_main, c, x) for x in ["cam1"] + sups))
    yf = rows["E"][1] + 20
    for line in textwrap.wrap("Global caption (all cameras): " + gcap, 190)[:2]:
        d.text((28, yf), line, font=TS, fill=GREY); yf += 24
    d.text((28, yf + 6), "Main camera: seed-paper payload (map at half resolution, edges at full resolution), reconstructed at 1920x1088. Supporting cameras: 896x512 payload and reconstruction."
           + (" Real-world photos: internal use only." if ds == "rw" else ""), font=TS, fill=GREY)
    out = OUT / f"process_{'real_world' if ds == 'rw' else 'carla'}_case{c:03d}.png"
    sheet.save(out); sheet.convert("RGB").save(out.with_suffix(".jpg"), quality=90)
    print("wrote", out, sheet.size)
    return sheet


def main():
    pages = [diagram(ds, c, s) for ds, c, s in CASES]
    pages[0].convert("RGB").save(OUT / "process_diagrams_all_cases.pdf", save_all=True, append_images=[p.convert("RGB") for p in pages[1:]], resolution=150)
    print("DIAGRAMS_DONE")


if __name__ == "__main__":
    main()
