#!/usr/bin/env python3
"""Shareable results of Damir's fusion (19 Nov 2026): chart, paired-test table, pipeline figures, example cases, short summary.
Writes results_share/ (images + README.txt). Examples follow a fixed rule: the first cases by number in each group.
"""
import json
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import binom

import paths

OUT = Path("results_share")
SETUPS = [("paper_k1", "Single-camera MMSD (Damir)"), ("paper_multi", "Multi-camera, captions only (earlier)"),
          ("fuse_noip", "Control: img2img, no IP-Adapter"), ("fuse", "Damir's multi-camera fusion")]
DATASETS = [("v3", "CARLA v3 (112 cases)"), ("rw", "Real-world, Astana (61 cases)")]
COLORS = ["#8c8c8c", "#c9b27c", "#7fa7c9", "#1f5fa8"]
try:
    FONT, FONT_B = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 24)
except OSError:
    FONT = FONT_B = ImageFont.load_default()


def load(run):
    out = {}
    for line in open(f"results/vlm/{run}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
            out[r["case"]] = (r["numbers"]["score"], r["positions"]["score"])
    return out


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def mcnemar(a, b, cases):
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))


def chart(data):
    fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
    width = 0.2
    for i, (key, label) in enumerate(SETUPS):
        xs, ys, lo, hi = [], [], [], []
        for d, (ds, _) in enumerate(DATASETS):
            j = data[ds]["joint"][key]; n = len(j); k = sum(j.values())
            a, b = wilson(k, n)
            xs.append(d + (i - 1.5) * width); ys.append(100 * k / n); lo.append(100 * (k / n - a)); hi.append(100 * (b - k / n))
        bars = ax.bar(xs, ys, width * 0.92, color=COLORS[i], label=label, yerr=[lo, hi], capsize=4, error_kw={"elinewidth": 1})
        for x, y in zip(xs, ys):
            ax.text(x, y + 1.5, f"{y:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold" if key == "fuse" else "normal")
    ax.set_xticks(range(len(DATASETS))); ax.set_xticklabels([l for _, l in DATASETS], fontsize=12)
    ax.set_ylim(0, 105); ax.set_ylabel("Pairs judged preserved (%)", fontsize=12)
    ax.set_title("VLM judge (gemma-4-31b-it): car numbers AND positions preserved in the main camera's view", fontsize=13)
    ax.legend(loc="upper left", fontsize=10, frameon=False, ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, "Error bars: 95% Wilson intervals. Same judge, prompts and cases for every setup. Main camera = cam1. Generation at the photo's resolution (1920x1088).",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "01_results_chart.png"); plt.close(fig)


def table(data):
    rows = [("fuse", "paper_k1", "Fusion vs single-camera MMSD"), ("fuse", "fuse_noip", "Fusion vs control (what the other cameras add)"),
            ("fuse_noip", "paper_k1", "Control vs single-camera (second pass alone)"), ("fuse", "paper_multi", "Fusion vs captions-only multi-camera")]
    cells = []
    for a, b, label in rows:
        row = [label]
        for ds, _ in DATASETS:
            j = data[ds]["joint"]; cases = sorted(j[a])
            w, l, p = mcnemar(j[a], j[b], cases)
            row.append(f"{100 * (w - l) / len(cases):+.1f} pts  ({w} better / {l} worse, p = {p:.3f})")
        cells.append(row)
    fix = ["Fusion fixes / breaks (vs single camera)"]
    for ds, _ in DATASETS:
        j = data[ds]["joint"]; m, f = j["paper_k1"], j["fuse"]
        fail = [c for c in m if m[c] == 0]; ok = [c for c in m if m[c] == 1]
        fix.append(f"fixes {sum(f[c] for c in fail)} of {len(fail)} failures, breaks {sum(1 - f[c] for c in ok)} of {len(ok)} successes")
    cells.append(fix)
    fig, ax = plt.subplots(figsize=(13, 2.8), dpi=150); ax.axis("off")
    t = ax.table(cellText=cells, colLabels=["Paired comparison (McNemar, joint score)"] + [l for _, l in DATASETS], loc="center", cellLoc="left", colLoc="left",
                 colWidths=[0.34, 0.33, 0.33])
    t.auto_set_font_size(False); t.set_fontsize(10); t.scale(1, 1.6)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_text_props(fontweight="bold"); cell.set_facecolor("#e8eef6")
    fig.tight_layout(); fig.savefig(OUT / "02_paired_tests.png"); plt.close(fig)


