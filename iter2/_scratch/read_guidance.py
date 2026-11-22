import zipfile, sys, io
from pathlib import Path
base = Path(r"C:\Users\mrbqble\My Drive (bibol.assetbek@nu.edu.kz)\uni\04\01\CSCI 408")
for name in ("Final Report Guidance.pdf", "Final Presentation Guidance.pdf"):
    p = base / name
    print("=" * 30, name, p.stat().st_size, "bytes")
    if zipfile.is_zipfile(p):
        z = zipfile.ZipFile(p)
        txts = sorted([n for n in z.namelist() if n.endswith(".txt")], key=lambda n: int("".join(ch for ch in Path(n).stem if ch.isdigit()) or 0))
        for n in txts:
            print(f"--- page {n}"); print(z.read(n).decode("utf-8", "replace"))
    else:
        try:
            from pypdf import PdfReader
            r = PdfReader(str(p))
            for i, pg in enumerate(r.pages, 1):
                print(f"--- page {i}"); print(pg.extract_text())
        except Exception as e:
            print("cannot read:", e)
