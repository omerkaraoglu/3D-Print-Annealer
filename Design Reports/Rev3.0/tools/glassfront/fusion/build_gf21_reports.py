"""Stage 5 (GF-2.1), offline: writes Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json and
..._Assembly_report.json for GF-2.1 (complete, written so that no errata file is needed; the GF-2.0 reports and the
verification's GF-2.0 errata are in archive/GF-2.0/) from the stage-5 dumps in %TEMP%\\rev3_glassfront\\gf21 and
%TEMP%\\rev3_glassfront\\scan_gf21_final.json, with sha256 of the master params file and the exported files.
The points the GF-2.0 errata corrected are written correctly here: shelf-end corners (R0.5 rounds, not sharp), the
stepped / telescopic slot shut-off, pip top -> glass back 0.50 (0.52 is to the glass body behind the 0.02 print
layer), PCB distances (body model and seating plane), tail frame classes by face (not by closest point), stud
envelope extremes reported per class.
Run AFTER 84 (export), 85 (docinfo), gf20_thickness_check.py on the exported frame STEP and
gf21_params_update.py --stage measured.   python -B build_gf21_reports.py"""
import hashlib
import json
import os
import time

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
TOOLS = "Design Reports/Rev3.0/tools/glassfront/fusion"
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
G = os.path.join(SCR, "gf21")


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


def stud_classes(fx):
    out = {}
    for f, e in fx["F"].items():
        for grp in ("stud_centred",):
            v = e[grp]
            k = v["flange_closest_at"]
            if k not in out or v["flange_env_d_mm"] < out[k][0]:
                out[k] = (v["flange_env_d_mm"], "%s centred" % f)
        for grp in ("stud_tol", "stud_extreme"):
            for nm, v in e[grp].items():
                k = v["flange_closest_at"]
                if k not in out or v["flange_env_d_mm"] < out[k][0]:
                    out[k] = (v["flange_env_d_mm"], "%s %s %s" % (f, grp, nm))
    return {k: {"d_mm": v[0], "where": v[1]} for k, v in out.items()}


