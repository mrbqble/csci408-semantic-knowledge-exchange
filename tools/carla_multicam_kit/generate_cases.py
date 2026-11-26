#!/usr/bin/env python3
"""
Multi-camera photo dataset for CARLA: case1 ... caseN.

One case = one moment at one junction photographed by 1 to 6 cameras placed differently.

    <out>/case1/cam1.jpg
    <out>/case2/cam1.jpg  cam2.jpg
    ...
    <out>/manifest.json   camera poses, junction, weather and visible-vehicle counts for every case
    <out>/README.txt

cam1 is the "main" camera (low and oblique); the others are spread around the junction at different
heights, distances and fields of view. All photos of one case are taken on the same simulation tick.

Cameras are placed at random but every pose is checked with ray casts: not inside or right behind
geometry (balustrades, trunks), a clear line of sight to the junction, no vehicle in front of the lens,
and at least --min-visible moving vehicles in view.

Needs a running CARLA 0.9.16 server and carla_multicam.py (the starter kit) in the same folder.

Example:
    python generate_cases.py --out output/dataset_v1 --cases 30
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
import carla_multicam as kit  # helpers from the starter kit (spawn_vehicles, get_frame, look_at, ...)

WEATHERS = ["ClearNoon", "CloudyNoon", "WetNoon", "SoftRainNoon", "ClearSunset", "WetCloudySunset"]
# Static things that really block a view (thin poles and signs are ignored on purpose).
BLOCKING = {"Buildings", "Walls", "Fences", "Vegetation", "Static", "Bridge", "GuardRail"}

# Render-based view check (semantic + depth at low resolution). CARLA semantic ids: 1 road, 3 building, 4 wall, 5 fence,
# 6 pole, 9 vegetation, 14-19 vehicles, 20 static, 22 other, 24 road line, 26 bridge, 28 guard rail.
SOLID_CLASSES = [3, 4, 5, 6, 9, 20, 22, 26, 28]
VEHICLE_CLASSES = [14, 15, 16, 17, 18, 19]
CHECK_W, CHECK_H = 640, 320
NEAR_SOLID_MAX = 0.04     # share of the frame covered by walls, trunks, leaves, railings closer than 8 m
NEAR_VEHICLE_MAX = 0.045  # share covered by vehicles closer than 10 m (a bus in front of the lens)
VEHICLE_TOTAL_MAX = 0.15
VEHICLE_TOTAL_MIN = 0.008
ROAD_MIN = 0.06


def log(msg):
    print(msg, flush=True)


def parse_args():
    p = argparse.ArgumentParser(description="CARLA multi-camera photo dataset: case1..caseN")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--tm-port", type=int, default=8000)
    p.add_argument("--town", default="Town10HD_Opt")
    p.add_argument("--out", default="output/dataset_v1")
    p.add_argument("--cases", type=int, default=30, help="number of cases (case1..caseN)")
    p.add_argument("--cam-counts", default="1,2,3,4,5,6",
                   help="camera counts, cycled over the cases: case k gets counts[(k-1) %% len]")
    p.add_argument("--width", type=int, default=2048)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--jpeg-quality", type=int, default=92)
    p.add_argument("--vehicles", type=int, default=70)
    p.add_argument("--walkers", type=int, default=30)
    p.add_argument("--walker-radius", type=float, default=70.0, help="pedestrians spawn within this distance of the junction, m")
    p.add_argument("--delta", type=float, default=0.05, help="simulation step, s")
    p.add_argument("--warmup", type=float, default=15.0, help="simulated seconds of traffic warm-up per junction")
    p.add_argument("--gap", type=float, default=8.0, help="simulated seconds between two cases at one junction")
    p.add_argument("--settle", type=float, default=2.5, help="simulated seconds the cameras run before the photo (auto-exposure)")
    p.add_argument("--min-visible", type=int, default=3, help="moving vehicles that must be in view of every camera")
    p.add_argument("--only-cases", default="",
                   help="comma-separated case numbers to (re)generate; an existing manifest in --out is kept and updated")
    p.add_argument("--junction-shift", type=int, default=0,
                   help="put case k at junction ((k-1)+shift) %% N; use it to redo cases that failed at a hard junction")
    p.add_argument("--rounds", type=int, default=12, help="how many times a rejected camera pose is re-drawn")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()
    args.cam_counts = [int(x) for x in args.cam_counts.split(",") if x.strip()]
    if not args.cam_counts or min(args.cam_counts) < 1:
        p.error("--cam-counts must be positive integers")
    args.only_cases = {int(x) for x in args.only_cases.split(",") if x.strip()}
    return args


# ---------------------------------------------------------------- junctions and plan

def list_junctions(world_map):
    """Junction centres sorted by junction id (same order as the starter kit's --junction-index)."""
    found = {}
    for wp in world_map.generate_waypoints(5.0):
        if wp.is_junction:
            j = wp.get_junction()
            found[j.id] = j.bounding_box.location
    if not found:
        raise RuntimeError("no junctions found on this map")
    return [found[k] for k in sorted(found)]


def plan_cases(n_cases, n_junctions, cam_counts, shift=0):
    plan = []
    for k in range(1, n_cases + 1):
        plan.append({"case": k,
                     "cameras": cam_counts[(k - 1) % len(cam_counts)],
                     "junction": (k - 1 + shift) % n_junctions,
                     "weather": WEATHERS[(k - 1) % len(WEATHERS)]})
    return plan


# ---------------------------------------------------------------- geometry checks

def xyz(loc):
    return {"x": round(loc.x, 2), "y": round(loc.y, 2), "z": round(loc.z, 2)}


def blocking_hits(world, a, b):
    """View-blocking static geometry on the segment a->b as (distance from a, label)."""
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
    """No geometry in a fan of rays in front of the lens (closer than 5 m, or two rays within 7 m) and none within 2 m around it."""
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
    for dx, dy, dz in ((2, 0, 0), (-2, 0, 0), (0, 2, 0), (0, -2, 0), (0, 0, 2)):
        if blocking_hits(world, loc, carla.Location(loc.x + dx, loc.y + dy, loc.z + dz)):
            return False
    return True


def project(loc, rot, fov, width, height, point):
    """Pinhole projection of a world point into a camera: (u, v, depth). Depth is metres along the view axis."""
    f = width / (2.0 * math.tan(math.radians(fov) / 2.0))
    w2c = np.array(carla.Transform(loc, rot).get_inverse_matrix())
    pc = w2c @ np.array([point[0], point[1], point[2], 1.0])
    depth = pc[0]  # CARLA camera axes: x forward, y right, z up
    if depth < 1e-3:
        return None
    return width / 2.0 + f * pc[1] / depth, height / 2.0 - f * pc[2] / depth, depth


def vehicle_center(v):
    bb = v.bounding_box
    m = np.array(v.get_transform().get_matrix())
    return m @ np.array([bb.location.x, bb.location.y, bb.location.z, 1.0])


def analyse_view(world, loc, rot, fov, width, height, vehicles):
    """(moving vehicles visible, a vehicle is right in front of the lens). Visibility = in frame, 7-90 m, clear line of sight."""
    visible, too_close = 0, False
    for v in vehicles:
        if not v.is_alive:
            continue
        p = vehicle_center(v)
        pr = project(loc, rot, fov, width, height, p)
        if pr is None:
            continue
        u, vpx, depth = pr
        if not (0 <= u < width and 0 <= vpx < height):
            continue
        if depth < 7.0:
            too_close = True
            continue
        if depth > 90.0:
            continue
        if line_of_sight(world, loc, carla.Location(float(p[0]), float(p[1]), float(p[2]))):
            visible += 1
    return visible, too_close


def sample_pose(rng, center, role, azimuth_deg):
    if role == "main":
        radius, height = rng.uniform(15.0, 34.0), rng.uniform(3.0, 5.5)
    else:
        radius = rng.uniform(12.0, 42.0)
        height = rng.choice([rng.uniform(3.0, 6.0), rng.uniform(6.0, 10.0), rng.uniform(10.0, 15.0)])
    ang = math.radians(azimuth_deg + rng.uniform(-12.0, 12.0))
    loc = carla.Location(center.x + radius * math.cos(ang), center.y + radius * math.sin(ang), center.z + height)
    aim = carla.Location(center.x + rng.uniform(-6.0, 6.0), center.y + rng.uniform(-6.0, 6.0),
                         center.z + rng.uniform(0.0, 1.5))
    pitch, yaw = kit.look_at(loc, aim)
    rot = carla.Rotation(pitch=pitch + rng.uniform(-3.0, 3.0), yaw=yaw + rng.uniform(-8.0, 8.0), roll=0.0)
    fov = rng.choice([70, 80, 90, 100])
    return loc, rot, fov


def view_quality(sem_img, depth_img):
    """Judge a camera from its own semantic and depth render: (ok, metrics, reason)."""
    h, w = sem_img.height, sem_img.width
    sem = np.frombuffer(sem_img.raw_data, dtype=np.uint8).reshape(h, w, 4)[:, :, 2]  # BGRA: class id is in R
    d = np.frombuffer(depth_img.raw_data, dtype=np.uint8).reshape(h, w, 4).astype(np.float64)
    depth = (d[:, :, 2] + d[:, :, 1] * 256.0 + d[:, :, 0] * 65536.0) / (256.0 ** 3 - 1.0) * 1000.0
    vehicle = np.isin(sem, VEHICLE_CLASSES)
    m = {"near_solid": float(np.mean(np.isin(sem, SOLID_CLASSES) & (depth < 8.0))),
         "near_vehicle": float(np.mean(vehicle & (depth < 10.0))),
         "vehicle": float(np.mean(vehicle)),
         "road": float(np.mean(np.isin(sem, [1, 24])))}
    reason = None
    if m["near_solid"] > NEAR_SOLID_MAX:
        reason = "near_solid"
    elif m["near_vehicle"] > NEAR_VEHICLE_MAX or m["vehicle"] > VEHICLE_TOTAL_MAX:
        reason = "vehicle_in_front"
    elif m["vehicle"] < VEHICLE_TOTAL_MIN:
        reason = "no_vehicles"
    elif m["road"] < ROAD_MIN:
        reason = "no_road"
    return reason is None, {k: round(v, 4) for k, v in m.items()}, reason


def make_aux_bp(lib, kind, width, height, fov):
    bp = lib.find("sensor.camera.depth" if kind == "depth" else "sensor.camera.semantic_segmentation")
    for name, value in {"image_size_x": width, "image_size_y": height, "fov": fov, "lens_k": 0.0, "lens_kcube": 0.0}.items():
        kit.set_attr(bp, name, value)
    return bp


def validate_poses(world, poses):
    """Render a low-resolution semantic + depth view from every pose and judge it. One result per pose."""
    lib = world.get_blueprint_library()
    sensors, queues = [], []
    try:
        for p in poses:
            for kind in ("semantic", "depth"):
                s = world.spawn_actor(make_aux_bp(lib, kind, CHECK_W, CHECK_H, p["fov"]),
                                      carla.Transform(p["loc"], p["rot"]))
                q = queue.Queue()
                s.listen(q.put)
                sensors.append(s)
                queues.append(q)
        imgs = []
        for _ in range(2):
            frame = world.tick()
            imgs = [kit.get_frame(q, frame) for q in queues]
        return [view_quality(imgs[2 * k], imgs[2 * k + 1]) for k in range(len(poses))]
    finally:
        for s in sensors:
            s.stop()
            s.destroy()


def propose_pose(world, rng, center, i, n, base, others, args, vehicles):
    """A random pose that passes the cheap ray-cast and vehicle-visibility checks, or None."""
    role = "main" if i == 0 else "support"
    azimuth = base + 360.0 * i / n
    target = carla.Location(center.x, center.y, center.z + 1.0)
    for attempt in range(40):
        loc, rot, fov = sample_pose(rng, center, role, azimuth)
        if any(loc.distance(c["loc"]) < 8.0 for c in others):
            continue
        if not line_of_sight(world, loc, target, margin=4.0):
            continue
        if not clear_near_lens(world, loc, rot, fov):
            continue
        need = args.min_visible if attempt < 25 else max(1, args.min_visible - 2)
        visible, too_close = analyse_view(world, loc, rot, fov, args.width, args.height, vehicles)
        if too_close or visible < need:
            continue
        return {"role": role, "loc": loc, "rot": rot, "fov": fov}
    return None


def build_layout(world, rng, center, n, args, vehicles):
    """n validated camera poses spread around the junction: (cams or None, rejection counts)."""
    base = rng.uniform(0.0, 360.0)
    cams = [None] * n
    rejected = defaultdict(int)
    for _ in range(args.rounds):
        pending = [i for i in range(n) if cams[i] is None]
        if not pending:
            break
        cands = {}
        for i in pending:
            others = [c for c in cams if c is not None] + list(cands.values())
            c = propose_pose(world, rng, center, i, n, base, others, args, vehicles)
            if c is not None:
                cands[i] = c
            else:
                rejected["no_pose_found"] += 1
        if not cands:
            continue
        idx = sorted(cands)
        for i, (ok, metrics, reason) in zip(idx, validate_poses(world, [cands[i] for i in idx])):
            cands[i]["quality"] = metrics
            if ok:
                cams[i] = cands[i]
            else:
                rejected[reason] += 1
    return (cams if all(c is not None for c in cams) else None), dict(rejected)


# ---------------------------------------------------------------- traffic

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


def run_ticks(world, n):
    for _ in range(max(0, int(n))):
        world.tick()


# ---------------------------------------------------------------- photos

def make_rgb_bp(lib, width, height, fov):
    bp = lib.find("sensor.camera.rgb")
    clean = {"image_size_x": width, "image_size_y": height, "fov": fov,
             "lens_k": 0.0, "lens_kcube": 0.0, "motion_blur_intensity": 0.0,
             "chromatic_aberration_intensity": 0.0, "bloom_intensity": 0.0, "lens_flare_intensity": 0.0,
             "gamma": 2.2}
    for name, value in clean.items():
        kit.set_attr(bp, name, value)
    return bp


def save_jpg(img, path, quality):
    arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)[:, :, :3][:, :, ::-1]
    Image.fromarray(np.ascontiguousarray(arr)).save(path, quality=quality, subsampling=0, optimize=True)


