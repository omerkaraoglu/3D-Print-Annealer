"""Assemble Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2_params.json from the outputs of the Fusion scripts
(scratchpad JSONs written by fusion/13, 17, 33-35, 39) and the offline calcs (hole_pattern_calc.py, fit_analyse.py).

Run after: fusion/39_frame_doc_report.py, fit_analyse.py, fit_analyse.py --parts, hole_pattern_calc.py --json.
"""
import json
import math
import os

SCR = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad")
HERE = os.path.dirname(os.path.abspath(__file__))
MECH = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Mechanical\Rev3.0_Frame"
EARS = {"H1": (30.0, 14.2), "H2": (93.0, 14.2), "H3": (174.0, 14.2), "H4": (189.8, 30.0), "H5": (189.8, 109.0),
        "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0), "H9": (15.2, 30.0)}
DOCS = {"project": "Oven (hub1, id a.YnVzaW5lc3M6ZWxla3Ryb21hZyMyMDI2MDMyNTEwNjk5OTY2MDE)",
        "folder": "Rev3.0 OVEN CONTROLLER (urn:adsk.wipprod:fs.folder:co.Fb1A0vSrQeCBrk8-kXBLeg)",
        "frame_document": "Rev3.0 Frame v2 (lineage urn:adsk.wipprod:dm.lineage:Y0nsfIZjQf-aVqUUyxdWYQ)",
        "assembly_document": "Rev3.0 Frame v2 fit assembly"}


def load(name, base=SCR):
    return json.load(open(os.path.join(base, name)))


def main():
    fr = load("frame_doc_report.json")
    pre = load("scan_pre_fillet.json")            # v2.0 pre-fillet scan (geometry before fillets, for reference)
    post = load("scan_post_fillet_v22.json")
    ribs = load("rib_pad_result.json", HERE)
    az0 = load("above_z0_check.json")
    hp = load("hole_pattern_result.json", HERE)
    fs = load("fit_summary.json")
    fp = load("fit_parts_summary.json")
    P = {p["name"]: p for p in fr["params"]}

    levels = {k: P[k]["value"] for k in ("Z_PCB", "Z_PANEL_BACK", "Z_SEAT", "Z_SHELF_BACK", "Z_GLASS", "Z_FRONT",
                                         "Z_FLANGE_BACK", "Z_STUD_TOP", "Z_CELL_FLOOR", "Z_CELL_RIB_TOP",
                                         "Z_TROUGH_TOP")}
    runs = hp["runs"]
    holes = []
    for h in hp["holes"]:
        n = h["name"]
        prev = [r for r in runs if r["to"] == n][0]
        nxt = [r for r in runs if r["from"] == n][0]
        ears = sorted((math.hypot(h["x"] - x, h["y"] - y), e) for e, (x, y) in EARS.items())
        side = "T" if abs(h["y"] - 8.75) < 1e-6 else ("B" if abs(h["y"] - 161.2) < 1e-6 else ("L" if h["x"] < 100 else "R"))
        th = [t for t in hp["slot_axes_thermal"] if t["name"] == n][0]
        holes.append({"name": n, "side": side, "slot_axis": th["slot_axis"], "slot_axis_deg": th["slot_axis_deg"],
                      "slot_axis_note": "unit vector / angle from +X, KiCad abs coords (y down), radial from the datum",
                      "r_from_datum_mm": th["r_from_datum_mm"],
                      "thermal_move_dT60_70ppm_datum_case_mm": th["move_datum_case_mm"],
                      "slot_travel_available_mm": th["travel_available_mm"],
                      "across_slot_clearance_mm": th["across_clearance_mm"],
                      "P1_fixed_case_along_mm": th["move_P1_fixed_along_mm"],
                      "P1_fixed_case_across_mm": th["move_P1_fixed_across_mm"],
                      "slot_width_mm": P["stud_hole"]["value"],
                      "slot_length_mm": round(P["stud_hole"]["value"] + P["stud_slot"]["value"], 3),
                      "x_abs": round(P[n.lower() + "_x"]["value"], 3),
                      "y_abs_down": round(P[n.lower() + "_y"]["value"], 3),
                      "Y_model": round(-P[n.lower() + "_y"]["value"], 3),
                      "param_x": n.lower() + "_x", "param_y": n.lower() + "_y",
                      "nearest_ear_hole": ears[0][1], "d_nearest_ear_hole_mm": round(ears[0][0], 2),
                      "d_pcb_outline_mm": h["d_pcb_outline_mm"],
                      "d_corner_arc_start_along_edge_mm": h["d_corner_arc_start_mm"],
                      "d_tail_loop_envelope_mm": h["d_tail_loop_env_mm"],
                      "span_to_previous_mm": prev["span_mm"], "previous": prev["from"],
                      "span_to_next_mm": nxt["span_mm"], "next": nxt["to"]})
    sl = post["slivers"]
    orig_sl = [s for s in sl if s["type"] in ("planar_drafted", "flat_perp_Z", "cone", "planar_UNDRAFTED")]
    out = {
        "_about": "Rev3.0 OVEN CONTROLLER carrier frame v2 (continuous flange, 10 M4 stud bosses). Built natively "
                  "in Fusion 360 by Design Reports/Rev3.0/tools/frame_v2/fusion/NN_*.py. Units mm / deg. Plan "
                  "coordinates abs KiCad (x, y down); model Y = -y; Z = 0 at the physical PCB back.",
        "documents": DOCS, "frame_document_version": fr["version"],
        "files": {"step": os.path.join(MECH, "Rev3.0_Frame_v2.step"), "stl": os.path.join(MECH, "Rev3.0_Frame_v2.stl"),
                  "f3d": os.path.join(MECH, "Rev3.0_Frame_v2.f3d"), "renders": os.path.join(MECH, "renders_v2")},
        "revision": "v2.2 final (2026-11-13; frame v6 FINAL, assembly v6 with both sheet peg holes X-slots): v2.1 (socket rule 6.5/11.0, symmetric 7.5/14, slots 4.5 x 5.3, tail walls "
                    "stepped at y 129, ribs to the shelf edge, hole shift) + stud tubes 5 above the flange back "
                    "(seat Z -3.52, full-height ribs, PEM FH-M4-18), pegs on the side flanges, radial slots",
        "user_parameters": fr["params"],
        "derived_levels_mm": levels,
        "stud_holes": holes,
        "stud_hole_count": len(holes),
        "stud_slot": P["stud_slot"]["value"], "tail_wall_step_y": P["tail_wall_step_y"]["value"],
        "datum": {"datum_x": P["datum_x"]["value"], "datum_y": P["datum_y"]["value"],
                  "note": "midpoint of the side pegs; stud slot axes radial from it"},
        "thermal": {"alpha_rel_per_K": 58e-6, "dT_K": 60, "peg_to_peg_growth_mm": hp["peg_to_peg_growth_mm"],
                    "sheet_P1": "slot 3.2 x 3.9 along X", "sheet_P2": "slot 3.2 x 3.9 along X",
                    "kinematics_note": "v2.2 final (owner decision): both sheet peg holes are X-slots, so the pegs fix "
                                       "only the y = 69.5 line and the rotation; x is located by the stud slots "
                                       "themselves (FH2/FH7 radial = Y-slots, 0.25 across-clearance in x) -> the frame "
                                       "grows about the pattern centre within +-0.25 and the datum case applies; "
                                       "peg-to-peg growth 0.645 is shared by the two slots (0.35 travel each). "
                                       "P1_fixed_case_* columns kept for reference only (superseded)",
                    "glass_location": "y +-0.1 by the pegs (dia 3 in 3.2-wide slots), x +-0.25 by the studs"},
        "oven_sheet": {"thickness_mm": 1.0, "material": "steel", "window": "VA + 0.5 per side, R1",
                       "stud_holes": "10 x round dia 4.3 (PEM FH-M4-18 clinch studs) at fh1..fh10",
                       "peg_holes": "P1 and P2: slot 3.2 x 3.9 along X (sheet_peg_hole 3.2 + sheet_peg_slot 0.7)",
                       "peg_positions_abs": [[9.77, 69.5], [195.17, 69.5]]},
        "stud_bending_T_section": hp["stud_bending"],
        "stud_hole_geometry": {"slot_width_at_Z_FRONT": P["stud_hole"]["value"],
                               "slot_length_at_Z_FRONT": round(P["stud_hole"]["value"] + P["stud_slot"]["value"], 3),
                               "slot_axis": "radial from the datum (datum_x, datum_y)",
                               "stud_boss_h_semantics": "tube height ABOVE THE FLANGE BACK (v2.2)",
                               "tube_top_Z_STUD_TOP": P["Z_STUD_TOP"]["value"],
                               "stack_from_sheet_mm": "7.5 frame + 1.0 DIN 9021 washer + 5 M4 nyloc = 13.5",
                               "stud_spec": "PEM FH-M4-18 (self-clinching stud, 18 mm)",
                               "rib": "one radial rib per tube, rib 1.5, full tube height (flange back -> tube top), 1 deg",
                               "hole_draft_deg": P["draft_loc"]["value"],
                               "tube_od_top": P["stud_boss_od"]["value"], "tube_top_Z": levels["Z_STUD_TOP"],
                               "tube_draft_deg": P["draft"]["value"], "rib_per_tube": 1, "gussets": 0,
                               "stud_offset_all_sides": P["stud_offset"]["value"],
                               "flange_w_all_sides": P["flange_w"]["value"]},
        "support_ribs": {"rule": "v1 positions/widths; free ends run to the shelf edge (window face) and, over the "
                                 "tail pocket, to the shelf end, trimmed flush by those cuts; kept at v1 length if a "
                                 "B.Cu pad would come closer than 1.0 mm",
                         "kept_v1_length": ribs["kept_v1_length"], "rib_to_pad_min_mm": ribs["rib_to_pad_min_mm"],
                         "rib_to_pad_min_pad": ribs["rib_to_pad_min_pad"], "rib_to_pad_min_rib": ribs["rib_to_pad_min_rib"],
                         "per_rib": ribs["ribs"]},
        "pegs": [{"name": "P1", "x_abs": P["peg1_x"]["value"], "y_abs_down": P["peg1_y"]["value"],
                  "where": "left flange front face, on the stud line", "dia_mm": 3.0, "height_mm": 0.8,
                  "draft_deg": 0.5, "sheet_hole": "slot 3.2 x 3.9 along X"},
                 {"name": "P2", "x_abs": P["peg2_x"]["value"], "y_abs_down": P["peg2_y"]["value"],
                  "where": "right flange front face, on the stud line", "dia_mm": 3.0, "height_mm": 0.8,
                  "draft_deg": 0.5, "sheet_hole": "slot 3.2 x 3.9 along X"}],
        "body": {"name": fr["body"], "volume_cm3": fr["volume_cm3"],
                 "mass_g_at_1.36_g_cm3": round(fr["volume_cm3"] * 1.36, 2), "faces": fr["faces"],
                 "bbox_abs": post["bbox_abs"], "timeline_count": fr["timeline_count"],
                 "timeline_unhealthy": fr["timeline_unhealthy"],
                 "features": [n for n in fr["timeline"] if not n.endswith("sketch") and not n.endswith("plane")]},
        "lift_calc": {"method": "unfolded stud-line runs, simply supported, gasket line load where the glass edge "
                                "runs alongside (exact) + uniform-share upper bound; I about own centroid",
                      "section": hp["section"], "q_nom_N_per_mm": hp["q_nom_N_per_mm"],
                      "q_max_N_per_mm": hp["q_max_N_per_mm"], "criterion_um": hp["criterion_lift_1000h_nom_um"],
                      "worst_nominal_1000h_um_exact": hp["worst_lift_nom_1000h_um"],
                      "worst_nominal_1000h_um_uniform_upper_bound": hp["worst_lift_nom_1000h_uniform_upper_bound_um"],
                      "worst_straight_run_uniform_um": hp["worst_straight_run_uniform_um"],
                      "runs": runs, "pass": hp["pass"],
                      "eight_hole_result": "v2.1 rules (6.5 from outline, 11.0 from H1..H9, 15 from corners): best "
                                           "8-hole layout 178.1 um exact (T2 R2 L2 B2) > 90 -> 10 holes (v2.0: 219 um)"},
        "checks": {
            "frame_vs_pcb_solid": fs["pcb_solid"],
            "frame_vs_components": {"bodies": fs["n_component_bodies"], "min_mm": fs["components_min_mm"],
                                    "closest_15": [{k: r[k] for k in ("ref", "part", "d_mm", "zmin", "p_frame")}
                                                   for r in fs["closest_components_15"]],
                                    "intersections": fs["intersections"]},
            "frame_vs_panel_parts": [{"part": r["part"], "d_mm": r["d_mm"], "p_frame": r["p_frame"]}
                                     for r in fs["panel_parts"]],
            "formex_sheet_vs_frame": fp["Formex sheet vs frame"],
            "gasket_vs_frame": fp["Gasket (compressed) vs frame"],
            "oven_sheet_patch_vs_frame": fp["Oven sheet patch vs frame"],
            "lead_tips_vs_formex_sheet": fp["lead_tips_vs_formex_sheet"],
            "q1_note": "Q1 TO-220 as modelled has untrimmed 8.1 mm leads (zmin -8.115): 0.54 mm3 through the "
                       "Formex sheet; trimmed to <= 2.5 mm (mandatory assembly step) -> 2.10 mm to the sheet. "
                       "Q1 to the frame: 32.72 mm.",
            "tool_access_dia12_Zm4.0_to_45_all_board_bodies_incl_DS1": fp["tool_access"],
            "socket_vs_frame_faces_above_washer_top_Zm2.52": fp.get("socket_vs_frame_wall_and_bosses"),
            "wire_stubs_J3_J4_R1_min_plan_gap_to_socket_mm": 7.0,
            "nothing_above_Z0_in_outline_plus_1mm": az0,
            "scans_pre_fillet_v2_0": {"faces": pre["faces"], "slivers": len(pre["slivers"]), "draft_flags": len(pre["flags"]),
                                 "counts": pre["counts"]},
            "scans_post_fillet": {"faces": post["faces"], "draft_flags": post["flags"], "counts": post["counts"],
                                  "sliver_rule_hits_total": len(sl), "sliver_rule_hits_original_faces": len(orig_sl),
                                  "sliver_rule_hits_are_fillet_blend_patches_max_area_mm2":
                                      max(s["area"] for s in sl) if sl else None,
                                  "min_area_mm2": post["min_area"], "min_2a_over_p_mm": post["min_2a_p"],
                                  "thin_strips_lt_1mm": len(post["thin_strips_lt_1mm"]),
                                  "thin_strip_widths": sorted(set(t["width_mm"] for t in post["thin_strips_lt_1mm"])),
                                  "unfilleted_concave_roots": post["unfilleted_concave_roots"]},
            "faces_at_Z_PCB": fr["faces_at_Z_PCB"],
            "creepage": {"closest_mains_copper_to_contact_mm": ribs["mains_to_frame_contact_min_mm"],
                         "closest_mains_copper": ribs["mains_to_frame_contact"],
                         "creepage_mm": ribs["creepage_mains_to_panel_mm"], "creepage_req_mm": 6.4,
                         "clearance_mm": ribs["clearance_mains_to_panel_mm"], "clearance_req_mm": 4.0,
                         "note": "v1 method; extended ribs remove the 0.5 shelf land from the path (v2.0: 8.52 mm)"},
            "unfilleted_roots_accepted_by_owner": 4,
            "tail_corner_R0_3_attempt": "R0.3 fillet on the 2 tail-pocket corners rose to Z -1.919 (0.18 above the "
                                        "shelf back, tight edge/face sampling) -> deleted, corners stay sharp",
            "fillet_feature_count": sum(1 for n in fr["timeline"] if n.startswith("Root fillets")),
        },
    }
    p = os.path.join(MECH, "Rev3.0_Frame_v2_params.json")
    json.dump(out, open(p, "w"), indent=1)
    print("written", p, len(out["user_parameters"]), "params,", len(holes), "holes")


if __name__ == "__main__":
    main()
