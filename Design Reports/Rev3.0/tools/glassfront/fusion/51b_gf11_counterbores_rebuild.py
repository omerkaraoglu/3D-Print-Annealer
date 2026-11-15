"""51b - stage 3 (GF-1.1), item 1 re-made after the first scan of 51 (51 is superseded; a clean rebuild runs 51b
only, after 50):
  * floor round cb_r 0.25 (51: 0.2): with 0.2 the round's cylinder strips on the 1.6 straight sides were 0.31 x 1.6
    (2A/P 0.26, and the verification calls a cylinder longer than 1.5 a design face); 0.25 gives 2A/P 0.315 for the
    round and leaves a 0.317 flat floor ring (slot 5.41 / counterbore 6.54 at the floor)
  * F5-F8 floor at Z_SHEET_BACK + cb_floor_mid (2.0 = 1.0 into the flange front; 0.6 clearance over a 1.4 flange): at
    0.6 deep the straight wall left above a 0.25 round would be a 0.35 x 1.6 strip (2A/P 0.29)
  * F1-F4 unchanged in intent: floor at Z_SHEET_BACK + cb_floor (1.6) in the pad
Deletes 'Counterbore floor edges R cb_r', 'Fastener counterbores F1-F8' and their sketch if present, then:
  'Fastener counterbores F1-F8 sketch' (8 stadiums cb_w x cb_l coaxial with the slots, Z_SHEET_BACK plane)
  'Fastener counterbores F1-F4 (pads)'  cut +Z cb_floor, 1 deg narrowing with depth
  'Fastener counterbores F5-F8'         cut +Z cb_floor_mid, 1 deg
  'Counterbore floor edges R cb_r'      edge set on the 8 floor / wall loops."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

H = "( cb_l - cb_w ) / 2"


def floor_loops(b, zf, ks):
    edges = adsk.core.ObjectCollection.create()
    nfl = 0
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType or abs(f.pointOnFace.z * 10 - zf) > 1e-4:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if n.z > -0.9999:
            continue
        c = f.centroid
        if min(math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) for k in ks) > 2.0:
            continue
        nfl += 1
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            if lp.isOuter:
                for e in range(lp.edges.count):
                    edges.add(lp.edges.item(e))
    return nfl, edges


def run(_context: str):
    L.check_doc()
    L.log("=== 51b start")
    L.set_param("cb_r", "0.25 mm", "mm", "GF-1.1: counterbore floor edge round (0.25: round and floor ring both 2A/P "
                                       ">= 0.3)")
    L.set_param("cb_floor_mid", "2.0 mm", "mm", "GF-1.1: F5-F8 counterbore floor above Z_SHEET_BACK (1.0 into the "
                                              "flange front, 0.6 over a 1.4 flange)")
    for nm in ("Counterbore floor edges R cb_r", "Fastener counterbores F1-F8"):
        f = L.feature(nm)
        if f is not None:
            f.deleteMe()
    sk = L.comp().sketches.itemByName("Fastener counterbores F1-F8 sketch")
    if sk is not None:
        sk.deleteMe()
    b = L.body()
    sk = L.new_sketch("Fastener counterbores F1-F8", "Z_SHEET_BACK plane")
    sk.isComputeDeferred = False
    for k in range(1, 9):
        L.stadium(sk, "f%d_x - %s * f%d_ux" % (k, H, k), "f%d_y - %s * f%d_uy" % (k, H, k),
                  "f%d_x + %s * f%d_ux" % (k, H, k), "f%d_y + %s * f%d_uy" % (k, H, k), "cb_w / 2")
    L.solve(sk, 8)
    if L.under_constrained(sk):
        raise RuntimeError("counterbore sketch under-constrained")
    pads = [(L.P("f%d_x" % k), L.P("f%d_y" % k)) for k in (1, 2, 3, 4)]
    is_pad = lambda a, bb: any(abs((bb[0] + bb[1]) / 2 - x) < 1 and abs((bb[2] + bb[3]) / 2 - y) < 1 for x, y in pads)
    p14 = L.pick_profiles(sk, is_pad)
    p58 = L.pick_profiles(sk, lambda a, bb: not is_pad(a, bb))
    if p14.count != 4 or p58.count != 4:
        raise RuntimeError("profiles %d / %d" % (p14.count, p58.count))
    L.extrude(p14, "cut", "cb_floor", +1, L.shrink(), "Fastener counterbores F1-F4 (pads)", b)
    L.extrude(p58, "cut", "cb_floor_mid", +1, L.shrink(), "Fastener counterbores F5-F8", b)
    n1, e1 = floor_loops(b, L.P("Z_SHEET_BACK") + L.P("cb_floor"), (1, 2, 3, 4))
    n2, e2 = floor_loops(b, L.P("Z_SHEET_BACK") + L.P("cb_floor_mid"), (5, 6, 7, 8))
    if n1 != 4 or n2 != 4:
        raise RuntimeError("floors %d / %d" % (n1, n2))
    for i in range(e2.count):
        e1.add(e2.item(i))
    ff = L.comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(e1, L.VI("cb_r"), True)
    fi.isRollingBallCorner = True
    fl = ff.add(fi)
    fl.name = "Counterbore floor edges R cb_r"
    n, bad = L.timeline_health()
    L.log("51b edges %d; timeline %d unhealthy %s; %s" % (e1.count, n, bad, L.body_stats()))
    print("edges", e1.count, n, bad, L.body_stats())
