from pathlib import Path
def patch(path, pairs):
    p = Path(path); t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert t.count(old) == 1, (path, t.count(old), old[:70]); t = t.replace(old, new)
    p.write_text(t, encoding="utf-8"); print("patched", path)
patch("payloads.py", [
 ('    ap.add_argument("--device", default="auto")\n',
  '    ap.add_argument("--device", default="auto")\n    ap.add_argument("--seg-input", default="", help="HxW segmenter input, e.g. 1024x2048 (default: the iteration-1 operating point 512x1024)")\n'),
 ('    seg, cap = ms.Segmenter(device, input_size=SEG_INPUT), ms.Captioner(device)\n',
  '    seg_input = tuple(int(v) for v in args.seg_input.lower().split("x")) if args.seg_input else SEG_INPUT\n    seg, cap = ms.Segmenter(device, input_size=seg_input), ms.Captioner(device)\n'),
])
patch("vlm_judge.py", [
 ('''DATASETS["cs"] = {"orig": lambda c: ITER1 / "data" / "cityscapes_val" / f"{c}.png", "cases": _cs_stems()}''',
  '''DATASETS["cs"] = {"orig": lambda c: ITER1 / "data" / "cityscapes_val" / f"{c}.png", "cases": _cs_stems()}
DATASETS["cs2"] = {"root": Path("data/cs_cases"), "cases": list(range(1, 101)), "photo": "cam1.png"}   # the same 100 images, case k = k-th stem'''),
 ('''    "v3_paper_k1":''', '''    "cs2_paper_seg1024":   ("cs2", "results/cs_paper/k1/case{c}_cam1.png", "Cityscapes, seed paper's single-camera MMSD rebuilt with the segmenter at full input size (1024x2048), 2048x1024, Cityscapes palette"),
    "v3_paper_k1":'''),
 ('''GROUPS["paper_res"] = ["rw_paper_k1", "rw_paper_multi", "v3_paper_k1", "v3_paper_multi"]''',
  '''GROUPS["paper_res"] = ["rw_paper_k1", "rw_paper_multi", "v3_paper_k1", "v3_paper_multi"]
GROUPS["cs_rerun"] = ["cs2_paper_seg1024"]'''),
 ('''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"]''',
  '''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"]'''),
])
import json
stems = [r["stem"] for r in json.loads(Path("../iter1/results/iteration1_palette_eval_100.json").read_text())["rows"]]
root = Path("data/cs_cases"); root.mkdir(parents=True, exist_ok=True)
import os
for k, s in enumerate(stems, start=1):
    d = root / f"case{k}"; d.mkdir(exist_ok=True)
    dst = d / "cam1.png"
    if not dst.exists():
        os.link(Path("../iter1/data/cityscapes_val") / f"{s}.png", dst)      # hard link: no copy
(root / "mapping.json").write_text(json.dumps({f"case{k}": s for k, s in enumerate(stems, start=1)}, indent=1))
print("cs_cases:", len(stems), "cases")
