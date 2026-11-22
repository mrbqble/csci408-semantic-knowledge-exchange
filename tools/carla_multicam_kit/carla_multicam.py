#!/usr/bin/env python3
"""
Синхронный сбор кадров одного перекрёстка с N камер в CARLA.

Возможности:
  - N камер по кругу вокруг перекрёстка ИЛИ каждая камера вручную через JSON-конфиг
  - настройка высоты, расстояния, наклона (pitch), поворота (yaw), крена (roll), FOV
  - типы камер: rgb, depth, semantic, instance (можно несколько одновременно)
  - качество: разрешение, экспозиция, гамма, motion blur, дисторсия объектива,
    хроматическая аберрация, JPEG-сжатие, шум, ч/б (ночной ИК-режим)
  - пресеты: clean (чистая картинка), cctv (как с уличной камеры), hd
  - сохранение раз в --interval секунд симуляции, все камеры в один и тот же момент

Структура выхода:
  out/
    cameras.json                     # позиции, углы и интринсики камер
    snap_000001/
      cam_01_rgb.jpg, cam_01_depth.png, cam_01_semantic.png, ...
      meta.json                      # время симуляции, машины, пешеходы
    snap_000002/ ...

Примеры:
  python carla_multicam.py --cameras 3 --interval 10 --snapshots 100
  python carla_multicam.py --cameras 4 --cam-height 10 --pitch -35 --preset cctv
  python carla_multicam.py --camera-config cameras_example.json --sensors rgb,semantic,depth

Зависимости: pip install carla numpy pillow
"""

import argparse
import json
import math
import os
import queue
import random

import carla
import numpy as np
from PIL import Image


# ---------------------------------------------------------------- пресеты качества

PRESETS = {
    # Чистая картинка без эффектов: для обучения детекторов на «идеальных» данных
    "clean": dict(width=1920, height=1080, fov=90, motion_blur=0.0, chromatic=0.0,
                  lens_k=0.0, lens_kcube=0.0, bloom=0.0, lens_flare=0.0,
                  noise=0.0, fmt="png", jpeg_quality=95, gamma=2.2),
    # Похоже на уличную камеру наблюдения: шире угол, дисторсия, шум, сжатие
    "cctv": dict(width=1280, height=720, fov=100, motion_blur=0.25, chromatic=0.3,
                 lens_k=-0.6, lens_kcube=0.0, bloom=0.1, lens_flare=0.0,
                 noise=6.0, fmt="jpg", jpeg_quality=55, gamma=2.2),
    # Высокое разрешение, лёгкие реалистичные эффекты
    "hd": dict(width=2560, height=1440, fov=90, motion_blur=0.1, chromatic=0.1,
               lens_k=-0.2, lens_kcube=0.0, bloom=0.3, lens_flare=0.1,
               noise=1.5, fmt="jpg", jpeg_quality=92, gamma=2.2),
}

SENSOR_BP = {
    "rgb": "sensor.camera.rgb",
    "depth": "sensor.camera.depth",
    "semantic": "sensor.camera.semantic_segmentation",
    "instance": "sensor.camera.instance_segmentation",
}


