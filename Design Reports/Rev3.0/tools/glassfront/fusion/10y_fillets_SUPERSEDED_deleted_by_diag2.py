"""10y - (SUPERSEDED: ran once, its 5 fillets were deleted by diag_rule_fillet_probe2.py because the tube "all edges" rule also took the wall and boss roots of the land-plate back at glass 3.0 but not at 4.0 - parameter-dependent coverage) root fillets R0.5, part 1 (v2 order: studs first, then bosses, cells, rib sides, shelf back):
  'Root fillets R0.5 - fastener tubes + tube ribs (rule)'  RULE fillet, all concave edges of the faces of
        'Fastener tubes F1-F8' and 'Tube ribs F1-F4'. A rule because these roots change topology with glass_t
        (tube top above / below the step-wall back at 3.5, step wall gone behind the flange at the snap 1.1);
        diag_rule_fillet_probe showed it stays healthy at 1.1 / 4.0 / 3.0, an edge set would lose its references.
  edge sets (topology independent of the flex parameters; gflib.EDGE_SETS, edges grouped by creating features):
        'PCB bosses on the walls', 'corner cells + cell ribs + cell bosses', 'PCB support rib sides',
        'shelf back (not into the tail pocket)' (the two bottom segments that end at the tail-pocket side faces stay
        sharp as in v2, corners 3 / 4).
Expects: 07b done, no fillets yet."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

SETS = ["PCB bosses on the walls", "corner cells + cell ribs + cell bosses", "PCB support rib sides",
        "shelf back (not into the tail pocket)"]


def run(_context: str):
    L.check_doc()
    L.log("=== 10 start")
    out = []
    f = L.rule_fillet("Root fillets R0.5 - fastener tubes + tube ribs (rule)", "all",
                      ["Fastener tubes F1-F8", "Tube ribs F1-F4"])
    out.append(("tubes + ribs (rule)", f.faces.count))
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("unhealthy after the tube rule fillet: %s" % bad)
    for s in SETS:
        f, k = L.fillet_set(s)
        out.append((s, k))
        n, bad = L.timeline_health()
        if bad:
            raise RuntimeError("unhealthy after %s: %s" % (s, bad))
    L.log("10 %s; %s; timeline %d" % (out, L.body_stats(), n))
    print(out, L.body_stats(), n, bad)
