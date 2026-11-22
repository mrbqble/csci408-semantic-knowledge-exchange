#!/usr/bin/env python3
"""
CARLA multi-camera photo dataset v2: low cameras (about 2 m), 3 to 6 cameras per case, varied positions.

    <out>/case1/cam1.jpg ... camN.jpg   N = 3..6, one photo per camera, all taken on the same simulation tick
    <out>/manifest.json                 per camera: height above ground, pitch / yaw / roll, azimuth around the
                                        focus point, off-axis angle, field of view, visible cars and pedestrians
    <out>/README.txt

What is different from v1
  * Cameras stand about 2 m above the ground (street level), not on poles.
  * Each case picks a focus point on the road. Cameras are placed around it at different kinds of positions:
    junction centre, on an arm of the junction, at a junction corner, on the sidewalk beside an arm, or free.
    Every camera sees the focus point, but views are angled (off-axis) instead of always looking at the centre.
  * 1920x1080 photos.
  * The number of visible cars and pedestrians is controlled. Counts come from the instance-segmentation
    render (an object counts when at least --min-instance-px pixels of it are visible at 960x540). Every photo
    has between --count-min and --count-max of each; case targets are drawn so the mean is about --count-mean.

Needs a running CARLA 0.9.16 server and carla_multicam.py (the starter kit) in the same folder.

Example:
    python generate_cases_v2.py --out output/dataset_v2 --cases 112
"""

import argparse
import json
import math
import os
import queue
import random
import shutil
import sys
from collections import defaultdict

import numpy as np
import carla
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carla_multicam as kit  # helpers from the starter kit (get_frame, set_attr)

WEATHERS = ["ClearNoon", "CloudyNoon", "WetNoon", "SoftRainNoon", "ClearSunset", "WetCloudySunset"]
GROUND_LABELS = {"Roads", "Sidewalks", "RoadLines", "Ground", "Terrain"}
# Static things that really block a view (thin poles and signs are ignored on purpose).
BLOCKING = {"Buildings", "Walls", "Fences", "Vegetation", "Static", "Bridge", "GuardRail"}

# CARLA semantic ids: 1 road, 3 building, 4 wall, 5 fence, 6 pole, 9 vegetation, 12 pedestrian, 14 car, 15 truck,
# 16 bus, 18 motorcycle, 19 bicycle, 20 static, 22 other, 24 road line, 26 bridge, 28 guard rail.
SOLID_CLASSES = [3, 4, 5, 6, 9, 20, 22, 26, 28]
CAR_CLASSES = [14, 15, 16]
TWO_WHEELER_CLASSES = [18, 19]
PED_CLASS = 12
VEHICLE_CLASSES = CAR_CLASSES + [17] + TWO_WHEELER_CLASSES

# Per-view quality limits (share of the frame)
NEAR_SOLID_MAX = 0.06     # walls, trunks, leaves, railings closer than 8 m
NEAR_VEHICLE_MAX = 0.20   # vehicles closer than 10 m
VEHICLE_TOTAL_MAX = 0.45
LENS_VEHICLE_MAX = 0.02   # vehicle closer than 2.5 m (camera inside or touching a car)
ROAD_MIN = 0.04

KINDS = ["centre", "arm", "corner", "side", "free"]
KIND_WEIGHTS = [0.14, 0.28, 0.20, 0.23, 0.15]


def log(msg):
    print(msg, flush=True)


