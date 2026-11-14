#!/usr/bin/env python3
"""Edge-node stage (Iteration 2): one semantic payload per camera photo.

Every camera of every case runs the unchanged MMSD sender of Iteration 1
(iter1/mmsd_sender.py): Mask2Former Swin-Large segmentation map, Canny edge map,
BLIP caption. The three modalities are written the way they would be transmitted
(lossless WebP, WebP, UTF-8), so the coordinator only ever sees the decoded payload.
The network between node and coordinator is out of scope (no delay, no loss).

Dataset layout (both CARLA datasets and the real-world dataset use it):
    <root>/caseK/camJ.(jpg|png)        photos of one moment, one per camera

Output:
    <out>/caseK/camJ_seg.webp  camJ_edge.webp  camJ_caption.txt  camJ_meta.json
    <out>/payload_index.json           bytes and per-stage milliseconds of every payload

Usage
  python payloads.py --dataset C:/carla_multicam_kit/output/carla_dataset_v2_low2m_3to6cams_hd --out data/carla_v2_payloads
Resumable: payloads already on disk are skipped.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "iter1"))
import mmsd_sender as ms  # noqa: E402

SEG_INPUT = (512, 1024)       # segmenter input (H, W): the operating point recorded in Iteration 1
SEG_TX_WIDTH = 1024           # transmitted map width, as in the paper (1024x512 for 2048x1024 images)
IMG_EXT = (".jpg", ".jpeg", ".png")


def case_dirs(root):
    return sorted((p for p in root.iterdir() if p.is_dir() and p.name.startswith("case") and p.name[4:].isdigit()),
                  key=lambda p: int(p.name[4:]))


def cam_images(case_dir):
    return sorted((p for p in case_dir.iterdir() if p.suffix.lower() in IMG_EXT and p.stem.startswith("cam")),
                  key=lambda p: int(p.stem[3:]))


def seg_tx_size(w, h):
    """Transmitted segmentation-map size: 1024 wide, same aspect ratio, height a multiple of 8."""
    return SEG_TX_WIDTH, int(round(SEG_TX_WIDTH * h / w / 8)) * 8


def timestamps(root):
    """Case -> simulator frame (CARLA manifest); None when the dataset has no manifest."""
    mf = root / "manifest.json"
    if not mf.exists():
        return {}
    return {c["folder"]: c.get("frame") for c in json.loads(mf.read_text())["cases"]}


def parse_range(text, n):
    if not text:
        return set(range(1, n + 1))
    out = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cases", default="", help="e.g. 1-20,25 (default: all)")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--seg-input", default="", help="HxW segmenter input, e.g. 1024x2048 (default: the iteration-1 operating point 512x1024)")
    ap.add_argument("--work-size", default="", help="WxH, e.g. 896x512: send the segmentation map at this size and compute the edge map on the photo resized to it "
                    "(the receiver models' working resolution); default: map at 1024 wide, edges at full resolution")
    args = ap.parse_args()
    if sys.platform == "win32":      # keep the laptop awake during long runs
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

    import torch
    device = ms.pick_device(args.device)
    dirs = case_dirs(args.dataset)
    want = parse_range(args.cases, max(int(d.name[4:]) for d in dirs))
    dirs = [d for d in dirs if int(d.name[4:]) in want]
    ts = timestamps(args.dataset)
    seg_input = tuple(int(v) for v in args.seg_input.lower().split("x")) if args.seg_input else SEG_INPUT
    seg, cap = ms.Segmenter(device, input_size=seg_input), ms.Captioner(device)
    work = tuple(int(v) for v in args.work_size.lower().split("x")) if args.work_size else None
    index_path = args.out / "payload_index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    warmed = False

    for ci, cdir in enumerate(dirs, 1):
        out_dir = args.out / cdir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        for img_path in cam_images(cdir):
            stem = img_path.stem
            meta_path = out_dir / f"{stem}_meta.json"
            if meta_path.exists():
                continue
            rgb = Image.open(img_path).convert("RGB")
            if not warmed:                       # untimed CUDA warm-up on the first photo
                seg(rgb); cap(rgb); warmed = True
            row = {"case": cdir.name, "cam": stem, "timestamp": ts.get(cdir.name), "source": str(img_path),
                   "w": rgb.width, "h": rgb.height, "file_b": img_path.stat().st_size}
            t = time.perf_counter(); labels = seg(rgb); ms._sync(device); row["seg_infer_ms"] = 1e3 * (time.perf_counter() - t)
            seg_size = work or seg_tx_size(rgb.width, rgb.height)
            edge_src = rgb.resize(work, Image.LANCZOS) if work else rgb
            row["work_size"] = list(work) if work else None
            t = time.perf_counter(); seg_b = ms.encode_segmentation(labels, size=seg_size); row["seg_encode_ms"] = 1e3 * (time.perf_counter() - t)
            t = time.perf_counter(); edge_b = ms.encode_edges(ms.canny_edges(edge_src)); row["edge_ms"] = 1e3 * (time.perf_counter() - t)
            t = time.perf_counter(); text = cap(rgb); ms._sync(device); row["caption_ms"] = 1e3 * (time.perf_counter() - t)
            cap_b = text.encode("utf-8")
            (out_dir / f"{stem}_seg.webp").write_bytes(seg_b)
            (out_dir / f"{stem}_edge.webp").write_bytes(edge_b)
            (out_dir / f"{stem}_caption.txt").write_bytes(cap_b)
            row.update(seg_b=len(seg_b), edge_b=len(edge_b), caption_b=len(cap_b), caption=text,
                       total_b=len(seg_b) + len(edge_b) + len(cap_b))
            meta_path.write_text(json.dumps(row, indent=1))      # written last: marks the payload complete
            index[f"{cdir.name}/{stem}"] = row
            print(f"[{ci}/{len(dirs)}] {cdir.name}/{stem}: {row['total_b'] / 1024:.1f} KB "
                  f"(seg {row['seg_b']} B, edge {row['edge_b']} B, caption {row['caption_b']} B) "
                  f"{row['seg_infer_ms']:.0f}/{row['edge_ms']:.0f}/{row['caption_ms']:.0f} ms | {text}", flush=True)
        index_path.write_text(json.dumps(index, indent=1))
    print("PAYLOADS_DONE", len(index), "payloads", flush=True)


if __name__ == "__main__":
    main()
