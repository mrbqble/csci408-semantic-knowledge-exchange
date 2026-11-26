from pathlib import Path
p = Path("blob_split.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep("def edge_markers(roi, edge_roi, dil):", "def edge_markers(roi, edge_roi, dil, minpiece=6):")
rep("        if st[i, cv2.CC_STAT_AREA] >= 6:\n            k += 1; markers[lab == i] = k", "        if st[i, cv2.CC_STAT_AREA] >= minpiece:\n            k += 1; markers[lab == i] = k")
rep('mk = edge_markers(roi, edge_roi, p["dil"])', 'mk = edge_markers(roi, edge_roi, p["dil"], p.get("minpiece", 6))')
i0 = t.index("CONFIGS = ["); i1 = t.index("]\n", t.index('("both", {"alpha": 0.7, "dil": 0})')) + 2
new_cfg = '''CONFIGS = [("none", {}), ("dist", {"alpha": 0.5}), ("dist", {"alpha": 0.6}),
           ("edge", {"dil": 1}), ("edge", {"dil": 1, "minpiece": 30}), ("edge", {"dil": 1, "minpiece": 60}), ("edge", {"dil": 1, "minpiece": 120}),
           ("edge", {"dil": 2, "minpiece": 30}), ("edge", {"dil": 2, "minpiece": 60}), ("edge", {"dil": 2, "minpiece": 120}),
           ("both", {"alpha": 0.6, "dil": 1, "minpiece": 60}), ("both", {"alpha": 0.6, "dil": 2, "minpiece": 60}),
           ("both", {"alpha": 0.6, "dil": 1, "minpiece": 120}), ("both", {"alpha": 0.6, "dil": 2, "minpiece": 120})]
'''
t = t[:i0] + new_cfg + t[i1:]
p.write_text(t, encoding="utf-8"); print("patched")
