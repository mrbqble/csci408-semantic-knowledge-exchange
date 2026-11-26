import time, numpy as np, torch
from PIL import Image
import paths
rgb = Image.open(paths.CARLA_V3 / "case112" / "cam1.jpg").convert("RGB")
print("== instance model API (CPU)", flush=True)
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
name = "facebook/mask2former-swin-large-cityscapes-instance"
proc = AutoImageProcessor.from_pretrained(name)
model = Mask2FormerForUniversalSegmentation.from_pretrained(name).eval()
print("id2label:", model.config.id2label, flush=True)
t = time.time()
inputs = proc(images=rgb, return_tensors="pt", size={"height": 512, "width": 1024})
with torch.no_grad():
    out = model(**inputs)
r = proc.post_process_instance_segmentation(out, threshold=0.5, target_sizes=[(rgb.height, rgb.width)])[0]
segm = r["segmentation"].numpy()
print(f"{time.time() - t:.0f} s on CPU; segmentation {segm.shape} ids {np.unique(segm)[:8]}; segments:", flush=True)
for s in r["segments_info"][:12]:
    print("  ", {k: (round(float(v), 2) if not isinstance(v, (bool, int)) else v) for k, v in s.items()}, model.config.id2label[int(s["label_id"])], int((segm == s["id"]).sum()), "px", flush=True)
print("== small detector weights", flush=True)
from torchvision.models import detection as D
w = D.FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
m = D.fasterrcnn_mobilenet_v3_large_fpn(weights=w).eval()
print("mobilenet detector params (M):", round(sum(p.numel() for p in m.parameters()) / 1e6, 1), flush=True)
m.transform.min_size = (480,); m.transform.max_size = 856
with torch.no_grad():
    o = m([w.transforms()(rgb)])[0]
print("detections >= 0.5:", int((o["scores"] >= 0.5).sum()), "labels", sorted(set(o["labels"][o["scores"] >= 0.5].tolist())), flush=True)
print("API_TEST_DONE", flush=True)
