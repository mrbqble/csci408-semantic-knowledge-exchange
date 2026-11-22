from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep('''GROUPS["fusion"] = ["rw_fuse", "rw_fuse_noip", "v3_fuse", "v3_fuse_noip"]''', '''GROUPS["fusion"] = ["rw_fuse", "rw_fuse_noip", "v3_fuse", "v3_fuse_noip"]
# 19-20 Nov (Damir): supporting reconstructions at full resolution (paper settings), then one-factor tuning of strength and IP-Adapter scale
for _ds in ("v3", "rw"):
    RUNS[f"{_ds}_fuseF"] = (_ds, f"results/{_ds}_fuseF_st0.5/fuse/case{{c}}.png", "fusion with full-resolution supporting reconstructions (strength 0.5, IP scale 1.0)")
    for _st in ("0.3", "0.4", "0.6"):
        RUNS[f"{_ds}_fuseF_st{_st}"] = (_ds, f"results/{_ds}_fuseF_st{_st}/fuse/case{{c}}.png", f"tuning: strength {_st}, IP scale 1.0 (full-resolution supports)")
    for _ip in ("0.5", "0.75"):
        RUNS[f"{_ds}_fuseF_ip{_ip}"] = (_ds, f"results/{_ds}_fuseF_st0.5/fuse_s{_ip}/case{{c}}.png", f"tuning: strength 0.5, IP scale {_ip} (full-resolution supports)")
GROUPS["fusion_full"] = ["rw_fuseF", "v3_fuseF"]
GROUPS["tune"] = [f"{d}_fuseF_{k}" for d in ("rw", "v3") for k in ("st0.3", "st0.4", "st0.6", "ip0.5", "ip0.75")]
GROUPS["fullres_tune"] = GROUPS["fusion_full"] + GROUPS["tune"]''')
rep('''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"] + GROUPS["fusion"]''',
    '''GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"] + GROUPS["fusion"] + GROUPS["fullres_tune"]''')
rep('''    ("fuse_noip", "paper_k1", "re-denoising the main reconstruction alone (img2img, no IP-Adapter)"),''', '''    ("fuse_noip", "paper_k1", "re-denoising the main reconstruction alone (img2img, no IP-Adapter)"),
    ("fuseF", "fuse", "supporting reconstructions at full resolution vs 896x512 (fusion, strength 0.5, IP scale 1.0)"),
    ("fuseF", "paper_k1", "fusion with full-resolution supports vs the single-camera MMSD"),''')
p.write_text(t, encoding="utf-8"); print("judge setups added")
