"""diag 2 - which rule-fillet definition fillets exactly the tube / tube-rib / step-wall roots at every glass_t?
First deletes the fillets made by 10 (the 'all edges' tube rule picked up every concave edge of the land-plate back
face at glass 3.0 - wall and boss roots - but not at 4.0, because the F5-F8 tubes touch that face only when their
top is above it: coverage that changes with the parameter). Then, for each probe: census of the unfilleted roots
per group WITHOUT the probe and WITH it, at glass_t 3.0 / 4.0 / 2.0 / 1.1, plus health; the probe is deleted again.
Result -> scratchpad rule_probe2.json."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

T, R, F, LP = "Fastener tubes F1-F8", "Tube ribs F1-F4", "Flange plate", "Land plate + step wall (back)"
PROBES = [("P1 [tubes ribs] | [flange landplate]", [T, R], [F, LP]),
          ("P2 [tubes ribs flange] | [landplate]", [T, R, F], [LP]),
          ("P3 [flange] | [tubes ribs landplate]", [F], [T, R, LP]),
          ("P5 [tubes ribs] | [flange landplate tubes]", [T, R], [F, LP, T])]
GROUPS = ("tubes + tube ribs", "step wall to flange back", "wall to land plate", "PCB bosses on the walls")
GLASS = ("3.0 mm", "4.0 mm", "2.0 mm", "1.1 mm")


def counts():
    c = {}
    for g, e, m, z, o in L.root_edges(0.9):
        if g in GROUPS:
            c[g] = c.get(g, 0) + 1
    return c


def sweep(f=None):
    ups = L.des().userParameters
    out = []
    for g in GLASS:
        ups.itemByName("glass_t").expression = g
        L.des().computeAll()
        n, bad = L.timeline_health()
        out.append({"glass": g, "faces": (f.faces.count if (f is not None and f.isValid) else None),
                    "bad": [b[1] + ": " + b[3][:80] for b in bad], "unfilleted": counts()})
    ups.itemByName("glass_t").expression = "3.0 mm"
    L.des().computeAll()
    return out


def run(_context: str):
    L.check_doc()
    tl = L.des().timeline
    for i in range(tl.count - 1, -1, -1):
        it = tl.item(i)
        if it.name.startswith("Root fillets"):
            it.entity.deleteMe()
    res = [{"probe": "none", "sweep": sweep()}]
    for name, one, two in PROBES:
        f = L.rule_fillet("probe " + name, "between", one, two)
        res.append({"probe": name, "sweep": sweep(f)})
        f.deleteMe()
    L.dump(res, "rule_probe2.json")
    for r in res:
        print(r["probe"])
        for s in r["sweep"]:
            print("   ", s["glass"], s["faces"], s["unfilleted"], s["bad"])
    print(L.timeline_health(), L.body_stats())
