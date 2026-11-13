"""08 - PCB screw pilots and mouth reliefs in the nine bosses.
  'PCB pilots H1-H9'   dia pilot_d at Z_PCB, cut toward the front by Z_PCB - Z_FRONT - pilot_floor (blind, the
                       front face stays closed), 0.5 deg draft narrowing toward the front.
  'PCB pilot reliefs'  dia cbore_d x cbore_h at the mouth (Z_PCB), 0.5 deg draft.
Expects: 07 done. Leaves 2 cut features.
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
    L.log("=== 08 start")
    b = L.body()
    for name, dia, depth in (("PCB pilots H1-H9", "pilot_d", "Z_PCB - Z_FRONT - pilot_floor"),
                             ("PCB pilot reliefs", "cbore_d", "cbore_h")):
        sk = L.new_sketch(name, "Z_PCB plane")
        for i in range(1, 10):
            L.circle(sk, "h%d_x" % i, "h%d_y" % i, dia)
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a, bb: True)
        if prof.count != 9:
            raise RuntimeError("%s profiles %d" % (name, prof.count))
        L.extrude(prof, "cut", depth, -1, L.shrink("draft_loc"), name, b)
    n, bad = L.timeline_health()
    L.log("08 %s; timeline %d unhealthy %s" % (L.body_stats(), n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