def parse_args():
    p = argparse.ArgumentParser(description="Multi-camera intersection capture for CARLA")
    g = p.add_argument_group("сервер и карта")
    g.add_argument("--host", default="localhost")
    g.add_argument("--port", type=int, default=2000)
    g.add_argument("--tm-port", type=int, default=8000)
    g.add_argument("--town", default=None, help="Например Town10HD_Opt. Если не задано, текущая карта")
    g.add_argument("--junction-index", type=int, default=0, help="Какой перекрёсток карты взять")

    g = p.add_argument_group("запись")
    g.add_argument("--interval", type=float, default=10.0, help="Интервал сохранения, секунды симуляции")
    g.add_argument("--snapshots", type=int, default=None, help="Сколько снимков сделать (приоритет над --duration)")
    g.add_argument("--duration", type=float, default=600.0, help="Длительность записи, секунды симуляции")
    g.add_argument("--delta", type=float, default=0.05, help="Шаг симуляции, с (0.05 = 20 FPS)")
    g.add_argument("--out", default="out")

    g = p.add_argument_group("расстановка камер")
    g.add_argument("--cameras", type=int, default=3, help="Количество камер (игнорируется при --camera-config)")
    g.add_argument("--camera-config", default=None, help="JSON с настройками каждой камеры отдельно")
    g.add_argument("--radius", type=float, default=25.0, help="Расстояние от центра перекрёстка, м")
    g.add_argument("--cam-height", type=float, default=7.0, help="Высота камер над дорогой, м")
    g.add_argument("--start-angle", type=float, default=45.0, help="Угол первой камеры на круге (45 = из угла)")
    g.add_argument("--pitch", type=float, default=None,
                   help="Наклон вниз в градусах (например -30). По умолчанию камера смотрит точно в центр")
    g.add_argument("--yaw-offset", type=float, default=0.0, help="Доворот влево/вправо от центра, градусы")
    g.add_argument("--roll", type=float, default=0.0, help="Крен (завал горизонта), градусы")
    g.add_argument("--aim-height", type=float, default=0.0,
                   help="На какой высоте над центром точка прицеливания, м")

    g = p.add_argument_group("тип и качество изображения")
    g.add_argument("--sensors", default="rgb", help="Через запятую: rgb,depth,semantic,instance")
    g.add_argument("--colorize", action="store_true",
                   help="Сохранять depth/semantic в цветном виде для просмотра (иначе сырые данные для обучения)")
    g.add_argument("--preset", choices=PRESETS.keys(), default="clean")
    g.add_argument("--width", type=int, default=None)
    g.add_argument("--height", type=int, default=None)
    g.add_argument("--fov", type=float, default=None)
    g.add_argument("--exposure", choices=["histogram", "manual"], default="histogram",
                   help="histogram = автоэкспозиция, manual = задаётся iso/shutter/fstop")
    g.add_argument("--iso", type=float, default=100.0)
    g.add_argument("--shutter", type=float, default=200.0, help="Выдержка 1/N секунды")
    g.add_argument("--fstop", type=float, default=1.4)
    g.add_argument("--exposure-bias", type=float, default=0.0, help="Ярче (+) / темнее (-)")
    g.add_argument("--gamma", type=float, default=None)
    g.add_argument("--motion-blur", type=float, default=None, help="0..1")
    g.add_argument("--chromatic", type=float, default=None, help="Хроматическая аберрация, 0..1")
    g.add_argument("--lens-k", type=float, default=None, help="Дисторсия объектива (<0 бочка/fisheye)")
    g.add_argument("--lens-kcube", type=float, default=None)
    g.add_argument("--bloom", type=float, default=None)
    g.add_argument("--lens-flare", type=float, default=None)
    g.add_argument("--noise", type=float, default=None, help="Шум сенсора, сигма в уровнях 0..255")
    g.add_argument("--format", dest="fmt", choices=["png", "jpg"], default=None)
    g.add_argument("--jpeg-quality", type=int, default=None, help="1..100, меньше = сильнее артефакты")
    g.add_argument("--grayscale", action="store_true", help="Ч/б картинка (имитация ночного ИК-режима)")

    g = p.add_argument_group("сцена")
    g.add_argument("--vehicles", type=int, default=40)
    g.add_argument("--walkers", type=int, default=30)
    g.add_argument("--weather", default="ClearNoon",
                   help="ClearNoon, CloudyNoon, WetNoon, HardRainNoon, ClearSunset, ClearNight ...")
    g.add_argument("--seed", type=int, default=42)

    args = p.parse_args()
    # Значения пресета подставляются туда, где параметр не задан явно
    for k, v in PRESETS[args.preset].items():
        if getattr(args, k) is None:
            setattr(args, k, v)
    args.sensors = [s.strip() for s in args.sensors.split(",") if s.strip()]
    for s in args.sensors:
        if s not in SENSOR_BP:
            p.error(f"Неизвестный тип камеры: {s}. Доступно: {', '.join(SENSOR_BP)}")
    return args


