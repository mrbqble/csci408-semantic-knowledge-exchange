import json, subprocess, collections
R = "mrbqble/csci408-semantic-knowledge-exchange"
def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, encoding="utf-8"); return json.loads(r.stdout) if r.stdout.strip() else r.stderr
iss = [i for i in gh("api", f"repos/{R}/issues?state=all&per_page=100") if "pull_request" not in i]
titles = collections.Counter(i["title"] for i in iss)
print("issues:", len(iss), "| duplicates:", [t for t, c in titles.items() if c > 1])
print("closed:", sum(i["state"] == "closed" for i in iss), "| open:", sum(i["state"] == "open" for i in iss))
per = collections.Counter(a["login"] for i in iss for a in i["assignees"])
print("assignments per login:", dict(per))
print("unassigned:", [f"#{i['number']} {i['title']}" for i in iss if not i["assignees"]])
q = 'query{ user(login:"mrbqble"){ projectV2(number:2){ shortDescription views(first:10){ nodes{ name layout } } items(first:100){ totalCount nodes{ content{ ... on Issue{ number } } fieldValues(first:20){ nodes{ ... on ProjectV2ItemFieldSingleSelectValue{ name field{ ... on ProjectV2SingleSelectField{ name } } } ... on ProjectV2ItemFieldDateValue{ date field{ ... on ProjectV2Field{ name } } } } } } } } } }'
p = gh("api", "graphql", "-f", f"query={q}")["data"]["user"]["projectV2"]
print("board items:", p["items"]["totalCount"], "| views:", [(v["name"], v["layout"]) for v in p["views"]["nodes"]], "| description:", p["shortDescription"])
st = collections.Counter(); nodates = []
for it in p["items"]["nodes"]:
    fv = {(n.get("field") or {}).get("name"): n.get("name") or n.get("date") for n in it["fieldValues"]["nodes"] if n}
    st[fv.get("Status")] += 1
    if not (fv.get("Start") and fv.get("End")): nodates.append(it["content"].get("number"))
print("status:", dict(st), "| items without Start/End:", nodates)
for m in gh("api", f"repos/{R}/milestones?state=all&per_page=100"):
    print(f"milestone {m['number']} {m['state']:<6} due {m['due_on'][:10]} open={m['open_issues']} closed={m['closed_issues']} {m['title']}")
muts = [f["name"] for f in gh("api", "graphql", "-f", "query=query{ __schema{ mutationType{ fields{ name } } } }")["data"]["__schema"]["mutationType"]["fields"]]
print("view mutations available:", [m for m in muts if "View" in m])
for login in ("Y3rnur", "Zhengis04", "CheffCorleOne", "mrbqble"):
    print(login, "->", gh("api", f"users/{login}").get("name"))
