from pathlib import Path
def patch(path, pairs):
    p = Path(path); t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert t.count(old) == 1, (path, t.count(old), old[:70]); t = t.replace(old, new)
    p.write_text(t, encoding="utf-8"); print("patched", path)
patch("payloads.py", [
 ('    ap.add_argument("--device", default="auto")\n',
  '    ap.add_argument("--device", default="auto")\n    ap.add_argument("--work-size", default="", help="WxH, e.g. 896x512: send the segmentation map at this size and compute the edge map on the photo resized to it "\n                    "(the receiver models\' working resolution); default: map at 1024 wide, edges at full resolution")\n'),
 ('    seg, cap = ms.Segmenter(device, input_size=SEG_INPUT), ms.Captioner(device)\n',
  '    seg, cap = ms.Segmenter(device, input_size=SEG_INPUT), ms.Captioner(device)\n    work = tuple(int(v) for v in args.work_size.lower().split("x")) if args.work_size else None\n'),
 ('            t = time.perf_counter(); seg_b = ms.encode_segmentation(labels, size=seg_tx_size(rgb.width, rgb.height)); row["seg_encode_ms"] = 1e3 * (time.perf_counter() - t)\n            t = time.perf_counter(); edge_b = ms.encode_edges(ms.canny_edges(rgb)); row["edge_ms"] = 1e3 * (time.perf_counter() - t)\n',
  '            seg_size = work or seg_tx_size(rgb.width, rgb.height)\n            edge_src = rgb.resize(work, Image.LANCZOS) if work else rgb\n            row["work_size"] = list(work) if work else None\n            t = time.perf_counter(); seg_b = ms.encode_segmentation(labels, size=seg_size); row["seg_encode_ms"] = 1e3 * (time.perf_counter() - t)\n            t = time.perf_counter(); edge_b = ms.encode_edges(ms.canny_edges(edge_src)); row["edge_ms"] = 1e3 * (time.perf_counter() - t)\n'),
])
patch("gt_eval.py", [
 ('        sc = 1024 / row["master_size"][0]\n        det = [[v * sc for v in d["bbox_master_px"]] for d in row["detections"] if d["class"] in VEH]\n',
  '        sx, sy = 1024 / row["master_size"][0], 576 / row["master_size"][1]\n        det = [[d["bbox_master_px"][0] * sx, d["bbox_master_px"][1] * sy, d["bbox_master_px"][2] * sx, d["bbox_master_px"][3] * sy]\n               for d in row["detections"] if d["class"] in VEH]\n'),
])
patch("compare_runs.py", [
 ('        ob = vboxes(json.loads((args.a / "oracle_gen" / f"case{c}.json").read_text()))\n        for name, f in ((na, fa), (nb, fb)):\n            row = json.loads(f.read_text())\n            vb = vboxes(row)\n',
  '        for name, f, ana in ((na, fa, args.a), (nb, fb, args.b)):\n            row = json.loads(f.read_text())\n            sx, sy = 1024 / row["master_size"][0], 576 / row["master_size"][1]   # both runs in the 1024x576 frame\n            to = lambda bs: [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in bs]\n            ob = to(vboxes(json.loads((ana / "oracle_gen" / f"case{c}.json").read_text())))   # each run against its own oracle\n            vb = to(vboxes(row))\n'),
])
