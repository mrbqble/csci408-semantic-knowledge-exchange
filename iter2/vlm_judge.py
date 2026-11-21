#!/usr/bin/env python3
"""VLM judge: does the reconstruction of the reference camera preserve the NUMBER and the POSITIONS of cars? (required metric, Damir, 11 Nov 2026)

Prompts, model and score parsing are taken unchanged from Damir's reference script `batch_evaluation.py`: each pair (original photo of the reference
camera, its reconstruction) gets two separate requests, car numbers and car positions, each answered with a final "Score: 0" or "Score: 1".
Only the semantic content is judged: the prompts tell the model to ignore colour, texture and background. Reported per setup, as in the seed paper's
VLM evaluation: share of pairs with numbers preserved, positions preserved, and both (joint success).

Setups are listed in RUNS. Each pair's result is appended to results/vlm/<run>.jsonl (raw answers kept); a restart skips finished pairs and retries
failed ones. Cases are processed case by case across all requested setups, so every setup is judged under the same API conditions.

The Gemini API key is read from GEMINI_API_KEY in the environment, else from the Windows user environment (registry), else from the file
%USERPROFILE%\\.gemini_api_key. It is never printed or written.

Usage:
  python vlm_judge.py --runs core --dry-run          check that every image exists, no API calls
  python vlm_judge.py --runs v3_default --limit 2    smoke test
  python vlm_judge.py --runs core                    judge the core setups (resumable)
  python vlm_judge.py --report                       write VLM_JUDGE_REPORT.md from whatever is finished
"""
import argparse
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import paths

MODEL_NAME = "gemma-4-31b-it"               # as in batch_evaluation.py

# --- prompts: copied verbatim from batch_evaluation.py -----------------------------------------------------------------------------------
PROMPT_CAR_POSITIONS = """You are evaluating a pair of images: the first image is the original image, and the second image is a reconstructed image generated using semantic segmentation, edge maps, and a textual description.

Please compare the two images and focus only on the spatial positions of cars.

Assign a score of 1 if:
- The positions of cars in the reconstructed image are largely consistent with their positions in the original image (e.g., relative locations, left/right placement, front/back placement).

Assign a score of 0 if:
- The positions of cars in the reconstructed image are clearly incorrect, significantly shifted, missing, or inconsistent with the original image.

Ignore minor visual differences such as color, texture, or background details.
Provide a brief explanation for your decision.
Finally, output a single overall score of either 0 or 1 on the last line, in the format "Score: X"."""

PROMPT_CAR_NUMBERS = """You are evaluating a pair of images: the first image is the original image, and the second image is a reconstructed image generated using semantic segmentation, edge maps, and a textual description.

Please compare the two images and focus only on the number of cars present.

Assign a score of 1 if:
- The number of cars in the reconstructed image matches the number of cars in the original image.

Assign a score of 0 if:
- The reconstructed image contains more or fewer cars than the original image.

Ignore differences in car appearance, position, size, or background details.
Provide a brief explanation for your decision.
Finally, output a single overall score of either 0 or 1 on the last line, in the format "Score: X"."""
PROMPTS = {"numbers": PROMPT_CAR_NUMBERS, "positions": PROMPT_CAR_POSITIONS}

# --- retry policy: as in batch_evaluation.py ---------------------------------------------------------------------------------------------
MAX_RETRIES = 8
RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 300
MAX_RETRY_TOTAL_SECONDS = 1200
REQUEST_TIMEOUT_SECONDS = 180
RETRYABLE_CLIENT_CODES = {408, 429}

# --- setups ------------------------------------------------------------------------------------------------------------------------------
DATASETS = {
    "v3": {"root": paths.CARLA_V3, "cases": list(range(1, 113)), "photo": "cam1.jpg"},
    "rw": {"root": paths.REAL_WORLD_CORE, "cases": [1 + 6 * i for i in range(61)], "photo": "cam1.png"},
}
ITER1 = Path(__file__).resolve().parent.parent / "iter1"


def _cs_stems():
    """The 100 Cityscapes validation images of iteration 1's evaluation (every 5th of 500)."""
    f = ITER1 / "results" / "iteration1_palette_eval_100.json"
    return [r["stem"] for r in json.loads(f.read_text())["rows"]] if f.exists() else []


