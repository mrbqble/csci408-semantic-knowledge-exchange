from PIL import Image, ImageDraw
stem = "frankfurt_000000_000294_leftImg8bit"
orig = Image.open(f"../iter1/data/cityscapes_val/{stem}.png").convert("RGB").resize((1024, 512))
old = Image.open(f"../iter1/data/components_m2f/{stem}_seg.webp").convert("RGB").resize((1024, 512), Image.NEAREST)
new = Image.open("data/cs_payloads/case1/cam1_seg.webp").convert("RGB").resize((1024, 512), Image.NEAREST)
sheet = Image.new("RGB", (1024, 1536), "white")
for i, (label, im) in enumerate((("original", orig), ("iteration 1 payload (segmenter at 384x384 default)", old), ("new payload (segmenter at 1024x2048)", new))):
    sheet.paste(im, (0, 512 * i)); d = ImageDraw.Draw(sheet); d.rectangle([0, 512 * i, 420, 512 * i + 18], fill="black"); d.text((4, 512 * i + 4), label, fill="white")
sheet.resize((768, 1152)).save("_scratch/cs_seg_compare.jpg", quality=88)
print("ok")
