"""04 - tail-pocket wall block + corner cells.

* 'Tail wall block': rectangle x (tr_x0 - wall)..(tr_x1 + wall), y pocket_y1..outer_y1 on the Z_FRONT plane,
  joined from Z_FRONT up to Z_TROUGH_TOP with 1 deg draft (shrinking up). Its bottom face (y outer_y1) is the
  SAME drafted plane as the body's bottom face (same line at Z_FRONT, same draft) so the two merge. The
  tail pocket itself is cut later (06) through block + body, which leaves the two side walls and the beam.
* 'Corner cells': two rounded rectangles (R cell_r) on the Z_CELL_FLOOR plane, cut up through Z_TROUGH_TOP with
  1 deg draft (widening up). The cell side next to the tail wall is placed at
  (tr_x0 - wall) + (Z_CELL_FLOOR - Z_FRONT) * tan(draft) so that it lies ON the block's drafted face
  (no step, no sliver). Floor = Z_FRONT .. Z_CELL_FLOOR (flange plate + body).

Expects: 02 done. Leaves: features 'Tail wall block', 'Corner cells'.
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
    L.log("=== 04 start")
    b = L.body()
    sk = L.new_sketch("Tail wall block", "Z_FRONT plane")
    L.rrect(sk, "tr_x0 - wall", "tr_x1 + wall", "pocket_y1", "outer_y1", None)
    sk.isComputeDeferred = False
    prof = L.pick_profiles(sk, lambda a, bb: True)
    if prof.count != 1:
        raise RuntimeError("block profiles %d" % prof.count)
    L.extrude(prof, "join", "Z_TROUGH_TOP - Z_FRONT", +1, L.shrink(), "Tail wall block", b)
    L.log("04 block: " + L.body_stats())

    sk2 = L.new_sketch("Corner cells", "Z_CELL_FLOOR plane")
    L.rrect(sk2, "pocket_x0", "tr_x0 - wall + ( Z_CELL_FLOOR - Z_FRONT ) * tan(draft)",
            "pocket_y1 + wall", "tr_y1", "cell_r")
    L.rrect(sk2, "tr_x1 + wall - ( Z_CELL_FLOOR - Z_FRONT ) * tan(draft)", "pocket_x1",
            "pocket_y1 + wall", "tr_y1", "cell_r")
    sk2.isComputeDeferred = False
    prof2 = L.pick_profiles(sk2, lambda a, bb: True)
    if prof2.count != 2:
        raise RuntimeError("cell profiles %d" % prof2.count)
    L.extrude(prof2, "cut", "Z_TROUGH_TOP - Z_CELL_FLOOR + 1 mm", +1, L.grow(), "Corner cells", b)
    L.log("04 cells: " + L.body_stats())
    L.show_iso()
    print(L.body_stats())