# ---------------------------------------------------------------- геометрия

def find_junction(world_map, index):
    junctions = {}
    for wp in world_map.generate_waypoints(5.0):
        if wp.is_junction:
            j = wp.get_junction()
            junctions[j.id] = j
    if not junctions:
        raise RuntimeError("На карте не найдено перекрёстков")
    ids = sorted(junctions)
    return junctions[ids[index % len(ids)]], len(ids)


def look_at(cam_loc, target):
    dx, dy, dz = target.x - cam_loc.x, target.y - cam_loc.y, target.z - cam_loc.z
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def build_camera_specs(args, center):
    """Список камер: позиция + углы + оптика. Из JSON-конфига или по кругу."""
    if args.camera_config:
        with open(args.camera_config, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = [{"angle": args.start_angle + 360.0 * i / args.cameras} for i in range(args.cameras)]

    specs = []
    for i, c in enumerate(raw, start=1):
        height = c.get("height", args.cam_height)
        if "x" in c and "y" in c:  # координаты относительно центра перекрёстка, м
            x, y = center.x + c["x"], center.y + c["y"]
        else:
            a = math.radians(c.get("angle", args.start_angle + 360.0 * (i - 1) / len(raw)))
            r = c.get("radius", args.radius)
            x, y = center.x + r * math.cos(a), center.y + r * math.sin(a)
        loc = carla.Location(x=x, y=y, z=center.z + height)

        target = carla.Location(x=center.x, y=center.y, z=center.z + c.get("aim_height", args.aim_height))
        auto_pitch, auto_yaw = look_at(loc, target)
        pitch = c.get("pitch", args.pitch if args.pitch is not None else auto_pitch)
        yaw = c["yaw"] if "yaw" in c else auto_yaw + c.get("yaw_offset", args.yaw_offset)
        roll = c.get("roll", args.roll)

        specs.append({
            "name": c.get("name", f"cam_{i:02d}"),
            "transform": carla.Transform(loc, carla.Rotation(pitch=pitch, yaw=yaw, roll=roll)),
            "fov": c.get("fov", args.fov),
            "width": c.get("width", args.width),
            "height": c.get("height_px", args.height),
        })
    return specs


def intrinsics(width, height, fov):
    f = width / (2.0 * math.tan(math.radians(fov) / 2.0))
    return [[f, 0.0, width / 2.0], [0.0, f, height / 2.0], [0.0, 0.0, 1.0]]


def transform_to_dict(t):
    return {
        "location": {"x": t.location.x, "y": t.location.y, "z": t.location.z},
        "rotation": {"pitch": t.rotation.pitch, "yaw": t.rotation.yaw, "roll": t.rotation.roll},
    }


# ---------------------------------------------------------------- сенсоры

def set_attr(bp, name, value):
    """Ставит атрибут, только если он есть в этой версии CARLA."""
    if bp.has_attribute(name):
        bp.set_attribute(name, str(value))


def make_blueprint(lib, sensor, spec, args):
    bp = lib.find(SENSOR_BP[sensor])
    set_attr(bp, "image_size_x", spec["width"])
    set_attr(bp, "image_size_y", spec["height"])
    set_attr(bp, "fov", spec["fov"])
    # Дисторсия есть у всех камер, чтобы маски совпадали с RGB пиксель в пиксель
    set_attr(bp, "lens_k", args.lens_k)
    set_attr(bp, "lens_kcube", args.lens_kcube)
    if sensor == "rgb":
        set_attr(bp, "exposure_mode", args.exposure)
        set_attr(bp, "exposure_compensation", args.exposure_bias)
        set_attr(bp, "iso", args.iso)
        set_attr(bp, "shutter_speed", args.shutter)
        set_attr(bp, "fstop", args.fstop)
        set_attr(bp, "gamma", args.gamma)
        set_attr(bp, "motion_blur_intensity", args.motion_blur)
        set_attr(bp, "chromatic_aberration_intensity", args.chromatic)
        set_attr(bp, "bloom_intensity", args.bloom)
        set_attr(bp, "lens_flare_intensity", args.lens_flare)
    return bp


def get_frame(q, frame, timeout=10.0):
    """Достаёт из очереди кадр, соответствующий нужному тику симуляции."""
    while True:
        img = q.get(timeout=timeout)
        if img.frame == frame:
            return img
        if img.frame > frame:
            raise RuntimeError(f"Пропущен кадр {frame} (получен {img.frame})")


def save_rgb(img, path_noext, args, np_rng):
    arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)
    arr = arr[:, :, :3][:, :, ::-1].astype(np.float32)  # BGRA -> RGB
    if args.noise > 0:
        arr += np_rng.normal(0.0, args.noise, arr.shape)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if args.grayscale:
        im = im.convert("L")
    if args.fmt == "jpg":
        im.save(path_noext + ".jpg", quality=args.jpeg_quality)
    else:
        im.save(path_noext + ".png")


