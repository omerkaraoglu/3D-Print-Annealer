"""diag - probe what a rule fillet actually fillets: for each probe (rule type + feature sets) create it at the end
of the timeline, compare the concave-root census (gflib.root_edges) before / after, then DELETE it again.
Also flexes glass_t over 1.1 / 4.0 / 3.0 with the probe in place and records its health.
The design is left as it was (every probe fillet is deleted). Results -> scratchpad rule_probe.json."""
import importlib
import json
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

PROBES = [
    ("between tubes | flange", "between", ["Fastener tubes F1-F8"], ["Flange plate"]),
    ("all edges tubes+ribs", "all", ["Fastener tubes F1-F8", "Tube ribs F1-F4"], None),
    ("between land plate | flange", "between", ["Land plate + step wall (back)"], ["Flange plate"]),
]


def census():
    out = {}
    for g, e, m, z, o in L.root_edges(0.9):
        key = (g, round(m[0], 2), round(m[1], 2), round(m[2], 2))
        out[key] = o
    return out


def run(_context: str):
    L.check_doc()
    ups = L.des().userParameters
    base = census()
    res = []
    for name, kind, one, two in PROBES:
        ff = L.comp().features.filletFeatures
        ri = ff.createRuleFilletInput()
        if kind == "all":
            ri.setByAllEdges([L.feature(n) for n in one])
        else:
            ri.setByBetweenFacesOrFeatures([L.feature(n) for n in one], [L.feature(n) for n in two])
        ri.radius = L.VI("fillet_root")
        ri.topologyType = adsk.fusion.RuleFilletTopologyTypes.FilletsOnlyRuleFilletTopologyType
        ri.isRollingBallCorner = True
        f = ff.addRuleFillet(ri)
        after = census()
        gone = [list(k) + [list(base[k])] for k in base if k not in after]
        flex = []
        for g in ("1.1 mm", "4.0 mm", "3.0 mm"):
            ups.itemByName("glass_t").expression = g
            L.des().computeAll()
            n, bad = L.timeline_health()
            flex.append((g, f.faces.count if f.isValid else None, bad))
        res.append({"probe": name, "faces": f.faces.count, "filleted_edges": len(gone),
                     "groups": sorted(set(x[0] for x in gone)), "edges": gone[:80], "flex": flex})
        f.deleteMe()
    L.dump(res, "rule_probe.json")
    for r in res:
        print(r["probe"], r["faces"], r["filleted_edges"], r["groups"], r["flex"])
