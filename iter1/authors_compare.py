"""Print the authors' per-image compressed sizes and BLIP captions (local check, OMEN)."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "authors_check" / "SSMD-SAMR-main" / "SSMD" / "all_data_generated"
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    s = json.loads((d / f"{d.name}_compression_stats.json").read_text())
    c = json.loads((d / f"{d.name}_captions.json").read_text(encoding="utf-8"))
    blip = c["captions"]["blip"]["text"]
    print(f"{d.name}\tseg {s['segmentation']['compressed_size_bytes']}\tedge {s['edge']['compressed_size_bytes']}"
          f"\tcaption {len(blip.encode('utf-8'))}\t{blip}")
