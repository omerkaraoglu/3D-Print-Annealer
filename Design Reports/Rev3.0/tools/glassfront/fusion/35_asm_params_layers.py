"""35 - stage 2, Part B: assembly user parameters + the layer components, siblings of 'Frame GF' under the root.
Every outline / level is a user-parameter expression (component coords = model coords, identity occurrences):
  'Glass'           glass outline (glass_x0..glass_y1, R_glass), Z_GLASS_FRONT .. Z_GLASS_BACK (glass_t), chamfer
                    glass_arris x 45 deg on the front and back edges; body 'Glass print (black, 0.02)' = the printed
                    black layer, print_t deep INSIDE the glass back (outer edge print_setback inside the glass edge,
                    print window pw_* R pw_r open); the glass is cut by it (combine, tool kept) so the two bodies do
                    not overlap; sketch 'Logo zone' (hidden) on the glass back.
  'Optical bond'    panel outline (panel_*), R bond_r, Z_GLASS_BACK .. Z_CTP_FRONT (t_opt)
  'Formex sheet'    panel outline - sheet_inset, R1, Z_FORMEX_FRONT .. Z_SEAT (sheet_t), as v2
  'Bead'            ring bead_edge .. bead_edge + bead_w inside the glass edge (R_glass - ...), Z_LAND .. Z_GLASS_BACK
                    (t_bond), with dia pip_d holes at the 8 pips (the bead flows round them)
  'VHB tape strips' 4 straight strips s_tape_in .. s_tape_out, ending tape_margin before the dia pad_d corner pads,
                    Z_SHEET_BACK .. Z_FLANGE_FRONT (t_gap)
  'Oven sheet'      flange outline + sheet_margin (R flange_R + sheet_margin) with the cut-out (s_cut, R_glass + s_cut),
                    Z_GLASS_FRONT .. Z_SHEET_BACK (t_sheet): body 'Oven sheet S4/S8 (no holes)' and hidden body
                    'Oven sheet R4 (rivet holes)' with dia riv_hole at F1-F4.
Appearances: glass 'Glass (Grey)', print black enamel, bond translucent blue, Formex grey, bead RED and tape YELLOW
(visualisation colours; both are black in reality), sheet steel satin."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

C = "stage 2 assembly: "
PARAMS = [
    ("board_dz", "0.08 mm", C + "KiCad STEP has no copper / mask: board occurrence +0.08 so the physical PCB back is Z 0 (v2 32)"),
    ("ds1_model_back", "-5.0 mm", C + "DS1 panel back in the KiCad board model (v2 stand-off 5.0)"),
    ("ds1_dz", "Z_PANEL_BACK - ds1_model_back", C + "DS1 occurrence (panel, CTP, tails) moved by this in Z (snapshot, script 38)"),
    ("glass_arris", "0.5 mm", C + "glass arris 0.5 x 45 deg front and back (concept 4.3)"),
    ("print_t", "0.02 mm", C + "printed black layer shown as a 0.02 body inside the glass back (real 15-30 um)"),
    ("print_setback", "glass_arris + 0.1 mm", C + "print outer edge inside the glass edge (flat back face ends at glass_arris)"),
    ("logo_cx", "gc_x", C + "logo zone centre x (chin)"), ("logo_cy", "( pw_y1 + glass_y1 ) / 2", C + "logo zone centre y"),
    ("logo_w", "100 mm", C + "logo zone max width"), ("logo_h", "20 mm", C + "logo zone max height"),
    ("bond_r", "0.5 mm", C + "optical bond corner radius (panel-sized)"),
    ("sheet_inset", "0.5 mm", C + "Formex sheet = panel outline - this per side, R1 (v2 32)"),
    ("sheet_margin", "40 mm", C + "oven-sheet patch = flange outline + this all round"),
    ("stud_d", "4.0 mm", C + "M4 weld stud shank (thread major dia)"),
    ("stud_l", "16 mm", C + "M4 x 16 CD weld stud, length from the sheet back"),
    ("stud_fl_d", "5.5 mm", C + "ISO 13918 PT M4 weld flange dia (5.3..5.7)"),
    ("stud_fl_k", "0.7 mm", C + "ISO 13918 PT M4 weld flange height (0.7..1.4; minimum modelled)"),
    ("w4_od", "12 mm", C + "DIN 9021 M4 washer OD"), ("w4_id", "4.3 mm", C + "DIN 9021 M4 washer ID"),
    ("w4_t", "1.0 mm", C + "DIN 9021 M4 washer thickness"),
    ("nut_s", "7 mm", C + "ISO 10511 M4 nyloc nut across flats"), ("nut_m", "5 mm", C + "ISO 10511 M4 nyloc nut height"),
    ("riv_d", "4.8 mm", C + "R4 blind rivet shank dia"), ("riv_head_d", "10 mm", C + "R4 dome head dia"),
    ("riv_head_k", "1.6 mm", C + "R4 dome head height in front of the sheet (master 1.5-2.0 proud)"),
    ("riv_hole", "5.2 mm", C + "R4 sheet hole (tri-fold 4.8: 5.2 +0.1/0, master)"),
    ("riv_blind_d", "9 mm", C + "R4 formed blind head envelope dia (ASSUMED, tri-fold / bulb 4.8)"),
    ("riv_blind_h", "4 mm", C + "R4 formed blind head envelope height (ASSUMED)"),
    ("w5_od", "15 mm", C + "DIN 9021 M5 backing washer OD"), ("w5_id", "5.3 mm", C + "DIN 9021 M5 washer ID"),
    ("w5_t", "1.2 mm", C + "DIN 9021 M5 washer thickness"),
    ("socket_d", "12 mm", C + "socket OD for the M4 nuts (v2 rule)"), ("socket_top", "45 mm", C + "socket check cylinder top Z"),
]


def grect_in(sk, s_expr):
    """glass outline offset INWARD by s (expression)"""
    s = "( %s )" % s_expr
    return L.rrect(sk, "glass_x0 + %s" % s, "glass_x1 - %s" % s, "glass_y0 + %s" % s, "glass_y1 - %s" % s,
                   "R_glass - %s" % s)


def flat_faces(b, z_mm, nz_sign):
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) > 0.9999 and n.z * nz_sign > 0 and abs(f.pointOnFace.z * 10 - z_mm) < 1e-4:
            out.append(f)
    return out


def run(_context: str):
    L.check_doc()
    L.log("=== 35 start")
    for n, e, c in PARAMS:
        L.set_param(n, e, "mm", c)
    res = {}
    # ------------------------------------------------------------------------------------------------- Glass
    o = L.new_comp("Glass")
    c = o.component
    pf = L.cplane(c, "Z_GLASS_FRONT (glass)", "Z_GLASS_FRONT")
    pb = L.cplane(c, "Z_GLASS_BACK (glass)", "Z_GLASS_BACK")
    sk = L.csketch(c, "Glass outline", pf)
    L.grect(sk, "0 mm")
    pr = L.solve(sk, 1)
    f = L.cextrude(c, pr, "new", "glass_t", +1, "Glass", body_name="Glass")
    glass = f.bodies.item(0)
    edges = adsk.core.ObjectCollection.create()
    for fc in flat_faces(glass, L.P("Z_GLASS_FRONT"), -1) + flat_faces(glass, L.P("Z_GLASS_BACK"), +1):
        for k in range(fc.edges.count):
            edges.add(fc.edges.item(k))
    ci = c.features.chamferFeatures.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, L.VI("glass_arris"), False)
    ch = c.features.chamferFeatures.add(ci)
    ch.name = "Glass arris front + back"
    sk = L.csketch(c, "Glass print", pb)
    grect_in(sk, "print_setback")
    L.rrect(sk, "pw_x0", "pw_x1", "pw_y0", "pw_y1", "pw_r")
    L.solve(sk)
    ring = L.profiles_with_loops(sk, 2)
    if ring.count != 1:
        raise RuntimeError("print ring profiles %d" % ring.count)
    f = L.cextrude(c, ring, "new", "print_t", -1, "Glass print", body_name="Glass print (black, 0.02)")
    prt = f.bodies.item(0)
    tools = adsk.core.ObjectCollection.create()
    tools.add(prt)
    cbi = c.features.combineFeatures.createInput(glass, tools)
    cbi.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    cbi.isKeepToolBodies = True
    cb = c.features.combineFeatures.add(cbi)
    cb.name = "Glass minus print layer"
    sk = L.csketch(c, "Logo zone", pb)
    L.rrect(sk, "logo_cx - logo_w / 2", "logo_cx + logo_w / 2", "logo_cy - logo_h / 2", "logo_cy + logo_h / 2")
    L.solve(sk)
    sk.isVisible = False
    glass.appearance = L.appearance("Glass (Grey)")
    prt.appearance = L.appearance("Paint - Enamel Glossy (Black)")
    res["Glass"] = [L.body_stats(glass), L.body_stats(prt)]
    # ------------------------------------------------------------------------------------------------- Optical bond
    o = L.new_comp("Optical bond")
    c = o.component
    sk = L.csketch(c, "Optical bond", L.cplane(c, "Z_GLASS_BACK (bond)", "Z_GLASS_BACK"))
    L.rrect(sk, "panel_x0", "panel_x1", "panel_y0", "panel_y1", "bond_r")
    f = L.cextrude(c, L.solve(sk, 1), "new", "t_opt", +1, "Optical bond", body_name="Optical bond (t_opt)")
    f.bodies.item(0).appearance = L.appearance("Plastic - Translucent Glossy (Blue)")
    res["Optical bond"] = L.body_stats(f.bodies.item(0))
    # ------------------------------------------------------------------------------------------------- Formex
    o = L.new_comp("Formex sheet")
    c = o.component
    sk = L.csketch(c, "Formex sheet", L.cplane(c, "Z_FORMEX_FRONT (Formex)", "Z_FORMEX_FRONT"))
    L.rrect(sk, "panel_x0 + sheet_inset", "panel_x1 - sheet_inset", "panel_y0 + sheet_inset", "panel_y1 - sheet_inset",
            "1 mm")
    f = L.cextrude(c, L.solve(sk, 1), "new", "Z_SEAT - Z_FORMEX_FRONT", +1, "Formex sheet", body_name="Formex sheet")
    f.bodies.item(0).appearance = L.appearance("Plastic - Matte (Gray)")
    res["Formex sheet"] = L.body_stats(f.bodies.item(0))
    # ------------------------------------------------------------------------------------------------- Bead
    o = L.new_comp("Bead")
    c = o.component
    sk = L.csketch(c, "Bead", L.cplane(c, "Z_LAND (bead)", "Z_LAND"))
    grect_in(sk, "bead_edge")
    grect_in(sk, "bead_edge + bead_w")
    for k in range(1, 9):
        L.circle(sk, "pip%d_x" % k, "pip%d_y" % k, "pip_d")
    L.solve(sk)
    pr = L.profiles_with_loops(sk, 10)
    if pr.count != 1:
        raise RuntimeError("bead profile with 10 loops: %d" % pr.count)
    f = L.cextrude(c, pr, "new", "t_bond", -1, "Bead", body_name="Bead (4.0 x t_bond)")
    f.bodies.item(0).appearance = L.appearance("Plastic - Matte (Red)")
    res["Bead"] = L.body_stats(f.bodies.item(0))
    # ------------------------------------------------------------------------------------------------- Tape
    o = L.new_comp("VHB tape strips")
    c = o.component
    pl = L.cplane(c, "Z_SHEET_BACK (tape)", "Z_SHEET_BACK")
    end_x0, end_x1 = "f1_x + pad_d / 2 + tape_margin", "f2_x - pad_d / 2 - tape_margin"
    end_y0, end_y1 = "f1_y + pad_d / 2 + tape_margin", "f4_y - pad_d / 2 - tape_margin"
    strips = {"top": (end_x0, end_x1, "glass_y0 - s_tape_out", "glass_y0 - s_tape_in"),
              "bottom": (end_x0, end_x1, "glass_y1 + s_tape_in", "glass_y1 + s_tape_out"),
              "left": ("glass_x0 - s_tape_out", "glass_x0 - s_tape_in", end_y0, end_y1),
              "right": ("glass_x1 + s_tape_in", "glass_x1 + s_tape_out", end_y0, end_y1)}
    res["VHB tape strips"] = []
    for nm, (x0, x1, y0, y1) in strips.items():
        sk = L.csketch(c, "VHB strip %s" % nm, pl)
        L.rrect(sk, x0, x1, y0, y1)
        f = L.cextrude(c, L.solve(sk, 1), "new", "t_gap", +1, "VHB strip %s" % nm, body_name="VHB strip %s" % nm)
        f.bodies.item(0).appearance = L.appearance("Plastic - Matte (Yellow)")
        res["VHB tape strips"].append(L.body_stats(f.bodies.item(0)))
    # ------------------------------------------------------------------------------------------------- Oven sheet
    o = L.new_comp("Oven sheet")
    c = o.component
    pl = L.cplane(c, "Z_GLASS_FRONT (sheet)", "Z_GLASS_FRONT")
    bodies = {}
    for nm, holes in (("Oven sheet S4/S8 (no holes)", False), ("Oven sheet R4 (rivet holes)", True)):
        sk = L.csketch(c, nm, pl)
        L.rrect(sk, "fl_x0 - sheet_margin", "fl_x1 + sheet_margin", "fl_y0 - sheet_margin", "fl_y1 + sheet_margin",
                "flange_R + sheet_margin")
        L.grect(sk, "s_cut")
        if holes:
            for k in range(1, 5):
                L.circle(sk, "f%d_x" % k, "f%d_y" % k, "riv_hole")
        L.solve(sk)
        pr = L.profiles_with_loops(sk, 6 if holes else 2)
        if pr.count != 1:
            raise RuntimeError("%s profile: %d" % (nm, pr.count))
        f = L.cextrude(c, pr, "new", "t_sheet", +1, nm, body_name=nm)
        bodies[nm] = f.bodies.item(0)
        bodies[nm].appearance = L.appearance("Steel - Satin")
    bodies["Oven sheet R4 (rivet holes)"].isLightBulbOn = False
    res["Oven sheet"] = [L.body_stats(b) for b in bodies.values()]
    n, bad = L.timeline_health()
    L.log("35 %s; timeline %d unhealthy %s" % (res, n, bad))
    print(res, n, bad)
