from pathlib import Path
p = Path("VLM_FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("# VLM-judge evaluation (Damir's requirement), 13-14 Nov 2026\n", "# VLM-judge evaluation (Damir's requirement), 13-19 Nov 2026\n")
anchor = "## 0. Headline (14 Nov)"
new = """## Update 19 Nov: Damir's multi-camera fusion beats his single-camera MMSD

**Pipeline** (Damir's diagram of 17 Nov; `coordinator.py` variants `fuse` / `fuse_noip`, example figures in `fusion_demo/`):
- every device is reconstructed from its own payload;
- the main reconstruction (cam1, at the paper settings of section 0) gets noise added (img2img, strength 0.5);
- the main camera's segmentation and edge maps go on the ControlNets;
- the other devices' reconstructions go on the IP-Adapter (mean CLIP embedding, scale 1.0);
- the global caption is the prompt.

The supporting reconstructions were made at 896x512 to save time. The IP-Adapter sees them at 224x224 anyway. The control is the same img2img pass without the IP-Adapter.

| Joint (numbers / positions) | CARLA v3 (112) | Real-world (61) |
|---|---|---|
| Damir's single-camera MMSD (the main reconstruction) | 56.2% (57.1 / 88.4) | 75.4% (77.0 / 95.1) |
| Our earlier multi-camera receiver (all cameras' captions only) | 50.0% (50.9 / 96.4) | 73.8% (73.8 / 95.1) |
| Control: img2img second pass without the IP-Adapter | 61.6% (63.4 / 92.9) | 63.9% (63.9 / 93.4) |
| **Damir's fusion** | **69.6%** (69.6 / 93.8) | **80.3%** (80.3 / 96.7) |

| Paired test on the joint score (McNemar) | CARLA v3 | Real-world |
|---|---|---|
| Fusion vs single-camera MMSD | **+13.4 pts** (31 better / 16 worse, p = 0.040) | +4.9 pts (7 / 4, p = 0.55) |
| Fusion vs control (what the supporting views add) | +8.0 pts (21 / 12, p = 0.16) | **+16.4 pts** (13 / 3, p = 0.021) |
| Control vs single-camera MMSD (the second pass alone) | +5.4 pts (19 / 13, p = 0.38) | -11.5 pts (4 / 11, p = 0.12) |
| Fusion vs our earlier captions-only receiver | **+19.6 pts** (35 / 13, p = 0.002) | +6.6 pts (12 / 8, p = 0.50) |

- **The first multi-camera receiver that beats the single-camera baseline under the judge.** The gain is significant on CARLA and points the same way on real-world, where joint success reaches 80.3%.
- **The supporting views always help.** The fusion beats the same pass without them on both datasets, significantly on real-world. On CARLA, part of the gain already comes from the second pass itself. On real-world the second pass alone hurts, and the supporting views more than make up for it.
- **Trade-off.** The fusion fixes 31 of the 49 CARLA cases where the single camera fails, and breaks 16 of the 63 where it passes. On real-world it fixes 7 of 15 and breaks 4 of 46.
- **Untuned so far:** strength 0.5 and IP-Adapter scale 1.0 (both as in Damir's code), and the 896x512 supporting reconstructions.

"""
rep(anchor, new + anchor)
rep("## 6. Open questions for Damir\n", "## 6. Open questions for Damir\n\n**Damir's answer (18 Nov):** the paper's judge was an older Gemma model that is no longer available. That explains why our 41% on the paper's own Cityscapes images differs from the paper's 86%. Absolute numbers can only be compared under the same judge.\n\n")
p.write_text(t, encoding="utf-8"); print("findings updated")
r = Path("README.md"); rt = r.read_text(encoding="utf-8").rstrip()
rt += """

Damir's fusion (19 Nov):
1. Supporting reconstructions: `coordinator.py --payloads data/<set>_native --out results/<set>_support --variants k1 --k1-cams all --size 896x512 --palette cs`.
2. Fusion and control: `coordinator.py --payloads <paper payloads> --out results/<set>_fuse --variants fuse,fuse_noip --size 1920x1088 --palette cs --fuse-main results/<set>_paper/k1 --fuse-support results/<set>_support/k1`.
3. Judge setups: `rw_fuse`, `rw_fuse_noip`, `v3_fuse`, `v3_fuse_noip`.

For one case with every intermediate saved: `fusion_demo.py --dataset rw --case 1`.
"""
r.write_text(rt + "\n", encoding="utf-8"); print("README updated")
