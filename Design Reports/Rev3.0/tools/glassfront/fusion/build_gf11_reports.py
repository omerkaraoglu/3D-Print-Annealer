"""Offline (stage 3, GF-1.1): refresh
  Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json
  Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Assembly_report.json
for the GF-1.1 model. Bases: the stage-2 reports (copied once to %TEMP%\\rev3_glassfront\\stage2_dumps\\*_report_stage2.json
and always rebuilt from there, so the script can be re-run) + the stage-3 dumps:
  docinfo_asm.json (47), scan_gf11_cb74.json (53 / 20 on the final frame), flex_gf11c.json (90), fit_parts.json +
  fit_parts_worstflange.json (39 / 57), fit_board.json, fit_tails.json, sections_asm.json (40-42), offline_asm_*.json /
  offline_abovez.json (gf_asm_offline.py), gf11\\as_modelled.json (57), gf11\\boss_pilot_check.json (60),
  gf11\\final\\thickness_check.json (gf11_thickness_check.py on the exported frame STEP).
The assembly checks are re-derived with build_stage2_reports.assembly_report() (same code as stage 2) and then the
stage-2 verdict texts are replaced by GF-1.1 ones. Usage: python build_gf11_reports.py"""
import datetime
import hashlib
import json
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stage2_reports as B  # noqa: E402

SCR = B.SCR
MECH = B.MECH
FR_OUT, AS_OUT = B.FR_OUT, B.AS_OUT
S2 = os.path.join(SCR, "stage2_dumps")
GF11 = os.path.join(SCR, "gf11")
PARAMS = os.path.join(MECH, "Rev3.0_GlassFront_params.json")


def J(n):
    p = os.path.join(SCR, n)
    if not os.path.exists(p):                      # J20 / J2 wire corridors: not re-run (fastener positions unchanged)
        p = os.path.join(S2, n)
    return json.load(open(p, encoding="utf-8"))


def Jg(n):
    return json.load(open(os.path.join(GF11, n), encoding="utf-8"))


def file_info(name, sha=False):
    p = os.path.join(MECH, name)
    st = os.stat(p)
    out = {"bytes": st.st_size,
           "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S") + " +03:00"}
    if sha:
        out["sha256"] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def backups():
    for src, dst in ((FR_OUT, "Frame_report_stage2.json"), (AS_OUT, "Assembly_report_stage2.json")):
        d = os.path.join(S2, dst)
        if not os.path.exists(d):
            shutil.copyfile(src, d)
    return (json.load(open(os.path.join(S2, "Frame_report_stage2.json"), encoding="utf-8")),
            json.load(open(os.path.join(S2, "Assembly_report_stage2.json"), encoding="utf-8")))


DOC_VERSIONS = {"4": "stage 1 final", "5": "Part A cell corners", "6": "Part B layers + fasteners",
                "7": "board STEP imported + positioned", "8": "studs split from washers + nuts (36b)",
                "9": "stage 2 final", "10": "GF-1.1 geometry (stage 3, 48-56) - saved by 59, all exports taken from it",
                "11": "GF-1.1: comment of user parameter cb_floor corrected (61, documentation only)",
                "12": "identical to v11: the MCP executed the top-level wrapper of 61 twice (second save without "
                      "changes)",
                "13": "GF-1.1 lead round 2: counterbore cb_w 7.4 x cb_l 9.0 (62); saved by 59 (MSG round 2), frame "
                      "STEP / STL, assembly STEP and glass STEP taken from it (frame STEP verified independently, "
                      "sha256 47742d2f...)",
                "14": "GF-1.1 round 3, hardware only (frame frozen, fingerprint checked): R4 rivet head dia 14 "
                      "(DIN 7337 K14), S8 shim DIN 988 7 x 13 x 1.0 (64); saved by 65, only the .f3d exported"}
EXPORT_VER = 13          # frame STEP / STL, assembly STEP, glass STEP
F3D_VER = 14
ASSEMBLY_ONLY = "--assembly-only" in sys.argv


def hw_json():
    return Jg("round3_hardware.json")


def ex_json():
    return Jg("extreme_stud_tape.json")


def cb_margin():
    ex = ex_json()

    def worst(s, k):
        rows = [(n, v[k]) for n, v in s.items() if isinstance(v, dict) and k in v and v[k]]
        n, r = min(rows, key=lambda t: t[1]["d_mm"])
        return dict(r, position=n)
    out = {"case": "flange dia 5.7 x 1.4 (worst case), ONE stud moved in the model (63) until its shank is 0.002 from "
                   "the slot wall / slot end (offsets 0.703 across, 1.503 along at F1; 0.707 / 1.507 at F5) and on the "
                   "end arcs (30 / 60 deg); flange faces measured face to face against the counterbore walls, floor "
                   "round and floor"}
    for f in ("F1", "F5"):
        s = ex["studs"][f]
        out[f + (" (F1-F4 type, floor 1.6)" if f == "F1" else " (F5-F8 type, floor 2.0)")] = {
            "centred": s["centred"],
            "extreme_min": {"to_wall": worst(s, "flange_to_wall"), "to_floor_round": worst(s, "flange_to_floor_round"),
                            "to_floor": worst(s, "flange_to_floor")},
            "per_position": {n: {k: (v[k]["d_mm"] if isinstance(v[k], dict) else v[k]) for k in v}
                             for n, v in s.items() if n not in ("faces", "flange_faces", "shank_faces", "centred")}}
    out["note"] = ("the same minimum at every extreme position (slot and counterbore are offsets of the same stadium "
                   "segment); ~0.15 at the opening, the minimum sits at the flange top edge where the 1 deg wall draft "
                   "and the R0.3 floor round close in")
    return out


