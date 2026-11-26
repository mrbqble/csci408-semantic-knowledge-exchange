import json
from scipy.stats import binom
mapping = json.load(open("data/cs_cases/mapping.json"))
def load(f, key):
    out = {}
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
            out[key(r["case"])] = r
    return out
new = load("results/vlm/cs2_paper_seg1024.jsonl", lambda c: mapping[f"case{c}"])
old = load("results/vlm/cs_authors.jsonl", lambda c: c)
common = sorted(set(new) & set(old))
j = lambda r: r["numbers"]["score"] * r["positions"]["score"]
n = len(common)
for label, d in (("new payload (segmenter 1024x2048)", new), ("iteration 1 payload (384x384 default)", old)):
    k_num = sum(d[c]["numbers"]["score"] for c in common); k_pos = sum(d[c]["positions"]["score"] for c in common); k_j = sum(j(d[c]) for c in common)
    print(f"{label:40} n={n}  numbers {100*k_num/n:.1f}%  positions {100*k_pos/n:.1f}%  joint {100*k_j/n:.1f}%")
b = sum(1 for c in common if j(new[c]) > j(old[c])); a = sum(1 for c in common if j(old[c]) > j(new[c]))
p = 1.0 if a + b == 0 else min(1.0, 2 * binom.cdf(min(a, b), a + b, 0.5))
print(f"paired: new better {b}, old better {a}, McNemar p = {p:.3f}")
