"""02 - all user parameters (document level) of the GlassFront frame and the construction planes at the Z levels.

Single source of truth: Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json (GF-1.0, frozen).
  * driving parameters: lower-case names as in the master JSON (glass_t, t_opt, t_bond, t_sheet, t_gap, g_bs, ...)
  * derived Z levels: the master JSON expressions (Z_* names as in the JSON), never typed numbers
  * level snap (cad_rules): snap_keep = min(1; floor(|Z_FLANGE_BACK_RAW - Z_LANDPLATE_BACK_RAW| / level_snap))
    is 0 when the two plate backs differ by < level_snap (0.5) and 1 otherwise;
    Z_FLANGE_BACK = Z_STEPWALL_BACK + snap_keep * (Z_FLANGE_BACK_RAW - Z_STEPWALL_BACK) (same for the land plate),
    Z_STEPWALL_BACK = max(Z_FLANGE_BACK_RAW; Z_LANDPLATE_BACK_RAW)  -> fully automatic, no manual step
  * plan rectangles: expressions of print window / border / glass_y1 / s-offsets, so they reproduce the JSON numbers
  * v2 parameters carried over (carried_over_from_v2) with their v2 values; 26 support-rib positions as rib<k>_a
Planes (in component 'Frame GF', hidden): one per Z level used by a sketch. Root planes (visible names 'REF ...')
for stage 2: glass front / back, CTP front, panel back, Formex front, sheet back, flange front, land.

Expects: 01 done (active document tagged gf/doc). Leaves: parameters, planes. Re-runnable (set_param updates).
"""
import importlib
import json
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

