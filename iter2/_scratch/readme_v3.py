from pathlib import Path
p = Path(r"C:\Users\mrbqble\My Drive (bibol.assetbek@nu.edu.kz)\uni\04\01\CSCI 408\Senior Project Work\Datasets\Simulated\carla_dataset_v3_ids\README.txt")
t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60])
    t = t.replace(old, new)
title_old = "CARLA multi-camera photo dataset v2 (low cameras, 3-6 per case)\n================================================================"
title_new = "CARLA multi-camera photo dataset v3 (low cameras, 3-6 per case; v2 generator plus visible-object ids and world positions)"
rep(title_old, title_new + "\n" + "=" * len(title_new))
rep("112 cases, 504 photos. Map Town10HD_Opt, CARLA 0.9.16, seed 25.",
    "112 cases, 504 photos. Map Town10HD_Opt, CARLA 0.9.16. Main run seed 21; cases 23 and 72 failed there and were regenerated with seed 25 at another junction.")
rep("                   distance_to_focus_m, fov, position kind, and the visible cars / pedestrians / two-wheelers\n",
    "                   distance_to_focus_m, fov, position kind, the visible cars / pedestrians / two-wheelers, and (new in v3)\n                   'instances', the visible objects with ids and positions (see below)\n")
old_regen = "Regenerate\n  python generate_cases_v2.py --out output/dataset_v2 --cases 112 --seed 25\n"
assert old_regen in t
new_regen = '''Visible-object ids and positions (new in v3)
  Every camera in manifest.json has 'instances': one entry per car (cars, trucks, buses), pedestrian and two-wheeler with at
  least 20 visible pixels in that camera's 960x540 render (the same render the counts come from; 'aux_resolution' in the
  manifest is [960, 540]).
    id            instance-segmentation id; for actors it is the CARLA actor id, shared by all cameras of the case
                  (ids of static parked cars were not checked across cameras)
    kind          car | pedestrian | two_wheeler
    visible_px    visible pixels in the 960x540 render
    counts_in_gt  true when visible_px >= 80, i.e. the object is included in 'counts'
    depth_m       median depth of the object's pixels, metres along the optical axis
    centroid_px, bbox_px   pixel centroid and box [x1, y1, x2, y2] in the 960x540 render
    world         for actors: bounding-box centre x, y, z (CARLA world frame, metres), yaw and extent;
                  null for static parked cars, which are not actors (recover a position from depth_m, centroid_px and the camera pose)
  Two vehicles in case 87 report NaN positions (2 of the 4,689 objects counted in the ground truth); treat them like parked cars.

Regenerate
  python generate_cases_v3.py --out output/dataset_v3 --cases 112 --seed 21 --resume --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12
  Failed cases are retried with --only-cases N --junction-shift 4 and another seed. The generator is in the project's GitHub
  repo, folder carla/ (pull request 34). Whether the same seed reproduces the same images was not checked.
'''
t = t.replace(old_regen, new_regen)
p.write_text(t, encoding="utf-8")
print("README updated")
