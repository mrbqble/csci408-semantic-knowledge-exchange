from pathlib import Path
def patch(path, old, new):
    p = Path(path); t = p.read_text(encoding="utf-8")
    assert t.count(old) == 1, (path, t.count(old), old[:70])
    p.write_text(t.replace(old, new), encoding="utf-8")
patch("iter2/geofuse.py", 'MANIFEST = Path(r"C:\\carla_multicam_kit\\output\\carla_dataset_v2_low2m_3to6cams_hd\\manifest.json")',
      'from paths import CARLA_V2  # noqa: E402\n\nMANIFEST = CARLA_V2 / "manifest.json"')
patch("iter2/geom_check.py", 'm = json.load(open(r"C:\\carla_multicam_kit\\output\\carla_dataset_v2_low2m_3to6cams_hd\\manifest.json"))',
      'from paths import CARLA_V2\nm = json.load(open(CARLA_V2 / "manifest.json"))')
patch("iter2/blob_count.py", 'json.load(open(r"C:\\carla_multicam_kit\\output\\carla_dataset_v2_low2m_3to6cams_hd\\manifest.json"))',
      'json.load(open(__import__("paths").CARLA_V2 / "manifest.json"))')
patch("iter2/sweep_gf.py", 'subprocess.run([r"..\\.venv\\Scripts\\python.exe", "geofuse.py"', 'subprocess.run([sys.executable, "geofuse.py"')
t = Path("iter2/sweep_gf.py").read_text(encoding="utf-8")
if "import sys" not in t:
    Path("iter2/sweep_gf.py").write_text(t.replace("import json, subprocess, sys", "import json, subprocess, sys") if "import json, subprocess, sys" in t else "import sys\n" + t, encoding="utf-8")
print("paths patched")
