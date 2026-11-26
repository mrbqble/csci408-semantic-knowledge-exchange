#!/usr/bin/env python3
"""Run one network experiment end to end (Windows host; Docker Desktop + the WSL2 kernel with netem).

  python netsim/run_experiment.py --profile 1mbps --mode shared --k 4 --cases 1-10
  python netsim/run_experiment.py --profile 256kbps --k 3 --fail cam3@5 --deadline 25

What it does
  1. scripts/netem_up.ps1 (loads sch_netem/tbf/htb into the WSL kernel, starts Docker if needed)
  2. builds the image csci408-netsim once, writes plan.json + compose.yml for this run
  3. router + ingest + one sender container per camera (cam1..camK) on two bridge networks;
     senders replay the cached payloads of iter2/data/carla_v2_payloads through the shaped link
  4. waits for the ingest container to exit, saves logs, tears everything down
  5. deadline_filter.py: arrival_virtual = Pi 5 compute + measured transfer; on-time tree for coordinator.py

Modes   shared  (default) one shared bottleneck on the router: the profile's rate is the TOTAL for all K cameras
        perlink every camera shapes its own egress: the rate is PER camera (optimistic: more cameras, more bandwidth)
K is the maximum number of cameras per case (cases with fewer cameras send fewer).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import deadline_filter as df  # noqa: E402

DEFAULT_PAYLOADS = REPO / "iter2" / "data" / "carla_v2_payloads"
IMAGE = "csci408-netsim:latest"
PROJECT = "csci408ns"
EDGE_NET, CORE_NET = "172.30.1.0/24", "172.30.2.0/24"
ROUTER_EDGE, ROUTER_CORE, INGEST_IP = "172.30.1.2", "172.30.2.2", "172.30.2.10"


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, **kw)


def parse_cases(text, avail):
    if not text:
        return set(avail)
    out = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def build_plan(payload_dir, k, want):
    cases, cams = [], {}
    dirs = [p for p in payload_dir.iterdir() if p.is_dir() and re.fullmatch(r"case\d+", p.name)]
    nums = {int(p.name[4:]): p for p in dirs}
    wanted = parse_cases(want, nums)
    for n in sorted(nums):
        if n not in wanted:
            continue
        c = sorted((m.name[: -len("_meta.json")] for m in nums[n].glob("cam*_meta.json")), key=lambda s: int(s[3:]))
        c = [x for x in c if int(x[3:]) <= k]
        if c:
            cases.append(nums[n].name)
            cams[nums[n].name] = c
    return {"cases": cases, "cams": cams, "k": k}


def netem_string(p, rate=True, loss=True):
    parts = []
    if p.get("delay_ms"):
        parts.append(f"delay {p['delay_ms']}ms" + (f" {p['jitter_ms']}ms" if p.get("jitter_ms") else ""))
    if loss and p.get("loss_pct"):
        parts.append(f"loss {p['loss_pct']}%")
    if rate and p.get("rate"):
        parts.append(f"rate {p['rate']}")
    return " ".join(parts)


def compose_yaml(run_dir, payload_dir, plan, prof, mode, fail, go_timeout):
    full, delay_only = netem_string(prof), netem_string(prof, rate=False, loss=False)
    y = lambda s: json.dumps(s)          # JSON strings are valid YAML scalars
    cams = sorted({c for v in plan["cams"].values() for c in v}, key=lambda c: int(c[3:]))
    L = ["name: " + PROJECT, "networks:",
         "  edge:", "    ipam:", "      config:", f"        - subnet: {EDGE_NET}",
         "  core:", "    ipam:", "      config:", f"        - subnet: {CORE_NET}",
         "services:",
         "  router:", f"    image: {IMAGE}", "    container_name: ns-router", '    entrypoint: ["/app/router.sh"]',
         "    cap_add: [NET_ADMIN]", "    sysctls:", '      net.ipv4.ip_forward: "1"', "    environment:",
         f"      EDGE_IP: {ROUTER_EDGE}", f"      CORE_IP: {ROUTER_CORE}",
         f"      NETEM_UP: {y(full if mode == 'shared' else '')}", f"      NETEM_DOWN: {y(delay_only)}",
         "    networks:", f"      edge: {{ipv4_address: {ROUTER_EDGE}}}", f"      core: {{ipv4_address: {ROUTER_CORE}}}",
         "  ingest:", f"    image: {IMAGE}", "    container_name: ns-ingest", '    entrypoint: ["/app/node.sh", "ingest.py"]',
         "    cap_add: [NET_ADMIN]", "    depends_on: [router]", "    environment:",
         f"      ROUTE_NET: {EDGE_NET}", f"      ROUTE_GW: {ROUTER_CORE}", "      RUN_DIR: /run_dir",
         f"      GO_TIMEOUT_S: {y(str(go_timeout))}",
         "    volumes:", "      - type: bind", f"        source: {y(run_dir.as_posix())}", "        target: /run_dir",
         "    networks:", f"      core: {{ipv4_address: {INGEST_IP}}}"]
    for i, cam in enumerate(cams):
        L += [f"  {cam}:", f"    image: {IMAGE}", f"    container_name: ns-{cam}",
              '    entrypoint: ["/app/node.sh", "sender.py"]', "    cap_add: [NET_ADMIN]", "    depends_on: [router]",
              "    environment:", f"      CAM: {cam}", f"      INGEST: {INGEST_IP}:50051", "      RUN_DIR: /run_dir",
              "      PAYLOADS: /data/payloads", f"      ROUTE_NET: {CORE_NET}", f"      ROUTE_GW: {ROUTER_EDGE}",
              f"      NETEM_EGRESS: {y(full if mode == 'perlink' else '')}",
              f"      FAIL_AFTER: {y(str(fail.get(cam, -1)))}",
              "    volumes:", "      - type: bind", f"        source: {y(run_dir.as_posix())}", "        target: /run_dir",
              "        read_only: true",
              "      - type: bind", f"        source: {y(payload_dir.as_posix())}", "        target: /data/payloads",
              "        read_only: true",
              "    networks:", f"      edge: {{ipv4_address: 172.30.1.{11 + i}}}"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="1mbps", help="name in profiles.json")
    ap.add_argument("--mode", default="shared", choices=["shared", "perlink"])
    ap.add_argument("--k", type=int, default=4, help="max cameras per case")
    ap.add_argument("--cases", default="", help="e.g. 1-10,25 (default: all)")
    ap.add_argument("--fail", default="", help="node failure, e.g. cam3@5: cam3 goes silent after 5 cases")
    ap.add_argument("--deadline", type=float, default=df.DEFAULT_DEADLINE_S, help="virtual seconds after capture (placeholder default)")
    ap.add_argument("--go-timeout", type=float, default=20, help="real seconds the barrier waits for a silent camera")
    ap.add_argument("--payloads", type=Path, default=DEFAULT_PAYLOADS)
    ap.add_argument("--tag", default="")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=180)
    a = ap.parse_args()

    profiles = json.loads((HERE / "profiles.json").read_text())
    if a.profile not in profiles or a.profile.startswith("_"):
        sys.exit(f"unknown profile {a.profile!r}; choices: {[p for p in profiles if not p.startswith('_')]}")
    prof = profiles[a.profile]
    fail = {}
    if a.fail:
        m = re.fullmatch(r"(cam\d+)@(\d+)", a.fail)
        if not m:
            sys.exit("--fail must look like cam3@5")
        fail[m.group(1)] = int(m.group(2))

    plan = build_plan(a.payloads, a.k, a.cases)
    if not plan["cases"]:
        sys.exit("no cases selected")
    n_pay = sum(len(v) for v in plan["cams"].values())
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}_{a.profile}_{a.mode}_K{a.k}" + ("_fail-" + a.fail.replace("@", "at") if a.fail else "") + (f"_{a.tag}" if a.tag else "")
    run_dir = HERE / "runs" / name
    (run_dir / "received").mkdir(parents=True)
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=1))
    config = {"profile": a.profile, "profile_values": prof, "mode": a.mode, "k": a.k, "cases": a.cases or "all",
              "fail": a.fail, "deadline_s": a.deadline, "go_timeout_s": a.go_timeout,
              "netem_shared_uplink": netem_string(prof) if a.mode == "shared" else "",
              "netem_per_camera": netem_string(prof) if a.mode == "perlink" else "",
              "netem_downlink": netem_string(prof, rate=False, loss=False)}
    (run_dir / "run_config.json").write_text(json.dumps(config, indent=1))
    compose_path = run_dir / "compose.yml"
    compose_path.write_text(compose_yaml(run_dir, a.payloads, plan, prof, a.mode, fail, a.go_timeout))
    print(f"run: {run_dir}\n  {len(plan['cases'])} cases, {n_pay} payloads, profile {a.profile} ({netem_string(prof) or 'no shaping'}), mode {a.mode}, K<={a.k}", flush=True)

    r = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "scripts" / "netem_up.ps1")])
    if r.returncode:
        sys.exit("netem_up.ps1 failed: fix the environment first")
    if a.rebuild or run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
        print("building image ...", flush=True)
        run(["docker", "build", "-t", IMAGE, str(HERE)], check=True)

    base = ["docker", "compose", "-f", str(compose_path), "-p", PROJECT]
    run(base + ["down", "--remove-orphans", "-t", "1"], capture_output=True)
    t0 = time.time()
    run(base + ["up", "-d"], check=True)
    timed_out = False
    try:
        run(["docker", "wait", "ns-ingest"], capture_output=True, timeout=a.max_minutes * 60)
    except subprocess.TimeoutExpired:
        timed_out = True
        print("TIMED OUT waiting for the ingest container")
    wall = time.time() - t0
    log = run(base + ["logs", "--no-color", "--timestamps"], capture_output=True, encoding="utf-8", errors="replace")
    (run_dir / "run.log").write_text(log.stdout or "", encoding="utf-8")
    run(base + ["down", "--remove-orphans", "-t", "1"], capture_output=True)
    print(f"containers finished in {wall:.0f}s wall clock; logs in run.log", flush=True)

    if not (run_dir / "arrival_log.jsonl").exists():
        sys.exit("no arrival_log.jsonl: nothing was received, see run.log")
    summary, rows = df.process(run_dir, a.deadline, df.PI5_COMPUTE_S)
    summary["wall_clock_s"] = round(wall, 1)
    summary["timed_out"] = timed_out
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()