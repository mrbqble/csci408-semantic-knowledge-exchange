import json, collections, numpy as np
import geom
m = json.load(open(r"C:\carla_multicam_kit\output\v3_smoke\manifest.json"))
print("aux_resolution", m.get("aux_resolution"))
src = collections.Counter(); kinds = collections.Counter(); off = []
union_stats = []
for c in m["cases"]:
    world_by_id = {}
    seen = collections.defaultdict(set)
    for ci, cam in enumerate(c["cameras"]):
        n_gt = sum(1 for i in cam["instances"] if i["kind"] == "car" and i["counts_in_gt"])
        assert n_gt == cam["counts"]["cars"], (c["case"], ci, n_gt, cam["counts"]["cars"])
        for i in cam["instances"]:
            kinds[i["kind"]] += 1
            w = i.get("world"); src[(i["kind"], w["source"] if w else "unresolved")] += 1
            if w:
                world_by_id[i["id"]] = w
                if i["counts_in_gt"]: seen[i["id"]].add(ci)
            if w and i["visible_px"] >= 80:
                dp = geom.depth_point(cam, i["centroid_px"][0], i["centroid_px"][1], i["depth_m"])
                off.append((i["kind"], w["source"], float(np.hypot(dp[0] - w["x"], dp[1] - w["y"]))))
    rec1 = {i["id"] for i in c["cameras"][0]["instances"] if i["kind"] == "car" and i["counts_in_gt"]}
    union = {i["id"] for cam in c["cameras"] for i in cam["instances"] if i["kind"] == "car" and i["counts_in_gt"]}
    union_stats.append((c["case"], len(rec1), len(union), len(c["cameras"])))
print("instance kinds:", dict(kinds)); print("world-position source:", dict(src))
for k in ("car", "pedestrian"):
    for s in ("actor", "environment_object"):
        d = [o[2] for o in off if o[0] == k and o[1] == s]
        if d: print(f"  depth-backprojection vs recorded position, {k}/{s}: n={len(d)}, median {np.median(d):.2f} m, p90 {np.percentile(d, 90):.2f} m")
print("case, cars seen by Rec1, cars seen by any camera, cameras:", union_stats)
print("sample instance:", json.dumps(m["cases"][0]["cameras"][0]["instances"][0]))
