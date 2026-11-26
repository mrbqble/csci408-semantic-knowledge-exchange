from pathlib import Path
p = Path("coordinator.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep("                 cn_scales=(1.0, 1.0), edge_thr=40):", "                 cn_scales=(1.0, 1.0), edge_thr=40, control_end=1.0, negative_prompt=None):")
rep("        self.cn_scales, self.edge_thr = tuple(cn_scales), edge_thr", "        self.control_end, self.negative_prompt = control_end, negative_prompt       # ControlNet off after this fraction of the steps; negative prompt\n        self.cn_scales, self.edge_thr = tuple(cn_scales), edge_thr")
rep("                        controlnet_conditioning_scale=list(self.cn_scales),\n",
    "                        controlnet_conditioning_scale=list(self.cn_scales), control_guidance_end=self.control_end,\n                        **({\"negative_prompt\": self.negative_prompt} if self.negative_prompt else {}),\n")
rep('    args = ap.parse_args()\n    if sys.platform',
    '    ap.add_argument("--steps", type=int, default=rx.STEPS, help="denoising steps (default: the authors\' receiver)")\n'
    '    ap.add_argument("--guidance", type=float, default=rx.GUIDANCE, help="classifier-free guidance scale")\n'
    '    ap.add_argument("--control-end", type=float, default=1.0, help="ControlNets act on this fraction of the steps (1.0 = all)")\n'
    '    ap.add_argument("--negative-prompt", default=None)\n'
    '    args = ap.parse_args()\n    if sys.platform')
rep("coord = Coordinator((w, h), args.palette, cn_scales=cn_scales, edge_thr=args.edge_thr)",
    "coord = Coordinator((w, h), args.palette, steps=args.steps, guidance=args.guidance, cn_scales=cn_scales, edge_thr=args.edge_thr,\n                        control_end=args.control_end, negative_prompt=args.negative_prompt)")
rep('"seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": donor,\n                 "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr}',
    '"seed": coord.seed, "steps": coord.steps, "guidance": coord.guidance, "donor_case": donor,\n                 "cn_scales": list(coord.cn_scales), "edge_thr": coord.edge_thr, "control_end": coord.control_end,\n                 "negative_prompt": coord.negative_prompt}')
p.write_text(t, encoding="utf-8"); print("coordinator patched")