def photograph(world, cams, case_dir, args, vehicles):
    """Spawn one RGB camera per pose, wait for auto-exposure, take all photos on one tick."""
    os.makedirs(case_dir, exist_ok=True)
    lib = world.get_blueprint_library()
    sensors, queues = [], []
    try:
        for c in cams:
            s = world.spawn_actor(make_rgb_bp(lib, args.width, args.height, c["fov"]),
                                  carla.Transform(c["loc"], c["rot"]))
            q = queue.Queue()
            s.listen(q.put)
            sensors.append(s)
            queues.append(q)

        def step():
            frame = world.tick()
            return frame, [kit.get_frame(q, frame) for q in queues]

        for _ in range(int(args.settle / args.delta)):
            step()
        for _ in range(4):  # wait a little if a vehicle is in front of a lens or a street is empty right now
            stats = [analyse_view(world, c["loc"], c["rot"], c["fov"], args.width, args.height, vehicles) for c in cams]
            if all(vis >= 1 and not close for vis, close in stats):
                break
            for _ in range(int(2.0 / args.delta)):
                step()
        frame, images = step()
        sim_time = world.get_snapshot().timestamp.elapsed_seconds
        for i, img in enumerate(images, 1):
            save_jpg(img, os.path.join(case_dir, f"cam{i}.jpg"), args.jpeg_quality)
        stats = [analyse_view(world, c["loc"], c["rot"], c["fov"], args.width, args.height, vehicles) for c in cams]
        return frame, sim_time, [s_[0] for s_ in stats]
    finally:
        for s in sensors:
            s.stop()
            s.destroy()


