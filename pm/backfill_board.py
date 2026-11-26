"""Backfill the GitHub milestones, issues and Projects v2 board (#2) from the work Group 22 actually did in fall 2026."""
import json, pathlib, subprocess, time
from datetime import date

R, OWNER = "mrbqble/csci408-semantic-knowledge-exchange", "mrbqble"
PEOPLE = {"Bibol": "mrbqble", "Yernur": "Y3rnur", "Zhengis": "Zhengis04", "Temirshin": "CheffCorleOne"}
FULL = {"Bibol": "Bibol Assetbek", "Yernur": "Yernur Kenzhaly", "Zhengis": "Zhengis Kosher", "Temirshin": "Temirshin Kantemirov"}
ALL = ["Bibol", "Yernur", "Zhengis", "Temirshin"]
NOTE = ("\n\n---\n_Backfilled on 26 Nov 2026 from the team's records (git history, Telegram, Drive). "
        "Start and End on the project board are the dates the work was done; the issue itself was created later._")

def gh(args, data=None):
    r = subprocess.run(["gh", *args], input=None if data is None else json.dumps(data), capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else None

def rest(method, path, data=None):
    return gh(["api", path, "-X", method] + (["--input", "-"] if data is not None else []), data)

def gql(q, **v):
    a = ["api", "graphql", "-f", f"query={q}"]
    for k, val in v.items():
        a += ["-f", f"{k}={val}"]
    return gh(a)["data"]

def fmt(d):
    y, m, dd = map(int, d.split("-")); return f"{dd} {date(y, m, dd).strftime('%b %Y')}"

T = []
def task(title, ms, labels, who, start, end, status, what, where=""):
    T.append(dict(title=title, ms=ms, labels=labels, who=ALL if who == "all" else who, start=start, end=end, status=status, what=what, where=where))

D = "Done"
task("Choose the topic and register the team", "setup", ["deliverable"], ["Yernur", "Bibol"], "2026-08-19", "2026-09-06", D,
     "Reviewed the faculty proposals and chose Prof. Zorbas's semantic knowledge exchange topic (proposed in the team by Yernur on 28 Aug). Entered the team, topic, project type (R&D) and complexity (Highest) in the course registration sheet (Bibol).")
task("Contact the adviser and book the biweekly meeting slot", "setup", ["coordination"], ["Yernur"], "2026-09-01", "2026-09-03", D,
     "Agreed the biweekly meeting slot with Prof. Zorbas by email.")
task("Feasibility probe: payload size and latency per component", "setup", ["experiment"], ["Bibol"], "2026-09-10", "2026-09-20", D,
     "Measured segmentation, edge-map and caption payloads and their compute time on COCO and Cityscapes against a JPEG baseline, and set up Cityscapes access.",
     "initial commit `f170c0f` (`semantic_probe.py`, `probe_*.json`)")
task("Set up the GitHub repository, Projects board and team Drive", "setup", ["coordination"], ["Bibol"], "2026-09-18", "2026-09-20", D,
     "Created the repository and this board, invited the team, and set up the shared Google Drive folders.")
task("Write the Kickoff document", "setup", ["deliverable"], "all", "2026-09-14", "2026-09-20", D,
     "Each member wrote two of the eight sections; Bibol assembled and submitted the document. Graded 95%.", "Drive: Kickoff Document - Group 22")
task("Collect the literature (29 papers) and set up the review tracker", "lit", ["literature"], ["Bibol"], "2026-09-10", "2026-10-09", D,
     "Collected the papers recommended by the adviser and found by the team, with a review tracker and a tracking sheet.", "Drive: Literature Review / Papers for Review")
task("Group the papers into thematic clusters", "lit", ["literature"], ["Yernur", "Zhengis"], "2026-10-07", "2026-10-07", D,
     "Grouped the collected papers into six thematic clusters for the survey.", "Drive: Literature survey (6 clusters)")
task("Write the comparative literature survey and the 2-page IEEE review", "lit", ["literature", "deliverable"], ["Bibol", "Yernur"], "2026-10-09", "2026-11-03", D,
     "Bibol drafted the survey and the 2-page review (15 Oct); Yernur rewrote the survey and corrected the references (3 Nov). Shown to the adviser on 9 Nov.",
     "Drive: Literature Survey — Group 22, group22-lit-review-preview.pdf")
task("Write the technical paper reviews", "lit", ["literature"], "all", "2026-10-15", "2026-11-09", D,
     "One review per paper with the course template, written by all four members.", "Drive: Literature Review / Technical Paper Reviews")
task("Reproduce the MMSD sender on Cityscapes; encoding and Canny ablations", "iter1", ["implementation", "experiment"], ["Bibol"], "2026-09-28", "2026-10-09", D,
     "Sender on all 500 Cityscapes validation images, WebP/PNG encoding ablation, Canny sweep and CPU timing.", "PRs #27, #28")
task("Run the authors' configuration and a receiver smoke test", "iter1", ["implementation"], ["Bibol"], "2026-10-09", "2026-10-12", D,
     "Matched the sender and receiver to the authors' code (shared by D. Assylbek) and ran the single-camera receiver on our GPU.", "PR #29")
task("Test the segmentation palette (Cityscapes vs ADE20K) on 100 images", "iter1", ["experiment"], ["Bibol"], "2026-10-10", "2026-10-12", D,
     "Compared the two colour palettes for the segmentation ControlNet, first on 5 images and then on 100.", "PRs #30, #31")
task("Fix the segmenter input size (512×1024 operating point)", "iter1", ["experiment"], ["Bibol"], "2026-10-12", "2026-10-12", D,
     "Found that the library silently resized the segmenter input to 384×384, measured payload and time per input size, and fixed 512×1024 as the project setting.", "PRs #32, #33")
task("Research the coordinator fusion architecture", "iter1", ["literature"], ["Bibol"], "2026-10-05", "2026-10-12", D,
     "Decision document comparing fusion options for the coordinator, shared with the team on 12 Oct.")
task("Specify the dataset scenes", "data", ["dataset"], ["Yernur", "Temirshin"], "2026-10-15", "2026-10-20", D,
     "Decided which scenes, angles, distances and image formats to record and simulate; checked with the adviser on 20 Oct.")
task("Set up CARLA and generate the first multi-camera dataset (v1)", "data", ["dataset"], ["Zhengis", "Yernur", "Bibol"], "2026-10-15", "2026-10-17", D,
     "CARLA 0.9.16 on the OMEN and the first case generator: 30 cases with 1–6 synchronised cameras per junction.", "Drive: Materials/Datasets/Simulated")
task("Record real-world videos, batch 1 (three phones)", "data", ["dataset"], ["Zhengis", "Yernur", "Bibol"], "2026-10-22", "2026-10-22", D,
     "Nine videos of the same road scenes filmed at the same time from three phones.", "Drive: Materials/Datasets/Real-world/Video")
task("Extract and synchronise the real-world frames (V1)", "data", ["dataset"], ["Bibol"], "2026-10-22", "2026-10-25", D,
     "7,883 frames, audio synchronisation of the three phones, 366 triplets and 729 cases with one to three cameras.", "Drive: Materials/Datasets/Real-world/V1")
task("Generate CARLA v2 and v3 with per-object ground truth", "data", ["dataset"], ["Zhengis", "Yernur", "Bibol"], "2026-10-22", "2026-10-25", D,
     "112 cases each with three to six cameras; v3 adds every visible object's instance ID, box and world position.", "`tools/carla_multicam_kit/`; Drive: Materials/Datasets/Simulated")
task("Record real-world videos, batch 2 (parking scenes)", "data", ["dataset"], ["Zhengis", "Bibol", "Yernur"], "2026-11-07", "2026-11-07", D,
     "Fourteen more videos of parking and roadside scenes, where cars stand close together.", "Drive: Materials/Datasets/Real-world/Video")
task("Extract the real-world batch 2 (V2)", "data", ["dataset"], ["Bibol"], "2026-11-07", "2026-11-07", D,
     "Frames and synchronised cases from the second batch.", "Drive: Materials/Datasets/Real-world/V2")
task("Generate CARLA v4 and the training crops", "data", ["dataset"], ["Zhengis", "Yernur", "Bibol"], "2026-11-08", "2026-11-08", D,
     "224 new CARLA cases; with v2 and 305 real-world cases they give 8,620 training and 1,088 validation crops for spring fine-tuning.", "Drive: Materials/Datasets/Simulated/carla_dataset_v4_train")
task("Organise the datasets and outputs on the team Drive", "data", ["coordination"], ["Bibol"], "2026-10-17", "2026-11-22", D,
     "Dataset folders grouped by camera count, READMEs, pipeline outputs, and the 22 Nov storage clean-up.", "Drive: Materials/")
task("Write the Requirements & Design document", "rd", ["deliverable"], "all", "2026-10-20", "2026-10-25", D,
     "Sections split across the four members (overview, requirements, preliminary design with use-case and sequence diagrams, tasking plan, conclusion); Bibol assembled and submitted it.",
     "Drive: Requirements & Design Document - Group 22")
task("Plan the receiver after the 14 Oct lab meeting", "iter2", ["coordination"], ["Yernur"], "2026-10-14", "2026-10-15", D,
     "Turned D. Assylbek's receiver idea from the lab meeting into a step-by-step plan for the team.")
task("Build the first multi-camera pipeline with detector-based evaluation", "iter2", ["implementation", "experiment"], ["Bibol"], "2026-10-12", "2026-10-25", D,
     "Payloads for every camera, caption fusion and two IP-Adapter variants, with detector-based evaluation (later replaced by the VLM judge).", "PR #34 (`iter2/FINDINGS.md`)")
task("Try geometric (ground-plane) fusion across cameras", "iter2", ["experiment"], ["Bibol"], "2026-10-23", "2026-10-25", D,
     "Associated vehicles across cameras on the ground plane using the CARLA camera poses.", "PR #34")
task("Build the network-emulation prototype (gRPC, Docker, netem)", "iter2", ["implementation"], ["Zhengis"], "2026-10-25", "2026-10-25", D,
     "Payload schema, sender, router and ingest containers, network profiles and a run script. Prototype only; the transport layer continues in spring.", "`netsim/`")
task("Detector-era experiments: crop refinement, ControlNet sweep, sender vehicle list", "iter2", ["experiment"], ["Zhengis", "Bibol"], "2026-11-07", "2026-11-10", D,
     "Zhengis specified the crop-refinement experiment; the runs also covered a ControlNet strength sweep, a sender-side vehicle list and higher resolutions. Superseded by the VLM-judge protocol on 12 Nov.",
     "`iter2/NEXT_STEPS_RESULTS.md`, `iter2/REFINE_FULL_REPORT.md`")
task("Status report and demo for the lab", "iter2", ["coordination"], ["Bibol", "Yernur"], "2026-11-10", "2026-11-11", D,
     "Bibol prepared the status report and before/after demo; Yernur presented it to D. Assylbek on 11 Nov and wrote up his feedback.", "`iter2/STATUS_2026-11-11.md`, `iter2/demo/`")
task("Implement the VLM judge and re-judge every receiver", "iter2", ["experiment"], ["Bibol", "Yernur"], "2026-11-12", "2026-11-15", D,
     "gemma-4-31b-it with D. Assylbek's prompts, payload size per element and the Cityscapes reproduction check. Yernur relayed the lab's requirements.", "`iter2/VLM_FINDINGS.md`")
task("Implement Damir's fusion receiver and run it on all cases", "iter2", ["implementation", "experiment"], ["Bibol", "Yernur"], "2026-11-17", "2026-11-19", D,
     "img2img from the main reconstruction, ControlNets on the main maps, IP-Adapter on the supporting reconstructions; pilot and full run on 173 cases. Yernur clarified the design with D. Assylbek.", "`iter2/coordinator.py`, `iter2/fusion_demo/`")
task("Tune strength and IP-Adapter scale; full-resolution supports", "iter2", ["experiment"], ["Bibol"], "2026-11-19", "2026-11-21", D,
     "Tuning/held-out split fixed in advance; full-resolution supporting reconstructions as an ablation.", "`iter2/TUNING_RESULTS.md`")
task("Results package, report kit and hand-off for the report", "iter2", ["deliverable"], ["Bibol"], "2026-11-19", "2026-11-22", D,
     "Figures and tables generated from the judge answers, plus the hand-off package for writing the report.", "`iter2/report_kit/`, `iter2/handoff/`")
task("Explain real vs simulated results; hard cases for the lab", "iter2", ["experiment"], ["Bibol"], "2026-11-23", "2026-11-25", D,
     "Why real-world photos score higher than CARLA, every case where the fusion fixes the baseline, and the parked-rows scenario.", "`iter2/report_kit/4_real_vs_simulated.md`")
task("Pipeline step figures and process diagrams for both datasets", "iter2", ["deliverable"], ["Bibol", "Yernur"], "2026-11-23", "2026-11-26", D,
     "One figure per pipeline step for a real-world and a CARLA case, and six stage-by-stage process diagrams; Yernur designed the diagram layout.", "`iter2/report_kit/figures/`")
task("Repository housekeeping and merge of iteration 2", "iter2", ["implementation"], ["Bibol"], "2026-11-22", "2026-11-26", D,
     "All code and text outputs moved into the repository; PR #34 merged into main with iteration 1 kept on `iteration-1-final`.", "PR #34")
task("Biweekly adviser meetings", None, ["coordination"], "all", "2026-09-14", "2026-11-23", D,
     "Meetings with Prof. Zorbas on 14 Sep, 28 Sep, 12 Oct, 28 Oct, 9 Nov and 23 Nov.")
task("Lab meetings with D. Assylbek", None, ["coordination"], "all", "2026-10-02", "2026-11-18", D,
     "Meetings on 4 Oct, 14 Oct, 11 Nov and 18 Nov; Yernur organised them and kept the notes.")
task("Write the final report", "final", ["deliverable"], "all", "2026-11-22", "2026-11-27", "In Progress",
     "Final report in the course structure, written by the team.", "Drive: Final Report - Group 22")
task("Prepare and record the final presentation", "final", ["deliverable"], "all", "2026-11-25", "2026-11-27", "In Progress",
     "Slides (Temirshin) and the 4–6 minute recorded video with a demo.")
task("Generate the Turnitin report and submit", "final", ["deliverable"], [], "2026-11-27", "2026-11-27", "Todo",
     "Turnitin report from the Moodle assignment; upload the report, Turnitin report, video and slides to the Zormpas / Group 22 folder by 23:59.")
for title, s, e in [("Add CI for the unit tests", "2027-01-12", "2027-01-31"),
                    ("Validate the VLM judge: repeat runs, second judge, small human study", "2027-02-01", "2027-02-28"),
                    ("Fine-tune the fusion stage (ControlNet / IP-Adapter, LoRA)", "2027-02-01", "2027-03-31"),
                    ("Complete the transport layer over emulated links", "2027-02-01", "2027-03-31"),
                    ("Run the sender on a Raspberry Pi 5 with a power meter", "2027-03-01", "2027-03-31"),
                    ("Allocation study: smaller supporting payloads, main-camera choice, camera dropout", "2027-03-01", "2027-04-30"),
                    ("More real-world data, with a blurred subset for publication", "2027-03-01", "2027-04-30"),
                    ("Paper draft, poster and final presentation", "2027-04-01", "2027-05-15")]:
    task(title, "spring", ["spring-2027"], [], s, e, "Todo", "Planned for Senior Project II (from the plan in the final report).")

MS = {"setup": dict(n=1, title="Setup & Kickoff", due="2026-09-20", desc="Topic, team, tooling and the Kickoff document."),
      "lit": dict(n=3, title="Literature review", due="2026-11-09", desc="Papers, clustering, comparative survey, 2-page IEEE review, technical paper reviews."),
      "iter1": dict(title="Iteration 1: MMSD sender", due="2026-10-12", desc="Reproduction of the seed paper's sender and settings (PRs #27–#33)."),
      "data": dict(title="Datasets", due="2026-11-08", desc="CARLA v1–v4 and the real-world recordings, extraction and synchronisation."),
      "rd": dict(n=2, title="Requirements & Design", due="2026-10-25", desc="Requirements and Design document, submitted 25 Oct 2026."),
      "iter2": dict(title="Iteration 2: multi-camera receiver", due="2026-11-26", desc="Multi-camera receiver, VLM-judge evaluation and the material for the report (PR #34)."),
      "final": dict(n=4, title="Final Report & Presentation", due="2026-11-27", desc="Final report, Turnitin report and recorded presentation, due 27 Nov 2026 23:59."),
      "spring": dict(title="Spring 2027", due="2027-05-15", desc="Planned work for Senior Project II.")}
DONE_MS = ["setup", "lit", "iter1", "data", "rd", "iter2"]

ctx = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in map(pathlib.Path, [r"C:\Users\mrbqble\Desktop\csci408-probe\setup_project.py", r"C:\Users\mrbqble\Desktop\csci408-probe\share_project.py"]) if p.exists())
ok = {}
for s, login in PEOPLE.items():
    name = (rest("GET", f"users/{login}").get("name") or "")
    hit = any(x.lower() in name.lower() for x in (s, FULL[s].split()[1], "Ernur" if s == "Yernur" else s))
    if not hit:
        hit = any(login.lower() in l.lower() and (s.lower() in l.lower() or FULL[s].split()[1].lower() in l.lower()) for l in ctx.splitlines())
        name += " (checked in the September scripts)" if hit else ""
    ok[s] = hit
    print(f"user {login}: {name!r} -> {'verified' if hit else 'NOT verified'} as {FULL[s]}")

