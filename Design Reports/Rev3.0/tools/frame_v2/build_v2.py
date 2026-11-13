"""Verify the Rev3.0 carrier frame from its STEP + params JSON: CAD checks, fit check, hand calculations,
renders, sections, drawing and sheet DXF, then out/summary.json.

  <venv>/Scripts/python.exe build_v2.py                      v2: Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2.step + _params.json
  <venv>/Scripts/python.exe build_v2.py --v1                 regression run on the v1 STEP + v1_params.json
  options: --frame <step>  --params <json>  --board <board STEP>  --export-board  --no-render
           --out <dir> (JSON outputs)  --img <dir> (PNGs)

Steps: (1) frame STEP + params (+ sanity: bbox vs body outline, flange plane, params' own body stats), (2) cadcheck,
(3) fitcheck (board STEP, cached in this process), (4) calc, (5) renders, sections, drawing + DXF, (6) summary.json,
and with --v1 (7) the regression table against v1's own results (tools/frame/out/fitcheck.json, calc.json, or
the reference numbers embedded below if the v1 folder has moved).
Outputs: v2 -> out/*.json, Mechanical/Rev3.0_Frame/renders_v2/*.png, Mechanical/Rev3.0_Frame/Rev3.0_FrontSheet_Pattern_v2.dxf
         --v1 -> out/v1/*.json, renders_v2/v1_regression/*
"""
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common_v2 as C
import cadcheck_v2
import fitcheck_v2
import calc_v2

V1_OUT = os.path.normpath(os.path.join(HERE, r"..\frame\out"))
V1_REF = {   # v1 reference results (tools/frame/out, build of 2026-11-13) - used if the v1 folder is gone
    "component_overlaps": 0, "closest_component": ["F3", 1.268], "tail_min": 1.554, "panel_min": 0.15,
    "pcb_dist": 0.08, "rib_pad_min": [1.32, "J3.1"], "boss_pad_min": [4.46, "J2.1"], "mains_contact": 1.32,
    "creepage": 8.52, "clearance": 6.70, "slivers": [0, 342], "gasket_dist": 0.607, "sheet_overlap": 0.0,
    "oven_overlap": 0.0, "ps1_gap_to_sheet": 1.33, "I_mm4": 309, "top_span": 59.7, "lift_1000h_nom_um": 95.6,
    "stud_bearing_real_MPa": 9.1, "boss_bearing_cons_MPa": 16.3, "gasket_force_max_N": 591, "volume_cm3": 32.5,
}


def v1_reference():
    ref = dict(V1_REF)
    src = "embedded"
    try:
        fit = json.load(open(os.path.join(V1_OUT, "fitcheck.json")))
        summ = json.load(open(os.path.join(V1_OUT, "summary.json")))
        calc = json.load(open(os.path.join(V1_OUT, "calc.json")))
        cc = fit["closest_components"][0]
        ref.update({"component_overlaps": len(fit["component_overlaps"]), "closest_component": [cc["ref"], cc["min_dist"]],
                    "tail_min": fit["tail_min_dist"], "panel_min": fit["panel_min_dist"],
                    "pcb_dist": fit["pcb_body"]["min_dist"], "rib_pad_min": fit["plan"]["rib_to_pad_min"],
                    "boss_pad_min": fit["plan"]["boss_to_pad_min"],
                    "mains_contact": fit["plan"]["mains_to_frame_contact_min"][0],
                    "creepage": fit["plan"]["creepage_mains_to_panel_mm"],
                    "clearance": fit["plan"]["clearance_mains_to_panel_mm"],
                    "slivers": [len(summ["fit"]["slivers"]["slivers"]), summ["fit"]["slivers"]["faces"]],
                    "gasket_dist": fit["gasket_vs_frame"]["min_dist"], "sheet_overlap": fit["sheet_vs_frame"]["overlap_mm3"],
                    "oven_overlap": summ["fit"]["oven_sheet_vs_frame_overlap_mm3"],
                    "ps1_gap_to_sheet": next(r["gap_to_sheet"] for r in fit["lead_protrusions"] if r["ref"] == "PS1"),
                    "I_mm4": calc["frame_beam"]["I_mm4"], "top_span": calc["frame_beam"]["span_mm"],
                    "lift_1000h_nom_um": calc["frame_beam"]["nom"]["lift_1000h_um"],
                    "stud_bearing_real_MPa": calc["feet"]["bearing_real_MPa"],
                    "boss_bearing_cons_MPa": calc["boss"]["bearing_cons_MPa"],
                    "gasket_force_max_N": calc["gasket"]["force_max_N"], "volume_cm3": summ["frame"]["volume_cm3"]})
        src = V1_OUT
    except Exception:
        pass
    return ref, src


