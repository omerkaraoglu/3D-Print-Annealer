"""Stage 4: master parameter file GF-1.1 -> GF-2.0 (Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json).
Concept (the specification): Design Reports/Rev3.0/tools/glassfront/concept/concept_gf2.md + concept_gf2_params.json;
lead decisions 1-6 of the GF-2.0 brief (border 18.5 on all four sides as ONE driving value, g_bend 3.00, S4 / R4 only
(S8 dropped), divider rib, tail pocket floor = bridge + flange plate, everything else as the concept table).
Never edit the master by hand; this script keeps every existing key name and list structure where the item survives,
removes the chin / S8 / F5-F8 items, adds new entries with the {name, value, unit, note} shape, marks the values
that are no longer valid as 'to be re-verified at GF-2.0' and writes a top-level change_log (the GF-1.1 change_log is
kept inside it under 'previous_revisions').
Do NOT import concept/concept_calc.py (importing it rewrites this file with GF-1.0 values).

Usage (python -B):
  gf20_params_update.py --stage design     first run: GF-1.1 -> GF-2.0 (refuses if the file is not GF-1.1);
                                           backup %TEMP%\\rev3_glassfront\\gf20\\params_GF-1.1.json
  gf20_params_update.py --stage measured   (re)writes 'as_modelled_GF-2.0' and the measured values from the stage-4
                                           check dumps in %TEMP%\\rev3_glassfront\\gf20 (refuses unless GF-2.0)"""
