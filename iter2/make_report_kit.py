#!/usr/bin/env python3
"""Report kit (21 Nov 2026): figures and CSV tables for the final report, generated directly from the VLM-judge results.
Writes report_kit/figures and report_kit/tables, and prints every judged setup.
"""
import csv
import json
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import binom

import paths
import vlm_judge as vj

KIT = Path("report_kit")
FIG, TAB = KIT / "figures", KIT / "tables"
DS = [("v3", "CARLA v3 (112 cases)"), ("rw", "Real-world, Astana (61 cases)")]


def load(run):
    out, f = {}, Path(f"results/vlm/{run}.jsonl")
    if f.exists():
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("numbers", {}).get("score") is not None and r.get("positions", {}).get("score") is not None:
                out[r["case"]] = (r["numbers"]["score"], r["positions"]["score"])
    return out


def joint(d):
    return {c: v[0] * v[1] for c, v in d.items()}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n; dd = 1 + z * z / n; c = (p + z * z / (2 * n)) / dd
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / dd
    return c - h, c + h


def mcnemar(a, b):
    cases = sorted(set(a) & set(b))
    w = sum(1 for c in cases if a[c] > b[c]); l = sum(1 for c in cases if a[c] < b[c])
    return len(cases), w, l, (1.0 if w + l == 0 else min(1.0, 2 * binom.cdf(min(w, l), w + l, 0.5)))


def all_setups():
    rows = []
    for run, (ds, _pattern, desc) in vj.RUNS.items():
        d = load(run)
        if not d:
            continue
        n = len(d); kn = sum(v[0] for v in d.values()); kp = sum(v[1] for v in d.values()); kj = sum(v[0] * v[1] for v in d.values())
        lo, hi = wilson(kj, n)
        rows.append({"setup": run, "dataset": ds, "description": desc, "n": n, "numbers_pct": round(100 * kn / n, 1),
                     "positions_pct": round(100 * kp / n, 1), "joint_pct": round(100 * kj / n, 1), "joint_ci95_low": round(100 * lo, 1),
                     "joint_ci95_high": round(100 * hi, 1)})
    with open(TAB / "all_setups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"{r['setup']:24} n={r['n']:3}  numbers {r['numbers_pct']:5.1f}  positions {r['positions_pct']:5.1f}  joint {r['joint_pct']:5.1f} "
              f"[{r['joint_ci95_low']:.0f}-{r['joint_ci95_high']:.0f}]")
    return {r["setup"]: r for r in rows}


MAIN = [("paper_k1", "Single-camera MMSD (seed paper)"), ("paper_multi", "Multi-camera, captions only"),
        ("fuse_noip", "Control: img2img, no IP-Adapter"), ("fuse", "Damir's fusion, supports 896x512"),
        ("fuseF", "Damir's fusion, supports full resolution")]
COLORS = ["#8c8c8c", "#c9b27c", "#9bb7d4", "#1f5fa8", "#5b8fd1"]


def bars(groups, series, values, cis, title, ylabel, out, colors, note=None, ylim=105, fmt="{:.1f}%"):
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    k = len(series); width = 0.8 / k
    for i, s in enumerate(series):
        xs = [g + (i - (k - 1) / 2) * width for g in range(len(groups))]
        ys = [values[g][i] for g in range(len(groups))]
        err = None
        if cis:
            err = [[ys[g] - cis[g][i][0] for g in range(len(groups))], [cis[g][i][1] - ys[g] for g in range(len(groups))]]
        ax.bar(xs, ys, width * 0.92, color=colors[i], label=s, yerr=err, capsize=3, error_kw={"elinewidth": 1})
        for x, y in zip(xs, ys):
            ax.text(x, y + 1.2, fmt.format(y), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(groups, fontsize=11)
    ax.set_ylim(0, ylim); ax.set_ylabel(ylabel); ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9, frameon=False, ncol=2, loc="upper left"); ax.spines[["top", "right"]].set_visible(False)
    if note:
        fig.text(0.01, 0.01, note, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(out); plt.close(fig)


def main_chart(S):
    vals, cis = [], []
    for ds, _ in DS:
        vals.append([S[f"{ds}_{k}"]["joint_pct"] for k, _ in MAIN])
        cis.append([(S[f"{ds}_{k}"]["joint_ci95_low"], S[f"{ds}_{k}"]["joint_ci95_high"]) for k, _ in MAIN])
    bars([l for _, l in DS], [l for _, l in MAIN], vals, cis, "VLM judge: car numbers AND positions preserved in the main camera's view",
         "Pairs judged preserved (%)", FIG / "fig01_main_results.png", COLORS,
         "Judge gemma-4-31b-it, Damir's prompts. Error bars: 95% Wilson intervals. Main reconstruction at the paper's settings (photo resolution 1920x1088).")


def evolution_chart(S):
    steps = [("default", "First receiver:\n1024x576, captions"), ("both_fixes", "Damir's fixes:\n896x512 + ADE20K"),
             ("paper_k1", "Paper settings,\nsingle camera"), ("paper_multi", "Paper settings,\ncaptions only"),
             ("fuse", "Damir's fusion,\nsupports 896x512"), ("fuseF", "Damir's fusion,\nsupports full res")]
    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=150)
    for i, (ds, label) in enumerate(DS):
        ys = [S[f"{ds}_{k}"]["joint_pct"] for k, _ in steps]
        ax.plot(range(len(steps)), ys, marker="o", lw=2, label=label, color=["#c0504d", "#1f5fa8"][i])
        for x, y in enumerate(ys):
            ax.text(x, (y + 2) if i == 1 else (y - 5), f"{y:.1f}", ha="center", fontsize=9, color=["#c0504d", "#1f5fa8"][i])
    ax.set_xticks(range(len(steps))); ax.set_xticklabels([l for _, l in steps], fontsize=9)
    ax.set_ylim(0, 100); ax.set_ylabel("Joint success (%)"); ax.legend(frameon=False)
    ax.set_title("How the receiver changed the VLM-judge score (same judge, same cases)", fontsize=12)
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(FIG / "fig02_receiver_evolution.png"); plt.close(fig)


