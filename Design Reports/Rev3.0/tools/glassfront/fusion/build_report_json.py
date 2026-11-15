"""Offline: assemble Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json from the dumps that the Fusion
scripts and gf_offline_checks.py wrote into %TEMP%\\rev3_glassfront (docinfo 27, flex 90, scan 20, sections 21 ->
offline thin, above_z0 23 -> offline abovez, carry 22 -> offline carry, dimcheck 24) plus the master JSON.
Usage: python build_report_json.py"""
import json
import math
import os

SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MASTER = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
OUT = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Frame_report.json")
LEVELS = ["Z_TROUGH_TOP", "Z_PCB", "Z_SHELF_BACK", "Z_SEAT", "Z_FORMEX_FRONT", "Z_PANEL_BACK", "Z_CTP_FRONT",
          "Z_GLASS_BACK", "Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP",
          "Z_LANDPLATE_BACK", "Z_STEPWALL_BACK", "Z_TUBE_TOP", "Z_TAIL_TFT_EXIT", "Z_TAIL_CTP_EXIT", "Z_LOOP_FRONT"]


def J(name):
    return json.load(open(os.path.join(SCR, name), encoding="utf-8"))


def main():
    master = json.load(open(MASTER, encoding="utf-8"))
    doc = J("docinfo.json")
    flex = J("flex_final.json")
    scan = J("scan_final.json")
    thin = J("offline_thin.json")
    abz = J("offline_abovez.json")
    carry = J("offline_carry.json")
    cm = J("carry_measure.json")
    dim = J("dimcheck.json")
    pv = {p["name"]: p for p in doc["user_parameters"]}
    k = math.tan(math.radians(1.0))

    # derived levels: Fusion value vs master JSON (3.0 column) + expression
    expr = {e["name"]: e["value"] for e in master["derived_levels"]["expressions"]}
    lv = []
    for n in LEVELS:
        p = pv[n]
        lv.append({"name": n, "fusion_expression": p["expression"], "master_expression": expr.get(n),
                   "fusion_value_mm": p["value"], "master_value_glass_3.0": master["derived_levels"]["evaluated_by_glass_t"]["3.0"][n]})
    extra = [pv[n] for n in ("Z_FLANGE_BACK_RAW", "Z_LANDPLATE_BACK_RAW", "snap_keep", "Z_TRIB_TOP", "Z_CELL_RIB_TOP")]

    # flex table + comparison with the master's evaluated_by_glass_t
    ftab = []
    for r in flex:
        g = r["params"]["glass_t"].replace(" mm", "").replace(" ", "")
        ref = master["derived_levels"]["evaluated_by_glass_t"].get("%.1f" % float(g)) if r["case"].startswith("glass") \
            or r["case"].startswith("default") else None
        dev = None
        if ref:
            dev = max(abs(r["levels"][n] - ref[n]) for n in r["levels"] if n in ref)
        ftab.append({"case": r["case"], "params": r["params"], "timeline_healthy": r["healthy"],
                     "timeline_unhealthy": r["timeline_unhealthy"], "features_failed": len(r["timeline_unhealthy"]),
                     "bodies_in_component": r["bodies_in_component"], "lumps": r.get("lumps"),
                     "volume_cm3": r.get("volume_cm3"), "mass_g": r.get("mass_g_at_1.36"), "faces": r.get("faces"),
                     "bbox_abs": r.get("bbox_abs"), "levels": r["levels"],
                     "max_level_dev_vs_master_table_mm": None if dev is None else round(dev, 6),
                     "unfilleted_concave_roots_by_group": r.get("unfilleted_concave_roots_by_group")})

    # scans
    sl = scan["slivers"]
    by_type = {}
    for s in sl:
        by_type[s["type"]] = by_type.get(s["type"], 0) + 1
    design_slivers = [s for s in sl if s["type"] in ("planar_drafted", "flat_perp_Z", "cone", "planar_UNDRAFTED")]
    scans = {"face_count": doc["body_props"]["faces"], "classification_counts": scan["counts"],
             "draft_flags": scan["flags"], "draft_values_planar_deg": scan["draft_values_planar"],
             "cone_half_angles_deg": scan["cone_half_angles"],
             "sliver_rule": "area < 0.5 mm2 or 2A/P < 0.3 mm",
             "slivers_total": len(sl), "slivers_by_type": by_type,
             "slivers_note": "other_3 = sphere and torus / cylinder = R0.5 fillet blend patches at fillet corners "
                             "(v2 had 57 such patches); design-face slivers listed separately",
             "design_face_slivers": design_slivers,
             "fillet_blend_slivers_max_area_mm2": max(s["area"] for s in sl if s not in design_slivers),
             "thin_strip_scan_lt_1mm": scan["thin_strips_lt_1mm"],
             "thin_strip_note": "all 8 on the lip (lip top flat between the R0.3 rounds and the 0.51 lip outer face "
                                "between R0.3 and the R0.2 root): the 1.0 lip is narrow by design",
             "thin_wall_probe": thin,
             "unfilleted_concave_roots": [r for r in scan["unfilleted_concave_roots"]]}

    carry_out = {
        "method": "v2 STEP (Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2.step) imported into a temporary occurrence of "
                  "this document (script 22), measured, deleted again; plan sections compared offline (XOR areas)",
        "v2_step_volume_cm3": cm["v2_volume_cm3"],
        "bosses_and_pilots": {h: {"xy_abs": v["xy"], "gf_cones": v["gf_cones"], "v2_cones": v["v2_cones"],
                                  "gf_pilot_floor_z": v["gf_pilot_floor_z"], "v2_pilot_floor_z": v["v2_pilot_floor_z"]}
                              for h, v in cm["bosses"].items()},
        "bosses_verdict": "identical: boss dia 8.000 at Z 0 / 1 deg, pilot dia 2.391 at Z -0.5 / 0.5 deg, relief "
                          "dia 3.200 x 0.5 / 0.5 deg at all nine positions; the boss cones end at the land-plate back "
                          "(Z -7.92) instead of the v2 flange back (-8.52); the blind pilots end 1.0 behind the GF "
                          "front face under them (the land, Z -10.42): floor Z -9.42 (v2 -10.02), engaged depth 9.42 "
                          "instead of 10.02",
        "sections_xor": carry["levels"],
        "sections_verdict": "26 support ribs (free spans, Z -1.0 and -3.35): max XOR 0.0009 mm2 = identical; window "
                            "edge (shelf inner edge) identical; pilots identical; tail-pocket side walls above Z 0 "
                            "(Z +2.0, y 129.5..147): XOR 0.40 mm2 per wall over 17.5 mm = the 0.0105 mm shift of the "
                            "1 deg drafted faces whose draft reference moved from v2 Z_FRONT (-11.02) to GF Z_LAND "
                            "(-10.42); x limits at the front face, step at y 129 at Z_PCB and top Z +4.05 unchanged",
        "flat_levels_gf_mm2": cm["flat_levels_gf"], "flat_levels_v2_mm2": cm["flat_levels_v2"],
        "levels_verdict": "Z 0 (PCB back), -0.5 (relief floors), -2.1 (shelf back), -4.6 (shelf front = Formex seat), "
                          "+4.05 (tail walls) present in both",
        "above_Z0_inside_board_outline_plus_1mm": abz,
    }

    sharp = [
        {"corner": "8 pip roots (land / pip, dia 1.5 circles)", "Z": -10.42,
         "where_abs": [[58.48, 13.07], [58.48, 151.1], [149.22, 13.07], [149.22, 151.1], [16.01, 46.1275],
                       [191.69, 46.1275], [16.01, 118.0425], [191.69, 118.0425]],
         "why": "a 0.5 root fillet would consume the 1.5 x 0.5 pip (height tolerance +-0.05 on the top)"},
        {"corner": "4 corner-pad roots (flange front / pad, dia 18 circles round F1-F4)", "Z": -12.42,
         "where_abs": [[2.11, -0.83], [205.59, -0.83], [205.59, 165.0], [2.11, 165.0]],
         "why": "tape strips end tape_margin 1.0 before the pads on a FLAT flange face (master JSON)"},
        {"corner": "seat-ring root (flange front / seat-ring outer face, closed loop = glass + 2.9, R8.9)", "Z": -12.42,
         "where_abs": "x 10.21..197.49, y 7.27..156.90",
         "why": "tape strip inner edge at s 3.9 needs 1.0 flat flange face beyond s 2.9 (tape_margin)"},
        {"corner": "tail-pocket corner left: shelf end face (y 119.0) / tail-pocket side face", "Z": [-4.6, -2.1],
         "where_abs": [39.077, 118.978], "why": "as v2 corner 1 (R0.5 rolls up the tail wall)"},
        {"corner": "tail-pocket corner right", "Z": [-4.6, -2.1], "where_abs": [167.523, 118.978],
         "why": "as v2 corner 2"},
        {"corner": "shelf back / bottom pocket wall, left segment", "Z": -2.1, "where_abs": "y 119.80, x 29.27..39.06",
         "why": "as v2 corner 3 (fillet would roll across the shelf end at the tail pocket)"},
        {"corner": "shelf back / bottom pocket wall, right segment", "Z": -2.1, "where_abs": "y 119.80, x 167.55..175.67",
         "why": "as v2 corner 4"},
        {"corner": "9 pilot floors + 9 relief floors (blind holes)", "Z": [-9.42, -0.5],
         "where_abs": "H1-H9", "why": "as v2 (hole bottoms, formed by the pilot pins)"},
    ]

    deviations = [
        {"item": "lip width reference", "master": "lip_in R6.4 'at the lip top'; lip_w 1.0 'root'; lip_out R7.4",
         "built": "lip_in at the lip top (Z_GLASS_FRONT), lip_out at the lip root (Z_SHEET_BACK), 1 deg on both faces",
         "numbers": "lip root width 1.0175 (not 1.000), lip top width 0.965 (concept 'top 0.97'), flat top 0.39 between "
                    "the R0.3 rounds; g1 to the cut-out 0.400 at the root / 0.417 at the top; g2 0.400 at the lip top, "
                    "0.348 at the glass back (recess narrows 1 deg)",
         "why": "both plan rectangles and lip_w cannot hold at one Z with drafted faces; lip_in and lip_out kept "
                "exactly at the JSON offsets, lip_w is the derived quantity"},
        {"item": "seat-ring / step-wall outer face", "built": "s 2.9 at the flange front (A side, 2.8825 at the ring "
                                                              "top) and s 2.9 at the flange back (B side, step wall back part)",
         "numbers": "ring top width 1.4825 (lip root s 1.4 .. 2.8825)", "why": "draft reference choice, JSON gives no Z"},
        {"item": "level snap", "master": "Z_FLANGE_BACK snapped to Z_STEPWALL_BACK when |dZ| < 0.5",
         "built": "fully automatic expression (snap_keep = min(1; floor(|dZ| / level_snap))), applied to Z_FLANGE_BACK "
                  "and, per the Z_STEPWALL_BACK text ('snap both'), to Z_LANDPLATE_BACK",
         "numbers": "identical to the master table at glass 1.1 / 2.0 / 3.0 / 4.0 (max dev 0.000 mm); no manual step"},
        {"item": "PCB pilot depth", "master": "pilot_floor 1.0 'above Z_FRONT' (v2)",
         "built": "floor 1.0 behind the GF front face under the bosses (the land)", "numbers": "floor Z -9.42 (v2 -10.02)"},
        {"item": "tube ribs F1-F4 (direction and height not in the JSON)",
         "built": "45 deg line from the fastener to the glass corner-arc centre (normal to the step-wall corner), 1.5 "
                  "at the root, from inside the tube (d 8.5) to 0.5 into the step wall (d 15.64); top Z_TRIB_TOP = "
                  "max(min(Z_TUBE_TOP; Z_STEPWALL_BACK); Z_FLANGE_BACK + trib_h_min) (new parameter trib_h_min 1.0)",
         "numbers": "rib height 2.0 at glass 3.0 (tube 2.5), 1.0 at 2.0, 2.5 at 4.0, 1.0 free-ended at 1.1",
         "why": "a rib to the tube top stood 0.5 proud of the step-wall back as a 0.4 mm stub (first build, 07b)"},
        {"item": "F5-F8 tube rib", "master": "'one 1.5 rib to the step wall' per tube",
         "built": "no rib at F5-F8", "numbers": "the dia-18 tube edge is at s 2.0, the step wall reaches s 2.9: the "
                                                 "tube overlaps and merges with the step wall by 0.9 in plan"},
        {"item": "outer wall / corner cells follow the moved pocket", "built": "outer wall 2.5 outside the clearance "
                                                                             "pocket (outer_x0 16.72, v2 17.27); cell top boundary pocket_y1 + wall = 122.30 (v2 121.75)",
         "numbers": "near-sliver and narrow crescent at the H7 / H6 cells (see known_weaknesses)",
         "why": "pocket_clr 0.8 with the v2 construction rules (wall kept 2.5)"},
        {"item": "draft reference of the carried-over walls", "built": "outer wall block, tail-wall block, tail pocket "
                                                                      "and cells referenced at Z_LAND (the GF front face) instead of v2 Z_FRONT",
         "numbers": "their 1 deg faces sit 0.0105 mm further out / in at a given Z (XOR 0.40 mm2 per tail wall above Z 0)"},
        {"item": "pocket lead-in", "built": "v2's 0.8 x 45 deg panel lead-in dropped",
         "why": "the panel hangs from the glass; the clearance pocket is not a locating pocket (concept 4.4)"},
        {"item": "mass", "master": "concept estimate ~70 cm3 / 95 g", "numbers": "built 84.00 cm3 / 114.2 g"},
        {"item": "not modelled (reference parameters only)", "built": "bead, tape strips, sheet cut-out, glass, print "
                                                                      "window, logo zone (stage 2)"},
    ]

    weaknesses = [
        "H7 corner cell: the planar strip of the cell top wall between the H7 boss root fillet and the cell's corner "
        "arc is 0.39 mm at its narrowest (face 2.28 mm2, 2A/P 0.295 < 0.3: one design-face sliver), x 34.59 y 122.22, "
        "Z -7.43..0. Cause: the cell top wall moved 0.55 towards the boss with the clearance pocket (v2 strip ~1.3 "
        "before fillets). Fix options: keep the v2 cell boundary (wall to the pocket 1.95), or round that cell corner "
        "into the boss.",
        "H6 corner cell: crescent of air between the H6 boss and the cell's top-left corner arc (max 1.04 mm wide); "
        "within the R0.5 root-fillet band at the floor the thin-gap probe finds 0.55 x 1.37 mm (Z -7.7); above it >= "
        "1.0. Same crescent existed in v2 (~1.0 mm wide).",
        "Seat-ring and pad roots on the flange front are sharp (tape margin); toolmaker may break them <= 0.2.",
        "Tube ribs are only 1.0 high at glass 2.0 and a free-standing 1.0 rib at 1.1 (the step wall no longer stands "
        "above the flange back there).",
        "Root fillets of the tubes / tube ribs and of the step wall / walls are RULE fillets selected by feature: if "
        "those features are edited so that their faces merge with others, the selection follows the feature faces "
        "(the flex test shows the same unfilleted-root census in every case).",
        "Part mass 114 g, about 20 % above the concept estimate (flange 223.5 x 185.8 x 2.5 dominates).",
    ]

    stage2 = {
        "document": doc["document"], "document_id": doc["dataFile_id"],
        "structure": "root component 'Rev3.0 GlassFront' > occurrence 'Frame GF:1' (component 'Frame GF', one body "
                     "'Frame GF'). Add 'Glass', 'Oven sheet', 'Tape', 'Board' ... as sibling components under the root.",
        "guard": "every script checks attribute gf/doc == 'Rev3.0 GlassFront' (gflib.check_doc)",
        "level_parameters": ["glass_t", "t_opt", "t_bond", "t_sheet", "t_gap", "g_bs", "panel_t", "sheet_t",
                             "Z_GLASS_FRONT", "Z_GLASS_BACK", "Z_CTP_FRONT", "Z_PANEL_BACK", "Z_FORMEX_FRONT",
                             "Z_SEAT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP",
                             "Z_TUBE_TOP", "Z_TAIL_TFT_EXIT", "Z_TAIL_CTP_EXIT", "Z_LOOP_FRONT"],
        "plan_parameters": ["glass_x0", "glass_x1", "glass_y0", "glass_y1", "R_glass", "gc_x", "gc_y", "border",
                            "pw_x0", "pw_x1", "pw_y0", "pw_y1", "pw_r", "aa_x0..aa_y1", "va_x0..va_y1",
                            "panel_x0..panel_y1", "s_lip_in", "s_lip_out", "s_cut", "s_ring", "s_tape_in",
                            "s_tape_out", "tape_w", "tape_margin", "bead_w", "bead_edge", "pip_in", "f1_x..f8_y",
                            "f1_ux..f8_uy", "slot_w", "slot_l", "pad_d", "tube_top_d"],
        "outline_rule": "every glass-related outline = glass rectangle offset by s (expression), corner R_glass + s "
                        "(gflib.grect): glass s 0, lip inner s_lip_in, lip outer s_lip_out, sheet cut-out s_cut, "
                        "seat ring s_ring, tape s_tape_in / s_tape_out",
        "root_planes": ["REF Z_GLASS_FRONT", "REF Z_GLASS_BACK", "REF Z_CTP_FRONT", "REF Z_PANEL_BACK",
                        "REF Z_FORMEX_FRONT", "REF Z_SHEET_BACK", "REF Z_FLANGE_FRONT", "REF Z_LAND"],
        "frame_planes": ["Z_GLASS_FRONT plane", "Z_SHEET_BACK plane", "Z_FLANGE_FRONT plane", "Z_FLANGE_BACK plane",
                         "Z_LAND plane", "Z_LANDPLATE_BACK plane", "Z_TUBE_TOP plane", "Z_SEAT plane",
                         "Z_SHELF_BACK plane", "Z_PCB plane"],
        "reusable_sketches_in_Frame_GF": ["Glass recess sketch (lip_in at the lip top)", "Lip sketch (lip_out at the "
                                          "lip root)", "Seat ring (step wall front) sketch (s_ring)",
                                          "Corner pads F1-F4 sketch", "Fastener slots F1-F8 sketch",
                                          "Pips P1-P8 sketch", "Fastener tubes F1-F8 sketch"],
        "contact_faces": "glass back rests on the bead over the land (Z_LAND) with t_bond; glass front flush with the "
                         "lip top (Z_GLASS_FRONT); sheet back on the seat-ring top and pad tops (Z_SHEET_BACK); tape "
                         "between Z_SHEET_BACK and Z_FLANGE_FRONT; studs through the slots at f1..f8",
    }

    feats = [{"i": it["i"], "name": it["name"], "type": it["type"]} for it in doc["timeline"] if it["type"] != "Sketch"]
    rep = {
        "about": "Rev3.0 GlassFront carrier frame 'Frame GF', native parametric Fusion 360 part, stage 1 (frame only). "
                 "Built by Design Reports/Rev3.0/tools/glassfront/fusion/NN_*.py from the master "
                 "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json (GF-1.0). Units mm / deg; plan "
                 "coordinates abs KiCad (x, y down); model X = x, Y = -y, Z = 0 at the PCB back, -Z to the oven front.",
        "master_revision": master["revision"],
        "document": {k: doc.get(k) for k in ("document", "dataFile_id", "version", "version_note", "project", "folder", "component",
                                          "body", "attribute_guard", "timeline_count")},
        "exports": {"step": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step (component 'Frame GF', 1 solid, "
                            "787 faces, units cm as v2)",
                    "stl": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.stl (binary, high refinement)",
                    "renders": "Mechanical/Rev3.0_GlassFront/renders/Fusion_FrameGF_*.png"},
        "user_parameters": doc["user_parameters"],
        "derived_levels": lv, "derived_helpers": extra,
        "features": feats,
        "body": dict(doc["body_props"], name="Frame GF", material_density_g_cm3=1.36,
                     appearance="Plastic - Matte (Black)"),
        "dimension_check": dim["probes"],
        "flat_face_levels_mm2": dim["flat_face_levels_mm2"],
        "scans": scans,
        "flex_test": ftab,
        "carried_over_check": carry_out,
        "deviations_from_master": deviations,
        "sharp_inside_corners": sharp,
        "known_weaknesses": weaknesses,
        "stage2": stage2,
    }
    json.dump(rep, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(OUT, os.path.getsize(OUT))
    for r in ftab:
        print(r["case"], r["timeline_healthy"], r["features_failed"], r["bodies_in_component"], r["volume_cm3"],
              r["bbox_abs"], r["max_level_dev_vs_master_table_mm"])


if __name__ == "__main__":
    main()
