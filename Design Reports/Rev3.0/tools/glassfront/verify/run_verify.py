"""Glass-front frame GF-1.0 - independent verification, ONE command:

  <venv>\\Scripts\\python.exe run_verify.py [--frame f.step] [--params p.json] [--board b.step] [--no-render]

Runs A spec_check, B mould_check, C carryover, D fit_check, E calc_gf, renders and section plots on the same
loaded STEP and writes:
  out/summary.json   STEP / params / board identity (size, mtime, sha256), verdict table, fails, timings, and
                     whether the STEP differs from the one of the previous run (out/summary.json read first)
  out/cadcheck.json  A (spec), B (mould), C (carry-over)
  out/fitcheck.json, out/fitcheck.txt   D
  out/calc.json, out/calc.md            E
  Mechanical/Rev3.0_GlassFront/renders/verify/*.png
"""
import json
import os
import sys
import time
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vcommon as C


def condensed(spec, mould, carry, fit, calc, G):
    """one row per check family: (id, check, measured, required, verdict)"""
    R = []
    def add(i, chk, meas, req, v):
        R.append({"id": i, "check": chk, "measured": meas, "required": req, "verdict": v})
    # ---- A
    groups = {}
    for r in spec["rows"]:
        groups.setdefault(r["group"], []).append(r)
    for g, rows in groups.items():
        f = [r for r in rows if r["verdict"] == "FAIL"]
        p = [r for r in rows if r["verdict"] == "PASS"]
        if f:
            for r in f:
                add("A", "%s: %s (%s)" % (g, r["item"], r["where"]), r["measured"], r["required"], "FAIL")
            if p:
                add("A", "%s: other checks" % g, "%d pass" % len(p), "tol 0.01 / 0.05 deg", "PASS")
        elif p:
            worst = max((abs(r["diff"]) for r in p if r["diff"] is not None), default=0.0)
            add("A", "%s (%d checks)" % (g, len(p)), "max |diff| %.4f" % worst, "tol 0.01 mm / 0.05 deg", "PASS")
        for r in rows:
            if r["verdict"] == "INFO" and g in ("lip", "fasteners", "Z levels", "body", "plan / profiles"):
                if "washer" in r["item"] and not r["item"].startswith("F1 "):
                    continue
                if "clearance-pocket face at the land" in r["item"] and "top edge, x 80" not in r["where"]:
                    continue
                if "visible g1" in r["item"] and "top edge, x 80" not in r["where"]:
                    continue
                if "lip width at the top" in r["item"] and "top edge, x 80" not in r["where"]:
                    continue
                add("A", "%s: %s" % (g, r["item"]), r["measured"], r["required"], "INFO")
    # ---- B
    s = mould["slivers"]
    add("B", "slivers (2A/P < 0.3 or area < 0.5): design faces / fillet blend patches", "%d / %d (max blend %.3f mm2)" % (
        len(s["design_face_slivers"]), s["fillet_blend_slivers"], s["max_blend_area"]), "0 design faces",
        "PASS" if not s["design_face_slivers"] else "FAIL")
    d = mould["draft"]
    add("B", "draft along Z (every face)", "%d flagged; cones %s; drafted planes %s" % (len(d["flagged"]), d["cone_semi_angles_deg"],
        d["drafted_plane_angles_deg"]), ">= 0.25 deg everywhere (1 / 0.5 deg rules)", "PASS" if d["ok"] else "FAIL")
    c = mould["columns"]
    add("B", "undercut: vertical rays, %.2f mm grid (%d rays)" % (c["grid_mm"], c["rays"]), "%d columns with > 1 material interval" % len(
        c["multi_interval_columns"]), "0", "PASS" if c["ok"] else "FAIL")
    v = mould["visibility"]
    add("B", "undercut: face visibility along the pull (mesh points, exact outward side)", "%d occluded faces; A %d / B %d / split %d" % (
        len(v["occluded_faces"]), v["faces_A"], v["faces_B"], v["faces_split"]), "0", "PASS" if not v["occluded_faces"] else "FAIL")
    add("B", "parting: faces in front of the flange-front plane formed from +Z; flange edge widest at the front",
        "%d; %s" % (len(v["parting_violations"]), "yes" if mould["flange_edge"]["ok"] else "NO"), "0; yes",
        "PASS" if not v["parting_violations"] and mould["flange_edge"]["ok"] else "FAIL")
    t = mould["thin"]
    lipw = [w for w in t["thin_walls"] if w.get("what")]
    other = [w for w in t["thin_walls"] if not w.get("what")]
    add("B", "thin walls < 1.0 (%d plan + %d vertical sections)" % (len([p for p in t["planes"] if p["kind"] == "plan"]),
                                                                  len([p for p in t["planes"] if p["kind"] != "plan"])),
        "lip %d segments (min %.3f, by design); other %d%s" % (len(lipw), min([w["width_max"] for w in lipw] or [0]), len(other),
                                                             (": " + "; ".join("%s %.2f at %s" % (w["plane"], w["width_max"], w["at"]) for w in other)) if other else ""),
        "only the lip", "PASS" if not other else "FAIL")
    vn = [dict(g, plane=p["name"]) for p in t["planes"] for g in p["v_notches"]]
    vn_steel = [g for g in vn if "re-entrant" in g["class"]]
    vn_wall = [g for g in vn if "re-entrant" not in g["class"]]
    add("B", "thin gaps < 1.0 (knife-edge steel): slots / V-notches", "%d / %d%s%s" % (len(t["thin_gaps"]), len(vn),
        (": " + "; ".join("%s %s w%.2f at %s" % (g["plane"], g["class"].split("(")[0].strip(), g["width_max"], g["at"]) for g in vn_steel)) if vn_steel else "",
        ("; %d wall-side wedge%s (%s) = raster ends of the 1.0 lip at its corners, not steel" % (
            len(vn_wall), "s" if len(vn_wall) > 1 else "", ", ".join("%s at %s" % (g["plane"], g["at"]) for g in vn_wall))) if vn_wall else ""),
        "0 slots", "PASS" if not t["thin_gaps"] else "FAIL")
    kn, sp_ = t.get("steel_knife_edges", []), t.get("sharp_plastic_edges", [])
    add("B", "acute corners < %.0f deg in the plan sections: steel knife edges / sharp plastic edges" % t.get("acute_limit_deg", 60),
        "%d / %d%s" % (len(kn), len(sp_), (": " + "; ".join("%s %.0f deg at %s" % (k["plane"], k["angle_deg"], k["at"]) for k in (kn + sp_)[:8])) if kn or sp_ else ""),
        "0 knife edges", "PASS" if not kn else "FAIL")
    th = mould["thick"]
    add("B", "thick sections: inscribed sphere > %.1f (2 x wall)" % th["limit_dia_mm"], "max %.2f; %d spots: %s" % (
        th["max_sphere_dia"], len(th["spots_over_limit"]), "; ".join("%.1f at %s (%s)" % (s_["max_sphere_dia"], s_["at_abs"], s_["what"])
                                                                   for s_ in th["spots_over_limit"][:9])), "none > 5.0", "PASS" if th["ok"] else "FAIL")
    if th.get("top_spots"):
        add("B", "thick sections: largest inscribed spheres (top 5, any value)", "; ".join(
            "%.2f at %s (%s)" % (s_["max_sphere_dia"], s_["at_abs"], s_["what"]) for s_ in th["top_spots"][:5]), "<= 5.0", "INFO")
    if mould.get("thick_v2"):
        add("B", "(reference) v2 thick sections, same method", "max %.2f; %d spots" % (mould["thick_v2"]["max_sphere_dia"],
            len(mould["thick_v2"]["spots_over_limit"])), "-", "INFO")
    # ---- C
    add("C", "carried-over slab Z >= -5.0 vs v2: GF-only / v2-only volume", "%.1f / %.1f mm3 in %d regions" % (
        carry["gf_only_mm3"], carry["v2_only_mm3"], len(carry["regions"])), "explained by the params", "INFO")
    for k, vv in carry["by_explanation"].items():
        add("C", "  " + k, "GF-only %.1f / v2-only %.1f mm3 (%d regions)" % (vv["GF only"], vv["v2 only"], vv["regions"]),
            "params", "FAIL" if k.startswith(("UNEXPLAINED", "corner-cell")) else "PASS")
    # ---- D
    for r in fit["rows"]:
        add("D", "%s: %s" % (r["group"], r["check"]), r["measured"], r["required"], r["verdict"])
    # ---- E
    secs = calc["sections"]
    Ic = calc["concept_ring_section"]["I"]
    for k in ("mid-top (x 80)", "mid-side left (y 60)", "mid-bottom over the tail pocket (x 80), beam + land plate + flange",
              "near the top-left corner (x 23, past the corner arc and the side shelf)", "mid-top through F5 (x 103.85)",
              "corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib)"):
        add("E", "ring I, " + k, "%.0f mm4 (%.2f x concept)" % (secs[k]["I_mm4"], secs[k]["I_mm4"] / Ic), "concept %.0f (doc 1174)" % Ic, "INFO")
    rows = calc["grillage"]["rows"]
    base = [r for r in rows if r["run"].startswith("concept")]
    meas = [r for r in rows if r["run"].startswith("measured min")]
    for b, m in zip(base, meas):
        add("E", "50 N / 250 N at %s (measured I)" % b["load_point"], "w %.4f mm, lip line %.4f, glass %.1f MPa, ring %.1f MPa" % (
            m["w_50N_mm"], m["lip_line_50N_mm"], m["glass_250N_MPa"], m["ring_250N_MPa"]),
            "concept w %.4f, lip %.4f, glass %.1f, ring %.1f" % (b["w_50N_mm"], b["lip_line_50N_mm"], b["glass_250N_MPa"], b["ring_250N_MPa"]), "INFO")
    add("E", "bead area", "%.1f mm2" % calc["bead"]["area_mm2"], "2510 (concept)", "INFO")
    add("E", "volume / mass", "%.3f cm3 / %.1f g" % (calc["volume"]["volume_cm3"], calc["volume"]["mass_g"]), "~70 cm3 / ~95 g (concept)", "INFO")
    return R


