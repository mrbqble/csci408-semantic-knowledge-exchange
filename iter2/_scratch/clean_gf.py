from pathlib import Path
p = Path("geofuse.py"); t = p.read_text(encoding="utf-8")
lines = [l for l in t.split("\n") if "if False else None" not in l]
p.write_text("\n".join(lines), encoding="utf-8")
