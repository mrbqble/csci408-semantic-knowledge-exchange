from pathlib import Path
p = Path("make_demo.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep("from PIL import Image, ImageDraw\n", "import textwrap\n\nfrom PIL import Image, ImageDraw, ImageFont\n")
rep('COL = {"gt": (0, 255, 0), "det": (255, 220, 0)}\n',
    'COL = {"gt": (0, 255, 0), "det": (255, 220, 0)}\nTW, TH = 512, 288                      # panel tile size\ntry:\n    FONT = ImageFont.truetype("arial.ttf", 13)\nexcept OSError:\n    FONT = ImageFont.load_default()\n')
rep('''def draw(img, boxes, colour, label):
    im = img.copy()
    d = ImageDraw.Draw(im)
    for b in boxes:
        d.rectangle(b, outline=colour, width=2)
    d.rectangle([0, 0, 360, 18], fill="black")
    d.text((4, 4), label, fill="white")
    return im''', '''def draw(img, boxes, colour, label):
    """Tile at panel size: boxes scaled from the 1024x576 frame, label drawn at the final size so it stays readable."""
    im = img.resize((TW, TH), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    s = TW / W
    for b in boxes:
        d.rectangle([v * s for v in b], outline=colour, width=2)
    d.rectangle([0, 0, d.textlength(label, font=FONT) + 10, 18], fill="black")
    d.text((5, 2), label, fill="white", font=FONT)
    return im''')
rep('''            info = Image.new("RGB", (W, H), "white")
            di = ImageDraw.Draw(info)''', '''            info = Image.new("RGB", (TW, TH), "white")
            di = ImageDraw.Draw(info)''')
rep('''            for i, t in enumerate(l for l in lines if l):
                di.text((20, 30 + 34 * i), t[:110], fill="black")
            tiles.append(info)
            tw, th = 512, 288
            panel = Image.new("RGB", (3 * tw, 2 * th), "white")
            for i, t in enumerate(tiles):
                panel.paste(t.resize((tw, th), Image.LANCZOS), ((i % 3) * tw, (i // 3) * th))''', '''            y = 12
            for t in (l for l in lines if l):
                for part in textwrap.wrap(t, 72):
                    di.text((12, y), part, fill="black", font=FONT)
                    y += 18
                y += 4
            tiles.append(info)
            panel = Image.new("RGB", (3 * TW, 2 * TH), "white")
            for i, t in enumerate(tiles):
                panel.paste(t, ((i % 3) * TW, (i // 3) * TH))''')
p.write_text(t, encoding="utf-8"); print("patched")