# ---------------------------------------------------------------- main

def write_readme(out, args, n_cases, n_photos):
    text = f"""CARLA multi-camera photo dataset
================================
{n_cases} cases, {n_photos} photos. Map {args.town}, CARLA 0.9.16, seed {args.seed}.

Layout
  caseK/camJ.jpg   one photo per camera of case K; all photos of a case were taken on the same simulation tick
  manifest.json    per case: number of cameras, junction, weather, simulation time, and for every camera its
                   pose (location in m, rotation in degrees), field of view, distance to the junction centre,
                   height, and how many moving vehicles were in view (ray-cast estimate, parked cars not counted)

Cameras
  cam1 is the main camera: low (3-5.5 m) and oblique. The other cameras are spread around the junction
  at different heights (3-15 m), distances (12-42 m) and fields of view (70-100 degrees).
  Case K has ((K-1) mod 6) + 1 cameras, so cases cycle through 1, 2, 3, 4, 5 and 6 cameras.

Photos
  {args.width}x{args.height} JPEG (quality {args.jpeg_quality}), no lens distortion, no motion blur.

Regenerate
  python generate_cases.py --out output/dataset_v1 --cases {n_cases} --seed {args.seed}
"""
    with open(os.path.join(out, "README.txt"), "w", encoding="utf-8") as f:
        f.write(text)


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
    tm = client.get_trafficmanager(args.tm_port)
    out = args.out
    os.makedirs(out, exist_ok=True)
    manifest = {"carla": client.get_server_version(), "map": args.town, "seed": args.seed,
                "image": {"width": args.width, "height": args.height, "format": "jpeg", "quality": args.jpeg_quality},
                "main_camera": "cam1", "cases": [], "failed_cases": []}
    manifest_path = os.path.join(out, "manifest.json")
    if args.only_cases and os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["cases"] = [e for e in manifest["cases"] if e["case"] not in args.only_cases]
        manifest["failed_cases"] = [k for k in manifest["failed_cases"] if k not in args.only_cases]
    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = args.delta
        world.apply_settings(settings)
        tm.set_synchronous_mode(True)
        tm.set_random_device_seed(args.seed)
        world.set_pedestrians_seed(args.seed)

        junctions = list_junctions(world.get_map())
        plan = plan_cases(args.cases, len(junctions), args.cam_counts, args.junction_shift)
        if args.only_cases:
            plan = [item for item in plan if item["case"] in args.only_cases]
        by_junction = defaultdict(list)
        for item in plan:
            by_junction[item["junction"]].append(item)
        log(f"{len(plan)} cases over {len(by_junction)} of {len(junctions)} junctions")

        for j_index in sorted(by_junction):
            center = junctions[j_index]
            log(f"--- junction {j_index} at ({center.x:.0f}, {center.y:.0f}): cases {[c['case'] for c in by_junction[j_index]]}")
            vehicles = kit.spawn_vehicles(world, args.tm_port, center, args.vehicles, rng)
            walkers, controllers = spawn_walkers_near(world, center, args.walkers, args.walker_radius, rng)
            try:
                run_ticks(world, args.warmup / args.delta)
                for item in by_junction[j_index]:
                    k, n = item["case"], item["cameras"]
                    world.set_weather(getattr(carla.WeatherParameters, item["weather"], carla.WeatherParameters.ClearNoon))
                    run_ticks(world, 10)
                    done = False
                    for attempt in range(1, 4):
                        cams, rejected = build_layout(world, rng, center, n, args, vehicles)
                        if cams is None:
                            log(f"case {k}: no valid layout for {n} camera(s) (attempt {attempt}; rejected {rejected}), advancing traffic")
                            run_ticks(world, 5.0 / args.delta)
                            continue
                        shutil.rmtree(os.path.join(out, f"case{k}"), ignore_errors=True)
                        frame, sim_time, visible = photograph(world, cams, os.path.join(out, f"case{k}"), args, vehicles)
                        entry = {"case": k, "folder": f"case{k}", "n_cameras": n, "junction_index": j_index,
                                 "junction_center": xyz(center), "weather": item["weather"],
                                 "frame": frame, "sim_time_s": round(sim_time, 2), "cameras": []}
                        for i, (c, vis) in enumerate(zip(cams, visible), 1):
                            entry["cameras"].append({
                                "file": f"cam{i}.jpg", "role": c["role"], "location": xyz(c["loc"]),
                                "rotation": {"pitch": round(c["rot"].pitch, 1), "yaw": round(c["rot"].yaw, 1), "roll": 0.0},
                                "fov": c["fov"], "height_m": round(c["loc"].z - center.z, 1),
                                "view_check": c.get("quality"),
                                "distance_to_center_m": round(math.hypot(c["loc"].x - center.x, c["loc"].y - center.y), 1),
                                "vehicles_visible": vis})
                        manifest["cases"].append(entry)
                        log(f"case {k}: {n} camera(s), junction {j_index}, {item['weather']}, "
                            f"vehicles in view {visible}, rejected poses {rejected} -> case{k}/")
                        done = True
                        break
                    if not done:
                        manifest["failed_cases"].append(k)
                        log(f"case {k}: FAILED, skipped")
                    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
                        json.dump(manifest, f, indent=2)
                    run_ticks(world, args.gap / args.delta)
            finally:
                for c in controllers:
                    c.stop()
                client.apply_batch([carla.command.DestroyActor(a) for a in controllers + walkers + vehicles])
                world.tick()

        manifest["cases"].sort(key=lambda e: e["case"])
        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        n_photos = sum(e["n_cameras"] for e in manifest["cases"])
        write_readme(out, args, len(manifest["cases"]), n_photos)
        log(f"done: {len(manifest['cases'])} cases, {n_photos} photos in {out}"
            + (f", failed cases: {manifest['failed_cases']}" if manifest["failed_cases"] else ""))
    finally:
        tm.set_synchronous_mode(False)
        world.apply_settings(original)


if __name__ == "__main__":
    main()