def regression(fit, cad, calc, info):
    """rows: (quantity, v1 reference, v2 toolchain, |diff| <= 0.01, why)"""
    ref, src = v1_reference()
    f3, pl = fit["fit3d"], fit["plan"]
    cc = f3["closest_components"][0]
    ps1 = next((r for r in f3["lead_protrusions"] if r["ref"] == "PS1"), None)
    top = [r for r in calc["beam"]["runs"] if r["edge"] == "top"]
    tmax = max(top, key=lambda r: r["span_mm"]) if top else None
    bk_fp = pl["footprint"]["pad_min_by_kind"]
    bk_ct = pl["contact"]["pad_min_by_kind"]
    rows = []

    def row(q, r, m, why="", tol=0.01, num=True):
        ok = (abs(float(r) - float(m)) <= tol) if num else (r == m)
        rows.append({"quantity": q, "v1": r, "v2_toolchain": m, "match": ok, "why": "" if ok else why})
    row("component overlaps", ref["component_overlaps"], len(f3["component_overlaps"]), num=False)
    row("closest component (%s)" % ref["closest_component"][0], ref["closest_component"][1], cc["min_dist"])
    row("closest component ref", ref["closest_component"][0], cc["ref"], num=False)
    row("FPC tails min", ref["tail_min"], f3["tail_min_dist"])
    row("panel min", ref["panel_min"], f3["panel_min_dist"])
    row("PCB body distance", ref["pcb_dist"], f3["pcb_body"]["min_dist"])
    row("ribs vs B.Cu pads (footprint at the rib base, as v1)", ref["rib_pad_min"][0], bk_fp["rib"][0])
    row("  pad", ref["rib_pad_min"][1], bk_fp["rib"][1], num=False)
    row("ribs vs B.Cu pads (Z 0 contact faces of the STEP)", ref["rib_pad_min"][0], bk_ct["rib"][0],
        "the STEP's rib tops are drafted 1 deg over 2.1 mm: 0.037 mm per side narrower than v1's nominal rib rectangle "
        "(v1 checked the rib base); the footprint row reproduces v1")
    if "boss" in bk_ct:
        row("bosses vs B.Cu pads (Z 0 contact faces)", ref["boss_pad_min"][0], bk_ct["boss"][0],
            "v1 measured to the full dia-8 circle, including the part merged into the outer wall; the STEP exposes "
            "only the outer arc of H8/H9, so J2.1 is nearest to a rib (2.49) and the nearest exposed boss arc is "
            "at F3.2", tol=0.01)
    row("mains copper -> frame contact (footprint)", ref["mains_contact"], pl["footprint"]["mains_to_frame_min"][0])
    row("creepage mains -> panel (footprint)", ref["creepage"], pl["footprint"]["creepage_mains_to_panel_mm"])
    row("creepage mains -> panel (Z 0 contact)", ref["creepage"], pl["contact"]["creepage_mains_to_panel_mm"],
        "+0.05 from the drafted rib top (see above)")
    row("clearance mains -> panel", ref["clearance"], pl["clearance_mains_to_panel_mm"])
    row("sliver faces", "%d of %d" % tuple(ref["slivers"]), "%d of %d" % (len(cad["slivers"]["slivers"]),
                                                                         cad["slivers"]["faces"]), num=False)
    row("gasket vs frame", ref["gasket_dist"], f3["gasket_vs_frame"]["min_dist"])
    row("Formex sheet overlap mm3", ref["sheet_overlap"], f3["sheet_vs_frame"]["overlap_mm3"])
    row("oven-sheet patch overlap mm3", ref["oven_overlap"], f3["oven_sheet_vs_frame"]["overlap_mm3"])
    if ps1:
        row("PS1 leads gap to the Formex sheet", ref["ps1_gap_to_sheet"], ps1["gap_to_sheet"])
    row("frame volume cm3", ref["volume_cm3"], info["volume_cm3"], tol=0.05)
    row("beam I (analytic) mm4", ref["I_mm4"], calc["beam"]["section"]["I_mm4"], tol=0.5)
    if tmax:
        row("longest top span mm", ref["top_span"], tmax["span_mm"],
            "corners count as supports (brief): F1 at x 13 sits outside the body corner (17.27), so the F1-F2 run is "
            "55.4; the longest top run is F2-F3 = 59.6 (v1 took F1-F2 = 72.7 - 13 = 59.7)")
        row("top lift 1000 h nominal um (full q, analytic I)", ref["lift_1000h_nom_um"], tmax["nom"]["lift_1000h_um"],
            "span 59.6 instead of 59.7 (L^4)", tol=0.05)
    row("stud tube bearing real MPa", ref["stud_bearing_real_MPa"], calc["studs"]["bearing_real_MPa"],
        "bearing area measured on the STEP: F2/F3 tubes merge into the wall, the free ring is 53.9 mm2, not the "
        "nominal 55.0", tol=0.05)
    row("PCB boss bearing (cons) MPa", ref["boss_bearing_cons_MPa"], calc["boss"]["bearing_cons_MPa"], tol=0.05)
    row("gasket force max N", ref["gasket_force_max_N"], calc["gasket"]["force_max_N"], tol=0.5)
    return {"reference": src, "rows": rows, "all_match": all(r["match"] for r in rows),
            "explained": all(r["match"] or r["why"] for r in rows)}