def parse_args():
    p = argparse.ArgumentParser(description="CARLA multi-camera photo dataset v2 (low cameras, 3-6 per case)")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--tm-port", type=int, default=8000)
    p.add_argument("--town", default="Town10HD_Opt")
    p.add_argument("--out", default="output/dataset_v2")
    p.add_argument("--cases", type=int, default=112, help="number of cases (case1..caseN)")
    p.add_argument("--cam-counts", default="3,4,5,6", help="camera counts, cycled over the cases")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--aux-width", type=int, default=960, help="width of the semantic/depth/instance renders used for counting")
    p.add_argument("--aux-height", type=int, default=540)
    p.add_argument("--jpeg-quality", type=int, default=92)
    p.add_argument("--cam-height", type=float, default=2.0, help="mean camera height above ground, m")
    p.add_argument("--cam-height-sd", type=float, default=0.12)
    p.add_argument("--count-min", type=int, default=3)
    p.add_argument("--count-max", type=int, default=20)
    p.add_argument("--count-mean", type=float, default=10.0)
    p.add_argument("--min-instance-px", type=int, default=80, help="visible pixels (at the aux resolution) for an object to count")
    p.add_argument("--vehicles", default="40,120", help="min,max vehicles spawned near the junction per case")
    p.add_argument("--walkers", default="40,130", help="min,max pedestrians spawned near the junction per case")
    p.add_argument("--local-radius", type=float, default=80.0, help="traffic spawns within this distance of the junction, m")
    p.add_argument("--delta", type=float, default=0.05, help="simulation step, s")
    p.add_argument("--warmup", type=float, default=5.0, help="simulated seconds of traffic warm-up per case")
    p.add_argument("--settle", type=float, default=2.0, help="simulated seconds the RGB cameras run before the photo (auto-exposure)")
    p.add_argument("--rounds", type=int, default=14, help="rounds of candidate poses per layout")
    p.add_argument("--candidates", type=int, default=3, help="candidate poses per missing camera per round")
    p.add_argument("--only-cases", default="", help="comma-separated case numbers to (re)generate")
    p.add_argument("--junction-shift", type=int, default=0)
    p.add_argument("--resume", action="store_true", help="skip cases already in the manifest")
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()
    args.cam_counts = [int(x) for x in args.cam_counts.split(",") if x.strip()]
    if not args.cam_counts or min(args.cam_counts) < 1:
        p.error("--cam-counts must be positive integers")
    args.vehicles = [int(x) for x in args.vehicles.split(",")]
    args.walkers = [int(x) for x in args.walkers.split(",")]
    args.only_cases = {int(x) for x in args.only_cases.split(",") if x.strip()}
    return args


# ---------------------------------------------------------------- plan, junctions, targets

def list_junctions(world_map):
    found = {}
    for wp in world_map.generate_waypoints(5.0):
        if wp.is_junction:
            j = wp.get_junction()
            found[j.id] = j.bounding_box.location
    if not found:
        raise RuntimeError("no junctions found on this map")
    return [found[k] for k in sorted(found)]


def plan_cases(n_cases, n_junctions, cam_counts, shift=0):
    return [{"case": k,
             "cameras": cam_counts[(k - 1) % len(cam_counts)],
             "junction": (k - 1 + shift) % n_junctions,
             "weather": WEATHERS[(k - 1) % len(WEATHERS)]} for k in range(1, n_cases + 1)]


def sample_target(rng, args):
    """Case target for the visible count: a Beta draw scaled to [count_min, count_max] with mean count_mean."""
    lo, hi = args.count_min, args.count_max
    m = (args.count_mean - lo) / float(hi - lo)
    a = 2.1
    b = a * (1.0 / m - 1.0)
    return int(round(lo + (hi - lo) * rng.betavariate(a, b)))


def xyz(loc):
    return {"x": round(loc.x, 2), "y": round(loc.y, 2), "z": round(loc.z, 2)}


# ---------------------------------------------------------------- geometry checks (ray casts)

def blocking_hits(world, a, b):
    hits = []
    for lp in world.cast_ray(a, b):
        name = str(lp.label)
        if name in BLOCKING:
            hits.append((lp.location.distance(a), name))
    return hits


def line_of_sight(world, a, b, margin=3.0):
    dist = a.distance(b)
    return not any(d < dist - margin for d, _ in blocking_hits(world, a, b))


def clear_near_lens(world, loc, rot, fov):
    """No geometry in a fan of rays in front of the lens (closer than 5 m, or two rays within 7 m) and none within 1.5 m."""
    n_hit = 0
    for k in (-0.45, -0.3, -0.15, 0.0, 0.15, 0.3, 0.45):
        f = carla.Rotation(pitch=rot.pitch, yaw=rot.yaw + k * fov, roll=0.0).get_forward_vector()
        end = carla.Location(loc.x + 7.0 * f.x, loc.y + 7.0 * f.y, loc.z + 7.0 * f.z)
        hits = blocking_hits(world, loc, end)
        if hits:
            if min(d for d, _ in hits) < 5.0:
                return False
            n_hit += 1
    if n_hit >= 2:
        return False
    for dx, dy, dz in ((1.5, 0, 0), (-1.5, 0, 0), (0, 1.5, 0), (0, -1.5, 0), (0, 0, 1.5)):
        if blocking_hits(world, loc, carla.Location(loc.x + dx, loc.y + dy, loc.z + dz)):
            return False
    return True


def ground_z(world, x, y, z_ref):
    """Height of the street surface below (x, y), or None if a roof, canopy or shelter is above it or nothing is below."""
    roof = False
    for lp in world.cast_ray(carla.Location(x, y, z_ref + 12.0), carla.Location(x, y, z_ref - 12.0)):
        name = str(lp.label)
        if name in GROUND_LABELS:
            return None if roof else lp.location.z
        if name in BLOCKING:
            roof = True
    return None


