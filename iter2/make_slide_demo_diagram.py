#!/usr/bin/env python3
"""Landscape stage-by-stage diagram of one CARLA case for the DEMO slide (sized for the area under the slide title:
1704 x 640 slide pixels, rendered at 2x = 3408 x 1280). Stages left to right: photos -> sender payload ->
rebuild of each camera -> fusion pass -> result checked by the judge. CARLA only, so it can live in the public repo.
Usage: python make_slide_demo_diagram.py [case]   (default: CARLA v3 case 6)
"""
import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import paths

C = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = Path("report_kit/figures/slides"); OUT.mkdir(parents=True, exist_ok=True)
ROOT = paths.CARLA_V3 / f"case{C}"
PAY_MAIN, PAY_SUP = Path("data/v3_payloads") / f"case{C}", Path("data/v3_native") / f"case{C}"
REC_MAIN, FUSED = Path(f"results/v3_paper/k1/case{C}_cam1.png"), Path(f"results/v3_fuse/fuse/case{C}.png")
REC_SUP = lambda cam: Path(f"results/v3_support/k1/case{C}_{cam}.png")


def F(name, size):
    for n in (name, "arialbd.ttf" if "b." in name else "arial.ttf"):
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            pass
    return ImageFont.load_default()


B, R = (lambda s: F("segoeuib.ttf", s)), (lambda s: F("segoeui.ttf", s))
BG, NAVY, GREY, STEEL = (236, 236, 236), (43, 45, 66), (74, 78, 90), (61, 90, 128)
RED, GREEN, ORANGE, WHITE = (192, 57, 43), (46, 125, 50), (190, 110, 10), (255, 255, 255)
W, H = 3408, 1280
img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)


def pic(path, w, h):
    im = Image.open(path).convert("RGB")
    r = max(w / im.width, h / im.height)
    im = im.resize((max(int(im.width * r + 0.5), w), max(int(im.height * r + 0.5), h)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))


def paste(path, x, y, w, h, outline=None, width=7):
    img.paste(pic(path, int(w), int(h)), (int(x), int(y)))
    if outline:
        d.rectangle([x - 3, y - 3, x + w + 2, y + h + 2], outline=outline, width=width)


def arrow(p1, p2, color=NAVY, width=8, head=28):
    d.line([p1, p2], fill=color, width=width)
    a = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    d.polygon([p2, (p2[0] - head * math.cos(a - 0.45), p2[1] - head * math.sin(a - 0.45)),
               (p2[0] - head * math.cos(a + 0.45), p2[1] - head * math.sin(a + 0.45))], fill=color)


def wrap(x, y, s, f, width_px, fill=GREY, lh=1.22):
    line, yy = "", y
    for word in s.split():
        t = (line + " " + word).strip()
        if d.textlength(t, font=f) <= width_px:
            line = t
        else:
            d.text((x, yy), line, font=f, fill=fill); yy += f.size * lh; line = word
    if line:
        d.text((x, yy), line, font=f, fill=fill); yy += f.size * lh
    return yy


def runs(x, y, parts, f):
    for s, col in parts:
        d.text((x, y), s, font=f, fill=col); x += d.textlength(s, font=f)


def kb(*files):
    return sum(p.stat().st_size for p in files if p.exists()) / 1024


cams = sorted(p.stem for p in ROOT.iterdir() if p.stem.startswith("cam") and p.suffix == ".jpg")
sups = [c for c in cams if c != "cam1"]
main_kb = kb(PAY_MAIN / "cam1_seg.webp", PAY_MAIN / "cam1_edge.webp", PAY_MAIN / "cam1_caption.txt")
sup_kb = [kb(PAY_SUP / f"{c}_seg.webp", PAY_SUP / f"{c}_edge.webp", PAY_SUP / f"{c}_caption.txt") for c in sups]
buf = io.BytesIO(); Image.open(ROOT / "cam1.jpg").convert("RGB").save(buf, "JPEG", quality=90); jpeg_kb = len(buf.getvalue()) / 1024
caption = (PAY_MAIN / "cam1_caption.txt").read_text(encoding="utf-8").strip()