M = "mm"
D = "deg"
U = ""
PARAMS = [
    # ---- moulding rules (v2 carried over) -------------------------------------------------------------------
    ("wall", "2.5 mm", M, "nominal wall, PA6-GF30 (v1 frame.py WALL) [v2]"),
    ("rib", "1.5 mm", M, "rib thickness at the root = 0.6 x wall (v1 RIB_T) [v2]"),
    ("draft", "1 deg", D, "draft on every face along the pull Z (v1 DRAFT) [v2]"),
    ("draft_loc", "0.5 deg", D, "draft of pilots and fastener slots (v1 DRAFT_LOC) [v2]"),
    ("fillet_root", "0.5 mm", M, "root fillets at bosses, ribs, walls/plates (v1 FILLET_IN) [v2]"),
    ("frame_r", "5 mm", M, "outer wall block corner radius (v1 FRAME_R) [v2]"),
    ("lip_top_r", "0.3 mm", M, "GF: lip top edges R0.3 both sides (concept 4.4, flat 0.37)"),
    ("lip_root_r", "0.2 mm", M, "GF: lip root fillet R0.2 (lip outer face to seat ring top)"),
    ("level_snap", "0.5 mm", M, "GF cad_rules level snap: plate backs closer than this are snapped together"),
    # ---- driving parameters (master JSON driving_parameters) ---------------------------------------------------
    ("glass_t", "3.0 mm", M, "glass thickness, DRIVING; valid 1.1 / 2.0 / 3.0 / 4.0 (master JSON)"),
    ("t_opt", "0.3 mm", M, "optical bond glass -> CTP lens (LOCA 0.30 +-0.03)"),
    ("t_bond", "1.0 mm", M, "glass -> land bond line, elastic bead, nominal (flush jig)"),
    ("t_sheet", "1.0 mm", M, "oven front sheet, steel 0.8..1.5; lip height above the seat ring"),
    ("t_gap", "1.0 mm", M, "flange front -> sheet back between the hard stops (VHB / foam)"),
    ("g_bs", "0.8 mm", M, "panel back -> Formex air gap, nominal (back-stop)"),
    ("print_inset", "0.3 mm", M, "print window = AA inset by this per side"),
    ("border", "14.0 mm", M, "print-window edge -> glass edge, top / left / right"),
    ("glass_y1", "154.0 mm", M, "glass bottom edge, abs y (chin)"),
    ("R_glass", "6.0 mm", M, "glass corner radius"),
    ("g2", "0.4 mm", M, "gap glass edge -> lip inner face at 20 C (at the lip top)"),
    ("lip_w", "1.0 mm", M, "lip width (root)"),
    ("g1", "0.4 mm", M, "gap lip outer face -> sheet cut-out edge at 20 C"),
    ("seat_ring_w", "1.5 mm", M, "sheet-seat ring width outside the lip"),
    ("pocket_clr", "0.8 mm", M, "panel outline -> clearance pocket wall per side (v2 0.25 superseded)"),
    ("bead_w", "4.0 mm", M, "glass -> frame bead width after squeeze (reference, not modelled)"),
    ("bead_edge", "0.9 mm", M, "bead outer edge inside the glass edge"),
    ("bead_pocket_min", "1.0 mm", M, "min bead inner edge -> pocket face (reference)"),
    ("fast_off", "11.0 mm", M, "fastener centre outside the glass edge (x and y at corners, normal at mid-sides)"),
    ("flange_beyond_glass", "21.0 mm", M, "flange outline = glass + this"),
    ("flange_R", "10.0 mm", M, "flange outer corner radius (centre = corner fastener)"),
    ("flange_t", "2.5 mm", M, "flange thickness = wall"),
    ("slot_w", "5.4 mm", M, "fastener stadium slot width at the flange front, 0.5 deg draft"),
    ("slot_l", "7.0 mm", M, "fastener stadium slot length, long axis towards the glass centre"),
    ("pad_d", "18.0 mm", M, "F1-F4 front pad dia (top at Z_SHEET_BACK)"),
    ("tube_top_d", "pad_d", M, "fastener tube dia at its top (= pad_d), 1 deg draft"),
    ("tube_h", "2.5 mm", M, "fastener tube height above the flange back"),
    ("pip_d", "1.5 mm", M, "stand-off pip dia at the base, 1 deg draft"),
    ("pip_h", "0.5 mm", M, "stand-off pip height above the land"),
    ("tape_w", "12.0 mm", M, "VHB strip width (reference)"),
    ("tape_margin", "1.0 mm", M, "min flat flange face beyond each tape edge (reference)"),
    ("trough_R", "1.5 mm", M, "tail-pocket bottom inner corner radius (v2 trough_r 5.0 superseded)"),
    # ---- v2 stack (carried over) ---------------------------------------------------------------------------
    ("sheet_t", "0.4 mm", M, "Formex insulating sheet (v1 SHEET_T) [v2]"),
    ("panel_t", "5.32 mm", M, "SAT070AT40D21 LCM 3.34 + CTP 1.98 (v1 PANEL_T) [v2]"),
    ("shelf_t", "wall", M, "shelf (Formex seat) thickness = wall [v2]"),
    ("loop_z_top", "2.55 mm", M, "top of the FPC U-loop return legs (panel model) [v2]"),
    ("loop_clr", "1.5 mm", M, "clearance round the loop envelopes [v2]"),
    ("cell_rib_h", "5 mm", M, "corner-cell rib top above the land (v2: above Z_FRONT) [v2]"),
    ("seat_w", "2.6 mm", M, "shelf reach inside the panel outline (v1 SEAT_W) [v2]"),
    ("rib_bury", "0.5 mm", M, "support / cell / tube ribs run this far into the wall they meet [v2]"),
    ("rib_overshoot", "0.5 mm", M, "support-rib free ends run this far past the cut that trims them flush [v2.1]"),
    # ---- Z levels (master JSON derived_levels.expressions) -----------------------------------------------------
    ("Z_PCB", "0 mm", M, "PCB back = boss / support-rib / wall tops [v2]"),
    ("Z_TROUGH_TOP", "loop_z_top + loop_clr", M, "tail-pocket walls / bottom beam top, outside the board only [v2]"),
    ("Z_SEAT", "-4.6 mm", M, "shelf front = Formex back (Formex PSA-bonded) [v2 level]"),
    ("Z_SHELF_BACK", "Z_SEAT + shelf_t", M, "shelf back [v2]"),
    ("Z_FORMEX_FRONT", "Z_SEAT - sheet_t", M, "Formex front (= v2 panel back)"),
    ("Z_PANEL_BACK", "Z_FORMEX_FRONT - g_bs", M, "panel back, nominal (floats with the tolerances)"),
    ("Z_CTP_FRONT", "Z_PANEL_BACK - panel_t", M, "CTP cover-lens front"),
    ("Z_GLASS_BACK", "Z_CTP_FRONT - t_opt", M, "glass printed face"),
    ("Z_GLASS_FRONT", "Z_GLASS_BACK - glass_t", M, "FLUSH PLANE = lip top = sheet front"),
    ("Z_SHEET_BACK", "Z_GLASS_FRONT + t_sheet", M, "sheet back = seat-ring top = corner-pad tops"),
    ("Z_FLANGE_FRONT", "Z_SHEET_BACK + t_gap", M, "flange front face (tape / gasket on it); parting line on the flange outline"),
    ("Z_LAND", "Z_GLASS_BACK + t_bond", M, "glass land = recess floor (bead, pips)"),
    ("Z_PIP_TOP", "Z_LAND - pip_h", M, "stand-off pip tops"),
    ("Z_FLANGE_BACK_RAW", "Z_FLANGE_FRONT + flange_t", M, "flange back before the level snap"),
    ("Z_LANDPLATE_BACK_RAW", "Z_LAND + wall", M, "land-plate back before the level snap"),
    ("Z_STEPWALL_BACK", "max(Z_FLANGE_BACK_RAW; Z_LANDPLATE_BACK_RAW)", M, "back of the step wall = max of the two plate backs"),
    ("snap_keep", "min(1; floor(abs(Z_FLANGE_BACK_RAW - Z_LANDPLATE_BACK_RAW) / level_snap))", U,
     "level snap: 0 = the plate backs differ by < level_snap -> both snapped to Z_STEPWALL_BACK; 1 = no snap"),
    ("Z_FLANGE_BACK", "Z_STEPWALL_BACK + snap_keep * ( Z_FLANGE_BACK_RAW - Z_STEPWALL_BACK )", M,
     "flange back = Z_FLANGE_FRONT + flange_t; = Z_STEPWALL_BACK if within level_snap of the land-plate back"),
    ("Z_LANDPLATE_BACK", "Z_STEPWALL_BACK + snap_keep * ( Z_LANDPLATE_BACK_RAW - Z_STEPWALL_BACK )", M,
     "land-plate back (corner-cell floors, PCB-boss bases) = Z_LAND + wall, snapped as the flange back"),
    ("Z_TUBE_TOP", "Z_FLANGE_BACK + tube_h", M, "fastener tube top = washer / rivet seat"),
    ("Z_CELL_RIB_TOP", "Z_LAND + cell_rib_h", M, "corner-cell rib tops (v2 rule: cell_rib_h above the front face)"),
    ("trib_h_min", "1.0 mm", M, "GF: minimum tube-rib height above the flange back (only governs when the step wall "
                                "does not stand above the flange back, i.e. at the level snap)"),
    ("Z_TRIB_TOP", "max(min(Z_TUBE_TOP; Z_STEPWALL_BACK); Z_FLANGE_BACK + trib_h_min)", M,
     "GF: tube-rib top = tube top, but never above the step-wall back (no stub above the plate), and at least "
     "trib_h_min above the flange back"),
    ("Z_TAIL_TFT_EXIT", "Z_PANEL_BACK - 2.6 mm", M, "TFT tail centre at the panel edge (reference, estimated)"),
    ("Z_TAIL_CTP_EXIT", "Z_PANEL_BACK - 3.9 mm", M, "CTP tail centre at the panel edge (reference, estimated)"),
    ("Z_LOOP_FRONT", "Z_TAIL_CTP_EXIT - 0.15 mm", M, "front-most point of the tail loops (reference)"),
    # ---- panel / view area / active area (abs KiCad x, y down) ------------------------------------------------
    ("panel_x0", "20.02 mm", M, "panel outline left (DS1 Dwgs.User) [v2]"),
    ("panel_x1", "184.92 mm", M, "panel outline right [v2]"),
    ("panel_y0", "19.00 mm", M, "panel outline top [v2]"),
    ("panel_y1", "119.00 mm", M, "panel outline bottom [v2]"),
    ("va_x0", "26.31 mm", M, "CTP cover view area left [v2] (reference)"),
    ("va_x1", "181.39 mm", M, "CTP cover view area right [v2] (reference)"),
    ("va_y0", "23.23 mm", M, "CTP cover view area top [v2] (reference)"),
    ("va_y1", "110.15 mm", M, "CTP cover view area bottom [v2] (reference)"),
    ("aa_x0", "26.81 mm", M, "display active area left (DS)"),
    ("aa_x1", "180.89 mm", M, "display active area right (DS)"),
    ("aa_y0", "23.87 mm", M, "display active area top (DS)"),
    ("aa_y1", "109.79 mm", M, "display active area bottom (DS)"),
    ("pw_x0", "aa_x0 + print_inset", M, "print window left (27.11)"),
    ("pw_x1", "aa_x1 - print_inset", M, "print window right (180.59)"),
    ("pw_y0", "aa_y0 + print_inset", M, "print window top (24.17)"),
    ("pw_y1", "aa_y1 - print_inset", M, "print window bottom (109.49)"),
    ("pw_r", "0.5 mm", M, "print window corner radius (reference for the glass)"),
    # ---- glass and its offsets (s = distance outward from the glass edge) --------------------------------------
    ("glass_x0", "pw_x0 - border", M, "glass left (13.11)"),
    ("glass_x1", "pw_x1 + border", M, "glass right (194.59)"),
    ("glass_y0", "pw_y0 - border", M, "glass top (10.17)"),
    ("gc_x", "( glass_x0 + glass_x1 ) / 2", M, "glass centre x = cut-out centre = fastener-pattern centre (103.85)"),
    ("gc_y", "( glass_y0 + glass_y1 ) / 2", M, "glass centre y (82.085)"),
    ("s_lip_in", "g2", M, "s of the lip inner face = recess wall AT THE LIP TOP (lip_in R6.4)"),
    ("s_lip_out", "g2 + lip_w", M, "s of the lip outer face AT THE LIP ROOT (lip_out R7.4)"),
    ("s_cut", "s_lip_out + g1", M, "s of the sheet cut-out edge (reference; cut R7.8)"),
    ("s_ring", "s_lip_out + seat_ring_w", M, "s of the seat-ring / step-wall outer face AT THE FLANGE FRONT (R8.9)"),
    ("s_ring_b", "s_ring + ( Z_FLANGE_BACK - Z_FLANGE_FRONT ) * tan(draft)", M,
     "step-wall back outline drawn on the flange-front plane so that it is s_ring AT THE FLANGE BACK"),
    ("s_tape_in", "s_ring + tape_margin", M, "tape strips inner edge (reference, 3.9)"),
    ("s_tape_out", "s_tape_in + tape_w", M, "tape strips outer edge (reference, 15.9)"),
    ("pip_in", "bead_edge + bead_w / 2", M, "pip / bead centre line inside the glass edge (2.9)"),
    # ---- fasteners F1-F8 -----------------------------------------------------------------------------------
    ("f_x0", "glass_x0 - fast_off", M, "left fastener line x (2.11)"),
    ("f_x1", "glass_x1 + fast_off", M, "right fastener line x (205.59)"),
    ("f_y0", "glass_y0 - fast_off", M, "top fastener line y (-0.83)"),
    ("f_y1", "glass_y1 + fast_off", M, "bottom fastener line y (165.00)"),
    ("fl_x0", "glass_x0 - flange_beyond_glass", M, "flange outline left (-7.89)"),
    ("fl_x1", "glass_x1 + flange_beyond_glass", M, "flange outline right (215.59)"),
    ("fl_y0", "glass_y0 - flange_beyond_glass", M, "flange outline top (-10.83)"),
    ("fl_y1", "glass_y1 + flange_beyond_glass", M, "flange outline bottom (175.00)"),
    ("trib_d0", "tube_top_d / 2 - rib_bury", M, "tube rib F1-F4: start along its axis from the fastener centre (buried in the tube)"),
    ("trib_d1", "( fast_off + R_glass ) * sqrt(2) - ( R_glass + s_ring ) + rib_bury", M,
     "tube rib F1-F4: end along its 45 deg axis (buried rib_bury into the step wall at the corner arc)"),
    # ---- clearance pocket, shelf, window (v2 rules, GF pocket_clr) ---------------------------------------------
    ("pocket_x0", "panel_x0 - pocket_clr", M, "clearance pocket left at Z_SEAT (19.22)"),
    ("pocket_x1", "panel_x1 + pocket_clr", M, "clearance pocket right at Z_SEAT (185.72)"),
    ("pocket_y0", "panel_y0 - pocket_clr", M, "clearance pocket top at Z_SEAT (18.20)"),
    ("pocket_y1", "panel_y1 + pocket_clr", M, "clearance pocket bottom at Z_SEAT (119.80)"),
    ("pocket_r", "0.5 mm", M, "clearance pocket corner radius"),
    ("win_x0", "panel_x0 + seat_w", M, "window inside the shelf, left, at Z_SEAT [v2]"),
    ("win_x1", "panel_x1 - seat_w", M, "window right [v2]"),
    ("win_y0", "panel_y0 + seat_w", M, "window top [v2]"),
    ("win_y1", "panel_y1 - seat_w", M, "window bottom [v2]"),
    ("win_r", "1 mm", M, "window corner radius [v2]"),
    # ---- tail pocket ---------------------------------------------------------------------------------------
    ("loop_ctp_x0", "40.7 mm", M, "CTP U-loop envelope left (panel model) [v2]"),
    ("loop_ctp_x1", "75.8 mm", M, "CTP U-loop envelope right [v2]"),
    ("loop_ctp_y1", "137.4 mm", M, "CTP U-loop envelope bottom [v2]"),
    ("loop_tft_x0", "84.0 mm", M, "TFT U-loop envelope left [v2]"),
    ("loop_tft_x1", "165.9 mm", M, "TFT U-loop envelope right [v2]"),
    ("loop_tft_y1", "146.2 mm", M, "TFT U-loop envelope bottom [v2]"),
    ("tr_x0", "loop_ctp_x0 - loop_clr", M, "tail pocket left at Z_LAND (39.2) [v2]"),
    ("tr_x1", "loop_tft_x1 + loop_clr", M, "tail pocket right at Z_LAND (167.4) [v2]"),
    ("tr_y1", "loop_tft_y1 + trough_R", M, "tail pocket bottom face at Z_LAND (147.70; R1.5 keeps 1.5 to the TFT loop corner)"),
    ("tr_y0", "panel_y1 + ( Z_SEAT - Z_LAND ) * tan(draft)", M,
     "tail-pocket top line at Z_LAND, so the shelf ends flush with the panel bottom edge at Z_SEAT"),
    ("tail_wall_step_y", "129.0 mm", M, "tail-pocket side walls stay at Z_PCB for y < this (at Z_PCB) [v2.1]"),
    # ---- outer wall block, corner cells -------------------------------------------------------------------
    ("outer_x0", "pocket_x0 - wall", M, "outer wall block left at Z_LAND (wall 2.5 outside the pocket)"),
    ("outer_x1", "pocket_x1 + wall", M, "outer wall block right at Z_LAND"),
    ("outer_y0", "pocket_y0 - wall", M, "outer wall block top at Z_LAND"),
    ("outer_y1", "tr_y1 + wall", M, "outer wall block bottom at Z_LAND (bottom beam)"),
    ("cell_r", "2 mm", M, "corner-cell corner radius [v2]"),
    ("crib_y", "139 mm", M, "corner-cell cross rib position, abs y [v2]"),
    # ---- PCB bosses ----------------------------------------------------------------------------------------
    ("boss_od", "8.0 mm", M, "PCB screw boss dia at Z_PCB [v2]"),
    ("pilot_d", "2.4 mm", M, "pilot for ST2.9 / PT K30 at Z_PCB [v2]"),
    ("pilot_floor", "1.0 mm", M, "blind pilot ends this far behind the front face (GF: the land) [v2]"),
    ("cbore_d", "3.2 mm", M, "mouth relief dia [v2]"),
    ("cbore_h", "0.5 mm", M, "mouth relief depth [v2]"),
]
EARS = {"h1": (30.0, 14.2), "h2": (93.0, 14.2), "h3": (174.0, 14.2), "h4": (189.8, 30.0), "h5": (189.8, 109.0),
        "h6": (175.0, 123.8), "h7": (30.0, 123.8), "h8": (15.2, 109.0), "h9": (15.2, 30.0)}
