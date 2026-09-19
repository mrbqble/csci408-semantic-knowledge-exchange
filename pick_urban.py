#!/usr/bin/env python3
"""Select genuine urban/street images from COCO val2017 using the instance
annotations, and extract them into images_urban/.

Rationale: the Cityscapes-trained SegFormer predicts 19 urban classes. Running
it on indoor/animal photos yields a near-uniform label map that compresses to
almost nothing, which fakes an impressive compression ratio. We need street
scenes for the numbers to mean anything.
"""
import json, urllib.request, zipfile, shutil
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
ANN_ZIP = ROOT / "annotations_trainval2017.zip"
ANN_JSON = ROOT / "annotations" / "instances_val2017.json"
VAL_ZIP = ROOT / "val2017.zip"
OUT = ROOT / "images_urban"
N_WANT = 25

# COCO category ids
VEHICLE = {3: "car", 6: "bus", 8: "truck", 4: "motorcycle", 2: "bicycle"}
TRAFFIC = {10: "traffic light", 13: "stop sign"}
PERSON = {1: "person"}

if not ANN_JSON.exists():
    if not ANN_ZIP.exists():
        print("Downloading COCO annotations (~241 MB)...")
        urllib.request.urlretrieve(
            "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
            ANN_ZIP)
    print("Extracting instances_val2017.json...")
    with zipfile.ZipFile(ANN_ZIP) as z:
        z.extract("annotations/instances_val2017.json", ROOT)

print("Loading annotations...")
ann = json.loads(ANN_JSON.read_text())
imgs = {i["id"]: i for i in ann["images"]}

counts = defaultdict(lambda: defaultdict(int))
for a in ann["annotations"]:
    if a.get("iscrowd"):
        continue
    counts[a["image_id"]][a["category_id"]] += 1

scored = []
for iid, c in counts.items():
    veh = sum(c.get(k, 0) for k in VEHICLE)
    traf = sum(c.get(k, 0) for k in TRAFFIC)
    ppl = sum(c.get(k, 0) for k in PERSON)
    # a real street scene: several vehicles, or vehicles plus traffic furniture
    if veh < 3 and not (veh >= 1 and traf >= 1):
        continue
    im = imgs[iid]
    # prefer bigger images -- resolution drives payload size
    score = veh * 2 + traf * 3 + min(ppl, 5) + (im["width"] * im["height"]) / 4e5
    scored.append((score, iid))

scored.sort(reverse=True)
picked = [imgs[i] for _, i in scored[:N_WANT]]
print(f"Matched {len(scored)} street scenes; taking top {len(picked)}")

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
names = {p["file_name"] for p in picked}
with zipfile.ZipFile(VAL_ZIP) as z:
    for e in z.infolist():
        base = e.filename.split("/")[-1]
        if base in names:
            with z.open(e) as src, open(OUT / base, "wb") as dst:
                shutil.copyfileobj(src, dst)

got = sorted(OUT.glob("*.jpg"))
mp = sum(p["width"] * p["height"] for p in picked) / len(picked) / 1e6
print(f"Extracted {len(got)} images into {OUT.name}/  (mean {mp:.2f} MP)")
for p in picked[:5]:
    c = counts[p["id"]]
    veh = sum(c.get(k, 0) for k in VEHICLE)
    traf = sum(c.get(k, 0) for k in TRAFFIC)
    print(f"  {p['file_name']}  {p['width']}x{p['height']}  vehicles={veh} traffic={traf}")
