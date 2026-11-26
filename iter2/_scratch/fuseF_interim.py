import json
from scipy.stats import binom
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = x["numbers"]["score"] * x["positions"]["score"]
    return out
def mcn(a, b, cases):
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))
for ds in ("rw", "v3"):
    R = {k: load(f"{ds}_{k}") for k in ("paper_k1", "fuse", "fuseF")}
    cases = sorted(set.intersection(*(set(v) for v in R.values())))
    n = len(cases)
    print(f"=== {ds}: {n} cases in common")
    for k in R:
        print(f"  {k:9} joint {100*sum(R[k][c] for c in cases)/n:5.1f}%")
    for a, b in (("fuseF", "fuse"), ("fuseF", "paper_k1"), ("fuse", "paper_k1")):
        w, l, p = mcn(R[a], R[b], cases)
        print(f"  {a} vs {b}: {100*(w-l)/n:+.1f} pts (better {w}, worse {l}, p = {p:.3f})")