DATASETS["cs"] = {"orig": lambda c: ITER1 / "data" / "cityscapes_val" / f"{c}.png", "cases": _cs_stems()}
DATASETS["cs2"] = {"root": Path("data/cs_cases"), "cases": list(range(1, 101)), "photo": "cam1.png"}   # the same 100 images, case k = k-th stem

RUNS = {  # label: (dataset, reconstruction path pattern, description)
    "v3_default":          ("v3", "results/v3/prompt_only/case{c}.png", "all cameras' captions, 1024x576, Cityscapes palette (current receiver)"),
    "v3_k1":               ("v3", "results/v3/k1/case{c}_cam1.png", "reference camera only, 1024x576, Cityscapes palette"),
    "v3_both_fixes":       ("v3", "results/v3_native_ade/prompt_only/case{c}.png", "all cameras' captions, 896x512 working size, ADE20K palette"),
    "v3_k1_both_fixes":    ("v3", "results/v3_native_ade/k1/case{c}_cam1.png", "reference camera only, 896x512 working size, ADE20K palette"),
    "v3_cn07_15":          ("v3", "results/v3_cn07_15/prompt_only/case{c}.png", "current receiver with ControlNet canny 0.7 / seg 1.5"),
    "v3_resolution_only":  ("v3", "results/v3_native_cs/prompt_only/case{c}.png", "896x512 working size, Cityscapes palette"),
    "v3_palette_only":     ("v3", "results/v3_ade/prompt_only/case{c}.png", "1024x576, ADE20K palette"),
    "rw_default":          ("rw", "results/rw_core/prompt_only/case{c}.png", "all cameras' captions, 1024x576, Cityscapes palette (current receiver)"),
    "rw_k1":               ("rw", "results/rw_core/k1/case{c}_cam1.png", "reference camera only, 1024x576, Cityscapes palette"),
    "rw_both_fixes":       ("rw", "results/rw_native_ade/prompt_only/case{c}.png", "all cameras' captions, 896x512 working size, ADE20K palette"),
    "rw_k1_both_fixes":    ("rw", "results/rw_native_ade/k1/case{c}_cam1.png", "reference camera only, 896x512 working size, ADE20K palette"),
    "rw_cn07_15":          ("rw", "results/rw_cn07_15/prompt_only/case{c}.png", "current receiver with ControlNet canny 0.7 / seg 1.5"),
    "rw_resolution_only":  ("rw", "results/rw_native_cs/prompt_only/case{c}.png", "896x512 working size, Cityscapes palette"),
    "rw_palette_only":     ("rw", "results/rw_ade/prompt_only/case{c}.png", "1024x576, ADE20K palette"),
    "cs_authors":          ("cs", str(ITER1 / "results" / "palette100" / "A_cs_full" / "{c}.png"), "Cityscapes (the seed paper's kind of data), authors' receiver settings: 2048x1024, Cityscapes palette, single camera (iteration 1)"),
    "cs_ade":              ("cs", str(ITER1 / "results" / "palette100" / "B_ade_full" / "{c}.png"), "Cityscapes, authors' settings with the ADE20K palette (iteration 1)"),
    "cs2_paper_seg1024":   ("cs2", "results/cs_paper/k1/case{c}_cam1.png", "Cityscapes, seed paper's single-camera MMSD rebuilt with the segmenter at full input size (1024x2048), 2048x1024, Cityscapes palette"),
    "v3_paper_k1":         ("v3", "results/v3_paper/k1/case{c}_cam1.png", "seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution"),
    "v3_paper_multi":      ("v3", "results/v3_paper/prompt_only/case{c}.png", "same settings, all cameras' captions (our multi-camera receiver)"),
    "rw_paper_k1":         ("rw", "results/rw_paper/k1/case{c}_cam1.png", "seed paper's single-camera MMSD at its own settings: reference camera only, generated at the photo's resolution (1920x1088), Cityscapes palette, map at half resolution, edges at full resolution"),
    "rw_paper_multi":      ("rw", "results/rw_paper/prompt_only/case{c}.png", "same settings, all cameras' captions (our multi-camera receiver)"),
    "rw_fuse":             ("rw", "results/rw_fuse/fuse/case{c}.png", "Damir's fusion: img2img from the main reconstruction (paper settings, strength 0.5), main seg+edge on the ControlNets, supporting reconstructions on the IP-Adapter (scale 1.0), global caption"),
    "rw_fuse_noip":        ("rw", "results/rw_fuse/fuse_noip/case{c}.png", "control: the same img2img pass without the IP-Adapter"),
    "v3_fuse":             ("v3", "results/v3_fuse/fuse/case{c}.png", "Damir's fusion (as rw_fuse)"),
    "v3_fuse_noip":        ("v3", "results/v3_fuse/fuse_noip/case{c}.png", "control: the same img2img pass without the IP-Adapter"),
    "v3_identity":         ("v3", str(paths.CARLA_V3 / "case{c}" / "cam1.jpg"), "calibration: the original photo judged against itself (the judge's ceiling)"),
    "rw_identity":         ("rw", str(paths.REAL_WORLD_CORE / "case{c}" / "cam1.png"), "calibration: the original photo judged against itself (the judge's ceiling)"),
    "v3_both_fixes_cn":    ("v3", "results/v3_native_ade_cn/prompt_only/case{c}.png", "both fixes + ControlNet canny 0.7 / seg 1.5"),
    "v3_k1_both_fixes_cn": ("v3", "results/v3_native_ade_cn/k1/case{c}_cam1.png", "reference camera only, both fixes + canny 0.7 / seg 1.5"),
    "rw_both_fixes_cn":    ("rw", "results/rw_native_ade_cn/prompt_only/case{c}.png", "both fixes + ControlNet canny 0.7 / seg 1.5"),
    "rw_k1_both_fixes_cn": ("rw", "results/rw_native_ade_cn/k1/case{c}_cam1.png", "reference camera only, both fixes + canny 0.7 / seg 1.5"),
}
GROUPS = {
    "core": ["v3_default", "v3_both_fixes", "v3_k1", "v3_k1_both_fixes", "rw_default", "rw_both_fixes", "rw_k1", "rw_k1_both_fixes"],
    "extra": ["v3_identity", "rw_identity", "v3_both_fixes_cn", "v3_k1_both_fixes_cn", "rw_both_fixes_cn", "rw_k1_both_fixes_cn",
              "v3_cn07_15", "v3_resolution_only", "v3_palette_only", "rw_cn07_15", "rw_resolution_only", "rw_palette_only"],
}
GROUPS["paper"] = ["cs_authors", "cs_ade"]
GROUPS["paper_res"] = ["rw_paper_k1", "rw_paper_multi", "v3_paper_k1", "v3_paper_multi"]
GROUPS["cs_rerun"] = ["cs2_paper_seg1024"]
GROUPS["fusion"] = ["rw_fuse", "rw_fuse_noip", "v3_fuse", "v3_fuse_noip"]
# 19-20 Nov (Damir): supporting reconstructions at full resolution (paper settings), then one-factor tuning of strength and IP-Adapter scale
for _ds in ("v3", "rw"):
    RUNS[f"{_ds}_fuseF"] = (_ds, f"results/{_ds}_fuseF_st0.5/fuse/case{{c}}.png", "fusion with full-resolution supporting reconstructions (strength 0.5, IP scale 1.0)")
    for _st in ("0.3", "0.4", "0.6"):
        RUNS[f"{_ds}_fuseF_st{_st}"] = (_ds, f"results/{_ds}_fuseF_st{_st}/fuse/case{{c}}.png", f"tuning: strength {_st}, IP scale 1.0 (full-resolution supports)")
    for _ip in ("0.5", "0.75"):
        RUNS[f"{_ds}_fuseF_ip{_ip}"] = (_ds, f"results/{_ds}_fuseF_st0.5/fuse_s{_ip}/case{{c}}.png", f"tuning: strength 0.5, IP scale {_ip} (full-resolution supports)")
