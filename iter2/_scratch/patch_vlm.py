from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep("def pairs_for(run):", '''def wait_until_healthy(client, model, max_hours):
    """The Gemma endpoint has outages (500 / 504 even for text-only requests): ping it, and while it is down check again every 10 minutes."""
    start = time.time()
    while True:
        try:
            r = client.models.generate_content(model=model, contents=["Reply with the single word: ready"])
            if r.text:
                print(f"{datetime.now():%Y-%m-%d %H:%M} API healthy", flush=True)
                return True
        except Exception as e:
            print(f"{datetime.now():%Y-%m-%d %H:%M} API not available ({str(e)[:100]}); next check in 10 min", flush=True)
        if time.time() - start > max_hours * 3600:
            return False
        time.sleep(600)


def pairs_for(run):''')
rep("def judge(runs, limit, delay, model, dry_run):", "def judge(runs, limit, delay, model, dry_run, max_wait_hours=24):")
rep('''    OUT.mkdir(parents=True, exist_ok=True)
    done = {r: load_done(r) for r in runs}''', '''    OUT.mkdir(parents=True, exist_ok=True)
    if not wait_until_healthy(client, model, max_wait_hours):
        sys.exit(f"the API stayed unavailable for {max_wait_hours} h")
    done = {r: load_done(r) for r in runs}
    fails = 0''')
rep('''            n_done += 1
            s = {q: row.get(q, {}).get("score") for q in PROMPTS}''', '''            n_done += 1
            fails = fails + 1 if "error" in row else 0
            if fails >= 3:                              # probably an outage again: wait for the endpoint before burning more pairs
                print("3 failed pairs in a row: waiting for the API", flush=True)
                wait_until_healthy(client, model, max_wait_hours)
                fails = 0
            s = {q: row.get(q, {}).get("score") for q in PROMPTS}''')
rep('    ap.add_argument("--dry-run", action="store_true")\n', '    ap.add_argument("--dry-run", action="store_true")\n    ap.add_argument("--max-wait-hours", type=float, default=24, help="how long to wait for the API to come back")\n')
rep("    judge(runs, args.limit, args.delay, args.model, args.dry_run)", "    judge(runs, args.limit, args.delay, args.model, args.dry_run, args.max_wait_hours)")
p.write_text(t, encoding="utf-8"); print("patched")