def gf11_changes(pv, am, cb_margin):
    P = lambda n: pv[n]["value"]
    return [
        {"item": "1 + lead amendment: weld-stud counterbore",
         "built": "stadium %.1f wide x %.1f long at the opening (Z_SHEET_BACK), coaxial with each 5.4 x 7.0 slot (slot "
                  "outline + 1.0 per side, lead round 2; first GF-1.1 build 7.2 x 8.8 = + 0.9), 1 deg draft narrowing "
                  "with depth (A-half core), floor edge round R%.1f; "
                  "F1-F4 floor %.1f above Z_SHEET_BACK in the pad face (Z -11.82 at glass 3.0); F5-F8 floor %.1f above "
                  "Z_SHEET_BACK = 1.0 into the flange front (Z -11.42); slot 5.4 x 7.0 unchanged below the floors" %
                  (P("cb_w"), P("cb_l"), P("cb_r"), P("cb_floor"), P("cb_floor_mid")),
         "parameters": ["cb_w", "cb_l", "cb_floor", "cb_floor_mid", "cb_r"],
         "features": ["Fastener counterbores F1-F8 sketch", "Fastener counterbores F1-F4 (pads)",
                      "Fastener counterbores F5-F8", "Counterbore floor edges R cb_r"],
         "numbers": {"floor_clearance_over_1.4_flange": am["cb_floor_clear_over_1.4_flange"],
                     "pad_hard_stop_face_each_F1-F4_mm2": am["pad_contact_area_mm2"],
                     "pad_annulus_round_counterbore_mm": {"along_slot": am["pad_annulus_min"],
                                                          "across_slot": am["pad_annulus_across"], "required": 3.0},
                     "flange_to_counterbore_wall_worst_position": cb_margin}},
        {"item": "2: fastener boss coring",
         "built": "annular groove from the back round every tube F1-F8: r %.1f..%.1f at the tube top, %.1f deep below "
                  "Z_TUBE_TOP (floor Z -10.72 at glass 3.0, 2.7 above the pad face / 1.7 above the flange front at "
                  "F5-F8), 1 deg on both walls (groove widening to the back), floor rounds R%.1f; the cut is "
                  "two-sided (+1.0 above the tube top) so that no blend remnant hangs over the groove at glass 4.0" %
                  (P("core_r_in"), P("core_r_out"), P("core_depth"), P("core_floor_r")),
         "parameters": ["core_r_in", "core_r_out", "core_depth", "core_floor_r"],
         "features": ["Fastener tube coring F1-F8 sketch", "Fastener tube coring F1-F8",
                      "Coring groove floor edges R core_floor_r"],
         "numbers": {"washer_bearing_DIN9021_M4_mm2": 80.71, "rivet_backing_washer_DIN9021_M5_mm2": 88.41,
                     "required": ">= 80", "inner_wall_min_mm": "slot end to groove inner wall 2.7 (r 6.2 - 3.5)",
                     "outer_skin_mm": 1.5, "groove_floor_above_pad_face_mm": 2.7}},
        {"item": "3: H6 corner cell",
         "built": "the stage-2 solid fill (h6_fill_y) is gone; the cell wall towards the tail pocket is jogged inwards "
                  "(x %.2f at the cell floor) so that the tail wall keeps h6_wall_min %.1f at Z_PCB, and an R%.1f "
                  "corner arc tangent to the jogged wall and the cell top wall runs into the boss (boss crosses it at "
                  "~58 deg); slant back to the old cell wall from y %.1f over %.1f; boss and pilot untouched" %
                  (am["h6_jog_x"], P("h6_wall_min"), P("h6_corner_r"), P("h6_jog_y"), P("h6_jog_len")),
         "parameters": ["h6_wall_min", "h6_corner_r", "h6_jog_y", "h6_jog_len"], "deleted_parameters": ["h6_fill_y"],
         "features": ["Corner cells sketch (edited)", "Root fillets R0.5 - corner cells + cell ribs + cell bosses "
                                                      "(re-created, 81 edges)"],
         "numbers": {"boss_to_jogged_wall_air_at_boss_equator_mm": am["h6_air_min"],
                     "air_profile": am.get("h6_air_note"), "max_sphere_at_H6_mm": 4.53,
                     "boss_pilot_relief_cones_vs_stage2": "identical at H1-H9 (60_gf11_boss_pilot_check.py)"}},
        {"item": "4: tail pocket",
         "built": "side walls moved out by tail_side_add 0.3 (x 38.9 / 167.7 at the land), 1 deg draft and R1.5 "
                  "corners kept, bottom face 147.7 unchanged (loop_clr not raised: bottom-beam clearance 1.763 >= 1.6)",
         "parameters": ["tail_side_add"], "features": ["Tail pocket sketch (2 dims)"],
         "numbers": {"tail_wall_at_Z0_beside_cells_mm": 1.84, "tail_wall_at_H6_jog_Z_PCB_mm": 1.1,
                     "trough_top_wall_mm": "~1.69", "bottom_land_and_bead": "unchanged (pocket bottom face not moved)"}},
        {"item": "5: corner gaps",
         "built": "glass corner R_glass 6.25 (print layer, bead outlines follow), sheet cut-out corner R_cut 7.55 "
                  "(S4/S8 and R4 sheet bodies); lip R6.4 / R7.4 and seat ring R8.9 unchanged (frame outlines on the new "
                  "R_frame = 6.0)", "parameters": ["R_glass", "R_frame", "R_cut"]},
        {"item": "6: F5-F8 tube to step-wall blend",
         "built": "rule fillet tube_sw_r between the fastener tubes and the land plate + step wall: 1.2 at glass "
                  "3.0 / 4.0, 0.75 at 2.0 (junction only 1.0 high), 0.5 at the 1.1 snap; inserted before the R0.5 "
                  "tube rule fillet", "parameters": ["tube_sw_r"],
         "features": ["Root fillets tube_sw_r - F5-F8 tube to step wall (rule)"],
         "numbers": {"steel_wedge": "none: verification thin probe at Z -7.67 finds no gap (GF-1.0: two 0.3 wedges at "
                                    "F8, x 9.84)"}},
        {"item": "7: S8 spacer", "built": "DIN 988 6 x 12 x 1.0 shim (spacer_id 6.0 / spacer_od 12) on the stud "
                                          "between sheet and flange at F5-F8; bodies renamed 'Spacer DIN 988 6x12x1.0 Fk'",
         "parameters": ["spacer_id", "spacer_od"],
         "numbers": {"radial_clearance_to_flange_5.5": 0.25, "radial_clearance_to_flange_5.7": 0.15}},
        {"item": "8: bookkeeping", "built": "params only: lip width 1.0175 root / 0.9825 top, g1 at the front 0.4175"}]


