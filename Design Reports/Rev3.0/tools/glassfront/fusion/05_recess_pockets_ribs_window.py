"""05 - the cavities, in this order (support ribs inserted before the Window cut as v2.1):
  'Glass recess'           glass + s_lip_in (R6.4) on the Z_GLASS_FRONT plane (= lip top), cut +Z to Z_LAND,
                           1 deg narrowing to the back (A core): lip inner face / recess wall, floor = the land.
  'Clearance pocket'       panel + pocket_clr (R pocket_r) on the Z_SEAT plane, cut -Z through Z_LAND,
                           1 deg widening to the front (A core); its end face at Z_SEAT is the shelf front (v2 level).
  'Above-shelf space'      pocket outline on the Z_SHELF_BACK plane, cut +Z through Z_PCB, 1 deg widening up (v2).
  'PCB support ribs (26)'  v1 positions (rib<k>_a), width rib, wall end buried rib_bury into the moved pocket wall,
                           free end rib_overshoot past the window / shelf end (trimmed flush by the next cuts),
                           Z_SHELF_BACK -> Z_PCB, 1 deg (v2.1, gflib.rib_exprs).
  'Window'                 win_* (R win_r) on the Z_SEAT plane, cut +Z through Z_PCB + 1, 1 deg widening up (v2.1).
  'Tail pocket'            x tr_x0..tr_x1, y tr_y0..tr_y1 (R trough_R bottom corners) on the Z_LAND plane, cut +Z
                           through Z_TROUGH_TOP, 1 deg widening up: through opening, NO floor (the glass chin closes
                           the front); shelf end flush with the panel bottom edge at Z_SEAT (tr_y0 expression).
Expects: 04 done.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 05 start")
    b = L.body()
    uc = {}

    sk = L.new_sketch("Glass recess", "Z_GLASS_FRONT plane")
    L.grect(sk, "s_lip_in")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_LAND - Z_GLASS_FRONT", +1, L.shrink(), "Glass recess", b)

    sk = L.new_sketch("Clearance pocket", "Z_SEAT plane")
    L.rrect(sk, "pocket_x0", "pocket_x1", "pocket_y0", "pocket_y1", "pocket_r")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_SEAT - Z_LAND + 1 mm", -1, L.grow(), "Clearance pocket", b)

    sk = L.new_sketch("Above-shelf space", "Z_SHELF_BACK plane")
    L.rrect(sk, "pocket_x0", "pocket_x1", "pocket_y0", "pocket_y1", "pocket_r")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_PCB - Z_SHELF_BACK + 1 mm", +1, L.grow(), "Above-shelf space", b)

    sk = L.new_sketch("PCB support ribs (26)", "Z_SHELF_BACK plane")
    for k in range(1, 27):
        L.rrect(sk, *L.rib_exprs(k))
    pr = L.solve(sk, 26)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_PCB - Z_SHELF_BACK", +1, L.shrink(), "PCB support ribs (26)", b)

    sk = L.new_sketch("Window", "Z_SEAT plane")
    L.rrect(sk, "win_x0", "win_x1", "win_y0", "win_y1", "win_r")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_PCB - Z_SEAT + 1 mm", +1, L.grow(), "Window", b)

    sk = L.new_sketch("Tail pocket", "Z_LAND plane")
    L.rrect(sk, "tr_x0", "tr_x1", "tr_y0", "tr_y1", "trough_R", corners={"bl", "br"})
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_TROUGH_TOP - Z_LAND + 1 mm", +1, L.grow(), "Tail pocket", b)

    n, bad = L.timeline_health()
    L.log("05 %s; under-constrained %s; timeline %d unhealthy %s" % (L.body_stats(), uc, n, bad))
    L.show_iso()
    print(L.body_stats(), uc, n, bad)
