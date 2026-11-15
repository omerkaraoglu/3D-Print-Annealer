"""04 - the frame-v2 structure behind the land plate (v2 scripts 02/04/05 with Z_FRONT -> Z_LAND, pocket_clr 0.8):
  'Outer wall block'        outer_* (pocket +- wall, R frame_r) on the Z_LAND plane, +Z to Z_PCB, 1 deg shrinking
                            (v2 'Body (outer wall block)'; its front part is buried in the land plate).
  'Tail wall block'         x tr_x0 - wall .. tr_x1 + wall, y (tail_wall_step_y at Z_PCB) .. outer_y1 on the Z_LAND
                            plane, +Z to Z_TROUGH_TOP, 1 deg shrinking (v2.1: step face at y 129 at Z_PCB).
  'Corner cells'            v2 cells on the Z_LANDPLATE_BACK plane (cell floor = land-plate back), cut +Z through
                            Z_TROUGH_TOP, 1 deg widening up; the inner side lies on the tail-wall block's face.
  'PCB bosses H1-H9'        dia boss_od at Z_PCB, -Z to the middle of the land plate, 1 deg growing to the front.
  'Cell ribs boss to beam'  rib 1.5 along y at h7_x / h6_x, cell floor -> Z_CELL_RIB_TOP (v2).
  'Cell ribs across'        rib 1.5 along x at crib_y (v2).
Expects: 03 done.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

CELL_DX = "( Z_LANDPLATE_BACK - Z_LAND ) * tan(draft)"


def run(_context: str):
    L.check_doc()
    L.log("=== 04 start")
    b = L.body()
    uc = {}

    sk = L.new_sketch("Outer wall block", "Z_LAND plane")
    L.rrect(sk, "outer_x0", "outer_x1", "outer_y0", "outer_y1", "frame_r")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_PCB - Z_LAND", +1, L.shrink(), "Outer wall block", b)

    sk = L.new_sketch("Tail wall block", "Z_LAND plane")
    L.rrect(sk, "tr_x0 - wall", "tr_x1 + wall", "tail_wall_step_y - ( Z_PCB - Z_LAND ) * tan(draft)", "outer_y1", None)
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_TROUGH_TOP - Z_LAND", +1, L.shrink(), "Tail wall block", b)

    sk = L.new_sketch("Corner cells", "Z_LANDPLATE_BACK plane")
    L.rrect(sk, "pocket_x0", "tr_x0 - wall + " + CELL_DX, "pocket_y1 + wall", "tr_y1", "cell_r")
    L.rrect(sk, "tr_x1 + wall - " + CELL_DX, "pocket_x1", "pocket_y1 + wall", "tr_y1", "cell_r")
    pr = L.solve(sk, 2)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_TROUGH_TOP - Z_LANDPLATE_BACK + 1 mm", +1, L.grow(), "Corner cells", b)

    sk = L.new_sketch("PCB bosses H1-H9", "Z_PCB plane")
    for i in range(1, 10):
        L.circle(sk, "h%d_x" % i, "h%d_y" % i, "boss_od")
    pr = L.solve(sk, 9)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_PCB - Z_LAND - wall / 2", -1, L.grow(), "PCB bosses H1-H9", b)

    sk = L.new_sketch("Cell ribs boss to beam", "Z_LANDPLATE_BACK plane")
    for h in ("h7", "h6"):
        L.rrect(sk, "%s_x - rib / 2" % h, "%s_x + rib / 2" % h, "%s_y" % h, "tr_y1 + rib_bury", None)
    pr = L.solve(sk, 2)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_CELL_RIB_TOP - Z_LANDPLATE_BACK", +1, L.shrink(), "Cell ribs boss to beam", b)

    sk = L.new_sketch("Cell ribs across", "Z_LANDPLATE_BACK plane")
    L.rrect(sk, "pocket_x0 - rib_bury", "tr_x0 - wall + %s + rib_bury" % CELL_DX, "crib_y - rib / 2", "crib_y + rib / 2", None)
    L.rrect(sk, "tr_x1 + wall - %s - rib_bury" % CELL_DX, "pocket_x1 + rib_bury", "crib_y - rib / 2", "crib_y + rib / 2", None)
    pr = L.solve(sk, 2)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_CELL_RIB_TOP - Z_LANDPLATE_BACK", +1, L.shrink(), "Cell ribs across", b)

    n, bad = L.timeline_health()
    L.log("04 %s; under-constrained %s; timeline %d unhealthy %s" % (L.body_stats(), uc, n, bad))
    L.show_iso()
    print(L.body_stats(), uc, n, bad)
