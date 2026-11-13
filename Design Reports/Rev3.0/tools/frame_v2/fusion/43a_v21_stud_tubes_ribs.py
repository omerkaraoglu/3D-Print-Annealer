"""43a - v2.1 stud tubes + radial ribs at the new pattern (same recipe as 09/10): 'Stud FHn tube' (dia
stud_boss_od at Z_STUD_TOP, 1 deg draft growing to Z_FRONT) and 'Stud FHn rib' (rib 1.5, from hole radius + 1.0
to rib_bury into the drafted wall measured at the rib top, Z_FLANGE_BACK -> Z_STUD_TOP, 1 deg draft).
Expects: 42 done; fh1..fh10 = fv2lib.STUDS (41)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

TOPDR = "( Z_STUD_TOP - Z_FRONT ) * tan(draft)"


def rib_rect(n, side):
    h0 = "stud_hole / 2 + 1 mm"
    if side == "T":
        return (n + "_x - rib / 2", n + "_x + rib / 2", n + "_y + " + h0, "outer_y0 + rib_bury + " + TOPDR)
    if side == "B":
        return (n + "_x - rib / 2", n + "_x + rib / 2", "outer_y1 - rib_bury - " + TOPDR, n + "_y - " + h0)
    if side == "R":
        return ("outer_x1 - rib_bury - " + TOPDR, n + "_x - " + h0, n + "_y - rib / 2", n + "_y + rib / 2")
    return (n + "_x + " + h0, "outer_x0 + rib_bury + " + TOPDR, n + "_y - rib / 2", n + "_y + rib / 2")


def run(_context: str):
    L.check_doc()
    L.log("=== 43a start")
    b = L.body()
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        sk = L.new_sketch("Stud %s tube" % name, "Z_STUD_TOP plane")
        L.circle(sk, n + "_x", n + "_y", "stud_boss_od")
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 1:
            raise RuntimeError("tube %s profiles %d" % (name, prof.count))
        L.extrude(prof, "join", "stud_boss_h", -1, L.grow(), "Stud %s tube" % name, b)
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        sk = L.new_sketch("Stud %s rib" % name, "Z_FLANGE_BACK plane")
        L.rrect(sk, *rib_rect(n, side), None)
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 1:
            raise RuntimeError("rib %s profiles %d" % (name, prof.count))
        L.extrude(prof, "join", "stud_boss_h - flange_t", +1, L.shrink(), "Stud %s rib" % name, b)
    n_, bad = L.timeline_health()
    L.log("43a %s; timeline %d unhealthy %s" % (L.body_stats(), n_, bad))
    L.show_iso()
    print(L.body_stats(), n_, bad)
