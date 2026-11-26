"""Stage the 5 palette-test reconstructions for an eval-only smoke test of palette_eval.py (OMEN)."""
import shutil
from pathlib import Path

r = Path("results")
for v, src, pattern in [("A_cs_full", r / "receiver_smoke", "*_blip_reconstructed.png"),
                        ("B_ade_full", r / "palette_test" / "B_ade_full", "*.png")]:
    dst = r / "palette100_smoke" / v
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob(pattern)):
        shutil.copy2(f, dst / (f.name.replace("_blip_reconstructed.png", ".png")))
print("staged", {v: len(list((r / "palette100_smoke" / v).glob("*.png"))) for v in ("A_cs_full", "B_ade_full")})
