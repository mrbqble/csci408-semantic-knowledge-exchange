#!/usr/bin/env python3
"""Report hand-off package (22 Nov 2026): everything the team needs to write the final report, assembled into one folder.
Usage: python make_handoff.py <output folder>
"""
import csv
import json
import shutil
import statistics as st
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import paths

OUT = Path(sys.argv[1])
ROOT = Path(".")                                    # iter2/
ITER1 = Path("../iter1")
DSET = {"v3": {"photos": paths.CARLA_V3, "ext": ".jpg", "pay": "data/v3_payloads", "native": "data/v3_native", "label": "CARLA v3"},
        "rw": {"photos": paths.REAL_WORLD_CORE, "ext": ".png", "pay": "data/rw_core_payloads", "native": "data/rw_native", "label": "Real-world Astana"}}
SETUPS = [("paper_k1", "Single-camera MMSD (seed paper)", "results/{ds}_paper/k1/case{c}_cam1.png"),
          ("paper_multi", "Multi-camera, captions only", "results/{ds}_paper/prompt_only/case{c}.png"),
          ("fuse_noip", "Control: img2img, no IP-Adapter", "results/{ds}_fuse/fuse_noip/case{c}.png"),
          ("fuse", "Damir's fusion, supports 896x512 (recommended)", "results/{ds}_fuse/fuse/case{c}.png"),
          ("fuseF", "Damir's fusion, supports full resolution", "results/{ds}_fuseF_st0.5/fuse/case{c}.png")]
RW_CASES = [1 + 6 * k for k in range(61)]
try:
    FONT, FONT_S = ImageFont.truetype("arial.ttf", 18), ImageFont.truetype("arial.ttf", 14)
except OSError:
    FONT = FONT_S = ImageFont.load_default()


def jl(run):
    out, f = {}, Path(f"results/vlm/{run}.jsonl")
    if f.exists():
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
                out[r["case"]] = r
    return out


def jpeg(src, dst, width=1280, q=88):
    im = Image.open(src).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=q)


def copy(src, dst):
    src = Path(src)
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree(src, dst, dirs_exist_ok=True) if src.is_dir() else shutil.copy2(src, dst))
    else:
        print("missing:", src)


def verdict(r):
    if r is None:
        return "not judged"
    n, p = r["numbers"]["score"], r["positions"]["score"]
    return f"count {'OK' if n else 'WRONG'}, positions {'OK' if p else 'WRONG'}"


def ncams():
    m = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    return {int(str(c["case"]).replace("case", "")): c["n_cameras"] for c in m["cases"]}


def cams_of(ds, c):
    return sorted(p.stem for p in (DSET[ds]["photos"] / f"case{c}").iterdir() if p.stem.startswith("cam") and p.suffix == DSET[ds]["ext"])


def panel(tiles, out, w=512, h=288, title=None):
    head = 34 if title else 0
    sheet = Image.new("RGB", (len(tiles) * (w + 6) + 6, head + h + 52), "white")
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((8, 8), title, fill="black", font=FONT)
    for i, (path, label, r) in enumerate(tiles):
        x = 6 + i * (w + 6)
        if path and Path(path).exists():
            sheet.paste(Image.open(path).convert("RGB").resize((w, h), Image.LANCZOS), (x, head))
        d.text((x, head + h + 4), label, fill="black", font=FONT_S)
        if r is not None:
            ok = r["numbers"]["score"] * r["positions"]["score"]
            d.text((x, head + h + 24), verdict(r), fill=(0, 120, 0) if ok else (190, 0, 0), font=FONT_S)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=85)


