#!/usr/bin/env python3
"""Delete the 26 speculative task issues; keep the 4 syllabus milestones.

Uses the GraphQL deleteIssue mutation - the REST API has no delete endpoint,
only close. Deletion is permanent and issue numbers are not reused.
"""
import json
import subprocess
import sys

REPO_OWNER = "mrbqble"
REPO_NAME = "csci408-semantic-knowledge-exchange"


def gh(args, parse=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! {r.stderr.strip()[:180]}")
        return None
    out = r.stdout.strip()
    if not parse or not out:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


issues = gh(["api", f"repos/{REPO_OWNER}/{REPO_NAME}/issues?state=all&per_page=100"])
if issues is None:
    sys.exit("could not list issues")

# safety: refuse if anything has been engaged with by the team
engaged = [i for i in issues if i.get("comments", 0) > 0]
if engaged:
    sys.exit(f"ABORT: {len(engaged)} issue(s) have comments - not deleting")

print(f"deleting {len(issues)} issues...")
ok = fail = 0
for i in issues:
    m = f'mutation {{ deleteIssue(input:{{issueId:"{i["node_id"]}"}}) {{ clientMutationId }} }}'
    if gh(["api", "graphql", "-f", f"query={m}"]) is not None:
        ok += 1
    else:
        fail += 1
        print(f"  ! failed #{i['number']}")
print(f"  deleted {ok}, failed {fail}")

print("\nverifying...")
left = gh(["api", f"repos/{REPO_OWNER}/{REPO_NAME}/issues?state=all&per_page=100"])
print(f"  issues remaining: {len(left) if left is not None else '?'}")

ms = gh(["api", f"repos/{REPO_OWNER}/{REPO_NAME}/milestones?state=all"])
print(f"  milestones kept:  {len(ms) if ms else 0}")
for m in ms or []:
    print(f"    - {m['title']}  due {m['due_on'][:10]}  ({m['open_issues']} open)")

items = gh(["project", "item-list", "2", "--owner", REPO_OWNER, "--format", "json"])
n = len(items.get("items", [])) if isinstance(items, dict) else "?"
print(f"  project board items: {n}")