FAST = {1: ("f_x0", "f_y0"), 2: ("f_x1", "f_y0"), 3: ("f_x1", "f_y1"), 4: ("f_x0", "f_y1"),
        5: ("gc_x", "f_y0"), 6: ("f_x1", "gc_y"), 7: ("gc_x", "f_y1"), 8: ("f_x0", "gc_y")}
PIPS = {1: ("glass_x0 + ( glass_x1 - glass_x0 ) / 4", "glass_y0 + pip_in"),
        2: ("glass_x0 + ( glass_x1 - glass_x0 ) / 4", "glass_y1 - pip_in"),
        3: ("glass_x0 + 3 * ( glass_x1 - glass_x0 ) / 4", "glass_y0 + pip_in"),
        4: ("glass_x0 + 3 * ( glass_x1 - glass_x0 ) / 4", "glass_y1 - pip_in"),
        5: ("glass_x0 + pip_in", "glass_y0 + ( glass_y1 - glass_y0 ) / 4"),
        6: ("glass_x1 - pip_in", "glass_y0 + ( glass_y1 - glass_y0 ) / 4"),
        7: ("glass_x0 + pip_in", "glass_y0 + 3 * ( glass_y1 - glass_y0 ) / 4"),
        8: ("glass_x1 - pip_in", "glass_y0 + 3 * ( glass_y1 - glass_y0 ) / 4")}

