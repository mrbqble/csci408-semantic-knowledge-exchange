#!/usr/bin/env python3
"""Sender: one emulated camera node. Replays the cached Iteration 2 payloads of its camera.

For every case of plan.json in which this camera takes part: Go(case) (barrier), then Send(payload).
Environment: CAM (e.g. cam3), INGEST (host:port), RUN_DIR (plan.json), PAYLOADS (payload tree),
FAIL_AFTER (stop silently after this many cases, -1 = never: Test Case 3 node failure).
The node's own compute time is NOT slept: it is added analytically afterwards (deadline_filter.py).
"""
import json
import os
import sys
import time
from pathlib import Path

import grpc
import payload_pb2 as pb
import payload_pb2_grpc as pbg

CAM = os.environ["CAM"]
INGEST = os.environ["INGEST"]
RUN = Path(os.environ.get("RUN_DIR", "/run_dir"))
PAY = Path(os.environ.get("PAYLOADS", "/data/payloads"))
FAIL_AFTER = int(os.environ.get("FAIL_AFTER", "-1"))
PLAN = json.loads((RUN / "plan.json").read_text())


def say(msg):
    print(f"[{CAM} {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def park():
    while True:                       # never exit: compose is waiting on the ingest container only
        time.sleep(3600)


def connect():
    ch = grpc.insecure_channel(INGEST, options=[("grpc.max_send_message_length", 64 << 20),
                                                ("grpc.max_receive_message_length", 64 << 20)])
    for _ in range(60):
        try:
            grpc.channel_ready_future(ch).result(timeout=5)
            return ch
        except grpc.FutureTimeoutError:
            say("waiting for ingest ...")
    sys.exit("ingest unreachable")


def main():
    stub = pbg.IngestStub(connect())
    sent = 0
    for case in PLAN["cases"]:
        if CAM not in PLAN["cams"][case]:
            continue
        if 0 <= FAIL_AFTER <= sent:
            say(f"simulated node failure after {sent} cases: going silent")
            park()
        stub.Go(pb.GoRequest(cam=CAM, case_id=case), timeout=900)
        d = PAY / case
        meta_text = (d / f"{CAM}_meta.json").read_text()
        meta = json.loads(meta_text)
        msg = pb.Payload(case_id=case, cam=CAM, timestamp=int(meta.get("timestamp") or 0),
                         seg_webp=(d / f"{CAM}_seg.webp").read_bytes(),
                         edge_webp=(d / f"{CAM}_edge.webp").read_bytes(),
                         caption=(d / f"{CAM}_caption.txt").read_text(encoding="utf-8"),
                         meta_json=meta_text)
        t0 = time.perf_counter()
        msg.t_send_ns = time.time_ns()
        stub.Send(msg, timeout=900)
        sent += 1
        say(f"{case}: {msg.ByteSize() / 1024:.1f} KB acked after {time.perf_counter() - t0:.2f}s")
    stub.Done(pb.DoneRequest(cam=CAM), timeout=60)
    say(f"all {sent} cases sent")
    park()


if __name__ == "__main__":
    main()