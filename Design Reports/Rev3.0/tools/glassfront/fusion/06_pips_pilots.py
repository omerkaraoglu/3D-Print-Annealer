"""06 - small features on the land and in the bosses:
  'Pips P1-P8'          dia pip_d at pip<k>_x / _y (bead centre line, quarter points) on the Z_LAND plane, -Z by pip_h
                        to Z_PIP_TOP, 1 deg shrinking to the front (A side).
  'PCB pilots H1-H9'    dia pilot_d at Z_PCB, cut -Z by Z_PCB - Z_LAND - pilot_floor (blind, 1.0 floor behind the
                        land = the front face under the bosses), 0.5 deg narrowing to the front (v2).
  'PCB pilot reliefs'   dia cbore_d x cbore_h at the mouth, 0.5 deg (v2).
Expects: 05 done.
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
    L.log("=== 06 start")
    b = L.body()
    uc = {}
    sk = L.new_sketch("Pips P1-P8", "Z_LAND plane")
    for k in range(1, 9):
        L.circle(sk, "pip%d_x" % k, "pip%d_y" % k, "pip_d")
    pr = L.solve(sk, 8)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "pip_h", -1, L.shrink(), "Pips P1-P8", b)

    for name, dia, depth in (("PCB pilots H1-H9", "pilot_d", "Z_PCB - Z_LAND - pilot_floor"),
                             ("PCB pilot reliefs", "cbore_d", "cbore_h")):
        sk = L.new_sketch(name, "Z_PCB plane")
        for i in range(1, 10):
            L.circle(sk, "h%d_x" % i, "h%d_y" % i, dia)
        pr = L.solve(sk, 9)
        uc[sk.name] = L.under_constrained(sk)
        L.extrude(pr, "cut", depth, -1, L.shrink("draft_loc"), name, b)
    n, bad = L.timeline_health()
    L.log("06 %s; under-constrained %s; timeline %d unhealthy %s" % (L.body_stats(), uc, n, bad))
    print(L.body_stats(), uc, n, bad)