LAB = {"deliverable": ("0e8a16", "Course document or submission"), "literature": ("5319e7", "Literature work"), "dataset": ("fbca04", "Dataset work"),
       "implementation": ("1d76db", "Code and pipeline"), "experiment": ("d93f0b", "Measurement and evaluation"), "coordination": ("c5def5", "Meetings and organisation"),
       "spring-2027": ("bfdadc", "Planned for Senior Project II")}
have = {l["name"] for l in rest("GET", f"repos/{R}/labels?per_page=100")}
for n, (c, d) in LAB.items():
    if n not in have:
        rest("POST", f"repos/{R}/labels", {"name": n, "color": c, "description": d}); time.sleep(0.5)

ems = rest("GET", f"repos/{R}/milestones?state=all&per_page=100")
by_title, by_num = {m["title"]: m for m in ems}, {m["number"]: m for m in ems}
for k, m in MS.items():
    body = {"title": m["title"], "due_on": m["due"] + "T12:00:00Z", "description": m["desc"]}
    num = by_title[m["title"]]["number"] if m["title"] in by_title else (m.get("n") if m.get("n") in by_num else None)
    m["number"] = rest("PATCH", f"repos/{R}/milestones/{num}", body)["number"] if num else rest("POST", f"repos/{R}/milestones", body)["number"]
    time.sleep(0.5)

