"""30 - stage 2, Part A: fix the two boss-side corners of the bottom corner cells (stage-1 known weaknesses 1 and 2).

Cause (stage 1): the cell top wall moved 0.55 towards the bosses with the clearance pocket (pocket_y1 + wall = 122.30,
v2 121.75), so
  H7 (left cell, top-RIGHT corner): the boss meets the top wall 0.88 before the R2 corner arc -> after the R0.5 boss
      root fillet a 0.39-wide flat strip of the top wall (face 2.28 mm2, 2A/P 0.295) between fillet and arc.
  H6 (right cell, top-LEFT corner): the boss crosses the R2 corner arc and runs 1.0 from the cell's left (tail) wall
      -> a crescent of air 1.0 wide (0.55 inside the R0.5 root-fillet band at Z -7.7) = a thin steel blade.

Fix (bosses, pilots, reliefs, ribs, pockets untouched; only the cell cut outline changes):
  H7: the corner arc at the boss gets its own radius cell_r_h7 = 1.0 (was cell_r 2.0): the boss now meets a full
      top wall, the flat beyond the boss root fillet is ~1.2 (floor) .. ~1.3 (Z 0) wide; boss to tail wall 2.6 is a
      proper slot (no fill there: filling it would make an 8 mm solid section pilot -> tail pocket).
  H6: the corner is blended INTO the boss: the R2 corner arc (cell_r) is moved down the left wall so that it is
      tangent to the left wall and crosses the boss at 90 deg on the cell floor (circle orthogonal to the boss
      circle at Z_LANDPLATE_BACK): centre (XL + cell_r, h6_fill_y),
         h6_fill_y = h6_y + sqrt(cell_r^2 + r_boss_floor^2 - (h6_x - XL - cell_r)^2),
         r_boss_floor = boss_od / 2 + (Z_PCB - Z_LANDPLATE_BACK) tan(draft), XL = cell left at the floor.
      The arc's top end is joined to the top line by a vertical line at x = XL + cell_r that lies inside the boss
      at every Z (the boss join refills it). The 1.0 crescent becomes solid: the boss merges into the tail wall.
      Done inside the 'Corner cells sketch' (arc tangent to the left line in the same profile -> tangent at every
      Z under the 1 deg taper; a separate join would leave a taper-mismatch sliver at the tangent point).
  The edge-set fillet 'Root fillets R0.5 - corner cells + cell ribs + cell bosses' is deleted and re-created at the
  same timeline position from gflib.EDGE_SETS (it collects the new arc <-> boss / floor roots).

Parameters added: cell_r_h7, h6_fill_y (document level, comments say 'stage 2 Part A').
Expects: stage-1 model (v4). Leaves: timeline marker at the end; prints health, edges, body stats.
"""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

CELL_DX = "( Z_LANDPLATE_BACK - Z_LAND ) * tan(draft)"
XL_R = "( tr_x1 + wall - %s )" % CELL_DX                 # right cell, left wall at the cell floor (abs x)
RB = "( boss_od / 2 + ( Z_PCB - Z_LANDPLATE_BACK ) * tan(draft) )"
DXC = "( h6_x - %s - cell_r )" % XL_R
H6_FILL_Y = "h6_y + sqrt( cell_r * cell_r + %s * %s - %s * %s )" % (RB, RB, DXC, DXC)
CELL_SET = "corner cells + cell ribs + cell bosses"
CELL_FILLET = "Root fillets R0.5 - " + CELL_SET


def near(p, x, y, tol=0.02):
    g = p.geometry
    return abs(g.x * 10 - x) < tol and abs(-g.y * 10 - y) < tol