def main():
    params_p = os.path.join(MECH, "Rev3.0_GlassFront_params.json")
    prm = json.load(open(params_p, encoding="utf-8"))
    if not str(prm["revision"]).startswith("GF-2.1") or "as_modelled_GF-2.1" not in prm:
        raise SystemExit("params file not GF-2.1 / measured stage missing")
    exp, doc, am = J(G, "export.json"), J(G, "docinfo.json"), J(G, "as_modelled_frame.json")
    scan = J(SCR, "scan_gf21_final.json")
    th, flex = J(G, "thickness_final", "thickness_check.json"), J(G, "flex_final.json")
    fp, ft, fb, fx = J(G, "fit_parts.json"), J(G, "fit_tails.json"), J(G, "fit_board.json"), J(G, "fasteners.json")
    bz, bzd = J(G, "bend_zone_final.json"), J(G, "bend_zone_probe_derivation.json")
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
    thin = th["thin"]
    thin_list = []
    for w in thin.get("thin_walls", []):
        what = ("the 1.0 lip (by design; the ring over the whole lip)" if w.get("plane") == "lip" else
                "H6 tail wall beside the jogged cell wall, 1.1 at Z_PCB (GF-1.1 h6_wall_min, by design)"
                if abs(w["at"][0] - 168.4) < 1.0 else "UNEXPECTED")
        thin_list.append({"plane": w.get("plane"), "class": w.get("class"), "width_max_mm": w.get("width_max"),
                          "at": w.get("at"), "length_mm": w.get("length"), "what": what})
    bzf = bz[0]
    frame_rep = {
        "about": ("Rev3.0 glass-front carrier frame ('Frame GF'), revision GF-2.1, Fusion 360 (stage 5: GF-2.0 rebuilt at "
                  "border 19.0 / g_bend 3.23). Written complete for GF-2.1 by %s/build_gf21_reports.py; no errata file. "
                  "CAD-side values; the independent verification of GF-2.1 follows. GF-2.0 reports + errata: "
                  "Mechanical/Rev3.0_GlassFront/archive/GF-2.0/." % TOOLS),
        "master_revision": prm["revision"],
        "master_params": {"file": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json", "sha256": sha(params_p)},
        "document": {"name": doc["document"], "dataFile_id": doc["dataFile_id"], "version": doc["version"],
                     "versions_GF-2.x": [v for v in doc["versions"] if isinstance(v, dict) and v["version"] >= 15],
                     "guard": doc["guard"], "timeline_count": doc["timeline_count"],
                     "timeline_unhealthy": doc["timeline_unhealthy"], "user_parameters": doc["user_parameters"],
                     "only_document_modified": True},
        "exports": {"step": files["Rev3.0_GlassFront_Frame.step"], "stl": files["Rev3.0_GlassFront_Frame.stl"],
                    "exported_from_version": doc["version"],
                    "note": "the frame is not changed after this export; the STEP goes to independent verification as exported"},
        "change_GF-2.0_to_GF-2.1": {
            "driven_by": "user parameters only (script 87): border 18.5 -> 19.0, g_bend 3.00 -> 3.23, logo_cy rule; the "
                         "timeline (204 items) and the topology are unchanged (889 faces)",
            "split": prm["change_log"]["split"],
            "bend_zone_CAD_side": {"derivation_probe": [{"params": r["params"],
                                                          "CTP": {k: v["d_mm"] for k, v in r["tails"]["CTP"].items() if isinstance(v, dict)},
                                                          "TFT": {k: v["d_mm"] for k, v in r["tails"]["TFT"].items() if isinstance(v, dict)},
                                                          "bead_to_break_land_plane": r["bead_to_break_formula_land_plane"]}
                                                         for r in bzd],
                                   "calibration": "at 18.5 / 3.00 the probe gives CTP nominal 0.946 / panel RSS 0.655 / panel "
                                                  "WC 0.383 = the verification's 0.946 / 0.654 / 0.382; its full worst case "
                                                  "(rigid exit-Z shift, tail thickness as -0.025) gives 0.257 against the "
                                                  "verification's 0.239 (re-swept tail): the probe reads ~0.02 high there",
                                   "GF-2.1": bzf}},
        "body": dict(am["frame"], name="Frame GF", material_density_g_cm3=1.36, material="PA6-GF30 black",
                     appearance="Plastic - Matte (Black)"),
        "levels_glass_3.0": am["levels"],
        "driving_and_key_parameters": doc["gf20_parameters"],
        "pips": am["pips"],
        "pad_hard_stop_faces_mm2": am["pad_hard_stop_faces_mm2"],
        "scans": {"tag": scan["tag"], "face_count": scan["body"]["faces"], "classification_counts": scan["counts"],
                  "draft_flags": [{"why": f["why"], "type": f["type"], "centroid_abs": f["centroid_abs"], "area_mm2": f["area"]}
                                  for f in scan["flags"]],
                  "draft_flags_note": "only the 4 counterbore floors (Z -11.82) and the 4 coring-groove floors (Z -10.72) at "
                                      "F1-F4: horizontal floors at levels outside the scan's list, by design as GF-1.1 / "
                                      "GF-2.0. No undrafted face, no A-side face above Z_SEAT",
                  "draft_values_planar_deg": scan["draft_values_planar"], "cone_half_angles_deg": scan["cone_half_angles"],
                  "slivers_total": len(scan["slivers"]),
                  "slivers_by_type": {t: sum(1 for s in scan["slivers"] if s["type"] == t) for t in
                                      sorted(set(s["type"] for s in scan["slivers"]))},
                  "design_face_slivers": [s for s in scan["slivers"] if s["type"] in ("planar_drafted", "flat_perp_Z", "cone")],
                  "fillet_blend_slivers_max_area_mm2": max(s["area"] for s in scan["slivers"]),
                  "thin_strips_lt_1mm": scan["thin_strips_lt_1mm"],
                  "thin_strip_note": "faces narrower than 1.0 between parallel edges (not wall thicknesses): counterbore floor "
                                     "rings, lip top flats, the bridge pocket face between the 0.3 break and the R1.5 nose and "
                                     "the break face (by design)",
                  "unfilleted_concave_roots": scan["unfilleted_concave_roots"]},
        "thickness_and_thin_walls": {
            "method": "verification toolchain (tools/glassfront/verify mould_check, read-only) via gf20_thickness_check.py on "
                      "the exported frame STEP: voxel 0.2, 3D EDT, limit 5.0; thin probe with THIN_MIN 1.2 on the "
                      "toolchain's planes + probes Z -9.0, Z -8.3, x 79.92, x 60, y 138",
            "params_used": th.get("params"), "max_inscribed_sphere_mm": th["max_sphere_dia"],
            "spots_over_5.0": th["spots_over_5.0"], "top_spots": th["top5"], "thin_walls_lt_1.2": thin_list,
            "thin_extra_probes_lt_1.2": th.get("thin_extra_walls"), "thin_gaps": thin.get("thin_gaps"),
            "steel_knife_edges": thin.get("steel_knife_edges"), "frame_step": th["frame"]},
        "flex_test": {"cases": flex_table,
                      "note": "script 71 (TAG final, GF-2.1 defaults): every case recomputes the whole design; every parameter "
                              "returned to its default and the default recomputed last"},
        "deviations_from_the_concept_and_GF-2.0": [
            {"item": "logo zone centre", "value": "y 118.24 = centred between window y1 + 1.0 and glass y1 - 2.5 (15 high: 1.25 "
             "/ 2.75)", "reason": "the border centre 118.99 would leave 2.0 to the glass edge (< 2.5); same rule as the "
             "verification's GF-2.0 correction (117.99)"},
            {"item": "flange bottom edge", "value": "150.235 at the flange front (unchanged; glass + 21 = 149.49 < the bottom "
             "wall)", "reason": "flush with the bottom-wall outer face, as GF-2.0"},
            {"item": "tail solids", "value": "unchanged (concept route, bodies still named 'GF-2.0 (bent back)')",
             "reason": "tail assumptions unchanged (lead): the 0.23 of g_bend is clearance to the nose"},
            {"item": "floors at glass 1.1", "value": "Z_FLOOR_LOW rule of GF-2.0 kept", "reason": "one topology at every glass_t"}],
        "moulding_notes": {
            "bridge_feed": "as GF-2.0: the 128.8 mm bridge is tied to the bottom wall by the flange plate and the divider rib; "
                           "fill / warp simulation still required",
            "slot_shut_off": "as the verified GF-2.0 cad rule, with the slot now 3.23 wide: parting on the bridge side at the "
                             "break top (y 122.235, Z -10.12) and on the front side at the shelf corner (y 119.00, Z_SEAT "
                             "-4.60), rising 5.52 over 3.23; A-side ledge 3.23 x 0.3 + telescopic face along y 119.0 (>= 3 "
                             "deg); angles to be re-verified at GF-2.1",
            "nose": "R1.5 on the B side; 1.0 of flat pocket face above the 0.3 break",
            "land_edge": "bead inner edge 1.06 from the break edge on the land plane (1.07 at Z_LAND + 0.01), 1.36 from the "
                         "pocket-face plane"},
        "inside_corners": [
            "sharp on purpose: 8 pip roots, 4 pad roots (F1-F4), seat-ring root (tape margin), shelf back <-> bottom pocket wall "
            "2 segments (v2 corners 3 / 4), pilot and relief floors",
            "R0.5 vertical rounds at the two shelf-end corners (y 119.0 x tail-pocket side walls, Z_SEAT .. Z_SHELF_BACK), "
            "added at GF-2.0 by the late-block rule fillet (verified 2026-11-16), kept"],
        "scripts_GF-2.1": ["gf21_archive_gf20.py", "86_gf21_bend_zone_probe.py", "gf21_params_update.py", "87_gf21_params.py",
                           "71 / 76 / 78-85 (GF-2.0 scripts run with DUMP gf21 / PREFIX GF21 / GF-2.1 DEFAULTS)",
                           "gf20_thickness_check.py", "build_gf21_reports.py"],
        "renders": [r for r in renders if r.startswith(("Fusion_GF21_", "Fusion_FrameGF_"))]}
    json.dump(frame_rep, open(os.path.join(MECH, "Rev3.0_GlassFront_Frame_report.json"), "w", encoding="utf-8"), indent=1)

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
    pips = [dict(q, to_glass_back_mm=round(q["to_glass_mm"] - 0.02, 4)) for q in fp["pips"]]
    tails = {}
    for nm, e in ft["tails"].items():
        pcb = next((q["d_mm"] for q in e["board_bodies_within_6"] if "PCB" in q["path"]), None)
        tails[nm] = {"frame_min": e["frame_overall"]["d_mm"], "frame_by_face_class": {k: v["d_mm"] for k, v in
                                                                                     sorted(e["frame_by_class"].items())},
                     "panel_edge_+0.35": e["frame_overall_panel_edge_+0.35"],
                     "panel_edge_-0.35": e["frame_overall_panel_edge_-0.35"],
                     "glass": e["parts"]["glass"]["d_mm"], "glass_print": e["parts"]["glass print"]["d_mm"],
                     "bead": e["parts"]["bead"]["d_mm"], "optical_bond": e["parts"]["optical bond"]["d_mm"],
                     "Formex": e["parts"]["Formex sheet"]["d_mm"], "PCB_body_model": pcb,
                     "PCB_component_seating_plane": "0.614 TFT / 0.414 CTP (verification GF-2.0; board and tail route unchanged)",
                     "bbox": e["bbox"]}
    asm = {
        "about": "Rev3.0 glass-front fit assembly, revision GF-2.1 (stage 5), written complete by %s/build_gf21_reports.py; "
                 "CAD-side values; GF-2.0 reports + errata in Mechanical/Rev3.0_GlassFront/archive/GF-2.0/" % TOOLS,
        "master_revision": prm["revision"],
        "document": {"name": doc["document"], "dataFile_id": doc["dataFile_id"], "version": doc["version"],
                     "timeline_count": doc["timeline_count"], "timeline_unhealthy": doc["timeline_unhealthy"]},
        "component_tree": doc["component_tree"],
        "variants": {"S4": "visible default", "R4": "hidden component 'Rivets R4 F1-F4 (hidden)' + hidden body 'Oven sheet R4 "
                     "(rivet holes)'", "S8": "removed at GF-2.0"},
        "how_driven": "every part body is user-parameter driven: border 19.0 moved glass, print, logo zone, bead (+ pip holes), "
                      "VHB strips, sheet cut-out, studs, washers, rivets; optical bond / Formex / board / tails unchanged",
        "tails": {"component": "Tails GF-2.0 (bent-back route)", "status": "unchanged from GF-2.0 (concept route; the "
                  "assumptions straight 0.5, R_in 1.5, t 0.30 unchanged)", "per_tail": tails,
                  "bend_zone_CAD_side_GF-2.1": bzf["tails"],
                  "connector_note": "the tail ends lie inside the J10 / J11 models (insertion; solid KiCad models): overlaps "
                                    "with housing_0 / actuator_1 are model artefacts as at GF-1.1 / GF-2.0"},
        "checks": {
            "1_interference_frame_vs_every_body": {
                "frame_vs_parts": fparts,
                "frame_vs_board_bodies": {"measured_within_6mm": len(fr_board),
                                          "touching_or_overlapping": [r["path"] for r in fr_board if r["frame"]["d_mm"] < 0.001],
                                          "closest": sorted([(round(r["frame"]["d_mm"], 4), r["path"].split("+")[-1])
                                                             for r in fr_board])[:8]},
                "verdict": "0 mm3 overlap between the frame and every assembly body (designed contacts at 0.0: Formex on the "
                           "shelf, bead on the land, VHB strips on the flange, sheet on the seat ring / pads, washers on the "
                           "tube tops); frame -> PCB 0.08 (board_dz artefact as GF-1.1)"},
            "2_part_pairs": {"touching_pairs": pairs, "same_variant_overlaps": same_variant_overlaps,
                             "note": "S4 / R4 pairs overlap by construction (two variants at the same fastener positions)"},
            "3_flush_and_gaps": {"flush": fp["flush"], "g2_glass_edge_to_lip": fp["g2_glass_edge_to_lip"],
                                 "g1_cutout_to_lip": fp["g1_cutout_to_lip"], "pips_to_glass": pips,
                                 "pip_note": "to_glass_back_mm = pip top Z_PIP_TOP -> glass back Z_GLASS_BACK (0.50); "
                                             "to_glass_mm is to the glass body, which sits 0.02 behind the print layer there"},
            "4_bead_and_tape": {"bead": fp["bead"], "bead_area_band_mm2": prm["as_modelled_GF-2.1"]["bead_area_mm2"],
                                "bead_to_bridge": bzf["bead_to_break"], "tape": fp["tape"]},
            "5_tails": tails,
            "6_board": {"parts_touching_board_bodies": board_touch,
                        "note": "Q1 (TO-220) lead tips vs the Formex: known GF-1.1 item (untrimmed model); tail roots touch the "
                                "panel at the exit (<= 0.001 mm3, the tail leaves the panel edge there)"},
            "7_fasteners": {"summary": fx["summary"], "envelope_min_by_class": stud_classes(fx), "per_fastener": fx["F"],
                            "note": "frame geometry round F1-F4 unchanged from GF-2.0 (translated with the glass corners); "
                                    "the verification's GF-2.0 stud-seat minima (wall 0.072, floor round 0.051, floor 0.20, "
                                    "shank 0.0001 at F3 end + across, finer positions) apply unchanged"}},
        "renders": renders,
        "exports": files,
        "assembly_step_content": {k: exp.get(k) for k in ("assembly_step_products", "assembly_step_solids",
                                                         "gf11_reference_bodies_in_assembly_step",
                                                         "gf20_tail_bodies_in_assembly_step")}}
    json.dump(asm, open(os.path.join(MECH, "Rev3.0_GlassFront_Assembly_report.json"), "w", encoding="utf-8"), indent=1)
    print("written frame + assembly reports; params sha", sha(params_p), "frame step", files["Rev3.0_GlassFront_Frame.step"])


if __name__ == "__main__":
    main()
