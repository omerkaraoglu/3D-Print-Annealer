"""52 - stage 3 (GF-1.1), item 2: annular coring grooves in the eight fastener bosses, from the back.
'Fastener tube coring F1-F8 sketch' on the Z_TUBE_TOP plane: per fastener two concentric circles dia 2 core_r_in
(12.4) and 2 core_r_out (15.4) -> annulus profiles.
'Fastener tube coring F1-F8' cut -Z by core_depth (3.3), 1 deg narrowing with depth (B-side blades release +Z):
groove 1.5 wide at the tube top, 1.385 at the floor; washer seat dia 12.4 in the middle (DIN 9021 M4 dia 12 sits
fully on it; the M5 rivet washer dia 15 bridges the groove); outer skin 1.3 at the top to the dia-18 tube; floor
2.7 above the pad face at glass 3.0 (>= 2.0 required under the F1-F4 hard stops).
'Coring groove floor edges R core_floor_r' (0.5): edge set on both floor loops (flat floor 0.385 left).
core_r_out chosen 7.7 (brief 7.6): with 7.6 the floor would be 1.285 wide and two R0.5 rounds would leave a 0.285
flat = a design-face sliver (2A/P < 0.3).
Expects: 51 done."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 52 start")
    L.set_param("core_r_out", "7.7 mm", "mm", "GF-1.1: coring groove outer radius at the tube top (skin 1.3 to the "
                                             "dia-18 tube; 7.7 not 7.6 so the R0.5 floor rounds leave a 0.385 flat)")
    b = L.body()
    sk = L.new_sketch("Fastener tube coring F1-F8", "Z_TUBE_TOP plane")
    for k in range(1, 9):
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, "2 * core_r_in")
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, "2 * core_r_out")
    L.solve(sk)
    pr = L.profiles_with_loops(sk, 2)
    if pr.count != 8:
        raise RuntimeError("coring annuli %d" % pr.count)
    L.extrude(pr, "cut", "core_depth", -1, L.shrink(), "Fastener tube coring F1-F8", b)
    zf = L.P("Z_TUBE_TOP") - L.P("core_depth")
    edges = adsk.core.ObjectCollection.create()
    nfl = 0
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        if abs(f.pointOnFace.z * 10 - zf) > 1e-4:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if n.z < 0.9999:
            continue
        c = f.centroid
        if min(math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) for k in range(1, 9)) > 2.0:
            continue
        nfl += 1
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            for e in range(lp.edges.count):
                edges.add(lp.edges.item(e))
    if nfl != 8:
        raise RuntimeError("groove floor faces %d" % nfl)
    ff = L.comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, L.VI("core_floor_r"), True)
    fi.isRollingBallCorner = True
    fl = ff.add(fi)
    fl.name = "Coring groove floor edges R core_floor_r"
    n, bad = L.timeline_health()
    L.log("52 floors %d, edges %d; timeline %d unhealthy %s; %s" % (nfl, edges.count, n, bad, L.body_stats()))
    print("floors", nfl, "edges", edges.count, n, bad, L.body_stats())
