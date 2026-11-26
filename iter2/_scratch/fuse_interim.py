import json
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = (x["numbers"]["score"], x["positions"]["score"])
    return out
runs = {r: load(r) for r in ("rw_paper_k1", "rw_fuse", "rw_fuse_noip")}
common = sorted(set.intersection(*(set(v) for v in runs.values())))
print("common cases:", len(common), common)
for r, d in runs.items():
    n = sum(d[c][0] for c in common); p = sum(d[c][1] for c in common); j = sum(d[c][0] * d[c][1] for c in common)
    print(f"{r:14} numbers {n}/{len(common)}  positions {p}/{len(common)}  joint {j}/{len(common)}")
