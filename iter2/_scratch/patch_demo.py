from pathlib import Path
p = Path("make_demo.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('''    if s["gt"]:
        gt = gt_boxes(manifest_cases[case])
        return float(hits(gt, det_boxes(row), 0.5).mean()) if gt else None
    return row.get("vehicle_recall")''',
'''    ref = gt_boxes(manifest_cases[case]) if s["gt"] else det_boxes(json.loads((s["default"] / "analysis" / "oracle_gen" / f"case{case}.json").read_text()))
    return float(hits(ref, det_boxes(row), 0.5).mean()) if ref else None''')
rep('''                ra, rb = ref_row.get("vehicle_recall"), new_row.get("vehicle_recall")''',
'''                ra, rb = (float(hits(ref, da, 0.5).mean()), float(hits(ref, db, 0.5).mean())) if ref else (None, None)''')
p.write_text(t, encoding="utf-8"); print("patched")
