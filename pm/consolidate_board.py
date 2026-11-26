"""Consolidate the backfilled board into 14 major fall tasks (+7 spring), then delete the absorbed issues (approved by Bibol, 26 Nov)."""
import json, subprocess, time
from collections import Counter
from datetime import date
R = "mrbqble/csci408-semantic-knowledge-exchange"
LOGIN = {"Bibol": "mrbqble", "Yernur": "Y3rnur", "Zhengis": "Zhengis04", "Temirshin": "CheffCorleOne"}
FULL = {"Bibol": "Bibol Assetbek", "Yernur": "Yernur Kenzhaly", "Zhengis": "Zhengis Kosher", "Temirshin": "Temirshin Kantemirov"}
ALL = list(LOGIN)
NOTE = ("\n\n---\n_Recorded on 26 Nov 2026 from the team's records (git history, Telegram, Drive). "
        "Start and End on the board are the dates the work was done; the issue itself was created later._")
def gh(args, data=None):
    r = subprocess.run(["gh", *args], input=None if data is None else json.dumps(data), capture_output=True, text=True, encoding="utf-8")
    if r.returncode: raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return json.loads(r.stdout) if r.stdout.strip() else None
def rest(m, p, d=None): return gh(["api", p, "-X", m] + (["--input", "-"] if d is not None else []), d)
def gql(q, **v):
    a = ["api", "graphql", "-f", f"query={q}"]
    for k, x in v.items(): a += ["-f", f"{k}={x}"]
    return gh(a)["data"]
def fmt(d): y, m, dd = map(int, d.split("-")); return f"{dd} {date(y, m, dd).strftime('%b %Y')}"
iss = {i["title"]: i for i in rest("GET", f"repos/{R}/issues?state=all&per_page=100") if "pull_request" not in i}
MS = {m["title"]: m["number"] for m in rest("GET", f"repos/{R}/milestones?state=all&per_page=100")}
K = {"setup": "Setup & Kickoff", "lit": "Literature review", "iter1": "Iteration 1: MMSD sender", "data": "Datasets", "rd": "Requirements & Design",
     "iter2": "Iteration 2: multi-camera receiver", "final": "Final Report & Presentation", None: None}
N = []
def t(keep, title, absorb, who, ms, labels, start, end, status, what, where=""):
    N.append(dict(keep=keep, title=title, absorb=absorb, who=who, ms=ms, labels=labels, start=start, end=end, status=status, what=what, where=where))
t("Choose the topic and register the team", "Topic and adviser selection", ["Contact the adviser and book the biweekly meeting slot"], ALL, "setup", ["deliverable", "coordination"],
  "2026-08-19", "2026-09-06", "Done", "Chose Prof. Zorbas's topic from the faculty proposals, declared the project type (R&D) and complexity (Highest), registered the team, and set up the biweekly adviser meetings.")
t("Write the Kickoff document", "Kickoff document", [], ALL, "setup", ["deliverable"], "2026-09-14", "2026-09-20", "Done",
  "The first course document: problem and motivation, planned system, hardware and software, evaluation plan, risks, deliverables and schedule. Each member wrote two of the eight sections; Bibol assembled and submitted it. Graded 95%.", "Drive: Kickoff Document - Group 22")
t("Write the Requirements & Design document", "Requirements & Design document", [], ALL, "rd", ["deliverable"], "2026-10-20", "2026-10-25", "Done",
  "The second course document: functional, non-functional and domain requirements, stakeholders, use cases, sequence diagrams, architecture and the tasking plan. Sections were split across the four members; Bibol assembled and submitted it on 25 Oct.", "Drive: Requirements & Design Document - Group 22")
t("Write the final report", "Final report",
  ["Results package, report kit and hand-off for the report", "Explain real vs simulated results; hard cases for the lab", "Pipeline step figures and process diagrams for both datasets", "Generate the Turnitin report and submit"],
  ALL, "final", ["deliverable"], "2026-11-19", "2026-11-27", "In Progress",
  "The CSCI 408 final report in the course structure, with the analysis and figures prepared for it (Bibol, Yernur): why real-world photos score higher than CARLA, the hard cases where multi-camera fusion helps, the step-by-step pipeline figures and process diagrams for both datasets, and the results package and report kit. Ends with the Turnitin report and the upload to the Zormpas / Group 22 folder (due 27 Nov 2026, 23:59).",
  "Drive: Final Report - Group 22; `iter2/report_kit/`")
t("Prepare and record the final presentation", "Final presentation", [], ALL, "final", ["deliverable"], "2026-11-25", "2026-11-27", "In Progress",
  "Slides (Temirshin) and the 4–6 minute recorded video with a demo of the system.")
