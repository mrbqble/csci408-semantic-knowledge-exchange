"""Mask2Former accuracy vs input resolution on 50 Cityscapes val images (OMEN, GPU).

transformers 5.17's processor resizes to a fixed 384x384 square by default. This
runs the same model and processor with explicit sizes and scores each against the
ground truth (19 classes, ignore 255, one confusion matrix per setting).
"""
import time
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from cityscapesscripts.helpers.labels import id2label
from PIL import Image

import mmsd_sender as ms

lut = np.full(256, 255, np.uint8)
for i, lab in id2label.items():
    if 0 <= i < 256 and 0 <= lab.trainId < 19:
        lut[i] = lab.trainId
here = Path(__file__).resolve().parent
gt_zip = zipfile.ZipFile(here.parent / "gtFine_trainvaltest.zip")
files = sorted((here / "data" / "cityscapes_val").glob("*.png"))[::10]
gts = {}
for f in files:
    stem = f.name.replace("_leftImg8bit.png", "")
    gts[f] = lut[np.asarray(Image.open(BytesIO(gt_zip.read(f"gtFine/val/{stem.split('_')[0]}/{stem}_gtFine_labelIds.png"))))]

seg = ms.Segmenter("cuda")
for h, w in [(384, 384), (512, 1024), (768, 1536), (1024, 2048)]:
    conf, t0, shape = np.zeros((19, 19), np.int64), time.perf_counter(), None
    try:
        for f in files:
            img = Image.open(f).convert("RGB")
            inputs = seg.proc(images=img, size={"height": h, "width": w}, return_tensors="pt").to("cuda")
            shape = shape or tuple(inputs["pixel_values"].shape[-2:])
            with torch.no_grad():
                out = seg.model(**inputs)
            pred = seg.proc.post_process_semantic_segmentation(out, target_sizes=[(img.height, img.width)])[0].cpu().numpy()
            gt = gts[f]; valid = gt != 255
            conf += np.bincount(19 * gt[valid].astype(np.int64) + pred[valid].astype(np.int64), minlength=361).reshape(19, 19)
        iou = np.diag(conf) / (conf.sum(0) + conf.sum(1) - np.diag(conf))
        print(f"input {shape}: mIoU {100 * np.nanmean(iou):.1f}, pixel acc {100 * np.diag(conf).sum() / conf.sum():.1f}, "
              f"pole {100 * iou[5]:.0f}, traffic light {100 * iou[6]:.0f}, person {100 * iou[11]:.0f}, rider {100 * iou[12]:.0f}, "
              f"car {100 * iou[13]:.0f} | {(time.perf_counter() - t0) / len(files):.2f} s per image", flush=True)
    except torch.OutOfMemoryError:
        print(f"input {h}x{w}: out of GPU memory", flush=True)
        torch.cuda.empty_cache()
print("RES_TEST_DONE")