def save_other(img, sensor, path_noext, args):
    if args.colorize and sensor == "depth":
        img.save_to_disk(path_noext + ".png", carla.ColorConverter.LogarithmicDepth)
    elif args.colorize and sensor == "semantic":
        img.save_to_disk(path_noext + ".png", carla.ColorConverter.CityScapesPalette)
    else:
        # Сырые данные: semantic -> id класса в R-канале,
        # depth -> глубина закодирована в RGB, instance -> класс в R, id объекта в G+B
        img.save_to_disk(path_noext + ".png", carla.ColorConverter.Raw)


# ---------------------------------------------------------------- трафик

def spawn_vehicles(world, tm_port, center, count, rng):
    bps = [bp for bp in world.get_blueprint_library().filter("vehicle.*")
           if int(bp.get_attribute("number_of_wheels")) == 4]
    points = sorted(world.get_map().get_spawn_points(), key=lambda t: t.location.distance(center))
    vehicles = []
    for t in points:
        if len(vehicles) >= count:
            break
        bp = rng.choice(bps)
        if bp.has_attribute("color"):
            bp.set_attribute("color", rng.choice(bp.get_attribute("color").recommended_values))
        v = world.try_spawn_actor(bp, t)
        if v:
            v.set_autopilot(True, tm_port)
            vehicles.append(v)
    return vehicles


def spawn_walkers(world, count, rng):
    lib = world.get_blueprint_library()
    walker_bps = lib.filter("walker.pedestrian.*")
    ctrl_bp = lib.find("controller.ai.walker")
    walkers, controllers = [], []
    for _ in range(count * 2):
        if len(walkers) >= count:
            break
        loc = world.get_random_location_from_navigation()
        if loc is None:
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
        c.go_to_location(world.get_random_location_from_navigation())
        c.set_max_speed(1.0 + rng.random() * 0.6)
    return walkers, controllers


def actor_info(a):
    t = a.get_transform()
    bb = a.bounding_box
    return {
        "id": a.id,
        "type": a.type_id,
        **transform_to_dict(t),
        "bbox_extent": {"x": bb.extent.x, "y": bb.extent.y, "z": bb.extent.z},
        "bbox_center": {"x": bb.location.x, "y": bb.location.y, "z": bb.location.z},
    }


# ---------------------------------------------------------------- main

