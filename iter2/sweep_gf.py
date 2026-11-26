import json, subprocess, sys
rows = []
for amin in (10, 30):
    for gate in (1.5, 2.5, 4.0):
        out = f"results/geofuse_a{amin}_g{gate}"
        subprocess.run([sys.executable, "geofuse.py", "--out", out, "--min-area", str(amin), "--gate", str(gate)], capture_output=True, check=True)
        s = json.load(open(out + "/summary.json"))
        for g in ("vehicle", "person"):
            for k, v in s["counts_vs_gt"][g].items():
                rows.append((amin, gate, g, k, v["mae"], v["bias"], v["within1"]))
print(f"{'minA':>5}{'gate':>6}{'group':>9}{'rule':>6}{'MAE':>7}{'bias':>7}{'within1':>9}")
for r in rows:
    if r[2] == "vehicle" or r[3] in ("F0", "F4", "F5"):
        print(f"{r[0]:5}{r[1]:6.1f}{r[2]:>9}{r[3]:>6}{r[4]:7.2f}{r[5]:7.2f}{r[6]:9.2f}")
