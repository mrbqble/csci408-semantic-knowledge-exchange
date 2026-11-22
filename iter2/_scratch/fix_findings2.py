from pathlib import Path
p = Path("FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60])
    t = t.replace(old, new)
rep("People, Rec1 blobs: MAE 2.53 (bias +0.28) at 10 px, 2.14 (bias -0.96) at 30 px; fusion does not help (MAE 2.58).",
    "People, Rec1 blobs: MAE 2.53 (bias +0.28) at 10 px, 2.14 (bias -0.96) at 30 px; fusion does not help (MAE 2.58). For comparison, people MAE against ground truth on the same cases: `prompt_only` 4.06 (bias -3.87), `k1` 5.35 (-5.24), detector on the original photo 2.91 (+2.52, because it counts people the ground truth excludes).")
rep("and gets close to ground truth on people (MAE 2.1-2.5, bias near zero at 10 px) where the generative view recovers about 28%.",
    "and is closer to ground truth on people (MAE 2.1-2.5, bias near zero at 10 px) than the generative view (`prompt_only` 4.06, which recovers about 28% of the people the detector sees).")
p.write_text(t, encoding="utf-8"); print("ok")
