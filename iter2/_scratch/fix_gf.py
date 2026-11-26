from pathlib import Path
p = Path("geofuse.py"); t = p.read_text(encoding="utf-8")
old = '"class": ids[max(votes, key=votes.get)], "world_xy_m"'
assert t.count(old) == 1
p.write_text(t.replace(old, '"class": max(votes, key=votes.get), "world_xy_m"'), encoding="utf-8")
