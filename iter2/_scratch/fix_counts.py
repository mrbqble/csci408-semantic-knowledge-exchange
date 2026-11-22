import csv, json
from pathlib import Path
# 1) patch analysis.py (two columns were sliced off)
p = Path("analysis.py"); t = p.read_text(encoding="utf-8")
old = "**{k: c[k] for k in cols[3:11]}"
assert t.count(old) == 1
p.write_text(t.replace(old, "**{k: c[k] for k in cols[3:13]}"), encoding="utf-8")
# 2) regenerate counts.csv for the finished roots from the per-case JSON (no detector rerun)
cols = ["case", "variant", "reference", "car", "truck", "bus", "motorcycle", "bicycle", "person", "cars_4wheel", "vehicles",
        "two_wheelers", "pedestrians", "gt_cars", "gt_pedestrians", "gt_two_wheelers"]
for root in ("results/carla_v2", "results/pilot_cs"):
    ana = Path(root) / "analysis"
    rows = []
    for vdir in sorted(d for d in ana.iterdir() if d.is_dir()):
        for f in sorted(vdir.glob("case*.json"), key=lambda f: int(f.stem[4:])):
            r = json.loads(f.read_text()); c, g = r["counts"], r["gt"] or {}
            rows.append({"case": r["case"], "variant": r["variant"], "reference": r["reference"], **{k: c[k] for k in cols[3:13]},
                         "gt_cars": g.get("cars_4wheel"), "gt_pedestrians": g.get("pedestrians"), "gt_two_wheelers": g.get("two_wheelers")})
    with open(ana / "counts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(root, len(rows), "rows; sample:", {k: rows[-1][k] for k in ("case", "variant", "person", "pedestrians", "two_wheelers")})
# 3) what the manifest gives per camera
m = json.load(open(r"C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd\manifest.json"))
cam = m["cases"][0]["cameras"][0]
print("camera keys:", sorted(cam.keys())); print("case keys:", sorted(m["cases"][0].keys()))
print("all cameras have pose+fov:", all(all(k in c for k in ("location", "pitch_deg", "yaw_deg", "roll_deg", "fov", "height_m")) for cs in m["cases"] for c in cs["cameras"]),
      "| roll values:", sorted({c["roll_deg"] for cs in m["cases"] for c in cs["cameras"]}))
