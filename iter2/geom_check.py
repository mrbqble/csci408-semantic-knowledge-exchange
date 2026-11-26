import json, itertools
import numpy as np
import geom
from paths import CARLA_V2
m = json.load(open(CARLA_V2 / "manifest.json"))
print(f"{'yaw_sign':>9}{'pitch_sign':>11}{'focus in frame':>16}{'median |dist to image centre| px':>34}")
for ys, ps in itertools.product((1, -1), (1, -1)):
    inside, dist, n = 0, [], 0
    for c in m["cases"]:
        fp = c["focus_point"]; pt = (fp["x"], fp["y"], fp["z"])
        for cam in c["cameras"]:
            n += 1
            px = geom.project(cam, pt, yaw_sign=ys, pitch_sign=ps)
            if px and 0 <= px[0] < geom.W_IMG and 0 <= px[1] < geom.H_IMG:
                inside += 1
            if px: dist.append(np.hypot(px[0] - geom.W_IMG / 2, px[1] - geom.H_IMG / 2))
    print(f"{ys:9}{ps:11}{inside / n:16.3f}{np.median(dist):34.0f}   (n={n})")
# round trip: focus pixel -> ground -> focus point
errs = []
for c in m["cases"]:
    fp = c["focus_point"]; pt = np.array([fp["x"], fp["y"], fp["z"]])
    for cam in c["cameras"]:
        px = geom.project(cam, pt)
        if px:
            g = geom.ground_point(cam, *px, z_ground=pt[2], max_range=500)
            if g is not None: errs.append(np.linalg.norm(g - pt))
print("round-trip error (m): median %.4f max %.4f, n=%d" % (np.median(errs), np.max(errs), len(errs)))
