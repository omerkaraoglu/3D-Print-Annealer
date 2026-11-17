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


def condensed(spec, mould, carry, fit, calc, G, carry_prev=None):
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
    w12 = t.get("walls_lt_1p2")
    if w12 is not None:
        add("B", "walls < %.1f listed (19+ plan / 11 vertical sections; INFO, the criterion stays < 1.0)" % t.get("list_limit_mm", 1.2),
            "%d: %s" % (len(w12), "; ".join("%s %.2f at %s%s" % (w["plane"], w["width_max"], [round(float(v), 2) for v in w["at"]], " (%s)" % w["what"] if w.get("what") else "")
                                           for w in sorted(w12, key=lambda q: q["width_max"])[:14])), "list", "INFO")
    si = mould.get("sharp_inside")
    if si:
        new = [k for k in si["groups"] if k.startswith("tail pocket")]
        add("B", "sharp inside corners (concave edges > %.0f deg without a round), by feature" % si["min_angle_deg"],
            "%d: %s" % (si["sharp_concave_edges"], "; ".join("%s %d (%.0f mm)" % (k, v["edges"], v["length_mm"])
                                                              for k, v in sorted(si["groups"].items(), key=lambda kv: -kv[1]["edges"])
                                                              if not k.startswith("other (")) +
                        "; other %d (fillet-to-fillet creases at rib ends, the H6 jog)" % sum(v["edges"] for k, v in si["groups"].items() if k.startswith("other ("))),
            "none in the bridge / slot / rib / tail pocket (GF-2.0: 160, GF-1.1: 162 by the same scan)", "PASS" if not new else "FAIL")
    br = mould.get("bridge")
    if br:
        bf = br["by_feature"]
        def sides(k):
            return bf.get(k, {}).get("sides", {})
        ok = br["occluded_points_in_zone"] == 0 and set(sides("nose R%.1f" % G.bend_nose_R)) <= {"B (+Z)"} and set(sides("land break 0.3 x 45")) <= {"A (-Z)"}
        add("B", "bridge / bend-gap slot: tool half of every face in the slot zone; undercut points",
            "; ".join("%s %s" % (k, v["sides"]) for k, v in bf.items()) + "; occluded points %d" % br["occluded_points_in_zone"],
            "nose B only, break A only, 0 occluded", "PASS" if ok else "FAIL")
        so = br["shut_off"][0] if br["shut_off"] else None
        if so:
            k_st = next(k for k in so if k.startswith("option_stepped"))
            add("B", "bend-gap slot A/B shut-off (x %.0f): parting on the bridge side at the break top, on the front side at the shelf corner" % so["x"],
                "PB %s, PF %s: rise %.2f over %.2f; straight shut-off -> B steel wedge %.1f deg; stepped -> B %.1f / A %.1f deg, telescopic %.2f high" % (
                    so["PB_chamfer_top_yZ"], so["PF_shelf_corner_yZ"], so["rise_mm"], so["run_mm"], so["option_straight_PF_PB"]["B_steel_wedge_at_PB_deg"],
                    so[k_st]["B_steel_at_PB_deg"], so[k_st]["A_steel_at_PB_deg"], so[k_st]["telescopic_shutoff_height_mm"]),
                "params cad_rules shut-off rule (the 'shut-off A/B' entry)", "INFO")
    # ---- C
    for tag, cr, ref in (("v2", carry, "v2"), ("%s release" % C.PREV_TAG, carry_prev, C.PREV_TAG)):
        if not cr:
            continue
        add("C", "carried-over slab Z >= -5.0 vs %s: GF-only / %s-only volume" % (tag, ref), "%.1f / %.1f mm3 in %d regions" % (
            cr["gf_only_mm3"], cr["v2_only_mm3"], len(cr["regions"])), "explained by the params" if ref == "v2" else "explained by the change list", "INFO")
        for k, vv in cr["by_explanation"].items():
            add("C", "  %s%s" % ("" if ref == "v2" else "[vs %s] " % ref, k), "GF-only %.1f / %s-only %.1f mm3 (%d regions)" % (vv["GF only"], ref, vv["v2 only"], vv["regions"]),
                "params" if ref == "v2" else "change list", "FAIL" if k.startswith(("UNEXPLAINED", "corner-cell")) else "PASS")
    # ---- D
    for r in fit["rows"]:
        add("D", "%s: %s" % (r["group"], r["check"]), r["measured"], r["required"], r["verdict"])
    # ---- E
    secs = calc["sections"]
    pv = calc["port_validation"]
    add("E", "grillage port (copy) reproduces the GF-1.1 concept, S4, glass 3.0, 5 load points", "%s mm" % pv["w50_mm"],
        "%s (+-0.0015)" % pv["concept_w50_mm"], "PASS" if pv["ok"] else "FAIL")
    cs = calc["concept_sections_3.0"]
    for k, v in secs.items():
        if v.get("I_mm4") is None:
            continue
        ref = cs["channel"]["top"]["I"] if "top" in k else cs["channel"]["left"]["I"] if "left" in k else cs["channel"]["right"]["I"] if "right" in k else \
            cs["channel"]["bottom"]["I"] if "channel" in k else cs["bridge_bottom"]["I"] if "bridge only" in k else None
        add("E", "ring I, " + k, "%.0f mm4%s" % (v["I_mm4"], " (%.2f x concept)" % (v["I_mm4"] / ref) if ref else ""),
            "concept %.0f" % ref if ref else "GF-1.1 range 1053-2034", "INFO")
    rows = calc["grillage"]["rows"]
    def pick(bottom, tg, src, lp):
        return next(r for r in rows if r["bottom"] == bottom and r["glass_t"] == tg and r["I_source"].startswith(src) and r["load_point"] == lp)
    lps = [r["load_point"] for r in rows if r["bottom"] == "channel" and r["glass_t"] == 3.0 and r["I_source"].startswith("measured")]
    PR = calc.get("previous_release") or {}
    pt = PR.get("tag", "previous")
    for lp in lps:
        m, b = pick("channel", 3.0, "measured", lp), pick("bridge", 3.0, "measured", lp)
        c = pick("channel", 3.0, "concept", lp)
        add("E", "50 N / 250 N at %s, glass 3.0 (measured I; channel / bridge-only bound)" % lp,
            "w %.4f / %.4f mm, lip line %.4f / %.4f, glass %.1f / %.1f MPa (SF %.2f / %.2f), ring %.1f / %.1f MPa, stud %.0f N" % (
                m["w_50N_mm"], b["w_50N_mm"], m["lip_line_50N_mm"], b["lip_line_50N_mm"], m["glass_250N_MPa"], b["glass_250N_MPa"],
                m["glass_SF_250N"], b["glass_SF_250N"], m["ring_250N_MPa"], b["ring_250N_MPa"], m["stud_250N_N"]),
            "concept rectangles w %.4f, glass %.1f" % (c["w_50N_mm"], c["glass_250N_MPa"]), "INFO")
    for tg in (1.1, 2.0, 3.0, 4.0):
        mc, mb = pick("channel", tg, "measured", "window centre"), pick("bridge", tg, "measured", "window centre")
        ec, eb = pick("channel", tg, "measured", "glass bottom edge, mid"), pick("bridge", tg, "measured", "glass bottom edge, mid")
        w11 = PR.get("push_50N_window_centre_mm", {}).get("%.1f" % tg)
        l11 = PR.get("push_50N_lip_line_max_mm", {}).get("%.1f" % tg)
        s11 = PR.get("glass_250N_max_MPa", {}).get("%.1f" % tg)
        add("E", "glass %.1f, 50 N: window centre / bottom edge mid (channel / bridge only); 250 N glass max" % tg,
            "%.4f / %.4f | %.4f / %.4f mm; %.0f / %.0f MPa (SF %.2f / %.2f)" % (mc["w_50N_mm"], mb["w_50N_mm"], ec["w_50N_mm"], eb["w_50N_mm"],
                                                                          max(r["glass_250N_MPa"] for r in rows if r["glass_t"] == tg and r["bottom"] == "channel" and r["I_source"].startswith("measured")),
                                                                          max(r["glass_250N_MPa"] for r in rows if r["glass_t"] == tg and r["bottom"] == "bridge" and r["I_source"].startswith("measured")),
                                                                          min(r["glass_SF_250N"] for r in rows if r["glass_t"] == tg and r["bottom"] == "channel" and r["I_source"].startswith("measured")),
                                                                          min(r["glass_SF_250N"] for r in rows if r["glass_t"] == tg and r["bottom"] == "bridge" and r["I_source"].startswith("measured"))),
            "%s: centre %s, lip line max %s, glass 250 N max %s MPa (channel)" % (pt, w11, l11, s11), "INFO")
    worst_edge = max(r["lip_line_50N_mm"] for r in rows if r["I_source"].startswith("measured") and r["load_point"] != "window centre" and r["glass_t"] >= 2.0)
    worst_edge11 = max(r["lip_line_50N_mm"] for r in rows if r["I_source"].startswith("measured") and r["load_point"] != "window centre")
    add("E", "50 N on an edge / the border: lip-line deflection, glass 2.0-4.0 (1.1), both bottom bounds",
        "max %.4f mm (%.4f at 1.1)" % (worst_edge, worst_edge11), "<= 0.15 (flushness inspection limit, concept_gf2 4.2)",
        "PASS" if worst_edge <= 0.15 else "FAIL")
    for k, v in calc["impact_0p5J"].items():
        if not k.startswith("channel"):
            continue
        vb = calc["impact_0p5J"]["bridge" + k[len("channel"):]]
        add("E", "0.5 J impact SF, glass %s: window centre / bend-gap strip (whole border free; strip only), channel | bridge bound" % k.split()[-1],
            "%.2f / %.2f; %.2f | %.2f / %.2f; %.2f" % (v["window_centre"]["SF"], v["bend_gap_strip_whole_border_free"]["SF"], v["bend_gap_strip_only"]["SF"],
                                                     vb["window_centre"]["SF"], vb["bend_gap_strip_whole_border_free"]["SF"], vb["bend_gap_strip_only"]["SF"]),
            "estimate; %s centre %s, strip (whole border free) %s" % (pt, PR.get("impact_SF_centre", {}).get(k.split()[-1]),
                                                                       PR.get("impact_SF_strip_whole_border", {}).get(k.split()[-1])), "INFO")
    bd = calc["bead"]
    add("E", "bead area (0.9..4.9 band, R_glass corners) / dead load / 250 N pull", "%.1f mm2 / %.2f kPa / %.3f MPa" % (bd["area_mm2"], bd["dead_load_kPa"], bd["pull_250N_MPa"]),
        "params %s; %s %s / %s / %s" % (bd["params_bead_area"], pt, PR.get("bead_area_mm2"), PR.get("bead_dead_load_kPa"), PR.get("bead_pull_250N_MPa")),
        "PASS" if abs(bd["area_mm2"] - float(bd["params_bead_area"])) < 0.5 else "FAIL")
    sh = {s["case"]: s for s in bd["shear"]}
    wcase = sh["bound + 0.3 % moisture, +70 C"]
    add("E", "bead shear at the corner (r %.1f): bound 70 ppm/K +70 C + 0.3 %% moisture vs d_allow class 50 at the thinnest line 0.73" % bd["r_bead_corner_mm"],
        "d %.3f vs %.3f (ext. %.1f %%); thermal only (70 ppm) %.3f; class 25 at t 1.0: %.3f" % (
            wcase["d_mm"], wcase["class50_t0.73_allow"], 100 * wcase["eq_ext_t0.73"], sh["bound 70 ppm/K, +70 C"]["d_mm"], wcase["class25_t1.0_allow"]),
        "d <= t sqrt(2e + e^2) (class 50, design doc 7.7)", "PASS" if wcase["ok_class50_t0.73"] else "FAIL")
    tf = calc["tape_fasteners"]
    add("E", "VHB: area / module dead load / 250 N / thermal shear 50-70 ppm", "%.1f mm2 / %.2f kPa / %.1f kPa / %s %%" % (
        tf["tape_area_mm2"], tf["tape_dead_load_kPa"], tf["tape_250N_kPa"], tf["tape_thermal_shear_pct_50_70"]),
        "%s %s / %s / %s / %s; 3M slow shear <= 300 %%" % (pt, PR.get("tape_area_mm2"), PR.get("tape_dead_load_kPa"), PR.get("tape_250N_kPa"),
                                                          PR.get("tape_thermal_shear_pct_50_70")), "INFO")
    add("E", "studs: radial thermal move vs float along the slot; reaction at 250 N; M4 washer at 500 N",
        "%s mm vs %.2f; %.0f N; %s MPa" % (tf["stud_radial_move_mm_50_70"], tf["stud_float_along_slot_mm"], tf["stud_reaction_250N_max_N"], tf["washer_M4_500N_MPa"]),
        "move < float; washer < 15 MPa", "PASS" if max(tf["stud_radial_move_mm_50_70"]) < tf["stud_float_along_slot_mm"] and
        (tf["washer_M4_500N_MPa"] is None or max(tf["washer_M4_500N_MPa"]) < 15) else "FAIL")
    bzc = calc.get("bend_zone_criterion") or {}
    if bzc.get("measured_3D"):
        c_ = bzc["criterion"]
        for n, v in bzc["measured_3D"].items():
            add("E", "bend zone (nose / pocket face / break), %s tail: nominal / panel at its RSS position / worst case (3D, fit check)" % n,
                "%.3f / %.3f / %.3f (panel position only %.3f; with print-to-edge +-0.1 %.3f)" % (v["nominal"], v["RSS"], v["WC"], v["WC_panel_only"], v["WC_print_0.1"]),
                ">= %.2f at RSS (+%.3f), > %.1f at WC (+%.2f, exit +-%.1f, tail +%.2f)" % (c_["min_at_RSS"], c_["rss"], c_["min_at_WC"], c_["wc"], c_["exit_Z_tol"], c_["tail_t_tol"]),
                "PASS" if v["RSS"] >= c_["min_at_RSS"] - 1e-4 and v["WC"] > c_["min_at_WC"] else "FAIL")
        gb = bzc["g_bend_budget"]
        add("E", "g_bend budget (RSS position term incl. print-to-edge): %s; border limit with the A1 land measured to the break edge" % gb["formula"],
            "%.3f (modelled g_bend %.2f, %+.3f); limit for border %.1f: %.3f (land %.2f) -> reserve of the budget %.3f, of the modelled g_bend %.3f" % (
                gb["sum"], gb["modelled_g_bend"], gb["modelled_g_bend_vs_budget"], gb["border"], gb["limit_for_border"], gb["land_min"],
                gb["reserve_to_limit"], gb["modelled_g_bend_vs_limit"]),
            "budget <= modelled g_bend <= limit", "PASS" if gb["sum"] <= gb["modelled_g_bend"] + 1e-9 and gb["modelled_g_bend"] <= gb["limit_for_border"] + 1e-9 else "FAIL")
        nd = bzc.get("g_bend_needed_for_concept_0.45_at_WC") or {}
        if nd:
            wcc = bzc["measured_3D"]["CTP"]["WC"]
            add("E", "the concept's intent >= 0.45 at the full worst case (GF-2.0 open finding 1; CTP governs)",
                "CTP WC %.3f (margin %+.3f; panel position only %.3f, print +-0.1 %.3f); g_bend at which WC = 0.45: %.3f (all contributors) / %.3f (panel only)" % (
                    wcc, wcc - 0.45, bzc["measured_3D"]["CTP"]["WC_panel_only"], bzc["measured_3D"]["CTP"]["WC_print_0.1"],
                    nd["CTP"]["g_bend_for_0.45_at_WC_all_contributors"], nd["CTP"]["g_bend_for_0.45_at_WC_panel_position_only"]),
                ">= 0.45", "PASS" if wcc >= 0.45 - 1e-4 else "FAIL")
    add("E", "volume / mass", "%.3f cm3 / %.1f g" % (calc["volume"]["volume_cm3"], calc["volume"]["mass_g"]),
        "params %s cm3; %s" % (calc["volume"]["params_as_modelled"], calc["volume"].get("prev")), "INFO")
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
    carry = timed("C carry-over vs v2", lambda: carryover.run(ctx, ref="v2")) if want("C") else old_cad.get("carryover")
    carry_prev = (timed("C carry-over vs %s" % C.PREV_TAG, lambda: carryover.run(ctx, ref="prev")) if want("C") else old_cad.get("carryover_vs_prev")) \
        if ctx.G.gf2 else None
    C.dump({"step": fid, "spec": spec, "mould": mould, "carryover": carry, "carryover_vs_prev": carry_prev}, ctx.out("cadcheck.json"))
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
        calc = timed("E calc", lambda: calc_gf.run(ctx, fit=fit))
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
        sec = timed("sections", lambda: sections_gf.run(ctx, fit=fit))
        if sec:
            imgs.update(sec["images"])
            if spec is not None:
                spec["section_dims_measured"] = sec["dims_measured"]
        if mould:
            imgs["thickness_map"] = mould["thick"]["map_png"]
            if mould.get("draft_map_png"):
                imgs["draft_map"] = mould["draft_map_png"]
        C.dump({"step": fid, "spec": spec, "mould": mould, "carryover": carry, "carryover_vs_prev": carry_prev}, ctx.out("cadcheck.json"))
    try:
        rows = condensed(spec, mould, carry, fit, calc, ctx.G, carry_prev)
    except Exception:
        errors["condensed table"] = traceback.format_exc()
        rows = []
    # comparison with an archived earlier revision run (out/GF-1.0/summary.json), row by row on (id, check)
    prev_dir = None
    for a in argv:
        if a.startswith("--compare="):
            prev_dir = a.split("=", 1)[1]
    prev_dir = prev_dir or os.path.join(ctx.outdir, C.PREV_TAG if ctx.G.gf2 else "GF-1.0")
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
                          "v2_step": getattr(ctx, "v2_info", None), "prev_step": getattr(ctx, "prev_info", None), "prev_tag": C.PREV_TAG,
                          "board_step": C.file_id(ctx.board_path) if getattr(ctx, "board_path", None) else None,
                          "board_geom": C.file_id(C.BOARD_GEOM),
                          "glass_t": ctx.G.glass_t, "panel_dz_applied_to_DS1": round(ctx.panel_dz, 3)},
               "step_changed_since_previous_run": None if prev is None else (prev.get("sha256") != fid["sha256"]),
               "previous_run_step": prev,
               "step_changed_during_this_run": fid_end["sha256"] != fid["sha256"],
               "table": rows, "fails": [r for r in rows if r["verdict"] == "FAIL"],
               "remaining_fails_in_words": ["%s %s: measured %s; required %s" % (r["id"], r["check"], r["measured"], r["required"])
                                            for r in rows if r["verdict"] == "FAIL"],
               "open_findings": ctx.G.raw.get("open_findings"),
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
