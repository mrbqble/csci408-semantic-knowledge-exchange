import re
from pathlib import Path
src = Path(r"C:\CARLA\jobs\regroup_cases_by_cameras.py").read_text(encoding="utf-8")
m = re.search(r"DATASETS = \{.*?\n\}\n", src, flags=re.S)
assert m, "DATASETS block not found"
new_block = 'DATASETS = {\n    "CARLA v3": (os.path.join(BASE, "Simulated", "carla_dataset_v3_ids"), (".jpg",), "manifest"),\n}\n'
out = src.replace(m.group(0), new_block)
assert out.count("22 Oct 2026") == 1
out = out.replace("22 Oct 2026", "25 Oct 2026")
Path("regroup_v3.py").write_text(out, encoding="utf-8")
print("regroup_v3.py written")
