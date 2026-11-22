from pathlib import Path
p = Path("STATUS_2026-11-11.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:50]); t = t.replace(old, new)
rep("{{V3_CN_ROW}}", "| Receiver, fused prompt, ControlNet canny 0.7 / seg 1.5 (proposed default) | 0.537 | 0.61 | 2.50 | 10.5 s |")
rep("| Sender-side vehicle list (Faster R-CNN ResNet50 at the sender), see 4 | 0.78 | 0.85 | 1.46 | 97 ms at the sender, +68 B per photo |\n",
    "| Sender-side vehicle list (Faster R-CNN ResNet50 at the sender), see 4 | 0.78 | 0.85 | 1.46 | 97 ms at the sender, +68 B per photo |\n\n"
    "Paired change in per-case recall, canny 0.7 / seg 1.5 minus default: +0.046 (95% CI +0.019 to +0.074); on cases 61-112, which were not used to choose the setting: +0.047 (+0.013 to +0.080). "
    "Recall by size goes 0.07 to 0.14 under 24 px and 0.38 to 0.44 at 24-48 px.\n")
rep("{{RW_ROWS}}", "| | Recall | Precision | Vehicles under 24 px | 24-48 px | 48-120 px |\n|---|---|---|---|---|---|\n"
    "| Receiver, current default | 0.469 | 0.76 | 0.17 | 0.17 | 0.79 |\n| Receiver, canny 0.7 / seg 1.5 | 0.562 | 0.75 | 0.21 | 0.31 | 0.88 |\n\n"
    "Paired change in per-case recall: +0.066 (95% CI +0.030 to +0.099).")
rep("- **Not the payload:** 96% of the vehicles the detector finds on the original photo are present in the transmitted map; they are lost when the image is generated.",
    "- **Not the payload:** 96% of the vehicles the detector finds on the original photo are present in the transmitted map (measured on CARLA v2); they are lost when the image is generated.")
rep("{{CN_DECISION}}", "confirmed on every case: CARLA +0.046 (CI +0.019 to +0.074), real-world +0.066 (CI +0.030 to +0.099); CARLA precision 0.63 to 0.61. Proposed new default (`--cn-scales 0.7,1.5`), not switched yet")
rep("{{CN_QUESTION}}", "5. We propose switching the receiver default to ControlNet canny 0.7 / seg 1.5, which needs only one flag.")
assert "{{" not in t
p.write_text(t, encoding="utf-8"); print("status filled")
