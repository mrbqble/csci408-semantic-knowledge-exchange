import json
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = x["numbers"]["score"] * x["positions"]["score"]
    return out
for ds in ("v3", "rw"):
    m, f = load(f"{ds}_paper_k1"), load(f"{ds}_fuse")
    fixed = sorted(c for c in f if f[c] == 1 and m.get(c) == 0); broken = sorted(c for c in f if f[c] == 0 and m.get(c) == 1)
    print(ds, "fixed:", fixed[:8], "broken:", broken[:6])