t("Collect the literature (29 papers) and set up the review tracker", "Literature review and survey", ["Group the papers into thematic clusters", "Write the comparative literature survey and the 2-page IEEE review"],
  ALL, "lit", ["literature", "deliverable"], "2026-09-10", "2026-11-03", "Done",
  "Collected about 29 papers, grouped them into six themes, and wrote the comparative literature survey and the 2-page IEEE review the adviser asked for, comparing approaches rather than summarising papers one by one. Shown to the adviser on 9 Nov.",
  "Drive: Literature Review (papers, tracker, survey, 2-page review)")
t("Write the technical paper reviews", "Technical paper reviews", [], ALL, "lit", ["literature"], "2026-10-15", "2026-11-09", "Done",
  "One structured review per paper, using the course's template, written by all four members.", "Drive: Literature Review / Technical Paper Reviews")
t("Specify the dataset scenes", "Real-world dataset",
  ["Record real-world videos, batch 1 (three phones)", "Extract and synchronise the real-world frames (V1)", "Record real-world videos, batch 2 (parking scenes)", "Extract the real-world batch 2 (V2)", "Organise the datasets and outputs on the team Drive"],
  ALL, "data", ["dataset"], "2026-10-15", "2026-11-07", "Done",
  "Planned the scenes, filmed the same road scenes with three phones at the same time (22 Oct and 7 Nov), cut the videos into frames and aligned the phones in time by their audio, so that each case is one moment seen from up to three angles (366 three-phone triplets; 61 used in the evaluation). The datasets and outputs were organised on the team Drive (17 Oct – 22 Nov).",
  "Drive: Materials/Datasets/Real-world")
t("Set up CARLA and generate the first multi-camera dataset (v1)", "Simulated dataset in CARLA", ["Generate CARLA v2 and v3 with per-object ground truth", "Generate CARLA v4 and the training crops"],
  ["Zhengis", "Yernur", "Bibol"], "data", ["dataset"], "2026-10-15", "2026-11-08", "Done",
  "Scripts that place 3–6 virtual cameras around a junction in the CARLA driving simulator and save every view at the same instant, with the exact position of every car. v1–v3 (112 cases each) are the test sets, and v3 adds per-object ground truth; v4 (224 cases) and 8,620 image crops are prepared for spring fine-tuning.",
  "`tools/carla_multicam_kit/`; Drive: Materials/Datasets/Simulated")
t("Feasibility probe: payload size and latency per component", "Iteration 1: reproducing the seed paper's sender",
  ["Set up the GitHub repository, Projects board and team Drive", "Reproduce the MMSD sender on Cityscapes; encoding and Canny ablations", "Run the authors' configuration and a receiver smoke test",
   "Test the segmentation palette (Cityscapes vs ADE20K) on 100 images", "Fix the segmenter input size (512×1024 operating point)", "Research the coordinator fusion architecture"],
  ["Bibol"], "iter1", ["implementation", "experiment"], "2026-09-10", "2026-10-12", "Done",
  "Rebuilt the seed paper's sender (photo → segmentation map, edge map, caption) and checked it against the paper on 500 Cityscapes images: payload sizes, file encodings, edge settings, the colour scheme the receiver expects, and a bug where the segmenter silently shrank images to 384×384. Ends with the settings used in all later experiments. Includes the September feasibility probe, the repository and board setup, and the fusion-architecture research.",
  "PRs #27–#33")
t("Plan the receiver after the 14 Oct lab meeting", "First multi-camera receiver and detector-based experiments",
  ["Build the first multi-camera pipeline with detector-based evaluation", "Try geometric (ground-plane) fusion across cameras", "Detector-era experiments: crop refinement, ControlNet sweep, sender vehicle list", "Status report and demo for the lab"],
  ["Bibol", "Yernur", "Zhengis"], "iter2", ["implementation", "experiment"], "2026-10-12", "2026-11-11", "Done",
  "First attempts at using the other cameras: merging all captions into one prompt, feeding other views to an image adapter, matching cars across cameras on the road plane, and redrawing small cars at a larger scale (Zhengis's idea). Scored with a car detector on the original and rebuilt images. Showed that the other cameras did not help in this form and that cars are lost when the image is generated, not in the payload. Yernur turned the lab's idea into the plan and presented the results to D. Assylbek on 11 Nov.",
  "PR #34 (`iter2/FINDINGS.md`, `iter2/STATUS_2026-11-11.md`)")
t("Build the network-emulation prototype (gRPC, Docker, netem)", "Network-emulation prototype", [], ["Zhengis"], "iter2", ["implementation"], "2026-10-25", "2026-10-25", "Done",
  "Software that imitates the network between the cameras and the server: each camera runs in a Docker container and sends its payload over gRPC, while Linux tc/netem limits bandwidth and adds delay and loss. Prototype; the transport layer continues in spring.", "`netsim/`")
