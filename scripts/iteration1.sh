#!/usr/bin/env bash
# Iteration 1 measurement: MMSD sender payload and latency per component.
# Run from anywhere; uses the repository's .venv if it exists.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python

"$PY" -m pytest -q tests
"$PY" fetch_coco_urban.py --out data/coco_urban
"$PY" mmsd_sender.py --images data/coco_urban --out results/iteration1_mmsd_coco_urban.json

# Cityscapes (2048x1024, the seed paper's dataset) needs the registered download;
# run these where the 500 val images are stored (on the OMEN: iter1/data/cityscapes_val):
# "$PY" mmsd_sender.py --images data/cityscapes_val --out results/iteration1_mmsd_cityscapes_val.json --device cuda --save-components data/components_m2f
# "$PY" encoding_ablation.py --images data/cityscapes_val --out results/iteration1_encoding_ablation_cityscapes_val.json --device cuda
# "$PY" canny_sweep.py --images data/cityscapes_val --out results/iteration1_canny_sweep_cityscapes_val.json
# "$PY" mmsd_sender.py --images data/cityscapes_val --limit 25 --device cpu --threads 4 --out results/iteration1_mmsd_cityscapes_cpu4.json
# "$PY" receiver_smoke_test.py --components data/components_m2f --limit 5 --out results/iteration1_receiver_smoke_test.json --save-dir results/receiver_smoke
# "$PY" palette_test.py --components data/components_m2f --originals data/cityscapes_val --baseline results/receiver_smoke --limit 5 --out results/iteration1_palette_test.json --save-dir results/palette_test
# "$PY" palette_eval.py --components data/components_m2f --originals data/cityscapes_val --step 5 --limit 100 --out results/iteration1_palette_eval_100.json --save-dir results/palette100
