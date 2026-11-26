from pathlib import Path
p = Path("geofuse.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)
rep('    ap.add_argument("--cases", default="1-112")\n',
    '    ap.add_argument("--cases", default="1-112")\n    ap.add_argument("--manifest", type=Path, default=MANIFEST)\n    ap.add_argument("--payloads", type=Path, default=PAYLOADS)\n')
rep("manifest = json.loads(MANIFEST.read_text())", "manifest = json.loads(args.manifest.read_text())")
rep('Image.open(PAYLOADS / case["folder"]', 'Image.open(args.payloads / case["folder"]')
p.write_text(t, encoding="utf-8"); print("geofuse parametrised")
