#!/usr/bin/env python3
"""Ingest: the coordinator-side receiver of the emulated network.

* Go(case)   barrier. Every live camera of a case is released together once all of them have asked,
             so the K payloads of one moment hit the link at the same instant. A camera that does
             not show up within GO_TIMEOUT_S is declared dead and no longer waited for (Test Case 3).
* Send(...)  receives one payload, stamps its arrival (wall clock, same VM clock as the senders),
             writes it in the Iteration 2 payload layout under received/ and appends one line to
             arrival_log.jsonl with the measured transfer time.
* Done(cam)  the sender has no more cases. The process exits when every live camera is done.

Environment: RUN_DIR (default /run_dir; holds plan.json, receives received/ and arrival_log.jsonl),
GO_TIMEOUT_S, FIRST_GO_TIMEOUT_S, IDLE_EXIT_S, PORT.
"""
import json
import os
import threading
import time
from collections import defaultdict
from concurrent import futures
from pathlib import Path

import grpc
import payload_pb2 as pb
import payload_pb2_grpc as pbg

RUN = Path(os.environ.get("RUN_DIR", "/run_dir"))
OUT = RUN / "received"
GO_TIMEOUT = float(os.environ.get("GO_TIMEOUT_S", "20"))
FIRST_GO_TIMEOUT = float(os.environ.get("FIRST_GO_TIMEOUT_S", "90"))
IDLE_EXIT = float(os.environ.get("IDLE_EXIT_S", "60"))
PORT = int(os.environ.get("PORT", "50051"))

PLAN = json.loads((RUN / "plan.json").read_text())
CAMS = PLAN["cams"]
ALL_CAMS = sorted({c for v in CAMS.values() for c in v}, key=lambda c: int(c[3:]))


def say(msg):
    print(f"[ingest {time.strftime('%H:%M:%S')}] {msg}", flush=True)


class Ingest(pbg.IngestServicer):
    def __init__(self):
        self.cv = threading.Condition()
        self.arrived = defaultdict(set)
        self.released = set()
        self.dead = set()
        self.done = set()
        self.seq = 0
        self.last_activity = time.monotonic()
        self.log_lock = threading.Lock()
        self.log = open(RUN / "arrival_log.jsonl", "a", buffering=1, encoding="utf-8")
        self.finished = threading.Event()

    def touch(self):
        self.last_activity = time.monotonic()

    # ---- barrier -------------------------------------------------------------------------
    def Go(self, req, ctx):
        case, cam = req.case_id, req.cam
        with self.cv:
            timeout = GO_TIMEOUT if self.released else FIRST_GO_TIMEOUT
            deadline = time.monotonic() + timeout
            self.arrived[case].add(cam)
            self.touch()
            while True:
                expected = [c for c in CAMS.get(case, []) if c not in self.dead]
                if case in self.released or all(c in self.arrived[case] for c in expected):
                    break
                left = deadline - time.monotonic()
                if left <= 0:
                    for c in expected:
                        if c not in self.arrived[case]:
                            self.dead.add(c)
                            say(f"{c} did not reach the barrier of {case} within {timeout:.0f}s: declared dead")
                    break
                self.cv.wait(left)
            if case not in self.released:
                say(f"{case}: released {sorted(self.arrived[case])}")
            self.released.add(case)
            self.cv.notify_all()
            self.touch()
        self._maybe_finish()
        return pb.GoReply(proceed=True)

    # ---- payload -------------------------------------------------------------------------
    def Send(self, req, ctx):
        t_recv = time.time_ns()                     # the last byte has arrived: gRPC delivers whole messages
        wire = req.ByteSize()
        cam = req.cam
        cdir = OUT / req.case_id
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / f"{cam}_seg.webp").write_bytes(req.seg_webp)
        (cdir / f"{cam}_edge.webp").write_bytes(req.edge_webp)
        (cdir / f"{cam}_caption.txt").write_bytes(req.caption.encode("utf-8"))
        transfer_s = (t_recv - req.t_send_ns) / 1e9
        meta = json.loads(req.meta_json)
        meta["net"] = {"t_send_ns": req.t_send_ns, "t_recv_ns": t_recv, "transfer_s": transfer_s, "wire_bytes": wire}
        (cdir / f"{cam}_meta.json").write_text(json.dumps(meta, indent=1))   # written last: completes the payload
        with self.log_lock:
            self.seq += 1
            self.log.write(json.dumps({
                "seq": self.seq, "case": req.case_id, "cam": cam, "timestamp": req.timestamp,
                "wire_bytes": wire, "seg_b": len(req.seg_webp), "edge_b": len(req.edge_webp),
                "caption_b": len(req.caption.encode("utf-8")),
                "t_send_ns": req.t_send_ns, "t_recv_ns": t_recv, "transfer_s": transfer_s}) + "\n")
        self.touch()
        say(f"{req.case_id}/{cam}: {wire / 1024:.1f} KB in {transfer_s:.2f}s ({wire * 8 / max(transfer_s, 1e-9) / 1e3:.0f} kbit/s)")
        return pb.Ack(ok=True)

    def Done(self, req, ctx):
        with self.cv:
            self.done.add(req.cam)
            self.touch()
            self.cv.notify_all()
        say(f"{req.cam} done")
        self._maybe_finish()
        return pb.Ack(ok=True)

    def _maybe_finish(self):
        with self.cv:
            live = [c for c in ALL_CAMS if c not in self.dead]
            if all(c in self.done for c in live):
                self.finished.set()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    svc = Ingest()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=64),
                         options=[("grpc.max_receive_message_length", 64 << 20),
                                  ("grpc.max_send_message_length", 64 << 20)])
    pbg.add_IngestServicer_to_server(svc, server)
    server.add_insecure_port(f"0.0.0.0:{PORT}")
    server.start()
    say(f"listening on :{PORT}; {len(PLAN['cases'])} cases, cameras {ALL_CAMS}")
    while not svc.finished.is_set():
        time.sleep(0.5)
        if svc.done and time.monotonic() - svc.last_activity > IDLE_EXIT:
            say(f"idle for {IDLE_EXIT:.0f}s after some cameras finished: exiting")
            break
    time.sleep(1.0)                                  # let the last acks leave
    server.stop(grace=5).wait()
    svc.log.close()
    (RUN / "ingest_summary.json").write_text(json.dumps(
        {"payloads": svc.seq, "done": sorted(svc.done), "dead": sorted(svc.dead),
         "never_finished": sorted(set(ALL_CAMS) - svc.done - svc.dead)}, indent=1))
    say(f"finished: {svc.seq} payloads, dead={sorted(svc.dead)}")


if __name__ == "__main__":
    main()