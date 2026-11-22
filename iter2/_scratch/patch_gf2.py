from pathlib import Path
p = Path("geofuse.py"); t = p.read_text(encoding="utf-8")
def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (t.count(old), old)
    t = t.replace(old, new)
rep("def associate(per_cam, gate):",
    'def group_mask(seg_rgb, ids):\n    a = np.asarray(seg_rgb).astype(np.int64)\n    key = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]\n    return np.isin(key, [KEY[t] for t in ids]).astype(np.uint8)\n\n\ndef associate(per_cam, gate):')
rep('res = {g: {k: [] for k in ("F0", "F2", "F3")} for g in GROUPS}', 'res = {g: {k: [] for k in ("F0", "F2", "F3", "F4", "F5")} for g in GROUPS}')
rep("            extra, extra2 = 0, 0\n", "            extra, extra2, extra4, extra5 = 0, 0, 0, 0\n            ref_mask = cv2.dilate(group_mask(segs[0], ids), np.ones((5, 5), np.uint8))\n")
rep("                if not has_ref and in_ref:\n                    extra += 1\n                    extra2 += int(len({ci for ci, _ in o[\"members\"]}) >= 2)\n",
    "                in_mask = bool(in_ref and ref_mask[int(px[1]), int(px[0])] > 0)\n                two = len({ci for ci, _ in o[\"members\"]}) >= 2\n                if not has_ref and in_ref:\n                    extra += 1\n                    extra2 += int(two)\n                if not has_ref and in_mask:\n                    extra4 += 1\n                    extra5 += int(two)\n")
rep('for k, v in (("F0", f0), ("F2", f0 + extra), ("F3", f0 + extra2)):', 'for k, v in (("F0", f0), ("F2", f0 + extra), ("F3", f0 + extra2), ("F4", f0 + extra4), ("F5", f0 + extra5)):')
rep('"F3": f0 + extra2, "gt": gt', '"F3": f0 + extra2, "F4": f0 + extra4, "F5": f0 + extra5, "gt": gt')
p.write_text(t, encoding="utf-8")
print("patched")
