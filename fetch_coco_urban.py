#!/usr/bin/env python3
"""Download the 25 COCO val2017 street scenes used by the September probe.

The file list is read from probe_urban.json, whose images were chosen by
pick_urban.py from the COCO instance annotations (at least three vehicles, or
vehicles plus traffic furniture). COCO images are public; no account is needed.
"""
import argparse
import json
import urllib.request
from pathlib import Path

BASE = "http://images.cocodataset.org/val2017/"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", default=Path("probe_urban.json"), type=Path)
    ap.add_argument("--out", default=Path("data/coco_urban"), type=Path)
    args = ap.parse_args()

    files = [row["file"] for row in json.loads(args.list.read_text())["rows"]]
    args.out.mkdir(parents=True, exist_ok=True)
    for name in files:
        dst = args.out / name
        if dst.exists() and dst.stat().st_size > 0:
            continue
        for attempt in range(1, 6):          # the COCO server can stall a connection
            try:
                with urllib.request.urlopen(BASE + name, timeout=20) as r:
                    data = r.read()
                tmp = dst.with_suffix(".part")
                tmp.write_bytes(data)
                tmp.rename(dst)              # never leave a truncated image behind
                print("fetched", name, flush=True)
                break
            except OSError as e:
                print(f"retry {attempt} for {name}: {e}", flush=True)
        else:
            raise SystemExit(f"could not download {name}")
    print(f"{len(files)} images in {args.out}")


if __name__ == "__main__":
    main()
