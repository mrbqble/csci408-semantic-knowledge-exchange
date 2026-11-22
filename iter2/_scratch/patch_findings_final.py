from pathlib import Path
p = Path("VLM_FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("**Coverage:** 1,926 of 1,930 pairs over 22 setups. The last 4 pairs (one or two each in `rw_default`, `rw_k1` and `v3_resolution_only`) are being retried and will update `VLM_JUDGE_REPORT.md`, which holds the full table with 95% intervals and every paired test.",
    "**Coverage:** all 1,930 pairs over 22 setups. `VLM_JUDGE_REPORT.md` holds the full table with 95% intervals and every paired test.")
rep("| Current receiver: 1024x576, Cityscapes palette, all cameras' captions | 36.6% (36.6) | 28.3% (28.3) |", "| Current receiver: 1024x576, Cityscapes palette, all cameras' captions | 36.6% (36.6) | 27.9% (27.9) |")
rep("| Same, reference camera only | 33.0% (33.9) | 27.1% (27.1) |", "| Same, reference camera only | 33.0% (33.9) | 26.2% (26.2) |")
rep("| Working resolution only (896x512, edges at that size) | 37.8% (39.6) | 44.3% (44.3) |", "| Working resolution only (896x512, edges at that size) | 37.5% (39.3) | 44.3% (44.3) |")
rep("| Both fixes vs current receiver | +7.1 pts (p = 0.27) | **+18.3 pts (p = 0.019)** |", "| Both fixes vs current receiver | +7.1 pts (p = 0.27) | **+18.0 pts (p = 0.019)** |")
rep("| Working resolution alone | +0.9 pts (p = 1.0) | **+15.0 pts (p = 0.049)** |", "| Working resolution alone | +0.9 pts (p = 1.0) | **+16.4 pts (p = 0.031)** |")
rep("| ADE20K palette alone | +0.9 pts (p = 1.0) | +1.7 pts (p = 1.0) |", "| ADE20K palette alone | +0.9 pts (p = 1.0) | +1.6 pts (p = 1.0) |")
rep("| All cameras' captions vs reference camera only, current receiver | +3.6 pts (p = 0.59) | +1.7 pts (p = 1.0) |", "| All cameras' captions vs reference camera only, current receiver | +3.6 pts (p = 0.59) | +1.6 pts (p = 1.0) |")
rep("**Damir's resolution point is what matters on real photos** (+15 to +18 points).", "**Damir's resolution point is what matters on real photos** (+16 to +18 points).")
p.write_text(t, encoding="utf-8"); print("findings updated")
