from pathlib import Path
p = Path("VLM_FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("| Same with the ADE20K palette | 42.0% | 82.0% | 41.0% [32-51] |",
    "| Same with the ADE20K palette | 42.0% | 82.0% | 41.0% [32-51] |\n"
    "| Same images, payloads rebuilt with the segmenter at full size (1024x2048), 2048x1024, Cityscapes palette (14 Nov; 98 of 100 judged) | 42.9% | 83.7% | 40.8% |")
rep("- With the same judge, our reproduction of the seed method scores 41%, not about 86%. The low scores on our own datasets are therefore not caused by those datasets.",
    "- With the same judge, our reproduction of the seed method scores 41%, not about 86%.\n"
    "- **Not an iteration-1 artifact.** Iteration 1 made these payloads with the segmenter's 384x384 default, which costs about 19 mIoU points. Rebuilding them at full size gives the same result: 40.8% vs 41.8% joint on the same 98 images (13 better, 14 worse, McNemar p = 1.0).")
rep("The Cityscapes street scenes, full of parked cars, may be harder to count exactly. The questions to Damir (section 6) still decide this.",
    "Rebuilding the Cityscapes payloads with the segmenter at full size did not change that (40.8%, section 2). The Cityscapes street scenes, full of parked cars, may be harder to count exactly. The questions to Damir (section 6) still decide this.")
p.write_text(t, encoding="utf-8"); print("findings updated")
r = Path("README.md"); rt = r.read_text(encoding="utf-8")
rt = rt.rstrip() + "\n\nCityscapes rerun (14 Nov): `data/cs_cases/case<k>/cam1.png` is the k-th image of `../iter1/results/iteration1_palette_eval_100.json` (hard links, mapping in `data/cs_cases/mapping.json`); payloads with `payloads.py --seg-input 1024x2048`, reconstructions in `results/cs_paper` (`--variants k1 --size 2048x1024`), judged as setup `cs2_paper_seg1024`.\n"
r.write_text(rt, encoding="utf-8"); print("README updated")
