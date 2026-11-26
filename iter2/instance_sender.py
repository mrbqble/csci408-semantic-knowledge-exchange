#!/usr/bin/env python3
"""How many ground-truth vehicles could the SENDER report directly? (CARLA v3, cam1, 917 vehicles, GPU)

Instead of (or besides) the segmentation map, the sender would transmit a list of vehicles: class + box, 9 bytes each (1 byte class, 4 x int16).
Tested sources, all scored against the ground truth by Hungarian matching of boxes at IoU 0.5 / 0.3 in the 1024x576 frame, by size and by what the
plain semantic blobs look like (own / merged / no blob):
  Mask2Former Swin-L Cityscapes INSTANCE (car, truck, bus segments, box of the visible mask), at two input sizes
  Faster R-CNN MobileNetV3-Large FPN (COCO), a small detector, at 800 and 480 px short side
  Faster R-CNN ResNet50 v2 (COCO), the large detector used as the 'detector on the original photo' elsewhere
Reference points: the receiver (prompt_only master view + detector) finds 0.49 of these vehicles at IoU 0.5; plain blobs of the transmitted map 0.33.
Detector boxes cover the whole vehicle while the ground truth is the visible part, so IoU 0.3 is the fairer column for them.
Usage: python instance_sender.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

import gtlib
from blob_split import H, W

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "iter1"))
import mmsd_sender as ms  # noqa: E402

INSTANCE_MODEL = "facebook/mask2former-swin-large-cityscapes-instance"
INSTANCE_SIZES = [(512, 1024), (768, 1376)]
VEH_NAMES = ("car", "truck", "bus")
COCO_VEH = (3, 6, 8)
MIN_AREA_1024 = 12                  # same minimum as the blob experiments, in the 1024x576 frame


def to_frame(box, w, h):
    return (box[0] * W / w, box[1] * H / h, box[2] * W / w, box[3] * H / h)


def run_instance(device, cases, torch):
    from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
    proc = AutoImageProcessor.from_pretrained(INSTANCE_MODEL)
    model = Mask2FormerForUniversalSegmentation.from_pretrained(INSTANCE_MODEL).to(device).eval()
    id2label = model.config.id2label
    res = {}
    for size in INSTANCE_SIZES:
        preds, secs = {}, []
        for i, c in enumerate(cases):
            rgb = Image.open(c["photo"]).convert("RGB")
            for rep in (0, 1) if i == 0 else (1,):                      # first photo: untimed warm-up pass
                torch.cuda.synchronize(); t = time.perf_counter()
                inputs = proc(images=rgb, return_tensors="pt", size={"height": size[0], "width": size[1]}).to(device)
                with torch.no_grad():
                    out = model(**inputs)
                r = proc.post_process_instance_segmentation(out, threshold=0.5, target_sizes=[(rgb.height, rgb.width)])[0]
                torch.cuda.synchronize()
            secs.append(time.perf_counter() - t)
            segm = r["segmentation"].cpu().numpy()
            boxes = []
            for s in r["segments_info"]:
                if id2label[int(s["label_id"])] in VEH_NAMES:
                    ys, xs = np.nonzero(segm == s["id"])
                    if len(ys) * (W / rgb.width) * (H / rgb.height) >= MIN_AREA_1024:
                        boxes.append(to_frame((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1), rgb.width, rgb.height))
            preds[c["name"]] = boxes
        res[f"Mask2Former instance {size[0]}x{size[1]}"] = (preds, 1000 * float(np.mean(secs)), sum(p.numel() for p in model.parameters()) / 1e6)
    return res


def run_detector(device, cases, torch, kind, min_size):
    from torchvision.models import detection as D
    if kind == "mobilenet":
        wts = D.FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
        model = D.fasterrcnn_mobilenet_v3_large_fpn(weights=wts)
    else:
        wts = D.FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
        model = D.fasterrcnn_resnet50_fpn_v2(weights=wts)
    model = model.to(device).eval()
    model.transform.min_size = (min_size,)
    model.transform.max_size = int(min_size * 16 / 9) + 2
    tf = wts.transforms()
    preds, secs = {}, []
    for i, c in enumerate(cases):
        rgb = Image.open(c["photo"]).convert("RGB")
        x = tf(rgb).to(device)
        for rep in (0, 1) if i == 0 else (1,):
            torch.cuda.synchronize(); t = time.perf_counter()
            with torch.no_grad():
                o = model([x])[0]
            torch.cuda.synchronize()
        secs.append(time.perf_counter() - t)
        keep = (o["scores"] >= 0.5).cpu().numpy() & np.isin(o["labels"].cpu().numpy(), COCO_VEH)
        preds[c["name"]] = [to_frame(b, rgb.width, rgb.height) for b in o["boxes"].cpu().numpy()[keep]]
    return preds, 1000 * float(np.mean(secs)), sum(p.numel() for p in model.parameters()) / 1e6


def main():
    import torch
    device = ms.pick_device("auto")
    cases = gtlib.gt_cases()
    cats = {c["name"]: gtlib.categories(c["boxes"], c["payload_mask"]) for c in cases}
    n_gt = sum(len(c["boxes"]) for c in cases)
    print(f"{len(cases)} cases, {n_gt} ground-truth vehicles; categories from the transmitted semantic map: " +
          ", ".join(f"{k} {sum(v.count(k) for v in cats.values())}" for k in ("own blob", "merged blob", "no blob")), flush=True)
    print(gtlib.header() + f"{'B/photo':>9}{'ms':>7}{'Mparam':>8}", flush=True)
    runs = {}
    for name, fn in (("instance", lambda: run_instance(device, cases, torch)),
                     ("mobilenet800", lambda: {"Faster R-CNN MobileNetV3 800px": run_detector(device, cases, torch, "mobilenet", 800)}),
                     ("mobilenet480", lambda: {"Faster R-CNN MobileNetV3 480px": run_detector(device, cases, torch, "mobilenet", 480)}),
                     ("resnet", lambda: {"Faster R-CNN ResNet50 v2 800px": run_detector(device, cases, torch, "resnet", 800)})):
        try:
            runs.update(fn())
        except Exception as e:                                           # a missing download must not stop the other sources
            print(f"{name}: failed: {type(e).__name__}: {str(e)[:150]}", flush=True)
        torch.cuda.empty_cache()
    out = {}
    for label, (preds, ms_, params) in runs.items():
        s = gtlib.score(cases, preds, cats)
        mean_boxes = np.mean([len(v) for v in preds.values()])
        print(gtlib.row(label, s) + f"{9 * mean_boxes:9.0f}{ms_:7.0f}{params:8.0f}", flush=True)
        out[label] = dict(s, bytes_per_photo=9 * float(mean_boxes), ms_per_photo=ms_, mparams=params)
    Path("results").mkdir(exist_ok=True)
    Path("results/instance_sender.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
