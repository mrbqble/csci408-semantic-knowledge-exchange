from pathlib import Path
import subprocess
msg = """iter2: November experiments, demo and meeting status (11 Nov)

- STATUS_2026-11-11.md: summary for the meeting with Damir (pipeline, metric, results, questions)
- demo/: 18 before/after cases (10 CARLA v3, 8 real-world) chosen by a fixed worst-to-best rule, with Rec1's payload files
- new experiments (NEXT_STEPS_RESULTS.md): loss breakdown, splitting merged blobs from the payload, prompt_refine
  (crop-and-redraw of small cars), 2048x1152 generation, segmenter input size, sender-side vehicle list, hyperparameter
  sweep with hold-out; ControlNet canny 0.7 / seg 1.5 confirmed on all cases (proposed default, not switched)
- coordinator.py: --steps --guidance --control-end --negative-prompt, variant prompt_refine; analysis.py --analysis-dir
  (defaults unchanged)
- training data prep (training_prep.py; crops stay out of git), result summaries force-added
"""
Path("iter2/_scratch/commit_msg2.txt").write_bytes(msg.encode("utf-8"))
body = subprocess.run(["gh", "pr", "view", "34", "--json", "body", "-q", ".body"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
update = """

## Update, 10 Nov 2026 (second commit)
- `iter2/STATUS_2026-11-11.md`: summary for the meeting with Damir (what exists, the metric, results, open questions).
- `iter2/demo/`: 18 before/after examples (10 CARLA v3, 8 real-world) chosen by a fixed worst-to-best rule, each with the payload files Rec1 transmits and both reconstructions.
- New experiments, compiled in `iter2/NEXT_STEPS_RESULTS.md`: where vehicles are lost (size, merged blobs); splitting merged blobs from the existing payload (not possible with rules); crop-and-redraw of small cars (`prompt_refine`: +0.019 recall on all 173 cases, off by default); generation at 2048x1152 (no gain); segmenter input size (no gain); sender-side vehicle list (Faster R-CNN at the sender: recall 0.78 vs ground truth, +68 B per photo); hyperparameter sweep with a hold-out check.
- ControlNet canny 0.7 / seg 1.5 confirmed on every case: CARLA v3 recall 0.485 to 0.537 against ground truth (paired +0.046, CI +0.019 to +0.074), real-world 0.469 to 0.562 against the detector on the original (+0.066, CI +0.030 to +0.099). Proposed as the new default; not switched yet.
- `coordinator.py` options `--steps`, `--guidance`, `--control-end`, `--negative-prompt` and the variant `prompt_refine`; `analysis.py --analysis-dir`. Defaults are unchanged.
- Training data prepared on the OMEN, not in git: CARLA v4 (224 cases, `carla/generate_cases_v3.py --seed 31`) and 8,620 training / 1,088 validation crops, with CARLA v3 and the 61 evaluated real-world cases held out.
"""
Path("iter2/_scratch/pr_body2.md").write_bytes((body + update).encode("utf-8"))
print("message files written")