def main(argv):
    t0 = time.time()
    ctx = C.Context(argv)
    prev = None
    prev_summary = {}
    sp = ctx.out("summary.json")
    if os.path.exists(sp):
        try:
            prev_summary = json.load(open(sp))
            prev = prev_summary["inputs"]["frame"]
        except Exception:
            prev = None
    _ = ctx.frame
    fid = ctx.frame_info
    C.log("STEP %s  %d bytes  mtime %s  sha256 %s  (unit %s)" % (fid["file"], fid["bytes"], fid["mtime"], fid["sha256"], fid["declared_unit"]))
    times = {}
    import spec_check, mould_check, carryover, fit_check, calc_gf, render_gf, sections_gf

    errors = {}

    def timed(name, fn):
        t = time.time()
        try:
            r = fn()
        except Exception:
            errors[name] = traceback.format_exc()
            C.log("ERROR in %s:\n%s" % (name, errors[name]))
            r = None
        times[name] = round(time.time() - t, 1)
        return r
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))     # e.g. --only A,B (re-use the rest from out/)
    def want(k):
        return only is None or k in only
    old_cad = json.load(open(ctx.out("cadcheck.json"))) if (only and os.path.exists(ctx.out("cadcheck.json"))) else {}
    spec = timed("A spec", lambda: spec_check.run(ctx)) if want("A") else old_cad.get("spec")
    mould = timed("B mould", lambda: mould_check.run(ctx)) if want("B") else old_cad.get("mould")
    if mould is not None and want("B"):
        mould["thick_v2"] = timed("B v2 thick (reference)", lambda: {k: v for k, v in mould_check.thick_sections(ctx.v2, ctx.G, None).items() if k != "map_png"})
    carry = timed("C carry-over", lambda: carryover.run(ctx)) if want("C") else old_cad.get("carryover")
    C.dump({"step": fid, "spec": spec, "mould": mould, "carryover": carry}, ctx.out("cadcheck.json"))
    if want("D"):
        fit = timed("D fit", lambda: fit_check.run(ctx))
        if fit is not None:
            C.dump(fit, ctx.out("fitcheck.json"))
            open(ctx.out("fitcheck.txt"), "w", encoding="utf8").write(
                "Glass-front frame fit check - STEP %s (%s, %d bytes, sha256 %s)\n\n" % (os.path.basename(fid["file"]), fid["mtime"], fid["bytes"], fid["sha256"])
                + fit["table"] + "\n")
    else:
        fit = json.load(open(ctx.out("fitcheck.json"))) if os.path.exists(ctx.out("fitcheck.json")) else None
    if want("E"):
        calc = timed("E calc", lambda: calc_gf.run(ctx))
        if calc is not None:
            C.dump(calc, ctx.out("calc.json"))
            open(ctx.out("calc.md"), "w", encoding="utf8").write(calc_gf.markdown(calc, fid))
    else:
        calc = json.load(open(ctx.out("calc.json"))) if os.path.exists(ctx.out("calc.json")) else None
    imgs = {} if want("R") else dict(prev_summary.get("images", {}))
    if ctx.render and want("R"):
        r_ = timed("renders", lambda: render_gf.run(ctx))
        if r_:
            imgs.update(r_)
        sec = timed("sections", lambda: sections_gf.run(ctx))
        if sec:
            imgs.update(sec["images"])
            if spec is not None:
                spec["section_dims_measured"] = sec["dims_measured"]
        if mould:
            imgs["thickness_map"] = mould["thick"]["map_png"]
        C.dump({"step": fid, "spec": spec, "mould": mould, "carryover": carry}, ctx.out("cadcheck.json"))
    try:
        rows = condensed(spec, mould, carry, fit, calc, ctx.G)
    except Exception:
        errors["condensed table"] = traceback.format_exc()
        rows = []
    # comparison with an archived earlier revision run (out/GF-1.0/summary.json), row by row on (id, check)
    prev_dir = None
    for a in argv:
        if a.startswith("--compare="):
            prev_dir = a.split("=", 1)[1]
    prev_dir = prev_dir or os.path.join(ctx.outdir, "GF-1.0")
    diff = []
    if os.path.exists(os.path.join(prev_dir, "summary.json")):
        old = {(r["id"], r["check"]): r for r in json.load(open(os.path.join(prev_dir, "summary.json")))["table"]}
        for r in rows:
            o = old.get((r["id"], r["check"]))
            if o is None:
                r["previous"] = "new check"
                diff.append({"id": r["id"], "check": r["check"], "before": "new check (no row of that name before)",
                             "before_verdict": "-", "now": r["measured"], "now_verdict": r["verdict"]})
            else:
                r["previous"] = {"measured": o["measured"], "verdict": o["verdict"]}
                if str(o["measured"]) != str(r["measured"]) or o["verdict"] != r["verdict"]:
                    diff.append({"id": r["id"], "check": r["check"], "before": o["measured"], "before_verdict": o["verdict"],
                                 "now": r["measured"], "now_verdict": r["verdict"]})
        gone = [k for k in old if k not in {(r["id"], r["check"]) for r in rows}]
        diff += [{"id": k[0], "check": k[1], "before": old[k]["measured"], "before_verdict": old[k]["verdict"],
                  "now": "check no longer produced", "now_verdict": "-"} for k in gone]
    fid_end = C.file_id(ctx.frame_path)
    summary = {"about": "Independent verification of the %s glass-front frame STEP (CadQuery / OCP / VTK), tools/glassfront/verify" % (
                   str(ctx.G.revision).split(" ")[0]),
               "inputs": {"frame": fid, "params": C.file_id(ctx.params_path), "params_revision": ctx.G.revision,
                          "v2_step": getattr(ctx, "v2_info", None),
                          "board_step": C.file_id(ctx.board_path) if getattr(ctx, "board_path", None) else None,
                          "board_geom": C.file_id(C.BOARD_GEOM),
                          "glass_t": ctx.G.glass_t, "panel_dz_applied_to_DS1": round(ctx.panel_dz, 3)},
               "step_changed_since_previous_run": None if prev is None else (prev.get("sha256") != fid["sha256"]),
               "previous_run_step": prev,
               "step_changed_during_this_run": fid_end["sha256"] != fid["sha256"],
               "table": rows, "fails": [r for r in rows if r["verdict"] == "FAIL"],
               "counts": {v: sum(1 for r in rows if r["verdict"] == v) for v in ("PASS", "FAIL", "INFO")},
               "changes_vs_previous_revision": {"compared_with": prev_dir, "rows": diff},
               "images": imgs, "timings_s": times, "total_s": round(time.time() - t0, 1), "errors": errors,
               "partial_run": sorted(only) if only else None}
    if only and prev_summary:       # partial run: keep the identities / timings of the modules not re-run
        for k in ("v2_step", "board_step"):
            if summary["inputs"].get(k) is None:
                summary["inputs"][k] = prev_summary.get("inputs", {}).get(k)
        if summary["inputs"].get("board_step") is None:
            try:
                summary["inputs"]["board_step"] = C.file_id(C.board_step(ctx.board_opt))
            except Exception:
                pass
        summary["timings_s"] = dict(prev_summary.get("timings_s", {}), **times)
        summary["partial_run_of"] = prev_summary.get("inputs", {}).get("frame", {}).get("sha256")
    C.dump(summary, sp)
    C.log("\n%-3s %-100s %-50s %-40s %s" % ("", "check", "measured", "required", "verdict"))
    for r in rows:
        C.log("%-3s %-100s %-50s %-40s %s" % (r["id"], str(r["check"])[:100], str(r["measured"])[:50], str(r["required"])[:40], r["verdict"]))
    C.log("\ncounts %s; total %.0f s; STEP sha256 %s%s" % (summary["counts"], summary["total_s"], fid["sha256"][:16],
                                                         "  (CHANGED DURING THE RUN - re-run!)" if summary["step_changed_during_this_run"] else ""))
    return summary


if __name__ == "__main__":
    main(sys.argv[1:])
