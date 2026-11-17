"""67 - stage 4 (GF-2.0): driving parameters + the first structural edits of the bottom edge
(concept: ../concept/concept_gf2.md, values: ../concept/concept_gf2_params.json; lead decisions 1, 2, 5).

  parameters  border 14.0 -> 18.5 (ONE driving value for all four sides); glass_y1 = pw_y1 + border (derived, the
              chin is gone; was the driving 154.0); new g_bend 3.0 (DRIVING), bend_y1 = panel_y1 + g_bend (bridge
              pocket face at Z_LAND, 122.00), bend_nose_R 1.5, land_break 0.3, tail_R_in_min 1.5, tail_straight_l0
              0.5, tail_t 0.30, Z_TAIL_LEG (reference), div_x 79.92 / div_t = wall (divider rib),
              flange_y1_bottom = max(glass + 21; bottom-wall outer face continued to the flange front) and
              fl_y1 = flange_y1_bottom; logo_h 20 -> 15 (logo zone in the 18.5 bottom border); comments refreshed.
  'Outer wall block'  sketch redefined from the Z_LAND plane to the Z_FLANGE_FRONT plane, outline offset by
              (Z_LAND - Z_FLANGE_FRONT) tan(draft) and corner R frame_r + the same, extent Z_PCB - Z_FLANGE_FRONT:
              every wall face above Z_LAND is the same plane as before (GF-1.1 geometry kept), but below the board
              edge the walls now stand on the flange plate (needed where there is no land plate: the bottom wall,
              the cell walls and the tail walls over the flange; at glass 4.0 the flange back is 0.5 in front of
              Z_LAND). Its bottom face is coplanar with the flange edge (flush, fl_y1).
  'Tail pocket'  becomes the BEND-GAP SLOT: a line at y = bend_y1 splits the sketch, the cut keeps the front piece
              (tr_y0 .. bend_y1, from Z_LAND through Z_TROUGH_TOP + 1, 1 deg widening to the back). Its front face
              (the shelf end) is unchanged; its back face between Z_LAND and Z_LANDPLATE_BACK is the bridge pocket
              face (y 122.00 at Z_LAND).
  'Tail pocket over the bridge'  NEW cut right after it: the rest of the pocket (bend_y1 .. tr_y1, R trough_R) from
              Z_LANDPLATE_BACK through Z_TROUGH_TOP + 1, 1 deg; outline offset by (Z_LANDPLATE_BACK - Z_LAND)
              tan(draft) so the side walls and the bottom face 147.70 are the same planes as the slot's / GF-1.1's.
              Floor = land-plate back (the bridge); script 68 lowers it to the flange back beyond the step wall.
Refuses to run twice (bend_y1 exists)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

G = "GF-2.0: "
DZW = "( Z_LAND - Z_FLANGE_FRONT ) * tan(draft)"            # outer wall block: Z_LAND outline -> flange-front plane
DZB = "( Z_LANDPLATE_BACK - Z_LAND ) * tan(draft)"          # pocket walls: Z_LAND outline -> land-plate-back plane

NEW = [  # name, expression, unit, comment (created in this order)
    ("g_bend", "3.0 mm", "mm", G + "DRIVING bend gap: panel bottom edge -> bridge pocket face over the tail span = straight "
     "0.5 + R_in 1.5 + tail 0.30 + clearance 0.45 + panel position 0.25 (concept_gf2 2.1); 3.09 is the most the 18.5 "
     "border holds with the full bead"),
    ("bend_y1", "panel_y1 + g_bend", "mm", G + "bridge pocket face (back face of the bend-gap slot) abs y at Z_LAND over "
     "the tail span (122.00), 1 deg widening to the back"),
    ("bend_nose_R", "1.5 mm", "mm", G + "nose round on the bridge back-inner edge (land-plate back x pocket face) >= "
     "tail_R_in_min, so a taut tail is never bent tighter"),
    ("land_break", "0.3 mm", "mm", G + "45 deg break on the land front-inner edge (land x pocket face) over the tail span: "
     "cannot snag a tail when the frame is lowered in J2"),
    ("tail_R_in_min", "1.5 mm", "mm", G + "minimum inner bend radius of both FPC tails, static (ASSUMPTION to confirm on a "
     "real panel)"),
    ("tail_straight_l0", "0.5 mm", "mm", G + "tail straight beyond the panel edge face before the first bend (ASSUMPTION)"),
    ("tail_t", "0.3 mm", "mm", G + "FPC tail thickness used for the route and the tail solids (estimate 0.3 +-0.05)"),
    ("Z_TAIL_LEG", "Z_TAIL_TFT_EXIT + 2 * ( tail_R_in_min + tail_t / 2 )", "mm", G + "nominal front-leg centre of both "
     "tails after the two 90 deg bends (-5.10, every glass_t; reference, no frame feature at it)"),
    ("div_x", "79.92 mm", "mm", G + "divider rib centre x = middle of the 8.20 gap between the tail exits (CTP x1 75.82, "
     "TFT x0 84.02, measured on DS1)"),
    ("div_t", "wall", "mm", G + "divider rib thickness at the bridge floor (Z_LANDPLATE_BACK), 1 deg both sides"),
    ("flange_y1_bottom", "max(glass_y1 + flange_beyond_glass; outer_y1 + ( Z_LAND - Z_FLANGE_FRONT ) * tan(draft))",
     "mm", G + "flange bottom edge abs y at the flange front = the bottom-wall outer face (tr_y1 + wall = 150.20 at "
     "Z_LAND, 1 deg) continued to the parting plane (150.235 at glass 3.0): flush; glass + 21 = 148.99 would cut the "
     "wall; max() keeps glass + 21 for larger borders"),
]
CHANGE = [  # name, expression or None (keep), comment
    ("border", "18.5 mm", G + "print-window edge -> glass edge on ALL FOUR sides (owner; was 14.0 top/left/right + chin "
     "44.51); the one driving value, may be retuned after the real-panel test"),
    ("glass_y1", "pw_y1 + border", G + "glass bottom edge abs y = pw_y1 + border (127.99), DERIVED (was the driving "
     "154.0 = chin)"),
    ("fl_y1", "flange_y1_bottom", G + "flange outline bottom (150.235 at the flange front, glass 3.0) = flange_y1_bottom"),
    ("logo_h", "15 mm", G + "logo zone max height in the 18.5 bottom border (>= 1.0 from the window, >= 2.5 from the edge)"),
    ("logo_cx", None, G + "logo zone centre x"),
    ("logo_cy", None, G + "logo zone centre y in the bottom border (118.74)"),
    ("glass_x0", None, "glass left (8.61)"), ("glass_x1", None, "glass right (199.09)"),
    ("glass_y0", None, "glass top (5.67)"),
    ("gc_x", None, "glass centre x = cut-out centre = fastener-pattern centre (103.85)"),
    ("gc_y", None, "glass centre y (66.83 = print-window centre at GF-2.0)"),
    ("f_x0", None, "left fastener line x (-2.39)"), ("f_x1", None, "right fastener line x (210.09)"),
    ("f_y0", None, "top fastener line y (-5.33)"), ("f_y1", None, "bottom fastener line y (138.99)"),
    ("fl_x0", None, "flange outline left (-12.39)"), ("fl_x1", None, "flange outline right (220.09)"),
    ("fl_y0", None, "flange outline top (-15.33)"),
    ("Z_LOOP_FRONT", None, "front-most point of the tails (reference): GF-2.0 only at the exit in the bend gap; the front "
     "legs run at Z_TAIL_LEG"),
    ("trough_R", None, "tail-pocket bottom inner corner radius (unchanged at GF-2.0)"),
]


def outer_wall_block(d, tl):
    sk = L.comp().sketches.itemByName("Outer wall block sketch")
    f = L.feature("Outer wall block")
    sk.timelineObject.rollTo(True)
    if not sk.redefine(L.plane("Z_FLANGE_FRONT plane")):
        raise RuntimeError("redefine failed")
    rep = {"( outer_x0 ) + 100 mm": "( outer_x0 - %s ) + 100 mm" % DZW,
           "( outer_x1 ) + 100 mm": "( outer_x1 + %s ) + 100 mm" % DZW,
           "( outer_y0 ) + 100 mm": "( outer_y0 - %s ) + 100 mm" % DZW,
           "( outer_y1 ) + 100 mm": "( outer_y1 + %s ) + 100 mm" % DZW,
           "frame_r": "frame_r + %s" % DZW}
    k = 0
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        e = dm.parameter.expression
        if e in rep:
            dm.parameter.expression = rep[e]
            k += 1
    if k != 8:
        raise RuntimeError("outer wall block dims changed %d" % k)
    tl.moveToEnd()
    f.timelineObject.rollTo(True)
    ok = f.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("Z_PCB - Z_FLANGE_FRONT")),
                            adsk.fusion.ExtentDirections.PositiveExtentDirection, L.VI(L.shrink()))
    tl.moveToEnd()
    if not ok:
        raise RuntimeError("outer wall block extent")
    return k


def split_tail_pocket(d, tl):
    sk = L.comp().sketches.itemByName("Tail pocket sketch")
    f = L.feature("Tail pocket")
    lines = [sk.sketchCurves.sketchLines.item(i) for i in range(sk.sketchCurves.sketchLines.count)]
    vert = [ln for ln in lines if abs(ln.startSketchPoint.geometry.x - ln.endSketchPoint.geometry.x) < 1e-7]
    if len(vert) != 2:
        raise RuntimeError("tail pocket vertical lines %d" % len(vert))
    vert.sort(key=lambda ln: ln.startSketchPoint.geometry.x)
    yb = L.P("bend_y1")
    xl, xr = vert[0].startSketchPoint.geometry.x * 10, vert[1].startSketchPoint.geometry.x * 10
    sk.isComputeDeferred = True
    ln = sk.sketchCurves.sketchLines.addByTwoPoints(L.P3(xl, yb), L.P3(xr, yb))
    gc = sk.geometricConstraints
    gc.addCoincident(ln.startSketchPoint, vert[0])
    gc.addCoincident(ln.endSketchPoint, vert[1])
    gc.addHorizontal(ln)
    L._dim_y(sk, ln.startSketchPoint, "bend_y1", (xl - 6) / 10.0)
    sk.isComputeDeferred = False
    front = L.pick_profiles(sk, lambda a, bb: bb[3] < yb + 0.01)
    if sk.profiles.count != 2 or front.count != 1:
        raise RuntimeError("tail pocket split: %d profiles, %d front" % (sk.profiles.count, front.count))
    f.timelineObject.rollTo(True)
    f.profile = front
    tl.moveToEnd()
    return L.under_constrained(sk)


def bridge_pocket(d, tl):
    f = L.feature("Tail pocket")
    f.timelineObject.rollTo(False)
    sk = L.new_sketch("Tail pocket over the bridge", "Z_LANDPLATE_BACK plane")
    L.rrect(sk, "tr_x0 - tail_side_add - %s" % DZB, "tr_x1 + tail_side_add + %s" % DZB, "bend_y1",
            "tr_y1 + %s" % DZB, "trough_R + %s" % DZB, corners={"bl", "br"})
    pr = L.solve(sk, 1)
    uc = L.under_constrained(sk)
    L.extrude(pr, "cut", "Z_TROUGH_TOP - Z_LANDPLATE_BACK + 1 mm", +1, L.grow(), "Tail pocket over the bridge", L.body())
    tl.moveToEnd()
    return uc


def run(_context: str):
    d = L.check_doc()
    L.log("=== 67 start")
    ups = d.userParameters
    if ups.itemByName("bend_y1") is not None:
        raise RuntimeError("67 already applied")
    tl = d.timeline
    old = {nm: (ups.itemByName(nm).expression, round(L.P(nm), 4)) for nm, e, c in CHANGE}
    for nm, e, u, c in NEW:
        L.set_param(nm, e, u, c)
    for nm, e, c in CHANGE:
        p = ups.itemByName(nm)
        if e is not None:
            p.expression = e
        p.comment = c
    d.computeAll()
    after_params = L.timeline_health()
    res = {"old": old, "new": {nm: (ups.itemByName(nm).expression, round(L.P(nm), 4)) for nm, e, c in CHANGE},
           "new_params": {nm: round(L.P(nm), 4) for nm, e, u, c in NEW}}
    res["health_after_params"] = after_params[1]
    res["outer_wall_block_dims"] = outer_wall_block(d, tl)
    d.computeAll()
    res["health_after_outer_wall"] = L.timeline_health()[1]
    res["tail_pocket_split_uc"] = split_tail_pocket(d, tl)
    d.computeAll()
    res["health_after_slot"] = L.timeline_health()[1]
    res["bridge_pocket_uc"] = bridge_pocket(d, tl)
    d.computeAll()
    n, bad = L.timeline_health()
    res.update({"timeline": n, "unhealthy": bad, "frame": L.body_dict()})
    L.dump(res, "gf20/67_params_border_bridge.json")
    L.log("67 %s" % res)
    print(res)
