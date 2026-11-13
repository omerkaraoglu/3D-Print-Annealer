"""07 - 26 PCB support ribs (v1 rectangles from v1_geometry.json, unchanged positions/widths/inner ends).
Only change vs v1: the end at the wall runs rib_bury = 0.5 into the wall (v1: 0.1), so the drafted rib end is
buried at every height (owner rule: rib ends overlap the wall >= 0.5). Ribs stand on the shelf back
(Z_SHELF_BACK) and end at Z_PCB (they bear the PCB back), 1.5 at the root, 1 deg draft.
Rib positions are fixed sketch geometry (not parameters): they were placed >= 1.0 mm from every B.Cu pad.

Expects: 06 done (above-shelf space cut). Leaves feature 'PCB support ribs (26)'.
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
    L.log("=== 07 start")
    b = L.body()
    bury = L.P("rib_bury")
    px0, px1, py0, py1 = L.P("pocket_x0"), L.P("pocket_x1"), L.P("pocket_y0"), L.P("pocket_y1")
    sk = L.new_sketch("PCB support ribs (26)", "Z_SHELF_BACK plane")
    rects = []
    for (x0, x1, y0, y1, side) in L.RIBS:
        if side == "T":
            y0 = py0 - bury
        elif side == "B" and y1 > py1:          # the two corner ribs end in the bottom pocket wall
            y1 = py1 + bury
        elif side == "L":
            x0 = px0 - bury
        elif side == "R":
            x1 = px1 + bury
        rects.append((x0, x1, y0, y1))
        L.rrect(sk, x0, x1, y0, y1, None, dims=False)
    L.fix_all(sk)
    sk.isComputeDeferred = False
    prof = L.pick_profiles(sk, lambda a, bb: True)
    if prof.count != 26:
        raise RuntimeError("rib profiles %d" % prof.count)
    L.extrude(prof, "join", "Z_PCB - Z_SHELF_BACK", +1, L.shrink(), "PCB support ribs (26)", b)
    n, bad = L.timeline_health()
    L.log("07 ribs %s; timeline %d unhealthy %s; rects %s" % (L.body_stats(), n, bad,
                                                              [tuple(round(v, 4) for v in r) for r in rects]))
    L.show_iso()
    print(L.body_stats(), n, bad)