def paired_tables(S):
    comps = [("fuse", "paper_k1", "Fusion (896x512 supports) vs single-camera MMSD"), ("fuse", "fuse_noip", "Fusion vs control (what the other cameras add)"),
             ("fuse_noip", "paper_k1", "Control vs single camera (second pass alone)"), ("fuse", "paper_multi", "Fusion vs captions-only multi-camera"),
             ("paper_multi", "paper_k1", "Captions-only multi-camera vs single camera"), ("fuseF", "paper_k1", "Fusion (full-res supports) vs single camera"),
             ("fuseF", "fuse", "Full-res supports vs 896x512 supports"), ("both_fixes", "default", "Damir's two fixes vs first receiver"),
             ("resolution_only", "default", "Working resolution alone vs first receiver"), ("palette_only", "default", "ADE20K palette alone vs first receiver")]
    rows = []
    for a, b, label in comps:
        row = {"comparison": label}
        for ds, _ in DS:
            n, w, l, p = mcnemar(joint(load(f"{ds}_{a}")), joint(load(f"{ds}_{b}")))
            row[f"{ds}_n"] = n; row[f"{ds}_diff_pts"] = round(100 * (w - l) / n, 1) if n else ""; row[f"{ds}_better"] = w; row[f"{ds}_worse"] = l; row[f"{ds}_p"] = round(p, 3)
        rows.append(row)
    with open(TAB / "paired_tests.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    cells = [[r["comparison"]] + [f"{r[f'{ds}_diff_pts']:+.1f} pts ({r[f'{ds}_better']}/{r[f'{ds}_worse']}, p = {r[f'{ds}_p']:.3f})" for ds, _ in DS] for r in rows]
    fig, ax = plt.subplots(figsize=(13, 4.2), dpi=150); ax.axis("off")
    t = ax.table(cellText=cells, colLabels=["Paired comparison (McNemar exact test, joint score)"] + [l for _, l in DS], loc="center", cellLoc="left",
                 colLoc="left", colWidths=[0.42, 0.29, 0.29])
    t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.5)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_text_props(fontweight="bold"); cell.set_facecolor("#e8eef6")
    fig.tight_layout(); fig.savefig(FIG / "fig03_paired_tests.png"); plt.close(fig)
    for r in rows:
        print(r)