def find_keys(node, rx, path="", out=None, limit=60):
    """(path, value) of every key matching rx in the params JSON (e.g. the per-rib reach), for the summary"""
    import re
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            p = path + "." + str(k) if path else str(k)
            if re.search(rx, str(k), re.I) and len(out) < limit:
                out.append([p, v])
            find_keys(v, rx, p, out, limit)
    elif isinstance(node, list):
        for i, e in enumerate(node):
            nm = e.get("name") if isinstance(e, dict) else None
            if nm and re.search(rx, str(nm), re.I) and "value" in e and len(out) < limit:
                out.append([path + "[" + str(nm) + "]", e["value"]])
            find_keys(e, rx, "%s[%d]" % (path, i), out, limit)
    return out


def sanity(ctx):
    """frame STEP vs params: body outline inside the bbox, flange plane = bbox zmin (pegs aside), params' own stats"""
    D, info = ctx.D, ctx.frame_info
    bb = info["bbox_model"]
    x0, x1, y0, y1 = D.OUTER
    notes = []
    if not (bb[0] <= x0 + 0.5 and bb[1] >= x1 - 0.5 and bb[2] <= -y1 + 0.5 and bb[3] >= -y0 - 0.5):
        notes.append("frame bbox %s does not contain the body outline OUTER %s (abs): coordinate frame?" % (bb, D.OUTER))
    zmin_expected = D.Z_FRONT - (D.PEG_H if D.PEGS else 0)
    if abs(bb[4] - zmin_expected) > 0.05:
        notes.append("frame zmin %.3f, expected %.3f (Z_FRONT - peg height)" % (bb[4], zmin_expected))
    body = ctx.P.raw.get("body") or ctx.P.raw.get("body_stats") or {}
    vol = next((v for k, v in body.items() if "volume" in k.lower() and isinstance(v, (int, float))), None)
    if vol:
        v = vol / 1000 if vol > 1000 else vol         # mm3 or cm3
        if abs(v - info["volume_cm3"]) > 0.01 * info["volume_cm3"]:
            notes.append("params body volume %.3f cm3 vs STEP %.3f cm3" % (v, info["volume_cm3"]))
    return {"ok": not notes, "notes": notes}


