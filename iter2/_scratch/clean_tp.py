from pathlib import Path
p = Path("training_prep.py"); t = p.read_text(encoding="utf-8")
old = '            summary["splits"].setdefault(source, {}).setdefault(sp, 0)\n'
assert t.count(old) == 1
p.write_text(t.replace(old, ""), encoding="utf-8"); print("cleaned")
