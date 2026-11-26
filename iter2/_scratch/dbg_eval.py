import json, math
import eval_union as E
m = json.load(open(r"C:\carla_multicam_kit\output\carla_dataset_v3_ids\manifest.json"))
bad_gt, none_gt, n = [], 0, 0
for case in m["cases"]:
    for kind, objs in E.gt_objects(case).items():
        for i, d in objs.items():
            n += 1
            if d["xy"] is None: none_gt += 1
            elif not all(math.isfinite(v) for v in d["xy"]): bad_gt.append((case["folder"], kind, i, d["xy"]))
print("GT objects", n, "| no position", none_gt, "| non-finite", len(bad_gt), bad_gt[:5])
bad_pred = 0
for f in sorted(__import__("pathlib").Path("results/v3_geofuse").glob("case*.json")):
    g = json.load(open(f))
    for grp, v in g["objects"].items():
        for o in v["list"]:
            if not all(math.isfinite(x) for x in o["world_xy_m"]): bad_pred += 1; print("bad geofuse object", f.name, grp, o)
print("non-finite geofuse objects", bad_pred)
# a raw instance with problematic depth?
worst = max((i["depth_m"], c["folder"], i["id"], i["kind"], bool(i.get("world"))) for c in m["cases"] for cam in c["cameras"] for i in cam["instances"] if i["counts_in_gt"])
print("largest depth_m among GT instances:", worst)
