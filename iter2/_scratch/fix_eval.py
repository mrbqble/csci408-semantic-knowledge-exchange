from pathlib import Path
p = Path("eval_union.py"); t = p.read_text(encoding="utf-8")
old = '            if inst.get("world"):\n                d["xy"] = (inst["world"]["x"], inst["world"]["y"])\n'
assert t.count(old) == 1
new = '            w = inst.get("world")\n            if w and np.isfinite(w["x"]) and np.isfinite(w["y"]):       # a few actors report NaN transforms: use depth instead\n                d["xy"] = (w["x"], w["y"])\n'
t = t.replace(old, new)
p.write_text(t, encoding="utf-8"); print("patched")
