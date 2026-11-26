from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('''RUNS = {  # label: (dataset, reconstruction path pattern, description)''', '''ITER1 = Path(__file__).resolve().parent.parent / "iter1"


def _cs_stems():
    """The 100 Cityscapes validation images of iteration 1's evaluation (every 5th of 500)."""
    f = ITER1 / "results" / "iteration1_palette_eval_100.json"
    return [r["stem"] for r in json.loads(f.read_text())["rows"]] if f.exists() else []


DATASETS["cs"] = {"orig": lambda c: ITER1 / "data" / "cityscapes_val" / f"{c}.png", "cases": _cs_stems()}

RUNS = {  # label: (dataset, reconstruction path pattern, description)''')
rep('''    "v3_identity":''', '''    "cs_authors":          ("cs", str(ITER1 / "results" / "palette100" / "A_cs_full" / "{c}.png"), "Cityscapes (the seed paper's kind of data), authors' receiver settings: 2048x1024, Cityscapes palette, single camera (iteration 1)"),
    "cs_ade":              ("cs", str(ITER1 / "results" / "palette100" / "B_ade_full" / "{c}.png"), "Cityscapes, authors' settings with the ADE20K palette (iteration 1)"),
    "v3_identity":''')
rep('''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"]''', '''GROUPS["paper"] = ["cs_authors", "cs_ade"]
GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"]''')
rep('''    ("both_fixes_cn", "k1_both_fixes_cn", "multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5)"),
]''', '''    ("both_fixes_cn", "k1_both_fixes_cn", "multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5)"),
    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),
]''')
rep('''def pairs_for(run):
    ds, pattern, _ = RUNS[run]
    d = DATASETS[ds]
''', '''def pairs_for(run):
    ds, pattern, _ = RUNS[run]
    d = DATASETS[ds]
    if "orig" in d:
        return [(c, d["orig"](c), Path(pattern.format(c=c))) for c in d["cases"]]
''')
rep('''    for ds in ("v3", "rw"):
        for b, a, question in COMPARISONS:''', '''    for ds in ("v3", "rw", "cs"):
        for b, a, question in COMPARISONS:''')
p.write_text(t, encoding="utf-8"); print("Cityscapes setups added")
