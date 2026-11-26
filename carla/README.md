# carla: multi-camera dataset generator

Copies of the scripts that generated the CARLA datasets (previously only in `C:\carla_multicam_kit`, which is not under version control). CARLA 0.9.16 (UE4), map `Town10HD_Opt`; install notes are in the original kit's `setup.md`.

- `carla_multicam.py`: helpers from the starter kit (imported by the generators).
- `generate_cases_v2.py`: v2 generator (112 cases, 3-6 low cameras per case, visible cars / pedestrians / two-wheelers counted from the instance-segmentation render; an object counts at >= 80 px at 960x540).
- `generate_cases_v3.py`: v2 plus, per camera, the list of visible objects (`instances`) with id, kind, visible pixels, depth, centroid and box in the 960x540 render, and the world position of the object (actors: bounding-box centre; static parked cars are not actors and have `world: null`; a few actors report NaN positions). The manifest also stores `aux_resolution`.

Server: `CarlaUE4.exe -quality-level=Epic -carla-rpc-port=2000 -RenderOffScreen` (needs the desktop GPU session). Commands used:
```
python generate_cases_v2.py --out OUT_V2 --cases 112 --seed 11 --resume --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12
python generate_cases_v3.py --out OUT_V3 --cases 112 --seed 21 --resume --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12
# failed cases, retried at other junctions (v3 shown; the first v3 run failed cases 23 and 72):
python generate_cases_v3.py --out OUT_V3 --cases 112 --seed 25 --only-cases 23,72 --junction-shift 4 --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12
```
v2 was produced by an initial run followed by resumes and retries (retry seeds are 11 + shift); the first run's flags were not recorded. Whether the same seed reproduces identical scenes was not checked (v2 was also built from several runs); treat a regenerated dataset as a new dataset.
