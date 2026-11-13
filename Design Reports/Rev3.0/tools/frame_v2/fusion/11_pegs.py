"""11 - 'Pegs P1 P2': two locating pegs dia peg_d x peg_h on the front face of the corner-cell floors at
(peg1_x, peg1_y), (peg2_x, peg2_y), 0.5 deg draft narrowing toward the tip (into dia 3.2 holes in the sheet).
Feature is suppressed when the user parameter pegs_on = 0 (Fusion cannot link suppression to a parameter;
rerun this script after changing pegs_on).
Expects: 10 done. Leaves feature 'Pegs P1 P2'.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 11 start")
    b = L.body()
    f = L.feature("Pegs P1 P2")
    if f is None:
        v0 = b.physicalProperties.volume
        sk = L.new_sketch("Pegs P1 P2", "Z_FRONT plane")
        L.circle(sk, "peg1_x", "peg1_y", "peg_d")
        L.circle(sk, "peg2_x", "peg2_y", "peg_d")
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 2:
            raise RuntimeError("peg profiles %d" % prof.count)
        f = L.extrude(prof, "join", "peg_h", -1, L.shrink("draft_loc"), "Pegs P1 P2", b)
        dv = (L.body().physicalProperties.volume - v0) * 1000.0
        L.log("11 pegs added %.3f mm3 (expect ~2 x 5.6)" % dv)
        if dv < 5.0:
            raise RuntimeError("pegs did not join (dv %.3f mm3)" % dv)
    f.isSuppressed = L.P("pegs_on") < 0.5
    n, bad = L.timeline_health()
    L.log("11 %s; suppressed %s; timeline %d unhealthy %s" % (L.body_stats(), f.isSuppressed, n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
