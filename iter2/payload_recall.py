import json, sys, numpy as np
from pathlib import Path
from PIL import Image
from scipy.optimize import linear_sum_assignment
sys.argv = ["x"]
from analysis import box_iou
sys.path.insert(0, "../iter1")
import mmsd_sender as ms
VEH = ("car", "truck", "bus", "motorcycle")
root = Path("results/carla_v2/analysis"); pay = Path("data/carla_v2_payloads")
pal = ms.CITYSCAPES_PALETTE
veh_keys = [(int(pal[t][0]) << 16) | (int(pal[t][1]) << 8) | int(pal[t][2]) for t in (13, 14, 15, 16, 17, 18)]
bins = [(0, 24, "<24 px"), (24, 48, "24-48"), (48, 120, "48-120"), (120, 1e9, ">120")]
stat = {b[2]: dict(n=0, in_payload=0, matched_all=0, matched_in=0, in_matched=0) for b in bins}
for i in range(1, 113):
    c = f"case{i}"
    o = json.loads((root / "oracle_gen" / f"{c}.json").read_text())
    p = json.loads((root / "prompt_only" / f"{c}.json").read_text())
    seg = np.asarray(Image.open(pay / c / "cam1_seg.webp").convert("RGB"))
    key = (seg[..., 0].astype(np.int32) << 16) | (seg[..., 1].astype(np.int32) << 8) | seg[..., 2]
    isveh = np.isin(key, veh_keys)
    ob = [d["bbox_master_px"] for d in o["detections"] if d["class"] in VEH]
    pb = [d["bbox_master_px"] for d in p["detections"] if d["class"] in VEH]
    hit = np.zeros(len(ob), bool)
    if ob and pb:
        iou = box_iou(np.array(ob), np.array(pb)); r, cc = linear_sum_assignment(-iou)
        for a, b in zip(r, cc):
            if iou[a, b] >= 0.5: hit[a] = True
    for j, b in enumerate(ob):
        x1, y1, x2, y2 = (int(round(v)) for v in b)
        x1, y1 = max(x1, 0), max(y1, 0); x2, y2 = min(x2, seg.shape[1]), min(y2, seg.shape[0])
        if x2 <= x1 or y2 <= y1: continue
        cov = float(isveh[y1:y2, x1:x2].mean())
        side = ((b[2]-b[0]) * (b[3]-b[1])) ** 0.5
        for lo, hi, name in bins:
            if lo <= side < hi:
                s = stat[name]; s["n"] += 1; inp = cov >= 0.30
                s["in_payload"] += int(inp); s["matched_all"] += int(hit[j])
                s["matched_in"] += int(hit[j] and inp); s["in_matched"] += int(inp)
tot = {k: sum(s[k] for s in stat.values()) for k in ("n", "in_payload", "matched_all", "matched_in", "in_matched")}
print("oracle vehicles (112 cases, cam1, at 1024x576), by box side length")
print(f"{'size':8}{'n':>5}{'in seg payload':>16}{'receiver recall':>17}{'recall | in payload':>21}")
for name, s in list(stat.items()) + [("all", tot)]:
    print(f"{name:8}{s['n']:5}{s['in_payload']/s['n']:16.2f}{s['matched_all']/s['n']:17.2f}{(s['matched_in']/s['in_matched'] if s['in_matched'] else float('nan')):21.2f}")
