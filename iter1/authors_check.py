"""Run the seed authors' scripts 01 + 02 on the first 10 Cityscapes val images (OMEN, local only).

Their code is not copied into our repository. The only change: Gemma 3n is skipped,
because google/gemma-3n-e2b-it is a gated model and no Hugging Face token is set up.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

here = Path(__file__).resolve().parent                     # ...\csci408-probe\iter1
check = here / "authors_check"
check.mkdir(exist_ok=True)
zipfile.ZipFile(here / "SSMD-SAMR-main.zip").extractall(check)
src = check / "SSMD-SAMR-main" / "SSMD"

for f in sorted((here / "data" / "cityscapes_val").glob("*.png"))[:10]:
    city_dir = src / "data" / "leftImg8bit" / "val" / f.name.split("_")[0]
    city_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, city_dir / f.name)

code = (src / "01_generate_components.py").read_text(encoding="utf-8")
for old, new in [
    ("    gemma = Gemma3VisionCaptioner()\n    gemma.load()\n", "    gemma = None  # Gemma 3n skipped (gated model)\n"),
    ("            gemma_text = gemma.generate_caption(image)\n", '            gemma_text = ""\n'),
]:
    assert code.count(old) == 1, old
    code = code.replace(old, new)
(src / "01_nogemma.py").write_text(code, encoding="utf-8")

for script in ("01_nogemma.py", "02_preprocess_components.py"):
    print("running authors'", script, flush=True)
    subprocess.run([sys.executable, script], cwd=src, check=True)
print("AUTHORS_CHECK_DONE", flush=True)
