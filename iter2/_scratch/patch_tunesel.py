from pathlib import Path
p = Path("tune_select.py"); t = p.read_text(encoding="utf-8")
def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:70]); t = t.replace(old, new)
rep('''            w_, d_, s_ = load(f"{ds}_{run_}"), load(f"{ds}_fuseF"), load(f"{ds}_paper_k1")
            cases = [c for c in HOLD[ds] if c in w_ and c in d_ and c in s_]''', '''            w_, d_, s_, h_ = load(f"{ds}_{run_}"), load(f"{ds}_fuseF"), load(f"{ds}_paper_k1"), load(f"{ds}_fuse")
            cases = [c for c in HOLD[ds] if c in w_ and c in d_ and c in s_ and c in h_]''')
rep('''                                                        f"single camera {100*sum(s_[c] for c in cases)/n:.1f}% (n = {len(cases)})")''', '''                                                        f"896x512-support fusion {100*sum(h_[c] for c in cases)/n:.1f}%, "
                                                        f"single camera {100*sum(s_[c] for c in cases)/n:.1f}% (n = {len(cases)})")''')
rep('''            for key, (a, b) in {"winner vs current setting": (w_, d_), "winner vs single-camera MMSD": (w_, s_),
                                "current setting vs single-camera MMSD": (d_, s_)}.items():''', '''            for key, (a, b) in {"winner vs current setting": (w_, d_), "winner vs single-camera MMSD": (w_, s_),
                                "current setting vs single-camera MMSD": (d_, s_), "winner vs fusion with 896x512 supports": (w_, h_)}.items():''')
p.write_text(t, encoding="utf-8"); print("tune_select: 896x512-support comparison added to the held-out report")
