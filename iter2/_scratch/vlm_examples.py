import json
rows = [json.loads(l) for l in open("results/vlm/rw_both_fixes.jsonl", encoding="utf-8")]
rows = [r for r in rows if r.get("numbers", {}).get("score") is not None]
ok = [r for r in rows if r["numbers"]["score"] == 1]
bad = [r for r in rows if r["numbers"]["score"] == 0]
for label, sample in (("numbers preserved", ok[:1]), ("numbers NOT preserved", bad[:3])):
    for r in sample:
        t = " ".join(r["numbers"]["text"].split())
        print(f"case{r['case']} ({label}): {t[:520]}\n")
