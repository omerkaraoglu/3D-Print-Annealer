"""50 - stage 3 (GF-1.1), item 6: F5-F8 tube to step-wall blend R tube_sw_r (1.2) instead of R0.5.
RULE fillet (fillets only) between ['Fastener tubes F1-F8'] and ['Land plate + step wall (back)'], inserted just
BEFORE 'Root fillets R0.5 - fastener tubes + tube ribs (rule)' (marker rolled back there), so that rule (R0.5)
re-collects only the remaining tube / rib roots. Only F5-F8 tubes touch the step wall (F1-F4 reach it through their
ribs, a different feature). Rule, not edge set: the step-wall back face vanishes at the level snap (glass 1.1).
Expects: 49 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

NAME = "Root fillets tube_sw_r - F5-F8 tube to step wall (rule)"


def run(_context: str):
    L.check_doc()
    L.log("=== 50 start")
    d = L.des()
    tl = d.timeline
    if L.feature(NAME) is not None:
        raise RuntimeError("exists already")
    nxt = L.feature("Root fillets R0.5 - fastener tubes + tube ribs (rule)")
    nxt.timelineObject.rollTo(True)
    f = L.rule_fillet(NAME, "between", ["Fastener tubes F1-F8"], ["Land plate + step wall (back)"], "tube_sw_r")
    nf = f.faces.count
    tl.moveToEnd()
    d.computeAll()
    n, bad = L.timeline_health()
    rr = L.feature("Root fillets R0.5 - fastener tubes + tube ribs (rule)")
    L.log("50 '%s' %d faces; tube rule %d faces; timeline %d unhealthy %s; %s" % (NAME, nf, rr.faces.count, n, bad,
                                                                                  L.body_stats()))
    print(NAME, nf, "tube rule faces", rr.faces.count, n, bad, L.body_stats())