t("Implement the VLM judge and re-judge every receiver", "VLM judge and the multi-camera fusion receiver",
  ["Implement Damir's fusion receiver and run it on all cases", "Tune strength and IP-Adapter scale; full-resolution supports", "Repository housekeeping and merge of iteration 2"],
  ["Bibol", "Yernur"], "iter2", ["implementation", "experiment"], "2026-11-12", "2026-11-26", "Done",
  "Following the lab: (1) a vision-language model (gemma-4-31b-it) compares each rebuilt image with the original and answers two yes/no questions, same number of cars and same positions, as in the seed paper; (2) D. Assylbek's fusion design rebuilds every camera, then redraws the main camera's image once more with the other cameras' reconstructions as visual hints. Joint success 69.6% against 56.2% for the single camera on CARLA, 80.3% against 75.4% on real photos. Includes tuning, the full-resolution ablation and merging iteration 2 into main (PR #34). Yernur carried the design questions between the team and the lab.",
  "`iter2/VLM_FINDINGS.md`, `iter2/coordinator.py`, PR #34")
t("Biweekly adviser meetings", "Meetings with the adviser and the lab", ["Lab meetings with D. Assylbek"], ALL, None, ["coordination"], "2026-09-14", "2026-11-23", "Done",
  "Six biweekly meetings with Prof. Zorbas (14 Sep, 28 Sep, 12 Oct, 28 Oct, 9 Nov, 23 Nov) and four with D. Assylbek (4 Oct, 14 Oct, 11 Nov, 18 Nov). Yernur organised them and kept the notes.")
EXTRA_DELETE = ["Add CI for the unit tests"]

proj = gql('query{ user(login:"mrbqble"){ projectV2(number:2){ id fields(first:50){ nodes{ ... on ProjectV2Field{ id name dataType } ... on ProjectV2SingleSelectField{ id name options{ id name } } } } } } }')["user"]["projectV2"]
PID = proj["id"]; F = {n["name"]: n for n in proj["fields"]["nodes"] if n}; OPT = {o["name"]: o["id"] for o in F["Status"]["options"]}
ADD = 'mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{projectId:$p, contentId:$c}){ item{ id } } }'
SS = 'mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){ projectV2Item{ id } } }'
SD = 'mutation($p:ID!,$i:ID!,$f:ID!,$d:Date!){ updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{date:$d}}){ projectV2Item{ id } } }'
ok, todelete = True, []
for n in N:
    i = iss.get(n["keep"]) or iss.get(n["title"])
    if not i: print("MISSING kept issue:", n["keep"]); ok = False; continue
    body = (f"{n['what']}\n\n**Who:** {', '.join(FULL[w] for w in n['who'])}\n**When:** {fmt(n['start'])} – {fmt(n['end'])}"
            + (f"\n**Where:** {n['where']}" if n["where"] else "") + (NOTE if n["status"] == "Done" else ""))
    patch = {"title": n["title"], "body": body, "assignees": [LOGIN[w] for w in n["who"]], "labels": n["labels"],
             "milestone": MS[K[n["ms"]]] if n["ms"] else None, "state": "closed" if n["status"] == "Done" else "open"}
    if n["status"] == "Done": patch["state_reason"] = "completed"
    try:
        rest("PATCH", f"repos/{R}/issues/{i['number']}", patch)
        item = gql(ADD, p=PID, c=i["node_id"])["addProjectV2ItemById"]["item"]["id"]
        gql(SS, p=PID, i=item, f=F["Status"]["id"], o=OPT[n["status"]])
        gql(SD, p=PID, i=item, f=F["Start"]["id"], d=n["start"]); gql(SD, p=PID, i=item, f=F["End"]["id"], d=n["end"])
        print(f"kept #{i['number']}: {n['title']}")
    except Exception as e:
        print("EDIT FAILED", n["title"], e); ok = False
    todelete += [iss[a] for a in n["absorb"] if a in iss]
todelete += [iss[a] for a in EXTRA_DELETE if a in iss]
if ok:
    for i in todelete:
        try:
            gql('mutation($id:ID!){ deleteIssue(input:{issueId:$id}){ clientMutationId } }', id=i["node_id"]); print(f"deleted #{i['number']} {i['title']}"); time.sleep(0.3)
        except Exception as e:
            print("DELETE FAILED", i["number"], e)
else:
    print("Edits incomplete: nothing deleted.")
left = [i for i in rest("GET", f"repos/{R}/issues?state=all&per_page=100") if "pull_request" not in i]
print("issues now:", len(left), "| assignments:", dict(Counter(a["login"] for i in left for a in i["assignees"])))
for m in rest("GET", f"repos/{R}/milestones?state=all&per_page=100"):
    print(f"  milestone {m['state']:<6} {m['title']}: {m['closed_issues']} closed, {m['open_issues']} open")
print("CONSOLIDATION_DONE")