def verdicts(fit, cad, calc, info, san):
    v = {"single valid solid": info["valid"] and info["single_solid"],
         "STEP matches params (bbox, flange plane, volume)": san["ok"],
         "slivers (owner rule)": cad["slivers"]["ok"],
         "slivers other than root-fillet corner blends": cad["slivers"]["ok_excluding_fillet_blends"],
         "thin walls / slots < 1.0": cad["thin"]["ok"],
         "flange face flat, only pegs proud": cad["flange_face"]["ok"],
         "features found at the params positions": cad["features"]["ok"],
         "components / PCB / panel / tails / sheet / oven fit": bool(
             not fit["fit3d"]["component_overlaps"] and fit["fit3d"]["tail_min_dist"] >= fitcheck_v2.TAIL_MIN
             and fit["fit3d"]["panel_overlap_mm3"] < 1e-4 and fit["fit3d"]["oven_sheet_vs_frame"]["overlap_mm3"] < 1e-3),
         "contact patches vs pads, creepage, clearance": fit["plan"]["ok"],
         "tool access (socket vs board)": fit["tool_access"]["ok"],
         "washer + socket vs frame": fit["washer_vs_frame"]["ok"],
         "nothing above Z 0 within board + 1 mm": fit["above_pcb"]["ok"],
         "stud tube bearing <= creep allowance": calc["studs"]["bearing_ok"],
         "flange bending (realistic case c)": calc["flange"]["cases"]["c_realistic_lever_from_tube_face"]["ok"],
         "flange bending (brief case a, conservative)": calc["flange"]["cases"]["a_plate_OD_lever_offset"]["ok"],
         "beam lift (1000 h, nominal) <= limit": calc["beam"]["ok"],
         "thermal: every stud covered by its hole / slot (from the fixed point)": not calc["thermal"]["holes_to_slot"],
         "thermal: peg holes absorb the peg-to-peg growth": calc["thermal"].get("pegs", {}).get("ok", True)}
    if "d_T_section_measured_rib" in calc["flange"]["cases"]:
        v["flange bending, T-section with the measured rib (case d)"] = calc["flange"]["cases"]["d_T_section_measured_rib"]["ok"]
    if "b_plate_plus_rib" in calc["flange"]["cases"]:
        v["flange bending (with radial rib, case b)"] = calc["flange"]["cases"]["b_plate_plus_rib"]["ok"]
    return v


