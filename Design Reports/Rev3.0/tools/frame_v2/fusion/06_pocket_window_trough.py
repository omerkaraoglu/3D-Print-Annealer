"""06 - the cavities (v1 geometry):
  'Panel pocket'      pocket outline R pocket_r at Z_SEAT, cut toward the front through Z_FRONT, draft_loc
                      widening to the front (panel locating faces 0.5 deg).
  'Pocket lead-in'    0.8 x 45 deg at the mouth: outline offset li = leadin + (Z_SEAT - Z_FRONT - leadin)
                      * tan(draft_loc) on Z_FRONT, cut up 45 deg; it meets the drafted pocket face exactly at
                      Z_FRONT + leadin and runs on 0.2 into the pocket air (no cap on a face).
  'Above-shelf space' pocket outline at Z_SHELF_BACK, cut up through Z_PCB, 1 deg widening up.
  'Window'            window outline R win_r at Z_SEAT, cut up through the shelf, 1 deg widening up.
  'Tail pocket'       x tr_x0..tr_x1, y tr_y0..tr_y1 (R trough_r bottom corners, square top) on Z_FRONT, cut up
                      through Z_TROUGH_TOP, 1 deg widening up: removes the pocket wall and the shelf strip
                      y 119.0..119.25 over the pocket width (shelf end flush with the panel edge at Z_SEAT),
                      leaves the tail walls and the bottom beam of the 'Tail wall block'.
Expects: 05 done (bosses exist, so these cuts trim them). Leaves 5 cut features.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

LI = "( leadin + ( Z_SEAT - Z_FRONT - leadin ) * tan(draft_loc) )"


def one(sk, n=1):
    sk.isComputeDeferred = False
    pr = L.pick_profiles(sk, lambda a, bb: True)
    if pr.count != n:
        raise RuntimeError("%s: %d profiles" % (sk.name, pr.count))
    return pr


def run(_context: str):
    L.check_doc()
    L.log("=== 06 start")
    b = L.body()
    sk = L.new_sketch("Panel pocket", "Z_SEAT plane")
    L.rrect(sk, "pocket_x0", "pocket_x1", "pocket_y0", "pocket_y1", "pocket_r")
    L.extrude(one(sk), "cut", "Z_SEAT - Z_FRONT + 1 mm", -1, L.grow("draft_loc"), "Panel pocket", b)
    L.log("06 pocket " + L.body_stats())

    sk = L.new_sketch("Pocket lead-in", "Z_FRONT plane")
    L.rrect(sk, "pocket_x0 - " + LI, "pocket_x1 + " + LI, "pocket_y0 - " + LI, "pocket_y1 + " + LI,
            "pocket_r + " + LI)
    L.extrude(one(sk), "cut", "leadin + 0.2 mm", +1, L.shrink("45 deg"), "Pocket lead-in", b)
    L.log("06 lead-in " + L.body_stats())

    sk = L.new_sketch("Above-shelf space", "Z_SHELF_BACK plane")
    L.rrect(sk, "pocket_x0", "pocket_x1", "pocket_y0", "pocket_y1", "pocket_r")
    L.extrude(one(sk), "cut", "Z_PCB - Z_SHELF_BACK + 1 mm", +1, L.grow(), "Above-shelf space", b)
    L.log("06 above-shelf " + L.body_stats())

    sk = L.new_sketch("Window", "Z_SEAT plane")
    L.rrect(sk, "win_x0", "win_x1", "win_y0", "win_y1", "win_r")
    L.extrude(one(sk), "cut", "shelf_t + 1 mm", +1, L.grow(), "Window", b)
    L.log("06 window " + L.body_stats())

    sk = L.new_sketch("Tail pocket", "Z_FRONT plane")
    L.rrect(sk, "tr_x0", "tr_x1", "tr_y0", "tr_y1", "trough_r", corners={"bl", "br"})
    L.extrude(one(sk), "cut", "Z_TROUGH_TOP - Z_FRONT + 1 mm", +1, L.grow(), "Tail pocket", b)
    n, bad = L.timeline_health()
    L.log("06 tail pocket %s; timeline %d unhealthy %s" % (L.body_stats(), n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
