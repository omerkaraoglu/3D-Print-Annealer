"""Stage 3: master parameter file GF-1.0 -> GF-1.1 (Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json).
Edits only what the GF-1.1 brief (items 1-8 + lead amendment 7.2 x 8.8 + drawings-review corrections) changes, keeps
every existing key name and list structure, adds new entries with the existing {name, value, unit, note} shape and a
top-level "change_log" block. Values measured on the final model are passed in AS_MODELLED (from the stage-3 checks).
Usage: python gf11_params_update.py   (refuses if the file is already GF-1.1)"""
import json
import os
import shutil

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
BACKUP = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\stage1_dumps\params_GF-1.0.json"
AS_MODELLED = json.load(open(r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\gf11\as_modelled.json"))


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def main():
    raw = json.load(open(P, encoding="utf-8"))
    if str(raw.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("already GF-1.1")
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    log = []

    def chg(item, path, old, new, note=""):
        log.append({"item": item, "path": path, "old": old, "new": new, "note": note})

    A = AS_MODELLED
    old_rev = raw["revision"]
    raw["revision"] = ("GF-1.1 (2026-11-15: GF-1.0 + stage-3 batch items 1-8 from the Fusion fit findings F1 / F2 and the "
                       "CadQuery verification; see change_log)")
    chg("-", "revision", old_rev, raw["revision"])
    old_st = raw["status"]
    raw["status"] = "frozen for CAD 2026-11-15, revised GF-1.1 2026-11-15 (stage 3)"
    chg("-", "status", old_st, raw["status"])
    dp = raw["driving_parameters"]
    # item 5: glass corner radius; the frame outlines keep the old radius as R_frame
    e = entry(dp, "R_glass")
    chg(5, "driving_parameters.R_glass.value", e["value"], 6.25, "glass corner only; same glass rectangle")
    e["value"], e["note"] = 6.25, ("glass corner radius (GF-1.1: 6.0 -> 6.25 opens the corner gap g2 to ~0.50; the frame "
                                   "outlines keep R_frame 6.0 + s)")
    dp.append({"name": "R_frame", "value": 6.0, "unit": "mm",
               "note": "GF-1.1: reference radius of the glass-offset FRAME outlines (lip_in R6.4 = R_frame + g2, lip_out "
                       "R7.4, seat ring R8.9) = the GF-1.0 R_glass"})
    chg(5, "driving_parameters.R_frame", None, 6.0, "added")
    dp.append({"name": "R_cut", "value": 7.55, "unit": "mm",
               "note": "GF-1.1: sheet cut-out corner radius (GF-1.0 R_glass + s_cut = 7.8); g1 at the corner ~0.50"})
    chg(5, "driving_parameters.R_cut", None, 7.55, "added")
    dp.append({"name": "tail_side_add", "value": 0.3, "unit": "mm",
               "note": "GF-1.1: tail-pocket side walls moved out by this (x 38.9 / 167.7); tail-wall block and corner "
                       "cells unchanged (tail walls 0.3 thinner)"})
    chg(4, "driving_parameters.tail_side_add", None, 0.3, "added")
    rect = {r["name"]: r for r in raw["plan_rectangles"]}
    chg(5, "plan_rectangles.glass.R", rect["glass"]["R"], 6.25)
    rect["glass"]["R"] = 6.25
    chg(5, "plan_rectangles.cut.R", rect["cut"]["R"], 7.55)
    rect["cut"]["R"] = 7.55
    rect["cut"]["note"] = "SHEET CUT-OUT, laser, +-0.1 (GF-1.1: corner R 7.8 -> 7.55)"
    tp = rect["tail_pocket"]
    chg(4, "plan_rectangles.tail_pocket.x0/x1", [tp["x0"], tp["x1"]], [38.9, 167.7])
    tp["x0"], tp["x1"] = 38.9, 167.7
    tp["note"] = ("tail pocket at the land (GF-1.1: side walls +0.3 each = tr_x0 - 0.3 / tr_x1 + 0.3; bottom face 147.7 "
                  "and R1.5 unchanged)")
    # sheet variants
    sv = raw["sheet_variants"]
    co = entry(sv["common"], "cut_out")
    old = co["note"]
    co["note"] = co["note"].replace("R 7.8", "R 7.55")
    chg(5, "sheet_variants.common.cut_out.note", old, co["note"])
    old = sv["R4"]["value"]
    sv["R4"]["value"] = ("4 holes at F1-F4: dia 5.2 +0.1/0 (dia 4.8 blind rivet, tri-fold / bulb; GESIPA 5.1-5.4); VHB "
                         "strips; heads ~1.0-2.0 proud")
    chg("drawings review", "sheet_variants.R4.value", old, sv["R4"]["value"], "rivet hole 5.2 everywhere")
    # fasteners
    fs = raw["fasteners"]
    hw = fs["hardware"]
    sp = entry(hw, "spacer_S8")
    chg(7, "fasteners.hardware.spacer_S8.value", sp["value"], "DIN 988 6 x 12 x 1.0 shim")
    sp["value"] = ("DIN 988 6 x 12 x 1.0 shim (bore 6.0 passes the 5.3-5.7 weld flange) on the stud between sheet and "
                   "flange at F5-F8")
    st = entry(hw, "stud")
    old = st["note"]
    st["note"] = ("S4: F1-F4; S8: F1-F8. ISO 13918 PT M4 weld flange dia 5.3-5.7 x 0.7-1.4 sits in the fastener "
                  "counterbore (GF-1.1)")
    chg(1, "fasteners.hardware.stud.note", old, st["note"])
    wn = entry(hw, "washer_nut")
    old = wn["note"]
    wn["note"] = ("bearing 80.7 mm2 as modelled (GF-1.1: the washer sits on the dia-12.4 seat inside the coring groove; "
                  ">= 80 required) -> 6.2 MPa at 500 N")
    chg(2, "fasteners.hardware.washer_nut.note", old, wn["note"], "consequence of the tube coring")
    rv = entry(hw, "rivet")
    old = rv["value"]
    rv["value"] = rv["value"].replace("black head; grip", "black head; sheet hole dia 5.2 +0.1/0; grip")
    chg("drawings review", "fasteners.hardware.rivet.value", old, rv["value"])
    fs["counterbore"] = [
        {"name": "cb_w", "value": 7.2, "unit": "mm", "note": "stadium width at the opening (Z_SHEET_BACK), coaxial with "
                                                            "the slot = slot_w + 2 x 0.9 (lead amendment)"},
        {"name": "cb_l", "value": 8.8, "unit": "mm", "note": "stadium length at the opening, along the slot axis = "
                                                            "slot_l + 2 x 0.9"},
        {"name": "cb_floor_F1-F4", "value": 1.6, "unit": "mm",
         "note": "floor above Z_SHEET_BACK in the corner pads (Z -11.82 at glass 3.0): 0.2 over a 1.4 flange"},
        {"name": "cb_floor_F5-F8", "value": 2.0, "unit": "mm",
         "note": "floor above Z_SHEET_BACK at F5-F8 = 1.0 into the flange front (Z -11.42 at glass 3.0): 0.6 over a 1.4 "
                 "flange; 0.6 deep would leave a 0.3 x 1.6 wall strip (sliver) above the floor round"},
        {"name": "cb_r", "value": 0.3, "unit": "mm", "note": "floor edge round"},
        {"name": "cb_draft", "value": 1.0, "unit": "deg", "note": "walls narrowing with depth (opening towards the sheet, "
                                                                 "A half)"},
        {"name": "pad_contact_area_F1-F4", "value": A["pad_contact_area_mm2"], "unit": "mm2",
         "note": "pad hard-stop face left round the counterbore (as modelled), annulus >= %.2f" % A["pad_annulus_min"]}]
    chg("1 + amendment", "fasteners.counterbore", None, "added (7.2 x 8.8, floors 1.6 / 2.0, R0.3, 1 deg)")
    fs["tube_coring"] = [
        {"name": "core_r_in", "value": 6.2, "unit": "mm", "note": "groove inner radius at the tube top (washer seat dia "
                                                                 "12.4)"},
        {"name": "core_r_out", "value": 7.5, "unit": "mm",
         "note": "groove outer radius at the tube top (skin 1.5 to the dia-18 tube; 7.6 would clip the R0.5 tube-top / "
                 "step-wall fillet at glass 4.0)"},
        {"name": "core_depth", "value": 3.3, "unit": "mm", "note": "below Z_TUBE_TOP (floor 2.7 above the pad face at "
                                                                  "glass 3.0, >= 2.0 required)"},
        {"name": "core_floor_r", "value": 0.4, "unit": "mm", "note": "floor rounds (groove 1.185 wide at the floor)"},
        {"name": "core_draft", "value": 1.0, "unit": "deg", "note": "walls, groove widening to the back (B half); the "
                                                                    "cut also runs 1.0 above the tube top"},
        {"name": "max_inscribed_sphere", "value": A["max_sphere_dia"], "unit": "mm",
         "note": "whole frame after GF-1.1, verification toolchain method (voxel 0.2, 3D EDT); limit 5.0"}]
    chg(2, "fasteners.tube_coring", None, "added (r 6.2-7.5, 3.3 deep, R0.4, 1 deg)")
    pt = fs["pad_tube"]
    pt.append({"name": "tube_sw_r", "value": "min(1.2; max(0.5; 0.75 x (Z_STEPWALL_BACK - Z_FLANGE_BACK)))", "unit": "mm",
               "note": "GF-1.1: F5-F8 tube to step-wall blend: 1.2 at glass 3.0 / 4.0, 0.75 at 2.0, 0.5 at 1.1; the "
                       "F5-F8 tube base gets the same radius"})
    chg(6, "fasteners.pad_tube.tube_sw_r", "R0.5", "R1.2 (glass 3.0)")
    # H6 corner cell
    raw["corner_cell_H6"] = [
        {"name": "h6_wall_min", "value": 1.1, "unit": "mm", "note": "tail wall left beside the H6 cell jog at Z_PCB "
                                                                   "(thinnest place)"},
        {"name": "h6_jog_x", "value": A["h6_jog_x"], "unit": "mm", "note": "abs x of the jogged cell wall at the cell "
                                                                          "floor (Z_LANDPLATE_BACK)"},
        {"name": "h6_corner_r", "value": 2.5, "unit": "mm", "note": "cell corner arc at the boss, tangent to the jogged "
                                                                   "wall and the top wall; the boss crosses it at ~58 deg"},
        {"name": "h6_jog_y", "value": 126.6, "unit": "mm", "note": "lower end of the jogged wall (h6_y + 2.8)"},
        {"name": "h6_jog_len", "value": 1.6, "unit": "mm", "note": "slant back to the cell wall (to y 128.2)"},
        {"name": "boss_to_wall_air_min", "value": A["h6_air_min"], "unit": "mm",
         "note": "air between the H6 boss and the jogged wall away from the rounded V where the boss crosses the arc"}]
    chg(3, "corner_cell_H6", "solid fill h6_fill_y (stage 2)", "jogged cell wall + R2.5 corner (coring)")
    # bead, print, gasket
    raw["bead"].append({"name": "bead_area", "value": A["bead_area_mm2"], "unit": "mm2",
                        "note": "as modelled (4.0 band, corners following the GF-1.1 glass R6.25, without the 8 pip "
                                "holes); concept 2510"})
    chg("drawings review", "bead.bead_area", 2510, A["bead_area_mm2"], "as modelled")
    ink = entry(raw["print"], "ink")
    chg("drawings review", "print.ink.value", ink["value"], "2K organic preferred")
    ink["value"] = ("2K organic (epoxy/PU) screen ink preferred over fired ceramic enamel (enamel lowers glass strength "
                    "120 -> about 75 MPa); must pass cross-cut GT0-1 and the silicone / LOCA adhesion coupons")
    fg = entry(raw["tape_and_gasket"], "foam_gasket_S8")
    old = fg["value"]
    fg["value"] = fg["value"].replace("notched round the F5-F8 spacers", "eight pieces between the eight spacers") \
        if "notched round the F5-F8 spacers" in fg["value"] else fg["value"] + "; eight pieces"
    chg("drawings review", "tape_and_gasket.foam_gasket_S8.value", old, fg["value"])
    # item 8: as-designed lip values
    raw["gaps"].append({"name": "g1_at_front_as_designed", "value": 0.4175, "unit": "mm",
                        "note": "GF-1.1 bookkeeping: g1 at the flush plane (lip outer face at the lip top, 1 deg)"})
    dpl = entry(dp, "lip_w")
    dp.append({"name": "lip_w_root_as_designed", "value": 1.0175, "unit": "mm",
               "note": "GF-1.1 bookkeeping: lip width at the root (lip_in defined at the lip top, lip_out at the root, "
                       "both faces 1 deg); lip_w %.1f is the nominal" % dpl["value"]})
    dp.append({"name": "lip_w_top_as_designed", "value": 0.9825, "unit": "mm",
               "note": "GF-1.1 bookkeeping: lip width at the top (sharp-corner extrapolation)"})
    chg(8, "driving_parameters.lip_w_root_as_designed / lip_w_top_as_designed, gaps.g1_at_front_as_designed", None,
        [1.0175, 0.9825, 0.4175], "geometry unchanged")
    raw["cad_rules"] += [
        "GF-1.1: fastener counterbores 7.2 x 8.8 stadium coaxial with each slot, floor 1.6 (F1-F4, pad) / 2.0 (F5-F8) above "
        "Z_SHEET_BACK, R0.3 floor round, 1 deg; the 5.4 x 7.0 slot continues below.",
        "GF-1.1: annular coring groove round every fastener tube from the back, r 6.2-7.5 at the tube top, 3.3 deep, R0.4 "
        "floor rounds, 1 deg; the M4 washer sits on the dia-12.4 seat, the M5 rivet washer bridges the groove.",
        "GF-1.1: H6 corner cell: cell wall jogged to leave the tail wall 1.1 at Z_PCB, R2.5 corner arc into the boss; no "
        "solid fill (thick-section rule: inscribed sphere <= 5.0 everywhere).",
        "GF-1.1: frame outlines are glass-rectangle offsets with corner R_frame + s (R_frame 6.0); the glass corner is "
        "R_glass 6.25 and the sheet cut-out corner R_cut 7.55."]
    raw["as_modelled_GF-1.1"] = {"frame_volume_cm3": A["frame_volume_cm3"], "frame_mass_g_at_1.36": A["frame_mass_g"],
                                 "bead_area_mm2": A["bead_area_mm2"], "max_inscribed_sphere_mm": A["max_sphere_dia"],
                                 "note": "measured on the GF-1.1 Fusion model (document 'Rev3.0 GlassFront'); GF-1.0 "
                                         "model 84.0 cm3 / 114 g"}
    chg("drawings review", "as_modelled_GF-1.1", "84 cm3 / 114 g (GF-1.0 model)",
        "%.2f cm3 / %.1f g" % (A["frame_volume_cm3"], A["frame_mass_g"]))
    raw["change_log"] = {"from": "GF-1.0", "to": "GF-1.1", "date": "2026-11-15",
                         "by": "stage 3 Fusion agent (Design Reports/Rev3.0/tools/glassfront/fusion/gf11_params_update.py)",
                         "changes": log}
    json.dump(raw, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.load(open(P, encoding="utf-8"))
    print("written", P, len(log), "changes")


if __name__ == "__main__":
    main()
