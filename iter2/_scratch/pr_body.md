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
