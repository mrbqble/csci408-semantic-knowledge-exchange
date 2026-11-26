from pathlib import Path
p = Path("iter2/README.md"); t = p.read_text(encoding="utf-8")
add = """
## Added after the first pull request (November 2026)

Start with `STATUS_2026-11-11.md` (summary for the meeting), then `NEXT_STEPS_RESULTS.md` (the November experiments) and `demo/` (before/after examples).

| File | What it does |
|---|---|
| `loss_breakdown.py` | Where Rec1's vehicles are lost: by size and by own / merged / no blob in the transmitted map (CARLA v3 ground truth) |
| `gt_eval.py`, `gtlib.py` | Ground-truth scoring: recall at IoU 0.5 / 0.3 by size, precision, count error, paired bootstrap against a baseline run |
| `compare_runs.py` | Compares two runs against the detector on the original photo (for the real-world set, which has no ground truth) |
| `refine_report.py`, `refine_full_report.py` | The crop method (`--variants prompt_refine`): report on 20 selected images and on every case |
| `blob_split.py` | Can the existing payload separate touching vehicles? (shape and edge-map splitting) |
| `seg_resolution.py` | The sender's segmenter at larger input sizes |
| `instance_sender.py` | Sender-side vehicle list: instance segmentation and two detectors |
| `hp_sweep.py` | Receiver hyperparameter sweep (cases 1-24) with a hold-out check of the best setting (cases 25-60) |
| `training_prep.py` | Training crops for fine-tuning the ControlNets (written to `data/train_crops`, not in git) |
| `make_next_report.py`, `make_demo.py` | Build `NEXT_STEPS_RESULTS.md` and `demo/` |

New options: `coordinator.py --steps --guidance --control-end --negative-prompt` and the variant `prompt_refine`; `analysis.py --analysis-dir` (write an analysis into a separate folder).

| Folder under `results/` | How it was produced |
|---|---|
| `v3/prompt_refine`, `rw_core/prompt_refine`, `refine/analysis_*` | Crop method on 20 selected and on all cases |
| `v3_2048` | v3 cases 1-24, `--variants prompt_only --size 2048x1152` |
| `hp/<config>`, `hp/c0.7_seg1.5_holdout` | `hp_sweep.py` |
| `v3_cn07_15`, `rw_cn07_15` | `--cn-scales 0.7,1.5` on every case (v3 cases 1-60 copied from the sweep runs: same settings and seed) |
| `blob_split.json`, `seg_resolution.json`, `instance_sender.json`, `loss_breakdown.json`, `training_split.json`, `gt_eval_*.json` | The scripts of the same name |

Data generated on the OMEN, not in git: `data/v4_payloads` (CARLA v4, 224 training cases, made with `../carla/generate_cases_v3.py --seed 31`), `data/rw_core_all_payloads` (all 366 real-world core cases), `data/train_crops` (8,620 training and 1,088 validation crops; CARLA v3 and the 61 evaluated real-world cases are held out).
"""
p.write_text(t.rstrip() + "\n" + add, encoding="utf-8")
r = Path("README.md"); rt = r.read_text(encoding="utf-8")
anchor = "**Team:** Bibol Assetbek ? Temirshin Kantemirov ? Yernur Kenzhaly ? Zhengis Kosher\n"
assert rt.count(anchor) == 1
note = anchor + "\n> **Latest work (Nov 2026):** iteration 2, the multi-camera receiver with its evaluation, is in [`iter2/`](iter2/). Start with [`iter2/STATUS_2026-11-11.md`](iter2/STATUS_2026-11-11.md); before/after examples are in [`iter2/demo/`](iter2/demo/).\n"
r.write_text(rt.replace(anchor, note), encoding="utf-8")
print("readmes updated")
