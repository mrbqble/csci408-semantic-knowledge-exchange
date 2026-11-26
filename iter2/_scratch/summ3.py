import json, csv, collections
a = "results/carla_v2/analysis/"
s = json.load(open(a + "summary.json"))
keys = ["n_cases","mean_cars_4wheel","gt_mean_cars_4wheel","cars_4wheel_mae_vs_gt","cars_4wheel_bias_vs_gt","cars_4wheel_within1_vs_gt","cars_4wheel_pearson_vs_gt",
        "mean_pedestrians","vehicle_recall","vehicle_precision","person_recall","person_precision","vehicle_count_abs_err_vs_oracle","seconds"]
for v, d in s["variants"].items():
    print(f"-- {v}: " + ", ".join(f"{k}={d[k]:.2f}" for k in keys if d.get(k) is not None))
print("paired:", {k: (round(v['mean_diff'],2), [round(x,2) for x in v['ci95']]) for k, v in s["paired_abs_error_vs_gt"].items()})
print("payload KB/cam", round(s["payload_per_camera_kb_mean"],1), "photo KB", round(s["original_photo_kb_mean"],1))
# by camera count
rows = list(csv.DictReader(open(a + "counts.csv")))
cams = {}
for c in json.load(open(r"C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd\manifest.json"))["cases"]:
    cams[f"case{c['case']}"] = c["n_cameras"]
by = collections.defaultdict(list)
for r in rows:
    if r["variant"] in ("k1", "prompt_only", "oracle_gen") and r["gt_cars"]:
        by[(cams[r["case"]], r["variant"])].append(int(r["cars_4wheel"]) - int(r["gt_cars"]))
print("signed car error vs GT by #cameras (k1 / prompt_only / oracle_gen):")
for n in (3, 4, 5, 6):
    print(n, {v: round(sum(by[(n, v)]) / len(by[(n, v)]), 2) for v in ("k1", "prompt_only", "oracle_gen")}, "cases", len(by[(n, "k1")]))
