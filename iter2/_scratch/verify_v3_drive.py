import hashlib, json, os, random
from pathlib import Path
sim = Path(r"C:\Users\mrbqble\My Drive (bibol.assetbek@nu.edu.kz)\uni\04\01\CSCI 408\Senior Project Work\Datasets\Simulated")
drv = sim / "carla_dataset_v3_ids"; loc = Path(r"C:\carla_multicam_kit\output\carla_dataset_v3_ids")
md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()
dm = json.loads((drv / "manifest.json").read_text(encoding="utf-8")); lm = json.loads((loc / "manifest.json").read_text(encoding="utf-8"))
jpg_d = sorted(drv.rglob("*.jpg")); jpg_l = sorted(loc.rglob("*.jpg"))
print(f"JPEGs: drive {len(jpg_d)}, local {len(jpg_l)}; bytes drive {sum(p.stat().st_size for p in jpg_d):,}, local {sum(p.stat().st_size for p in jpg_l):,}")
# every manifest path resolves, camera count matches the folder, local case content equals drive content
problems = []
for dc, lc in zip(dm["cases"], lm["cases"]):
    folder = drv / dc["folder"]
    if dc["folder"].split("/")[1] != lc["folder"]: problems.append(("case name", dc["folder"], lc["folder"]))
    if not folder.is_dir(): problems.append(("missing folder", dc["folder"])); continue
    if dc["folder"].split("/")[0] != f"{dc['n_cameras']}_cameras": problems.append(("wrong group", dc["folder"], dc["n_cameras"]))
    for cam in dc["cameras"]:
        f = folder / cam["file"]
        if not f.exists(): problems.append(("missing photo", str(f))); continue
        if f.stat().st_size != (loc / lc["folder"] / cam["file"]).stat().st_size: problems.append(("size", str(f)))
    d2 = dict(dc, folder=lc["folder"]); 
    if d2 != lc: problems.append(("manifest case differs beyond folder", dc["case"]))
top_d = {k: v for k, v in dm.items() if k not in ("cases", "layout")}; top_l = {k: v for k, v in lm.items() if k != "cases"}
print("manifest: cases", len(dm["cases"]), "| top-level fields identical apart from 'layout':", top_d == top_l, "| layout note present:", "layout" in dm)
n_inst_d = sum(len(c["instances"]) for cs in dm["cases"] for c in cs["cameras"]); n_inst_l = sum(len(c["instances"]) for cs in lm["cases"] for c in cs["cameras"])
print(f"instances: drive {n_inst_d:,}, local {n_inst_l:,}")
print("problems:", problems[:5] if problems else "none")
# md5 spot check
rel = {p.name + "|" + p.parent.name: p for p in jpg_l}
pick = random.Random(0).sample(jpg_d, 60); bad = 0
for p in pick:
    if md5(p) != md5(rel[p.name + "|" + p.parent.name]): bad += 1
print(f"md5 spot check on {len(pick)} photos: {'all identical' if bad == 0 else str(bad) + ' MISMATCHES'}")
# local untouched, other Drive datasets untouched
lf = [p for p in loc.rglob("*") if p.is_file()]
print(f"local v3: {len(lf)} files, {sum(p.stat().st_size for p in lf):,} bytes (before: 506 files, 294,418,484); flat case dirs: {sum(1 for p in loc.iterdir() if p.is_dir() and p.name.startswith('case'))}")
other = [p for d in ("carla_dataset_v1", "carla_dataset_v2_low2m_3to6cams_hd") for p in (sim / d).rglob("*") if p.is_file()]
print(f"drive v1 + v2: {len(other)} files (before: 768 files across the Simulated folder)")
print("README first line:", (drv / "README.txt").read_text(encoding="utf-8").splitlines()[0][:90])
print("Drive for desktop processes:", sum(1 for _ in os.popen('tasklist /FI "IMAGENAME eq GoogleDriveFS.exe" /NH').read().splitlines() if "GoogleDriveFS" in _))