GROUPS["fusion_full"] = ["rw_fuseF", "v3_fuseF"]
GROUPS["tune"] = [f"{d}_fuseF_{k}" for d in ("rw", "v3") for k in ("st0.3", "st0.4", "st0.6", "ip0.5", "ip0.75")]
GROUPS["fullres_tune"] = GROUPS["fusion_full"] + GROUPS["tune"]
GROUPS["all"] = GROUPS["core"] + GROUPS["extra"] + GROUPS["paper"] + GROUPS["paper_res"] + GROUPS["cs_rerun"] + GROUPS["fusion"] + GROUPS["fullres_tune"]
COMPARISONS = [  # (setup B, setup A, question): reported as B minus A
    ("both_fixes", "default", "Damir's two fixes (working resolution + ADE20K palette) vs current receiver"),
    ("default", "k1", "multi-camera captions vs reference camera only (current receiver)"),
    ("both_fixes", "k1_both_fixes", "multi-camera captions vs reference camera only (with both fixes)"),
    ("resolution_only", "default", "working resolution alone"),
    ("palette_only", "default", "ADE20K palette alone"),
    ("cn07_15", "default", "ControlNet canny 0.7 / seg 1.5"),
    ("both_fixes_cn", "both_fixes", "canny 0.7 / seg 1.5 on top of both fixes"),
    ("both_fixes_cn", "k1_both_fixes_cn", "multi-camera captions vs reference camera only (both fixes + canny 0.7 / seg 1.5)"),
    ("ade", "authors", "ADE20K palette vs Cityscapes palette (authors' settings, 2048x1024)"),
    ("fuse", "paper_k1", "Damir's fusion vs the main reconstruction (his single-camera MMSD at paper settings)"),
    ("fuse", "fuse_noip", "supporting reconstructions through the IP-Adapter vs re-denoising only"),
    ("fuse_noip", "paper_k1", "re-denoising the main reconstruction alone (img2img, no IP-Adapter)"),
    ("fuseF", "fuse", "supporting reconstructions at full resolution vs 896x512 (fusion, strength 0.5, IP scale 1.0)"),
    ("fuseF", "paper_k1", "fusion with full-resolution supports vs the single-camera MMSD"),
    ("paper_multi", "paper_k1", "multi-camera captions vs the seed paper's single-camera MMSD, both at the paper's settings"),
    ("both_fixes_cn", "paper_k1", "our best multi-camera setting vs the seed paper's single-camera MMSD at its settings"),
    ("k1_both_fixes_cn", "paper_k1", "our best single-camera setting vs the seed paper's single-camera MMSD at its settings"),
]
SEED_PAPER = "seed paper (Table 6, MMSD single camera): numbers 86.9-88.9%, positions 94.4-97.6%, joint 86.1-86.9%"
OUT = Path("results/vlm")


