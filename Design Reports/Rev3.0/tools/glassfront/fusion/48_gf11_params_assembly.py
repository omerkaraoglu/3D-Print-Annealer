"""48 - stage 3 (GF-1.1), parameters + assembly-side changes:
  * user parameter R_glass (6.0, the reference radius of EVERY glass-offset outline of the frame) is RENAMED to
    R_frame (Fusion rewrites every expression that used it: lip, recess, seat ring, step wall, trib_d1 ...), so the
    frame outlines keep R6.4 / R7.4 / R8.9; a NEW R_glass = 6.25 is the glass corner only (item 5), and R_cut = 7.55
    the sheet cut-out corner (item 5); glass, print layer, bead and both oven-sheet bodies are re-pointed to them
  * S8 spacer: DIN 988 6 x 12 x 1.0 shim (bore spacer_id 6.0) instead of DIN 9021 M4 (item 7)
  * the frame parameters for 49: counterbores (item 1), coring grooves (item 2), H6 jog (item 3), tail pocket
    (item 4), F5-F8 tube blend (item 6).
Idempotent: skips the rename when R_frame exists."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

C = "GF-1.1: "
NEW = [
    ("R_glass", "6.25 mm", C + "glass corner radius (item 5; frame outlines use R_frame 6.0)"),
    ("R_cut", "7.55 mm", C + "sheet cut-out corner radius (item 5; cut-out rectangle unchanged)"),
    ("spacer_id", "6.0 mm", C + "S8 spacer DIN 988 6 x 12 x 1.0 bore (passes the 5.7 weld flange)"),
    ("spacer_od", "12 mm", C + "S8 spacer DIN 988 6 x 12 x 1.0 OD"),
    ("cb_w", "6.6 mm", C + "fastener counterbore width at its opening (Z_SHEET_BACK), stadium coaxial with the slot"),
    ("cb_l", "8.2 mm", C + "fastener counterbore length at its opening, along the slot axis"),
    ("cb_floor", "1.6 mm", C + "counterbore floor above Z_SHEET_BACK (1.4 flange + 0.2); F1-F4 in the pad, F5-F8 0.6 "
                             "into the flange front"),
    ("cb_r", "0.2 mm", C + "counterbore floor edge round"),
    ("core_r_in", "6.2 mm", C + "coring groove inner radius at the tube top (washer seat dia 12.4)"),
    ("core_r_out", "7.6 mm", C + "coring groove outer radius at the tube top (skin to the dia-18 tube 1.4)"),
    ("core_depth", "3.3 mm", C + "coring groove depth below Z_TUBE_TOP (floor 2.7 above the pad face at glass 3.0)"),
    ("core_floor_r", "0.5 mm", C + "coring groove floor edge rounds"),
    ("tail_side_add", "0.3 mm", C + "tail pocket side walls moved out by this (x tr_x0 - / tr_x1 + ), walls and cells "
                                  "stay"),
    ("h6_wall_min", "1.1 mm", C + "tail wall left beside the H6 cell jog, at Z_PCB (the thinnest place)"),
    ("h6_corner_r", "2.5 mm", C + "H6 cell corner arc at the boss (tangent point inside the boss at every Z)"),
    ("h6_jog_y", "h6_y + 2.8 mm", C + "H6 cell jog: lower end of the jogged wall (abs y)"),
    ("h6_jog_len", "1.6 mm", C + "H6 cell jog: length (y) of the slant back to the cell wall"),
    ("tube_sw_r", "1.2 mm", C + "F5-F8 tube to step-wall blend (item 6)"),
]


def set_dims(cn, sk_name, old, new):
    n = 0
    c = L.occ_by_comp(cn).component if cn != L.COMP_NAME else L.comp()
    sk = c.sketches.itemByName(sk_name)
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        if dm.parameter.expression.replace(" ", "") == old.replace(" ", ""):
            dm.parameter.expression = new
            n += 1
    return n


def run(_context: str):
    L.check_doc()
    L.log("=== 48 start")
    d = L.des()
    ups = d.userParameters
    if ups.itemByName("R_frame") is None:
        p = ups.itemByName("R_glass")
        p.name = "R_frame"
        p.comment = ("GF-1.1: reference radius of the frame outlines = GF-1.0 R_glass 6.0 (lip_in R6.4, lip_out R7.4, "
                     "seat ring R8.9 = R_frame + s)")
    for n, e, cmt in NEW:
        L.set_param(n, e, "mm", cmt)
    out = {
        "glass": set_dims("Glass", "Glass outline sketch", "R_frame + ( 0 mm )", "R_glass"),
        "print": set_dims("Glass", "Glass print sketch", "R_frame - ( print_setback )", "R_glass - print_setback"),
        "bead_out": set_dims("Bead", "Bead sketch", "R_frame - ( bead_edge )", "R_glass - bead_edge"),
        "bead_in": set_dims("Bead", "Bead sketch", "R_frame - ( bead_edge + bead_w )", "R_glass - ( bead_edge + bead_w )"),
        "sheet_S4": set_dims("Oven sheet", "Oven sheet S4/S8 (no holes) sketch", "R_frame + ( s_cut )", "R_cut"),
        "sheet_R4": set_dims("Oven sheet", "Oven sheet R4 (rivet holes) sketch", "R_frame + ( s_cut )", "R_cut"),
        "S8_spacer_id": set_dims("Washers, nuts, spacers S8 F5-F8 (hidden)", "S8 spacers DIN 9021 M4 sketch", "w4_id",
                                 "spacer_id"),
        "S8_spacer_od": set_dims("Washers, nuts, spacers S8 F5-F8 (hidden)", "S8 spacers DIN 9021 M4 sketch", "w4_od",
                                 "spacer_od")}
    c8 = L.occ_by_comp("Washers, nuts, spacers S8 F5-F8 (hidden)").component
    for i in range(c8.bRepBodies.count):
        b = c8.bRepBodies.item(i)
        if b.name.startswith("Spacer DIN 9021 M4"):
            b.name = b.name.replace("Spacer DIN 9021 M4", "Spacer DIN 988 6x12x1.0")
    d.computeAll()
    n, bad = L.timeline_health()
    L.log("48 dims %s; timeline %d unhealthy %s" % (out, n, bad))
    print(out, n, bad, "R_frame", L.P("R_frame"), "R_glass", L.P("R_glass"), "R_cut", L.P("R_cut"))
