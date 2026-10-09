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
# run this where the images are stored, e.g. on the OMEN:
# "$PY" mmsd_sender.py --images images_cityscapes --out results/iteration1_mmsd_cityscapes.json