GAP = 56; CW = [600, 600, 600, 480, 864]; X = [20]
for w in CW[:-1]:
    X.append(X[-1] + w + GAP)
YM, MH = 205, 338                       # main row: 600 x 338
CELL, CH, YS = (600 - 16) // 2, 164, 735  # supporting row: 2 x 2 grid of 292 x 164
grid = [(0, 0), (1, 0), (0, 1), (1, 1)]
cell_xy = lambda col, i: (X[col] + grid[i][0] * (CELL + 16), YS + grid[i][1] * (CH + 16))

for i, (x, t) in enumerate(zip(X, ["Photos", "Sender payload", "Rebuild each camera", "Fusion pass", "Result, checked by the judge"])):
    d.ellipse([x, 18, x + 84, 102], fill=STEEL); d.text((x + 42, 60), str(i + 1), font=B(52), fill=WHITE, anchor="mm")
    d.text((x + 104, 60), t, font=B(48), fill=NAVY, anchor="lm")
d.text((X[0], YM - 52), "MAIN CAMERA", font=B(36), fill=RED)
d.text((X[0], YS - 56), f"SUPPORTING ({', '.join(sups)})", font=B(36), fill=STEEL)

# 1 photos
paste(ROOT / "cam1.jpg", X[0], YM, CW[0], MH, RED)
d.text((X[0], YM + MH + 14), "the photo stays on the camera", font=R(36), fill=GREY)
for i, cam in enumerate(sups[:3]):
    paste(ROOT / f"{cam}.jpg", *cell_xy(0, i), CELL, CH)
if len(sups) <= 3:
    cx, cy = cell_xy(0, 3); wrap(cx + 12, cy + 18, "same junction, same moment", R(34), CELL - 24)

# 2 payload
tw = CELL; th = CH
paste(PAY_MAIN / "cam1_seg.webp", X[1], YM, tw, th); paste(PAY_MAIN / "cam1_edge.webp", X[1] + tw + 16, YM, tw, th)
d.rounded_rectangle([X[1], YM + th + 18, X[1] + CW[1], YM + MH], radius=14, fill=WHITE, outline=(205, 205, 205), width=3)
wrap(X[1] + 16, YM + th + 28, f"+ caption: \u201c{caption}\u201d", R(32), CW[1] - 32, fill=NAVY)
runs(X[1], YM + MH + 14, [(f"{main_kb:.0f} KB sent", NAVY), (f"  (JPEG: {jpeg_kb:.0f} KB)", GREY)], B(38))
for i, cam in enumerate(sups[:3]):
    cx, cy = cell_xy(1, i); hw = (CELL - 10) // 2; hh = hw * 9 // 16
    paste(PAY_SUP / f"{cam}_seg.webp", cx, cy + 6, hw, hh); paste(PAY_SUP / f"{cam}_edge.webp", cx + hw + 10, cy + 6, hw, hh)
    d.text((cx, cy + hh + 14), f"{cam}: {sup_kb[i]:.0f} KB", font=R(32), fill=GREY)
if len(sups) <= 3:
    cx, cy = cell_xy(1, 3); wrap(cx + 12, cy + 18, "smaller 896\u00d7512 payloads", R(34), CELL - 24)

# 3 rebuild
paste(REC_MAIN, X[2], YM, CW[2], MH, RED)
d.text((X[2], YM + MH + 12), "single-camera result:", font=B(36), fill=NAVY)
runs(X[2], YM + MH + 58, [("count WRONG", RED), (" \u00b7 positions OK", GREEN)], B(36))
for i, cam in enumerate(sups[:3]):
    paste(REC_SUP(cam), *cell_xy(2, i), CELL, CH)
if len(sups) <= 3:
    cx, cy = cell_xy(2, 3); wrap(cx + 12, cy + 18, "each from its own payload, ~8 s", R(34), CELL - 24)

