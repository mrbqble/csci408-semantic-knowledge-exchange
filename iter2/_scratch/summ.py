import json
keys = ["n_cases","mean_cars_4wheel","gt_mean_cars_4wheel","cars_4wheel_mae_vs_gt","cars_4wheel_bias_vs_gt","cars_4wheel_within1_vs_gt","cars_4wheel_pearson_vs_gt",
        "mean_pedestrians","gt_mean_pedestrians","pedestrians_mae_vs_gt","pedestrians_bias_vs_gt","pedestrians_pearson_vs_gt",
        "vehicle_recall","vehicle_precision","person_recall","person_precision","vehicle_count_abs_err_vs_oracle","seconds"]
for pal in ("cs","ade"):
    s = json.load(open(f"results/pilot_{pal}/analysis/summary.json"))
    print("=====", pal, "| payload KB/cam", round(s.get("payload_per_camera_kb_mean",0),1), "| photo KB", round(s.get("original_photo_kb_mean",0),1))
    for v, d in s["variants"].items():
        print(f"-- {v}")
        print("   " + ", ".join(f"{k}={d[k]:.2f}" for k in keys if d.get(k) is not None))
