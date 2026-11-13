"""Which nets carry a PWR_FLAG / no-connect flag in a set of sheets (baseline by default)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, BASELINE, Doc, Target, sheet_clusters, getprop, first, find, key  # noqa
from model_check import drawn_items  # noqa

d = sys.argv[1] if len(sys.argv) > 1 else BASELINE
t = Target(os.path.join(BASELINE, "baseline.xml"), BASELINE)
for sheet, fn in FILES.items():
    doc = Doc(os.path.join(d, fn), sheet)
    wires, points = drawn_items(doc)
    juncs = [(float(first(j, "at")[1]), float(first(j, "at")[2])) for j in find(doc.tree, "junction")]
    cl, _ = sheet_clusters(wires, points, juncs)
    members = {}
    for tag, cid in cl.items():
        members.setdefault(cid, []).append(tag)
    for tag, cid in cl.items():
        if tag[0] == "pwr" and tag[1] == "PWR_FLAG":
            pins = [m for m in members[cid] if m[0] == "pin"]
            names = sorted({m[1] for m in members[cid] if m[0] != "pin" and m[1] != "PWR_FLAG"})
            print(sheet, "PWR_FLAG on", names, [t.pin_net[(m[1], m[2])] for m in pins][:1])
    ncpts = {key((float(first(n, "at")[1]), float(first(n, "at")[2]))) for n in find(doc.tree, "no_connect")}
    hit = []
    for ref, node in doc.symbols.items():
        for num, p, o, pd in doc.pins_of(node):
            if key(p) in ncpts:
                hit.append("%s.%s" % (ref, num))
    print(sheet, "NC flags on", len(ncpts), "->", " ".join(hit))
