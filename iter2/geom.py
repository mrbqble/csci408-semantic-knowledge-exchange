"""Pinhole geometry for the CARLA cameras (Unreal left-handed frame: x forward, y right, z up; roll = 0 in this dataset)."""
import math
import numpy as np

W_IMG, H_IMG = 1024, 576        # transmitted segmentation-map size (same 16:9 aspect as the 1920x1080 photo)


def basis(pitch_deg, yaw_deg, yaw_sign=1, pitch_sign=1):
    p, y = math.radians(pitch_sign * pitch_deg), math.radians(yaw_sign * yaw_deg)
    f = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    r = np.array([-math.sin(y), math.cos(y), 0.0])
    u = np.array([-math.sin(p) * math.cos(y), -math.sin(p) * math.sin(y), math.cos(p)])
    return f, r, u


def focal_px(fov_deg, width=W_IMG):
    return (width / 2) / math.tan(math.radians(fov_deg) / 2)


def project(cam, point, **kw):
    """World point -> pixel (u, v) in the W_IMG x H_IMG frame, or None when behind the camera."""
    f, r, u = basis(cam["pitch_deg"], cam["yaw_deg"], **kw)
    c = np.array([cam["location"]["x"], cam["location"]["y"], cam["location"]["z"]])
    v = np.asarray(point, float) - c
    zc = v @ f
    if zc <= 0.1:
        return None
    fp = focal_px(cam["fov"])
    return (W_IMG / 2 + fp * (v @ r) / zc, H_IMG / 2 - fp * (v @ u) / zc)


def ground_point(cam, px, py, z_ground=0.0, max_range=90.0, **kw):
    """Pixel -> world point on the plane z = z_ground, or None (above the horizon / too far)."""
    f, r, u = basis(cam["pitch_deg"], cam["yaw_deg"], **kw)
    fp = focal_px(cam["fov"])
    d = f + ((px - W_IMG / 2) / fp) * r - ((py - H_IMG / 2) / fp) * u
    c = np.array([cam["location"]["x"], cam["location"]["y"], cam["location"]["z"]])
    if d[2] >= -1e-3:
        return None
    t = (z_ground - c[2]) / d[2]
    if t <= 0 or t * np.linalg.norm(d) > max_range:
        return None
    return c + t * d


def depth_point(cam, px, py, depth, width=960, height=540):
    """Pixel of a render of size width x height plus its depth (distance along the optical axis, m) -> world point."""
    f, r, u = basis(cam["pitch_deg"], cam["yaw_deg"])
    fp = focal_px(cam["fov"], width)
    d = f + ((px - width / 2) / fp) * r - ((py - height / 2) / fp) * u
    c = np.array([cam["location"]["x"], cam["location"]["y"], cam["location"]["z"]])
    return c + depth * d
