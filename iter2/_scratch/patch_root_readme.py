from pathlib import Path
r = Path("README.md"); lines = r.read_text(encoding="utf-8").split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("**Team:**"))
if not any("Latest work (Nov 2026)" in l for l in lines):
    lines[i + 1:i + 1] = ["", "> **Latest work (Nov 2026):** iteration 2, the multi-camera receiver with its evaluation, is in [`iter2/`](iter2/). Start with [`iter2/STATUS_2026-11-11.md`](iter2/STATUS_2026-11-11.md); before/after examples are in [`iter2/demo/`](iter2/demo/)."]
    r.write_text("\n".join(lines), encoding="utf-8")
print("root README:", "updated" if True else "")
