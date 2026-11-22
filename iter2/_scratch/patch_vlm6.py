from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('''    "v3_identity":''', '''    "v3_paper_k1":         ("v3", "results/v3_paper/k1/case{c}_cam1.png", "seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution"),
    "v3_paper_multi":      ("v3", "results/v3_paper/prompt_only/case{c}.png", "same settings, all cameras' captions (our multi-camera receiver)"),
    "rw_paper_k1":         ("rw", "results/rw_paper/k1/case{c}_cam1.png", "seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution"),
    "rw_paper_multi":      ("rw", "results/rw_paper/prompt_only/case{c}.png", "same settings, all cameras' captions (our multi-camera receiver)"),
    "v3_identity":''')
rep('''GROUPS["paper"] = ["cs_authors", "cs_ade"]
GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"]''', '''GROUPS["paper"] = ["cs_authors", "cs_ade"]
GROUPS["paper_res"] = ["rw_paper_k1", "rw_paper_multi", "v3_paper_k1", "v3_paper_multi"]
GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"]''')
rep('''    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),
]''', '''    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),
    ("paper_multi", "paper_k1", "multi-camera captions vs the seed paper's single-camera MMSD, both at the paper's settings"),
    ("both_fixes_cn", "paper_k1", "our best multi-camera setting vs the seed paper's single-camera MMSD at its settings"),
    ("k1_both_fixes_cn", "paper_k1", "our best single-camera setting vs the seed paper's single-camera MMSD at its settings"),
]''')
p.write_text(t, encoding="utf-8"); print("paper-settings setups added")
