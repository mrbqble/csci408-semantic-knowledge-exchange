from pathlib import Path
p = Path("refine_report.py"); t = p.read_text(encoding="utf-8")
old = 'concl.read_text(encoding="utf-8").strip()'
assert t.count(old) == 1
p.write_text(t.replace(old, 'concl.read_text(encoding="utf-8-sig").strip()'), encoding="utf-8")
