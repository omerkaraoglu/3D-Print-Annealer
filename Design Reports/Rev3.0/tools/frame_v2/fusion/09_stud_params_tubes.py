"""09 - stud-hole parameters fhN_x / fhN_y (N = 1..10; the coordinate on the stud line is an expression of
stud_yt / stud_yb / stud_xl / stud_xr, the other one a value) and the ten stud tubes 'Stud FHn tube':
circle dia stud_boss_od on the Z_STUD_TOP plane, joined toward the front down to Z_FRONT (through the flange
plate, buried in it) with 1 deg draft growing toward the front (dia 10.0 at the top, 10.087 at the flange
back face, 10.175 at Z_FRONT).
Expects: 08 done. Leaves 10 user-parameter pairs + 10 features.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

SIDE = {"T": "top edge", "R": "right edge", "B": "bottom edge", "L": "left edge"}


def run(_context: str):
    L.check_doc()
    L.log("=== 09 start")
    b = L.body()
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        L.set_param(n + "_x", xe, "mm", "stud hole %s x abs (KiCad), %s; hole_pattern_calc.py" % (name, SIDE[side]))
        L.set_param(n + "_y", ye, "mm", "stud hole %s y abs (KiCad, y down), %s" % (name, SIDE[side]))
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        sk = L.new_sketch("Stud %s tube" % name, "Z_STUD_TOP plane")
        L.circle(sk, n + "_x", n + "_y", "stud_boss_od")
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 1:
            raise RuntimeError("tube %s profiles %d" % (name, prof.count))
        L.extrude(prof, "join", "stud_boss_h", -1, L.grow(), "Stud %s tube" % name, b)
    n, bad = L.timeline_health()
    L.log("09 tubes %s; timeline %d unhealthy %s; holes %s" % (
        L.body_stats(), n, bad, [(nm, round(L.P(nm.lower() + "_x"), 3), round(L.P(nm.lower() + "_y"), 3))
                                 for nm, _, _, _ in L.STUDS]))
    L.show_iso()
    print(L.body_stats(), n, bad)
