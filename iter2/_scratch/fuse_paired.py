import json
from scipy.stats import binom
def load(r):
    out = {}
    for l in open(f"results/vlm/{r}.jsonl", encoding="utf-8"):
        x = json.loads(l)
        if x.get("numbers", {}).get("score") is not None and x.get("positions", {}).get("score") is not None:
            out[x["case"]] = x["numbers"]["score"] * x["positions"]["score"]
    return out
m, f, n = load("rw_paper_k1"), load("rw_fuse"), load("rw_fuse_noip")
cases = sorted(set(f) & set(n) & set(m))
def cmp(a, b, la, lb):
    win = [c for c in cases if a[c] > b[c]]; lose = [c for c in cases if a[c] < b[c]]
    p = 1.0 if not (win or lose) else min(1.0, 2 * binom.cdf(min(len(win), len(lose)), len(win) + len(lose), 0.5))
    print(f"{la} vs {lb}: better in {win}, worse in {lose}, McNemar p = {p:.2f}")
cmp(f, m, "fusion", "main"); cmp(f, n, "fusion", "control"); cmp(n, m, "control", "main")
print("main failed in:", [c for c in cases if m[c] == 0])