def tuning():
    cands = [("fuseF", "strength 0.5\nIP 1.0 (default)"), ("fuseF_st0.3", "strength 0.3"), ("fuseF_st0.4", "strength 0.4"), ("fuseF_st0.6", "strength 0.6"),
             ("fuseF_ip0.5", "IP scale 0.5"), ("fuseF_ip0.75", "IP scale 0.75")]
    tune = {"v3": list(range(1, 57)), "rw": [1 + 6 * k for k in range(30)]}
    D = {k: {ds: joint(load(f"{ds}_{k}")) for ds in tune} for k, _ in cands}
    common = {ds: [c for c in tune[ds] if all(c in D[k][ds] for k, _ in cands)] for ds in tune}
    rows = []
    for k, label in cands:
        v = sum(D[k]["v3"][c] for c in common["v3"]); r = sum(D[k]["rw"][c] for c in common["rw"])
        rows.append({"setting": label.replace("\n", " "), "carla_tuning_half": v, "carla_n": len(common["v3"]), "real_world_tuning_half": r,
                     "real_world_n": len(common["rw"]), "total": v + r})
    with open(TAB / "tuning.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    xs = range(len(rows))
    ax.bar(xs, [r["carla_tuning_half"] for r in rows], color="#5b8fd1", label=f"CARLA (n = {rows[0]['carla_n']})")
    ax.bar(xs, [r["real_world_tuning_half"] for r in rows], bottom=[r["carla_tuning_half"] for r in rows], color="#c9b27c",
           label=f"Real-world (n = {rows[0]['real_world_n']})")
    for x, r in zip(xs, rows):
        ax.text(x, r["total"] + 0.8, str(r["total"]), ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(list(xs)); ax.set_xticklabels([l for _, l in cands], fontsize=9); ax.set_ylabel("Joint successes on the tuning half")
    ax.set_ylim(0, max(r["total"] for r in rows) + 10); ax.legend(frameon=False, loc="lower right")
    ax.set_title("Tuning of Damir's fusion (full-resolution supports): flat between strength 0.4-0.6 and IP scale 0.75-1.0", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(FIG / "fig04_tuning.png"); plt.close(fig)
    print(rows)


def support_by_cameras():
    m = json.loads((paths.CARLA_V3 / "manifest.json").read_text())
    ncam = {int(str(c["case"]).replace("case", "")): c["n_cameras"] for c in m["cases"]}
    S, H, F = joint(load("v3_paper_k1")), joint(load("v3_fuse")), joint(load("v3_fuseF"))
    rows = []
    for k in sorted(set(ncam.values())):
        cs = [c for c in F if ncam.get(c) == k and c in H and c in S]
        rows.append({"group": f"CARLA, {k} cameras ({k - 1} supporting)", "n": len(cs), "single": sum(S[c] for c in cs), "fusion_896": sum(H[c] for c in cs),
                     "fusion_fullres": sum(F[c] for c in cs)})
    S2, H2, F2 = joint(load("rw_paper_k1")), joint(load("rw_fuse")), joint(load("rw_fuseF"))
    cs = [c for c in F2 if c in H2 and c in S2]
    rows.append({"group": "Real-world, 3 phones (2 supporting)", "n": len(cs), "single": sum(S2[c] for c in cs), "fusion_896": sum(H2[c] for c in cs),
                 "fusion_fullres": sum(F2[c] for c in cs)})
    with open(TAB / "support_resolution_by_cameras.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    vals = [[100 * r["single"] / r["n"], 100 * r["fusion_896"] / r["n"], 100 * r["fusion_fullres"] / r["n"]] for r in rows]
    bars([f"{r['group'].split(' (')[0]}\n(n = {r['n']})" for r in rows], ["Single camera", "Fusion, supports 896x512", "Fusion, supports full resolution"], vals, None,
         "Supporting-reconstruction resolution by number of cameras: the split follows the dataset, not the number of views", "Joint success (%)",
         FIG / "fig05_support_resolution_by_cameras.png", ["#8c8c8c", "#1f5fa8", "#5b8fd1"])
    print(rows)


def payload_chart():
    # per camera photo, KB, from PAYLOAD_SIZES.md (payload_sizes.py)
    rows = [("CARLA, paper payload\n(map 1024x576, edges full res)", 5.05, 51.07, 0.04), ("CARLA, working size\n(896x512)", 4.36, 16.44, 0.04),
            ("Real-world, paper payload", 4.03, 46.62, 0.04), ("Real-world, working size\n(896x512)", 3.48, 12.73, 0.04)]
    with open(TAB / "payload_sizes_kb.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow(["payload", "segmentation_map_kb", "edge_map_kb", "caption_kb", "total_kb"])
        for name, s, e, c in rows:
            wr.writerow([name.replace("\n", " "), s, e, c, round(s + e + c, 2)])
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    xs = range(len(rows))
    ax.bar(xs, [r[1] for r in rows], color="#7fa7c9", label="segmentation map")
    ax.bar(xs, [r[2] for r in rows], bottom=[r[1] for r in rows], color="#1f5fa8", label="edge map")
    for x, r in zip(xs, rows):
        ax.text(x, r[1] + r[2] + 1, f"{r[1] + r[2] + r[3]:.1f} KB", ha="center", fontsize=10)
    ax.set_xticks(list(xs)); ax.set_xticklabels([r[0] for r in rows], fontsize=9); ax.set_ylabel("KB per camera photo")
    ax.set_title("Payload size per element (caption about 0.04 KB); photo as JPEG q90: CARLA 531 KB, real-world 376 KB", fontsize=11)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(FIG / "fig06_payload_sizes.png"); plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
    S = all_setups()
    main_chart(S); evolution_chart(S); paired_tables(S); tuning(); support_by_cameras(); payload_chart()
    for src, dst in (("results_share/03_pipeline_real_world_case1.jpg", "fig07_pipeline_real_world_case1.jpg"),
                     ("results_share/04_pipeline_carla_case10.jpg", "fig08_pipeline_carla_case10.jpg"),
                     ("results_share/05_fixed_examples_carla.jpg", "fig09_examples_fixed_carla.jpg"),
                     ("results_share/06_fixed_examples_real_world.jpg", "fig10_examples_fixed_real_world.jpg"),
                     ("results_share/07_broken_examples.jpg", "fig11_examples_broken.jpg")):
        shutil.copy(src, FIG / dst)
    print("KIT_DONE")


if __name__ == "__main__":
    main()

