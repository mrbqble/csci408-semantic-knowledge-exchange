# CARLA and real-world dataset toolkit (copied from C:\carla_multicam_kit on the HP OMEN, 22 Nov 2026)

Scripts that produced the datasets on the team Drive (Senior Project Work/Datasets/):
- `generate_cases.py`, `generate_cases_v2.py`, `generate_cases_v3.py`, `carla_multicam.py`, `patch_v3.py`, `check_connection.py`, `run_*.bat`, `config.bat`, `configs/`: CARLA 0.9.16 multi-camera case generation (CARLA v1-v4). Setup notes in `setup.md`.
- `extract_real_world.py` (V1, takes 1-3) and `extract_real_world_v2.py` (V2, takes 4-8): frame extraction and phone synchronisation from the raw videos, using `phone_sync_manifest*.json` and `takes_v2.json`.
- `build_cases_grouped.py`, `build_cases_all_levels.py`: grouping of synchronised frames into `cases_1to3phones`.

The datasets and videos themselves are on the Drive, not in git. The same generators v2/v3 are also in `carla/` at the repository root.
