#!/usr/bin/env python3
"""Parallel segmented downloader for Cityscapes packages.

Why: the Cityscapes host serves ~0.45 MB/s on a single stream while the local
link does 8.5 MB/s. If that cap is per-connection, N range requests in parallel
give roughly N times the throughput.

Credentials: handled entirely by cityscapesscripts' own login(), which reads its
own stored config. This script never sees, reads, or passes a password.

Usage:
    python par_download.py --bench            # 60s throughput test, writes nothing
    python par_download.py --run -n 8         # full resume-aware download
"""
import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from cityscapesscripts.download.downloader import login

BASE = "https://www.cityscapes-dataset.com/file-handling/?packageID={}"
PACKAGES = {"leftImg8bit_trainvaltest.zip": 3, "gtFine_trainvaltest.zip": 1}

_lock = threading.Lock()
_got = {"bytes": 0}


def bump(n):
    with _lock:
        _got["bytes"] += n


def total_size(session, url):
    """Content-Length via a 1-byte range probe, and whether ranges are honoured."""
    r = session.get(url, allow_redirects=False, stream=True,
                    headers={"Range": "bytes=0-0"})
    cr = r.headers.get("Content-Range")
    r.close()
    if cr and "/" in cr:
        return int(cr.split("/")[-1]), True
    r = session.get(url, allow_redirects=False, stream=True)
    n = int(r.headers.get("Content-Length", 0))
    r.close()
    return n, False


def fetch_range(session, url, start, end, fh=None, stop_at=None):
    """Download [start, end] inclusive. Writes at offset if fh given."""
    hdr = {"Range": f"bytes={start}-{end}"}
    with session.get(url, allow_redirects=False, stream=True, headers=hdr) as r:
        pos = start
        for chunk in r.iter_content(chunk_size=1 << 18):   # 256 KB, not 1 KB
            if not chunk:
                continue
            if fh is not None:
                with _lock:
                    fh.seek(pos)
                    fh.write(chunk)
            pos += len(chunk)
            bump(len(chunk))
            if stop_at and time.time() > stop_at:
                return


def bench(session, url, size, conns, seconds=45):
    """Read distinct far-apart regions in parallel; measure aggregate rate."""
    print(f"  {conns} connection(s) for {seconds}s...", end="", flush=True)
    _got["bytes"] = 0
    span = size // (conns + 1)
    stop = time.time() + seconds
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=conns) as ex:
        futs = [ex.submit(fetch_range, session, url,
                          span * (i + 1), span * (i + 1) + 200 * 1024 * 1024,
                          None, stop)
                for i in range(conns)]
        for f in futs:
            try:
                f.result()
            except Exception as e:
                print(f" [conn error: {type(e).__name__}]", end="")
    dt = time.time() - t0
    rate = _got["bytes"] / dt / 1e6
    print(f"  {rate:6.2f} MB/s")
    return rate


def run(session, url, size, path, conns):
    have = os.path.getsize(path) if os.path.exists(path) else 0
    if have >= size:
        print("already complete")
        return
    print(f"resuming from {have/1e6:.1f} MB of {size/1e6:.1f} MB "
          f"using {conns} connections")

    with open(path, "r+b" if have else "wb") as fh:
        fh.truncate(size)
        remaining = size - have
        seg = remaining // conns
        bounds = [(have + i * seg,
                   have + (i + 1) * seg - 1 if i < conns - 1 else size - 1)
                  for i in range(conns)]

        _got["bytes"] = 0
        t0 = time.time()
        done = threading.Event()

        def report():
            while not done.wait(15):
                el = time.time() - t0
                got = _got["bytes"]
                rate = got / el / 1e6
                pct = 100 * (have + got) / size
                eta = (remaining - got) / (rate * 1e6) / 60 if rate > 0 else 0
                print(f"  {pct:5.1f}%  {rate:5.2f} MB/s  ETA {eta:5.1f} min",
                      flush=True)

        threading.Thread(target=report, daemon=True).start()
        with ThreadPoolExecutor(max_workers=conns) as ex:
            list(ex.map(lambda b: fetch_range(session, url, b[0], b[1], fh),
                        bounds))
        done.set()

    final = os.path.getsize(path)
    print(f"done: {final/1e6:.1f} MB in {(time.time()-t0)/60:.1f} min "
          f"({'OK' if final == size else 'SIZE MISMATCH'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="leftImg8bit_trainvaltest.zip")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("-n", "--connections", type=int, default=8)
    args = ap.parse_args()

    pid = PACKAGES.get(args.package)
    if pid is None:
        sys.exit(f"unknown package {args.package}")
    url = BASE.format(pid)

    print("logging in (credentials handled by cityscapesscripts)...")
    session = login()

    size, ranged = total_size(session, url)
    print(f"remote size: {size/1e6:.1f} MB   range requests honoured: {ranged}")
    if not ranged:
        sys.exit("server did not honour Range - parallel download not possible")

    if args.bench:
        print("\nthroughput test (downloads nothing to disk):")
        results = {}
        for c in (1, 4, 8):
            results[c] = bench(session, url, size, c)
            time.sleep(2)
        base = results[1]
        print("\nspeedup vs single connection:")
        for c, r in results.items():
            print(f"  {c} conn: {r/base:4.1f}x")
        best = max(results, key=results.get)
        rem = (size - os.path.getsize(args.package)) if os.path.exists(args.package) else size
        print(f"\nbest = {best} connections at {results[best]:.2f} MB/s")
        print(f"projected time for remaining {rem/1e6:.0f} MB: "
              f"{rem/results[best]/1e6/60:.0f} min")
        return

    if args.run:
        run(session, url, size, args.package, args.connections)
    else:
        print("nothing to do - pass --bench or --run")


if __name__ == "__main__":
    main()
