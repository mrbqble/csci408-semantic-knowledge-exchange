# START HERE: material for the final report (CSCI 408, Group 22)

Prepared 22 Nov 2026 by Bibol, from the experiments run on the HP OMEN laptop. It contains everything needed to write the report without running anything: what was built, how, on which data, every result, the statistics, example outputs and the literature. Read this file first, then `01_report_kit/README.md`.

---

## 1. What the report has to be (course requirements)

- **Form:** "a technical paper about the project in a form of conference paper" (course slides `01.pdf`, learning outcome 5; Syllabus outcome 5).
- **Weight and grading:** the Final Report is **25%** of the course grade. The adviser (Prof. Zorbas) grades content; the instructors (Yazici, Nguyen) grade **format and consistency**. The final presentation is a separate 20%, graded by a committee.
- **Deadline:** Friday 27 Nov 2026, 23:59 (team chat), together with the presentation.
- **Template:** the course files contain none. Format details were promised for the Week 12 "final report and presentation guidance session".
  - Use whatever template the instructors gave there. If there was none, the usual choice for a "conference paper" is the IEEE conference template (two columns).
  - Ask the instructors about page limits.
- **Continuity:** the paper should follow on from our earlier deliverables.
  - Kickoff: motivation, inputs and outputs, use cases, system description, hardware and software, evaluation plan.
  - Requirements and design: functional, non-functional and domain requirements; stakeholders; use cases; sequence diagrams; architecture.
  - The final paper should describe the system as built, and evaluate it against what we said we would evaluate (section 3 below).

## 2. Suggested paper structure, and where the material is