def frame_report(rep, doc, pv, am, prm):
    scan = J("scan_gf11_cb74.json")
    flex = J("flex_gf11c.json")
    thick = Jg(r"final\thickness_check.json")
    ex = ex_json()
    bp = Jg("boss_pilot_check.json")
    abz = J("offline_abovez.json")
    b = scan["body"]
    rep["about"] = rep["about"].replace("stage 1 (frame) + stage 2 Part A (cell-corner fix)",
                                        "stage 1 (frame) + stage 2 Part A (cell-corner fix) + stage 3 GF-1.1 "
                                        "(counterbores, boss coring, H6 cell, tail pocket, corner radii, F5-F8 blend)")
    rep["master_revision"] = prm["revision"]
    rep["document"].update({"version": doc["version"], "version_note": "frame geometry last changed in v13 (GF-1.1 "
                            "lead round 2, counterbore 7.4 x 9.0); v10 first GF-1.1 build, v11 / v12 parameter comment "
                            "only", "versions": DOC_VERSIONS,
                            "timeline_count_frame_items": 85, "timeline_count_document": doc["timeline_count"],
                            "timeline_unhealthy": doc["timeline_unhealthy"], "isModified": doc["isModified"]})
    rep["document"]["timeline_count"] = 85
    fs = file_info("Rev3.0_GlassFront_Frame.step", sha=True)
    rep["exports"] = {
        "step": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step (component 'Frame GF', 1 solid, %d faces; "
                "exported from v%d by 59 = 25 verbatim)" % (b["faces"], EXPORT_VER),
        "step_file": fs,
        "stl": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.stl (binary, high refinement, from v%d)" %
               EXPORT_VER,
        "stl_file": file_info("Rev3.0_GlassFront_Frame.stl"),
        "renders": "Mechanical/Rev3.0_GlassFront/renders/Fusion_FrameGF_*.png (regenerated for GF-1.1 by 45) and "
                   "Fusion_GF11_*.png (58); GF11_thickness_map_verify_toolchain.png (verification thickness map of the "
                   "exported STEP)"}
    # user parameters: current values, h6_fill_y removed, GF-1.1 frame parameters added
    up = []
    for p in rep["user_parameters"]:
        if p["name"] in pv:
            up.append(pv[p["name"]])
    have = {p["name"] for p in up}
    for n in ("R_frame", "tail_side_add", "h6_wall_min", "h6_corner_r", "h6_jog_y", "h6_jog_len", "tube_sw_r", "cb_w",
              "cb_l", "cb_floor", "cb_floor_mid", "cb_r", "core_r_in", "core_r_out", "core_depth", "core_floor_r"):
        if n not in have:
            up.append(pv[n])
    rep["user_parameters"] = up
    rep["body"].update({k: b[k] for k in ("volume_cm3", "mass_g_at_1.36", "faces", "edges", "lumps", "shells",
                                          "is_solid", "bbox_abs")})
    rep["features_GF-1.1"] = [
        {"timeline": 33, "name": "Corner cells sketch", "change": "H6 cell: jogged wall + R h6_corner_r arc (49)"},
        {"timeline": 52, "name": "Tail pocket", "change": "sketch dims tr_x0 - / tr_x1 + tail_side_add (49)"},
        {"timeline": 60, "name": "Root fillets R0.5 - corner cells + cell ribs + cell bosses", "change": "re-created, 81 "
                                                                                                         "edges (49)"},
        {"timeline": 70, "name": "Root fillets tube_sw_r - F5-F8 tube to step wall (rule)", "change": "new (50)"},
        {"timeline": 181, "name": "Fastener tube coring F1-F8 sketch", "change": "new (52)"},
        {"timeline": 182, "name": "Fastener tube coring F1-F8", "change": "new, two-sided cut (52, 55)"},
        {"timeline": 183, "name": "Coring groove floor edges R core_floor_r", "change": "new, 16 edges (52, 56)"},
        {"timeline": 184, "name": "Fastener counterbores F1-F8 sketch", "change": "new (51b)"},
        {"timeline": 185, "name": "Fastener counterbores F1-F4 (pads)", "change": "new, cut cb_floor (51b)"},
        {"timeline": 186, "name": "Fastener counterbores F5-F8", "change": "new, cut cb_floor_mid (51b)"},
        {"timeline": 187, "name": "Counterbore floor edges R cb_r", "change": "new, 32 edges (51b)"}]
    rep["flat_face_levels_note"] = ("flat_face_levels_mm2 is the stage-1 census; GF-1.1 adds -11.820 -Z (4 x 12.58, "
                                    "counterbore floors F1-F4), -11.420 -Z (4 x 12.35, F5-F8) and -10.720 +Z (8 x 17.16, "
                                    "groove floors) and reduces the pad / flange front / tube top faces accordingly")
    rep["dimension_check_note"] = ("stage-1 sections; the lip, seat ring and flange outlines did not change in GF-1.1 "
                                   "(they stay on R_frame 6.0 = the GF-1.0 R_glass)")
    sl = scan["slivers"]
    sc = rep["scans"]
    sc.update({
        "face_count": b["faces"], "classification_counts": scan["counts"],
        "draft_flags": scan["flags"],
        "draft_flags_note": "16 new horizontal faces, all intended: counterbore floors F1-F4 at -11.82 and F5-F8 at "
                            "-11.42 (A side, -Z) and the 8 coring-groove floors at -10.72 (B side, +Z); no other flag",
        "draft_values_planar_deg": scan["draft_values_planar"], "cone_half_angles_deg": scan["cone_half_angles"],
        "slivers_total": len(sl),
        "slivers_by_type": {t: sum(1 for s in sl if s["type"] == t) for t in sorted(set(s["type"] for s in sl))},
        "slivers_note": "GF-1.1: 57 sphere + 8 torus fillet-blend patches, 0 design-face slivers (planar / cone / "
                        "cylinder / flat), min 2A/P %.4f, min area %.4f mm2" % (scan["min_2a_p"], scan["min_area"]),
        "design_face_slivers": [s for s in sl if s["type"] in ("planar_drafted", "flat_perp_Z", "cone",
                                                               "cylinder_other")],
        "thin_strip_scan_lt_1mm": scan["thin_strips_lt_1mm"],
        "thin_strip_note": "8 lip-top strips as before (R0.3 / R0.2 lip rounds) + 24 counterbore faces: F5-F8 straight "
                           "walls 0.705 x 1.6 (2A/P 0.49), F5-F8 floor ledges 0.662, F1-F4 floor ledges 0.672 (the 1.0 "
                           "counterbore step minus the R0.3 round; 0.562 / 0.572 at 7.2 x 8.8); all above the 0.3 "
                           "sliver rule",
        "thin_wall_probe": {"source": "verification toolchain (verify/mould_check.py via gf11_thickness_check.py) on the "
                                      "exported frame STEP", "planes": thick["thin"]["planes"],
                            "verdict": "no wall < 1.0 except the 1.0 lip (by design; the 3 lip-corner 'V-notch' hits are "
                                       "raster artefacts at the lip corner arcs, identical in the GF-1.0 verification "
                                       "run); no thin gap anywhere (GF-1.0: two 0.3 steel wedges at F8, Z -7.67)"},
        "unfilleted_concave_roots": scan["unfilleted_concave_roots"]})
    sc["thickness_verification_method"] = {
        "file": "Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step", "file_info": thick["frame_info"],
        "method": "voxel 0.2 mm + 3D Euclidean distance transform (verify/mould_check.py thick check, limit 5.0)",
        "max_sphere_dia_mm": thick["max_sphere_dia"], "spots_over_5.0": thick["spots_over_5.0"],
        "top5": thick["top5"], "map": "renders/GF11_thickness_map_verify_toolchain.png",
        "GF-1.0_for_comparison": "6.0 at F1-F4 and H6, 5.2 at F5-F8 (verification agent)"}
    rep["flex_test"] = [{"case": r["case"], "healthy": r["healthy"], "bodies": r["bodies_in_component"],
                         "lumps": r["lumps"], "volume_cm3": r["volume_cm3"], "faces": r["faces"],
                         "timeline_unhealthy": r["timeline_unhealthy"], "roots": r["unfilleted_concave_roots_by_group"]}
                        for r in flex]
    rep["flex_test_note"] = ("GF-1.1 with the 7.4 x 9.0 counterbore (90 TAG gf11c after 62): all 7 cases healthy, 1 "
                             "body / 1 lump, same unfilleted-root census; parameters back at glass 3.0 (%.4f cm3, %d "
                             "faces); no -Z face over a groove at glass 4.0 (55 / 56 probe; groove unchanged in round 2)"
                             % (b["volume_cm3"], b["faces"]))
    rep["carried_over_check"]["GF-1.1"] = {
        "boss_pilot_relief_H1-H9": "identical to stage 2 (cones, radii, Z ranges, pilot floors) - %s" %
                                   ("no difference" if not bp["differences"] else bp["differences"]),
        "changed_by_design": "tail pocket side walls +0.3 (tail walls 0.3 thinner), H6 cell wall jog, counterbores, "
                             "coring grooves, F5-F8 tube blend; nothing else",
        "above_Z0": abz}
    rep["deviations_from_master"] += [
        {"item": "GF-1.1 core_r_out", "master": "brief: groove start r 6.2-7.6", "built": "7.5",
         "why": "7.6 clips the R0.5 tube-top / step-wall fillet at glass 4.0; 7.5 keeps a 1.5 skin"},
        {"item": "GF-1.1 core_floor_r", "master": "not given", "built": "R0.4",
         "why": "groove 1.185 wide at the floor; R0.5 would leave a 0.185 flat (sliver), R0.4 leaves 0.385"},
        {"item": "GF-1.1 F5-F8 counterbore depth", "master": "brief: >= 0.2 clear of a 1.4 flange (0.6 into the flange)",
         "built": "1.0 into the flange (0.6 clear)",
         "why": "0.6 deep leaves a 0.3 x 1.6 straight wall strip above the R0.3 floor round (2A/P < 0.3)"},
        {"item": "GF-1.1 cb_r", "master": "brief 0.2-0.3", "built": "0.3",
         "why": "0.2 / 0.25 produce floor-round cylinder strips with 2A/P 0.26-0.29 that the verification counts as "
                "design faces"},
        {"item": "GF-1.1 H6", "master": "brief: replace the solid fill with coring",
         "built": "cell wall jogged + R2.5 corner arc (the cell itself is the coring); no separate core",
         "why": "keeps the boss / pilot untouched, tail wall 1.1 at Z_PCB, sphere at H6 4.53"},
        {"item": "GF-1.1 tube_sw_r", "master": "brief R1.0-1.5", "built": "1.2 at glass 3.0 / 4.0, 0.75 at 2.0, 0.5 at 1.1",
         "why": "the tube / step-wall junction is only 1.0 high at glass 2.0 and absent at the 1.1 snap"}]
    kw = [w for w in rep["known_weaknesses"] if not (w.startswith("H6 corner:") or w.startswith("Stage 2 assembly finding")
                                                     or w.startswith("Part mass"))]
    kw += ["Part mass %.1f g (GF-1.1: %.3f cm3 at 1.36 g/cm3), about 18 %% above the concept estimate (flange 223.5 x "
           "185.8 x 2.5 dominates)." % (b["mass_g_at_1.36"], b["volume_cm3"]),
           "H6 cell (GF-1.1): the tail wall beside the jog is 1.1 at Z_PCB (thinnest wall outside the lip); the boss "
           "crosses the R2.5 corner arc at ~58 deg; that V is rounded R0.5 by the cell root-fillet set (rolling-ball "
           "blend face 8.59 mm2, Z -7.44..0, sphere corner at the floor); air 1.53 at the boss equator.",
           "Counterbore floor ledges are 0.66 (F5-F8) / 0.67 (F1-F4) wide between slot and floor round, the F5-F8 "
           "counterbore walls 0.7 high: fine core-pin detail, above the sliver rule.",
           "Weld flange in the counterbore at the extreme stud position (dia 5.7 x 1.4, modelled, shank against the "
           "slot wall / end): F1-F4 %.3f to the wall, %.3f to the R0.3 floor round, %.1f to the floor; F5-F8 %.3f / "
           "%.3f / %.1f (~0.15 at the opening)." % tuple(
               min(v[k]["d_mm"] for n, v in ex["studs"][f].items() if isinstance(v, dict) and k in v and v[k])
               for f in ("F1", "F5") for k in ("flange_to_wall", "flange_to_floor_round", "flange_to_floor")),
           "tube_sw_r is 0.75 at glass 2.0 and 0.5 at the 1.1 snap (below the 1.0-1.5 of the brief, geometry-limited)."]
    rep["known_weaknesses"] = kw
    rep["stage3_GF-1.1"] = {
        "brief": "GF-1.0 -> GF-1.1 batch, items 1-8 + lead amendment (counterbore 7.2 x 8.8) + lead round 2 "
                 "(counterbore 7.4 x 9.0, extreme-stud model, H6 V radius if one feature)",
        "round_2": {"counterbore": "cb_w 7.2 -> 7.4, cb_l 8.8 -> 9.0 (62, parameters only)",
                    "H6_V": "not changed: the V between the boss and the R2.5 arc already carries the R0.5 cell root "
                            "fillet (it is one of the 81 edges of 'Root fillets R0.5 - corner cells + cell ribs + cell "
                            "bosses'); a larger radius there means splitting that edge out of the 81-edge feature and "
                            "re-creating it (two features), so it was left at R0.5",
                    "scripts": ["62_gf11_cb_7p4x9p0.py", "90_flex_test.py (TAG gf11c)",
                                "53_gf11_scratch_export_scan.py (TAG_SUFFIX cb74)", "63_gf11_extreme_stud_tape.py",
                                "57 / 39 / 42 / gf_asm_offline.py re-run", "58 / 45 / 43 (2 sections) renders",
                                "59 (MSG round 2) save + exports", "gf11_params_round2.py"]},
        "scripts": ["48_gf11_params_assembly.py", "49_gf11_tail_pocket_h6.py", "50_gf11_tube_stepwall_blend.py",
                    "51_gf11_counterbores.py (superseded by 51b)", "51b_gf11_counterbores_rebuild.py",
                    "52_gf11_tube_coring.py", "53_gf11_scratch_export_scan.py", "54_gf11_flex_fixes.py",
                    "55_gf11_cb_amend_groove_twoside.py", "56_gf11_groove_floor_fillet.py",
                    "57_gf11_fit_worstcase_asmodelled.py", "58_gf11_renders.py", "59_gf11_save_export.py",
                    "60_gf11_boss_pilot_check.py", "61_gf11_comment_fix_save.py", "gf11_thickness_check.py",
                    "gf11_params_update.py", "build_gf11_reports.py"],
        "changes": gf11_changes(pv, am, cb_margin()),
        "volume_mass": {"GF-1.0": [84.016, 114.26], "GF-1.1": [b["volume_cm3"], b["mass_g_at_1.36"]],
                        "unit": ["cm3", "g at 1.36"]},
        "thickness_iterations": [{"run": "iter1 (after 52)", "note": "groove at r 6.2-7.7, before the amendment"},
                                 {"run": "iter3 (after 56, 7.2 x 8.8)", "max": 4.6},
                                 {"run": "cb74 scratch (after 62, 7.4 x 9.0)", "max": 4.6},
                                 {"run": "final (exported deliverable STEP)", "max": thick["max_sphere_dia"]}]}
    return rep


def assembly_report(rep2, doc, pv, am, fr):
    B.J = J
    tmp = os.path.join(SCR, "gf11", "assembly_report_rederived.json")
    B.AS_OUT = tmp
    a = B.assembly_report()
    B.AS_OUT = AS_OUT
    P = lambda n: pv[n]["value"]
    fw = J("fit_parts_worstflange.json")
    fwv = {(r["comp"], r["body"]): r for r in fw["frame_vs_parts"]}
    fp = J("fit_parts.json")
    a["about"] = a["about"].replace("fit assembly (stage 2)", "fit assembly (stage 2, updated to GF-1.1 in stage 3)")
    a["document"]["versions"] = DOC_VERSIONS
    a["parameters_added_stage3"] = [p for p in doc["user_parameters"] if p["comment"].startswith("GF-1.1")]
    hd = a["how_driven"]
    hd["Glass"] = hd["Glass"].replace("R_glass,", "R_glass (6.25 since GF-1.1; frame outlines on R_frame 6.0),")
    hd["Oven sheet"] = hd["Oven sheet"].replace("cut-out s_cut (R_glass + s_cut)", "cut-out s_cut (corner R_cut 7.55)")
    hd["Washers + nyloc nuts S4 / Washers, nuts, spacers S8"] = hd[
        "Washers + nyloc nuts S4 / Washers, nuts, spacers S8"].replace("S8 spacers w4 x t_gap", "S8 spacers DIN 988 "
                                                                       "spacer_id x spacer_od x t_gap")
    C = a["checks"]
    c1 = C["1_interference_frame_vs_every_body"]
    sp = []
    for k in (5, 6, 7, 8):
        for r in fp["part_pairs_within_0.5"]:
            if r["a"].endswith("Weld stud M4x16 F%d" % k) and r["b"].endswith("Spacer DIN 988 7x13x1.0 F%d" % k):
                sp.append({"F": k, "d_mm": r["d_mm"], "overlap_mm3": r.get("overlap_mm3")})
    c1.pop("S8_spacer_vs_S8_stud_weld_flange_mm3", None)
    c1["S8_shim_DIN988_7x13_vs_weld_flange"] = {
        "pairs_within_0.5": sp, "radial_bore_to_flange (concentric, modelled diameters)": {
            "5.5": round((P("spacer_id") - 5.5) / 2, 3), "5.7": round((P("spacer_id") - 5.7) / 2, 3),
            "5.8 flange + collar envelope (stud spec)": round((P("spacer_id") - 5.8) / 2, 3)}}
    c1["worst_case_flange_5.7x1.4 (57: stud_fl_d / stud_fl_k set, 39 re-run, restored)"] = {
        "frame_vs_studs_F1-F4": fwv[("Weld studs S4 F1-F4", "Weld stud M4x16 F1")]["d_mm"],
        "frame_vs_studs_F5-F8": fwv[("Weld studs S8 F5-F8 (hidden)", "Weld stud M4x16 F5")]["d_mm"],
        "frame_vs_spacers": fwv[("Washers, nuts, spacers S8 F5-F8 (hidden)", "Spacer DIN 988 7x13x1.0 F5")]["d_mm"],
        "spacer_to_flange_radial": round((P("spacer_id") - 5.7) / 2, 3),
        "sheet_vs_frame (pads seat)": {"S4/S8": fwv[("Oven sheet", "Oven sheet S4/S8 (no holes)")]["d_mm"],
                                       "R4": fwv[("Oven sheet", "Oven sheet R4 (rivet holes)")]["d_mm"],
                                       "overlap_mm3": fwv[("Oven sheet", "Oven sheet S4/S8 (no holes)")].get("overlap_mm3")},
        "flush": fw["flush"],
        "overlaps_with_the_frame": [k for k, r in fwv.items() if (r.get("overlap_mm3") or 0) > 0],
        "extreme_stud_positions (63)": cb_margin()}
    c1["verdict"] = ("GF-1.1 (counterbore 7.4 x 9.0): 0 overlap between the frame and every part, with the nominal "
                     "flange 5.5 x 0.7 and with the worst-case 5.7 x 1.4 (S4 / S8 studs 0.2 below the F1-F4 counterbore "
                     "floor, 0.6 at F5-F8; one stud modelled at its extreme positions: flange >= 0.098 from the F1 "
                     "counterbore floor round, >= 0.119 from the walls; the "
                     "pads and the seat ring touch the sheet with 0 overlap = the frame seats). S8 DIN 988 7 x 13 x 1.0 shims: 0.75 "
                     "radial to the 5.5 flange, 0.65 to 5.7 (round 3), flat on the flange front. R4 (round 3): dia-14 large-flange "
                     "heads, rivet shank 0.305 from the slot, 0 overlap. Stage-2 findings F1 / F2 closed. "
                     "No board body touches the frame; PCB 0.080 above the boss / rib / wall tops (copper + mask).")
    c2 = C["2_flushness_and_gaps"]
    g2 = {lv["z"]: lv["g2_glass_edge_to_frame"] for lv in J("offline_asm_gaps.json")["levels"]
          if "g2_glass_edge_to_frame" in lv}
    g1 = {lv["z"]: lv["g1_cutout_edge_to_frame"] for lv in J("offline_asm_gaps.json")["levels"]
          if "g1_cutout_edge_to_frame" in lv}
    c2["g2_note"] = ("GF-1.1 (glass R6.25 in the lip R6.4): sides 0.391 at Z -13.90 / -13.92 (front arris end), 0.374 "
                     "at -12.92, 0.357 at -11.94 (recess narrows 1 deg); corner diagonals 0.494 (front) .. 0.460 (back) "
                     "(GF-1.0: corners = sides); min 3D glass -> frame 0.3563 (side, back arris start)")
    c2["g1_note"] = ("GF-1.1 (cut-out R7.55 round the lip R7.4): sides 0.409 at mid sheet (Z -13.92), 0.336 at Z -13.47 "
                     "(R0.2 lip-root fillet), 0.546 at the lip-top R0.3; corner diagonals 0.512 at mid sheet, 0.439 at "
                     "-13.47 (GF-1.0: corners = sides)")
    c2["corner_vs_side_summary"] = {
        "g2": {str(z): {"sides_min": min(v[0] for s, v in g["by_side"].items() if not s.startswith("corner")),
                        "corner_diagonal": max(v[1] for s, v in g["by_side"].items() if s.startswith("corner"))}
               for z, g in g2.items()},
        "g1": {str(z): {"sides_min": min(v[0] for s, v in g["by_side"].items() if not s.startswith("corner")),
                        "corner_diagonal": max(v[1] for s, v in g["by_side"].items() if s.startswith("corner"))}
               for z, g in g1.items()},
        "target": "~0.40 sides, ~0.50 corners (GF-1.1 item 5)"}
    T = C["4_tails"]["per_tail"]
    C["4_tails"]["verdict"] = (
        "GF-1.1 (pocket side walls +0.3): CTP %.3f (front leg -> side wall x 38.89), TFT %.3f to the side wall, %.3f to "
        "the bottom face (y 147.82), %.3f to the R1.5 bottom corner - all >= 1.5 (target), the bottom beam >= 1.6 so "
        "loop_clr stays 1.5. The model's TFT minimum %.3f is the return leg 0.8 too far forward over the Z 0 rib near "
        "J10 (rigid-shift artefact; %.3f in the v2 position). Print / glass back: CTP %.3f, TFT %.3f; bead: TFT %.2f, "
        "CTP %.2f." % (T["ctp_tail_7"]["to_tail_pocket_side_wall"]["d_mm"],
                       T["tft_tail_5"]["to_tail_pocket_side_wall"]["d_mm"],
                       T["tft_tail_5"]["to_tail_pocket_bottom_face"]["d_mm"],
                       T["tft_tail_5"]["to_tail_pocket_corner_R1.5"]["d_mm"], T["tft_tail_5"]["model_frame_min"],
                       T["tft_tail_5"]["v2_position_frame_min"], T["ctp_tail_7"]["to_print_glass_back"],
                       T["tft_tail_5"]["to_print_glass_back"], T["tft_tail_5"]["to_bead"],
                       T["ctp_tail_7"]["to_bead"]))
    C["5_board"]["note"] = (C["5_board"]["note"] + " Above Z 0 (GF-1.1): %.1f mm3 (tail-pocket walls / trough), 0 "
                            "inside the board outline + 1, nearest 2.663 to the outline." %
                            C["5_board"]["above_Z0_inside_outline_plus_1mm"]["volume_above_Z0_mm3"])
    c6 = C["6_fasteners"]
    c6.pop("weld_flange_vs_slot", None)
    c6["counterbore_GF-1.1"] = {
        "cb_w x cb_l": [P("cb_w"), P("cb_l")], "floor_above_Z_SHEET_BACK": {"F1-F4": P("cb_floor"),
                                                                            "F5-F8": P("cb_floor_mid")},
        "floor_clearance_over_1.4_flange": am["cb_floor_clear_over_1.4_flange"],
        "pad_contact_area_each_mm2": am["pad_contact_area_mm2"],
        "pad_annulus_mm": {"along": am["pad_annulus_min"], "across": am["pad_annulus_across"], "required": 3.0},
        "flange_to_counterbore_extreme_stud (63)": cb_margin(),
        "verdict": "PASS: flange 5.3-5.7 x 0.7-1.4 clears the counterbore at every stud position, pads seat"}
    c6["tape_over_F5-F8_openings_S4 (63)"] = ex_json()["tape_F5-F8"]
    hw = hw_json()
    r4 = hw["R4"]["F1"]
    c6["rivets_R4"]["head"] = ("GF-1.1 round 3: large-flange head dia %.0f x %.1f (DIN 7337 large-flange type K14; "
                               "modelled with an R1.4 edge), head edge %.2f from the cut-out corner arc (axis %.2f); "
                               "pad face under the head %.2f mm2 per F1-F4 (a dia-10 head: %.2f)" %
                               (P("riv_head_d"), P("riv_head_k"), r4["head_edge_to_cut_out_corner_measured"]["d_mm"],
                                r4["axis_to_cut_out_edge"], r4["pad_face_under_head_dia14_mm2"],
                                r4["pad_face_under_head_dia10_mm2 (old head)"]))
    c6["round3_R4_per_position (64)"] = hw["R4"]
    c6["round3_S8_shim (64)"] = hw["S8"]
    c6["round3_d_cut_out_edge (64)"] = hw["d_cut_out_edge"]
    c6["round3_flange_envelope_5.8x1.4_decided (63)"] = {
        f: {n: v for n, v in Jg("extreme_stud_5p8x1p4.json")["studs"][f].items()
            if n not in ("faces", "flange_faces", "shank_faces")} for f in ("F1", "F5")}
    c6["round3_flange_envelope_5.9x1.5 (63)"] = {
        "F1 (F1-F4)": {n: v for n, v in Jg("extreme_stud_5p9x1p5.json")["studs"]["F1"].items()
                       if n not in ("faces", "flange_faces", "shank_faces")},
        "F5 (F5-F8)": {n: v for n, v in Jg("extreme_stud_5p9x1p5.json")["studs"]["F5"].items()
                       if n not in ("faces", "flange_faces", "shank_faces")},
        "verdict": "centred: clear (0.44 to the F1 floor round, 0.10 to the floor); stud pressed against the slot wall / "
                   "end: the 5.9 x 1.5 top edge touches the F1-F4 R0.3 floor round (overlap <= 0.0025 mm3, ~0.04 deep; "
                   "wall 0.024, floor 0.10); F5-F8 clear (wall 0.017, round 0.21, floor 0.5)"}
    c6["washer_bearing_note"] = ("GF-1.1: DIN 9021 M4 80.7 mm2 centred on the dia-12.4 seat inside the coring groove, 76.8 at 0.6 "
                                 "off-centre along the slot, 75.5 at 0.7 across, 65.9 at the slot end (7.6 MPa at 500 N; the "
                                 "washer overhangs the groove off-centre; 6.2 MPa centred); R4 DIN 9021 M5 backing washer "
                                 "88.4 mm2 centred (it does not bridge the groove: its rim r 7.5 ends at the groove outer "
                                 "edge), 97.3 at 0.6 off-centre, 106.8 at the slot end")
    c7 = C["7_chin"]
    c7["free_span"]["tail_pocket_opening_x"] = [round(P("tr_x0") - P("tail_side_add"), 3),
                                                round(P("tr_x1") + P("tail_side_add"), 3)]
    c7["free_span"]["x_span"] = round(P("tr_x1") - P("tr_x0") + 2 * P("tail_side_add"), 3)
    a["renders"] = sorted(f for f in os.listdir(os.path.join(MECH, "renders")) if f.startswith("Fusion_Assembly"))
    a["renders_GF-1.1"] = sorted(f for f in os.listdir(os.path.join(MECH, "renders"))
                                 if f.startswith("Fusion_GF11") or f.startswith("GF11_"))
    a["exports"] = {
        "Rev3.0_GlassFront_Assembly.step": dict(file_info("Rev3.0_GlassFront_Assembly.step"), what=(
            "root, variant S4 as visible, from v%d (59); Fusion omitted the hidden R4 / S8 / socket components and the "
            "hidden R4 sheet body (no 'hidden' / 'Check' / 'R4 (rivet' product in the file)" % EXPORT_VER)),
        "Rev3.0_GlassFront_Glass.step": dict(file_info("Rev3.0_GlassFront_Glass.step"),
                                             what="component Glass (R6.25 corners): glass + 0.02 print layer"),
        "Rev3.0_GlassFront.f3d": dict(file_info("Rev3.0_GlassFront.f3d"),
                                      what="Fusion archive of the whole document, v%d (round 3 hardware)" % F3D_VER),
        "Rev3.0_GlassFront_Frame.step": dict(file_info("Rev3.0_GlassFront_Frame.step", sha=True),
                                             what="frame, from v%d (59 = 25 verbatim)" % EXPORT_VER),
        "Rev3.0_GlassFront_Frame.stl": dict(file_info("Rev3.0_GlassFront_Frame.stl"), what="frame, from v%d" %
                                            EXPORT_VER)}
    tp = ex_json()["tape_F5-F8"]
    a["findings"] = [
        {"id": "F1", "status": "CLOSED in GF-1.1", "what": "CD weld stud flange vs the fastener slot",
         "now": "7.4 x 9.0 counterbore (slot + 1.0 per side), floor 1.6 / 2.0: 0 overlap with 5.7 x 1.4, also with the "
                "stud at its extreme positions; margins in checks.6"},
        {"id": "F2", "status": "CLOSED in GF-1.1", "what": "S8 spacer could not pass the weld flange",
         "now": "DIN 988 7 x 13 x 1.0 (round 3; first GF-1.1 build 6 x 12): 0.75 / 0.65 radial to the 5.5 / 5.7 "
                "flange, %.2f mm2 on the flange front" % hw_json()["S8"]["F5"]["contact_on_flange_front_mm2"]},
        {"id": "F7", "status": "CLOSED in round 3", "what": "R4 dia-10 rivet head over the counterbore",
         "now": "the counterbore left 23.7 mm2 of pad face under a dia-10 head; large-flange dia-14 head (K14): 99.1 mm2"},
        {"id": "F8", "status": "CLOSED (lead decision, round 3): stud spec tightened, frame frozen",
         "what": "weld flange + collar envelope",
         "numbers": "dia 5.9 x 1.5 touches the F1-F4 R0.3 counterbore floor round when the stud is pressed against the "
                    "slot wall (<= 0.0025 mm3, ~0.04 deep); clear when centred",
         "now": "params: after welding, flange incl. weld collar / flash within dia 5.8 x 1.4 and stud axis within +-0.3 "
                "of nominal relative to the cut-out; measured at the extreme stud positions (63): F1-F4 %.3f wall / %.3f "
                "floor round / %.2f floor, F5-F8 %.3f / %.3f / %.2f, no overlap" % tuple(
                    min(v["flange_to_" + k]["d_mm"] for v in Jg("extreme_stud_5p8x1p4.json")["studs"][f].values()
                        if isinstance(v, dict) and "offset_mm" in v)
                    for f in ("F1", "F5") for k in ("wall", "floor_round", "floor"))},
        {"id": "F3", "status": "OPEN (assembly rule)", "what": "Q1 lead length (carried over from v2)",
         "numbers": "untrimmed leads reach Z -8.115: 0.539 mm3 through the Formex, 2.612 mm3 into the LCM",
         "smallest_change": "keep the v2 rule: trim Q1 leads to <= 2.5 below the PCB back (2.10 to the Formex)"},
        {"id": "F4", "status": "IMPROVED in GF-1.1", "what": "tail clearance margin",
         "numbers": "CTP 1.830, TFT 1.832 side walls, 1.763 bottom face (GF-1.0: 1.530 / 1.532)"},
        {"id": "F5", "status": "info", "what": "panel model", "numbers": "LCM back at Z -5.805: Formex gap 0.805"},
        {"id": "F6", "status": "info (GF-1.1)", "what": "VHB tape over the F5-F8 counterbores (S4)",
         "numbers": "at F5-F8 the S4 tape strip spans the 7.4 x 9.0 counterbore opening (%.2f mm2 over air each, "
                    "measured) instead of the 5.4 x 7.0 slot (%.2f): %.1f mm2 less bonded flange front in total, "
                    "%.2f %% of the 7903 mm2 of tape" % (tp["F5"]["over_air_mm2"],
                                                         tp["reference_at_flange_front"]["slot_5.4x7.0_GF-1.0_mm2"],
                                                         tp["lost_vs_GF-1.0_total_mm2"],
                                                         100 * tp["lost_vs_GF-1.0_total_mm2"] / 7903.4)}]
    a["frozen_parameter_issues"] = []
    a["frozen_parameter_note"] = ("GF-1.1 master (Rev3.0_GlassFront_params.json, change_log) carries the counterbore, "
                                  "coring, H6, tail pocket, R_glass / R_frame / R_cut, tube_sw_r and DIN 988 spacer")
    hw = hw_json()
    a["round_3"] = {
        "scope": "hardware bodies of the hidden variants + params only; frame frozen (fingerprint checked by 64 / 65), "
                 "frame STEP / STL not re-exported, assembly STEP not re-exported (only hidden R4 / S8 bodies changed)",
        "parameters": {"riv_head_d": P("riv_head_d"), "riv_head_k": P("riv_head_k"), "spacer_id": P("spacer_id"),
                       "spacer_od": P("spacer_od")},
        "frame_fingerprint": hw["frame_fingerprint (unchanged)"],
        "clearance_pocket_reference": hw["pocket"], "formex_as_modelled": hw["formex"],
        "params_file": file_info("Rev3.0_GlassFront_params.json", sha=True)}
    pe = os.path.join(MECH, "Rev3.0_GlassFront_Frame_report_errata.json")
    if os.path.exists(pe):                     # round 4: the verified Frame report is not rewritten, errata instead
        a["frame_report_errata"] = dict(json.load(open(pe, encoding="utf-8")),
                                        file="Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report_errata.json")
    return a


def main():
    fr2, as2 = backups()
    doc = J("docinfo_asm.json")
    pv = {p["name"]: p for p in doc["user_parameters"]}
    am = Jg("as_modelled.json")
    prm = json.load(open(PARAMS, encoding="utf-8"))
    if not str(prm.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("run gf11_params_update.py first")
    fr = None if ASSEMBLY_ONLY else frame_report(fr2, doc, pv, am, prm)
    a = assembly_report(as2, doc, pv, am, fr)
    if not ASSEMBLY_ONLY:                      # round 3: the frame is frozen, its report is left as written in round 2
        json.dump(fr, open(FR_OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(a, open(AS_OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for p in (FR_OUT, AS_OUT):
        json.load(open(p, encoding="utf-8"))
    print("written", FR_OUT, os.path.getsize(FR_OUT), AS_OUT, os.path.getsize(AS_OUT))


if __name__ == "__main__":
    main()
