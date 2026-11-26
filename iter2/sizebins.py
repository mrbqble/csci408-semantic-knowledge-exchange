import json, numpy as np
from pathlib import Path
from scipy.optimize import linear_sum_assignment
import sys; sys.argv = ["x"]
from analysis import box_iou
a = Path("results/pilot_cs/analysis")
VEH = ("car", "truck", "bus", "motorcycle")
bins = [(0, 24*24, "tiny <24px^2"), (24*24, 48*48, "small 24-48"), (48*48, 120*120, "medium 48-120"), (120*120, 1e9, "large >120")]
for grp, names in (("vehicles", VEH), ("people", ("person",))):
    tot = {b[2]: [0, 0] for b in bins}
    for f in sorted((a / "k1").glob("case*.json")):
        k = json.loads(f.read_text()); o = json.loads((a / "oracle_gen" / f.name).read_text())
        ob = [d["bbox_master_px"] for d in o["detections"] if d["class"] in names]
        kb = [d["bbox_master_px"] for d in k["detections"] if d["class"] in names]
        hit = np.zeros(len(ob), bool)
        if ob and kb:
            iou = box_iou(np.array(ob), np.array(kb)); r, c = linear_sum_assignment(-iou)
            for i, j in zip(r, c):
                if iou[i, j] >= 0.5: hit[i] = True
        for i, b in enumerate(ob):
            area = (b[2]-b[0]) * (b[3]-b[1])
            for lo, hi, name in bins:
                if lo <= area < hi:
                    tot[name][0] += 1; tot[name][1] += int(hit[i])
    print(grp, {n: f"{h}/{t} = {h/t:.2f}" if t else "n/a" for n, (t, h) in tot.items()})