def verdict(score):
    n, p = score
    return f"count {'OK' if n else 'WRONG'}, positions {'OK' if p else 'WRONG'}"


def examples(data, picks, title, name):
    W, H, PAD, HEAD = 640, 360, 10, 70
    sheet = Image.new("RGB", (3 * W + 4 * PAD, HEAD + len(picks) * (H + 40) + PAD), "white")
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 14), title, fill="black", font=FONT_B)
    for i, (ds, c) in enumerate(picks):
        y = HEAD + i * (H + 40)
        root = paths.CARLA_V3 if ds == "v3" else paths.REAL_WORLD_CORE
        orig = next(p for p in (root / f"case{c}").iterdir() if p.stem == "cam1")
        tiles = [(Image.open(orig), f"{'CARLA' if ds == 'v3' else 'Real-world'} case {c}: original (main camera)", None),
                 (Image.open(f"results/{ds}_paper/k1/case{c}_cam1.png"), "Single-camera MMSD", data[ds]["raw"]["paper_k1"][c]),
                 (Image.open(f"results/{ds}_fuse/fuse/case{c}.png"), "Damir's fusion", data[ds]["raw"]["fuse"][c])]
        for k, (im, label, score) in enumerate(tiles):
            x = PAD + k * (W + PAD)
            sheet.paste(im.convert("RGB").resize((W, H), Image.LANCZOS), (x, y))
            d.text((x, y + H + 6), label + (f": {verdict(score)}" if score else ""), fill=(0, 110, 0) if score and score[0] * score[1] else
                   ((180, 0, 0) if score else (0, 0, 0)), font=FONT)
    sheet.save(OUT / name, quality=90)


def main():
    OUT.mkdir(exist_ok=True)
    data = {}
    for ds, _ in DATASETS:
        raw = {k: load(f"{ds}_{k}") for k, _ in SETUPS}
        cases = sorted(set.intersection(*(set(v) for v in raw.values())))
        data[ds] = {"raw": raw, "joint": {k: {c: raw[k][c][0] * raw[k][c][1] for c in cases} for k in raw}}
    chart(data); table(data)
    shutil.copy("fusion_demo/rw_case1/pipeline.jpg", OUT / "03_pipeline_real_world_case1.jpg")
    shutil.copy("fusion_demo/v3_case10/pipeline.jpg", OUT / "04_pipeline_carla_case10.jpg")
    picks = {}
    for ds, _ in DATASETS:
        j = data[ds]["joint"]; m, f = j["paper_k1"], j["fuse"]
        picks[ds] = ([c for c in sorted(m) if m[c] == 0 and f[c] == 1], [c for c in sorted(m) if m[c] == 1 and f[c] == 0])
    examples(data, [("v3", c) for c in picks["v3"][0][:3]], "Single camera fails, fusion succeeds: CARLA (first three such cases by number)", "05_fixed_examples_carla.jpg")
    examples(data, [("rw", c) for c in picks["rw"][0][:2]], "Single camera fails, fusion succeeds: real-world (first two such cases by number)", "06_fixed_examples_real_world.jpg")
    examples(data, [("v3", picks["v3"][1][0]), ("rw", picks["rw"][1][0])], "Single camera succeeds, fusion fails (first such case in each dataset)", "07_broken_examples.jpg")
    print("picks:", picks)


if __name__ == "__main__":
    main()
