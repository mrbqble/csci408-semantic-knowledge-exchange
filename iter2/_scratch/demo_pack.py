from pathlib import Path
from PIL import Image
for png in Path("fusion_demo").rglob("*.png"):
    Image.open(png).convert("RGB").save(png.with_suffix(".jpg"), quality=92)
readme = """# Damir's multi-camera pipeline: end-to-end examples

Built with `fusion_demo.py`, following Damir's diagram of 17 Nov 2026. Each folder holds one case; open `pipeline.jpg` first.

**Sender side, every device:** the seed paper's three-element payload: segmentation map (sent at half resolution), edge map (full resolution) and caption (`payload_<cam>_*`).

**Receiver side:**
1. Reconstruct every device from its own payload: single-camera MMSD (SD 1.5 + ControlNet canny + seg, the device's own caption), generated at the photo's resolution, 1920x1088 (`reconstruction_<cam>.jpg`).
2. Choose the main reconstruction (cam1, the dataset's main camera) and take its segmentation and edge maps.
3. Build a global caption from all devices' captions (`settings.json`).
4. Fuse in SD 1.5 img2img (`final_reconstruction.jpg`):
   - start from the main reconstruction with noise added (strength 0.5);
   - main segmentation and edge maps on the ControlNets;
   - the other devices' reconstructions on the IP-Adapter (`h94/IP-Adapter`, `ip-adapter_sd15`, scale 1.0);
   - the global caption as prompt.
5. Control: the same pass without the IP-Adapter (`control_no_ip_adapter.jpg`), to see what the supporting views change.

Damir's code and ours:

```
out = pipe(prompt=global_caption, image=main_recon, control_image=[main_edge, main_seg],
           ip_adapter_image=supporting_views, strength=0.5)                     # Damir
coord.i2i(prompt=global_caption, image=main_recon, control_image=[main_edge, main_seg],
          ip_adapter_image_embeds=[mean CLIP embedding of supporting_views], strength=0.5,
          num_inference_steps=20, guidance_scale=7.5)                            # ours (coordinator.fuse_i2i)
```

One IP-Adapter cannot take a list of images directly in `diffusers`, so the supporting views are combined by averaging their CLIP image embeddings.
Images here are JPEG copies; the PNG originals stay on the OMEN. Timings on an RTX 3070 laptop GPU: about 75 s per device reconstruction, about 39 s for the fusion pass.

| Folder | Devices | Note |
|---|---|---|
| `rw_case1` | 3 phones (real-world, Astana) | parked cars along a road |
| `v3_case10` | 4 CARLA cameras | pedestrians at a junction, few and distant cars |

Whether the fusion preserves car numbers and positions better than the main reconstruction alone is measured with the VLM judge (setups `rw_fuse`, `rw_fuse_noip` in `vlm_judge.py`).
"""
Path("fusion_demo/README.md").write_text(readme, encoding="utf-8")
print("jpg copies + README written")
