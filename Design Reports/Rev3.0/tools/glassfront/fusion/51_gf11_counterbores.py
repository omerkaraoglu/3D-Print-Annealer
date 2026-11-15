"""51 - stage 3 (GF-1.1), item 1: weld-stud flange relief.
'Fastener counterbores F1-F8 sketch' on the Z_SHEET_BACK plane: per fastener a stadium cb_w x cb_l (6.6 x 8.2),
coaxial with the slot and aligned with its radial axis (centres F -/+ (cb_l - cb_w)/2 * u, radius cb_w / 2), fully
dimensioned by expressions (gflib.stadium).
'Fastener counterbores F1-F8' cut +Z by cb_floor (1.6) from Z_SHEET_BACK, 1 deg narrowing with depth (opening towards
the sheet = A half): F1-F4 in the pad face (1.6 deep: 1.0 pad + 0.6 into the flange), F5-F8 0.6 into the flange
front (the tape gap gives the first 1.0). A 1.4 high flange on the sheet back keeps 0.2 to the floor.
'Counterbore floor edges R cb_r' (0.2): edge set on the concave floor / wall edges (outer loop of each floor ring).
The 5.4 x 7.0 slot below the floor is unchanged (R4 rivet location unchanged).
Expects: 50 done."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

H = "( cb_l - cb_w ) / 2"


def run(_context: str):
    L.check_doc()
    L.log("=== 51 start")
    b = L.body()
    sk = L.new_sketch("Fastener counterbores F1-F8", "Z_SHEET_BACK plane")
    sk.isComputeDeferred = False
    for k in range(1, 9):
        ax = "f%d_x - %s * f%d_ux" % (k, H, k)
        ay = "f%d_y - %s * f%d_uy" % (k, H, k)
        bx = "f%d_x + %s * f%d_ux" % (k, H, k)
        by = "f%d_y + %s * f%d_uy" % (k, H, k)
        L.stadium(sk, ax, ay, bx, by, "cb_w / 2")
    pr = L.solve(sk, 8)
    uc = L.under_constrained(sk)
    if uc:
        raise RuntimeError("counterbore sketch: %d curves not fully constrained" % uc)
    L.extrude(pr, "cut", "cb_floor", +1, L.shrink(), "Fastener counterbores F1-F8", b)
    zf = L.P("Z_SHEET_BACK") + L.P("cb_floor")
    edges = adsk.core.ObjectCollection.create()
    nfl = 0
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        if abs(f.pointOnFace.z * 10 - zf) > 1e-4:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if n.z > -0.9999:
            continue
        c = f.centroid
        if min(math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) for k in range(1, 9)) > 2.0:
            continue
        nfl += 1
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            if lp.isOuter:
                for e in range(lp.edges.count):
                    edges.add(lp.edges.item(e))
    if nfl != 8:
        raise RuntimeError("counterbore floor faces %d" % nfl)
    ff = L.comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, L.VI("cb_r"), True)
    fi.isRollingBallCorner = True
    fl = ff.add(fi)
    fl.name = "Counterbore floor edges R cb_r"
    n, bad = L.timeline_health()
    L.log("51 floors %d, fillet edges %d; timeline %d unhealthy %s; %s" % (nfl, edges.count, n, bad, L.body_stats()))
    print("floors", nfl, "edges", edges.count, n, bad, L.body_stats())
