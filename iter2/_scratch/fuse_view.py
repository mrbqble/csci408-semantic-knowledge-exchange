from PIL import Image, ImageDraw
import paths
c = 1
tiles = [("original cam1", Image.open(paths.REAL_WORLD_CORE / f"case{c}" / "cam1.png")),
         ("main reconstruction (paper settings)", Image.open(f"results/rw_paper/k1/case{c}_cam1.png")),
         ("supporting reconstruction cam2", Image.open(f"results/rw_support/k1/case{c}_cam2.png")),
         ("supporting reconstruction cam3", Image.open(f"results/rw_support/k1/case{c}_cam3.png")),
         ("fusion (IP-Adapter on cam2+cam3)", Image.open(f"results/rw_fuse/fuse/case{c}.png")),
         ("control: same img2img, no IP-Adapter", Image.open(f"results/rw_fuse/fuse_noip/case{c}.png"))]
W, H = 640, 360
sheet = Image.new("RGB", (2 * W, 3 * H), "white")
for i, (label, im) in enumerate(tiles):
    x, y = (i % 2) * W, (i // 2) * H
    sheet.paste(im.convert("RGB").resize((W, H)), (x, y))
    d = ImageDraw.Draw(sheet); d.rectangle([x, y, x + 300, y + 16], fill="black"); d.text((x + 4, y + 3), label, fill="white")
sheet.save("_scratch/fuse_case1.jpg", quality=88)
