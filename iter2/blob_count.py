import json, sys, csv, numpy as np, cv2
from pathlib import Path
from PIL import Image
sys.path.insert(0, "../iter1")
import mmsd_sender as ms
pal = ms.CITYSCAPES_PALETTE
def key_of(t): return (int(pal[t][0]) << 16) | (int(pal[t][1]) << 8) | int(pal[t][2])
groups = {"cars_4wheel": [13, 14, 15], "pedestrians": [11, 12]}      # car, truck, bus | person, rider
gt = {}
for c in json.load(open(__import__("paths").CARLA_V2 / "manifest.json"))["cases"]:
    for cam in c["cameras"]:
        if cam["file"] == "cam1.jpg":
            gt[f"case{c['case']}"] = {"cars_4wheel": cam["counts"]["cars"], "pedestrians": cam["counts"]["pedestrians"]}
rows = list(csv.DictReader(open("results/carla_v2/analysis/counts.csv")))
ref = {(r["case"], r["variant"]): r for r in rows}
pay = Path("data/carla_v2_payloads")
print(f"{'min blob area (px @1024x576)':30}{'cars MAE':>10}{'cars bias':>11}{'within1':>9}{'ped MAE':>9}{'ped bias':>10}")
for amin in (10, 30, 60):
    res = {k: [] for k in groups}
    for i in range(1, 113):
        c = f"case{i}"
        seg = np.asarray(Image.open(pay / c / "cam1_seg.webp").convert("RGB"))
        key = (seg[..., 0].astype(np.int32) << 16) | (seg[..., 1].astype(np.int32) << 8) | seg[..., 2]
        for g, ids in groups.items():
            mask = np.isin(key, [key_of(t) for t in ids]).astype(np.uint8)
            n, _, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
            res[g].append(int((st[1:, cv2.CC_STAT_AREA] >= amin).sum()) - gt[c][g])
    ce, pe = np.array(res["cars_4wheel"]), np.array(res["pedestrians"])
    print(f"{amin:<30}{np.abs(ce).mean():10.2f}{ce.mean():11.2f}{(np.abs(ce) <= 1).mean():9.2f}{np.abs(pe).mean():9.2f}{pe.mean():10.2f}")
for v in ("k1", "prompt_only", "oracle_gen"):
    ce = np.array([int(ref[(f"case{i}", v)]["cars_4wheel"]) - gt[f"case{i}"]["cars_4wheel"] for i in range(1, 113)])
    pe = np.array([int(ref[(f"case{i}", v)]["pedestrians"]) - gt[f"case{i}"]["pedestrians"] for i in range(1, 113)])
    print(f"{'ref: ' + v:30}{np.abs(ce).mean():10.2f}{ce.mean():11.2f}{(np.abs(ce) <= 1).mean():9.2f}{np.abs(pe).mean():9.2f}{pe.mean():10.2f}")
