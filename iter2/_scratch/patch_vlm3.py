from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('''    "rw_palette_only":     ("rw", "results/rw_ade/prompt_only/case{c}.png", "1024x576, ADE20K palette"),
}''', '''    "rw_palette_only":     ("rw", "results/rw_ade/prompt_only/case{c}.png", "1024x576, ADE20K palette"),
    "v3_both_fixes_cn":    ("v3", "results/v3_native_ade_cn/prompt_only/case{c}.png", "both fixes + ControlNet canny 0.7 / seg 1.5"),
    "v3_k1_both_fixes_cn": ("v3", "results/v3_native_ade_cn/k1/case{c}_cam1.png", "reference camera only, both fixes + canny 0.7 / seg 1.5"),
    "rw_both_fixes_cn":    ("rw", "results/rw_native_ade_cn/prompt_only/case{c}.png", "both fixes + ControlNet canny 0.7 / seg 1.5"),
    "rw_k1_both_fixes_cn": ("rw", "results/rw_native_ade_cn/k1/case{c}_cam1.png", "reference camera only, both fixes + canny 0.7 / seg 1.5"),
}''')
rep('''    "extra": ["v3_cn07_15", "v3_resolution_only", "v3_palette_only", "rw_cn07_15", "rw_resolution_only", "rw_palette_only"],''',
    '''    "extra": ["v3_both_fixes_cn", "v3_k1_both_fixes_cn", "rw_both_fixes_cn", "rw_k1_both_fixes_cn",
              "v3_cn07_15", "v3_resolution_only", "v3_palette_only", "rw_cn07_15", "rw_resolution_only", "rw_palette_only"],''')
rep('''    ("cn07_15", "default", "ControlNet canny 0.7 / seg 1.5"),
]''', '''    ("cn07_15", "default", "ControlNet canny 0.7 / seg 1.5"),
    ("both_fixes_cn", "both_fixes", "canny 0.7 / seg 1.5 on top of both fixes"),
    ("both_fixes_cn", "k1_both_fixes_cn", "multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5)"),
]''')
p.write_text(t, encoding="utf-8"); print("judge setups extended")