import copy
import json
import math
import os
import shutil
import sys

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
CONCEPT = os.path.join(REPO, "Design Reports", "Rev3.0", "tools", "glassfront", "concept", "concept_gf2_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\gf20"
BACKUP = os.path.join(SCR, "params_GF-1.1.json")
CREF = "Design Reports/Rev3.0/tools/glassfront/concept/concept_gf2.md"
DATE = "2026-11-16"
REV = ("GF-2.0 (2026-11-16: equal 18.5 border on all four sides, FPC tails bent back at the panel edge behind a bridge, "
       "S8 dropped (S4 / R4 only); concept %s; see change_log)" % CREF)
RV = "to be re-verified at GF-2.0"


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def drop(lst, name):
    for i, e in enumerate(lst):
        if e.get("name") == name:
            return lst.pop(i)
    raise KeyError(name)


def design(raw):
    if not str(raw.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("not GF-1.1 - the design stage runs once")
    os.makedirs(SCR, exist_ok=True)
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    con = json.load(open(CONCEPT, encoding="utf-8"))
    log = []

    def chg(item, path, old, new, reason):
        log.append({"item": item, "path": path, "old": old, "new": new, "reason": reason})

    old = raw["revision"]
    raw["revision"] = REV
    chg("-", "revision", old, REV, "new revision")
    old = raw["status"]
    raw["status"] = ("frozen for CAD 2026-11-15 (GF-1.0), GF-1.1 2026-11-15, GF-2.0 2026-11-16 (stage 4 Fusion rebuild, "
                     "document 'Rev3.0 GlassFront'); the 18.5 border and g_bend 3.00 are gated by the real-panel check "
                     "of concept_gf2.md sec. 2.4 (fold both tails over a 3.0 gauge with an R1.5 edge)")
    chg("-", "status", old, raw["status"], "")
    raw["about"] = raw["about"] + (" GF-2.0 (stage 4) edited by Design Reports/Rev3.0/tools/glassfront/fusion/"
                                   "gf20_params_update.py from %s." % CREF)
    old = raw["coordinates"]
    raw["coordinates"] = old.replace("v = 82.085 - y", "v = 66.83 - y")
    chg(6, "coordinates", old, raw["coordinates"], "glass centre moved to the window centre (equal borders)")

    # ------------------------------------------------------------------ driving parameters
    dp = raw["driving_parameters"]
    e = entry(dp, "border")
    chg(1, "driving_parameters.border", e["value"], 18.5, "lead decision 1: equal border on all four sides; smallest "
        "0.5 step that keeps the full GF-1.1 bead 4.0 x 1.0 and its margins at the bottom (concept_gf2.md sec. 3)")
    e["value"] = 18.5
    e["note"] = ("window edge -> glass edge on ALL FOUR sides (GF-2.0; GF-1.1: 14.0 top/left/right + 44.51 chin). The one "
                 "driving value of the glass outline: may be retuned after the real-panel test (concept_gf2.md 2.4); "
                 "18.5 holds while g_bend <= 3.09, else go to 19.0")
    e = drop(dp, "glass_y1")
    chg(1, "driving_parameters.glass_y1", e["value"], None, "removed as a driver: glass_y1 = print_window y1 + border "
        "(127.99), see plan_rectangles.glass")
    new_dp = [
        ("g_bend", 3.0, "mm", "DRIVING (GF-2.0): bend gap = panel bottom edge (y 119.00) -> bridge pocket face over the tail "
         "span = straight 0.5 + R_in 1.5 + tail 0.30 + clearance 0.45 + panel position 0.25 (concept_gf2.md 2.1); "
         "bridge face at y = panel_y1 + g_bend at Z_LAND, 1 deg widening to the back. A double-sided tail (R3.6) would "
         "need 5.1 and border 20.5"),
        ("bend_nose_R", 1.5, "mm", "GF-2.0: round on the bridge back-inner edge (land-plate back x bridge pocket face) >= "
         "tail_R_in_min, so a pulled tail is never bent tighter; leaves 1.0 of flat pocket face above the land"),
        ("land_break", 0.3, "mm", "GF-2.0: 45 deg break on the land front-inner edge (land x bridge pocket face) over the "
         "tail span, so the edge cannot snag a tail when the frame is lowered in J2; the flat land then starts 0.3 "
         "behind the pocket face (bead inner edge 0.79 from the break edge, 1.09 from the face)"),
        ("tail_R_in_min", 1.5, "mm", "GF-2.0 ASSUMPTION (to confirm on a real panel): minimum inner bend radius of both "
         "FPC tails, static (bend to install), >= 5 x 0.30"),
        ("tail_straight_l0", 0.5, "mm", "GF-2.0 ASSUMPTION (to confirm): tail straight beyond the panel edge face before "
         "the first bend"),
        ("tail_t", 0.3, "mm", "GF-2.0: FPC tail thickness used for the route and the fit-check tail solids (estimate, "
         "0.3 +-0.05 ZIF finger)"),
        ("div_x", 79.92, "mm", "GF-2.0: divider rib centre x = middle of the 8.20 gap between the tail exits (CTP x1 75.82, "
         "TFT x0 84.02, measured on DS1); 2.85 clear of each tail edge"),
        ("div_t", 2.5, "mm", "GF-2.0: divider rib thickness at the bridge floor (Z_LANDPLATE_BACK) = wall, 1 deg both sides"),
        ("flange_y1_bottom", 150.235, "mm", "GF-2.0: flange bottom edge abs y AT THE FLANGE FRONT (parting plane) = the "
         "bottom-wall outer face (tr_y1 + wall = 150.20 at Z_LAND, 1 deg) continued to the flange front: flush, one "
         "face; = max(glass_y1 + flange_beyond_glass; outer_y1 + (Z_LAND - Z_FLANGE_FRONT) tan(draft)) (glass + 21 = "
         "148.99 would cut the wall). Concept value 150.20 = the same face at Z_LAND"),
    ]
    for n, v, u, note in new_dp:
        dp.append({"name": n, "value": v, "unit": u, "note": note})
        chg(2 if n in ("g_bend", "bend_nose_R", "land_break") else (4 if n.startswith("div") else 5),
            "driving_parameters." + n, None, v, "added (%s)" % note.split(":")[0])

    # ------------------------------------------------------------------ derived levels
    dl = raw["derived_levels"]
    ex = dl["expressions"]
    e = entry(ex, "Z_LOOP_FRONT")
    e["note"] = ("front-most point of the tails: GF-2.0 only at the exit in the bend gap; the front legs run at "
                 "Z_TAIL_LEG (bent back)")
    ex += [
        {"name": "Z_TAIL_LEG", "value": "Z_TAIL_TFT_EXIT + 2 x (tail_R_in_min + tail_t / 2)", "unit": "mm",
         "note": "GF-2.0: nominal front-leg centre of both tails after the two 90 deg bends (-5.10 at every glass_t; "
                 "reference, no frame feature at it)"},
        {"name": "Z_FLOOR_LOW", "value": "min(Z_FLANGE_BACK, Z_LANDPLATE_BACK - 2 x fillet_root)", "unit": "mm",
         "note": "GF-2.0: floor behind the bridge (tail pocket and H6 / H7 cells beyond the step-wall back) = the flange "
                 "back, but at least 1.0 below the land-plate back so the floor always steps (one topology at every "
                 "glass_t). Differs from Z_FLANGE_BACK only at the level snap (glass 1.1: -8.92, flange 1.6 there "
                 "instead of a flat 2.6 - deviation from 'flat at 1.1' in concept_gf2.md 5.3)"},
        {"name": "Z_WALL_FRONT", "value": "min(Z_LAND, Z_FLANGE_BACK - 0.5)", "unit": "mm",
         "note": "GF-2.0 (CAD construction): front of the outer wall block; = Z_LAND except at glass 4.0, where the walls "
                 "below the board edge must reach the flange plate"},
        {"name": "Z_DISC_FRONT", "value": "Z_FLANGE_FRONT + 0.5", "unit": "mm",
         "note": "GF-2.0 (CAD construction): front of the land plate + step wall solid, inside the full flange plate (no "
                 "geometry change; keeps the parting-plane face a flange face)"},
    ]
    for g, lv in dl["evaluated_by_glass_t"].items():
        gt = float(g)
        lv["Z_TAIL_LEG"] = -5.1
        lv["Z_FLOOR_LOW"] = round(min(lv["Z_FLANGE_BACK"], lv["Z_LANDPLATE_BACK"] - 1.0), 4)
        lv["Z_WALL_FRONT"] = round(min(lv["Z_LAND"], lv["Z_FLANGE_BACK"] - 0.5), 4)
        lv["Z_DISC_FRONT"] = round(lv["Z_FLANGE_FRONT"] + 0.5, 4)
    chg(2, "derived_levels", None, ["Z_TAIL_LEG", "Z_FLOOR_LOW", "Z_WALL_FRONT", "Z_DISC_FRONT"],
        "added (every GF-1.1 level unchanged)")

    # ------------------------------------------------------------------ plan rectangles
    rect = {r["name"]: r for r in raw["plan_rectangles"]}
    newr = {"glass": (8.61, 199.09, 5.67, 127.99), "lip_in": (8.21, 199.49, 5.27, 128.39),
            "lip_out": (7.21, 200.49, 4.27, 129.39), "seat_ring_out": (5.71, 201.99, 2.77, 130.89),
            "cut": (6.81, 200.89, 3.87, 129.79), "tape_in": (4.71, 202.99, 1.77, 131.89),
            "tape_out": (-7.29, 214.99, -10.23, 143.89), "fastener_line": (-2.39, 210.09, -5.33, 138.99),
            "flange": (-12.39, 220.09, -15.33, 150.235)}
    for n, (x0, x1, y0, y1) in newr.items():
        r = rect[n]
        chg(1, "plan_rectangles.%s" % n, [r["x0"], r["x1"], r["y0"], r["y1"]], [x0, x1, y0, y1],
            "border 18.5 on all four sides, same offsets from the glass as GF-1.1" if n != "flange" else
            "glass + 21 top / sides; bottom = flange_y1_bottom (flush with the bottom wall)")
        r["x0"], r["x1"], r["y0"], r["y1"] = x0, x1, y0, y1
    rect["glass"]["note"] = ("glass outline, +-0.1 requested (+-0.2 fallback); 190.48 x 122.32; GF-2.0: y1 = print window y1 "
                             "+ border (derived), equal border 18.5")
    rect["flange"]["note"] = ("flange outline at the flange front (parting line). Top / sides = glass + 21, corner radius "
                              "flange_R centred on F1 / F2; bottom edge y 150.235 = flange_y1_bottom (the bottom wall's "
                              "outer face continued, 150.20 at Z_LAND), bottom corners R10 centred 10 inside the corner "
                              "(1.24 below F3 / F4). 232.48 x 165.57")
    rect["cut"]["note"] = "SHEET CUT-OUT, laser, +-0.1, R 7.55 (+0/-0.2); 194.08 x 125.92 (GF-2.0)"
    tp = rect["tail_pocket"]
    tp["note"] = ("GF-2.0: tail pocket x 38.9 / 167.7 and bottom face 147.7 (R1.5) as GF-1.1, defined at Z_LAND, 1 deg. "
                  "Its front y 119.0 .. bend_y1 122.00 is the BEND-GAP SLOT (open front to back, closed at the front by "
                  "the glass); behind the bridge it has a FLOOR: land-plate back Z_LANDPLATE_BACK (y 122.00 .. 130.89) "
                  "and the flange plate (Z_FLOOR_LOW, y 130.89 .. 147.70); bottom wall y 147.7 .. 150.2 = the frame's "
                  "outer wall, flush with the flange edge")
    chg(5, "plan_rectangles.tail_pocket.note", None, tp["note"], "lead decision 5")
    raw["plan_rectangles"] += [
        {"name": "bend_gap_slot", "x0": 38.9, "x1": 167.7, "y0": 119.0, "y1": 122.0, "R": None, "unit": "mm",
         "note": "GF-2.0: bend-gap slot over the tail span, front face = the old tail-pocket front (y 119.0 at Z_SEAT, "
                 "119.10 at Z_LAND = shelf end), back face = bridge pocket face y 122.00 at Z_LAND (1 deg). Open from the "
                 "land (glass back) to the tail pocket: shut-off between the recess core (A) and the tail-pocket core "
                 "(B) on the 3.0 x 128.8 opening"},
        {"name": "bridge", "x0": 38.9, "x1": 167.7, "y0": 122.0, "y1": 130.89, "R": None, "unit": "mm",
         "note": "GF-2.0: land plate (land y 122.00 .. 128.39 at Z_LAND, back Z_LANDPLATE_BACK) + step wall (128.39 .. "
                 "130.89) + flange plate over the tail span; nose R bend_nose_R on its back-inner edge, land_break 0.3 x "
                 "45 deg on its front-inner edge"},
        {"name": "divider_rib", "x0": 78.67, "x1": 81.17, "y0": 122.0, "y1": 147.7, "R": None, "unit": "mm",
         "note": "GF-2.0: divider rib in the tail pocket, x div_x +- div_t/2 at Z_LANDPLATE_BACK (1 deg both sides), front "
                 "face coplanar with the bridge pocket face, buried 0.5 into the bottom wall; floor (land-plate back / "
                 "flange back) -> Z_PCB in front of the tail-wall step (y 129.0 at Z_PCB), -> Z_TROUGH_TOP behind it; R0.5 "
                 "roots"},
    ]
    chg(4, "plan_rectangles.bend_gap_slot / bridge / divider_rib", None, "added", "lead decisions 2, 4, 5")

    # ------------------------------------------------------------------ plan points, lands
    pp = raw["plan_points"]
    e = entry(pp, "glass_centre")
    chg(6, "plan_points.glass_centre", e["value"], [103.85, 66.83], "equal borders: glass centre = window centre")
    e["value"] = [103.85, 66.83]
    e = drop(pp, "chin_border")
    chg(1, "plan_points.chin_border", e["value"], None, "removed (no chin)")
    e = entry(pp, "borders_top_left_right")
    e["name"], e["value"], e["note"] = "borders_all_four", 18.5, "window edge -> glass edge, all four sides (GF-2.0)"
    chg(1, "plan_points.borders_top_left_right", 14.0, {"borders_all_four": 18.5}, "renamed, all four sides")
    old_lands = copy.deepcopy(raw["lands"])
    raw["lands"] = [
        {"name": "abs left (front-view right)", "value": 10.61, "unit": "mm", "bead_to_pocket": 5.71,
         "note": "land width pocket face -> glass edge (at Z_SEAT; 0.10 less at the land); bead 0.9 .. 4.9 inside the glass edge"},
        {"name": "abs right (front-view left)", "value": 13.37, "unit": "mm", "bead_to_pocket": 8.47,
         "note": "as abs left"},
        {"name": "top", "value": 12.53, "unit": "mm", "bead_to_pocket": 7.63, "note": "as abs left"},
        {"name": "bottom over the tail span (x 38.9 .. 167.7)", "value": 5.99, "unit": "mm", "bead_to_pocket": 1.09,
         "note": "GF-2.0: to the bridge pocket face y 122.00 at Z_LAND (the governing bead_to_pocket, >= bead_pocket_min "
                 "1.0); the land_break 0.3 x 45 deg leaves 5.69 of flat land, bead inner edge 0.79 from the break edge"},
        {"name": "bottom outside the tail span", "value": 8.19, "unit": "mm", "bead_to_pocket": 3.29,
         "note": "GF-2.0: to the clearance-pocket wall y 119.80 (at Z_SEAT)"},
    ]
    chg(1, "lands", old_lands, raw["lands"], "equal border; the side and top land plates grow 4.5")

    # ------------------------------------------------------------------ bead, pips
    bead = raw["bead"]
    e = entry(bead, "bead_area")
    chg(1, "bead.bead_area", e["value"], "measured (see --stage measured)", "smaller glass perimeter")
    e["note"] = "as modelled at GF-2.0 (4.0 band, corners R_glass 6.25 - 0.9 / - 4.9, pip holes NOT subtracted, as GF-1.1)"
    pv = {1: (56.23, 8.57), 2: (56.23, 125.09), 3: (151.47, 8.57), 4: (151.47, 125.09), 5: (11.51, 36.25),
          6: (196.19, 36.25), 7: (11.51, 97.41), 8: (196.19, 97.41)}
    for k, xy in pv.items():
        e = entry(raw["pips"], "pip%d" % k)
        chg(6, "pips.pip%d" % k, e["value"], list(xy), "same rule (bead centre line, +-1/4 of each side)")
        e["value"] = list(xy)
    entry(raw["pips"], "pip2")["note"] += "; GF-2.0: on the 5.99 bottom land over the bridge"
    entry(raw["pips"], "pip4")["note"] += "; GF-2.0: on the 5.99 bottom land over the bridge"

    # ------------------------------------------------------------------ fasteners
    fa = raw["fasteners"]
    old_pos = copy.deepcopy(fa["positions"])
    cf = {f["name"]: f for f in con["fasteners_gf2"]}
    keep = []
    for f in fa["positions"]:
        n = f["name"]
        if n in ("F1", "F2", "F3", "F4"):
            c = cf[n]
            for k in ("x_abs", "y_abs_down", "slot_axis", "slot_axis_deg", "r_from_glass_centre",
                      "d_board_outline_incl_ears", "nearest_ear_hole", "d_ear_hole", "d_J20_J2_wire_corridor",
                      "d_tail_pocket_or_loops", "d_pcb_boss_edge_from_tube", "d_cut_out_edge",
                      "d_tube_edge_to_flange_edge", "front_view_u", "front_view_v"):
                f[k] = c[k] if not isinstance(c[k], float) else round(c[k], 4)
            f["used_by"] = "S4, R4"
            keep.append(f)
    fa["positions"] = keep
    fa["positions_note"] = ("GF-2.0: F1-F4 only (lead decision 3: S8 dropped). Nothing is moulded at F5-F8 (no tube, slot, "
                            "counterbore, coring, blend). d_* values from concept_gf2_params.json fasteners_gf2 (concept "
                            "method); d_cut_out_edge 16.14 measured on the model (81)")
    chg(3, "fasteners.positions", [p["name"] for p in old_pos], ["F1", "F2", "F3", "F4"],
        "S8 dropped; F1-F4 moved with the glass (glass corners + 11), d_* values re-derived (concept 5.2)")
    pt = fa["pad_tube"]
    e = entry(pt, "pad_d")
    e["note"] = "F1-F4 front pad dia, top at Z_SHEET_BACK (hard stop)"
    e = drop(pt, "tube_sw_r")
    chg(3, "fasteners.pad_tube.tube_sw_r", e["value"], None, "removed with the F5-F8 tubes")
    hw = fa["hardware"]
    e = entry(hw, "stud")
    old = e["note"]
    e["value"] = "M4 x 16 CD weld stud ISO 13918 (steel Cu-plated or A2), welded before coating; S4: F1-F4"
    e["note"] = ("S4: F1-F4 (GF-2.0: S8 dropped). ISO 13918 PT M4 weld flange dia 5.3-5.7 x 0.7-1.4 sits in the fastener "
                 "counterbore. After welding, the stud flange INCLUDING weld collar and flash must lie within dia 5.8 x "
                 "1.4 high, and the stud axis must be within +-0.3 of its nominal position relative to the cut-out. "
                 "Measured at GF-2.0 (81, dia 5.8 x 1.4 envelope): see as_modelled_GF-2.0.fasteners")
    chg(3, "fasteners.hardware.stud", old, e["note"], "S8 references removed; values re-measured")
    e = drop(hw, "spacer_S8")
    chg(3, "fasteners.hardware.spacer_S8", e["value"], None, "removed (S8 dropped)")
    cb = fa["counterbore"]
    for n in ("cb_w", "cb_l"):
        e = entry(cb, n)
        e["note"] = e["note"].split("; reference plane")[0] + "; reference plane Z_SHEET_BACK (the pad face, F1-F4)"
    e = drop(cb, "cb_floor_F5-F8")
    chg(3, "fasteners.counterbore.cb_floor_F5-F8", e["value"], None, "removed (no F5-F8)")
    e = drop(cb, "tape_over_opening_F5-F8_S4")
    chg(3, "fasteners.counterbore.tape_over_opening_F5-F8_S4", e["value"], None, "removed (no F5-F8 openings)")
    e = entry(cb, "flange_clearance_extreme_stud")
    old = e["value"]
    e["value"] = {"F1-F4": old["F1-F4"]}
    e["note"] = "GF-1.1 value (weld flange dia 5.7 x 1.4, stud against the slot wall / end); GF-2.0 dia 5.8 x 1.4 values in as_modelled_GF-2.0.fasteners"
    chg(3, "fasteners.counterbore.flange_clearance_extreme_stud.F5-F8", old.get("F5-F8"), None, "removed")
    for e in fa["tube_coring"]:
        if e["name"] == "max_inscribed_sphere":
            e["value"], e["note"] = RV, "GF-2.0: see as_modelled_GF-2.0.max_inscribed_sphere (verification toolchain method)"

    # ------------------------------------------------------------------ logo, tape, sheet variants
    lz = raw["logo_zone"]
    e = entry(lz, "logo_centre")
    chg(6, "logo_zone.logo_centre", e["value"], [103.85, 118.74], "the chin is gone: logo in the 18.5 bottom border")
    e["value"], e["note"] = [103.85, 118.74], "centre of the bottom border (window y1 109.49 .. glass y1 127.99)"
    e = entry(lz, "logo_h")
    chg(6, "logo_zone.logo_h", e["value"], 15.0, ">= 1.0 from the window, >= 2.5 from the glass edge")
    e["value"], e["note"] = 15.0, "max; strokes >= 0.5, >= 1 from the window, >= 2.5 from the glass edge; the bead and the bend gap behind it are hidden by the black layer"
    tg = raw["tape_and_gasket"]
    e = entry(tg, "strip_lengths")
    chg(6, "tape_and_gasket.strip_lengths", e["value"], {"top_bottom": 192.48, "sides": 124.32}, "new glass")
    e["value"] = {"top_bottom": 192.48, "sides": 124.32}
    e["note"] = "strips end 1.0 before the corner pads (measured 1.00 at all 8 ends); area 7603.2 mm2 (GF-1.1 7903)"
    e = drop(tg, "foam_gasket_S8")
    chg(3, "tape_and_gasket.foam_gasket_S8", e["value"], None, "removed (S8 dropped)")
    sv = raw["sheet_variants"]
    e = entry(sv["common"], "cut_out")
    chg(1, "sheet_variants.common.cut_out", e["value"], [6.81, 200.89, 3.87, 129.79], "194.08 x 125.92")
    e["value"] = [6.81, 200.89, 3.87, 129.79]
    old = sv.pop("S8")
    sv["S8_withdrawn"] = {"name": "S8", "value": "WITHDRAWN at GF-2.0 (lead decision 3)", "unit": "-",
                          "note": "the bottom fastener line runs through the tail pocket; every buildable S8 form moves the "
                                  "bottom edge 0.20-0.50 mm at 50 N (concept_gf2.md 4.2 / 5.2). Nothing is moulded at "
                                  "F5-F8; GF-1.1 S8 definition: %s" % old["value"]}
    chg(3, "sheet_variants.S8", old["value"], sv["S8_withdrawn"]["value"], "lead decision 3")
    sv["S4"]["note"] = "recommended (GF-2.0)"
    sv["R4"]["note"] = sv["R4"]["note"] + " (GF-2.0: same numbers, re-measured by script 81)"

    # ------------------------------------------------------------------ gaps, checks, rules
    for g in raw["gaps"]:
        if g["name"] in ("g2_glass_lip", "g1_lip_sheet"):
            g["note"] += "; GF-2.0: the glass is 9.0 wider -> the temperature values are " + RV + " (concept_gf2.md 5.3)"
    ck = raw["checks"]
    old_ck = copy.deepcopy(ck)
    for k in ("push_50N_window_centre_mm", "push_50N_lip_line_max_mm", "impact_0p5J_SF_centre", "impact_0p5J_SF_chin"):
        ck.pop(k, None)
    ck["GF-1.1_values_superseded"] = {k: old_ck[k] for k in ("push_50N_window_centre_mm", "push_50N_lip_line_max_mm",
                                                             "impact_0p5J_SF_centre", "impact_0p5J_SF_chin")}
    ck["push_50N_glass3.0_concept_estimate_mm"] = {"status": RV + " (FEA with the bead; concept grillage only)",
                                                   "S4/R4 channel": con["push_50N_mm_glass_3.0_channel"]["S4/R4: 4 corner studs + VHB"],
                                                   "S4/R4 + divider rib": con["push_50N_mm_glass_3.0_channel"]["S4/R4 + divider rib"]}
    ck["impact_0p5J_SF_concept_estimate"] = {"status": RV, "values": con["impact_SF_0p5J"],
                                             "note": "the chin case is gone; window centre governs (1.21 at 3.0)"}
    ck["fasteners_all_rules_pass"] = "F1-F4: yes (concept 5.2 table); F5-F8 not used"
    chg(6, "checks", "GF-1.1 push / impact values", "moved to checks.GF-1.1_values_superseded; concept estimates added",
        "the bottom edge, glass size and mass change")
    rules = raw["cad_rules"]
    for i, r in enumerate(rules):
        if r.startswith("Tape strips are straight"):
            rules[i] = ("Tape strips are straight (4 pieces) and end tape_margin before the corner pads F1-F4 (GF-2.0: there "
                        "is nothing at F5-F8).")
        elif r.startswith("Fastener slots are stadiums"):
            rules[i] = ("Fastener slots F1-F4 are stadiums slot_w x slot_l at the flange front, 0.5 deg draft (wider to the "
                        "back), long axis = slot_axis (towards the glass centre).")
        elif r.startswith("Tail pocket:"):
            rules[i] = ("GF-2.0: Tail pocket x 38.9 / 167.7, bottom face 147.70 (R1.5): bend-gap slot y 119.0 .. bend_y1 "
                        "open front to back; behind the bridge a floor = land-plate back (to the step-wall back) and the "
                        "flange plate (Z_FLOOR_LOW); bottom wall = outer wall, flush with the flange edge.")
        elif r.startswith("GF-1.1: fastener counterbores"):
            rules[i] = ("GF-1.1: fastener counterbores 7.4 x 9.0 stadium (slot + 1.0 per side) coaxial with each F1-F4 "
                        "slot, floor 1.6 above Z_SHEET_BACK (in the pad), R0.3 floor round, 1 deg; the 5.4 x 7.0 slot "
                        "continues below (GF-2.0: F1-F4 only).")
    rules += [
        "GF-2.0: one driving border (all four sides); glass_y1 = pw_y1 + border; g_bend drives the bridge pocket face "
        "(bend_y1 = panel_y1 + g_bend at Z_LAND); flange bottom = flange_y1_bottom (flush with the bottom wall).",
        "GF-2.0: bridge = land plate + step wall + flange plate over the tail span; nose R bend_nose_R on the land-plate "
        "back x pocket face (B side), land_break 0.3 x 45 deg on the land x pocket face (A side); slot faces 1 deg; the "
        "bend-gap slot is the only through-opening at the bottom (shut-off A/B on its 3.0 x 128.8 outline at Z_LAND).",
        "GF-2.0: divider rib x div_x, div_t 2.5 at the bridge floor, front face coplanar with the bridge pocket face, "
        "floor -> Z_PCB for y < tail_wall_step_y, -> Z_TROUGH_TOP beyond; R0.5 roots.",
        "GF-2.0: floors behind the bridge (tail pocket, H6 / H7 cells beyond the step-wall back) at Z_FLOOR_LOW; the cell "
        "ribs over the flange plate run from Z_FLOOR_LOW to Z_CELL_RIB_TOP; all their roots R0.5 (rule fillet).",
        "GF-2.0: S8 withdrawn - nothing is moulded at F5-F8.",
    ]
    chg(5, "cad_rules", "tail pocket / tape / slots / counterbore rules", "updated + 5 GF-2.0 rules", "GF-2.0 geometry")
    e = entry(raw["corner_cell_H6"], "h6_jog_y")
    e["note"] += "; GF-2.0: plan unchanged; the cell floor steps from the land-plate back to Z_FLOOR_LOW at the step-wall back (y 130.89)"

    # ------------------------------------------------------------------ tail route, invalidated list
    tr = copy.deepcopy(con["tail_route"])
    for t in tr.values():
        t["outline_developed"] = None
    tr["TFT"]["outline_developed"] = [[0.0, 7.0, 84.02, 122.62], [7.0, 31.0, 84.02, 165.90], [31.0, 67.65, 145.40, 165.90]]
    tr["CTP"]["outline_developed"] = [[0.0, 9.5, 40.72, 75.82], [9.5, 34.0, 50.92, 70.62], [34.0, 50.0, 58.27, 61.77]]
    tr["note"] = ("GF-2.0 tail route (concept_gf2.md 2.2), nominal centre lines (abs y, Z), glass-independent; "
                  "outline_developed = [v0, v1, x0, x1] along the developed length v from the panel edge (checked against "
                  "the DS1 tail bodies: x extents at v 0-7 / 7-31 / >31 TFT and 0-9.5 / 9.5-34 / >34 CTP). Swept as the "
                  "fit-check bodies 'TFT / CTP tail GF-2.0 (bent back)' (Fusion script 70)")
    raw["tail_route"] = tr
    raw["to_be_reverified_at_GF-2.0"] = con["gf11_values_invalidated"] + [
        "design document Rev3.0_GlassFront_Design.md sections 0.1, 0.2, 2.1, 2.2, 7.3, 7.4, 7.8, 8.6 (concept_gf2.md 6)",
        "drawings GF-D01..D50 (Mechanical/Rev3.0_GlassFront/drawings are GF-1.1)",
        "the verification toolchain (tools/glassfront/verify) reads the F5-F8 and chin items of the GF-1.1 file"]
    chg(6, "to_be_reverified_at_GF-2.0", None, "added", "concept_gf2.md 6 'GF-1.1 values that become invalid'")

    prev = raw.pop("change_log")
    raw["change_log"] = {"from": "GF-1.1", "to": "GF-2.0", "date": DATE,
                         "by": "stage 4 Fusion agent (Design Reports/Rev3.0/tools/glassfront/fusion/gf20_params_update.py)",
                         "concept": CREF,
                         "lead_decisions": {"1": "border 18.5 on all four sides, one driving parameter (glass_y1 derived)",
                                            "2": "g_bend 3.00, nose R1.5, 0.3 break over the tail span",
                                            "3": "S4 and R4 only; S8 dropped, nothing moulded at F5-F8",
                                            "4": "divider rib x 79.92, 2.5, y 122-147.7",
                                            "5": "tail pocket floor = bridge + flange plate; bottom wall = outer wall",
                                            "6": "everything else as the concept table"},
                         "changes": log, "previous_revisions": {"GF-1.1": prev}}
    return raw


def measured(raw):
    if not str(raw.get("revision", "")).startswith("GF-2.0"):
        raise SystemExit("run --stage design first")
    J = lambda n: json.load(open(os.path.join(SCR, n), encoding="utf-8")) if os.path.exists(os.path.join(SCR, n)) else None
    fr = J("as_modelled_frame.json")
    fp = J("fit_parts.json")
    ft = J("fit_tails.json")
    fx = J("fasteners.json")
    th = J("thickness_final/thickness_check.json") or J("thickness/thickness_check.json")
    ex = J("export.json")
    fl = J("flex_final.json")
    am = {"source": "Fusion document 'Rev3.0 GlassFront' version 18 (GF-2.0), stage-4 scripts 71, 78-84 and "
                    "gf20_thickness_check.py on the exported frame STEP; dumps in %TEMP%\\rev3_glassfront\\gf20"}
    if ex:
        import hashlib
        fp_ = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Frame.step")
        am["frame_step"] = dict(ex["files"]["Rev3.0_GlassFront_Frame.step"],
                                sha256=hashlib.sha256(open(fp_, "rb").read()).hexdigest())
    if fl:
        am["flex_test"] = [{"case": r["case"], "healthy": r["healthy"], "bodies": r["bodies_in_component"],
                            "lumps": r["lumps"], "volume_cm3": r["volume_cm3"], "faces": r["faces"]} for r in fl]
    if fr:
        f = fr["frame"]
        am.update({"frame_volume_cm3": f["volume_cm3"], "frame_mass_g_at_1.36": f["mass_g_at_1.36"], "faces": f["faces"],
                   "edges": f["edges"], "bodies": 1, "lumps": f["lumps"], "bbox_abs": f["bbox_abs"],
                   "pad_hard_stop_faces_mm2": fr["pad_hard_stop_faces_mm2"]})
    if fp:
        band = None
        for a in fp["bead"]["faces_at_Z_LAND_mm2"]:
            band = a
        holes = 8 * math.pi * (1.5 / 2) ** 2
        am["bead_area_mm2"] = {"band_without_subtracting_pips (GF-1.1 convention)": round(band + holes, 1),
                               "face_as_modelled_with_8_pip_holes": band}
        am["tape_area_mm2"] = fp["tape"]["total_area_mm2"]
        am["g2_sides_corners_mm (0.5 below the flush plane / glass back)"] = {
            "sides": [fp["g2_glass_edge_to_lip"]["gaps"]["left"][k] for k in sorted(fp["g2_glass_edge_to_lip"]["gaps"]["left"])],
            "corners": [fp["g2_glass_edge_to_lip"]["gaps"]["corner top-left"][k]
                        for k in sorted(fp["g2_glass_edge_to_lip"]["gaps"]["corner top-left"])]}
        am["g1_sides_corners_mm"] = {
            "sides": [fp["g1_cutout_to_lip"]["gaps"]["left"][k] for k in sorted(fp["g1_cutout_to_lip"]["gaps"]["left"])],
            "corners": [fp["g1_cutout_to_lip"]["gaps"]["corner top-left"][k]
                        for k in sorted(fp["g1_cutout_to_lip"]["gaps"]["corner top-left"])]}
        am["pip_top_to_glass_mm"] = sorted({q["to_glass_mm"] for q in fp["pips"]})
    if ft:
        am["tail_clearances_mm"] = {nm: {"frame_min": e["frame_overall"]["d_mm"],
                                         "frame_by_class": {k: v["d_mm"] for k, v in e["frame_by_class"].items()},
                                         "frame_min_panel_edge_+0.35": e["frame_overall_panel_edge_+0.35"],
                                         "frame_min_panel_edge_-0.35": e["frame_overall_panel_edge_-0.35"],
                                         "glass_print": e["parts"]["glass print"]["d_mm"],
                                         "glass": e["parts"]["glass"]["d_mm"], "bead": e["parts"]["bead"]["d_mm"],
                                         "optical_bond": e["parts"]["optical bond"]["d_mm"],
                                         "Formex": e["parts"]["Formex sheet"]["d_mm"],
                                         "PCB": next((q["d_mm"] for q in e["board_bodies_within_6"]
                                                      if "PCB" in q["path"]), None)}
                                    for nm, e in ft["tails"].items()}
    if fx:
        am["fasteners"] = fx["summary"]
    if th:
        am["max_inscribed_sphere_mm"] = th["max_sphere_dia"]
        am["thick_spots_over_5.0"] = len(th["spots_over_5.0"])
        am["thickest_spots"] = th["top5"]
        am["thin_walls_lt_1.2"] = [{"plane": w.get("plane"), "width_max": w.get("width_max"), "at": w.get("at"),
                                    "length": w.get("length")} for w in th.get("thin", {}).get("thin_walls", [])]
        am["thin_walls_note"] = ("< 1.2 only the 1.0 lip (ring) and the H6 tail wall 1.1 at Z_PCB (GF-1.1 h6_wall_min), "
                                 "both by design; nothing new at GF-2.0 (extra probes Z -9.0 / -8.3, x 79.92 / 60, y 138)")
    raw["as_modelled_GF-2.0"] = am
    e = entry(raw["bead"], "bead_area")
    if fp:
        e["value"] = am["bead_area_mm2"]["band_without_subtracting_pips (GF-1.1 convention)"]
    for e in raw["fasteners"]["tube_coring"]:
        if e["name"] == "max_inscribed_sphere" and th:
            e["value"] = th["max_sphere_dia"]
            e["note"] = "whole frame at GF-2.0, verification toolchain method (voxel 0.2, 3D EDT); limit 5.0"
    for e in raw["fasteners"]["counterbore"]:
        if e["name"] == "pad_contact_area_F1-F4" and fr:
            e["value"] = fr["pad_hard_stop_faces_mm2"]["F1"]
            e["note"] = "pad hard-stop face round the counterbore, as modelled at GF-2.0 (same as GF-1.1)"
    raw["change_log"]["measured_values"] = {"date": DATE, "written_by": "gf20_params_update.py --stage measured",
                                            "paths": ["as_modelled_GF-2.0", "bead.bead_area",
                                                      "fasteners.tube_coring.max_inscribed_sphere",
                                                      "fasteners.counterbore.pad_contact_area_F1-F4"]}
    return raw


def main():
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else None
    raw = json.load(open(P, encoding="utf-8"))
    if stage == "design":
        raw = design(raw)
    elif stage == "measured":
        raw = measured(raw)
    else:
        raise SystemExit(__doc__)
    tmp = P + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=1, ensure_ascii=False)
        f.write("\n")
    json.load(open(tmp, encoding="utf-8"))
    os.replace(tmp, P)
    print("written", P, "stage", stage)


if __name__ == "__main__":
    main()