def run(_context: str):
    L.check_doc()
    L.log("=== 30 start")
    d = L.des()
    tl = d.timeline
    L.set_param("cell_r_h7", "1.0 mm", "mm",
                "stage 2 Part A: H7 cell corner radius at the boss (boss meets a full top wall; was cell_r)")
    L.set_param("h6_fill_y", H6_FILL_Y, "mm",
                "stage 2 Part A: abs y of the centre of the H6 cell corner arc (cell_r, tangent to the left wall, "
                "crossing the boss at 90 deg on the cell floor)")
    sk = L.comp().sketches.itemByName("Corner cells sketch")
    xl = L.ev(XL_R)
    yt = L.P("pocket_y1") + L.P("wall")
    cr = L.P("cell_r")
    # ---------------------------------------------------------------- H7: radius of the boss-side corner
    xr_l = L.ev("tr_x0 - wall + " + CELL_DX)
    n7 = 0
    for i in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(i)
        if dm.objectType.endswith("SketchRadialDimension"):
            c = dm.entity.geometry.center
            if abs(c.x * 10 - (xr_l - cr)) < 0.05 and abs(-c.y * 10 - (yt + cr)) < 0.05:
                dm.parameter.expression = "cell_r_h7"
                n7 += 1
    if n7 != 1:
        raise RuntimeError("H7 corner radial dimension: found %d" % n7)
    # ---------------------------------------------------------------- H6: corner arc blended into the boss
    arcs = sk.sketchCurves.sketchArcs
    old = None
    for i in range(arcs.count):
        a = arcs.item(i)
        c = a.geometry.center
        if abs(c.x * 10 - (xl + cr)) < 0.05 and abs(-c.y * 10 - (yt + cr)) < 0.05:
            old = a
    if old is None:
        raise RuntimeError("H6 corner arc not found")
    top_pt = left_pt = top_line = left_line = None
    lines = sk.sketchCurves.sketchLines
    for i in range(lines.count):
        ln = lines.item(i)
        for p in (ln.startSketchPoint, ln.endSketchPoint):
            if near(p, xl + cr, yt):
                top_pt, top_line = p, ln
            if near(p, xl, yt + cr):
                left_pt, left_line = p, ln
    if top_pt is None or left_pt is None:
        raise RuntimeError("H6 corner lines not found")
    old.deleteMe()
    yc = L.P("h6_fill_y")
    A = arcs.addByCenterStartEnd(L.P3(xl + cr, yc), L.P3(xl + cr, yc - cr), L.P3(xl, yc))
    # identify the arc ends (arcs are always CCW in the sketch: start = top, end = left expected)
    sp, ep = A.startSketchPoint, A.endSketchPoint
    if near(sp, xl, yc, 0.05):
        sp, ep = ep, sp
    gc = sk.geometricConstraints
    gc.addCoincident(ep, left_pt)
    gc.addTangent(A, left_line)
    vl = lines.addByTwoPoints(top_pt, sp)
    gc.addVertical(vl)
    dr = sk.sketchDimensions.addRadialDimension(A, L.P3(xl + cr + 1.0, yc + 1.0))
    dr.parameter.expression = "cell_r"
    L._dim_y(sk, A.centerSketchPoint, "h6_fill_y", (xl + cr + 4) / 10.0)
    L._dim_x(sk, top_pt, "%s + cell_r" % XL_R, -(yt - 4) / 10.0)
    d.computeAll()
    uc = L.under_constrained(sk)
    npr = sk.profiles.count
    g = A.geometry
    arc_info = (round(g.center.x * 10, 4), round(-g.center.y * 10, 4), round(g.radius * 10, 4))
    L.log("30 sketch: under-constrained %d, profiles %d, new arc %s" % (uc, npr, arc_info))
    if npr != 2:
        raise RuntimeError("Corner cells sketch: %d profiles" % npr)
    n, bad = L.timeline_health()
    L.log("30 after sketch edit: timeline %d unhealthy %s" % (n, bad))
    # ---------------------------------------------------------------- the cut must still use both profiles
    cut = L.feature("Corner cells")
    if cut.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        cut.timelineObject.rollTo(False)
        cut.profile = L.pick_profiles(sk)
        tl.moveToEnd()
        d.computeAll()
    # ---------------------------------------------------------------- re-create the cell root fillets
    f = L.feature(CELL_FILLET)
    if f is None:
        raise RuntimeError("no feature " + CELL_FILLET)
    f.timelineObject.rollTo(True)
    f.deleteMe()
    nf, k = L.fillet_set(CELL_SET)
    tl.moveToEnd()
    d.computeAll()
    n, bad = L.timeline_health()
    L.log("30 cell fillet re-created: %d edges; timeline %d unhealthy %s; %s" % (k, n, bad, L.body_stats()))
    print("H7 dims", n7, "sketch under-constrained", uc, "profiles", npr, "new H6 arc", arc_info,
          "cell fillet edges", k, "timeline", n, "unhealthy", bad, L.body_stats())
