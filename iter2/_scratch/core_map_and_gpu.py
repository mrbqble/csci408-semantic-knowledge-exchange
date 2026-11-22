import csv, hashlib, json
from pathlib import Path
V1 = Path(r"C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1")
def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
idx = {md5(p): p.relative_to(V1 / "cases_1to3phones").as_posix() for p in (V1 / "cases_1to3phones").rglob("*.png")}
rows, missing = [], 0
for case_dir in sorted((V1 / "core").glob("case*"), key=lambda p: int(p.name[4:])):
    for img in sorted(case_dir.glob("cam*.png")):
        k = md5(img)
        rows.append({"core_case": case_dir.name, "camera": img.stem, "drive_path_in_V1_cases_1to3phones": idx.get(k, ""), "md5": k})
        missing += k not in idx
out = Path("dataset_maps"); out.mkdir(exist_ok=True)
with open(out / "real_world_v1_core_to_cases_1to3phones.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"core images: {len(rows)}, without an identical file in cases_1to3phones: {missing}")
secs, n = 0.0, 0
for p in Path("results").rglob("*.json"):
    try:
        v = json.loads(p.read_text()).get("seconds")
    except Exception:
        continue
    if isinstance(v, (int, float)) and v > 0:
        secs += v; n += 1
print(f"recorded generation passes: {n}, GPU time: {secs/3600:.1f} h")
judged = sum(1 for p in Path("results/vlm").glob("*.jsonl") for _ in open(p, encoding="utf-8"))
print("judge rows (pairs, incl. retries):", judged)
