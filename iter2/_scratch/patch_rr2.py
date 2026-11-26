from pathlib import Path
p = Path("refine_report.py"); t = p.read_text(encoding="utf-8")
old = '    lines.append("## Conclusion\\n\\n<!--CONCLUSION-->\\n")'
assert t.count(old) == 1, t.count(old)
new = '''    concl = Path("refine_conclusion.md")
    lines.append("## Conclusion\\n\\n" + (concl.read_text(encoding="utf-8").strip() if concl.exists() else "<!--CONCLUSION-->") + "\\n")'''
p.write_text(t.replace(old, new), encoding="utf-8"); print("patched")
