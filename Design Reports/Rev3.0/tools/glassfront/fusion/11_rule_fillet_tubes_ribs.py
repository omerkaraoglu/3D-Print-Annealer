"""11 - root fillet R0.5 of the fastener tubes and the tube ribs: RULE fillet (fillets only) on ALL concave edges of
the faces of 'Fastener tubes F1-F8' and 'Tube ribs F1-F4' (tube <-> flange back, tube <-> step wall incl. its root
fillet, tube top <-> step wall at glass 4.0, rib <-> tube, rib <-> flange back, rib <-> step wall, rib end <-> plate
at the snap). A rule because this topology changes with glass_t; the land-plate / wall / boss / step-wall roots
are already filleted by 10 (before the tubes), so the rule can only find tube and rib roots at every glass_t.
Expects: 10 done; tubes / ribs at the end of the timeline."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 11 start")
    L.des().timeline.moveToEnd()
    before = {}
    for g, e, m, z, o in L.root_edges(0.9):
        before[g] = before.get(g, 0) + 1
    f = L.rule_fillet("Root fillets R0.5 - fastener tubes + tube ribs (rule)", "all",
                      ["Fastener tubes F1-F8", "Tube ribs F1-F4"])
    after = {}
    for g, e, m, z, o in L.root_edges(0.9):
        after[g] = after.get(g, 0) + 1
    n, bad = L.timeline_health()
    L.log("11 rule: %d faces; roots before %s after %s; %s; timeline %d unhealthy %s" % (
        f.faces.count, before, after, L.body_stats(), n, bad))
    print(f.faces.count, before, after, L.body_stats(), n, bad)
