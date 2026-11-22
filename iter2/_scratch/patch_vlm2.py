from pathlib import Path
p = Path("vlm_judge.py"); t = p.read_text(encoding="utf-8")
start = t.index("def judge(runs, limit, delay, model, dry_run")
end = t.index("# -------------------------------------------------------------------------------------------------------------------------")
end = t.index("# ----", t.index("def judge(")) if t.index("# ----", t.index("def judge(")) > start else end
new_judge = '''def judge(runs, limit, delay, model, dry_run, max_wait_hours=24, workers=4):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    plan = {r: pairs_for(r) for r in runs}
    missing = [(r, str(p)) for r, ps in plan.items() for _, o, rec in ps for p in (o, rec) if not p.exists()]
    print(f"{sum(len(v) for v in plan.values())} pairs in {len(runs)} setups; missing files: {len(missing)}", flush=True)
    for r, p in missing[:10]:
        print("  missing:", r, p, flush=True)
    if dry_run:
        return
    key = api_key()
    if not key:
        sys.exit("GEMINI_API_KEY not found (environment, Windows user environment or ~/.gemini_api_key)")
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types as genai_types
    client = genai.Client(api_key=key, http_options=genai_types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000))
    OUT.mkdir(parents=True, exist_ok=True)
    if not wait_until_healthy(client, model, max_wait_hours):
        sys.exit(f"the API stayed unavailable for {max_wait_hours} h")
    done = {r: load_done(r) for r in runs}
    tasks = []                                          # case by case across setups, so all setups meet the same API conditions
    by_case = {}
    for r, ps in plan.items():
        for c, o, p in (ps[:limit] if limit else ps):
            by_case.setdefault((RUNS[r][0], c), []).append((r, o, p))
    for (ds, c), items in sorted(by_case.items()):
        for r, orig, recon in items:
            if c not in done[r] and orig.exists() and recon.exists():
                tasks.append((ds, c, r, orig, recon))
    print(f"{len(tasks)} pairs to judge with {workers} workers", flush=True)
    lock, healthy = threading.Lock(), threading.Event()
    healthy.set()
    state = {"fails": 0, "n": 0, "t0": time.time()}

    def one(task):
        ds, c, r, orig, recon = task
        healthy.wait()
        row = {"run": r, "dataset": ds, "case": c, "original": str(orig), "reconstruction": str(recon), "model": model}
        uploaded = []
        try:
            o_file = with_retries(lambda: client.files.upload(file=str(orig)), "upload", genai_errors); uploaded.append(o_file)
            g_file = with_retries(lambda: client.files.upload(file=str(recon)), "upload", genai_errors); uploaded.append(g_file)
            for q, prompt in PROMPTS.items():
                resp = with_retries(lambda: client.models.generate_content(model=model, contents=[prompt, o_file, g_file]), f"{r} case{c} {q}", genai_errors)
                text = resp.text or ""
                row[q] = {"score": extract_score(text), "text": text}
                time.sleep(delay)
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            for f in uploaded:
                try:
                    client.files.delete(name=f.name)
                except Exception:
                    pass
        row["timestamp"] = datetime.now().isoformat()
        trigger = False
        with lock:
            with open(OUT / f"{r}.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\\n")
            state["n"] += 1
            state["fails"] = state["fails"] + 1 if "error" in row else 0
            if state["fails"] >= 3 and healthy.is_set():
                healthy.clear(); state["fails"] = 0; trigger = True
            s = {q: row.get(q, {}).get("score") for q in PROMPTS}
            el = time.time() - state["t0"]
            print(f"[{state['n']}/{len(tasks)}] {r} case{c}: numbers {s['numbers']}, positions {s['positions']}" +
                  (f"  ERROR {row['error'][:100]}" if "error" in row else "") + f"  ({el / state['n']:.1f} s/pair overall)", flush=True)
        if trigger:
            print("3 failed pairs in a row: all workers wait for the API", flush=True)
            wait_until_healthy(client, model, max_wait_hours)
            healthy.set()
        return row

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, tasks))
    print("JUDGE_DONE", state["n"], "pairs this session", flush=True)


'''
t = t[:start] + new_judge + t[end:]
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60]); t = t.replace(old, new)
rep('    ap.add_argument("--max-wait-hours", type=float, default=24, help="how long to wait for the API to come back")\n',
    '    ap.add_argument("--max-wait-hours", type=float, default=24, help="how long to wait for the API to come back")\n'
    '    ap.add_argument("--workers", type=int, default=4, help="pairs judged in parallel")\n'
    '    ap.add_argument("--retry-base", type=float, default=10, help="first retry wait in seconds (batch_evaluation.py: 30), doubling")\n'
    '    ap.add_argument("--retry-cap", type=float, default=60, help="longest single retry wait (batch_evaluation.py: 300)")\n'
    '    ap.add_argument("--retries", type=int, default=12, help="attempts per request (batch_evaluation.py: 8)")\n')
rep("    judge(runs, args.limit, args.delay, args.model, args.dry_run, args.max_wait_hours)",
    "    global RETRY_DELAY_SECONDS, MAX_RETRY_DELAY_SECONDS, MAX_RETRIES\n    RETRY_DELAY_SECONDS, MAX_RETRY_DELAY_SECONDS, MAX_RETRIES = args.retry_base, args.retry_cap, args.retries\n"
    "    judge(runs, args.limit, args.delay, args.model, args.dry_run, args.max_wait_hours, args.workers)")
p.write_text(t, encoding="utf-8"); print("patched; judge() now parallel")
