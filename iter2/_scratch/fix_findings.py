from pathlib import Path
p = Path("FINDINGS.md"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60])
    t = t.replace(old, new)
rep("On v2, 112 cases, cam1, vehicles the detector finds on the original photo, by box side at 1024x576:",
    "On v2, 112 cases, cam1, vehicles the detector finds on the original photo, by box side at 1024x576 (receiver = `prompt_only`):")
rep("mostly the small and distant ones (48% of vehicle detections and 90% of people are under 48 px). People follow the same pattern (24-case pilot, single view: recall 7% under 24 px, 20% at 24-48 px, 64% at 48-120 px, 100% over 120 px).",
    "mostly the small and distant ones: 48% of the vehicle detections are under 48 px. People follow the same pattern but more strongly (24-case pilot, single view: 90% of the person detections are under 48 px; recall 7% under 24 px, 20% at 24-48 px, 64% at 48-120 px, 100% over 120 px).")
rep("against at most 0.28 and 0.15 for any Rec1-frame method", "against at most 0.28 and 0.16 for any Rec1-frame method")
rep("(bounding-box centre vs ground-contact point; 16% of vehicle ground-truth positions in the v3 smoke test came from depth backprojection because parked cars are not actors). Two ground-truth actors with NaN positions were also replaced by depth backprojection.",
    "(bounding-box centre vs ground-contact point). Parked cars are not actors, so their ground-truth position comes from depth backprojection (16 of 98 car instances in the 3-case v3 smoke test), and two ground-truth actors with NaN positions in the full set were handled the same way.")
p.write_text(t, encoding="utf-8"); print("ok")
