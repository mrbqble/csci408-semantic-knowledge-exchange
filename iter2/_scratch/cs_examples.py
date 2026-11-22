import json
rows = [json.loads(l) for l in open("results/vlm/cs_authors.jsonl", encoding="utf-8")]
rows = [r for r in rows if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None]
bad = [r for r in rows if r["numbers"]["score"] == 0][:2]
for r in bad:
    print(r["case"], "|", " ".join(r["numbers"]["text"].split())[:420], "\n")
