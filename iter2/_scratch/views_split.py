import json
import paths
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = x["numbers"]["score"] * x["positions"]["score"]
    return out
m = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
ncam = {int(str(c["case"]).replace("case", "")): c["n_cameras"] for c in m["cases"]}
F, H, S = load("v3_fuseF"), load("v3_fuse"), load("v3_paper_k1")
print("CARLA by number of cameras (supporting views = cameras - 1): joint successes")
print(f"{'cameras':>8} {'n':>4} {'single':>7} {'896 supports':>13} {'full-res supports':>18} {'full - 896':>11}")
for k in sorted(set(ncam.values())):
    cs = [c for c in F if ncam.get(c) == k and c in H and c in S]
    if cs:
        s, h, f = sum(S[c] for c in cs), sum(H[c] for c in cs), sum(F[c] for c in cs)
        print(f"{k:>8} {len(cs):>4} {s:>7} {h:>13} {f:>18} {f - h:>+11}")
R = {"F": load("rw_fuseF"), "H": load("rw_fuse")}
print("real-world (3 phones, 2 supporting views):", "896:", sum(R["H"].values()), "full-res:", sum(R["F"].values()), "of", len(R["F"]))
