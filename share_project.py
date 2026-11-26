#!/usr/bin/env python3
"""Grant the team write access to the Projects v2 board and link it to the repo.

Repo collaborator access does NOT carry over to a user-owned project - it is a
separate permission surface, and gh has no CLI subcommand for it, so this uses
the updateProjectV2Collaborators GraphQL mutation.
"""
import json
import subprocess
import sys

OWNER = "mrbqble"
PROJECT_NUMBER = 2
REPO = "csci408-semantic-knowledge-exchange"
TEAM = ["Y3rnur", "Zhengis04", "CheffCorleOne"]
ROLE = "WRITER"          # ADMIN | WRITER | READER | NONE


def gh(args, parse=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! {r.stderr.strip()[:200]}")
        return None
    out = r.stdout.strip()
    if not parse or not out:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def graphql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F", f"{k}={v}"]
    return gh(args)


# --- project node id ---
q = """
query($owner:String!, $num:Int!){
  user(login:$owner){ projectV2(number:$num){ id title url } }
}"""
res = graphql(q, owner=OWNER, num=PROJECT_NUMBER)
if not res:
    sys.exit("could not resolve project")
proj = res["data"]["user"]["projectV2"]
print(f"project: {proj['title']}  {proj['url']}")

# --- user node ids ---
ids = {}
for login in TEAM:
    r = graphql("query($l:String!){ user(login:$l){ id login } }", l=login)
    if r and r["data"]["user"]:
        ids[login] = r["data"]["user"]["id"]
        print(f"  resolved {login}")
    else:
        print(f"  ! could not resolve {login}")

if not ids:
    sys.exit("no users resolved")

# --- grant access ---
collabs = ", ".join(
    f'{{userId:"{uid}", role:{ROLE}}}' for uid in ids.values())
mutation = f"""
mutation {{
  updateProjectV2Collaborators(input:{{
    projectId:"{proj['id']}",
    collaborators:[{collabs}]
  }}) {{
    collaborators(first:20){{ nodes{{ ... on User {{ login }} }} }}
  }}
}}"""
out = gh(["api", "graphql", "-f", f"query={mutation}"])
if out:
    nodes = out["data"]["updateProjectV2Collaborators"]["collaborators"]["nodes"]
    print(f"\nproject collaborators now: "
          f"{', '.join(n.get('login','?') for n in nodes if n)}")
else:
    print("\nmutation failed")

# --- link project to repo so it shows in the repo's Projects tab ---
print("\nlinking project to repo...")
r = gh(["project", "link", str(PROJECT_NUMBER), "--owner", OWNER,
        "--repo", REPO], parse=False)
print(f"  {r or 'link failed (may already be linked)'}")
