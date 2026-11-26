#!/usr/bin/env python3
"""Create GitHub milestones, issues, and a Projects v2 roadmap for CSCI 408."""
import json
import subprocess
import sys

REPO = "mrbqble/csci408-semantic-knowledge-exchange"
OWNER = "mrbqble"


def gh(*args, parse=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! {' '.join(args[:3])}: {r.stderr.strip()[:160]}")
        return None
    out = r.stdout.strip()
    if not parse or not out:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


MILESTONES = [
    ("Kickoff Document", "2026-09-20", "Week 5 deliverable"),
    ("Requirements & Design", "2026-10-18", "Week 9 deliverable"),
    ("Literature Review (2-page IEEE)", "2026-10-31", "Adviser deliverable"),
    ("Final Report & Presentation", "2026-11-22", "Week 14 deliverable"),
]

# (title, body, milestone index, start, end, assignee or None)
TASKS = [
    ("Kickoff: Motivation and Summary (20%)",
     "Problem, inputs/outputs, use cases, high-level solution. Frame against "
     "MMSD: multi-node, heterogeneous components, no reconstruction.",
     0, "2026-09-18", "2026-09-20", "mrbqble"),
    ("Kickoff: System Description (20%)",
     "Components, interactions, architecture diagram, two-semester scope. "
     "BLOCKED on the coordinator aggregation decision.",
     0, "2026-09-18", "2026-09-20", None),
    ("Kickoff: Hardware & Software Requirements (10%)",
     "Simulation stack. Needs the network simulator choice from the adviser.",
     0, "2026-09-19", "2026-09-20", None),
    ("Kickoff: Evaluation Criteria and Plan (10%)",
     "Six metrics from the proposal. Measured baselines already in "
     "probe_cityscapes.json.", 0, "2026-09-19", "2026-09-20", "mrbqble"),
    ("Kickoff: Risks and Contingency (10%)",
     "Modelled-compute term dominating on WiFi/BLE; no citable energy model; "
     "edge maps at ~90% of payload.", 0, "2026-09-19", "2026-09-20", None),
    ("Kickoff: Deliverables + Project Management (20%)",
     "Deliverables list, Gantt chart from this board, per-member task "
     "assignment.", 0, "2026-09-19", "2026-09-20", "mrbqble"),
    ("Kickoff: References (10%)",
     "8-12 understood references. Seed paper plus cluster A/B heads.",
     0, "2026-09-18", "2026-09-20", None),
]

TASKS += [
    ("Literature: Cluster A - semantic comms foundations (5 papers)",
     "DeepJSCC, DeepSC, goal-oriented comms, Luo et al. overview.",
     2, "2026-09-21", "2026-10-15", None),
    ("Literature: Cluster B - classification-oriented semantic comms (6)",
     "Kang TCOM'22, Kang JSAC'23, SQ-GAN, Lee Access'19. Record how many are "
     "single-node - that is the gap statement.", 2, "2026-09-21", "2026-10-15", None),
    ("Literature: Cluster C - distributed/multi-device inference (6)",
     "Palena et al. Computer Networks 2024 first - nearest neighbour to our "
     "setup. Heaviest cluster.", 2, "2026-09-21", "2026-10-15", None),
    ("Literature: Cluster D - feature compression & information bottleneck (5)",
     "Shao JSAC'22, Chang IJCV'23, generative visual compression review.",
     2, "2026-09-21", "2026-10-15", None),
    ("Literature: Cluster E - on-device cost figures (4)",
     "Source of latency/memory/energy numbers to parameterize the simulator. "
     "Kargar & Zorbas 2025 included.", 2, "2026-09-21", "2026-10-15", None),
    ("Literature: Cluster F - simulators, energy models, scene generation (4)",
     "BIGGEST GAP: no citable energy model for the radio layer yet.",
     2, "2026-09-21", "2026-10-15", None),
    ("Write 2-page IEEE literature review",
     "Comparison-first, not paper-by-paper. Build the comparison matrix first, "
     "then write from it.", 2, "2026-10-16", "2026-10-31", "mrbqble"),

    ("Decide coordinator aggregation architecture",
     "Late fusion of per-component classifiers vs single multi-modal encoder. "
     "Largest open design question; blocks System Description.",
     1, "2026-09-21", "2026-09-30", None),
    ("Select and set up network simulator",
     "ns-3 vs OMNeT++/INET. Adviser preference decides.",
     1, "2026-09-21", "2026-10-05", None),
    ("Select citable energy model for the radio layer",
     "Needed because energy is modelled, not measured. Check Zorbas's own LoRa "
     "work.", 1, "2026-09-21", "2026-10-05", None),
    ("Switch payload encoding from PNG to WebP",
     "Seed paper gets 18.41 KB for the edge map with WebP; our 1-bit PNG takes "
     "31.0 KB. ~40% free saving.", 1, "2026-09-21", "2026-09-28", None),
    ("Resolve compression baseline: PNG original vs JPEG",
     "Seed paper reports 111x against a 2.28 MB lossless PNG. We measured "
     "against a 261 KB JPEG. Report both, state which.",
     1, "2026-09-21", "2026-09-28", "mrbqble"),
    ("Boundary smoothing on upsampled segmentation maps",
     "Our upsampled prediction is 3530 B vs 1249 B for hand-annotated ground "
     "truth - ragged bilinear edges compress badly.",
     1, "2026-09-28", "2026-10-12", None),
    ("Requirements & Design document",
     "Week 9 deliverable.", 1, "2026-10-05", "2026-10-18", None),

    ("Implement multi-node semantic decomposition",
     "Each simulated node extracts one different component.",
     3, "2026-10-19", "2026-11-09", None),
    ("Implement coordinator aggregation and classifier",
     "", 3, "2026-10-19", "2026-11-09", None),
    ("Implement centralized baseline classifier",
     "The comparison arm named in the proposal.", 3, "2026-10-19", "2026-11-02", None),
    ("Evaluation harness for all six metrics",
     "Accuracy, transmitted size, comms latency, per-device time, end-to-end "
     "time, energy.", 3, "2026-11-02", "2026-11-16", None),
    ("Final report and presentation",
     "Week 14.", 3, "2026-11-09", "2026-11-22", None),
]


def main():
    print("creating milestones...")
    ms_numbers = []
    existing = gh("api", f"repos/{REPO}/milestones") or []
    by_title = {m["title"]: m["number"] for m in existing}
    for title, due, desc in MILESTONES:
        if title in by_title:
            ms_numbers.append(by_title[title])
            print(f"  = {title}")
            continue
        r = gh("api", f"repos/{REPO}/milestones", "-f", f"title={title}",
               "-f", f"description={desc}", "-f", f"due_on={due}T23:59:59Z")
        ms_numbers.append(r["number"] if r else None)
        print(f"  + {title} (due {due})")

    print("\ncreating project...")
    proj = gh("project", "create", "--owner", OWNER,
              "--title", "CSCI 408 - Semantic Knowledge Exchange", "--format", "json")
    if not proj:
        sys.exit("project creation failed")
    pnum, pid = proj["number"], proj["id"]
    print(f"  project #{pnum}  {proj['url']}")

    print("creating date fields...")
    fields = {}
    for fname in ("Start", "End"):
        f = gh("project", "field-create", str(pnum), "--owner", OWNER,
               "--name", fname, "--data-type", "DATE", "--format", "json")
        if f:
            fields[fname] = f["id"]
            print(f"  + {fname}")

    print("\ncreating issues and adding to project...")
    for title, body, mi, start, end, assignee in TASKS:
        args = ["issue", "create", "--repo", REPO, "--title", title,
                "--body", body or title]
        if ms_numbers[mi]:
            args += ["--milestone", MILESTONES[mi][0]]
        if assignee:
            args += ["--assignee", assignee]
        url = gh(*args, parse=False)
        if not url:
            continue
        url = url.strip().splitlines()[-1]
        item = gh("project", "item-add", str(pnum), "--owner", OWNER,
                  "--url", url, "--format", "json")
        if item and fields:
            for fname, val in (("Start", start), ("End", end)):
                gh("project", "item-edit", "--id", item["id"],
                   "--project-id", pid, "--field-id", fields[fname],
                   "--date", val, parse=False)
        print(f"  + {title[:58]}")

    print(f"\ndone -> {proj['url']}")
    print("Open it, switch the view to Roadmap, and set the date fields to "
          "Start/End to get the Gantt.")


if __name__ == "__main__":
    main()
