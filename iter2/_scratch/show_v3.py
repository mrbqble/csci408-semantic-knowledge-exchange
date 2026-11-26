import json
s = json.load(open("results/v3/analysis/summary.json"))
keys = ["n_cases", "mean_cars_4wheel", "gt_mean_cars_4wheel", "cars_4wheel_mae_vs_gt", "cars_4wheel_bias_vs_gt", "cars_4wheel_within1_vs_gt", "mean_pedestrians", "vehicle_recall", "vehicle_precision", "person_recall"]
for v, d in s["variants"].items():
    print(v, {k: round(d[k], 2) for k in keys if d.get(k) is not None})
print("paired", {k: (round(v["mean_diff"], 2), [round(x, 2) for x in v["ci95"]]) for k, v in s["paired_abs_error_vs_gt"].items()})