def api_key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k and sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
                k = winreg.QueryValueEx(reg, "GEMINI_API_KEY")[0]
        except OSError:
            k = None
    if not k:
        f = Path.home() / ".gemini_api_key"
        k = f.read_text(encoding="utf-8").strip() if f.exists() else None
    return k


def extract_score(text):
    """Copied from batch_evaluation.py: the last 'score ... 0/1' wins; last resort a line holding only 0 or 1."""
    if not text:
        return None
    m = re.findall(r'score\W*(?:of|is|=)?\W*([01])(?!\d|\.\d)', text, re.IGNORECASE)
    if m:
        return int(m[-1])
    m = re.findall(r'^\W*([01])\W*$', text, re.MULTILINE)
    return int(m[-1]) if m else None


def with_retries(fn, description, genai_errors):
    start = time.monotonic()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            code = getattr(e, "code", None)
            if isinstance(e, genai_errors.ClientError) and code not in RETRYABLE_CLIENT_CODES:
                raise
            delay = min(RETRY_DELAY_SECONDS * 2 ** (attempt - 1), MAX_RETRY_DELAY_SECONDS)
            delay += random.uniform(0, delay * 0.1)
            elapsed = time.monotonic() - start
            if attempt == MAX_RETRIES or elapsed + delay > MAX_RETRY_TOTAL_SECONDS:
                print(f"  {description} giving up after {attempt} attempts ({elapsed:.0f}s)", flush=True)
                raise
            print(f"  {description} failed (attempt {attempt}/{MAX_RETRIES}): {str(e)[:160]}; retrying in {delay:.0f}s", flush=True)
            time.sleep(delay)


def wait_until_healthy(client, model, max_hours):
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


def pairs_for(run):
    ds, pattern, _ = RUNS[run]
    d = DATASETS[ds]
    if "orig" in d:
        return [(c, d["orig"](c), Path(pattern.format(c=c))) for c in d["cases"]]
    return [(c, d["root"] / f"case{c}" / d["photo"], Path(pattern.format(c=c))) for c in d["cases"]]


def load_done(run):
    f = OUT / f"{run}.jsonl"
    done = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
                done[r["case"]] = r
    return done


def judge(runs, limit, delay, model, dry_run, max_wait_hours=24, workers=4):
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
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
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


# ------------------------------------------------------------------------------------------------------------------------- report
def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def mcnemar_p(b, c):
    from scipy.stats import binom
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * binom.cdf(min(b, c), n, 0.5))


