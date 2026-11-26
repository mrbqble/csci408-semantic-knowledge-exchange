from pathlib import Path
p = Path("refine_report.py"); t = p.read_text(encoding="utf-8")
old = 'cells = [rate(*o["bins"][b[2]][::-1][::-1][1:2], o["bins"][b[2]][0]) if False else rate(o["bins"][b[2]][1], o["bins"][b[2]][0]) for b in BINS]'
assert t.count(old) == 1
p.write_text(t.replace(old, 'cells = [rate(o["bins"][b[2]][1], o["bins"][b[2]][0]) for b in BINS]'), encoding="utf-8"); print("cleaned")
