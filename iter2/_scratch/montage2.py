from PIL import Image, ImageDraw
case = "case5"
tiles = [("original", Image.open(rf"C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd\{case}\cam1.jpg").convert("RGB")),
         ("base canny1.0", Image.open(f"results/carla_v2/prompt_only/{case}.png")),
         ("canny0.5", Image.open(f"results/tune_c05/prompt_only/{case}.png")),
         ("canny0.0 (seg only)", Image.open(f"results/tune_c00/prompt_only/{case}.png"))]
W, H = 768, 432
sheet = Image.new("RGB", (W * 2, H * 2), "white")
for i, (label, im) in enumerate(tiles):
    x, y = (i % 2) * W, (i // 2) * H
    sheet.paste(im.convert("RGB").resize((W, H)), (x, y))
    d = ImageDraw.Draw(sheet); d.rectangle([x, y, x + 200, y + 16], fill="black"); d.text((x + 4, y + 3), f"{case} {label}", fill="white")
sheet.save("results/tune_montage_case5.jpg", quality=88)
print("ok")
