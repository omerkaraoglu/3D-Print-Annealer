"""07 - fastener tubes and their ribs (master JSON fasteners.pad_tube):
  'Fastener tubes F1-F8'  dia tube_top_d (= pad_d 18) at Z_TUBE_TOP on the Z_TUBE_TOP plane, -Z (NEGATIVE extent,
                          fixed at creation: the v2 lesson in 61_v22_fix_tube_direction) by tube_h + half the flange
                          thickness (buried in the flange), 1 deg growing to the front. F5-F8 overlap the step wall
                          by 0.9 in plan (tube edge s 2.0, step wall to s 2.9) and merge with it: no rib there.
  'Tube ribs F1-F4'       one rib (1.5 at the root) per corner tube on the Z_FLANGE_BACK plane, along the 45 deg line
                          from the fastener to the glass corner-arc centre (normal to the step-wall corner arc), from
                          trib_d0 (inside the tube) to trib_d1 (buried rib_bury into the step wall), +Z to Z_TRIB_TOP
                          = max(min(Z_TUBE_TOP; Z_STEPWALL_BACK); Z_FLANGE_BACK + trib_h_min): full tube height
                          where the step wall is taller (glass 4.0), flush with the step-wall back at 2.0 / 3.0 (no
                          stub standing on the plate), 1.0 high free-ended rib at the level snap (1.1).
                          1 deg shrinking. Corner points dimensioned by expressions.
Expects: 06 done. (First build: the rib was made to Z_TUBE_TOP and left a 0.5 x 0.4 stub on the step-wall back at
glass 3.0; 07b deleted and re-made it with this definition.)
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

C = "cos(45 deg)"
DIRS = {1: (1, 1), 2: (-1, 1), 3: (-1, -1), 4: (1, -1)}     # rib axis direction (abs x, y down) towards the glass corner


def corners(k):
    sx, sy = DIRS[k]
    fx, fy = "f%d_x" % k, "f%d_y" % k
    nx, ny = -sy, sx                                   # normal (abs coords), unit after * C
    pts = []
    for d, side in (("trib_d0", 1), ("trib_d1", 1), ("trib_d1", -1), ("trib_d0", -1)):
        xe = "%s + ( %d * %s ) * %s + ( %d * %s ) * rib / 2" % (fx, sx, d, C, side * nx, C)
        ye = "%s + ( %d * %s ) * %s + ( %d * %s ) * rib / 2" % (fy, sy, d, C, side * ny, C)
        pts.append((xe, ye))
    return pts


def make_ribs(b):
    sk = L.new_sketch("Tube ribs F1-F4", "Z_FLANGE_BACK plane")
    for k in (1, 2, 3, 4):
        L.poly4(sk, corners(k))
    pr = L.solve(sk, 4)
    uc = {sk.name: L.under_constrained(sk)}
    L.extrude(pr, "join", "Z_TRIB_TOP - Z_FLANGE_BACK", +1, L.shrink(), "Tube ribs F1-F4", b)
    return uc


def run(_context: str):
    L.check_doc()
    L.log("=== 07 start")
    b = L.body()
    uc = {}
    sk = L.new_sketch("Fastener tubes F1-F8", "Z_TUBE_TOP plane")
    for k in range(1, 9):
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, "tube_top_d")
    pr = L.solve(sk, 8)
    uc[sk.name] = L.under_constrained(sk)
    t = L.extrude(pr, "join", "tube_h + ( Z_FLANGE_BACK - Z_FLANGE_FRONT ) / 2", -1, L.grow(), "Fastener tubes F1-F8", b)
    zr = (min(f.boundingBox.minPoint.z for f in t.faces) * 10, max(f.boundingBox.maxPoint.z for f in t.faces) * 10)
    if zr[1] > L.P("Z_TUBE_TOP") + 1e-4:
        raise RuntimeError("tubes grew the wrong way: z %r" % (zr,))

    uc.update(make_ribs(b))
    n, bad = L.timeline_health()
    L.log("07 tubes z %.3f..%.3f; %s; under-constrained %s; timeline %d unhealthy %s" % (
        zr[0], zr[1], L.body_stats(), uc, n, bad))
    L.show_iso()
    print(zr, L.body_stats(), uc, n, bad)
