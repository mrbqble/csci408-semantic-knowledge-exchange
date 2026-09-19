#!/usr/bin/env python3
"""Verify a downloaded Cityscapes package against the published md5.

Matters here because par_download.py writes with 8 concurrent writers at
different file offsets. A gap in the middle would still produce a
correct-looking file size, so a checksum is the only real confirmation.
"""
import hashlib
import re
import sys
import time
from pathlib import Path

from cityscapesscripts.download.downloader import login

PACKAGES = {"leftImg8bit_trainvaltest.zip": 3, "gtFine_trainvaltest.zip": 1}
name = sys.argv[1] if len(sys.argv) > 1 else "leftImg8bit_trainvaltest.zip"
path = Path(name)

session = login()
r = session.get(f"https://www.cityscapes-dataset.com/md5-sum/?packageID={PACKAGES[name]}",
                allow_redirects=False)
m = re.search(r"\b([a-f0-9]{32})\b", r.text)
if not m:
    sys.exit(f"could not parse md5 from response: {r.text[:200]!r}")
expected = m.group(1)
print(f"expected md5: {expected}")

t0 = time.time()
h = hashlib.md5()
size = path.stat().st_size
read = 0
with open(path, "rb") as f:
    while chunk := f.read(1 << 24):          # 16 MB
        h.update(chunk)
        read += len(chunk)
        if read % (1 << 30) < (1 << 24):
            print(f"  hashed {read/1e9:.1f} / {size/1e9:.1f} GB", flush=True)
actual = h.hexdigest()
print(f"actual   md5: {actual}   ({time.time()-t0:.0f}s)")
print("MATCH - file is intact" if actual == expected else "MISMATCH - re-download")
