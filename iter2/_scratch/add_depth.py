from pathlib import Path
p = Path("geom.py"); t = p.read_text(encoding="utf-8")
if "def depth_point" not in t:
    t += '''

def depth_point(cam, px, py, depth, width=960, height=540):
    """Pixel of a render of size width x height plus its depth (distance along the optical axis, m) -> world point."""
    f, r, u = basis(cam["pitch_deg"], cam["yaw_deg"])
    fp = focal_px(cam["fov"], width)
    d = f + ((px - width / 2) / fp) * r - ((py - height / 2) / fp) * u
    c = np.array([cam["location"]["x"], cam["location"]["y"], cam["location"]["z"]])
    return c + depth * d
'''
    p.write_text(t, encoding="utf-8")
