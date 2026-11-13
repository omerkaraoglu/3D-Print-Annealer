"""01 - new Fusion design document for the Rev3.0 carrier frame v2, mm units, ALL user parameters,
construction planes at the Z levels.

Expects: nothing (creates a new document, which becomes the active one; no other document is touched).
Leaves: an empty parametric design tagged fv2/doc = 'Rev3.0 Frame v2', user parameters, planes.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

# (name, expression, unit, comment) - order matters (derived after their sources)
PARAMS = [
    # moulding rules
    ("wall", "2.5 mm", "mm", "nominal wall, PA6-GF30 (v1 frame.py WALL)"),
    ("rib", "1.5 mm", "mm", "rib thickness at the root = 0.6 x wall (v1 RIB_T)"),
    ("draft", "1 deg", "deg", "draft on every face along the pull Z (v1 DRAFT)"),
    ("draft_loc", "0.5 deg", "deg", "draft of the panel locating faces, pegs, pilot and stud holes (v1 DRAFT_LOC)"),
    ("fillet_root", "0.5 mm", "mm", "root fillets at bosses, ribs, wall/flange and wall/shelf (v1 FILLET_IN)"),
    ("frame_r", "5 mm", "mm", "outer body corner radius (v1 FRAME_R)"),
    # Z stack
    ("standoff", "5.0 mm", "mm", "PCB back -> panel back (v1 STANDOFF, panel model)"),
    ("sheet_t", "0.4 mm", "mm", "Formex insulating sheet (v1 SHEET_T)"),
    ("panel_t", "5.32 mm", "mm", "SAT070AT40D21 LCM 3.34 + CTP 1.98 (v1 PANEL_T)"),
    ("gasket_t", "1.0 mm", "mm", "closed-cell silicone sponge gasket, free (v1 GASKET_T)"),
    ("gasket_comp", "0.30", "", "gasket design compression fraction (v1 GASKET_COMP)"),
    ("oven_sheet_t", "1.0 mm", "mm", "steel oven front sheet 1.0..1.5 (v1 OVEN_SHEET_T)"),
    ("shelf_t", "wall", "mm", "shelf (panel seat) thickness = wall (v1 SHELF_T)"),
    ("Z_PCB", "0 mm", "mm", "physical PCB back face = boss / rib / wall tops"),
    ("Z_PANEL_BACK", "-standoff", "mm", "panel back face"),
    ("Z_SEAT", "Z_PANEL_BACK + sheet_t", "mm", "shelf front face (sheet on it, panel on the sheet)"),
    ("Z_SHELF_BACK", "Z_SEAT + shelf_t", "mm", "shelf back face"),
    ("Z_GLASS", "Z_PANEL_BACK - panel_t", "mm", "cover glass front"),
    ("Z_FRONT", "Z_GLASS - gasket_t * ( 1 - gasket_comp )", "mm",
     "flange front face = inner face of the oven sheet = parting plane"),
    ("loop_z_top", "2.55 mm", "mm", "top of the FPC U-loop return legs (panel model, v1 LOOP_Z[1])"),
    ("loop_z_bot", "-9.06 mm", "mm", "bottom of the FPC loops (panel model, v1 LOOP_Z[0])"),
    ("loop_clr", "1.5 mm", "mm", "clearance round the loop envelopes (v1 LOOP_CLR)"),
    ("Z_TROUGH_TOP", "loop_z_top + loop_clr", "mm", "top of the tail-pocket walls (outside the board only)"),
    # panel / pocket / shelf (abs KiCad x, y-down)
    ("panel_x0", "20.02 mm", "mm", "panel outline left (DS1 Dwgs.User)"),
    ("panel_x1", "184.92 mm", "mm", "panel outline right"),
    ("panel_y0", "19.00 mm", "mm", "panel outline top (abs y, down)"),
    ("panel_y1", "119.00 mm", "mm", "panel outline bottom"),
    ("va_x0", "26.31 mm", "mm", "cover view area left (SAT drawing)"),
    ("va_x1", "181.39 mm", "mm", "cover view area right"),
    ("va_y0", "23.23 mm", "mm", "cover view area top"),
    ("va_y1", "110.15 mm", "mm", "cover view area bottom"),
    ("pocket_clr", "0.25 mm", "mm", "panel to pocket wall per side (v1 POCKET_CLR)"),
    ("leadin", "0.8 mm", "mm", "45 deg lead-in at the pocket mouth (v1 LEADIN)"),
    ("seat_w", "2.6 mm", "mm", "shelf reach inside the panel outline (v1 SEAT_W; F3 leads >= 1 mm)"),
    ("pcb_rim_w", "2.1 mm", "mm", "PCB support ribs reach this far inside the panel outline (v1 PCB_RIM_W)"),
    ("rib_bury", "0.5 mm", "mm", "v2: support/cell/stud ribs run this far into the wall they meet (drafted end buried)"),
    ("pocket_x0", "panel_x0 - pocket_clr", "mm", "panel pocket left at Z_SEAT"),
    ("pocket_x1", "panel_x1 + pocket_clr", "mm", "panel pocket right at Z_SEAT"),
    ("pocket_y0", "panel_y0 - pocket_clr", "mm", "panel pocket top at Z_SEAT"),
    ("pocket_y1", "panel_y1 + pocket_clr", "mm", "panel pocket bottom at Z_SEAT"),
    ("pocket_r", "0.5 mm", "mm", "pocket corner radius (v1)"),
    ("win_x0", "panel_x0 + seat_w", "mm", "window inside the shelf, left, at Z_SEAT"),
    ("win_x1", "panel_x1 - seat_w", "mm", "window right"),
    ("win_y0", "panel_y0 + seat_w", "mm", "window top"),
    ("win_y1", "panel_y1 - seat_w", "mm", "window bottom"),
    ("win_r", "1 mm", "mm", "window corner radius (v1)"),
    # tail pocket
    ("loop_ctp_x0", "40.7 mm", "mm", "CTP U-loop envelope left (panel model)"),
    ("loop_ctp_x1", "75.8 mm", "mm", "CTP U-loop envelope right"),
    ("loop_ctp_y1", "137.4 mm", "mm", "CTP U-loop envelope bottom (abs y)"),
    ("loop_tft_x0", "84.0 mm", "mm", "TFT U-loop envelope left"),
    ("loop_tft_x1", "165.9 mm", "mm", "TFT U-loop envelope right"),
    ("loop_tft_y1", "146.2 mm", "mm", "TFT U-loop envelope bottom (abs y)"),
    ("trough_r", "5.0 mm", "mm", "tail-pocket bottom inner corner radius (v1 TROUGH_R)"),
    ("tr_x0", "loop_ctp_x0 - loop_clr", "mm", "tail pocket left at Z_FRONT"),
    ("tr_x1", "loop_tft_x1 + loop_clr", "mm", "tail pocket right at Z_FRONT"),
    ("tr_y1", "loop_tft_y1 + trough_r", "mm", "tail pocket bottom at Z_FRONT (R5 keeps >= 1.5 to the loop corner)"),
    ("tr_y0", "panel_y1 + ( Z_SEAT - Z_FRONT ) * tan(draft)", "mm",
     "tail-pocket cut top line at Z_FRONT, so the shelf ends flush with the panel bottom edge at Z_SEAT"),
    # outer body, cells
    ("outer_x0", "pocket_x0 - wall", "mm", "outer body left at Z_FRONT (v1 OUTER)"),
    ("outer_x1", "pocket_x1 + wall", "mm", "outer body right at Z_FRONT"),
    ("outer_y0", "pocket_y0 - wall", "mm", "outer body top at Z_FRONT"),
    ("outer_y1", "tr_y1 + wall", "mm", "outer body bottom at Z_FRONT (bottom beam)"),
    ("cell_r", "2 mm", "mm", "corner-cell corner radius (v1)"),
    ("cell_rib_h", "5 mm", "mm", "corner-cell rib top above Z_FRONT (brief)"),
    ("crib_y", "139 mm", "mm", "corner-cell cross rib position, abs y (v1 foot row F6/F7)"),
    # PCB bosses
    ("boss_od", "8.0 mm", "mm", "PCB screw boss dia at Z_PCB (v1 BOSS_OD)"),
    ("pilot_d", "2.4 mm", "mm", "pilot for ST2.9 / PT K30 at Z_PCB (v1 PILOT_D)"),
    ("pilot_floor", "1.0 mm", "mm", "v2: blind pilot ends this far above Z_FRONT (closed front face)"),
    ("cbore_d", "3.2 mm", "mm", "mouth relief dia (v1 CBORE_D)"),
    ("cbore_h", "0.5 mm", "mm", "mouth relief depth (v1 CBORE_H)"),
    # flange + studs
    ("flange_w", "14 mm", "mm", "flange width outside the body (top, right, bottom)"),
    ("flange_w_l", "15 mm", "mm", "flange width on the LEFT side (v2 deviation, see stud_offset_l)"),
    ("flange_t", "2.5 mm", "mm", "flange thickness (front face = parting/sealing plane)"),
    ("flange_r", "12 mm", "mm", "flange outer corner radius"),
    ("stud_hole", "4.5 mm", "mm", "M4 stud clearance hole, dia at Z_FRONT (narrowest), 0.5 deg draft wider at the back"),
    ("stud_boss_od", "10 mm", "mm", "stud tube OD at its top (nut/washer seat)"),
    ("stud_boss_h", "5 mm", "mm", "stud tube top above Z_FRONT"),
    ("stud_offset", "7.5 mm", "mm", "stud hole centre outside the wall outer face at Z_FRONT (top, right, bottom)"),
    ("stud_offset_l", "8.5 mm", "mm",
     "LEFT side: board edge is at x 20.0, 7.5 would put the holes 10.23 from the PCB outline (< 11.0 rule)"),
    ("Z_FLANGE_BACK", "Z_FRONT + flange_t", "mm", "flange back face"),
    ("Z_STUD_TOP", "Z_FRONT + stud_boss_h", "mm", "stud tube top = DIN 9021 washer seat"),
    ("Z_CELL_FLOOR", "Z_FRONT + wall", "mm", "corner-cell floor back face"),
    ("Z_CELL_RIB_TOP", "Z_FRONT + cell_rib_h", "mm", "corner-cell rib tops"),
    ("fl_x0", "outer_x0 - flange_w_l", "mm", "flange outline left at Z_FRONT"),
    ("fl_x1", "outer_x1 + flange_w", "mm", "flange outline right"),
    ("fl_y0", "outer_y0 - flange_w", "mm", "flange outline top"),
    ("fl_y1", "outer_y1 + flange_w", "mm", "flange outline bottom"),
    ("stud_xl", "outer_x0 - stud_offset_l", "mm", "left stud line x"),
    ("stud_xr", "outer_x1 + stud_offset", "mm", "right stud line x"),
    ("stud_yt", "outer_y0 - stud_offset", "mm", "top stud line y (abs)"),
    ("stud_yb", "outer_y1 + stud_offset", "mm", "bottom stud line y (abs)"),
    # pegs
    ("pegs_on", "1", "", "1 = locating pegs present; 0 = suppress feature 'Pegs P1 P2' (Fusion cannot link suppression)"),
    ("peg_d", "3 mm", "mm", "locating peg dia at the floor (v1 PEG_D)"),
    ("peg_h", "0.8 mm", "mm", "locating peg height (< oven sheet) (v1 PEG_H)"),
    ("peg1_x", "32.5 mm", "mm", "peg P1 x abs (v1 PEG_POS)"),
    ("peg1_y", "146.0 mm", "mm", "peg P1 y abs"),
    ("peg2_x", "172.5 mm", "mm", "peg P2 x abs"),
    ("peg2_y", "146.0 mm", "mm", "peg P2 y abs"),
]
EARS = {"h1": (30.0, 14.2), "h2": (93.0, 14.2), "h3": (174.0, 14.2), "h4": (189.8, 30.0), "h5": (189.8, 109.0),
        "h6": (175.0, 123.8), "h7": (30.0, 123.8), "h8": (15.2, 109.0), "h9": (15.2, 30.0)}

PLANES = [("Z_FRONT plane", "Z_FRONT"), ("Z_FLANGE_BACK plane", "Z_FLANGE_BACK"), ("Z_CELL_FLOOR plane", "Z_CELL_FLOOR"),
          ("Z_STUD_TOP plane", "Z_STUD_TOP"), ("Z_CELL_RIB_TOP plane", "Z_CELL_RIB_TOP"), ("Z_SEAT plane", "Z_SEAT"),
          ("Z_SHELF_BACK plane", "Z_SHELF_BACK"), ("Z_PCB plane", "Z_PCB"), ("Z_TROUGH_TOP plane", "Z_TROUGH_TOP")]


def run(_context: str):
    app = adsk.core.Application.get()
    L.log("=== 01 start; open docs before: %s" % [app.documents.item(i).name for i in range(app.documents.count)])
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    des = adsk.fusion.Design.cast(app.activeProduct)
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType
    des.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    L.mark_doc("Rev3.0 Frame v2")
    L.check_doc()
    for name, expr, unit, comment in PARAMS:
        L.set_param(name, expr, unit, comment)
    for h, (x, y) in EARS.items():
        L.set_param(h + "_x", "%.6f mm" % x, "mm", "PCB ear hole %s x abs (KiCad, NPTH dia 3.2)" % h.upper())
        L.set_param(h + "_y", "%.6f mm" % y, "mm", "PCB ear hole %s y abs (KiCad, y down)" % h.upper())
    for name, expr in PLANES:
        pl = L.offset_plane(name, expr)
        pl.isLightBulbOn = False
    # checks
    msg = []
    for n in ("Z_FRONT", "Z_SEAT", "Z_SHELF_BACK", "Z_GLASS", "Z_TROUGH_TOP", "tr_y0", "outer_x0", "outer_x1",
              "outer_y0", "outer_y1", "fl_x0", "fl_x1", "fl_y0", "fl_y1", "stud_xl", "stud_xr", "stud_yt", "stud_yb"):
        msg.append("%s=%.4f" % (n, L.P(n)))
    L.log("01 params: " + ", ".join(msg))
    L.log("01 doc '%s' active=%s, params %d, planes %d" % (
        app.activeDocument.name, app.activeDocument == doc, des.userParameters.count,
        des.rootComponent.constructionPlanes.count))
    print("\n".join(msg))
