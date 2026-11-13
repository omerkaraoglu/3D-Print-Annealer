"""43b - v2.1 stud SLOTS (coordinator item 2): 'Stud FHn slot' = stadium stud_hole wide x (stud_hole +
stud_slot) long, axis along the edge (X for the top/bottom rows, Y for the side columns), centred on (fhN_x,
fhN_y), cut from Z_FRONT up through flange and tube with draft_loc widening to the back. Sketched as a centre
rectangle (stud_slot x stud_hole) + two end circles (dia stud_hole); the growing taper makes the union a clean
drafted stadium (the end cones and the side planes stay tangent at every height).
Expects: 43a done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 43b start")
    b = L.body()
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        x, y = n + "_x", n + "_y"
        sk = L.new_sketch("Stud %s slot" % name, "Z_FRONT plane")
        if side in "TB":
            L.rrect(sk, x + " - stud_slot / 2", x + " + stud_slot / 2", y + " - stud_hole / 2", y + " + stud_hole / 2", None)
            L.circle(sk, x + " - stud_slot / 2", y, "stud_hole")
            L.circle(sk, x + " + stud_slot / 2", y, "stud_hole")
        else:
            L.rrect(sk, x + " - stud_hole / 2", x + " + stud_hole / 2", y + " - stud_slot / 2", y + " + stud_slot / 2", None)
            L.circle(sk, x, y + " - stud_slot / 2", "stud_hole")
            L.circle(sk, x, y + " + stud_slot / 2", "stud_hole")
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        L.extrude(prof, "cut", "stud_boss_h + 1 mm", +1, L.grow("draft_loc"), "Stud %s slot" % name, b)
    n_, bad = L.timeline_health()
    L.log("43b %s; timeline %d unhealthy %s" % (L.body_stats(), n_, bad))
    L.show_iso()
    print(L.body_stats(), n_, bad)