def main(argv):
    t0 = time.time()
    ctx = C.Context(argv)
    C.log("Rev3.0 carrier frame %s verification" % ctx.tag)
    C.log("  frame : %s" % ctx.frame_path)
    C.log("  params: %s" % ctx.params_path)
    C.log("  board : %s" % ctx.board_path)
    for p in (ctx.frame_path, ctx.params_path):
        if not os.path.exists(p):
            C.log("MISSING INPUT: %s" % p)
            return None
    C.log("[1] frame STEP + params")
    fr = ctx.frame
    info = ctx.frame_info
    D = ctx.D
    C.log("    solids %d valid %s volume %.3f cm3 faces %d bbox %s" % (info["solids"], info["valid"], info["volume_cm3"],
                                                                      info["faces"], info["bbox_model"]))
    san = sanity(ctx)
    for n in san["notes"] + ctx.P.notes:
        C.log("    NOTE: " + n)
    if ctx.P.defaults_used:
        C.log("    defaults used (not in the params JSON): %s" % sorted(set(ctx.P.defaults_used)))
    times = {}
    t = time.time(); C.log("[2] cadcheck"); cad = cadcheck_v2.run(ctx); times["cadcheck"] = round(time.time() - t, 1)
    t = time.time(); C.log("[3] fitcheck"); fit = fitcheck_v2.run(ctx); times["fitcheck"] = round(time.time() - t, 1)
    t = time.time(); C.log("[4] calc"); calc = calc_v2.run(ctx, cad["features"]); times["calc"] = round(time.time() - t, 1)
    files = {}
    if ctx.render:
        import render_v2, sections_v2, drawing_v2
        t = time.time(); C.log("[5] renders, sections, drawing")
        files.update(render_v2.run(ctx))
        files.update(sections_v2.run(ctx))
        dr = drawing_v2.run(ctx)
        files["drawing"], files["dxf"] = dr["png"], dr["dxf"]
        times["pictures"] = round(time.time() - t, 1)
    else:
        dr = None
    verd = verdicts(fit, cad, calc, info, san)
    summ = {"tag": ctx.tag, "inputs": {"frame": ctx.frame_path, "params": ctx.params_path, "board_step": ctx.board_path,
                                       "board_geom": C.BOARD_GEOM},
            "frame": info, "sanity": san, "params": ctx.P.report(), "design": D.summary(),
            "params_file_body": ctx.P.raw.get("body"), "params_file_checks": ctx.P.raw.get("checks"),
            "params_file_rib_reach": find_keys(ctx.P.raw, r"reach"),
            "verdicts": verd, "all_ok": all(verd.values()),
            "key": {"closest_component": fit["fit3d"]["closest_components"][0],
                    "tail_min": fit["fit3d"]["tail_min_dist"], "panel_min": fit["fit3d"]["panel_min_dist"],
                    "pcb_body": fit["fit3d"]["pcb_body"]["min_dist"],
                    "pads_contact": fit["plan"]["contact"]["pad_min"], "pads_footprint": fit["plan"]["footprint"]["pad_min"],
                    "creepage_contact": fit["plan"]["contact"]["creepage_mains_to_panel_mm"],
                    "creepage_footprint": fit["plan"]["footprint"]["creepage_mains_to_panel_mm"],
                    "clearance": fit["plan"]["clearance_mains_to_panel_mm"],
                    "tool_access_min": fit["tool_access"]["min_dist"], "washer_vs_frame": fit["washer_vs_frame"]["overlapping"],
                    "above_pcb_mm3": fit["above_pcb"]["volume_mm3"],
                    "above_pcb_plan_gap": fit["above_pcb"].get("plan_gap_above_z0_to_board_edge_mm"),
                    "slivers": [len(cad["slivers"]["slivers"]), cad["slivers"]["faces"]],
                    "draft_flagged": cad["draft"]["flagged_summary"],
                    "v_notches": sum(p.get("v_notches", 0) for p in cad["thin"]["planes"]),
                    "beam_I_mm4": calc["beam"]["section"]["I_mm4"], "worst_lift_1000h_nom_um": calc["beam"]["worst_lift_1000h_nom_um"],
                    "stud_bearing_real_MPa": calc["studs"]["bearing_real_MPa"],
                    "thermal_not_covered": calc["thermal"]["holes_to_slot"],
                    "thermal_reference": calc["thermal"]["reference"],
                    "rib_height_measured": calc["flange"].get("rib_height_measured_mm"),
                    "governing_3d_pad_component": fit["plan"].get("governing_3d")},
            "fit_table": fit["table"], "files": files, "drawing": dr, "seconds": times}
    if ctx.v1:
        summ["regression"] = regression(fit, cad, calc, info)
        C.log("\nREGRESSION vs v1 (%s)" % summ["regression"]["reference"])
        for r in summ["regression"]["rows"]:
            C.log("  %-58s v1 %-12s v2-toolchain %-12s %s%s" % (r["quantity"], r["v1"], r["v2_toolchain"],
                                                               "match" if r["match"] else "DIFF",
                                                               ("  - " + r["why"]) if r["why"] else ""))
    summ["seconds"]["total"] = round(time.time() - t0, 1)
    C.dump(summ, ctx.out("summary.json"))
    C.log("\nVERDICTS")
    for k, v in verd.items():
        C.log("  %-52s %s" % (k, "OK" if v else "NOT OK"))
    C.log("done in %.0f s -> %s" % (time.time() - t0, ctx.out("summary.json")))
    return summ


if __name__ == "__main__":
    main(sys.argv[1:])
