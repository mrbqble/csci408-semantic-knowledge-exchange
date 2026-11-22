from pathlib import Path
p = Path("blob_split.py"); t = p.read_text(encoding="utf-8")
old = """    k, mk = cv2.connectedComponents(core, connectivity=8)
    markers = mk.astype(np.int32)
    for i in range(1, n):                           # a blob without a marker keeps itself whole
        sel = cc == i
        if not (markers[sel] > 0).any():
            k += 1; markers[sel] = k - 1 + 0 if False else k
    return regrow(mask, markers)"""
new = """    k, mk = cv2.connectedComponents(core, connectivity=8)
    markers = mk.astype(np.int32)
    nxt = k                                         # next free label
    for i in range(1, n):                           # a blob without a marker keeps itself whole
        sel = cc == i
        if not (markers[sel] > 0).any():
            markers[sel] = nxt; nxt += 1
    return regrow(mask, markers)"""
assert t.count(old) == 1
p.write_text(t.replace(old, new), encoding="utf-8"); print("fixed")