# ---------------------------------------------------------------- render-based view check and counts

def decode(img, channels=4):
    return np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, channels)


def count_instances(cls, ids, classes, min_px):
    mask = np.isin(cls, classes)
    if not mask.any():
        return 0
    _, counts = np.unique(ids[mask], return_counts=True)
    return int(np.sum(counts >= min_px))


def analyse_images(sem_img, depth_img, inst_img, min_px, slack=1.0, with_instances=False):
    """View quality and visible-object counts from a camera's own semantic, depth and instance renders."""
    sem = decode(sem_img)[:, :, 2]  # BGRA: class id is in R
    d = decode(depth_img).astype(np.float64)
    depth = (d[:, :, 2] + d[:, :, 1] * 256.0 + d[:, :, 0] * 65536.0) / (256.0 ** 3 - 1.0) * 1000.0
    inst = decode(inst_img)
    cls = inst[:, :, 2]
    ids = inst[:, :, 1].astype(np.int64) + inst[:, :, 0].astype(np.int64) * 256  # actor id = G + 256 * B
    vehicle = np.isin(sem, VEHICLE_CLASSES)
    m = {"near_solid": float(np.mean(np.isin(sem, SOLID_CLASSES) & (depth < 8.0))),
         "near_vehicle": float(np.mean(vehicle & (depth < 10.0))),
         "vehicle": float(np.mean(vehicle)),
         "in_lens": float(np.mean(vehicle & (depth < 2.5))),
         "road": float(np.mean(np.isin(sem, [1, 24])))}
    reason = None
    if m["near_solid"] > NEAR_SOLID_MAX * slack:
        reason = "near_solid"
    elif m["in_lens"] > LENS_VEHICLE_MAX * slack:
        reason = "vehicle_in_lens"
    elif m["near_vehicle"] > NEAR_VEHICLE_MAX * slack or m["vehicle"] > VEHICLE_TOTAL_MAX * slack:
        reason = "vehicle_in_front"
    elif m["road"] < ROAD_MIN:
        reason = "no_road"
    counts = {"cars": count_instances(cls, ids, CAR_CLASSES, min_px),
              "pedestrians": count_instances(cls, ids, [PED_CLASS], min_px),
              "two_wheelers": count_instances(cls, ids, TWO_WHEELER_CLASSES, min_px)}
    out = {"reason": reason, "metrics": {k: round(v, 4) for k, v in m.items()}, "counts": counts}
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
    return out


def count_ok(counts, targets, args, tol_scale, margin=0):
    """(ok, reason): hard bounds on both counts, plus a window around the case targets that widens with tol_scale."""
    c, p = counts["cars"], counts["pedestrians"]
    if not (args.count_min + margin <= c <= args.count_max - margin):
        return False, "cars_out_of_range"
    if not (args.count_min + margin <= p <= args.count_max - margin):
        return False, "pedestrians_out_of_range"
    if abs(c - targets["cars"]) > max(2.0, 0.3 * targets["cars"]) * tol_scale:
        return False, "cars_off_target"
    if abs(p - targets["pedestrians"]) > max(2.0, 0.3 * targets["pedestrians"]) * tol_scale:
        return False, "pedestrians_off_target"
    return True, None


def make_cam_bp(lib, kind, width, height, fov):
    names = {"rgb": "sensor.camera.rgb", "semantic": "sensor.camera.semantic_segmentation",
             "depth": "sensor.camera.depth", "instance": "sensor.camera.instance_segmentation"}
    bp = lib.find(names[kind])
    attrs = {"image_size_x": width, "image_size_y": height, "fov": fov, "lens_k": 0.0, "lens_kcube": 0.0}
    if kind == "rgb":
        attrs.update({"motion_blur_intensity": 0.0, "chromatic_aberration_intensity": 0.0,
                      "bloom_intensity": 0.0, "lens_flare_intensity": 0.0, "gamma": 2.2})
    for name, value in attrs.items():
        kit.set_attr(bp, name, value)
    return bp


def spawn_aux(world, poses, width, height):
    """semantic + depth + instance sensors for every pose: (sensors, queues) with 3 entries per pose."""
    lib = world.get_blueprint_library()
    sensors, queues = [], []
    for p in poses:
        for kind in ("semantic", "depth", "instance"):
            s = world.spawn_actor(make_cam_bp(lib, kind, width, height, p["fov"]), carla.Transform(p["loc"], p["rot"]))
            q = queue.Queue()
            s.listen(q.put)
            sensors.append(s)
            queues.append(q)
    return sensors, queues


def destroy_sensors(sensors):
    for s in sensors:
        try:
            s.stop()
            s.destroy()
        except RuntimeError:
            pass


