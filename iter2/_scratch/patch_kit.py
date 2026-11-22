from pathlib import Path
def patch(path, pairs):
    p = Path(path); t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert t.count(old) == 1, (path, t.count(old), old[:60]); t = t.replace(old, new)
    p.write_text(t, encoding="utf-8"); print("patched", path)
patch("report_kit/README.md", [("Bibol Assetbek, Ernur Kenzhaly,", "Bibol Assetbek, Yernur Kenzhaly,")])
patch("report_kit/1_datasets.md", [
 ("| 224 | 3-6 | 992 | 1920x1080 |", "| 224 | 3-6 | about 1,000 | 1920x1080 |"),
 ("- **Scenes:** typically dense, with 10-20 cars, many of them parked and distant. That makes \"same number of cars\" a strict test.",
  "- **Scenes:** dense, with about 11.5 cars per main-camera photo on average (the October detector count on the originals) and often 15-20, many of them parked and distant. That makes \"same number of cars\" a strict test."),
])
patch("report_kit/2_pipeline.md", [
 ("each scored 1 or 0. The judge is told to ignore appearance and background.",
  "each scored 1 or 0. The questions concern only cars (their number and positions), not the rest of the scene."),
])
