## Summary
Iteration 2 pipeline, evaluation and write-up. The pipeline runs every camera's photo through the unchanged iteration-1 sender, rebuilds a master view at the coordinator (Rec1's edge and segmentation maps through two ControlNets, fused caption prompt, optional IP-Adapter), and outputs counts, classes and pixel positions per case. Network simulation, node failure and packet loss are out of scope.

Headline findings (details, tables and caveats in `iter2/FINDINGS.md`):
- The generative master view recovers about half of the vehicles (recall 0.51-0.58) and at most a third of the people the detector finds on the original photo. The loss is in generation: 96% of those vehicles are already in the transmitted segmentation map.
- Fused prompt beats the single view on two datasets (cars MAE 3.76 to 3.20 on v2, 3.17 to 2.71 on v3), but a control with captions from another case gave a similar gain on 24 cases, and neither IP-Adapter reading helped. Edge strength and 1280x704 gave no reliable gain.
- Ground-plane association across cameras reaches objects hidden from Rec1 (union recall 0.35 for vehicles vs at most 0.28 for any Rec1-frame method) but with precision 0.28. It needs camera poses (from the CARLA manifest here).

## What is in the PR
- `iter2/`: pipeline code, `FINDINGS.md`, `REPORT.md`, `README.md` (commands, run provenance), `paths.py` (dataset locations, env-overridable)
- `carla/`: generators v2 and v3 (v3 adds visible object ids and world positions to the manifest)
- `iter1/`: only the three modules iter2 imports (`mmsd_sender`, `receiver_smoke_test`, `palette_test`), unmodified; the rest of `iter1/` stays untracked
- Small result files force-added (`summary.json`, `counts.csv`, `detections.csv` for the three main runs, `v3_eval_union.json`); images, payloads and per-case JSON are ignored

## Notes for review
- The datasets are not in git (CARLA v2/v3 and the real-world set are on the OMEN); set paths in `iter2/paths.py` or the `CSCI408_*` environment variables.
- `iter2/ops/` holds the PowerShell used to run long jobs as scheduled tasks; it contains absolute paths and is a record, not a portable tool.
- Testing: after the path refactor I ran the whole chain (payloads, coordinator, analysis, fusion, scene evaluation, report) on a one-case v3 sample. The full results were produced before the refactor with the same scripts; the refactor only changed dataset path handling and one script's subprocess call.
- Not merged; no teammate has reviewed it yet.

## Update, 10 Nov 2026 (second commit)
- `iter2/STATUS_2026-11-11.md`: summary for the meeting with Damir (what exists, the metric, results, open questions).
- `iter2/demo/`: 18 before/after examples (10 CARLA v3, 8 real-world) chosen by a fixed worst-to-best rule, each with the payload files Rec1 transmits and both reconstructions.
- New experiments, compiled in `iter2/NEXT_STEPS_RESULTS.md`: where vehicles are lost (size, merged blobs); splitting merged blobs from the existing payload (not possible with rules); crop-and-redraw of small cars (`prompt_refine`: +0.019 recall on all 173 cases, off by default); generation at 2048x1152 (no gain); segmenter input size (no gain); sender-side vehicle list (Faster R-CNN at the sender: recall 0.78 vs ground truth, +68 B per photo); hyperparameter sweep with a hold-out check.
- ControlNet canny 0.7 / seg 1.5 confirmed on every case: CARLA v3 recall 0.485 to 0.537 against ground truth (paired +0.046, CI +0.019 to +0.074), real-world 0.469 to 0.562 against the detector on the original (+0.066, CI +0.030 to +0.099). Proposed as the new default; not switched yet.
- `coordinator.py` options `--steps`, `--guidance`, `--control-end`, `--negative-prompt` and the variant `prompt_refine`; `analysis.py --analysis-dir`. Defaults are unchanged.
- Training data prepared on the OMEN, not in git: CARLA v4 (224 cases, `carla/generate_cases_v3.py --seed 31`) and 8,620 training / 1,088 validation crops, with CARLA v3 and the 61 evaluated real-world cases held out.

## Update, 13 Nov 2026 (third commit): VLM-judge evaluation
Following the meeting with Damir (11 Nov): the VLM judge is the required metric, the payload stays the seed paper's three elements, payload sizes are reported per element, and the judge is run without and with two receiver fixes.
- `iter2/VLM_FINDINGS.md`: the judge is consistent (original vs itself 100%). Our reproduction of the seed receiver on Cityscapes scores 41% joint with this judge, against the paper's 86-87%. On our data, Damir's working-resolution fix helps on real photos (+15 to +18 points, p < 0.05), the palette fix changes nothing, and multi-camera captions never beat the reference camera alone. Best setting: 51-57% joint.
- `iter2/PAYLOAD_SIZES.md`: the edge map is 91% of today's payload; at the working resolution the payload drops to 16-21 KB per camera.
- Open questions for Damir: the paper's ControlNet weights, the judge version behind Table 6, and a sample of the paper's own reconstructions to calibrate against.
