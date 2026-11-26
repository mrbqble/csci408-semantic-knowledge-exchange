# START HERE: material for the final report (CSCI 408, Group 22)

Prepared 22 Nov 2026 by Bibol from the experiments on the HP OMEN laptop. It contains everything needed to write the report and make the presentation without running anything. Read this file first, then `01_report_kit/README.md`.

**Write in your own words.** A Turnitin report must be submitted with the final report. Use these documents as sources of facts and numbers; do not paste their text.

---

## 1. What is required (official course guidance)

Sources: `Final Report Guidance.pdf` and `Final Presentation Guidance.pdf` in the course Drive folder (`uni/04/01/CSCI 408/`), plus the Syllabus.

**Final report**
- **Purpose:** "provide a description of the project, summarize the work done so far, and outline initial plans for the spring semester".
- **Submit** the final report **and its Turnitin report** (generated through a Moodle assignment) to the course's shared Drive folder, in the subfolder with our adviser's name and group number, by **23:59 on Friday 27 Nov 2026**.
  - Submission folder: https://drive.google.com/drive/folders/1gscWWjaz0KgqwZpu3r_AGp8-1khEQvQC
- **Grading:** 25% of the course. Prof. Zorbas grades the technical content; the instructors check format and consistency (Syllabus).
- **Prescribed structure** (use exactly these sections):
  1. Introduction: (a) overview of the project; (b) objectives and goals
  2. Background / related work / literature review
  3. Project / product description: (a) system features; (b) requirements and functionalities; (c) design
  4. Progress this semester: (a) software-engineering methodology and third-party tools; (b) what was implemented (with screenshots); (c) problems encountered and how they were or will be addressed
  5. Plans for next semester (future work / conclusion)
  6. Ethical and legal considerations: (a) ethical issues; (b) legal compliance (data protection, intellectual property); (c) informed judgments and trade-offs; (d) sustainability and social responsibility
  7. References ("formatting is important")

**Final presentation** (20%, faculty committee)
- A **pre-recorded video of 4-6 minutes**.
- It must contain: an introduction to the problem; what was completed; issues and how they were resolved; **a demonstration of the system in use**; plans for spring.
- The committee scores Communication and Project Quality (0-10 each).
- **Submit** to the same Drive folder by the same deadline: the video, the slides, a copy of the final report, and the Turnitin report.

## 2. What to write in each section, and where the material is

| Section | Content | Material |
|---|---|---|
| **1a Overview** | Bandwidth-limited roadside cameras send a compact semantic payload (segmentation map, edge map, caption; 16-56 KB instead of a 376-531 KB JPEG); an edge receiver reconstructs the scene with Stable Diffusion. Our extension: several cameras observe the same scene. | `01_report_kit/README.md` (project in five sentences); `fig07`/`fig08` |
| **1b Objectives and goals** | Can payloads from other cameras make the main camera's reconstruction more faithful (car numbers and positions), measured with the VLM judge, at low communication cost? Quantified outcome below. | Section 4 below |
| **2 Literature** | Semantic communication; semantic image coding (seed paper, SPIC, SQ-GAN, ...); task-oriented transmission; multi-view and collaborative perception; distributed edge inference; energy; diffusion conditioning (Stable Diffusion, ControlNet, IP-Adapter) | `08_literature/literature_map.md` (28 papers plus models and datasets to cite) |
| **3a System features** | Per-camera payload extraction; per-camera reconstruction; multi-camera fusion; evaluation with a VLM judge | `01_report_kit/2_pipeline.md` 2.1-2.2 |
| **3b Requirements and functionalities** | Recap the requirements from our Requirements and Design document (shortcut in `Senior Project Work/`) and say how each is met. The payload size and processing-time measurements support the non-functional ones. | `Requirement and design document` (Drive); `03_statistics/timing_stats.csv`; `tables/payload_sizes_kb.csv` |
| **3c Design: process diagrams** | One vertical diagram per case showing every stage of the multi-camera MMSD process with its images: cameras and photos, payloads, per-camera reconstructions, ControlNet / img2img noise / IP-Adapter, final reconstruction. 6 distinct cases (3 real-world, 3 CARLA); PNG, JPG and a combined PDF | `01_report_kit/figures/process_diagrams/` |
| **3c / 4b Pipeline step by step (both datasets)** | One figure per pipeline step for a real-world and a simulated case (Prof. Zorbas asked for both on every step): input photos, payloads, per-camera reconstructions, fusion inputs, output and verdicts | `01_report_kit/figures/pipeline_steps/` |
| **3c Design** | Architecture: devices send payloads to an edge receiver; receiver = reconstruct every device, img2img from the main reconstruction, ControlNet (main maps), IP-Adapter (other reconstructions), global caption. Damir's diagram of 17 Nov is the reference. | `2_pipeline.md` 2.2; `fig07`/`fig08`; `06_code_snapshot/iter2/coordinator.py` |
| **4a Methodology and tools** | Iterative development in two iterations, biweekly meetings with Prof. Zorbas, lab meetings with Damir; GitHub (PR-based) and GitHub Projects; experiments as scripted batch jobs; data on Google Drive. Tools listed below. | Section 2.2 below; `06_code_snapshot/environment.txt` |
| **4b What was implemented** | Datasets (CARLA v3 and v4, real-world Astana v1/v2); sender; three receivers; VLM-judge evaluation; results. Screenshots: pipeline figures, example cases, gallery. | `01_report_kit/1_datasets.md`, `3_findings.md`; `figures/`; `04_example_cases/`; `05_gallery_all_cases/` |
| **Real vs simulated results** | Explain why real-world scores higher than CARLA: not easier scenes, not the judge; at the photo's resolution real cars keep more of their outlines (19.8% vs 12.8% edge pixels) and survive generation better (80% vs 66% of cars). Includes the judge-noise caveat | `01_report_kit/4_real_vs_simulated.md` |
| **4c Problems and solutions** | See the list in 2.3 below | `3_findings.md`; `02_detailed_reports/VLM_FINDINGS.md` |
| **5 Plans for spring** | Candidates in 2.4 below; agree them with Prof. Zorbas | |
| **6 Ethics and law** | Points in 2.5 below | |
| **7 References** | Format consistently (IEEE style is the safe default; ask the adviser) | `08_literature/literature_map.md` |