# 4 fusion boxes
bx, bw = X[3], CW[3]
boxes = [((YM, 560), STEEL, (232, 241, 251), "ControlNet", "main maps hold the layout"),
         ((592, 800), ORANGE, (255, 244, 224), "img2img 0.5", "redo half the steps from the main rebuild"),
         ((832, YS + 2 * CH + 16), GREEN, (236, 247, 236), "IP-Adapter", "adds what the other cameras saw")]
for (y1, y2), col, fill, title, body in boxes:
    d.rounded_rectangle([bx, y1, bx + bw, y2], radius=22, fill=fill, outline=col, width=6)
    d.text((bx + bw / 2, y1 + 16), title, font=B(46), fill=col, anchor="ma")
    yy = wrap(bx + 24, y1 + 82, body, R(34), bw - 48, fill=NAVY)
    if title == "ControlNet":
        iw = (bw - 64) // 2; ih = iw * 9 // 16
        paste(PAY_MAIN / "cam1_seg.webp", bx + 22, yy + 10, iw, ih); paste(PAY_MAIN / "cam1_edge.webp", bx + 42 + iw, yy + 10, iw, ih)

# flow arrows
mid_m, mid_s = YM + MH / 2, YS + CH + 8
for c in (0, 1):
    arrow((X[c] + CW[c] + 8, mid_m), (X[c + 1] - 12, mid_m), RED)
    arrow((X[c] + CW[c] + 8, mid_s), (X[c + 1] - 12, mid_s), STEEL)
top = YM - 30                                                      # main maps -> ControlNet, routed above row 3
d.line([(X[1] + CW[1] / 2, YM - 6), (X[1] + CW[1] / 2, top)], fill=STEEL, width=7)
d.line([(X[1] + CW[1] / 2, top), (bx + bw / 2, top)], fill=STEEL, width=7)
arrow((bx + bw / 2, top), (bx + bw / 2, YM - 10), STEEL, 7, 24)
arrow((X[2] + CW[2] + 8, YM + MH * 0.82), (bx - 12, 696), ORANGE)
arrow((X[2] + CW[2] + 8, mid_s), (bx - 12, mid_s + 40), GREEN)
FX, FY, FW = X[4], YM, CW[4]; FH = FW * 9 // 16
for (y1, y2), col, *_ in boxes:
    arrow((bx + bw + 8, (y1 + y2) / 2), (FX - 14, FY + FH / 2 + ((y1 + y2) / 2 - 690) * 0.3), col)

# 5 result + judge
paste(FUSED, FX, FY, FW, FH, GREEN, 9)
d.text((FX, FY + FH + 14), "multi-camera fusion:", font=B(40), fill=NAVY)
runs(FX + d.textlength("multi-camera fusion: ", font=B(40)), FY + FH + 14, [("count OK \u00b7 positions OK", GREEN)], B(40))
OW = 400; OH = OW * 9 // 16; OY = FY + FH + 82
paste(ROOT / "cam1.jpg", FX, OY, OW, OH)
d.text((FX, OY + OH + 8), "original, for the judge only", font=R(30), fill=GREY)
wrap(FX + OW + 26, OY, "The judge compares each rebuild with the original: same number of cars? same positions?", R(34), FW - OW - 26, fill=NAVY)

d.line([(20, 1150), (W - 20, 1150)], fill=(200, 200, 200), width=3)
d.text((20, 1178), f"CARLA v3 case {C}: {len(cams)} cameras at one junction, same simulation tick.  Laptop RTX 3070: sender ~0.7 s per photo, "
                   "main rebuild ~75 s, each supporting rebuild ~8 s, fusion pass ~40 s.", font=R(36), fill=GREY)
out = OUT / f"demo_pipeline_carla_case{C:03d}.png"
img.save(out); img.save(out.with_suffix(".jpg"), quality=92)
print("wrote", out, img.size, f"| main payload {main_kb:.1f} KB, JPEG q90 {jpeg_kb:.1f} KB, supports", [round(x, 1) for x in sup_kb])