PLANES = ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_LANDPLATE_BACK",
          "Z_TUBE_TOP", "Z_SEAT", "Z_SHELF_BACK", "Z_PCB"]
REF_PLANES = ["Z_GLASS_FRONT", "Z_GLASS_BACK", "Z_CTP_FRONT", "Z_PANEL_BACK", "Z_FORMEX_FRONT", "Z_SHEET_BACK",
              "Z_FLANGE_FRONT", "Z_LAND"]


def run(_context: str):
    L.check_doc()
    L.log("=== 02 start")
    for name, expr, unit, comment in PARAMS:
        L.set_param(name, expr, unit, comment)
    for h, (x, y) in EARS.items():
        L.set_param(h + "_x", "%.6g mm" % x, M, "PCB ear hole %s x abs (KiCad, NPTH 3.2) [v2]" % h.upper())
        L.set_param(h + "_y", "%.6g mm" % y, M, "PCB ear hole %s y abs (KiCad, y down) [v2]" % h.upper())
    for k, (xe, ye) in FAST.items():
        L.set_param("f%d_x" % k, xe, M, "fastener F%d x abs (master JSON fasteners)" % k)
        L.set_param("f%d_y" % k, ye, M, "fastener F%d y abs (KiCad, y down)" % k)
        r = "sqrt(( gc_x - f%d_x ) ^ 2 + ( gc_y - f%d_y ) ^ 2)" % (k, k)
        L.set_param("f%d_ux" % k, "( gc_x - f%d_x ) / %s" % (k, r), U, "F%d slot axis unit vector x (towards the glass centre)" % k)
        L.set_param("f%d_uy" % k, "( gc_y - f%d_y ) / %s" % (k, r), U, "F%d slot axis unit vector y (abs, y down)" % k)
    for k, (xe, ye) in PIPS.items():
        L.set_param("pip%d_x" % k, xe, M, "stand-off pip P%d x abs (bead centre line, quarter points)" % k)
        L.set_param("pip%d_y" % k, ye, M, "stand-off pip P%d y abs" % k)
    for k, (x0, x1, y0, y1, side) in enumerate(L.RIBS_V1, 1):
        a = x0 if side in "TB" else y0
        L.set_param("rib%d_a" % k, "%.6f mm" % a, M,
                    "PCB support rib %d (%s side): v1 position of its %s edge [v2]" % (k, side, "left" if side in "TB" else "top"))
    for name in PLANES:
        pl = L.offset_plane(name + " plane", name)
        pl.isLightBulbOn = False
    for name in REF_PLANES:
        pl = L.offset_plane("REF " + name, name, L.root())
        pl.isLightBulbOn = False
    chk = {}
    for n in ("Z_FORMEX_FRONT", "Z_PANEL_BACK", "Z_CTP_FRONT", "Z_GLASS_BACK", "Z_GLASS_FRONT", "Z_SHEET_BACK",
              "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP", "Z_LANDPLATE_BACK", "Z_STEPWALL_BACK",
              "Z_TUBE_TOP", "Z_TAIL_TFT_EXIT", "Z_TAIL_CTP_EXIT", "Z_LOOP_FRONT", "snap_keep",
              "glass_x0", "glass_x1", "glass_y0", "gc_x", "gc_y", "fl_x0", "fl_x1", "fl_y0", "fl_y1", "f1_x", "f1_y",
              "f1_ux", "f1_uy", "pocket_x0", "pocket_y1", "tr_y0", "tr_y1", "outer_y1", "trib_d0", "trib_d1",
              "pip1_x", "pip1_y", "pip5_y", "pip7_y", "s_ring_b"):
        chk[n] = round(L.P(n), 5)
    d = L.des()
    L.log("02 params %d, comp planes %d, root planes %d: %s" % (
        d.userParameters.count, L.comp().constructionPlanes.count, L.root().constructionPlanes.count, chk))
    print(d.userParameters.count, json.dumps(chk))
