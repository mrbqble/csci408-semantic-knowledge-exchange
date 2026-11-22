from pathlib import Path
p = Path("make_next_report.py"); t = p.read_text(encoding="utf-8")
old = '''    text = Path(path).read_text(encoding="utf-8", errors="replace").strip()'''
new = '''    noise = ("Loading weights", "Warning: You are sending", "LOAD REPORT", "UNEXPECTED", "MISSING", "Notes:", "model.pixel_level_module",
             "python.exe -u ", "\\x1b[", "Status     |")
    keep = [l for l in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
            if l.strip() and not any(n in l for n in noise) and not l.startswith("-----") and not (l.startswith("Key ") and "|" in l)]
    text = "\\n".join(keep).strip()'''
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8"); print("patched")
