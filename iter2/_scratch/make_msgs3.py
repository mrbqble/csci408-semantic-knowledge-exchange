from pathlib import Path
import subprocess
msg = """iter2: VLM-judge evaluation (Damir, 11 Nov), payload sizes per element

- vlm_judge.py: Damir's judge (gemma-4-31b-it, his prompts and parsing), resumable, parallel, waits out API outages
- 22 setups judged (1,926 of 1,930 pairs): current receiver vs Damir's two fixes (working resolution, ADE20K palette),
  single vs multi camera, calibration (original vs itself = 100%), Cityscapes reproduction of the seed receiver (41% joint)
- payloads.py --work-size: payload at the receiver's working resolution (16-21 KB per camera instead of 51-56 KB)
- payload_sizes.py / PAYLOAD_SIZES.md: size of segmentation map, edge map and caption per photo
- VLM_FINDINGS.md: interpretation; VLM_JUDGE_REPORT.md: all numbers; raw judge answers in results/vlm
- gt_eval.py / compare_runs.py: separate x/y scaling for non-1024x576 runs
"""
Path("iter2/_scratch/commit_msg3.txt").write_bytes(msg.encode("utf-8"))
body = subprocess.run(["gh", "pr", "view", "34", "--json", "body", "-q", ".body"], capture_output=True, text=True, encoding="utf-8").stdout.strip()
update = """

## Update, 13 Nov 2026 (third commit): VLM-judge evaluation
Following the meeting with Damir (11 Nov): the VLM judge is the required metric, the payload stays the seed paper's three elements, payload sizes are reported per element, and the judge is run without and with two receiver fixes.
- `iter2/VLM_FINDINGS.md`: the judge is consistent (original vs itself 100%). Our reproduction of the seed receiver on Cityscapes scores 41% joint with this judge, against the paper's 86-87%. On our data, Damir's working-resolution fix helps on real photos (+15 to +18 points, p < 0.05), the palette fix changes nothing, and multi-camera captions never beat the reference camera alone. Best setting: 51-57% joint.
- `iter2/PAYLOAD_SIZES.md`: the edge map is 91% of today's payload; at the working resolution the payload drops to 16-21 KB per camera.
- Open questions for Damir: the paper's ControlNet weights, the judge version behind Table 6, and a sample of the paper's own reconstructions to calibrate against.
"""
Path("iter2/_scratch/pr_body3.md").write_bytes((body + update).encode("utf-8"))
print("messages written")