proj = gql('query{ user(login:"mrbqble"){ projectV2(number:2){ id fields(first:50){ nodes{ ... on ProjectV2Field{ id name dataType } ... on ProjectV2SingleSelectField{ id name dataType options{ id name } } } } } } }')["user"]["projectV2"]
PID = proj["id"]; F = {n["name"]: n for n in proj["fields"]["nodes"] if n}
OPT = {o["name"]: o["id"] for o in F["Status"]["options"]}
dates_ok = F.get("Start", {}).get("dataType") == "DATE" and F.get("End", {}).get("dataType") == "DATE"
print("Start/End are date fields:", dates_ok)
ADD = 'mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }'
SS = 'mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){ projectV2Item{ id } } }'
SD = 'mutation($p:ID!,$i:ID!,$f:ID!,$d:Date!){ updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{date:$d}}){ projectV2Item{ id } } }'

existing, page = {}, 1
while True:
    b = rest("GET", f"repos/{R}/issues?state=all&per_page=100&page={page}")
    if not b: break
    existing.update({i["title"]: i for i in b if "pull_request" not in i}); page += 1

rows, fails = [], []
for t in T:
    try:
        names = ", ".join(FULL[w] for w in t["who"]) or "Unassigned"
        body = f"{t['what']}\n\n**Who:** {names}\n**When:** {fmt(t['start'])} – {fmt(t['end'])}" + (f"\n**Where:** {t['where']}" if t["where"] else "")
        body += NOTE if t["status"] == "Done" else ("\n\n_The dates are targets._" if t["ms"] == "spring" else "")
        asg = [PEOPLE[w] for w in t["who"] if ok[w]]
        if t["title"] in existing:
            num, node = existing[t["title"]]["number"], existing[t["title"]]["node_id"]
        else:
            data = {"title": t["title"], "body": body, "assignees": asg, "labels": t["labels"]}
            if t["ms"]: data["milestone"] = MS[t["ms"]]["number"]
            res = rest("POST", f"repos/{R}/issues", data); num, node = res["number"], res["node_id"]; time.sleep(1.2)
        item = gql(ADD, p=PID, c=node)["addProjectV2ItemById"]["item"]["id"]
        gql(SS, p=PID, i=item, f=F["Status"]["id"], o=OPT[t["status"]])
        if dates_ok:
            gql(SD, p=PID, i=item, f=F["Start"]["id"], d=t["start"]); gql(SD, p=PID, i=item, f=F["End"]["id"], d=t["end"])
        if t["status"] == "Done":
            rest("PATCH", f"repos/{R}/issues/{num}", {"state": "closed", "state_reason": "completed"})
        rows.append(f"#{num:<3} {t['status']:<11} {t['start']}..{t['end']}  {','.join(asg) or '-':<38} {t['title']}")
    except Exception as e:
        fails.append(f"{t['title']}: {e}")
for k in DONE_MS:
    rest("PATCH", f"repos/{R}/milestones/{MS[k]['number']}", {"state": "closed"})
readme = ("Tasks of CSCI 408 Senior Project I (fall 2026) as they were actually done, and the plan for Senior Project II.\n\n"
          "The fall issues were backfilled on 26 Nov 2026 from the team's records (git history, Telegram, Drive). "
          "**Start** and **End** are the dates the work was done; issue creation dates are later. Assignees are the members who did the work.")
gql('mutation($p:ID!,$s:String!,$r:String!){ updateProjectV2(input:{projectId:$p, shortDescription:$s, readme:$r}){ projectV2{ id } } }',
    p=PID, s="Group 22: fall 2026 tasks (done) and spring 2027 plan", r=readme)
muts = [f["name"] for f in gql("query{ __schema{ mutationType{ fields{ name } } } }")["__schema"]["mutationType"]["fields"]]
print("view-related mutations:", [m for m in muts if "View" in m])
print(f"\n{len(rows)} issues on the board, {len(fails)} failures")
print("\n".join(rows))
print("\n".join(fails))
