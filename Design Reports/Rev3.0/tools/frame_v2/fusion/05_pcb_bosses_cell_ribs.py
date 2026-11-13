"""05 - nine PCB screw bosses + corner-cell ribs.

* 'PCB bosses H1-H9': circles dia boss_od at (hN_x, hN_y) on the Z_PCB plane, joined toward -Z down to Z_FRONT
  with 1 deg draft growing toward the front (dia 8.0 at Z_PCB, 8.385 at Z_FRONT). Built BEFORE the pocket /
  lead-in / above-shelf cuts (06) so those cuts trim them, and AFTER the corner cells so H6/H7 stand in the cells.
* Corner-cell ribs (rib 1.5 at the root, 1 deg draft, Z_CELL_FLOOR -> Z_CELL_RIB_TOP):
    'Cell ribs boss to beam': along y at x = h7_x / h6_x, from the boss centre to the bottom cell wall + rib_bury
    'Cell ribs across':      along x at y = crib_y, from the outer wall (pocket_x0 - rib_bury) to the tail wall
                             face + rib_bury (left cell) and mirrored (right cell)
  Separate features for the two directions (crossing rectangles in one tapered extrude would taper the
  internal boundaries of the split profiles).

Expects: 04 done. Leaves: 3 features, body 'Frame v2'.
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
    L.log("=== 05 start")
    b = L.body()
    sk = L.new_sketch("PCB bosses H1-H9", "Z_PCB plane")
    for i in range(1, 10):
        L.circle(sk, "h%d_x" % i, "h%d_y" % i, "boss_od")
    sk.isComputeDeferred = False
    prof = L.pick_profiles(sk, lambda a, bb: True)
    if prof.count != 9:
        raise RuntimeError("boss profiles %d" % prof.count)
    L.extrude(prof, "join", "Z_PCB - Z_FRONT", -1, L.grow(), "PCB bosses H1-H9", b)
    L.log("05 bosses: " + L.body_stats())

    # ribs along y (boss -> bottom cell wall)
    sk2 = L.new_sketch("Cell ribs boss to beam", "Z_CELL_FLOOR plane")
    for h in ("h7", "h6"):
        L.rrect(sk2, "%s_x - rib / 2" % h, "%s_x + rib / 2" % h, "%s_y" % h, "tr_y1 + rib_bury", None)
    sk2.isComputeDeferred = False
    prof2 = L.pick_profiles(sk2, lambda a, bb: True)
    if prof2.count != 2:
        raise RuntimeError("cell rib A profiles %d" % prof2.count)
    L.extrude(prof2, "join", "cell_rib_h - wall", +1, L.shrink(), "Cell ribs boss to beam", b)

    sk3 = L.new_sketch("Cell ribs across", "Z_CELL_FLOOR plane")
    L.rrect(sk3, "pocket_x0 - rib_bury", "tr_x0 - wall + ( Z_CELL_FLOOR - Z_FRONT ) * tan(draft) + rib_bury",
            "crib_y - rib / 2", "crib_y + rib / 2", None)
    L.rrect(sk3, "tr_x1 + wall - ( Z_CELL_FLOOR - Z_FRONT ) * tan(draft) - rib_bury", "pocket_x1 + rib_bury",
            "crib_y - rib / 2", "crib_y + rib / 2", None)
    sk3.isComputeDeferred = False
    prof3 = L.pick_profiles(sk3, lambda a, bb: True)
    if prof3.count != 2:
        raise RuntimeError("cell rib B profiles %d" % prof3.count)
    L.extrude(prof3, "join", "cell_rib_h - wall", +1, L.shrink(), "Cell ribs across", b)
    n, bad = L.timeline_health()
    L.log("05 ribs: %s; timeline %d unhealthy %s" % (L.body_stats(), n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
