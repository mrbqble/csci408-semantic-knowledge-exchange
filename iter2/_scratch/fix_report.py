from pathlib import Path
p = Path("make_report.py"); t = p.read_text(encoding="utf-8")
old = 'out.append(f"| {v} | " + " | ".join(f2(d.get(k[0])) for k in keys) + " |")'
assert t.count(old) == 1
new = 'out.append(f"| {v} | " + " | ".join(str(int(d[k[0]])) if k[0] == "n_cases" else f2(d.get(k[0])) for k in keys) + " |")'
p.write_text(t.replace(old, new), encoding="utf-8"); print("patched make_report")
