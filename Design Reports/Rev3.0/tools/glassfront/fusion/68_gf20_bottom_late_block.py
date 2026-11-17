"""68 - stage 4 (GF-2.0): the bottom edge behind the bridge, as ONE block of features placed after the GF-1.1 root
fillets and before 'Fastener tubes F1-F4 sketch' (the marker is rolled back there and moved to the end afterwards).

Why a late block: everything before it keeps a GF-1.1-like topology at every glass_t (cell floors and the bridge
floor all at Z_LANDPLATE_BACK), so the GF-1.1 edge-set fillets keep their edges. The block then lowers the floors
beyond the step wall to the flange back and re-adds what that removes:

  'Floor over the flange plate (cells + tail pocket)'  cut on the Z_PCB plane, -Z to Z_FLANGE_BACK, 1 deg narrowing
        down; 3 profiles = H7 cell, tail pocket, H6 cell over y > step-wall back. Outlines offset from their own
        reference planes (cells Z_LANDPLATE_BACK, pocket Z_LAND) so every wall continues in its plane; the front edge
        follows the step-wall back face exactly (glass_y1 + s_ring_b at the flange front, 1 deg). Always cuts
        material (the cell ribs over the flange are in it), also at the level snap (glass 1.1).
        Floors: tail pocket y > 130.89 and the cells' lower parts = flange back (concept 3.1 / 5.3: 'the floor steps
        2.0 at y 130.89 at glass 3.0, flat at 1.1').
  'Cell ribs over the flange plate'  the H6 / H7 boss-to-beam ribs (from 0.5 inside the step wall) and the two cross
        ribs at crib_y, Z_FLANGE_BACK -> Z_CELL_RIB_TOP, outlines widened by (Z_LANDPLATE_BACK - Z_FLANGE_BACK)
        tan(draft) so their faces are the planes of the GF-1.1 ribs.
  'Divider rib (bridge, low)' / 'Divider rib (bridge, high)'  x div_x +- div_t/2 at Z_LANDPLATE_BACK, from the bridge
        pocket face (coplanar with it) to 0.5 past the step-wall back; Z_LANDPLATE_BACK -> Z_PCB in front of the
        tail-wall step (tail_wall_step_y at Z_PCB), -> Z_TROUGH_TOP behind it.
  'Divider rib (over the flange plate)'  from 0.5 inside the step wall to 0.5 into the bottom wall,
        Z_FLANGE_BACK -> Z_TROUGH_TOP (widened outline: same side planes).
  'Root fillets R0.5 - floors over the bridge and the flange plate (rule)'  rule fillet, fillets only, all edges of
        the features above + 'Tail pocket over the bridge'.
  'Root fillets R0.5 - outer wall to the flange plate (rule)'  between 'Flange plate' and 'Outer wall block' (the
        outer wall now stands on the flange plate below the board edge).
  'Bridge nose R bend_nose_R'  round on the land-plate back x bridge pocket face (2 edges, split by the divider rib)
  'Bridge land break land_break'  45 deg chamfer on the land x bridge pocket face (1 edge).
Refuses to run twice."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

T = "tan(draft)"
OC = "( Z_PCB - Z_LANDPLATE_BACK ) * %s" % T          # cells: Z_LANDPLATE_BACK outline -> Z_PCB plane
OP = "( Z_PCB - Z_LAND ) * %s" % T                     # pocket: Z_LAND outline -> Z_PCB plane
CDX = "( Z_LANDPLATE_BACK - Z_LAND ) * %s" % T         # = CELL_DX of 04
WR = "( Z_LANDPLATE_BACK - Z_FLANGE_BACK ) * %s" % T   # ribs: Z_LANDPLATE_BACK outline -> Z_FLANGE_BACK plane
YE_PCB = "glass_y1 + s_ring_b - ( Z_PCB - Z_FLANGE_FRONT ) * %s" % T                 # step-wall back face at Z_PCB
YSW_LB = "glass_y1 + s_ring_b - ( Z_LANDPLATE_BACK - Z_FLANGE_FRONT ) * %s" % T      # ... at Z_LANDPLATE_BACK
YSW_FB = "glass_y1 + s_ring"                                                         # ... at Z_FLANGE_BACK (130.89)
YSTEP_LB = "tail_wall_step_y - ( Z_PCB - Z_LANDPLATE_BACK ) * %s" % T                # tail-wall step at Z_LANDPLATE_BACK
YBRIDGE_LB = "bend_y1 + ( Z_LANDPLATE_BACK - Z_LAND ) * %s" % T                      # bridge face at Z_LANDPLATE_BACK

N_FLOOR = "Floor over the flange plate (cells + tail pocket)"
N_CRIBS = "Cell ribs over the flange plate"
N_DIV_LO = "Divider rib (bridge, low)"
N_DIV_HI = "Divider rib (bridge, high)"
N_DIV_FL = "Divider rib (over the flange plate)"
N_R2 = "Root fillets R0.5 - floors over the bridge and the flange plate (rule)"
N_R1 = "Root fillets R0.5 - outer wall to the flange plate (rule)"
N_NOSE = "Bridge nose R bend_nose_R"
N_BREAK = "Bridge land break land_break"


def health(tag, res):
    n, bad = L.timeline_health()
    res[tag] = bad
    L.log("68 %s: timeline %d unhealthy %s; %s" % (tag, n, bad, L.body_stats()))
    if bad:
        raise RuntimeError("68 unhealthy after %s: %s" % (tag, bad))


def floor_cut(b):
    sk = L.new_sketch(N_FLOOR, "Z_PCB plane")
    L.rrect(sk, "pocket_x0 - %s" % OC, "tr_x0 - wall + %s + %s" % (CDX, OC), YE_PCB, "tr_y1 + %s" % OC,
            "cell_r + %s" % OC, corners={"bl", "br"})
    L.rrect(sk, "tr_x0 - tail_side_add - %s" % OP, "tr_x1 + tail_side_add + %s" % OP, YE_PCB, "tr_y1 + %s" % OP,
            "trough_R + %s" % OP, corners={"bl", "br"})
    L.rrect(sk, "tr_x1 + wall - %s - %s" % (CDX, OC), "pocket_x1 + %s" % OC, YE_PCB, "tr_y1 + %s" % OC,
            "cell_r + %s" % OC, corners={"bl", "br"})
    pr = L.solve(sk, 3)
    uc = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_PCB - Z_FLANGE_BACK", -1, L.shrink(), N_FLOOR, b)
    return uc


def cell_ribs(b):
    sk = L.new_sketch(N_CRIBS, "Z_FLANGE_BACK plane")
    for h in ("h7", "h6"):
        L.rrect(sk, "%s_x - rib / 2 - %s" % (h, WR), "%s_x + rib / 2 + %s" % (h, WR), "%s - rib_bury" % YSW_FB,
                "tr_y1 + rib_bury + %s" % WR, None)
    L.rrect(sk, "pocket_x0 - rib_bury - %s" % WR, "tr_x0 - wall + %s + rib_bury + %s" % (CDX, WR),
            "crib_y - rib / 2 - %s" % WR, "crib_y + rib / 2 + %s" % WR, None)
    L.rrect(sk, "tr_x1 + wall - %s - rib_bury - %s" % (CDX, WR), "pocket_x1 + rib_bury + %s" % WR,
            "crib_y - rib / 2 - %s" % WR, "crib_y + rib / 2 + %s" % WR, None)
    pr = L.solve(sk)
    uc = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_CELL_RIB_TOP - Z_FLANGE_BACK", +1, L.shrink(), N_CRIBS, b)
    return uc, pr.count


def divider_rib(b):
    sk = L.new_sketch("Divider rib (bridge)", "Z_LANDPLATE_BACK plane")
    x0, x1 = "div_x - div_t / 2", "div_x + div_t / 2"
    left, right, top, bot = L.rrect(sk, x0, x1, YBRIDGE_LB, "%s + rib_bury" % YSW_LB, None)
    ystep = L.ev(YSTEP_LB)
    xl, xr = L.ev(x0), L.ev(x1)
    ln = sk.sketchCurves.sketchLines.addByTwoPoints(L.P3(xl, ystep), L.P3(xr, ystep))
    gc = sk.geometricConstraints
    gc.addCoincident(ln.startSketchPoint, left)
    gc.addCoincident(ln.endSketchPoint, right)
    gc.addHorizontal(ln)
    L._dim_y(sk, ln.startSketchPoint, YSTEP_LB, (xl - 6) / 10.0)
    sk.isComputeDeferred = False
    lo = L.pick_profiles(sk, lambda a, bb: bb[3] < ystep + 0.01)
    hi = L.pick_profiles(sk, lambda a, bb: bb[2] > ystep - 0.01)
    if lo.count != 1 or hi.count != 1:
        raise RuntimeError("divider rib bridge profiles %d / %d of %d" % (lo.count, hi.count, sk.profiles.count))
    uc1 = L.under_constrained(sk)
    L.extrude(lo, "join", "Z_PCB - Z_LANDPLATE_BACK", +1, L.shrink(), N_DIV_LO, b)
    L.extrude(hi, "join", "Z_TROUGH_TOP - Z_LANDPLATE_BACK", +1, L.shrink(), N_DIV_HI, b)
    sk = L.new_sketch(N_DIV_FL, "Z_FLANGE_BACK plane")
    L.rrect(sk, "%s - %s" % (x0, WR), "%s + %s" % (x1, WR), "%s - rib_bury" % YSW_FB, "tr_y1 + rib_bury + %s" % WR, None)
    pr = L.solve(sk, 1)
    uc2 = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_TROUGH_TOP - Z_FLANGE_BACK", +1, L.shrink(), N_DIV_FL, b)
    return uc1 + uc2


def nose_edges():
    b = L.body()
    z = L.P("Z_LANDPLATE_BACK")
    yb = L.ev(YBRIDGE_LB)
    x0, x1 = L.P("tr_x0") - L.P("tail_side_add") - 1, L.P("tr_x1") + L.P("tail_side_add") + 1
    out = adsk.core.ObjectCollection.create()
    for i in range(b.edges.count):
        e = b.edges.item(i)
        g = e.geometry
        if not isinstance(g, adsk.core.Line3D):
            continue
        p, q = e.startVertex.geometry, e.endVertex.geometry
        if abs(p.z * 10 - z) > 1e-3 or abs(q.z * 10 - z) > 1e-3:
            continue
        if abs(-p.y * 10 - yb) > 0.01 or abs(-q.y * 10 - yb) > 0.01:
            continue
        if min(p.x, q.x) * 10 < x0 or max(p.x, q.x) * 10 > x1 or abs(p.x - q.x) * 10 < 1.0:
            continue
        out.add(e)
    return out


def break_edges():
    b = L.body()
    z = L.P("Z_LAND")
    yb = L.P("bend_y1")
    out = adsk.core.ObjectCollection.create()
    for i in range(b.edges.count):
        e = b.edges.item(i)
        if not isinstance(e.geometry, adsk.core.Line3D):
            continue
        p, q = e.startVertex.geometry, e.endVertex.geometry
        if abs(p.z * 10 - z) > 1e-3 or abs(q.z * 10 - z) > 1e-3:
            continue
        if abs(-p.y * 10 - yb) > 0.01 or abs(-q.y * 10 - yb) > 0.01 or abs(p.x - q.x) * 10 < 50:
            continue
        out.add(e)
    return out


def run(_context: str):
    d = L.check_doc()
    L.log("=== 68 start")
    if L.feature(N_FLOOR) is not None:
        raise RuntimeError("68 already applied")
    tl = d.timeline
    res = {}
    anchor = L.comp().sketches.itemByName("Fastener tubes F1-F4 sketch")
    anchor.timelineObject.rollTo(True)
    b = L.body()
    res["floor_uc"] = floor_cut(b)
    health("floor cut", res)
    res["cell_ribs"] = cell_ribs(b)
    health("cell ribs", res)
    res["divider_uc"] = divider_rib(b)
    health("divider rib", res)
    ne = nose_edges()
    res["nose_edges"] = ne.count
    if ne.count != 2:
        raise RuntimeError("nose edges %d" % ne.count)
    L.fillet_edges([ne.item(i) for i in range(ne.count)], "bend_nose_R", N_NOSE)
    health("nose", res)
    be = break_edges()
    res["break_edges"] = be.count
    if be.count != 1:
        raise RuntimeError("break edges %d" % be.count)
    ci = L.comp().features.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(be, L.VI("land_break"), False)
    ch = L.comp().features.chamferFeatures.add(ci)
    ch.name = N_BREAK
    health("break", res)
    f = L.rule_fillet(N_R2, "all", [N_FLOOR, N_CRIBS, N_DIV_LO, N_DIV_HI, N_DIV_FL, "Tail pocket over the bridge"])
    res["R2_faces"] = f.faces.count
    health("R2", res)
    f = L.rule_fillet(N_R1, "between", ["Flange plate"], ["Outer wall block"])
    res["R1_faces"] = f.faces.count
    health("R1", res)
    tl.moveToEnd()
    d.computeAll()
    n, bad = L.timeline_health()
    res.update({"timeline": n, "unhealthy": bad, "frame": L.body_dict()})
    L.dump(res, "gf20/68_bottom_late_block.json")
    L.log("68 %s" % res)
    print(res)
