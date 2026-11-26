from pathlib import Path
p = Path("coordinator.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old)
    t = t.replace(old, new)
rep('def __init__(self, size=GEN_SIZE, palette="cs", steps=rx.STEPS, guidance=rx.GUIDANCE, seed=rx.SEED):',
    'def __init__(self, size=GEN_SIZE, palette="cs", steps=rx.STEPS, guidance=rx.GUIDANCE, seed=rx.SEED,\n                 cn_scales=(1.0, 1.0), edge_thr=40):')
rep('self.steps, self.guidance, self.seed = steps, guidance, seed',
    'self.steps, self.guidance, self.seed = steps, guidance, seed\n        self.cn_scales, self.edge_thr = tuple(cn_scales), edge_thr      # ControlNet scales (canny, seg); edge binarisation')
rep('num_inference_steps=self.steps, guidance_scale=self.guidance,',
    'num_inference_steps=self.steps, guidance_scale=self.guidance,\n                        controlnet_conditioning_scale=list(self.cn_scales),')
rep('return edge_condition(p.edge, self.size), seg_condition(p.seg, self.size, self.palette)',
    'return edge_condition(p.edge, self.size, self.edge_thr), seg_condition(p.seg, self.size, self.palette)')
rep('    args = ap.parse_args()\n',
    '    ap.add_argument("--cn-scales", default="1.0,1.0", help="ControlNet conditioning scales canny,seg (the authors use 1,1)")\n    ap.add_argument("--edge-thr", type=int, default=40, help="threshold when binarising the area-resampled edge map")\n    args = ap.parse_args()\n')
rep('coord = Coordinator((w, h), args.palette)',
    'cn_scales = tuple(float(v) for v in args.cn_scales.split(","))\n    coord = Coordinator((w, h), args.palette, cn_scales=cn_scales, edge_thr=args.edge_thr)')
rep('"seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": donor}',
    '"seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": donor,\n                 "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr}')
rep('"timestamp": p.timestamp, "size": [w, h], "palette": args.palette}, indent=1))',
    '"timestamp": p.timestamp, "size": [w, h], "palette": args.palette,\n                         "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr}, indent=1))')
p.write_text(t, encoding="utf-8")
print("patched")
