"""Drawing comparison of two sheet files, UUID-free: symbols (position, rotation, mirror, every field: value, position,
hidden), wires, labels, power symbols, junctions, no-connects, texts, rectangles, title block.
    python -I geomdiff.py <a.kicad_sch> <b.kicad_sch>"""
import sys
from core import parse, find, first, getprop

def r(v):
    return round(float(v), 3)

def items(path):
    t = parse(open(path, encoding="utf-8").read())
    out = {}
    syms, pw = {}, set()
    for s in find(t, "symbol"):
        ref = getprop(s, "Reference")
        at = first(s, "at"); m = first(s, "mirror")
        flds = []
        for p in find(s, "property"):
            pa = first(p, "at")
            hid = any(isinstance(h, list) and h and h[0] == "hide" for h in p)
            eff = first(p, "effects"); j = first(eff, "justify")
            flds.append((p[1], p[2] if p[1] != "Reference" or not ref.startswith("#") else "#", r(pa[1]), r(pa[2]), r(pa[3]) if len(pa) > 3 else 0, hid, str(j[1:]) if j else ""))
        key = (first(s, "lib_id")[1], r(at[1]), r(at[2]), r(at[3]) if len(at) > 3 else 0, str(m[1]) if m else "")
        if ref.startswith("#"):
            pw.add(key + (tuple(f for f in flds if f[0] == "Value"),))
        else:
            syms[ref] = key + (tuple(sorted(flds)), str(first(s, "uuid")[1]))
    out["symbols"] = syms
    out["power"] = pw
    out["wire"] = {tuple(sorted(((r(x[1]), r(x[2])) for x in find(first(w, "pts"), "xy")))) for w in find(t, "wire")}
    for k in ("label", "global_label"):
        out[k] = {(l[1], r(first(l, "at")[1]), r(first(l, "at")[2]), r(first(l, "at")[3])) for l in find(t, k)}
    out["junction"] = {(r(first(j, "at")[1]), r(first(j, "at")[2])) for j in find(t, "junction")}
    out["no_connect"] = {(r(first(j, "at")[1]), r(first(j, "at")[2])) for j in find(t, "no_connect")}
    out["text"] = {(x[1], r(first(x, "at")[1]), r(first(x, "at")[2])) for x in find(t, "text")}
    out["rectangle"] = {(r(first(x, "start")[1]), r(first(x, "start")[2]), r(first(x, "end")[1]), r(first(x, "end")[2])) for x in find(t, "rectangle")}
    tb = first(t, "title_block")
    out["title"] = {str(x) for x in tb[1:]} if tb else set()
    out["lib_symbols"] = {s[1] for s in find(first(t, "lib_symbols"), "symbol")}
    return out

a, b = items(sys.argv[1]), items(sys.argv[2])
nd = 0
for k in a:
    if k == "symbols":
        for ref in sorted(set(a[k]) | set(b[k])):
            if a[k].get(ref) != b[k].get(ref):
                nd += 1
                print("  symbol %s:\n    A %s\n    B %s" % (ref, a[k].get(ref), b[k].get(ref)))
        continue
    only_a, only_b = a[k] - b[k], b[k] - a[k]
    if only_a or only_b:
        nd += len(only_a) + len(only_b)
        print("  %s: only in A %d, only in B %d" % (k, len(only_a), len(only_b)))
        for x in sorted(only_a, key=str)[:40]: print("    A", x)
        for x in sorted(only_b, key=str)[:40]: print("    B", x)
print("differences:", nd)
