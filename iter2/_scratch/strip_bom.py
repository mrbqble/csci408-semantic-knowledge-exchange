from pathlib import Path
for name in ("commit_msg.txt", "pr_body.md"):
    p = Path("iter2/_scratch") / name
    b = p.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    p.write_bytes(b.replace(b"\r\n", b"\n"))
print("bom stripped")
