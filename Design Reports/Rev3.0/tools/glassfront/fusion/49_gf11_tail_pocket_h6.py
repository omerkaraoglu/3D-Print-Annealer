"""49 - stage 3 (GF-1.1), frame items 4 and 3:
  item 4  'Tail pocket sketch': side walls x tr_x0 - tail_side_add / tr_x1 + tail_side_add (0.3 each side); draft,
          R1.5 bottom corners, bottom face y tr_y1 unchanged. tr_x0 / tr_x1 themselves are NOT changed: the tail-wall
          block, the corner cells and their ribs stay where they are, the tail walls get 0.3 thinner.
  item 3  H6 cell corner (replaces the stage-2 h6_fill_y fill, which made a 6.0 lump): the cell's left wall jogs to
          XJ over the boss region so that the tail wall beside it is h6_wall_min (1.1) at Z_PCB, where it is thinnest
          (tail pocket face and cell wall both 1 deg, opposite);
            XJ = tr_x1 + tail_side_add + (Z_PCB - Z_LAND) tan(draft) + h6_wall_min + (Z_PCB - Z_LANDPLATE_BACK) tan(draft)
          the corner arc h6_corner_r (2.5) is tangent to the jogged wall and the cell top wall; its top tangent point
          lies inside the boss at every Z (no top-wall strip), the boss crosses the arc at ~58 deg; the jogged wall
          runs down to h6_jog_y, then a slant over h6_jog_len returns to the cell wall. The boss / pilot / relief are
          untouched; the air between boss and wall is >= 1.5 wide (was 1.0) except the rounded V where the boss
          crosses the arc.
          'Corner cells sketch': old fill arc + closing line deleted, new arc + 2 lines + 3 dims; the cut keeps both
          profiles; the cell edge-set fillet is deleted and re-created at its position (gflib.EDGE_SETS).
Parameter h6_fill_y deleted (unused)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

CELL_DX = "( Z_LANDPLATE_BACK - Z_LAND ) * tan(draft)"
XL_R = "( tr_x1 + wall - %s )" % CELL_DX
XJ = ("( tr_x1 + tail_side_add + ( Z_PCB - Z_LAND ) * tan(draft) + h6_wall_min + ( Z_PCB - Z_LANDPLATE_BACK ) * "
      "tan(draft) )")
CELL_SET = "corner cells + cell ribs + cell bosses"
CELL_FILLET = "Root fillets R0.5 - " + CELL_SET


def near(p, x, y, tol=0.03):
    g = p.geometry
    return abs(g.x * 10 - x) < tol and abs(-g.y * 10 - y) < tol


def health(tag):
    n, bad = L.timeline_health()
    L.log("49 %s: timeline %d unhealthy %s; %s" % (tag, n, bad, L.body_stats()))
    return n, bad


def run(_context: str):
    L.check_doc()
    L.log("=== 49 start")
    d = L.des()
    tl = d.timeline
    c = L.comp()
    # ------------------------------------------------------------------ item 4: tail pocket side walls
    sk = c.sketches.itemByName("Tail pocket sketch")
    k4 = 0
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        e = dm.parameter.expression.replace(" ", "")
        if e == "(tr_x0)+100mm":
            dm.parameter.expression = "( tr_x0 - tail_side_add ) + 100 mm"
            k4 += 1
        elif e == "(tr_x1)+100mm":
            dm.parameter.expression = "( tr_x1 + tail_side_add ) + 100 mm"
            k4 += 1
    if k4 != 2:
        raise RuntimeError("tail pocket dims %d" % k4)
    d.computeAll()
    h4 = health("tail pocket")
    # ------------------------------------------------------------------ item 3: H6 corner
    sk = c.sketches.itemByName("Corner cells sketch")
    xl, yt, cr = L.ev(XL_R), L.P("pocket_y1") + L.P("wall"), L.P("cell_r")
    yfill = L.P("h6_fill_y")
    arcs, lines = sk.sketchCurves.sketchArcs, sk.sketchCurves.sketchLines
    old = [arcs.item(i) for i in range(arcs.count)
           if abs(arcs.item(i).geometry.center.x * 10 - (xl + cr)) < 0.05 and
           abs(-arcs.item(i).geometry.center.y * 10 - yfill) < 0.05]
    if len(old) != 1:
        raise RuntimeError("H6 fill arc: %d" % len(old))
    vls = [ln for ln in (lines.item(i) for i in range(lines.count))
           if near(ln.startSketchPoint, xl + cr, yt) or near(ln.endSketchPoint, xl + cr, yt)]
    top_line = vline = None
    for ln in vls:
        g0, g1 = ln.startSketchPoint.geometry, ln.endSketchPoint.geometry
        if abs(g0.x - g1.x) < 1e-6:
            vline = ln
        else:
            top_line = ln
    top_pt = top_line.startSketchPoint if near(top_line.startSketchPoint, xl + cr, yt) else top_line.endSketchPoint
    left_line = left_pt = None
    for i in range(lines.count):
        ln = lines.item(i)
        for p in (ln.startSketchPoint, ln.endSketchPoint):
            if near(p, xl, yfill):
                left_line, left_pt = ln, p
    if vline is None or top_line is None or left_line is None:
        raise RuntimeError("H6 corner entities not found (%s %s %s)" % (vline, top_line, left_line))
    # the x dimension of top_pt (XL + cell_r) is replaced by the tangency chain
    for j in range(sk.sketchDimensions.count - 1, -1, -1):
        dm = sk.sketchDimensions.item(j)
        if dm.parameter.expression.replace(" ", "") == ("( %s + cell_r ) + 100 mm" % XL_R).replace(" ", ""):
            dm.deleteMe()
    old[0].deleteMe()
    vline.deleteMe()
    xj, rc = L.ev(XJ), L.P("h6_corner_r")
    yj = L.P("h6_jog_y")
    A = arcs.addByCenterStartEnd(L.P3(xj + rc, yt + rc), L.P3(xj + rc, yt), L.P3(xj, yt + rc))
    sp, ep = A.startSketchPoint, A.endSketchPoint
    if near(sp, xj, yt + rc, 0.05):
        sp, ep = ep, sp
    gc = sk.geometricConstraints
    gc.addCoincident(sp, top_pt)
    p2 = L.point(sk, XJ, "h6_jog_y")
    l1 = lines.addByTwoPoints(ep, p2)
    gc.addVertical(l1)
    gc.addTangent(A, l1)
    gc.addTangent(A, top_line)
    dr = sk.sketchDimensions.addRadialDimension(A, L.P3(xj + rc + 0.8, yt + rc + 0.8))
    dr.parameter.expression = "h6_corner_r"
    lines.addByTwoPoints(p2, left_pt)
    L._dim_y(sk, left_pt, "h6_jog_y + h6_jog_len", (xl - 4) / 10.0)
    d.computeAll()
    uc = L.under_constrained(sk)
    if sk.profiles.count != 2:
        raise RuntimeError("Corner cells sketch: %d profiles" % sk.profiles.count)
    cut = L.feature("Corner cells")
    if cut.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        cut.timelineObject.rollTo(False)
        cut.profile = L.pick_profiles(sk)
        tl.moveToEnd()
        d.computeAll()
    f = L.feature(CELL_FILLET)
    f.timelineObject.rollTo(True)
    f.deleteMe()
    nf, k = L.fillet_set(CELL_SET)
    tl.moveToEnd()
    d.computeAll()
    up = d.userParameters.itemByName("h6_fill_y")
    if up is not None and up.isDeletable:
        up.deleteMe()
    n, bad = health("H6")
    g = A.geometry
    print("tail pocket dims", k4, "health after item 4", h4, "| H6 arc", (round(g.center.x * 10, 4),
          round(-g.center.y * 10, 4), round(g.radius * 10, 4)), "XJ", round(xj, 4), "under-constrained", uc,
          "cell fillet edges", k, "timeline", n, bad, L.body_stats())