def example_cases(J):
    nc = ncams()
    picks = []
    for k in (3, 4, 5, 6):
        cs = sorted(c for c in nc if nc[c] == k)
        picks.append(("v3", cs[0], f"first {k}-camera case"))
        fixed = [c for c in cs if c in J["v3"]["fuse"] and c in J["v3"]["paper_k1"]
                 and J["v3"]["fuse"][c]["numbers"]["score"] * J["v3"]["fuse"][c]["positions"]["score"] == 1
                 and J["v3"]["paper_k1"][c]["numbers"]["score"] * J["v3"]["paper_k1"][c]["positions"]["score"] == 0 and c != cs[0]]
        if fixed:
            picks.append(("v3", fixed[0], f"first {k}-camera case where the fusion fixes a single-camera failure"))
    rj = lambda s, c: J["rw"][s][c]["numbers"]["score"] * J["rw"][s][c]["positions"]["score"]
    picks += [("rw", 1, "first real-world case"), ("rw", 7, "second real-world case")]
    fixed = [c for c in RW_CASES if rj("fuse", c) == 1 and rj("paper_k1", c) == 0]
    broken = [c for c in RW_CASES if rj("fuse", c) == 0 and rj("paper_k1", c) == 1]
    picks += [("rw", fixed[0], "first real-world case the fusion fixes"), ("rw", broken[0], "first real-world case the fusion breaks")]
    seen = set()
    for ds, c, why in picks:
        if (ds, c) in seen:
            continue
        seen.add((ds, c))
        base = OUT / "04_example_cases" / f"{ds}_case{c}"
        cams = cams_of(ds, c)
        caps, verdicts = {}, {}
        for cam in cams:
            jpeg(DSET[ds]["photos"] / f"case{c}" / f"{cam}{DSET[ds]['ext']}", base / "1_original_photos" / f"{cam}.jpg")
            for suf in ("seg.webp", "edge.webp", "caption.txt"):
                copy(Path(DSET[ds]["pay"]) / f"case{c}" / f"{cam}_{suf}", base / "2_payload_paper_settings" / f"{cam}_{suf}")
                copy(Path(DSET[ds]["native"]) / f"case{c}" / f"{cam}_{suf}", base / "2b_payload_896x512" / f"{cam}_{suf}")
            caps[cam] = (Path(DSET[ds]["pay"]) / f"case{c}" / f"{cam}_caption.txt").read_text(encoding="utf-8").strip()
            for src, name in ((f"results/{ds}_paper/k1/case{c}_{cam}.png", f"{cam}_single_camera_1920x1088.jpg"),
                              (f"results/{ds}_support/k1/case{c}_{cam}.png", f"{cam}_single_camera_896x512.jpg")):
                if Path(src).exists():
                    jpeg(src, base / "3_per_camera_reconstructions" / name)
        for key, label, pattern in SETUPS:
            src = Path(pattern.format(ds=ds, c=c))
            if src.exists():
                jpeg(src, base / "4_main_camera_results" / f"{key}.jpg")
            r = J[ds][key].get(c)
            verdicts[key] = {"setup": label, "numbers_score": r["numbers"]["score"] if r else None, "positions_score": r["positions"]["score"] if r else None,
                             "judge_numbers_answer": r["numbers"]["text"] if r else None, "judge_positions_answer": r["positions"]["text"] if r else None}
        (base / "judge_verdicts.json").write_text(json.dumps(verdicts, indent=1, ensure_ascii=False), encoding="utf-8")
        tiles = [(base / "1_original_photos" / "cam1.jpg", "original (main camera)", None)] + \
                [(base / "4_main_camera_results" / f"{k}.jpg", lab.split(" (")[0], J[ds][k].get(c)) for k, lab, _ in SETUPS]
        panel(tiles, base / "overview.jpg", w=420, h=236, title=f"{DSET[ds]['label']} case {c} ({len(cams)} cameras) - {why}")
        lines = [f"{DSET[ds]['label']}, case {c}: {len(cams)} cameras ({', '.join(cams)}); main camera cam1. Chosen as: {why}.", "",
                 "Captions (payload):"] + [f"  {cam}: {caps[cam]}" for cam in cams] + ["", "Judge verdicts for the main camera (joint = count OK and positions OK):"] + \
                [f"  {SETUPS[i][1]}: {verdict(J[ds][SETUPS[i][0]].get(c))}" for i in range(len(SETUPS))] + ["",
                 "Folders: 1 original photos, 2 payload (paper settings: segmentation map at half resolution, edge map at full resolution, caption),",
                 "2b payload at 896x512, 3 single-camera reconstruction of every camera (1920x1088 and 896x512), 4 results for the main camera,",
                 "judge_verdicts.json holds the judge's full answers. Images are JPEG copies (1280 px wide) of the PNG outputs."]
        (base / "README.txt").write_text("\n".join(lines), encoding="utf-8")
        print("example", ds, c, why)


def gallery(J):
    for ds in ("v3", "rw"):
        cases = range(1, 113) if ds == "v3" else RW_CASES
        for c in cases:
            tiles = [(DSET[ds]["photos"] / f"case{c}" / f"cam1{DSET[ds]['ext']}", "original (main camera)", None)] + \
                    [(Path(p.format(ds=ds, c=c)), lab.split(" (")[0], J[ds][k].get(c)) for k, lab, p in SETUPS if k in ("paper_k1", "fuse", "fuseF")]
            panel(tiles, OUT / "05_gallery_all_cases" / ("carla_v3" if ds == "v3" else "real_world") / f"case{c:03d}.jpg", w=448, h=252)
    print("gallery done")


