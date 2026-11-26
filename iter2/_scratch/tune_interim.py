import json
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = x["numbers"]["score"] * x["positions"]["score"]
    return out
cands = {"st0.5/ip1.0": "fuseF", "st0.3": "fuseF_st0.3", "st0.4": "fuseF_st0.4", "st0.6": "fuseF_st0.6", "ip0.5": "fuseF_ip0.5", "ip0.75": "fuseF_ip0.75"}
D = {k: load(f"v3_{v}") for k, v in cands.items()}
common = [c for c in range(1, 57) if all(c in d for d in D.values())]
print(f"CARLA tuning half, interim ({len(common)} of 56 cases judged in every setting):", ", ".join(f"{k} {sum(D[k][c] for c in common)}" for k in cands))
