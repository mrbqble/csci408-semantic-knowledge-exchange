from pathlib import Path
p = Path("iter2/README.md"); t = p.read_text(encoding="utf-8")
add = """
## VLM-judge evaluation (13 Nov 2026, after the meeting with Damir)

Damir's decisions: the VLM judge is the required metric (the earlier metrics stay as extra); the payload stays the three elements of the seed paper (no
vehicle list); payload size is reported per element; the judge is run without and with two receiver fixes (the models' working resolution and the
ADE20K palette expected by the segmentation ControlNet). Results: `VLM_FINDINGS.md` (interpretation) and `VLM_JUDGE_REPORT.md` (all setups, intervals,
paired tests); payload sizes: `PAYLOAD_SIZES.md`.

| File | What it does |
|---|---|
| `vlm_judge.py` | VLM judge with Damir's model, prompts and parsing (`batch_evaluation.py`); resumable, parallel workers, waits out API outages; `--report` |
| `payload_sizes.py` | Size of each payload element per photo, against the photo as stored and as JPEG q90 |
| `payloads.py --work-size 896x512` | Payload at the receiver's working resolution (map sent at 896x512, edge map computed at 896x512) |

The key is read from `GEMINI_API_KEY` (environment or Windows user environment) or `~/.gemini_api_key`; never stored in the repo.
Runs: `results/v3_native_ade`, `rw_native_ade` (both fixes), `*_native_cs` (resolution only), `*_ade` (palette only), `*_native_ade_cn` (both fixes +
canny 0.7 / seg 1.5); payloads in `data/v3_native`, `data/rw_native` (not in git). Raw judge answers: `results/vlm/*.jsonl`.
"""
p.write_text(t.rstrip() + "\n" + add, encoding="utf-8"); print("README updated")
