"""10 - per stud hole FHn:
  'Stud FHn rib'   ONE radial rib (rib = 1.5 at the root, 1 deg draft) on the Z_FLANGE_BACK plane, from inside
                   the tube wall (hole radius + 1.0 from the centre) to rib_bury beyond the drafted body wall
                   face measured at the rib top, up to Z_STUD_TOP (flush with the tube top = washer seat).
                   Both ends are buried at every height, so the rib really fuses tube and wall (gap ~2.5 / 3.5).
  'Stud FHn hole'  dia stud_hole at Z_FRONT, cut up through flange and tube, 0.5 deg draft widening to the back.
No gussets (decision: the tube is loaded in compression straight into the flange/sheet; the gasket reaction
reaches it through the 2.5 flange + the rib over a 2.5 mm gap; gussets would add slots next to the tube and
a socket clash risk above Z -6.5, for no measurable gain).
Expects: 09 done. Leaves 20 features.
"""
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
    L.log("=== 10 start")
    b = L.body()
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        sk = L.new_sketch("Stud %s rib" % name, "Z_FLANGE_BACK plane")
        L.rrect(sk, *rib_rect(n, side), None)
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 1:
            raise RuntimeError("rib %s profiles %d" % (name, prof.count))
        L.extrude(prof, "join", "stud_boss_h - flange_t", +1, L.shrink(), "Stud %s rib" % name, b)
    L.log("10 ribs " + L.body_stats())
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        sk = L.new_sketch("Stud %s hole" % name, "Z_FRONT plane")
        L.circle(sk, n + "_x", n + "_y", "stud_hole")
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 1:
            raise RuntimeError("hole %s profiles %d" % (name, prof.count))
        L.extrude(prof, "cut", "stud_boss_h + 1 mm", +1, L.grow("draft_loc"), "Stud %s hole" % name, b)
    n, bad = L.timeline_health()
    L.log("10 holes %s; timeline %d unhealthy %s" % (L.body_stats(), n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