def report():
    rows, lines = {}, []
    for r in RUNS:
        d = load_done(r)
        if d:
            rows[r] = d
    lines += ["# VLM judge results\n",
              f"Judge: `{MODEL_NAME}` through the Gemini API, prompts and score parsing unchanged from Damir's `batch_evaluation.py`. Each pair is the original photo of the "
              "reference camera (cam1) and its reconstruction; two separate requests per pair (car numbers, car positions), each scored 0/1. Joint = both 1. "
              "95% Wilson intervals in brackets.\n", f"Reference: {SEED_PAPER}.\n",
              "| setup | what it is | pairs | numbers preserved | positions preserved | joint |", "|---|---|---|---|---|---|"]
    for r, d in rows.items():
        n = len(d)
        k = {q: sum(x[q]["score"] for x in d.values()) for q in PROMPTS}
        kj = sum(x["numbers"]["score"] * x["positions"]["score"] for x in d.values())
        cell = lambda kk: f"{100 * kk / n:.1f}% [{100 * wilson(kk, n)[0]:.0f}-{100 * wilson(kk, n)[1]:.0f}]"
        lines.append(f"| {r} | {RUNS[r][2]} | {n} | {cell(k['numbers'])} | {cell(k['positions'])} | {cell(kj)} |")
    lines += ["", "## Paired comparisons (same cases; McNemar exact test on the joint score)\n",
              "| dataset | comparison | pairs | joint B | joint A | change | B better / A better | p |", "|---|---|---|---|---|---|---|---|"]
    for ds in ("v3", "rw", "cs"):
        for b, a, question in COMPARISONS:
            rb, ra = f"{ds}_{b}", f"{ds}_{a}"
            if rb not in rows or ra not in rows:
                continue
            common = sorted(set(rows[rb]) & set(rows[ra]))
            j = lambda d, c: d[c]["numbers"]["score"] * d[c]["positions"]["score"]
            jb, ja = [j(rows[rb], c) for c in common], [j(rows[ra], c) for c in common]
            bw = sum(1 for x, y in zip(jb, ja) if x > y); aw = sum(1 for x, y in zip(jb, ja) if y > x)
            n = len(common)
            lines.append(f"| {ds} | {question} | {n} | {100 * sum(jb) / n:.1f}% | {100 * sum(ja) / n:.1f}% | {100 * (sum(jb) - sum(ja)) / n:+.1f} pts | {bw} / {aw} | {mcnemar_p(bw, aw):.3f} |")
    unparsed = sum(1 for r in RUNS for line in ((OUT / f"{r}.jsonl").read_text(encoding="utf-8").splitlines() if (OUT / f"{r}.jsonl").exists() else [])
                   for q in PROMPTS if json.loads(line).get(q, {}).get("score", 0) is None)
    lines += ["", f"Answers whose score could not be parsed (counted as unfinished and retried): {unparsed}.\n"]
    Path("VLM_JUDGE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", default="core", help="comma list of setups, or core / extra / all")
    ap.add_argument("--limit", type=int, default=0, help="only the first N cases of each setup")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between API calls (batch_evaluation.py uses 3)")
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-wait-hours", type=float, default=24, help="how long to wait for the API to come back")
    ap.add_argument("--workers", type=int, default=4, help="pairs judged in parallel")
    ap.add_argument("--retry-base", type=float, default=10, help="first retry wait in seconds (batch_evaluation.py: 30), doubling")
    ap.add_argument("--retry-cap", type=float, default=60, help="longest single retry wait (batch_evaluation.py: 300)")
    ap.add_argument("--retries", type=int, default=12, help="attempts per request (batch_evaluation.py: 8)")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        return report()
    runs = []
    for part in args.runs.split(","):
        runs += GROUPS.get(part, [part])
    unknown = [r for r in runs if r not in RUNS]
    if unknown:
        sys.exit(f"unknown setups: {unknown}")
    global RETRY_DELAY_SECONDS, MAX_RETRY_DELAY_SECONDS, MAX_RETRIES
    RETRY_DELAY_SECONDS, MAX_RETRY_DELAY_SECONDS, MAX_RETRIES = args.retry_base, args.retry_cap, args.retries
    judge(runs, args.limit, args.delay, args.model, args.dry_run, args.max_wait_hours, args.workers)


if __name__ == "__main__":
    main()
