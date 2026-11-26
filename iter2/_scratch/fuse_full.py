import json
from scipy.stats import binom
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = (x["numbers"]["score"], x["positions"]["score"])
    return out
def mcn(a, b, cases):
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))
for ds in ("rw", "v3"):
    R = {k: load(f"{ds}_{k}") for k in ("paper_k1", "paper_multi", "fuse", "fuse_noip")}
    cases = sorted(set.intersection(*(set(v) for v in R.values())))
    n = len(cases)
    print(f"=== {ds}: {n} cases")
    J = {k: {c: v[c][0] * v[c][1] for c in cases} for k, v in R.items()}
    for k, v in R.items():
        print(f"  {k:12} numbers {100*sum(v[c][0] for c in cases)/n:5.1f}%  positions {100*sum(v[c][1] for c in cases)/n:5.1f}%  joint {100*sum(J[k].values())/n:5.1f}%")
    for a, b in (("fuse", "paper_k1"), ("fuse", "fuse_noip"), ("fuse_noip", "paper_k1"), ("fuse", "paper_multi")):
        w, l, p = mcn(J[a], J[b], cases)
        print(f"  {a} vs {b}: {100*(w-l)/n:+.1f} pts  (better {w}, worse {l}, p = {p:.3f})")
    fail = [c for c in cases if J["paper_k1"][c] == 0]; ok = [c for c in cases if J["paper_k1"][c] == 1]
    for k in ("fuse", "fuse_noip"):
        fixed = sum(J[k][c] for c in fail); broken = sum(1 - J[k][c] for c in ok)
        print(f"  {k}: fixes {fixed}/{len(fail)} cases where the main reconstruction fails, breaks {broken}/{len(ok)} where it passes")
