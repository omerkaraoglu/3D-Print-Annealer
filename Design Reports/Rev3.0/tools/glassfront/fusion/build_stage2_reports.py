"""Offline (stage 2): write
  Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json     (stage-1 report updated for Part A)
  Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Assembly_report.json  (Parts B-D)
from the dumps in %TEMP%\\rev3_glassfront (stage-1 originals kept in stage1_dumps\\). Usage: python build_stage2_reports.py"""
import json
import math
import os

SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
FR_OUT = os.path.join(MECH, "Rev3.0_GlassFront_Frame_report.json")
AS_OUT = os.path.join(MECH, "Rev3.0_GlassFront_Assembly_report.json")


def J(n):
    return json.load(open(os.path.join(SCR, n), encoding="utf-8"))


def r4(v):
    return None if v is None else round(v, 4)


def frame_report():
    rep = J(r"stage1_dumps\Frame_report_stage1.json")
    doc = J("docinfo_asm.json")
    scan = J("scan_partA.json")
    thin = J("offline_thin.json")
    flex = J("flex_partA.json")
    fsl = J("flex_slivers_partA.json")
    abz = J("offline_abovez.json")
    pv = {p["name"]: p for p in doc["user_parameters"]}
    rep["about"] = rep["about"].replace("stage 1 (frame only)", "stage 1 (frame) + stage 2 Part A (cell-corner fix)")
    rep["document"].update({"version": doc["version"], "version_note": "frame last changed in v5 (stage 2 Part A); "
                            "v6-v9 add the assembly components (frame unchanged)", "timeline_count_frame_items": 77,
                            "timeline_count_document": doc["timeline_count"]})
    rep["exports"]["step"] = ("Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step (component 'Frame GF', 1 solid, "
                              "787 faces; RE-EXPORTED 2026-11-15 14:21 after Part A, unchanged since)")
    rep["exports"]["stl"] = "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.stl (binary, high refinement; re-exported 14:21)"
    rep["exports"]["renders"] = ("Mechanical/Rev3.0_GlassFront/renders/Fusion_FrameGF_*.png (regenerated after Part A by "
                                 "45_frame_renders_refresh.py = 26 with every other component hidden)")
    names = [p["name"] for p in rep["user_parameters"]]
    for n in ("cell_r_h7", "h6_fill_y"):
        if n not in names:
            rep["user_parameters"].append(pv[n])
    b = scan["body"]
    rep["body"].update({k: b[k] for k in ("volume_cm3", "mass_g_at_1.36", "faces", "edges", "lumps", "shells", "is_solid",
                                          "bbox_abs")})
    rep["stage2_partA"] = {
        "defects (stage 1 known weaknesses 1, 2)": [
            "H7 cell: flat strip of the cell top wall 0.39 wide between the boss root fillet and the R2 corner arc "
            "(face 2.28 mm2, 2A/P 0.295)",
            "H6 cell: crescent of air 1.0 wide between the boss and the cell's left (tail) wall, 0.55 x 1.37 in the "
            "root-fillet band at Z -7.7 (a thin steel blade in the B core)"],
        "cause": "cell top wall at pocket_y1 + wall = 122.30 (v2 121.75): moved 0.55 towards the H6 / H7 bosses",
        "fix_H7": "the cell corner at the boss gets its own radius cell_r_h7 = 1.0 mm (was cell_r 2.0): radial dimension of "
                  "that one arc in 'Corner cells sketch'; the boss now meets a full top wall: flat beyond the boss root "
                  "fillet 1.16 (floor) .. 1.32 (Z 0) wide, face 9.71 mm2, 2A/P 1.111; boss to tail wall 2.6 stays a slot "
                  "(1.6 inside the fillet band). Filling it was rejected: 8 mm solid pilot -> tail pocket.",
        "fix_H6": "the R2 cell corner (cell_r) is moved down the left wall and blended into the boss: arc tangent to the "
                  "cell's left wall, centre (XL + cell_r, h6_fill_y), crossing the boss at 90 deg on the cell floor "
                  "(circle orthogonal to the boss circle: h6_fill_y = h6_y + sqrt(cell_r^2 + r_boss_floor^2 - "
                  "(h6_x - XL - cell_r)^2) = 127.153 at default, 127.168 at t_opt 1.0); a vertical line x = XL + cell_r "
                  "inside the boss closes the profile. Done in the 'Corner cells sketch' (same profile, same 1 deg "
                  "taper, so the arc stays tangent to the wall at every Z). The crescent becomes solid: the boss merges "
                  "into the tail wall; largest inscribed circle there ~5.4 (pilot -> tail pocket 6.4); for comparison "
                  "the fastener tube + flange is 5.0 solid.",
        "unchanged": "bosses, pilots, reliefs, cell ribs, support ribs, pockets, window, tail pocket: 22 carry-over check "
                     "re-run, all 123 comparison regions identical to stage 1 (XOR differences 0.0000), boss / pilot / relief "
                     "cones identical at H1-H9",
        "new_parameters": [pv["cell_r_h7"], pv["h6_fill_y"]],
        "timeline": "77 frame items as before: 'Corner cells sketch' edited (H7 radius dim; H6 arc deleted, new arc + "
                    "vertical line + 2 dims), 'Root fillets R0.5 - corner cells + cell ribs + cell bosses' deleted and "
                    "re-created at the same position from gflib.EDGE_SETS (79 edges, as stage 1)",
        "rule_fillets": "unchanged selection: 'wall + step wall to plates (rule)' 45 faces and 'fastener tubes + tube ribs "
                        "(rule)' 72 faces in the default and the 5 thick-glass / sheet / t_opt flex cases, 29 / 40 at glass 1.1 "
                        "(snap, same as stage 1's topology); none of their faces lies at the changed cell corners",
        "scans_after_fix": {
            "draft_flags": len(scan["flags"]), "faces": b["faces"], "volume_cm3": b["volume_cm3"],
            "slivers_total": len(scan["slivers"]),
            "slivers_by_type": {t: sum(1 for s in scan["slivers"] if s["type"] == t) for t in
                                sorted(set(s["type"] for s in scan["slivers"]))},
            "design_face_slivers": [s for s in scan["slivers"] if s["type"] in ("planar_drafted", "flat_perp_Z", "cone",
                                                                               "cylinder_other")],
            "min_2a_p": scan["min_2a_p"], "min_area_mm2": scan["min_area"],
            "thin_strips_lt_1mm": len(scan["thin_strips_lt_1mm"]),
            "thin_wall_probe": [{"z": lv["z"], "thin_walls": len(lv["thin_walls"]), "thin_gaps": len(lv["thin_gaps"])}
                                for lv in thin["levels"]],
            "thin_note": "thin walls only at Z -14.0 = the 1.0 lip (by design, as stage 1); thin gaps: none at any level "
                         "(stage 1: the H6 crescent at Z -7.7)",
            "unfilleted_concave_roots": {g: sum(1 for x in scan["unfilleted_concave_roots"] if x["group"] == g)
                                         for g in sorted(set(x["group"] for x in scan["unfilleted_concave_roots"]))},
            "above_Z0": abz},
        "flex_test_after_fix": [{"case": r["case"], "healthy": r["healthy"], "bodies": r["bodies_in_component"],
                                 "lumps": r["lumps"], "volume_cm3": r["volume_cm3"], "faces": r["faces"],
                                 "roots": r["unfilleted_concave_roots_by_group"]} for r in flex],
        "flex_slivers_after_fix": [{"case": r["case"], "design_face_slivers": r["design_face_slivers"],
                                    "fillet_blend_slivers": r["blend_slivers"], "rule_fillet_faces": r["fillet_faces"],
                                    "h6_fill_y": r["h6_fill_y"]} for r in fsl]}
    rep["scans"]["slivers_total"] = len(scan["slivers"])
    rep["scans"]["design_face_slivers"] = []
    rep["scans"]["slivers_note"] = ("after stage 2 Part A: 58 sphere + 8 torus R0.5 fillet-blend patches (max 0.44 mm2), "
                                    "0 design-face slivers (stage 1 had the H7 strip)")
    rep["scans"]["thin_wall_probe"] = thin
    rep["flex_test"] = rep["stage2_partA"]["flex_test_after_fix"]
    rep["known_weaknesses"] = [w for w in rep["known_weaknesses"] if not (w.startswith("H7 corner cell") or
                                                                          w.startswith("H6 corner cell"))]
    rep["known_weaknesses"].insert(0, "H6 corner: the boss is merged into the tail wall (stage 2 Part A); local solid "
                                      "section ~5.4 inscribed (pilot to tail pocket 6.4) - watch sink on the Z 0 wall top "
                                      "(PCB rests on the boss tops)")
    rep["known_weaknesses"].append("Stage 2 assembly finding (not a frame-geometry defect): the ISO 13918 PT M4 weld "
                                   "flange (5.3-5.7 x 0.7-1.4) does not fit the 5.4 slot at the F1-F4 pads (slot 5.383 "
                                   "at the pad top); see the assembly report")
    json.dump(rep, open(FR_OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return rep


def gap_rows(gaps, key):
    out = []
    for lv in gaps["levels"]:
        if key in lv:
            out.append({"z": lv["z"], "min": lv[key]["min"], "max": lv[key]["max"], "by_side": lv[key]["by_side"]})
    return out


def assembly_report():
    doc = J("docinfo_asm.json")
    fp = J("fit_parts.json")
    ob = J("offline_asm_board.json")
    ft = J("fit_tails.json")
    gaps = J("offline_asm_gaps.json")
    bear = J("offline_asm_bearing.json")
    wires = J("offline_asm_wires.json")
    abz = J("offline_abovez.json")
    pv = {p["name"]: p for p in doc["user_parameters"]}
    stage2 = [p for p in doc["user_parameters"] if p["comment"].startswith("stage 2")]
    fvp = {(r["comp"], r["body"]): r for r in fp["frame_vs_parts"]}

    def fr(c, b):
        r = fvp[(c, b)]
        return {"d_mm": r["d_mm"], "overlap_mm3": r.get("overlap_mm3"), "p_frame": r["p1"], "p_part": r["p2"]}
    pp = fp["part_pairs_within_0.5"]

    def pair(a, b):
        for r in pp:
            if (r["a"].startswith(a) and r["b"].startswith(b)) or (r["a"].startswith(b) and r["b"].startswith(a)):
                return {"d_mm": r["d_mm"], "overlap_mm3": r.get("overlap_mm3")}
        return None
    T = ft["tails"]
    tails = {}
    for nm in ("tft_tail_5", "ctp_tail_7"):
        m = T[nm]["model (rigid -0.80)"]
        v = T[nm]["v2 position (+0.80 back)"]
        rows = m["frame_faces"]

        def best(pred):
            c = [r for r in rows if pred(r)]
            return min(c, key=lambda r: r["d_mm"]) if c else None
        tails[nm] = {
            "model_frame_min": m["frame_min"],
            "model_frame_min_where": rows[0] if rows else None,
            "v2_position_frame_min": v["frame_min"], "v2_position_frame_min_points": v.get("frame_min_points"),
            "to_tail_pocket_side_wall": best(lambda r: r["owner"] == "Tail pocket" and abs(r["normal"][0]) > 0.99),
            "to_tail_pocket_bottom_face": best(lambda r: r["owner"] == "Tail pocket" and r["normal"][1] < -0.99),
            "to_tail_pocket_corner_R1.5": best(lambda r: r["owner"] == "Tail pocket" and r["type"] == 2),
            "to_land_Z_LAND_face": best(lambda r: r["owner"] == "Glass recess"),
            "to_Z0_faces_near_connector (return leg)": best(lambda r: abs(r["p_frame"][2]) < 1e-3),
            "to_print_glass_back": m["print"]["d_mm"], "to_glass_body": m["glass"]["d_mm"], "to_bead": m["bead"]["d_mm"],
            "to_bond": m["bond"]["d_mm"],
            "v2_position_to_print": v["print"]["d_mm"]}
    fingers = {nm: {"model_overlaps": T[nm]["model (rigid -0.80)"].get("overlaps_with_board_bodies"),
                    "v2_position_overlaps": T[nm]["v2 position (+0.80 back)"].get("overlaps_with_board_bodies")}
               for nm in ("tft_fingers_6", "ctp_fingers_8")}
    soc_board = {k: v for k, v in ft["sockets_vs_board"].items()}
    soc_frame = {s["socket"]: {"all_faces": s["vs_frame_all"]["d_mm"],
                               "faces_rising_above_washer_top": (s["vs_frame_faces_above_washer_top"] or {}).get("d_mm",
                                                                                                                 "> 10")}
                 for s in fp["sockets_vs_frame"]}
    P = lambda n: pv[n]["value"]
    rep = {
        "about": "Rev3.0 GlassFront fit assembly (stage 2): frame 'Frame GF' + glass, optical bond, Formex, bead, VHB "
                 "strips, oven sheet with fastener variants S4 (default) / R4 / S8, board STEP with DS1 at Z_PANEL_BACK. "
                 "Units mm; plan coordinates abs KiCad (x, y down); model X = x, Y = -y, Z 0 = PCB back, -Z = front.",
        "document": {"name": doc["document"], "dataFile_id": doc["dataFile_id"], "version": doc["version"],
                     "isModified": doc["isModified"], "timeline_count": doc["timeline_count"],
                     "timeline_unhealthy": doc["timeline_unhealthy"],
                     "versions": {"4": "stage 1 final", "5": "Part A cell corners", "6": "Part B layers + fasteners",
                                  "7": "board STEP imported + positioned", "8": "studs split from washers + nuts (36b)",
                                  "9": "final (this report)"},
                     "only_document_touched": True},
        "component_tree": doc["tree"],
        "parameters_added_stage2": stage2,
        "how_driven": {
            "Glass": "outline glass_x0..glass_y1 R_glass, Z_GLASS_FRONT..Z_GLASS_BACK (glass_t), chamfer glass_arris "
                     "front + back; 'Glass print (black, 0.02)' = print_t layer inside the glass back, outer edge "
                     "print_setback (glass_arris + 0.1) inside the glass edge, window pw_* R pw_r open; the glass body is "
                     "cut by it (combine, tool kept). Sketch 'Logo zone' (hidden) logo_cx/logo_cy/logo_w/logo_h.",
            "Optical bond": "panel outline panel_* R bond_r, Z_GLASS_BACK..Z_CTP_FRONT (t_opt)",
            "Formex sheet": "panel outline - sheet_inset, R1, Z_FORMEX_FRONT..Z_SEAT (sheet_t), as v2",
            "Bead": "ring bead_edge..bead_edge + bead_w inside the glass edge (corner R_glass - ...), Z_LAND..Z_GLASS_BACK "
                    "(t_bond), dia pip_d holes at the 8 pips",
            "VHB tape strips": "4 straight strips s_tape_in..s_tape_out, ends tape_margin before the dia pad_d pads at F1-F4, "
                               "Z_SHEET_BACK..Z_FLANGE_FRONT (t_gap)",
            "Oven sheet": "flange outline + sheet_margin (40), R flange_R + sheet_margin, cut-out s_cut (R_glass + s_cut), "
                          "Z_GLASS_FRONT..Z_SHEET_BACK (t_sheet); R4 body adds dia riv_hole at F1-F4",
            "Weld studs S4 F1-F4 / S8 F5-F8": "stud_d x stud_l from Z_SHEET_BACK + ISO 13918 PT weld flange stud_fl_d x "
                                              "stud_fl_k, at f<k>_x / f<k>_y",
            "Washers + nyloc nuts S4 / Washers, nuts, spacers S8": "DIN 9021 M4 (w4_*) on Z_TUBE_TOP, ISO 10511 M4 hex "
                                                                    "nut_s x nut_m on the washer; S8 spacers w4 x t_gap "
                                                                    "between sheet and flange",
            "Rivets R4": "dome head riv_head_d x riv_head_k (edge R riv_head_k - 0.2) in front of the sheet, shank riv_d "
                         "to the washer top, blind head envelope riv_blind_d x riv_blind_h (ASSUMED), DIN 9021 M5 (w5_*) "
                         "backing washers on Z_TUBE_TOP",
            "Check - socket cylinders": "dia socket_d from Z_TUBE_TOP + w4_t to socket_top at F1-F8",
            "Board": "kicad-cli STEP of a COPY of the board (37), occurrence +board_dz; DS1 occurrence (LCM, CTP, both "
                     "tails, fingers) moved rigidly by ds1_dz = Z_PANEL_BACK - ds1_model_back (-0.80) - position "
                     "snapshots (38), re-run 38 after changing board_dz / sheet_t / g_bs"},
        "board_import": {
            "command": "kicad-cli pcb export step --subst-models --user-origin 0x0mm -D KIPRJMOD=<project folder> -f "
                       "-o board_full.step <COPY of 3dFilamentDryer.kicad_pcb in %TEMP%\\rev3_glassfront\\board>",
            "kicad": "10.0", "board_md5": "82cfd2615aa8e4511e89f13eb2a7eb6c (commit a9d56fc)",
            "occurrences": 309, "bodies": 292, "import_seconds": 196,
            "note": "the KiCad project files were only copied; kicad-cli touched the mtime of "
                    "KiCad/3dFilamentDryer/.history/.git (no commit, no file content changed)"},
        "tails_treatment": (
            "The DS1 model's tails are rigid solids. The whole DS1 occurrence (panel AND tails AND fingers) was moved "
            "by -0.80 in Z. Consequences: (1) the tail legs attached to the panel edge and the U-loop fronts are where "
            "they really are (front-most CTP leg at Z -9.855 = Z_LOOP_FRONT -9.85 within 0.005); (2) the return legs "
            "and fingers are 0.80 too far forward: in reality the U-loops open up by 0.8 (U radius TFT 5.0 -> 5.4, CTP "
            "5.55 -> 5.95, concept 3c) and the fingers stay in J10 / J11; in the model the fingers overlap the PCB "
            "(TFT 8.8 mm3, CTP 2.45 mm3) - an artefact; (3) the loop bottoms keep their v2 y (in reality they rise by "
            "0.02-0.44), so y-clearances to the pocket bottom face are conservative. Every tail distance is therefore "
            "given twice: model position (correct for the panel-side legs and loop fronts) and v2 position (a "
            "temporary copy moved back +0.80: correct for the return legs / fingers)."),
        "checks": {},
        "renders": sorted(f for f in os.listdir(os.path.join(MECH, "renders")) if f.startswith("Fusion_Assembly")),
        "render_notes": "section views: temporary section analyses with hatch, frame shown white / Formex green / glass "
                        "light blue for contrast (restored); bead red and VHB yellow are visualisation colours (both "
                        "black in reality); a small round point glyph that belongs to the imported board STEP shows in "
                        "the views with the board (not geometry; absent in back_no_PCB and the frame renders)",
        "exports": {f: {"bytes": os.path.getsize(os.path.join(MECH, f)),
                        "what": w} for f, w in (
            ("Rev3.0_GlassFront_Assembly.step", "root, variant S4 as visible: 191 solids; Fusion omitted the hidden R4 / "
                                                "S8 / socket components and the hidden R4 sheet body (checked in the file)"),
            ("Rev3.0_GlassFront_Glass.step", "component Glass: glass with 0.5 arris + 0.02 print layer (2 solids)"),
            ("Rev3.0_GlassFront.f3d", "Fusion archive of the whole document (v9)"),
            ("Rev3.0_GlassFront_Frame.step", "frame, re-exported 14:21 right after Part A; frame unchanged since"),
            ("Rev3.0_GlassFront_Frame.stl", "frame, re-exported 14:21"))}}
    C = rep["checks"]
    # ---------------------------------------------------------------- C1
    C["1_interference_frame_vs_every_body"] = {
        "parts (all variants)": {"%s / %s" % k: {"d_mm": v["d_mm"], "overlap_mm3": v.get("overlap_mm3"),
                                                 "variant": v["variant"]} for k, v in fvp.items()},
        "board (292 bodies)": {"touching_or_overlapping": ob["frame_touching"],
                               "nearest_25": ob["frame_nearest_25"]},
        "verdict": ("0 overlap with the frame except the S4 / S8 weld flanges at F1-F4: 0.0574 mm3 each (ISO 13918 PT "
                    "M4 flange dia 5.5 x 0.7 in the 5.4 pad slot, which is 5.383 wide at the pad top) = FAIL (finding "
                    "F1). Intended contacts with 0 overlap: Formex on the shelf, bead on the land, 4 VHB strips in the "
                    "gap, sheet on seat ring + pads (S4 and R4 bodies), DIN 9021 washers on the tube tops (S4, S8, R4 M5), "
                    "S8 spacers on the flange front; PCB 0.080 above the boss / rib / wall tops (= the missing copper + "
                    "mask: physical contact). No board body touches the frame."),
        "part_pairs_touching": [r for r in pp if r["d_mm"] < 0.001],
        "variant_overlaps_not_real": "R4 rivets vs S4 sheet / S4 studs / S4 washers + nuts, S8 studs + spacers vs the "
                                     "VHB strips (S8 uses a foam gasket instead of tape): mutually exclusive variants",
        "S8_spacer_vs_S8_stud_weld_flange_mm3": pair("Weld studs S8 F5-F8 (hidden) / Weld stud M4x16 F5",
                                                     "Washers, nuts, spacers S8 F5-F8 (hidden) / Spacer DIN 9021 M4 F5"),
        "board_vs_parts_within_3mm": ob["parts_within_3mm_of_board_bodies"]}
    # ---------------------------------------------------------------- C2
    C["2_flushness_and_gaps"] = {
        "flush_plane_Z": fp["flush"], "flush_verdict": "glass front, lip top and sheet front all at Z -14.4200 "
                                                       "(difference 0.0000) - PASS",
        "g2_glass_edge_to_lip_inner_face_by_Z": gap_rows(gaps, "g2_glass_edge_to_frame"),
        "g2_note": "target 0.40 at the lip top; the recess wall has 1 deg draft (narrowing to the back): 0.391 at "
                   "Z -13.90 (end of the front arris) .. 0.374 mid .. 0.356 at Z -11.94 (start of the back arris); the "
                   "min 3D distance glass -> frame is 0.3563. Corners (glass R6 / lip R6.4, concentric) equal the sides "
                   "within 0.0004. At Z -14.37 (inside the arris and the lip-top R0.3) 0.975-0.983.",
        "g1_sheet_cutout_to_lip_outer_face_by_Z": gap_rows(gaps, "g1_cutout_edge_to_frame"),
        "g1_note": "target 0.40: 0.546 at Z -14.37 (lip-top R0.3), 0.4085 at mid sheet thickness (corners 0.4084), "
                   "0.336 at Z -13.47 = 0.05 in front of the sheet back where the R0.2 lip-root fillet starts; corners "
                   "(cut-out R7.8 / lip R7.4, concentric) equal the sides within 0.0003.",
        "tape_gap": {"sheet_back_Z": fp["layers"]["sheet_z"][1], "flange_front_Z": fp["layers"]["flange_front_faces_z"],
                     "gap_mm": round(fp["layers"]["flange_front_faces_z"][0] - fp["layers"]["sheet_z"][1], 4),
                     "tape_z": fp["layers"]["tape_z"]},
        "bead_thickness_mm": round(fp["layers"]["bead_z"][1] - fp["layers"]["bead_z"][0], 4),
        "pips": {"to_print_layer (= physical glass back)": 0.5, "to_glass_body (behind the 0.02 print)":
                 sorted(set(q["to_glass_mm"] for q in fp["pips"])), "per_pip": fp["pips"],
                 "note": "nominal clearance Z_PIP_TOP - Z_GLASS_BACK = 0.50 at all 8 pips (master WC min +0.13)"}}
    # ---------------------------------------------------------------- C3
    ds = ob["ds1"]
    C["3_panel"] = {
        "pocket_clearance_by_Z": {k: v for k, v in [(lv["z"], {kk: vv for kk, vv in lv.items() if kk != "z"})
                                                    for lv in gaps["levels"] if any(k.startswith("DS1") for k in lv)]},
        "pocket_min_3D": {p: ds[p]["frame"]["d_mm"] for p in ("lcm_0", "pu_tape_1", "sensor_2", "cover_print_3",
                                                             "cover_va_4")},
        "pocket_verdict": "min 0.821 at the LCM back edge (Z -5.805) against the pocket face / its R0.5 shelf-front "
                          "root fillet zone; 0.851 / 0.877 deeper in the LCM, 0.883 tape, 0.894 sensor; corners = sides "
                          "(the R0.5 pocket corners are inside the 0.8 offset). Target 0.8 nominal - PASS",
        "panel_back_to_Formex_mm": ds["lcm_0"]["Formex sheet / Formex sheet"]["d_mm"],
        "panel_back_note": "DS1 model LCM back at Z -5.805 (model panel_t 5.315, CTP front -11.120); target 0.80",
        "optical_bond_mm": round(fp["layers"]["bond_z"][1] - fp["layers"]["bond_z"][0], 4),
        "bond_contacts": {"glass": 0.0, "CTP cover (cover_print_3 / cover_va_4)": 0.0},
        "print_window": {
            "built_loops": doc["print_loops"],
            "vs_active_area_inside_by": {"left": round(P("pw_x0") - P("aa_x0"), 3),
                                         "right": round(P("aa_x1") - P("pw_x1"), 3),
                                         "top": round(P("pw_y0") - P("aa_y0"), 3),
                                         "bottom": round(P("aa_y1") - P("pw_y1"), 3)},
            "vs_cover_lens_view_area_inside_by (DS1 cover_va_4 body 26.31..181.39 x 23.23..110.15)": {
                "left": round(P("pw_x0") - 26.31, 3), "right": round(181.39 - P("pw_x1"), 3),
                "top": round(P("pw_y0") - 23.23, 3), "bottom": round(110.15 - P("pw_y1"), 3)},
            "note": "abs sides (front view mirrors left / right); AA from the master (= KiCad DS1 drawing)"}}
    # ---------------------------------------------------------------- C4
    C["4_tails"] = {"treatment": rep["tails_treatment"], "per_tail": tails, "fingers": fingers,
                    "verdict": ("target >= 1.5 to the frame: real (panel-side) minima CTP 1.530 (front leg -> tail-pocket "
                                "side wall x 39.19 and its corner with the clearance-pocket bottom face), TFT 1.532 "
                                "(loop side -> side wall x 167.43), 1.62 (TFT -> R1.5 bottom corner), 1.76 (TFT loop "
                                "bottom -> bottom face) - PASS with 0.03 margin. The model's TFT minimum 1.445 is the "
                                "return leg 0.8 too far forward over the Z 0 rib / wall top near J10 (artefact; 2.245 in "
                                "the v2 position, frame minimum there 1.546). Print / glass back: CTP 1.565, TFT 2.865; "
                                "bead: TFT 5.63, CTP 12.98.")}
    # ---------------------------------------------------------------- C5
    C["5_board"] = {"frame_vs_292_bodies_overlaps": len(ob["frame_touching"]),
                    "nearest": ob["frame_nearest_25"][:25],
                    "above_Z0_inside_outline_plus_1mm": abz,
                    "Formex_vs_lead_tips": ob["formex_vs_lead_tips"][:12],
                    "Q1_untrimmed": ft["deep_leads"],
                    "note": "Q1 (TO-220) leads untrimmed reach Z -8.115: 0.539 mm3 through the Formex and 2.612 mm3 into "
                            "the LCM; with the v2 rule (leads trimmed to <= 2.5 below the PCB back) 2.10 to the Formex and "
                            "3.31 to the LCM. Contact faces vs B.Cu pads: CadQuery agent."}
    # ---------------------------------------------------------------- C6
    w = P("w4_od") / 2
    C["6_fasteners"] = {
        "washer_bearing_on_tube_tops": bear,
        "washer_rim_beyond_slot_end": {"nominal (stud at slot centre)": round(w - P("slot_l") / 2, 3),
                                       "stud at the slot end (offset (slot_l - stud_d)/2 = 1.5)":
                                           round(w - P("slot_l") / 2 - (P("slot_l") - P("stud_d")) / 2, 3)},
        "stud_vs_stack": {"stud_top_Z": fp["fasteners"]["Weld stud M4x16 F1 [S4]"]["z"][1],
                          "nut_top_Z": fp["fasteners"]["Nyloc nut ISO 10511 M4 F1 [S4]"]["z"][1],
                          "protrusion_above_nut_mm": round(fp["fasteners"]["Weld stud M4x16 F1 [S4]"]["z"][1] -
                                                           fp["fasteners"]["Nyloc nut ISO 10511 M4 F1 [S4]"]["z"][1], 3),
                          "stack_sheet_back_to_nut_top_mm": round(fp["fasteners"]["Nyloc nut ISO 10511 M4 F1 [S4]"]["z"][1] -
                                                                  fp["levels"]["Z_SHEET_BACK"], 3),
                          "verdict": "4.0 of thread beyond the nut (>= 1.5 required; CD welding shortens ~0.3) - PASS"},
        "weld_flange_vs_slot": {"slot_w_at_flange_front": P("slot_w"),
                                "slot_w_at_pad_top": round(P("slot_w") - 2 * 1.0 * math.tan(math.radians(0.5)), 4),
                                "flange_dia_ISO13918_PT_M4": "5.5 (5.3..5.7), height 0.7..1.4",
                                "model_overlap_mm3_per_stud": fvp[("Weld studs S4 F1-F4", "Weld stud M4x16 F1")].get(
                                    "overlap_mm3"), "verdict": "FAIL (finding F1)"},
        "sockets_dia12_vs_board_true_nearest": soc_board,
        "sockets_dia12_vs_frame": soc_frame,
        "socket_note": "socket from the nut bottom (washer top Z -6.42) to Z +45; 1.000 to the tube top under the "
                       "washer at every F (the washer sits there); frame faces rising above the washer top: >= 8.42 (F5)",
        "rivets_R4": {"grip_mm": round(fp["fasteners"]["Backing washer DIN 9021 M5 F1 [R4]"]["z"][1] -
                                       fp["levels"]["Z_GLASS_FRONT"], 3),
                      "grip_note": "sheet 1.0 + pad 1.0 + flange 2.5 + tube 2.5 + washer 1.2 (master 8.2)",
                      "head": "dome dia 10 x 1.6 proud of the steel (master 1.5-2.0), head edge 11.24 from the cut-out "
                              "edge (centre 16.24)",
                      "shank_to_pad_slot_per_side": fvp[("Rivets R4 F1-F4 (hidden)", "Blind rivet 4.8 F1")]["d_mm"],
                      "shank_to_sheet_hole_per_side": round((P("riv_hole") - P("riv_d")) / 2, 3),
                      "blind_side": "formed head envelope dia 9 x 4 (ASSUMED) from Z -6.22 to -2.22 lies inside the dia-12 "
                                    "socket envelope: >= 17.05 to frame faces rising above the washer (F1-F4) and >= 20.72 "
                                    "to every board body"},
        "J20_J2_wire_exits": wires,
        "J20_J2_note": "plan distance to the corridors from the J20 / J2 courtyards to -x (+-2 mm, as concept_calc): F1 "
                       "to J2 27.52 (socket edge 21.52), F4 to J20 54.84 (48.84), F8 (S8 only) to J20 12.83 (nut corners "
                       "8.79, socket edge 6.83); no nut, stud or socket within 6 mm of the J20 / J2 models"}
    # ---------------------------------------------------------------- C7
    C["7_chin"] = {"glass_chin_y_gt_panel_y1": ft["chin"],
                   "land_plane_opening": doc["land_plane_openings_around_chin"],
                   "free_span": {"tail_pocket_opening_x": [P("tr_x0"), P("tr_x1")], "x_span": round(P("tr_x1") - P("tr_x0"), 3),
                                 "y_from_panel_edge_to_pocket_bottom": [P("panel_y1"), P("tr_y1")],
                                 "y_span": round(P("tr_y1") - P("panel_y1"), 3),
                                 "unsupported_glass_y_bond_edge_to_bead_inner_edge": [P("panel_y1"),
                                                                                      round(P("glass_y1") - P("bead_edge") - P("bead_w"), 3)],
                                 "unsupported_y_span": round(P("glass_y1") - P("bead_edge") - P("bead_w") - P("panel_y1"), 3)},
                   "verdict": "nothing touches the glass over the tail pocket: only the bead (bottom band) and the bond "
                              "(ends at y 119.0) touch it; nearest other bodies CTP tail 1.565 (print), TFT tail 2.865, "
                              "frame 0.356 (glass edge g2) / 0.500 (pips P2, P4 under the print) - PASS"}
    rep["findings"] = [
        {"id": "F1", "what": "CD weld stud flange vs the fastener slot (S4 / S8 at F1-F4)",
         "numbers": "ISO 13918 PT M4 flange dia 5.5 (5.3-5.7) x 0.7-1.4 high; slot 5.4 at the flange front, 5.383 at the "
                    "pad top (0.5 deg, wider to the back); model overlap 0.057 mm3 per stud (dia 5.5 x 0.7), more with "
                    "5.7 x 1.4: the frame cannot seat on the sheet",
         "smallest_change": "slot_w 5.4 -> 6.0 (>= 5.7 + 2 x 0.15); rivet clearance becomes 0.6 / side, DIN 9021 M4 "
                            "bearing ~78.8 mm2 (6.3 MPa at 500 N), washer rim at the worst offset unchanged (slot_l "
                            "kept). Alternative: a dia 6.5 x 1.5 counterbore only in the pad faces round the slot "
                            "(keeps 5.4 for rivet location). Frozen master - lead to decide."},
        {"id": "F2", "what": "S8 spacer DIN 9021 M4 (ID 4.3) cannot pass the weld flange (dia 5.5)",
         "numbers": "6.47 mm3 overlap per stud in the model; the spacer would sit on the flange (0.7-1.4) and the hard "
                    "stop would be 1.7-2.4 instead of 1.0",
         "smallest_change": "spacer with ID >= 6.0, 1.0 thick, e.g. DIN 988 6 x 12 x 1.0 shim (or the F1 slot fix "
                            "does not help here: the spacer lies on the sheet)"},
        {"id": "F3", "what": "Q1 lead length (carried over from v2)",
         "numbers": "untrimmed leads reach Z -8.115: 0.539 mm3 through the Formex, 2.612 mm3 into the LCM",
         "smallest_change": "keep the v2 assembly rule: trim Q1 leads to <= 2.5 below the PCB back (2.10 to the Formex)"},
        {"id": "F4", "what": "tail clearance margin", "numbers": "CTP front leg to the tail-pocket left wall 1.530, TFT "
                                                                "1.532 (target 1.5)",
         "smallest_change": "none required; if more margin is wanted, loop_clr 1.5 -> 1.7 moves tr_x0 / tr_x1 by 0.2"},
        {"id": "F5", "what": "panel model", "numbers": "LCM back at Z -5.805 (model 0.005 thicker than panel_t 5.32): "
                                                       "Formex gap 0.805", "smallest_change": "none"}]
    rep["frozen_parameter_issues"] = ["slot_w 5.4 is narrower than the ISO 13918 PT M4 weld flange (5.3-5.7) at "
                                      "F1-F4 (F1)", "hardware.spacer_S8 'DIN 9021 M4 washer 1.0' cannot pass the weld "
                                      "flange (F2)"]
    json.dump(rep, open(AS_OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return rep


if __name__ == "__main__":
    frame_report()
    a = assembly_report()
    print("written", FR_OUT, AS_OUT, len(json.dumps(a)))
