"""Mask2Former (as loaded by mmsd_sender.py) vs Cityscapes ground truth on 10 val images (OMEN, CPU).

Checks that the "MISSING swin.layernorm" warning at load time does not hurt the
segmenter: the published single-scale Cityscapes val mIoU of Mask2Former Swin-L
is 83.3. Standard protocol: one confusion matrix over all images, 19 classes,
ignore label 255.
"""
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from cityscapesscripts.helpers.labels import id2label
from PIL import Image

import mmsd_sender as ms

import sys
DEVICE = sys.argv[1] if len(sys.argv) > 1 else "cpu"
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 50
torch.set_num_threads(4)
lut = np.full(256, 255, np.uint8)
for i, lab in id2label.items():
    if 0 <= i < 256 and 0 <= lab.trainId < 19:
        lut[i] = lab.trainId

here = Path(__file__).resolve().parent
gt_zip = zipfile.ZipFile(here.parent / "gtFine_trainvaltest.zip")
files = sorted((here / "data" / "cityscapes_val").glob("*.png"))[::STEP]
seg = ms.Segmenter(DEVICE)
conf = np.zeros((19, 19), np.int64)
for f in files:
    stem = f.name.replace("_leftImg8bit.png", "")
    city = stem.split("_")[0]
    gt = lut[np.asarray(Image.open(BytesIO(gt_zip.read(f"gtFine/val/{city}/{stem}_gtFine_labelIds.png"))))]
    pred = seg(Image.open(f).convert("RGB"))
    valid = gt != 255
    conf += np.bincount(19 * gt[valid].astype(np.int64) + pred[valid].astype(np.int64), minlength=361).reshape(19, 19)
    if STEP > 1: print(f"{stem}: pixel acc {(gt[valid] == pred[valid]).mean():.3f}", flush=True)
iou = np.diag(conf) / (conf.sum(0) + conf.sum(1) - np.diag(conf))
print(f"mIoU over {len(files)} images: {100 * np.nanmean(iou):.1f} (published Swin-L single-scale: 83.3); "
      f"pixel acc {100 * np.diag(conf).sum() / conf.sum():.1f}")
print("per-class IoU:", " ".join(f"{k}:{100 * v:.0f}" for k, v in zip(range(19), iou)))
