"""Stage 4 (GF-2.0), offline: writes Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json and
..._Assembly_report.json for GF-2.0 (complete, no errata file) from the stage-4 dumps in %TEMP%\\rev3_glassfront\\gf20
and %TEMP%\\rev3_glassfront\\scan_<tag>.json, with sha256 of the master params file and of the exported files.
Run AFTER 84 (export), 85 (docinfo), gf20_thickness_check.py on the exported frame STEP and
gf20_params_update.py --stage measured.   python -B build_gf20_reports.py"""
import hashlib
import json
import os
import time

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
TOOLS = "Design Reports/Rev3.0/tools/glassfront/fusion"
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
G = os.path.join(SCR, "gf20")
CONCEPT = "Design Reports/Rev3.0/tools/glassfront/concept/concept_gf2.md"


def J(*p):
    path = os.path.join(*p)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def finfo(name):
    p = os.path.join(MECH, name)
    st = os.stat(p)
    return {"file": "Mechanical/Rev3.0_GlassFront/" + name, "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(st.st_mtime)), "sha256": sha(p)}


def main():
    params_p = os.path.join(MECH, "Rev3.0_GlassFront_params.json")
    prm = json.load(open(params_p, encoding="utf-8"))
    if not str(prm["revision"]).startswith("GF-2.0") or "as_modelled_GF-2.0" not in prm:
        raise SystemExit("params file not GF-2.0 / measured stage missing")
    exp, doc = J(G, "export.json"), J(G, "docinfo.json")
    am, scan = J(G, "as_modelled_frame.json"), J(SCR, "scan_gf20_final.json") or J(SCR, "scan_gf20_after77.json")
    th = J(G, "thickness_final", "thickness_check.json")
    flex = J(G, "flex_final.json")
    fp, ft, fb, fx = J(G, "fit_parts.json"), J(G, "fit_tails.json"), J(G, "fit_board.json"), J(G, "fasteners.json")
    ftp = J(G, "fit_tails_panel_back.json")
    files = {n: finfo(n) for n in ("Rev3.0_GlassFront_Frame.step", "Rev3.0_GlassFront_Frame.stl",
                                   "Rev3.0_GlassFront_Glass.step", "Rev3.0_GlassFront_Assembly.step",
                                   "Rev3.0_GlassFront.f3d")}
    renders = sorted(f for f in os.listdir(os.path.join(MECH, "renders")) if f.endswith(".png"))
    flex_table = [{"case": r["case"], "healthy": r["healthy"], "timeline_unhealthy": r["timeline_unhealthy"],
                   "bodies": r["bodies_in_component"], "lumps": r["lumps"], "volume_cm3": r["volume_cm3"],
                   "faces": r["faces"], "bbox_abs": r["bbox_abs"], "params": r["params"],
                   "levels": {k: r["levels"][k] for k in ("Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_LANDPLATE_BACK",
                                                         "Z_TUBE_TOP", "glass_y1", "bend_y1", "fl_y1", "f_y1")},
                   "unfilleted_concave_roots": r.get("unfilleted_concave_roots_by_group")} for r in flex]
    thin = th["thin"] if th else {}
    thin_list = [{"plane": w.get("plane"), "class": w.get("class"), "width_max_mm": w.get("width_max"),
                  "at": w.get("at"), "length_mm": w.get("length"),
                  "what": w.get("what") or ("the 1.0 lip (by design; ring over the whole lip)" if w.get("plane") == "lip"
                                            else "H6 tail wall beside the jogged cell wall, 1.1 at Z_PCB (GF-1.1 h6_wall_min, "
                                                 "by design)" if abs(w["at"][0] - 168.4) < 1.0 else "UNEXPECTED")}
                 for w in thin.get("thin_walls", [])] + [dict(w, plane=w.get("plane")) for w in th.get("thin_extra_walls", [])]
    frame_rep = {
        "about": ("Rev3.0 glass-front carrier frame ('Frame GF'), revision GF-2.0, built in Fusion 360 (stage 4). Written "
                  "complete for GF-2.0 by %s/build_gf20_reports.py (no errata file; the GF-1.1 report and errata are in "
                  "Mechanical/Rev3.0_GlassFront/archive/GF-1.1/)." % TOOLS),
        "master_revision": prm["revision"],
        "master_params": {"file": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json", "sha256": sha(params_p)},
        "concept": CONCEPT,
        "document": {"name": doc["document"], "dataFile_id": doc["dataFile_id"], "version": doc["version"],
                     "versions_GF-2.0": [v for v in doc["versions"] if isinstance(v, dict) and v["version"] >= 15],
                     "guard": doc["guard"], "timeline_count": doc["timeline_count"],
                     "timeline_unhealthy": doc["timeline_unhealthy"], "user_parameters": doc["user_parameters"],
                     "only_document_modified": True},
        "exports": {"step": files["Rev3.0_GlassFront_Frame.step"], "stl": files["Rev3.0_GlassFront_Frame.stl"],
                    "exported_from_version": doc["version"],
                    "note": "the frame is not changed after this export; the STEP goes to independent verification as exported"},
        "body": dict(am["frame"], name="Frame GF", material_density_g_cm3=1.36, material="PA6-GF30 black",
                     appearance="Plastic - Matte (Black)"),
        "levels_glass_3.0": am["levels"],
        "driving_and_key_parameters": doc["gf20_parameters"],
        "pips": am["pips"],
        "pad_hard_stop_faces_mm2": am["pad_hard_stop_faces_mm2"],
        "features_GF-2.0": [
            {"script": "66", "what": "S8 dropped: F5-F8 tubes, slots, counterbores, coring, tube blend deleted; sketches / "
             "features renamed F1-F4; coring and counterbore floor rounds re-created on F1-F4"},
            {"script": "67", "what": "border 18.5 (glass_y1 = pw_y1 + border), g_bend / bend_y1 and the GF-2.0 parameters; "
             "'Tail pocket' = bend-gap slot (front piece of the split sketch); new cut 'Tail pocket over the bridge' "
             "(floor = land-plate back); flange bottom = flange_y1_bottom (flush with the bottom wall)"},
            {"script": "68 / 69", "what": "late block before the tubes: 'Floor over the flange plate (cells + tail pocket)' "
             "cut to Z_FLOOR_LOW, 'Cell ribs over the flange plate', divider rib (bridge low / high, over the flange "
             "plate), 'Bridge nose R bend_nose_R', 'Bridge land break land_break', rule fillet 'Root fillets R0.5 - floors "
             "over the bridge and the flange plate (rule)'"},
            {"script": "72-75", "what": "level snap robustness: Z_FLOOR_LOW (floor always >= 1.0 below the land-plate back), "
             "rule W = all concave edges of ['Land plate + step wall (back)', 'Outer wall block'] (covers the outer wall "
             "on the flange plate), 'Outer wall block' starts at Z_WALL_FRONT, land plate + step wall solid starts at "
             "Z_DISC_FRONT (no geometry change)"},
            {"script": "77", "what": "coring-groove side-two taper restored (-draft) after the profile change of 66"}],
        "scans": {"tag": scan["tag"], "face_count": scan["body"]["faces"], "classification_counts": scan["counts"],
                  "draft_flags": [{"why": f["why"], "type": f["type"], "centroid_abs": f["centroid_abs"], "area_mm2": f["area"]}
                                  for f in scan["flags"]],
                  "draft_flags_note": "only the 4 counterbore floors (Z -11.82) and the 4 coring-groove floors (Z -10.72) at "
                                      "F1-F4: horizontal floors at levels not in the scan's list, by design as GF-1.1 (16 "
                                      "there with F5-F8). No undrafted face, no A-side face above Z_SEAT",
                  "draft_values_planar_deg": scan["draft_values_planar"], "cone_half_angles_deg": scan["cone_half_angles"],
                  "slivers_total": len(scan["slivers"]),
                  "slivers_by_type": {t: sum(1 for s in scan["slivers"] if s["type"] == t) for t in
                                      sorted(set(s["type"] for s in scan["slivers"]))},
                  "design_face_slivers": [s for s in scan["slivers"] if s["type"] in ("planar_drafted", "flat_perp_Z",
                                                                                     "cone")],
                  "fillet_blend_slivers_max_area_mm2": max(s["area"] for s in scan["slivers"]),
                  "thin_strips_lt_1mm": scan["thin_strips_lt_1mm"],
                  "thin_strip_note": "faces narrower than 1.0 between parallel edges (not wall thicknesses): counterbore "
                                     "floor rings 0.67 and lip top flats 0.39 / 0.51 (GF-1.1), the bridge pocket face "
                                     "between the 0.3 break and the R1.5 nose 0.73 and the break face 0.42 (GF-2.0, by "
                                     "design)",
                  "unfilleted_concave_roots": scan["unfilleted_concave_roots"]},
        "thickness_and_thin_walls": {
            "method": "verification toolchain (tools/glassfront/verify mould_check, read-only) via gf20_thickness_check.py "
                      "on the exported frame STEP: voxel 0.2, 3D EDT, limit 5.0; thin probe with THIN_MIN 1.2 (brief) "
                      "on the toolchain's planes + GF-2.0 probes (Z -9.0, Z -8.3, x 79.92, x 60, y 138)",
            "max_inscribed_sphere_mm": th["max_sphere_dia"] if th else None,
            "spots_over_5.0": th["spots_over_5.0"] if th else None,
            "top_local_maxima": th.get("top_local") if th else None,
            "thin_walls_lt_1.2": thin_list,
            "thin_gaps": thin.get("thin_gaps"), "steel_knife_edges": thin.get("steel_knife_edges"),
            "frame_step": th["frame"] if th else None},
        "flex_test": {"cases": flex_table,
                      "note": "every case recomputes the whole design (all components); every parameter returned to its "
                              "default and the default state recomputed last (script 71, TAG final)"},
        "deviations_from_concept": [
            {"item": "flange bottom edge", "concept": "flange_y1_bottom 150.20", "model": "150.235 at the flange front (parting "
             "plane) = 150.20 at Z_LAND", "reason": "the bottom wall's outer face (tr_y1 + wall = 150.20 at Z_LAND, 1 deg, "
             "unchanged from GF-1.1) is continued to the flange front so wall and flange edge are ONE flush face; 150.20 "
             "at the flange front would leave a 0.035 step or thin the wall"},
            {"item": "floors behind the bridge at glass 1.1 (flex variant)", "concept": "flat at 1.1 (5.3)",
             "model": "Z_FLOOR_LOW = min(Z_FLANGE_BACK; Z_LANDPLATE_BACK - 1.0): at glass 1.1 the tail pocket / cell floors "
             "over the flange are at Z -8.92 (flange 1.6 there) instead of flat -7.92 (2.6); glass 2.0 / 3.0 / 4.0 unchanged",
             "reason": "one topology at every glass_t: with a flat floor the late-block cut ends the GF-1.1 cell fillets "
             "in-line and the rule fillet fails at the level snap (flex test 71 frame_v1)"},
            {"item": "bridge pocket face draft", "concept": "y 122.00 'Z_LAND .. -9.42 flat'", "model": "y 122.00 at Z_LAND, "
             "1 deg widening to the back (122.017 at -9.42)", "reason": "slot faces 1 deg (concept 5.3 moulding note 3)"},
            {"item": "divider rib ends", "concept": "y 122.0 .. 147.7", "model": "front face coplanar with the bridge pocket "
             "face, back end buried 0.5 into the bottom wall; low part to Z_PCB in front of the tail-wall step (129.0 at "
             "Z_PCB), high part to Z_TROUGH_TOP", "reason": "concept 'floor -> Z 0 for y < 129, -> +4.05 beyond'"},
            {"item": "cell ribs over the flange plate", "concept": "cells: front = land plate + step wall + flange plate",
             "model": "the GF-1.1 cell ribs (boss-to-beam, across) are cut by the lowered floor and re-made from Z_FLOOR_LOW "
             "to Z_CELL_RIB_TOP in the same planes", "reason": "ribs must stand on the lowered floor"}],
        "moulding_notes": {
            "bridge_feed": "the 128.8 mm bridge (land plate 2.5 + step wall + flange plate) is tied to the bottom wall by the "
                           "flange plate along its full length and by the divider rib (2.5) in the middle; fill/warp "
                           "simulation still required (the land's inner edge carries the bond line)",
            "slot_shut_off": "the bend-gap slot is the only through-opening at the bottom: 3.0 x 128.8; A (recess core) / B "
                             "(tail-pocket core) shut-off on its outline at Z_LAND; along the bridge edge the 0.3 break "
                             "moves the shut-off line 0.3 up the slot face (formed by the A core)",
            "nose": "R1.5 on the B side (pocket core), 1.0 of flat pocket face left above the 0.3 break; the divider rib's "
                    "front face is coplanar with the pocket face and interrupts the nose (R0.5 roots blend into it)",
            "thin_land_edge": "bead inner edge 1.09 from the pocket face, 0.79 from the break edge (bead squeeze-out risk, "
                              "concept risk 4)"},
        "sharp_inside_corners": [
            "8 pip roots (land Z -10.42)", "4 corner-pad roots on the flange front, F1-F4 (tape margin)",
            "seat-ring root on the flange front (tape margin)", "shelf back <-> bottom pocket wall, 2 segments (v2 corners 3 / 4)",
            "pilot and relief floors (blind holes), as v2",
            "GF-2.0: the tail-pocket corners at the shelf end (bend-gap slot front face x side walls, y 119.1) as GF-1.1"],
        "scripts_GF-2.0": ["66_gf20_drop_s8_f5_f8.py", "67_gf20_params_border_bridge.py", "68_gf20_bottom_late_block.py",
                           "69_gf20_divider_rib_profiles.py", "70_gf20_tails.py", "71_gf20_flex_test.py",
                           "72_gf20_snap_fix.py", "73_gf20_rules_wallfront.py", "74_gf20_rule_w_all_edges.py",
                           "75_gf20_disc_front.py", "76_gf20_scan.py", "77_gf20_coring_taper_fix.py",
                           "78_gf20_fit_parts_gaps.py", "79_gf20_fit_tails.py", "80_gf20_fit_board.py",
                           "81_gf20_fasteners.py", "82_gf20_scratch_export_measure.py", "83_gf20_renders.py",
                           "84_gf20_save_export.py", "85_gf20_docinfo.py", "gf20_params_update.py",
                           "gf20_thickness_check.py", "build_gf20_reports.py", "diag_gf20_*.py"],
        "renders": [r for r in renders if r.startswith(("Fusion_GF20_", "Fusion_FrameGF_"))]}
    json.dump(frame_rep, open(os.path.join(MECH, "Rev3.0_GlassFront_Frame_report.json"), "w", encoding="utf-8"), indent=1)

    # ------------------------------------------------------------------------------------------- assembly report
    fparts = [{k: r.get(k) for k in ("comp", "body", "variant", "visible", "d_mm", "overlap_mm3")} for r in fp["frame_vs_parts"]]
    pairs = [{k: r.get(k) for k in ("a", "b", "variants", "d_mm", "overlap_mm3")} for r in fp["part_pairs_within_0.5"]
             if r["d_mm"] < 0.001]
    same_variant_overlaps = [p for p in pairs if (p.get("overlap_mm3") or 0) > 1e-4 and len(set(p["variants"])) == 1]
    board_touch = []
    for r in fb["results"]:
        for q in r["parts"]:
            if q["d_mm"] < 0.001:
                board_touch.append({"board_body": r["path"].split("+")[-1], "part": q["part"], "variant": q["variant"],
                                    "overlap_mm3": q.get("overlap_mm3")})
    fr_board = [r for r in fb["results"] if "frame" in r]
    asm = {
        "about": "Rev3.0 glass-front fit assembly, revision GF-2.0 (stage 4), written complete by %s/build_gf20_reports.py; "
                 "the GF-1.1 report is in Mechanical/Rev3.0_GlassFront/archive/GF-1.1/" % TOOLS,
        "master_revision": prm["revision"], "concept": CONCEPT,
        "document": {"name": doc["document"], "dataFile_id": doc["dataFile_id"], "version": doc["version"],
                     "timeline_count": doc["timeline_count"], "timeline_unhealthy": doc["timeline_unhealthy"]},
        "component_tree": doc["component_tree"],
        "variants": {"S4": "visible default (4 weld studs + washers + nyloc nuts, VHB strips, sheet without holes)",
                     "R4": "hidden component 'Rivets R4 F1-F4 (hidden)' + hidden body 'Oven sheet R4 (rivet holes)'",
                     "S8": "REMOVED at GF-2.0 (components 'Weld studs S8 F5-F8 (hidden)' and 'Washers, nuts, spacers S8 "
                           "F5-F8 (hidden)' deleted by script 66; there was no gasket body); socket checks F5-F8 deleted"},
        "how_driven": "every part body is a user-parameter driven feature (unchanged from GF-1.1 scripts 35 / 36): the "
                      "border change moved glass, print, logo zone (15 high), bond, bead (+ pip holes), tape strips, sheet "
                      "cut-out, studs, washers, rivets automatically",
        "tails": {"component": "Tails GF-2.0 (bent-back route)", "script": "70_gf20_tails.py",
                  "route": "tail_route.<TFT|CTP>.centreline_yZ of concept_gf2_params.json (= params tail_route), 0.30 thick",
                  "outline_developed": prm["tail_route"]["TFT"]["outline_developed"] and
                  {"TFT": prm["tail_route"]["TFT"]["outline_developed"], "CTP": prm["tail_route"]["CTP"]["outline_developed"]},
                  "outline_check": "x extents of the DS1 tail bodies measured along both legs (diag_gf20_old_tail_widths): "
                                   "TFT 84.02-122.62 to y 126.0 (v 7), 84.02-165.90 beyond, return leg 145.40-165.90; CTP "
                                   "40.72-75.82 to y 128.5 (v 9.5), 50.92-70.62, return leg 58.27-61.77 below y 127.5 (v 34)",
                  "bodies": {nm: {"bbox": e["bbox"], "volume_mm3": e["volume_mm3"]} for nm, e in ft["tails"].items()},
                  "old_tails": "DS1 bodies tft_tail_5, tft_fingers_6, ctp_tail_7, ctp_fingers_8 hidden and renamed "
                               "'GF-1.1 reference - ... (old flat route, hidden)'; not in the assembly STEP"},
        "checks": {
            "1_interference_frame_vs_every_body": {
                "frame_vs_parts": fparts,
                "frame_vs_board_bodies": {"measured_within_6mm": len(fr_board),
                                          "touching_or_overlapping": [r["path"] for r in fr_board if r["frame"]["d_mm"] < 0.001],
                                          "closest": sorted([(round(r["frame"]["d_mm"], 4), r["path"].split("+")[-1])
                                                             for r in fr_board])[:8]},
                "verdict": "0 mm3 overlap between the frame and every assembly body (designed contacts at 0.0 distance: "
                           "Formex on the shelf, bead on the land, VHB strips on the flange, sheet on the seat ring / pads, "
                           "washers on the tube tops); frame to PCB 0.08 (board_dz artefact as GF-1.1)"},
            "2_part_pairs": {"touching_pairs": pairs, "same_variant_overlaps": same_variant_overlaps,
                             "note": "S4 / R4 pairs overlap by construction (two variants of the same fastener positions)"},
            "3_flush_and_gaps": {"flush": fp["flush"], "g2_glass_edge_to_lip": fp["g2_glass_edge_to_lip"],
                                 "g1_cutout_to_lip": fp["g1_cutout_to_lip"], "pips_to_glass": fp["pips"]},
            "4_bead_and_tape": {"bead": fp["bead"], "bead_area_band_mm2": prm["as_modelled_GF-2.0"]["bead_area_mm2"],
                                "tape": fp["tape"]},
            "5_tails": {"per_tail": ft["tails"], "panel_beyond_first_bend": ftp,
                        "summary": prm["as_modelled_GF-2.0"].get("tail_clearances_mm"),
                        "connector_note": "the tail ends lie inside the J10 / J11 housings (insertion 4.0 / 3.0; the KiCad "
                                          "connector models are solid): the overlaps with housing_0 / actuator_1 are the "
                                          "insertion, not a fit issue"},
            "6_board": {"parts_touching_board_bodies": board_touch,
                        "note": "Q1 (TO-220) lead tips vs the Formex: known GF-1.1 item (untrimmed model); tail roots touch "
                                "the panel at the exit (<= 0.001 mm3, the tail leaves the panel edge there)"},
            "7_fasteners": fx},
        "renders": renders,
        "exports": {k: v for k, v in files.items()},
        "assembly_step_content": {k: exp.get(k) for k in ("assembly_step_products", "assembly_step_solids",
                                                         "gf11_reference_bodies_in_assembly_step",
                                                         "gf20_tail_bodies_in_assembly_step",
                                                         "hidden_or_reference_in_assembly_step")},
        "findings": [
            "CTP tail -> bridge nose 0.95 nominal, 0.62 with the panel edge 0.35 towards the bridge (concept 0.93 / 0.60); "
            "TFT 1.52 / 1.24",
            "both tails: the closest frame feature is the bridge nose; pocket side walls >= 1.65, bottom face >= 2.03 (TFT), "
            "divider rib >= 2.52 (incl. its root fillets)",
            "S8 hardware removed; R4 K14 heads and backing washers checked at F1-F4 (81)",
            "the gate of concept_gf2.md 2.4 (real panel: tail straight, thickness, bend over a 3.0 gauge) still applies "
            "before the tool"]}
    json.dump(asm, open(os.path.join(MECH, "Rev3.0_GlassFront_Assembly_report.json"), "w", encoding="utf-8"), indent=1)
    print("written frame + assembly reports; params sha", sha(params_p), "frame step", files["Rev3.0_GlassFront_Frame.step"])


if __name__ == "__main__":
    main()