CHECK_W, CHECK_H = 640, 360


def evaluate_poses(world, poses, args):
    """Low-resolution render check of candidate poses. One result dict per pose."""
    sensors, queues = spawn_aux(world, poses, CHECK_W, CHECK_H)
    try:
        frame = world.tick()
        imgs = [kit.get_frame(q, frame) for q in queues]
        min_px = max(8, int(args.min_instance_px * (CHECK_W * CHECK_H) / float(args.aux_width * args.aux_height)))
        return [analyse_images(imgs[3 * k], imgs[3 * k + 1], imgs[3 * k + 2], min_px) for k in range(len(poses))]
    finally:
        destroy_sensors(sensors)


# ---------------------------------------------------------------- camera poses

def make_context(world, world_map, center, lane_wps):
    arm = [(w.transform.location.x, w.transform.location.y, math.radians(w.transform.rotation.yaw))
           for w in lane_wps
           if not w.is_junction and 8.0 <= w.transform.location.distance(center) <= 45.0]
    inside = [(w.transform.location.x, w.transform.location.y, math.radians(w.transform.rotation.yaw))
              for w in lane_wps if w.is_junction and w.transform.location.distance(center) <= 8.0]
    return {"center": center, "arm": arm, "inside": inside, "map": world_map}


def choose_focus(world, rng, ctx, targets, vehicles, walkers):
    """Focus point on the road whose surroundings roughly match the case targets (about 60% of nearby actors are visible)."""
    c = ctx["center"]
    best, best_score = None, 1e9
    pool = ctx["arm"] + ctx["inside"][:max(1, len(ctx["inside"]) // 4)]
    for _ in range(14):
        if not pool:
            break
        x, y, _yaw = rng.choice(pool)
        gz = ground_z(world, x, y, c.z)
        if gz is None:
            continue
        f = carla.Location(x, y, gz)
        near_v = sum(1 for v in vehicles if v.is_alive and v.get_location().distance(f) < 35.0)
        near_p = sum(1 for w in walkers if w.is_alive and w.get_location().distance(f) < 35.0)
        score = abs(0.6 * near_v - targets["cars"]) + abs(0.6 * near_p - targets["pedestrians"])
        if score < best_score:
            best, best_score = f, score
    return best


def lane_distance(world_map, x, y, z):
    """Distance from (x, y) to the centre of the nearest drivable lane; traffic passes within about half a lane of it."""
    wp = world_map.get_waypoint(carla.Location(x, y, z), project_to_road=True, lane_type=carla.LaneType.Driving)
    if wp is None:
        return 99.0
    loc = wp.transform.location
    return math.hypot(loc.x - x, loc.y - y)


def sample_xy(rng, ctx, focus, kind):
    c = ctx["center"]
    if kind == "centre":
        r, a = rng.uniform(0.0, 5.0), rng.uniform(0.0, 2 * math.pi)
        return c.x + r * math.cos(a), c.y + r * math.sin(a)
    if kind == "arm" and ctx["arm"]:
        x, y, yaw = rng.choice(ctx["arm"])
        lat = rng.uniform(-1.5, 1.5) if rng.random() < 0.4 else rng.choice([-1.0, 1.0]) * rng.uniform(3.0, 6.5)
        return x - lat * math.sin(yaw), y + lat * math.cos(yaw)
    if kind == "side" and ctx["arm"]:
        x, y, yaw = rng.choice(ctx["arm"])
        lat = rng.choice([-1.0, 1.0]) * rng.uniform(4.0, 8.0)
        return x - lat * math.sin(yaw), y + lat * math.cos(yaw)
    if kind == "corner":
        a = math.radians(45.0 + 90.0 * rng.randrange(4) + rng.uniform(-15.0, 15.0))
        r = rng.uniform(13.0, 28.0)
        return c.x + r * math.cos(a), c.y + r * math.sin(a)
    r, a = rng.uniform(6.0, 40.0), rng.uniform(0.0, 2 * math.pi)  # free: ring around the focus
    return focus.x + r * math.cos(a), focus.y + r * math.sin(a)


def propose_pose(world, rng, ctx, focus, others, args, veh_xy=()):
    """A pose that sees the focus point from a varied position and passes the cheap ray-cast checks, or None."""
    aim_target = carla.Location(focus.x, focus.y, focus.z + 1.0)
    for _ in range(40):
        kind = rng.choices(KINDS, KIND_WEIGHTS)[0]
        x, y = sample_xy(rng, ctx, focus, kind)
        dist = math.hypot(focus.x - x, focus.y - y)
        if not (6.0 <= dist <= 45.0):
            continue
        if any((x - vx) ** 2 + (y - vy) ** 2 < 16.0 for vx, vy in veh_xy):
            continue
        if kind != "centre" and lane_distance(ctx["map"], x, y, ctx["center"].z) < 3.4:
            continue
        gz = ground_z(world, x, y, ctx["center"].z)
        if gz is None:
            continue
        height = min(2.3, max(1.7, rng.gauss(args.cam_height, args.cam_height_sd)))
        loc = carla.Location(x, y, gz + height)
        azimuth = math.degrees(math.atan2(y - focus.y, x - focus.x))
        too_near = False
        for o in others:
            d = loc.distance(o["loc"])
            if d < 5.0 or (d < 10.0 and abs((azimuth - o["azimuth"] + 180.0) % 360.0 - 180.0) < 15.0):
                too_near = True
                break
        if too_near:
            continue
        fov = rng.choice([70, 80, 90])
        spread = 0.45 if kind in ("side", "corner") else 0.32
        off_axis = rng.uniform(-spread, spread) * fov
        yaw = math.degrees(math.atan2(focus.y - y, focus.x - x)) + off_axis
        pitch = math.degrees(math.atan2(focus.z + 0.8 - loc.z, dist)) + rng.uniform(-2.0, 2.0)
        rot = carla.Rotation(pitch=max(-15.0, min(5.0, pitch)), yaw=yaw, roll=0.0)
        if not line_of_sight(world, loc, aim_target, margin=4.0):
            continue
        if not clear_near_lens(world, loc, rot, fov):
            continue
        return {"kind": kind, "loc": loc, "rot": rot, "fov": fov, "height": height, "ground_z": gz,
                "azimuth": azimuth, "distance": dist, "off_axis": off_axis}
    return None


def build_layout(world, rng, ctx, focus, n, args, targets, base_tol, veh_xy=()):
    """n validated poses: (cams or None, rejection counts)."""
    cams = [None] * n
    rejected = defaultdict(int)
    for rnd in range(args.rounds):
        pending = [i for i in range(n) if cams[i] is None]
        if not pending:
            break
        tol_scale = base_tol * (1.0 + rnd / 6.0)
        cands = []
        for i in pending:
            for _ in range(args.candidates):
                others = [c for c in cams if c is not None] + [p for _, p in cands]
                p = propose_pose(world, rng, ctx, focus, others, args, veh_xy)
                if p is not None:
                    cands.append((i, p))
        if not cands:
            rejected["no_pose_found"] += len(pending)
            continue
        results = evaluate_poses(world, [p for _, p in cands], args)
        for (i, p), res in zip(cands, results):
            if cams[i] is not None:
                continue
            if res["reason"] is not None:
                rejected[res["reason"]] += 1
                continue
            ok, why = count_ok(res["counts"], targets, args, tol_scale, margin=1)
            if not ok:
                rejected[why] += 1
                continue
            p["check"] = res
            cams[i] = p
    return (cams if all(c is not None for c in cams) else None), dict(rejected)


# ---------------------------------------------------------------- traffic

def spawn_vehicles_local(world, tm_port, lane_wps, center, count, radius, rng):
    lib = world.get_blueprint_library()
    bps = [b for b in lib.filter("vehicle.*") if b.has_attribute("number_of_wheels") and int(b.get_attribute("number_of_wheels")) == 4]
    wps = [w for w in lane_wps if w.transform.location.distance(center) <= radius]
    rng.shuffle(wps)
    vehicles = []
    for w in wps:
        if len(vehicles) >= count:
            break
        bp = rng.choice(bps)
        if bp.has_attribute("color"):
            bp.set_attribute("color", rng.choice(bp.get_attribute("color").recommended_values))
        bp.set_attribute("role_name", "autopilot")
        t = w.transform
        t.location.z += 0.5
        v = world.try_spawn_actor(bp, t)
        if v:
            vehicles.append(v)
    for v in vehicles:
        v.set_autopilot(True, tm_port)
    return vehicles


def spawn_walkers_near(world, center, count, radius, rng):
    lib = world.get_blueprint_library()
    walker_bps = lib.filter("walker.pedestrian.*")
    ctrl_bp = lib.find("controller.ai.walker")
    walkers, controllers = [], []
    tries = 0
    while len(walkers) < count and tries < count * 120:
        tries += 1
        loc = world.get_random_location_from_navigation()
        if loc is None or loc.distance(center) > radius:
            continue
        bp = rng.choice(walker_bps)
        if bp.has_attribute("is_invincible"):
            bp.set_attribute("is_invincible", "false")
        w = world.try_spawn_actor(bp, carla.Transform(loc))
        if w:
            walkers.append(w)
    world.tick()
    for w in walkers:
        controllers.append(world.spawn_actor(ctrl_bp, carla.Transform(), attach_to=w))
    world.tick()
    for c in controllers:
        c.start()
        dest = None
        for _ in range(40):
            d = world.get_random_location_from_navigation()
            if d is not None and d.distance(center) <= radius:
                dest = d
                break
        c.go_to_location(dest or world.get_random_location_from_navigation())
        c.set_max_speed(1.0 + rng.random() * 0.6)
    return walkers, controllers


def clear_traffic(client, world, vehicles, walkers, controllers):
    for c in controllers:
        try:
            c.stop()
        except RuntimeError:
            pass
    client.apply_batch([carla.command.DestroyActor(a) for a in controllers + walkers + vehicles])
    world.tick()


def run_ticks(world, n):
    for _ in range(max(0, int(n))):
        world.tick()


# ---------------------------------------------------------------- photos

def save_jpg(img, path, quality):
    arr = decode(img)[:, :, :3][:, :, ::-1]
    Image.fromarray(np.ascontiguousarray(arr)).save(path, quality=quality, optimize=True)


ENV_INDEX = {}


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


def photograph(world, cams, case_dir, args, targets, tol_scale=1.8):
    """RGB cameras settle (auto-exposure), then aux renders are added and the photos are taken on a tick where every
    camera passes the view and count checks. Returns (frame, sim_time, per-camera analysis) or None."""
    lib = world.get_blueprint_library()
    rgb, rgb_q = [], []
    aux, aux_q = [], []
    try:
        for c in cams:
            s = world.spawn_actor(make_cam_bp(lib, "rgb", args.width, args.height, c["fov"]), carla.Transform(c["loc"], c["rot"]))
            q = queue.Queue()
            s.listen(q.put)
            rgb.append(s)
            rgb_q.append(q)
        for _ in range(int(args.settle / args.delta)):
            frame = world.tick()
            for q in rgb_q:
                kit.get_frame(q, frame)
        aux, aux_q = spawn_aux(world, cams, args.aux_width, args.aux_height)
        for attempt in range(16):
            frame = world.tick()
            images = [kit.get_frame(q, frame) for q in rgb_q]
            axi = [kit.get_frame(q, frame) for q in aux_q]
            analyses = [analyse_images(axi[3 * k], axi[3 * k + 1], axi[3 * k + 2], args.min_instance_px, slack=1.6, with_instances=True) for k in range(len(cams))]
            ok = all(a["reason"] is None and count_ok(a["counts"], targets, args, tol_scale)[0] for a in analyses)
            if ok:
                sim_time = world.get_snapshot().timestamp.elapsed_seconds
                for a in analyses:
                    for inst in a.get("instances", []):
                        inst["world"] = object_world(world, inst["id"])
                os.makedirs(case_dir, exist_ok=True)
                for i, img in enumerate(images, 1):
                    save_jpg(img, os.path.join(case_dir, f"cam{i}.jpg"), args.jpeg_quality)
                return frame, sim_time, analyses
            run_ticks_with_queues(world, 4, rgb_q + aux_q)
        log("   capture check failed: " + "; ".join("%s %s" % (a["reason"] or count_ok(a["counts"], targets, args, tol_scale)[1] or "ok", a["counts"]) for a in analyses))
        return None
    finally:
        destroy_sensors(rgb + aux)


def run_ticks_with_queues(world, n, queues):
    for _ in range(n):
        frame = world.tick()
        for q in queues:
            kit.get_frame(q, frame)


# ---------------------------------------------------------------- main

def write_readme(out, args, manifest):
    st = manifest["stats"]
    text = f"""CARLA multi-camera photo dataset v2 (low cameras, 3-6 per case)
================================================================
{len(manifest['cases'])} cases, {st['photos']} photos. Map {args.town}, CARLA 0.9.16, seed {args.seed}.

Layout
  caseK/camJ.jpg   one photo per camera of case K (3 to 6 cameras); all photos of a case were taken on the same tick
  manifest.json    per case: junction, weather, focus point, count targets, and for every camera:
                   height_m (above ground), pitch / yaw / roll (degrees), azimuth_from_focus_deg, off_axis_deg,
                   distance_to_focus_m, fov, position kind, and the visible cars / pedestrians / two-wheelers

Cameras
  Height about {args.cam_height} m above the ground (sd {args.cam_height_sd} m). Every camera sees the case's focus point on the road.
  Position kinds: centre (junction centre), arm (on a road leading into the junction), corner (junction corner),
  side (sidewalk beside an arm, angled), free (ring around the focus). off_axis_deg is the angle between the viewing
  direction and the direction to the focus point, so views are angled instead of centred.
  Case K has cameras cycling 3, 4, 5, 6.

Counts
  Visible objects are counted from the instance-segmentation render at {args.aux_width}x{args.aux_height}; an object counts if at least
  {args.min_instance_px} of its pixels are visible. cars = cars, trucks, buses (parked ones included); pedestrians = walking people.
  Every photo has {args.count_min}-{args.count_max} cars and {args.count_min}-{args.count_max} pedestrians.
  Measured over all photos: cars mean {st['cars']['mean']}, min {st['cars']['min']}, max {st['cars']['max']};
  pedestrians mean {st['pedestrians']['mean']}, min {st['pedestrians']['min']}, max {st['pedestrians']['max']}.

Photos
  {args.width}x{args.height} JPEG (quality {args.jpeg_quality}), no lens distortion, no motion blur.

Regenerate
  python generate_cases_v2.py --out output/dataset_v2 --cases {len(manifest['cases'])} --seed {args.seed}
"""
    with open(os.path.join(out, "README.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def summarize(manifest):
    cars, peds, heights, kinds = [], [], [], defaultdict(int)
    photos = 0
    for e in manifest["cases"]:
        for c in e["cameras"]:
            photos += 1
            cars.append(c["counts"]["cars"])
            peds.append(c["counts"]["pedestrians"])
            heights.append(c["height_m"])
            kinds[c["kind"]] += 1

    def s(v):
        return {"mean": round(float(np.mean(v)), 2), "min": int(min(v)), "max": int(max(v))} if v else {"mean": 0, "min": 0, "max": 0}
    return {"photos": photos, "cars": s(cars), "pedestrians": s(peds),
            "height_m": {"mean": round(float(np.mean(heights)), 2) if heights else 0,
                         "min": round(min(heights), 2) if heights else 0, "max": round(max(heights), 2) if heights else 0},
            "kinds": dict(kinds)}


def save_manifest(out, manifest):
    manifest["cases"].sort(key=lambda e: e["case"])
    manifest["stats"] = summarize(manifest)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def main():
    args = parse_args()
    rng = random.Random(args.seed)
    client = carla.Client(args.host, args.port)
    client.set_timeout(120.0)
    world = client.get_world()
    if args.town and not world.get_map().name.endswith(args.town):
        log(f"loading {args.town} ...")
        world = client.load_world(args.town)

    original = world.get_settings()
    build_env_index(world)
    tm = client.get_trafficmanager(args.tm_port)
    out = args.out
    os.makedirs(out, exist_ok=True)
    manifest_path = os.path.join(out, "manifest.json")
    manifest = {"carla": client.get_server_version(), "map": args.town, "seed": args.seed,
                "image": {"width": args.width, "height": args.height, "format": "jpeg", "quality": args.jpeg_quality},
                "camera_height_m_target": args.cam_height, "count_range": [args.count_min, args.count_max],
                "count_mean_target": args.count_mean, "aux_resolution": [args.aux_width, args.aux_height], "cases": [], "failed_cases": []}
    if (args.resume or args.only_cases) and os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        redo = set(args.only_cases)
        manifest["cases"] = [e for e in manifest["cases"] if e["case"] not in redo]
        manifest["failed_cases"] = [k for k in manifest["failed_cases"] if k not in redo]
    done_cases = {e["case"] for e in manifest["cases"]} if args.resume else set()

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = args.delta
        world.apply_settings(settings)
        tm.set_synchronous_mode(True)
        tm.set_random_device_seed(args.seed)
        tm.set_global_distance_to_leading_vehicle(2.0)
        tm.global_percentage_speed_difference(25.0)
        world.set_pedestrians_seed(args.seed)

        world_map = world.get_map()
        junctions = list_junctions(world_map)
        lane_wps_all = [w for w in world_map.generate_waypoints(6.0) if w.lane_type == carla.LaneType.Driving]
        plan = plan_cases(args.cases, len(junctions), args.cam_counts, args.junction_shift)
        if args.only_cases:
            plan = [i for i in plan if i["case"] in args.only_cases]
        plan = [i for i in plan if i["case"] not in done_cases]
        by_junction = defaultdict(list)
        for item in plan:
            by_junction[item["junction"]].append(item)
        log(f"{len(plan)} cases to generate over {len(by_junction)} of {len(junctions)} junctions")

        for j_index in sorted(by_junction):
            center = junctions[j_index]
            lane_wps = [w for w in lane_wps_all if w.transform.location.distance(center) <= args.local_radius]
            ctx = make_context(world, world_map, center, lane_wps)
            log(f"--- junction {j_index} at ({center.x:.0f}, {center.y:.0f}): cases {[c['case'] for c in by_junction[j_index]]}")
            for item in by_junction[j_index]:
                k, n = item["case"], item["cameras"]
                world.set_weather(getattr(carla.WeatherParameters, item["weather"], carla.WeatherParameters.ClearNoon))
                targets = {"cars": sample_target(rng, args), "pedestrians": sample_target(rng, args)}
                done = False
                for attempt in range(1, 4):
                    n_veh = max(args.vehicles[0], min(args.vehicles[1], int(targets["cars"] * rng.uniform(2.4, 3.75))))
                    n_wlk = max(args.walkers[0], min(args.walkers[1], int(targets["pedestrians"] * rng.uniform(12.4, 19.5))))
                    vehicles = spawn_vehicles_local(world, args.tm_port, lane_wps, center, n_veh, args.local_radius, rng)
                    walkers, controllers = spawn_walkers_near(world, center, n_wlk, args.local_radius, rng)
                    try:
                        run_ticks(world, args.warmup / args.delta)
                        focus = choose_focus(world, rng, ctx, targets, vehicles, walkers)
                        if focus is None:
                            log(f"case {k}: no focus point (attempt {attempt})")
                            continue
                        base_tol = (1.0, 1.6, 3.0)[attempt - 1]
                        veh_xy = [(l.x, l.y) for l in (v.get_location() for v in vehicles if v.is_alive)]
                        cams, rejected = build_layout(world, rng, ctx, focus, n, args, targets, base_tol, veh_xy)
                        if cams is None:
                            log(f"case {k}: no valid layout for {n} cameras (attempt {attempt}; rejected {rejected})")
                            continue
                        shutil.rmtree(os.path.join(out, f"case{k}"), ignore_errors=True)
                        shot = photograph(world, cams, os.path.join(out, f"case{k}"), args, targets, base_tol * 2.6)
                        if shot is None:
                            log(f"case {k}: capture checks failed (attempt {attempt})")
                            shutil.rmtree(os.path.join(out, f"case{k}"), ignore_errors=True)
                            continue
                        frame, sim_time, analyses = shot
                        entry = {"case": k, "folder": f"case{k}", "n_cameras": n, "junction_index": j_index,
                                 "junction_center": xyz(center), "weather": item["weather"], "targets": targets,
                                 "focus_point": xyz(focus), "frame": frame, "sim_time_s": round(sim_time, 2),
                                 "traffic_spawned": {"vehicles": len(vehicles), "pedestrians": len(walkers)},
                                 "cameras": []}
                        for i, (c, a) in enumerate(zip(cams, analyses), 1):
                            entry["cameras"].append({
                                "file": f"cam{i}.jpg", "role": "main" if i == 1 else "support", "kind": c["kind"],
                                "height_m": round(c["height"], 2),
                                "pitch_deg": round(c["rot"].pitch, 1), "yaw_deg": round(c["rot"].yaw, 1), "roll_deg": 0.0,
                                "azimuth_from_focus_deg": round(c["azimuth"], 1),
                                "off_axis_deg": round(c["off_axis"], 1),
                                "distance_to_focus_m": round(c["distance"], 1),
                                "fov": c["fov"], "location": xyz(c["loc"]),
                                "counts": a["counts"], "view_check": a["metrics"],
                                "instances": a.get("instances", [])})
                        manifest["cases"].append(entry)
                        log(f"case {k}: {n} cameras, junction {j_index}, {item['weather']}, targets {targets['cars']}/{targets['pedestrians']}, "
                            f"cars {[c['counts']['cars'] for c in entry['cameras']]} peds {[c['counts']['pedestrians'] for c in entry['cameras']]} "
                            f"kinds {[c['kind'] for c in entry['cameras']]}")
                        done = True
                    finally:
                        clear_traffic(client, world, vehicles, walkers, controllers)
                    if done:
                        break
                if not done:
                    manifest["failed_cases"].append(k)
                    log(f"case {k}: FAILED, skipped")
                save_manifest(out, manifest)

        save_manifest(out, manifest)
        write_readme(out, args, manifest)
        st = manifest["stats"]
        log(f"done: {len(manifest['cases'])} cases, {st['photos']} photos in {out}; cars {st['cars']}, pedestrians {st['pedestrians']}, "
            f"height {st['height_m']}, kinds {st['kinds']}" + (f", failed cases: {manifest['failed_cases']}" if manifest["failed_cases"] else ""))
    finally:
        tm.set_synchronous_mode(False)
        world.apply_settings(original)


if __name__ == "__main__":
    main()