### 2.1 Key results to state

| Joint success (VLM judge) | CARLA v3 (112 cases) | Real-world (61 cases) |
|---|---|---|
| Single-camera MMSD (seed paper's method) | 56.2% | 75.4% |
| Multi-camera, captions only | 50.0% | 73.8% |
| **Damir's fusion, 896x512 supports (final configuration)** | **69.6%** (+13.4 pts, p = 0.040) | **80.3%** (+4.9 pts, n.s.) |
| Fusion, full-resolution supports (ablation) | 59.8% | 85.2% |

- **What the other cameras add,** measured as fusion vs the same pass without the IP-Adapter: +8.0 pts on CARLA, +16.4 pts on real-world (p = 0.021).
- **Judge calibration:** the original against itself scores 100%.
- **Payload per camera:** 50.7-56.2 KB (paper settings) or 16.3-20.8 KB (896x512), against a JPEG of 376-531 KB.
- **Sender:** about 0.7 s per photo.
- **Receiver** for a 3-camera case: about 130 s with the fusion, about 75 s for the single camera. Both run on a laptop RTX 3070.

### 2.2 Third-party tools and resources (section 4a)

- **Simulation and data:** CARLA 0.9.16 (Town10HD_Opt); three phones (iPhone 16 Pro Max, an Android phone, iPhone 16 Pro) for the real-world capture.
- **Models:**
  - sender: Mask2Former Swin-L (Cityscapes), BLIP base, Canny edges (OpenCV);
  - receiver: Stable Diffusion 1.5, ControlNet canny and seg, IP-Adapter;
  - judge: Gemma 4 31B (`gemma-4-31b-it`) through the Google Gemini API.
- **Software:** Python 3.14, PyTorch 2.14 (CUDA 13), Hugging Face diffusers 0.41 and transformers 5.17, Pillow, SciPy, matplotlib; Windows Task Scheduler for long batch jobs.
- **Collaboration:** GitHub (repository and Projects board), Google Drive (data and outputs), Telegram (coordination).
- **AI assistance:** an AI assistant (Claude) was used for coding, running experiments and drafting analysis. Check the course's AI-use policy and disclose it as required.

### 2.3 Problems encountered and how they were addressed (section 4c)

| Problem | What we did | Outcome |
|---|---|---|
| The library silently resized the segmenter input to 384x384, costing about 19 mIoU points (Iteration 1) | Fixed the input size at 512x1024 | Correct segmentation maps |
| The first evaluation (object-detector recall) did not match what the adviser cared about | Switched to Damir's VLM-judge protocol (12 Nov) | One agreed metric |
| Captions from the other cameras did not improve the main view | Implemented Damir's fusion architecture (17-19 Nov) | First significant multi-camera gain (CARLA +13.4 pts) |
| Generation at 1024x576 performed badly | Tested the models' working resolution and the paper's own resolution | Generating at the photo's resolution is best (single camera 56.2% / 75.4%) |
| Our reproduction scores 41% on Cityscapes against the paper's 86% | Ruled out the palette and the segmenter input size | Explained by the newer judge version (Damir); compare only under the same judge |
| The Gemma API was often overloaded (503 errors, 25-80 pairs per hour) | Parallel workers, retries, automatic waiting during outages | All pairs judged (3,478 judge records, including retries) |
| Risk of overfitting when tuning strength and IP-Adapter scale | Tuning half and held-out half, with the rule fixed in advance | No reliable gain; defaults kept |
| Synthetic vs real data disagree on supporting-image resolution | Ablation by number of cameras | Recommended 896x512; full resolution kept as an ablation |

### 2.4 Candidate plans for spring (section 5; agree with Prof. Zorbas)

1. **Communication and energy evaluation.** A trace-driven network simulation (ns-3 or OMNeT++) for latency. Energy with the first-order radio model (Heinzelman) and per-operation compute costs (Horowitz), calibrated against timings on edge hardware (Raspberry Pi 5).
2. **The sender on real edge hardware,** with timing and energy measured there.
3. **Reduce the fusion's failure cases** (16 of 63 broken on CARLA). Examples: choose the main camera adaptively, adapt strength per case, accept the fused result only when it agrees with the main reconstruction.
4. **Payload roles.** Supporting cameras could send the smaller 896x512 payload.
5. **Stronger evaluation.** A larger real-world set, a human check of the judge's verdicts, repeated judging.
6. **Fine-tuning the ControlNets** on traffic data. 8,620 training crops are already prepared.
7. **A faster receiver** (fewer steps, distilled models) towards near-real-time use.

### 2.5 Ethical and legal considerations (section 6)

- **(a) Ethical issues.**
  - The real-world photos show faces and licence plates of people who did not consent to being studied.
  - Traffic cameras raise surveillance concerns.
  - Generated reconstructions can drop or invent cars, so they must not be treated as evidence (e.g. for enforcement).
  - On the positive side, sending semantics instead of photos reduces how much personal detail leaves the device.
- **(b) Legal compliance.**
  - **Personal data:** Kazakhstan's Law No. 94-V "On personal data and their protection" (2013). Real-world images are kept internal; blur them in anything public.
  - **Cloud processing:** judging uploaded images to a third-party service (the Google Gemini API), including real-world photos. State this.
  - **Dataset licences:** Cityscapes is for non-commercial research only and may not be redistributed. CARLA code is MIT and its assets CC-BY. COCO images carry their own Flickr licences.
  - **Model licences:** Stable Diffusion 1.5 uses CreativeML OpenRAIL-M; Gemma has the Gemma Terms of Use; BLIP is BSD-3. Check the licences of ControlNet, IP-Adapter and Mask2Former on their model cards.
- **(c) Informed judgments.**
  - We kept real-world images out of public material and did not redistribute Cityscapes.
  - Example cases were chosen by fixed rules, not hand-picked.
  - The tuning rule was fixed before the results.
  - Negative results are reported (captions only; the Cityscapes gap).
  - The fusion design is credited to Damir Assylbek.
- **(d) Sustainability and social responsibility.**
  - The experiments used about **50 GPU-hours** on a laptop RTX 3070 (8,120 recorded generation passes), plus about 3,500 judged pairs through a cloud API.
  - Semantic payloads cut transmitted data by about 87-96% against JPEG, which matters for low-power IoT links.
  - Generating images at the receiver costs considerable compute; that is a trade-off to discuss.

### 2.6 The presentation video (4-6 minutes)

The demonstration must show the system in use. With Bibol not taking part, the options are:
- Show the step-by-step pipeline figures (`fig07`/`fig08`) and `04_example_cases/*/overview.jpg` as a walkthrough.
- Use the Drive folder `Pipeline Outputs/iteration2/fusion_demo` (the real intermediate images).
- Ask Bibol for a short screen recording of `fusion_demo.py` running on the OMEN.

## 3. Proposal vs delivered (explain this in 1b, 3b or 4c)

- **The pivot:** the registered proposal had each device send a different semantic component and the coordinator classify. At the 14 Sept adviser meeting the project moved to multi-camera reconstruction. Every device sends the seed paper's same three-element payload (confirmed by Damir, 11-12 Nov).
- **Classification accuracy** became preservation of car numbers and positions under the VLM judge.
- **Transmitted data size** was measured.
- **Per-device and end-to-end processing time** were measured on a laptop GPU, not on IoT hardware.
- **Communication latency and energy** were not measured; they are spring plans.
- **The October detector-based numbers** are superseded and should not be mixed in.

## 4. Pitfalls: what not to claim

1. Do not compare our percentages with the paper's 86-87%; the judge versions differ.
2. On real-world, fusion vs single camera (+4.9) is not significant; only fusion vs control is (p = 0.021). On CARLA, fusion vs single camera is significant (p = 0.040).
3. The judge is one model, run once per pair. Its consistency is shown; agreement with humans is not.
4. Timings come from a laptop GPU.
5. The final configuration uses the paper payload for the main camera and the 896x512 payload for the supporting reconstructions. Say so.
6. Credit the fusion design to Damir; our part is the implementation, the evaluation and the ablations.
7. Real-world images stay internal; Cityscapes images are not redistributed.

## 5. What is in this package, and where everything lives

| Folder | Contents |
|---|---|
| `01_report_kit/` | `README.md` (numbers to cite, figure list), `1_datasets.md`, `2_pipeline.md`, `3_findings.md`, `figures/` (11 figures), `tables/` (CSV) |
| `02_detailed_reports/` | `VLM_FINDINGS.md` (full log of the judge work), `VLM_JUDGE_REPORT.md` (all setups), `TUNING_RESULTS.md`, `PAYLOAD_SIZES.md`, READMEs; the October reports in `october_detector_era_superseded/` |
| `03_statistics/` | CSV tables, `timing_stats.csv`, `raw_judge_answers/` (every verdict with the judge's explanation), `judge_prompts.txt`, `judge_setups.csv`, `evaluation_cases.csv` |
| `04_example_cases/` | 12 cases with every intermediate image and the judge's verdicts |
| `05_gallery_all_cases/` | A comparison image for each of the 173 evaluated cases |
| `06_code_snapshot/` | Code snapshot and `environment.txt` |
| `07_datasets/` | CARLA manifest, dataset READMEs, case lists |
| `08_literature/` | `literature_map.md` |

**Where the full material lives:**
- **GitHub** (github.com/mrbqble/csci408-semantic-knowledge-exchange, branch `iter2-multicam`): all code, scripts (including the CARLA and real-world dataset tools), reports, text results and logs.
- **Google Drive** (`uni/04/01/CSCI 408/Senior Project Work/`):
  - `Datasets/`: CARLA v1-v4; real-world V1/V2 with the raw videos; mapping `V1/core_to_cases_1to3phones.csv`, which links the evaluated "core" case numbers to the files.
  - `Pipeline Outputs/`: payloads, the main reconstruction and fusion results, the fusion demo, report zips. Ablation and history outputs are kept on the laptop because of the Drive storage quota; their numbers are in GitHub.

## 6. How the project developed

| When | What |
|---|---|
| Aug-Sept | Topic proposal; group formation. **14 Sept:** pivot to multi-camera reconstruction. Kickoff document (20 Sept). |
| Oct | **Iteration 1:** reproduced the seed paper on Cityscapes. **Iteration 2:** CARLA datasets; real-world capture in Astana; first multi-camera receiver (captions); detector-based evaluation; Requirements and Design document (25 Oct). |
| 10-12 Nov | Status and demo for Damir. Decisions: the VLM judge is the metric; three-element payload; payload size per element. |
| 12-15 Nov | VLM-judge evaluation of all receivers; Damir's fixes; the paper's settings; Cityscapes reproduction. |
| 17-19 Nov | Damir's fusion architecture implemented and judged: first significant multi-camera gain. |
| 19-21 Nov | Full-resolution supports and tuning; report kit. |
| 22 Nov | This package; data moved to Drive, development material to GitHub. |

## 7. People

- **Team:** Bibol Assetbek, Yernur Kenzhaly, Zhengis Kosher, Temirshin Kantemirov.
- **Adviser:** Prof. Dimitrios Zorbas.
- **Lab:** Damir Assylbek, first author of the seed paper. He set the evaluation protocol and proposed the fusion architecture.
- **Instructors:** Adnan Yazici, Tu Nguyen.

## 8. Glossary

| Term | Meaning |
|---|---|
| Case | One moment of one scene, seen by several cameras |
| Main camera | cam1; its view is reconstructed and judged |
| Payload | Segmentation map, edge map and caption sent by a camera |
| MMSD | The seed paper's single-camera method: payload, then SD 1.5 with two ControlNets |
| Supporting reconstruction | A non-main camera's single-camera reconstruction, fed to the IP-Adapter |
| Fusion | img2img from the main reconstruction (strength 0.5) + ControlNets on the main maps + IP-Adapter on the supporting reconstructions + global caption |
| Control | The same img2img pass without the IP-Adapter |
| Joint success | The judge says both car numbers and car positions are preserved |
| McNemar "31/16" | Number of cases that succeed only with the first or only with the second receiver |