def main():
    args = parse_args()
    rng = random.Random(args.seed)
    np_rng = np.random.default_rng(args.seed)

    client = carla.Client(args.host, args.port)
    client.set_timeout(30.0)
    world = client.load_world(args.town) if args.town else client.get_world()

    original_settings = world.get_settings()
    tm = client.get_trafficmanager(args.tm_port)
    tm.set_random_device_seed(args.seed)

    sensors_actors, vehicles, walkers, controllers = [], [], [], []
    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = args.delta
        world.apply_settings(settings)
        tm.set_synchronous_mode(True)

        world.set_weather(getattr(carla.WeatherParameters, args.weather, carla.WeatherParameters.ClearNoon))

        junction, n_junctions = find_junction(world.get_map(), args.junction_index)
        center = junction.bounding_box.location
        print(f"Перекрёсток #{args.junction_index % n_junctions} из {n_junctions}, центр {center}")

        os.makedirs(args.out, exist_ok=True)
        lib = world.get_blueprint_library()
        specs = build_camera_specs(args, center)

        # Для каждой позиции камеры ставим все выбранные типы сенсоров в одну и ту же точку
        streams = []  # (имя камеры, тип сенсора, очередь)
        cam_meta = []
        for spec in specs:
            for sensor in args.sensors:
                actor = world.spawn_actor(make_blueprint(lib, sensor, spec, args), spec["transform"])
                q = queue.Queue()
                actor.listen(q.put)
                sensors_actors.append(actor)
                streams.append((spec["name"], sensor, q))
            cam_meta.append({"name": spec["name"], **transform_to_dict(spec["transform"]),
                             "fov": spec["fov"], "width": spec["width"], "height": spec["height"],
                             "intrinsics": intrinsics(spec["width"], spec["height"], spec["fov"]),
                             "note": "intrinsics без учёта lens_k дисторсии"})

        with open(os.path.join(args.out, "cameras.json"), "w", encoding="utf-8") as f:
            json.dump({"junction_center": {"x": center.x, "y": center.y, "z": center.z},
                       "sensors": args.sensors, "preset": args.preset,
                       "cameras": cam_meta}, f, indent=2, ensure_ascii=False)

        vehicles = spawn_vehicles(world, args.tm_port, center, args.vehicles, rng)
        walkers, controllers = spawn_walkers(world, args.walkers, rng)
        print(f"Машин: {len(vehicles)}, пешеходов: {len(walkers)}, "
              f"камер: {len(specs)}, сенсоров на камеру: {len(args.sensors)}")

        # Прогрев: трафик разъезжается, автоэкспозиция успевает подстроиться
        for _ in range(int(5.0 / args.delta)):
            frame = world.tick()
            for _, _, q in streams:
                get_frame(q, frame)

        ticks_per_save = max(1, round(args.interval / args.delta))
        total_ticks = args.snapshots * ticks_per_save if args.snapshots else int(args.duration / args.delta)

        snap = 0
        for tick in range(1, total_ticks + 1):
            frame = world.tick()
            images = [(name, sensor, get_frame(q, frame)) for name, sensor, q in streams]
            if tick % ticks_per_save != 0:
                continue

            snap += 1
            snap_dir = os.path.join(args.out, f"snap_{snap:06d}")
            os.makedirs(snap_dir, exist_ok=True)
            for name, sensor, img in images:
                path = os.path.join(snap_dir, f"{name}_{sensor}")
                if sensor == "rgb":
                    save_rgb(img, path, args, np_rng)
                else:
                    save_other(img, sensor, path, args)

            snapshot = world.get_snapshot()
            meta = {
                "snapshot": snap,
                "frame": frame,
                "sim_time_s": snapshot.timestamp.elapsed_seconds,
                "weather": args.weather,
                "vehicles": [actor_info(v) for v in vehicles if v.is_alive],
                "walkers": [actor_info(w) for w in walkers if w.is_alive],
            }
            with open(os.path.join(snap_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            print(f"[{snap}] t={meta['sim_time_s']:.1f}s -> {snap_dir}")

        print(f"Готово: {snap} снимков x {len(specs)} камер в {args.out}/")

    finally:
        for c in controllers:
            c.stop()
        for s in sensors_actors:
            s.stop()
        client.apply_batch([carla.command.DestroyActor(a)
                            for a in sensors_actors + controllers + walkers + vehicles])
        tm.set_synchronous_mode(False)
        world.apply_settings(original_settings)


if __name__ == "__main__":
    main()
