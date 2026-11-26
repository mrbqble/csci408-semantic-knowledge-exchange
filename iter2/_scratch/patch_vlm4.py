from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('''    "v3_both_fixes_cn":    ("v3",''', '''    "v3_identity":         ("v3", str(paths.CARLA_V3 / "case{c}" / "cam1.jpg"), "calibration: the original photo judged against itself (the judge's ceiling)"),
    "rw_identity":         ("rw", str(paths.REAL_WORLD_CORE / "case{c}" / "cam1.png"), "calibration: the original photo judged against itself (the judge's ceiling)"),
    "v3_both_fixes_cn":    ("v3",''')
rep('''    "extra": ["v3_both_fixes_cn",''', '''    "extra": ["v3_identity", "rw_identity", "v3_both_fixes_cn",''')
p.write_text(t, encoding="utf-8"); print("identity setups added")
