from pathlib import Path
p = Path(r"C:\carla_multicam_kit\generate_cases_v3.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)

rep("def analyse_images(sem_img, depth_img, inst_img, min_px, slack=1.0):",
    "def analyse_images(sem_img, depth_img, inst_img, min_px, slack=1.0, with_instances=False):")
rep('    return {"reason": reason, "metrics": {k: round(v, 4) for k, v in m.items()}, "counts": counts}',
'''    out = {"reason": reason, "metrics": {k: round(v, 4) for k, v in m.items()}, "counts": counts}
    if with_instances:     # v3: which objects are visible (ids), for a scene-level ground truth
        inst_list = []
        for kind, classes in (("car", CAR_CLASSES), ("pedestrian", [PED_CLASS]), ("two_wheeler", TWO_WHEELER_CLASSES)):
            mask = np.isin(cls, classes)
            if not mask.any():
                continue
            uid, cnt = np.unique(ids[mask], return_counts=True)
            for iid, px in zip(uid, cnt):
                if px < 20:
                    continue
                sel = mask & (ids == iid)
                ys, xs = np.nonzero(sel)
                inst_list.append({"id": int(iid), "kind": kind, "visible_px": int(px), "counts_in_gt": bool(px >= min_px),
                                  "depth_m": round(float(np.median(depth[sel])), 2),
                                  "centroid_px": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
                                  "bbox_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
        out["instances"] = inst_list
    return out''')

rep("def photograph(world, cams, case_dir, args, targets, tol_scale=1.8):",
'''ENV_INDEX = {}


def build_env_index(world):
    """Static-mesh vehicles (parked cars) are not actors: index the map's environment objects by id."""
    for name in ("Car", "Truck", "Bus", "Motorcycle", "Bicycle", "Pedestrians", "Rider"):
        lab = getattr(carla.CityObjectLabel, name, None)
        if lab is None:
            continue
        try:
            for o in world.get_environment_objects(lab):
                ENV_INDEX[int(o.id)] = o
        except Exception as e:
            log(f"environment objects {name}: {e}")
    log(f"environment-object index: {len(ENV_INDEX)} objects")


def object_world(world, iid):
    """World position (bounding-box centre) of an instance-segmentation id, or None when it is neither an actor nor an indexed object."""
    a = world.get_actor(iid)
    if a is not None:
        tr = a.get_transform()
        c = tr.transform(a.bounding_box.location)
        e = a.bounding_box.extent
        return {"source": "actor", "type": a.type_id, "x": round(c.x, 2), "y": round(c.y, 2), "z": round(c.z, 2),
                "yaw": round(tr.rotation.yaw, 1), "extent": [round(e.x, 2), round(e.y, 2), round(e.z, 2)]}
    o = ENV_INDEX.get(iid)
    if o is not None:
        bb = o.bounding_box
        return {"source": "environment_object", "name": o.name, "x": round(bb.location.x, 2), "y": round(bb.location.y, 2),
                "z": round(bb.location.z, 2), "extent": [round(bb.extent.x, 2), round(bb.extent.y, 2), round(bb.extent.z, 2)]}
    return None


def photograph(world, cams, case_dir, args, targets, tol_scale=1.8):''')

rep("args.min_instance_px, slack=1.6) for k in range(len(cams))]", "args.min_instance_px, slack=1.6, with_instances=True) for k in range(len(cams))]")
rep("                sim_time = world.get_snapshot().timestamp.elapsed_seconds\n",
'''                sim_time = world.get_snapshot().timestamp.elapsed_seconds
                for a in analyses:
                    for inst in a.get("instances", []):
                        inst["world"] = object_world(world, inst["id"])
''')
rep("    original = world.get_settings()\n", "    original = world.get_settings()\n    build_env_index(world)\n")
rep('"counts": a["counts"], "view_check": a["metrics"]})', '"counts": a["counts"], "view_check": a["metrics"],\n                                "instances": a.get("instances", [])})')
rep('"cases": [], "failed_cases": []}', '"aux_resolution": [args.aux_width, args.aux_height], "cases": [], "failed_cases": []}')
p.write_text(t, encoding="utf-8")
print("patched v3")