def timing():
    rows = []
    for ds in ("v3", "rw"):
        for folder, label in ((DSET[ds]["pay"], "paper payload (segmenter input 512x1024, map 1024x576, edges full res)"),
                              (DSET[ds]["native"], "896x512 payload")):
            metas = [json.loads(p.read_text()) for p in Path(folder).glob("case*/cam*_meta.json")]
            if not metas:
                continue
            for key in ("seg_infer_ms", "seg_encode_ms", "edge_ms", "caption_ms", "total_b"):
                vals = [m[key] for m in metas if key in m]
                if vals:
                    rows.append({"side": "sender", "dataset": DSET[ds]["label"], "stage": f"{label}: {key}", "n": len(vals), "mean": round(st.mean(vals), 1),
                                 "median": round(st.median(vals), 1)})
        for folder, label in ((f"results/{ds}_paper/k1", "single-camera reconstruction 1920x1088 (s)"), (f"results/{ds}_support/k1", "single-camera reconstruction 896x512 (s)"),
                              (f"results/{ds}_paper/prompt_only", "captions-only reconstruction 1920x1088 (s)"), (f"results/{ds}_fuse/fuse", "fusion pass, strength 0.5 (s)"),
                              (f"results/{ds}_fuse/fuse_noip", "control pass (s)")):
            vals = []
            for p in Path(folder).glob("*.json"):
                try:
                    v = json.loads(p.read_text()).get("seconds")
                    if v:
                        vals.append(v)
                except Exception:
                    pass
            if vals:
                rows.append({"side": "receiver", "dataset": DSET[ds]["label"], "stage": label, "n": len(vals), "mean": round(st.mean(vals), 2), "median": round(st.median(vals), 2)})
    f = OUT / "03_statistics" / "timing_stats.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r)


def statistics_folder():
    s = OUT / "03_statistics"
    copy("report_kit/tables", s / "tables")
    copy("results/vlm", s / "raw_judge_answers")
    copy("TUNING_RESULTS.md", s / "TUNING_RESULTS.md")
    import vlm_judge as vj
    (s / "judge_prompts.txt").write_text("VLM judge: gemma-4-31b-it (Gemini API), prompts copied from Damir's batch_evaluation.py\n\n=== car numbers ===\n"
                                         + vj.PROMPTS["numbers"] + "\n\n=== car positions ===\n" + vj.PROMPTS["positions"] + "\n", encoding="utf-8")
    with open(s / "judge_setups.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["setup", "dataset", "reconstruction_path_pattern", "description"])
        for k, (ds, pat, desc) in vj.RUNS.items():
            w.writerow([k, ds, pat, desc])
    with open(s / "evaluation_cases.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["dataset", "case", "n_cameras", "half"])
        nc = ncams()
        for c in range(1, 113):
            w.writerow(["CARLA v3", c, nc.get(c), "tuning" if c <= 56 else "held-out"])
        for i, c in enumerate(RW_CASES):
            w.writerow(["Real-world Astana", c, 3, "tuning" if i < 30 else "held-out"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    J = {ds: {k: jl(f"{ds}_{k}") for k, _, _ in SETUPS} for ds in ("v3", "rw")}
    copy("report_kit", OUT / "01_report_kit")
    d = OUT / "02_detailed_reports"
    for f in ("VLM_FINDINGS.md", "VLM_JUDGE_REPORT.md", "TUNING_RESULTS.md", "PAYLOAD_SIZES.md", "README.md"):
        copy(f, d / ("iter2_README.md" if f == "README.md" else f))
    copy("fusion_demo/README.md", d / "fusion_demo_README.md")
    for f in ("FINDINGS.md", "REPORT.md", "STATUS_2026-11-11.md", "NEXT_STEPS_RESULTS.md", "REFINE_REPORT.md", "REFINE_FULL_REPORT.md"):
        copy(f, d / "october_detector_era_superseded" / f)
    statistics_folder()
    timing()
    example_cases(J)
    gallery(J)
    c = OUT / "06_code_snapshot"
    for p in list(ROOT.glob("*.py")) + list(ROOT.glob("*.md")):
        copy(p, c / "iter2" / p.name)
    copy("carla", c / "iter2" / "carla")
    copy("ops", c / "iter2" / "ops")
    for p in ITER1.glob("*.py"):
        copy(p, c / "iter1" / p.name)
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv"], capture_output=True, text=True).stdout
        (c / "environment.txt").write_text(f"Python {sys.version}\n\nGPU:\n{gpu}\npip freeze:\n{freeze}", encoding="utf-8")
    except Exception as e:
        print("environment:", e)
    ds_dir = OUT / "07_datasets"
    copy(paths.CARLA_V3 / "manifest.json", ds_dir / "carla_v3_manifest.json")
    for name in ("README.md", "README.txt"):
        copy(paths.CARLA_V3 / name, ds_dir / f"carla_v3_{name}") if (paths.CARLA_V3 / name).exists() else None
        copy(paths.REAL_WORLD_CORE.parent / name, ds_dir / f"real_world_{name}") if (paths.REAL_WORLD_CORE.parent / name).exists() else None
    copy("data/cs_cases/mapping.json", ds_dir / "cityscapes_100_case_to_image.json")
    copy(Path("../iter1/results/iteration1_palette_eval_100.json"), ds_dir / "iteration1_cityscapes_100_eval.json")
    print("HANDOFF_BUILT", OUT)


if __name__ == "__main__":
    main()
