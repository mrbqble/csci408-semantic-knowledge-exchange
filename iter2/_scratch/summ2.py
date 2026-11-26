import json
s = json.load(open("results/pilot_cs/analysis/summary.json"))
keys = ["mean_cars_4wheel","cars_4wheel_mae_vs_gt","cars_4wheel_bias_vs_gt","cars_4wheel_within1_vs_gt","cars_4wheel_pearson_vs_gt","mean_pedestrians",
        "vehicle_recall","vehicle_precision","person_recall","person_precision","vehicle_count_abs_err_vs_oracle","person_count_abs_err_vs_oracle"]
print("GT mean cars", s["variants"]["k1"].get("gt_mean_cars_4wheel"), "| GT mean peds", s["variants"]["k1"].get("gt_mean_pedestrians"))
print(f"{'variant':16}" + "".join(f"{k[:14]:>15}" for k in keys))
for v, d in s["variants"].items():
    print(f"{v:16}" + "".join(f"{d[k]:15.2f}" if d.get(k) is not None else f"{'-':>15}" for k in keys))
print("\npaired |err| vs GT, variant minus k1 (negative = better than k1):")
for k, v in s["paired_abs_error_vs_gt"].items():
    print(" ", k, v and {"n": v["n"], "mean_diff": round(v["mean_diff"], 2), "ci95": [round(x, 2) for x in v["ci95"]]})