| Section | Content | Material in this package |
|---|---|---|
| Title, abstract | Multi-camera semantic image exchange: other cameras' payloads improve the main camera's reconstruction. Key numbers below. | `01_report_kit/README.md` (numbers to cite) |
| 1. Introduction | Motivation: bandwidth-limited IoT cameras; send semantics instead of images. Problem: can several cameras of one scene improve the reconstruction? Contributions (suggested list below). | Topic proposal (section 3); `01_report_kit/3_findings.md` 3.1 |
| 2. Related work | Semantic communication; semantic image coding (the seed paper, SPIC, SQ-GAN); task-oriented transmission; multi-view and collaborative perception; distributed edge inference; diffusion conditioning (ControlNet, IP-Adapter) | `08_literature/literature_map.md` |
| 3. System design | Architecture: devices send payloads to an edge receiver. Requirements recap. Sender and receiver components. | `01_report_kit/2_pipeline.md` 2.1-2.2; figures `fig07`/`fig08` (pipeline step by step) |
| 4. Method | Sender payload; receiver A (single-camera MMSD), B (captions only), C (Damir's fusion: per-camera reconstruction, img2img from the main one, IP-Adapter on the others) | `01_report_kit/2_pipeline.md`; `06_code_snapshot/iter2/coordinator.py` (`fuse_i2i`) |
| 5. Experimental setup | Datasets (CARLA v3 112 cases, real-world 61 cases, Cityscapes 100); hardware; settings; VLM judge and its calibration; statistics (Wilson intervals, McNemar test) | `01_report_kit/1_datasets.md`, `2_pipeline.md` 2.3; `03_statistics/judge_prompts.txt`, `evaluation_cases.csv` |
| 6. Results | Main comparison; receiver evolution; ablations (control, support resolution, tuning); payload size; processing time | `01_report_kit/3_findings.md` 3.2-3.6; figures `fig01`-`fig06`; `03_statistics/tables/*.csv`, `timing_stats.csv` |
| 7. Discussion | Why captions alone do not help; fix/break trade-off; synthetic vs real (support resolution); the judge version vs the paper | `3_findings.md` 3.4-3.5; examples `fig09`-`fig11`, `04_example_cases/` |
| 8. Limitations and future work | Judge (single model, single run); strict count criterion; small real-world set; no energy/latency measurement; no fine-tuning; fixed main camera | `3_findings.md` 3.7; section 5 below |
| 9. Conclusion | Recommended configuration and its gain | `3_findings.md` 3.8 |
| References | | `08_literature/literature_map.md` |

**Suggested contributions** (agree with Damir and Prof. Zorbas how to credit the fusion design; Damir proposed it):
1. Two multi-camera evaluation datasets.
   - CARLA v3: 112 synchronised multi-camera cases with 3-6 cameras and ground-truth objects.
   - Real-world Astana: 366 synchronised 3-phone triplets, 61 evaluated.
2. A VLM-judge evaluation of the seed paper's single-camera MMSD receiver on multi-camera traffic scenes: the effect of generation resolution and segmentation palette, plus judge calibration.
3. Implementation and evaluation of a multi-camera fusion receiver. It reconstructs every camera and then refines the main view with the others through an IP-Adapter. It beats the single camera significantly on CARLA (+13.4 points, p = 0.04), and controls and ablations show where the gain comes from.
4. Communication and compute cost per camera: payload 16-56 KB (against a 376-531 KB JPEG), and processing times.

## 3. Proposal vs delivered: what to say about the evaluation plan

The topic proposal promised classification by an edge coordinator, evaluated against a centralised model on accuracy, transmitted data, latency, per-device time, end-to-end time and energy. The project moved, under the advisers' direction, to reconstructing the main camera's view and judging its semantic fidelity. The report must state this openly.

| Proposed metric | Status | What we can report |
|---|---|---|
| Classification accuracy | **Replaced.** We reconstruct images instead of classifying them, following the seed paper and Damir's evaluation protocol. | VLM-judge preservation of car numbers and positions (joint success). The October detector-based per-car recall is superseded and should not be mixed in. |
| Transmitted data size | **Measured** | Payload per element and per camera (`fig06`, `tables/payload_sizes_kb.csv`): 50.7-56.2 KB per camera at the paper's settings, 16.3-20.8 KB at 896x512, against a 376-531 KB JPEG (q90) |
| Per-device processing time | **Measured** on the laptop GPU (RTX 3070), not on IoT hardware | `03_statistics/timing_stats.csv`. Sender per photo: segmentation about 265-280 ms, encoding 55-62 ms, edges 80-100 ms, caption about 305 ms, about 0.7 s in total. |
| End-to-end inference time | **Measured** (receiver, laptop GPU) | Single-camera reconstruction 75-77 s (1920x1088); supporting reconstruction about 7.8 s (896x512); fusion pass 39-43 s. A 3-camera case is about 130 s with the fusion, against about 75 s for the single camera. |
| Communication latency | **Not measured** (no network in the loop) | Can only be estimated from payload size and an assumed bandwidth. Label it clearly as an estimate. |
| Energy consumption | **Not measured** | Future work |
| Comparison with a centralised baseline | **Changed** | We compare against the seed paper's single-camera MMSD (the state-of-the-art baseline we build on) and against sending the photo as JPEG (data size) |

Another change to explain: the proposal imagined each device sending a *different* semantic component. In the final design every device sends the *same* three-element payload, following the seed paper; Damir decided this on 11-12 Nov. A sender-side vehicle list was tried and dropped by that decision.

## 4. Key numbers (cite from the CSV tables in `03_statistics/tables/`)

| | CARLA v3 (112) | Real-world (61) |
|---|---|---|
| Single-camera MMSD (paper settings) | 56.2% joint | 75.4% |
| Captions-only multi-camera | 50.0% | 73.8% |
| **Damir's fusion, 896x512 supports (recommended)** | **69.6%** | **80.3%** |
| Damir's fusion, full-resolution supports (ablation) | 59.8% | 85.2% |
| Fusion vs single camera (McNemar) | +13.4 pts, 31/16, p = 0.040 | +4.9 pts, 7/4, p = 0.55 |
| Fusion vs no-IP-Adapter control | +8.0 pts, p = 0.16 | +16.4 pts, p = 0.021 |
| Positions preserved (the five main receivers) | 88-96% | 93-97% |

- **Calibration:** the original photo judged against itself scores 100% (173 of 173).
- **Seed paper reproduction:** 41.0% on 100 Cityscapes images. The paper reports 86-87% with an older judge that is no longer available, so the two are not comparable (Damir).
- **Tuning:** a flat optimum; strength 0.5 and IP-Adapter scale 1.0 are kept.

## 5. What not to claim (common pitfalls)

1. **Do not compare our percentages with the paper's 86-87%.** Different judge versions.
2. **On real-world, only fusion vs control is significant** (p = 0.021). Fusion vs single camera there is +4.9 points, not significant (61 cases). On CARLA, fusion vs single camera is significant.
3. **Do not mix the October detector numbers** (recall at IoU 0.5) with the judge numbers. Damir asked us to drop detector-based evaluation.
4. **The judge is one model, run once per pair.** Calibration shows consistency, not agreement with humans.
5. **Timings come from a laptop GPU.** The sender did not run on IoT hardware. Energy and latency were not measured.
6. **Recommended configuration:** the main camera uses the paper payload, and the supporting cameras' reconstructions use the 896x512 payload. Say so explicitly.
7. **Credit the fusion architecture to Damir (D. Assylbek)**, who proposed it. Our part is the implementation, the evaluation and the ablations.
8. **Privacy:** the real-world photos show faces and licence plates. Use CARLA images in anything public, or blur them.
9. **Licensing:** Cityscapes images may not be redistributed. Show at most small examples in the paper, with citation.

## 6. What is in this package

| Folder | Contents |
|---|---|
| `01_report_kit/` | **Main reference:** `README.md` (numbers to cite, figure list), `1_datasets.md`, `2_pipeline.md`, `3_findings.md`, `figures/` (11 report-ready figures), `tables/` (CSV) |
| `02_detailed_reports/` | Full working reports: `VLM_FINDINGS.md` (the complete log of the judge work), `VLM_JUDGE_REPORT.md` (all 40+ setups with intervals and tests), `TUNING_RESULTS.md`, `PAYLOAD_SIZES.md`, the iter2 README, the fusion demo README. `october_detector_era_superseded/` holds the October reports (history only). |
| `03_statistics/` | `tables/` (all setups, paired tests, tuning, support resolution, payload sizes), `timing_stats.csv` (sender and receiver times), `raw_judge_answers/` (every judge answer with its full text, one `.jsonl` per setup), `judge_prompts.txt`, `judge_setups.csv`, `evaluation_cases.csv` |
| `04_example_cases/` | 12 cases (8 CARLA, 4 real-world, chosen by fixed rules). Each has original photos of all cameras, payload files, the reconstruction of every camera, results of every receiver, the judge's full answers, an `overview.jpg` and a `README.txt`. |
| `05_gallery_all_cases/` | One comparison image per evaluated case (112 CARLA + 61 real-world): original, single camera, fusion with 896x512 supports, fusion with full-resolution supports, with the judge verdict under each |
| `06_code_snapshot/` | All code (iter2 pipeline, iter1 reproduction, CARLA generators) and `environment.txt` (exact package versions, GPU). Live repository: github.com/mrbqble/csci408-semantic-knowledge-exchange, branch `iter2-multicam` (PR #34). |
| `07_datasets/` | CARLA v3 manifest (every case, camera and weather), dataset README files, the Cityscapes case list. **Full datasets are on the team Drive** (`uni/04/01/CSCI 408/Senior Project Work/Datasets/`), not in this zip. |
| `08_literature/` | `literature_map.md`: references for the 28 collected papers, grouped, with their relevance, plus the models, datasets and tools to cite |

## 7. How the project developed (for the methods or development-process part)

| When | What |
|---|---|
| Earlier in the semester | Topic proposal, kickoff document, requirements and design document |
| Oct 2026 | **Iteration 1:** reproduced the seed paper's sender and receiver on Cityscapes; found and fixed the segmenter input-size pitfall (384x384 squash). **Iteration 2 start:** CARLA multi-camera datasets (v2, then v3 with ground truth) and the 3-phone real-world capture in Astana; the first multi-camera receiver (captions of all cameras); detector-based evaluation. |
| 10-11 Nov | Status report and demo for Damir. Decisions: the VLM judge is the required metric; the payload stays three-element; report payload size per element. |
| 12-15 Nov | VLM judge implemented with Damir's prompts. Every receiver variant judged; Damir's two fixes (working resolution, palette); the paper's settings; Cityscapes reproduction. Result: other cameras' captions do not help. |
| 17-19 Nov | Damir proposed the fusion architecture. Implemented, demonstrated on single cases, then judged on all cases: first significant multi-camera gain. |
| 19-21 Nov | Damir's follow-ups: full-resolution supporting reconstructions; tuning of strength and IP-Adapter scale with a tuning/held-out split. |
| 21-22 Nov | Report kit and this hand-off package |

## 8. People

- **Team:** Bibol Assetbek, Yernur Kenzhaly, Zhengis Kosher, Temirshin Kantemirov.
- **Adviser:** Prof. Dimitrios Zorbas.
- **Lab:** Damir Assylbek, first author of the seed paper. He proposed the evaluation protocol and the fusion architecture.
- **Course instructors:** Adnan Yazici, Tu Nguyen.

## 9. Glossary

| Term | Meaning |
|---|---|
| Case | One moment of one scene seen by several cameras at the same time |
| Main camera | cam1: the camera whose view is reconstructed and judged |
| Payload | What a camera sends: segmentation map, edge map, caption |
| MMSD | The seed paper's single-camera method: payload, then Stable Diffusion 1.5 with two ControlNets |
| Supporting reconstruction | The single-camera reconstruction of a non-main camera, fed to the IP-Adapter in the fusion |
| Fusion | Damir's receiver: img2img from the main reconstruction (strength 0.5), ControlNets on the main maps, IP-Adapter on the supporting reconstructions, global caption |
| Control | The same img2img pass without the IP-Adapter |
| Joint success | The judge says both "car numbers preserved" and "car positions preserved" |
| McNemar test | Paired test on the same cases; "31/16" means 31 cases succeed only with the first receiver and 16 only with the second |
