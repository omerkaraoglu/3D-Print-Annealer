"""GF-D21 tail fold gauge and fold test (GF-2.1): the gauge that forms the g_bend bend-gap slot with the panel edge
(R1.5 nose at the bridge's height), the test on one real panel and its pass criteria (concept_gf2.md 2.4 / 7 risk 1).
Every product number comes from the master (g_bend, bend_nose_R, bend_gap_slot, divider rib, Z levels, tail_route,
the g_bend and border notes); the fold-fit pass rule (gauge slot, feeler, tail limit, pass / fail) from the master
'fold_test' block (addendum 2026-11-16, the one source); gauge make and test counts from drafting_choices.json.

  <venv>/Scripts/python.exe make_tailgauge.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_TailFoldGauge.{dxf,pdf,png}
"""
import datetime
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (Params, Choices, Rect, OUT_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text, rev_note,
                       master_ref)
from gf_geom import Geom
from gf_draft import Sheet, THICK, THIN, XTHIN, MM_PER_PT, lw, clip_poly

C_LIM, C_CTP, C_TFT, C_REF, C_G = "#c0392b", "#6a5fb0", "#d35400", "#3b6fb6", "#a7acb3"
LAYERS = [("GAUGE", 7, "CONTINUOUS"), ("NOSE_TANGENT", 1, "DASHED"), ("ENGRAVE", 3, "CONTINUOUS"),
          ("LIMIT_REF", 1, "DASHED"), ("PANEL_REF", 5, "DASHDOT"), ("SECTION", 4, "CONTINUOUS"),
          ("TEXT", 7, "CONTINUOUS")]


def gauge_data(P, C, G):
    """gauge geometry in its own plan frame: x = abs x - slot centre, y = distance OUT from the panel edge face;
    section frame: y as plan, h = height above the CTP front (= the plate the panel lies on, face down)"""
    tg = C("tg_gauge")
    sl = P.rect("bend_gap_slot")
    g = P.d("g_bend")
    R = P.d("bend_nose_R")
    H = P.level("Z_LANDPLATE_BACK") - P.level("Z_CTP_FRONT")          # bridge floor above the CTP front
    # GF-2.1: the whole fold-fit rule is read from the master block fold_test (the g_bend / border notes no longer
    # carry the budget text); every number is checked against the values it rests on - a mismatch stops the run
    ft = P._use("fold_test", P.raw["fold_test"])
    bz = P._use("tail_clearance_criteria.bend_zone", P.raw["tail_clearance_criteria"]["bend_zone"])
    clr, pos, pos_wc = bz["clearance_min_at_RSS_mm"], bz["panel_position_RSS_mm"], bz["panel_position_WC_mm"]
    l0, R_in, t = P.d("tail_straight_l0"), P.d("tail_R_in_min"), P.d("tail_t")
    fe, lim = ft["feeler_mm"], ft["tail_outer_surface_limit_from_panel_edge_mm"]
    fe_x, need_lim, res_g = ft["exact_feeler_for_the_budget_mm"], ft["needed_gap_at_the_limit_mm"], \
        ft["reserve_to_g_bend_mm"]
    g_max, land_a1, assumed = ft["border_limit_needed_gap_mm"], ft["A1_land_to_the_break_edge_mm"], \
        ft["assumed_tail_mm"]
    bezel = round(G.window.y0 - G.panel.y0, 4)                  # window edge -> panel edge (bottom)
    assert abs(ft["gauge_slot_mm"] - g) < 1e-9, (ft["gauge_slot_mm"], g)        # the gauge slot IS g_bend
    assert abs(round(g - fe, 3) - lim) < 1e-9, (g, fe, lim)
    assert abs(round(clr + pos, 3) - fe_x) < 1e-9, (clr, pos, fe_x)            # exact feeler = 0.45 + 0.308
    assert fe >= fe_x - 1e-9 and fe - 0.05 < fe_x, (fe, fe_x)                    # next 0.05-step leaf at or above
    assert abs(round(lim + clr + pos, 3) - need_lim) < 1e-9, (lim, need_lim)
    assert abs(round(g - need_lim, 3) - res_g) < 1e-9, (g, need_lim, res_g)
    assert abs(l0 + R_in + t - assumed) < 1e-9, (l0, R_in, t, assumed)
    assert abs(P.d("bead_edge") + P.d("bead_w") + P.d("bead_pocket_min") + P.d("land_break") - land_a1) < 1e-9
    assert abs(round(P.d("border") - bezel - land_a1, 3) - g_max) < 1e-9, (bezel, land_a1, g_max)
    m_p = re.search(r"border ([\d.]+) holds by the budget: needed gap <= ([\d.]+) \+ ([\d.]+) \+ ([\d.]+) = ([\d.]+) "
                    r"<= g_bend ([\d.]+) \(reserve ([\d.]+)\) <= limit ([\d.]+) \(border ([\d.]+) - bezel ([\d.]+) - "
                    r"land ([\d.]+); reserve ([\d.]+)\)", ft["pass"])
    assert m_p, ("master fold_test.pass: wording changed", ft["pass"])
    pv = [float(m_p.group(i)) for i in range(1, 13)]
    assert pv[:10] + [pv[10]] == [P.d("border"), lim, clr, round(pos, 2), need_lim, g, res_g, g_max, P.d("border"),
                                  bezel, land_a1], pv
    res_lim = pv[11]
    assert abs(round(g_max - need_lim, 3) - res_lim) < 1e-9, (g_max, need_lim, res_lim)
    m_q = re.search(r"a tail up to ([\d.]+) keeps >= ([\d.]+) at the RSS position and up to ([\d.]+) keeps > 0 at the "
                    r"full worst case.*?holds only up to ([\d.]+) \(CTP margin ([\d.]+)", ft["pass"])
    assert m_q, ("master fold_test.pass: 3D results not found", ft["pass"])
    tail_rss, tail_wc, tail_int, margin = (float(m_q.group(i)) for i in (1, 3, 4, 5))
    of1 = P._use("open_findings.1_bend_zone_clearance_worst_case",
                 P.raw["open_findings"]["1_bend_zone_clearance_worst_case"])
    ctp_wc = of1["measured_GF-2.1_mm"]["CTP"]["full_WC"]
    assert abs(round(ctp_wc - clr, 3) - margin) < 1e-9, (ctp_wc, margin)
    assert abs(bz["results_GF-2.1"]["CTP"]["at_WC"] - ctp_wc) < 1e-9
    mn = P._use("open_findings.margins_note_GF-2.1", P.raw["open_findings"]["margins_note_GF-2.1"])
    assert ("+%s mm" % ("%.3f" % margin)) in mn, (margin, mn)
    m_f = re.search(r"Border ([\d.]+) holds while g <= ([\d.]+) \(g_bend raised to g\); above that border = ([\d.]+) "
                    r"\+ g \+ ([\d.]+) \(e\.g\. ([\d.]+) covers g <= ([\d.]+)\)", ft["fail"])
    assert m_f, ("master fold_test.fail: wording changed", ft["fail"])
    fv = [float(m_f.group(i)) for i in range(1, 7)]
    assert fv[:4] == [P.d("border"), g_max, bezel, land_a1], fv
    assert abs(round(fv[4] - bezel - land_a1, 3) - fv[5]) < 1e-9, fv
    border_next, g_next = fv[4], fv[5]
    m_a = re.search(r"passes with ([\d.]+) to spare \(gap ([\d.]+) at the assumed tail\)", ft["assumed_tail_note"])
    spare, gap_assumed = float(m_a.group(1)), float(m_a.group(2))
    assert abs(round(lim - assumed, 3) - spare) < 1e-9 and abs(round(g - assumed, 3) - gap_assumed) < 1e-9
    g_prev = P.change("driving_parameters.g_bend.value")[0]          # the GF-2.0 slot: that gauge is not valid
    assert "is not valid" in ft["about"] and ("%.2f" % g_prev) in ft["about"], ft["about"]
    m4 = re.search(r">= (\d+) x ([\d.]+)", P.dnote("tail_R_in_min"))
    r_factor = float(m4.group(1))
    xm = 0.5 * (sl.x0 + sl.x1)
    L_slot = sl.x1 - sl.x0
    pad = tg["pad_len"]
    D = tg["depth"]
    x0, x1 = -L_slot / 2.0 - pad, L_slot / 2.0 + pad
    outline = [(x0, 0.0), (-L_slot / 2.0, 0.0), (-L_slot / 2.0, g), (L_slot / 2.0, g), (L_slot / 2.0, 0.0),
               (x1, 0.0), (x1, g + D), (x0, g + D)]
    flat = H - R
    nose = [(g + R - R * math.cos(math.radians(a)), flat + R * math.sin(math.radians(a))) for a in range(0, 91, 5)]
    section = [(g, 0.0), (g + D, 0.0), (g + D, H), (g + R, H)] + nose[::-1][1:]
    dv = P.d("div_x") - xm
    tails = {}
    for nm in ("CTP", "TFT"):
        pts, trd = G.tail_route(nm)
        tails[nm] = dict(x=(trd["x_exit"][0] - xm, trd["x_exit"][1] - xm),
                         x_all=(min(s[2] for s in trd["outline_developed"]) - xm,
                                max(s[3] for s in trd["outline_developed"]) - xm),
                         h_exit=trd["Z_exit"] - P.level("Z_CTP_FRONT"),
                         s_end=trd["S_end_y"] - P.val("carried_over_from_v2", "panel_y1"),
                         route=[(y - P.val("carried_over_from_v2", "panel_y1"), Z - P.level("Z_CTP_FRONT"))
                                for y, Z in pts])
    panel = (P.val("carried_over_from_v2", "panel_x0") - xm, P.val("carried_over_from_v2", "panel_x1") - xm)
    return dict(tg=tg, g=g, R=R, H=H, clr=clr, pos=pos, pos_wc=pos_wc, fe=fe, lim=lim, fe_x=fe_x, ft=ft,
                need_lim=need_lim, res_g=res_g, res_lim=res_lim, g_max=g_max, land_a1=land_a1, bezel=bezel,
                assumed=assumed, spare=spare, gap_assumed=gap_assumed, border_next=border_next, g_next=g_next,
                tail_rss=tail_rss, tail_wc=tail_wc, tail_int=tail_int, margin=margin, ctp_wc=ctp_wc, g_prev=g_prev,
                bz=bz, exit_tol=bz["exit_Z_tol_mm"], t_tol=bz["tail_t_tol_mm"],
                r_factor=r_factor, xm=xm, L_slot=L_slot, pad=pad, D=D, x0=x0, x1=x1, outline=outline, flat=flat,
                section=section, div=(dv - P.d("div_t") / 2.0, dv + P.d("div_t") / 2.0), tails=tails, panel=panel,
                l0=P.d("tail_straight_l0"), R_in=P.d("tail_R_in_min"), t=P.d("tail_t"),
                panel_t=P.val("carried_over_from_v2", "panel_t"), sl=sl)


def write_dxf(path, P, C, G, T):
    doc, msp = new_dxf(LAYERS)
    dxf_poly(msp, [(x, -y, 0.0) for x, y in T["outline"]], "GAUGE")
    yt = T["g"] + T["R"]
    msp.add_line((-T["L_slot"] / 2.0, -yt), (T["L_slot"] / 2.0, -yt), dxfattribs={"layer": "NOSE_TANGENT"})
    for xd in T["div"]:
        msp.add_line((xd, -(T["g"] + T["R"] + 0.5)), (xd, -(T["g"] + T["D"] - 1.0)), dxfattribs={"layer": "ENGRAVE"})
    msp.add_line((-T["L_slot"] / 2.0, -T["lim"]), (T["L_slot"] / 2.0, -T["lim"]), dxfattribs={"layer": "LIMIT_REF"})
    msp.add_line((T["panel"][0], 0.0), (T["panel"][1], 0.0), dxfattribs={"layer": "PANEL_REF"})
    # section profile 1:1 beside the plan (y -> x, h -> y), closed
    ox, oy = T["x1"] + 20.0, -T["D"]
    dxf_poly(msp, [(ox + y, oy + h, 0.0) for y, h in T["section"]], "SECTION")
    dxf_text(msp, "GF-D21 TAIL FOLD GAUGE %s - plan seen from above (panel CTP face down above the gauge): x = abs x - "
             "%s, y = -distance from the panel edge face; mm. NOSE_TANGENT = end of the R%s nose on the top face; "
             "LIMIT_REF = %s line: tail outer surface limit from the panel edge face (slot %s - feeler %s, master "
             "fold_test), not cut." % (P.revision, n(T["xm"]), n(T["R"]), n2(T["lim"]), n2(T["g"]), n2(T["fe"])),
             T["x0"], -(T["g"] + T["D"] + 8.0), 2.5)
    dxf_text(msp, "SECTION (height above the CTP front), 1:1", ox, oy + T["H"] + 3.0, 2.0)
    doc.saveas(path)


def make(out_dir=OUT_DIR):
    P, C = Params(), Choices()
    G = Geom(P)
    T = gauge_data(P, C, G)
    tg, ts = T["tg"], C("tg_test")
    base = os.path.join(out_dir, "GF_TailFoldGauge")
    write_dxf(base + ".dxf", P, C, G, T)
    sh = Sheet()
    sh.frame()
    # ---------------------------------------------------------------- plan 1:1 (from above, panel face down)
    ox, oy = 112.0, 252.0
    Pp = lambda x, y: (ox + x, oy - y)
    sh.T(16.0, 279.0, "GAUGE - PLAN seen from above (panel lies CTP face down on a flat plate)   1 : 1", fs=8.0,
         weight="bold")
    sh.T(16.0, 274.5, "The gauge forms the %s bend-gap slot with the panel edge face over the tail span; its end pads "
                      "touch the panel edge outside the tails." % n(T["g"]), fs=6.0)
    pa, pb = T["panel"]
    ph = 14.0                                                          # panel strip drawn (bottom edge zone)
    sh.poly([Pp(pa, 0), Pp(pb, 0), Pp(pb, -ph), Pp(pa, -ph)], fc="#f4c79a", ec="0.3", w=THIN, geom=False)
    sh.T(*Pp(pa + 2.0, -ph + 2.5), "panel, bottom edge zone (CTP face down)", fs=6.0, va="center")
    for nm, col in (("CTP", C_CTP), ("TFT", C_TFT)):
        xa, xb = T["tails"][nm]["x"]
        sh.L([Pp(xa, 0)[0], Pp(xb, 0)[0]], [Pp(0, -0.6)[1]] * 2, w=1.2, c=col, geom=False)
        sh.T(Pp(0.5 * (xa + xb), 0)[0], Pp(0, -2.0)[1], "%s tail exit x %s-%s" % (
            nm, n(xa + T["xm"], 2), n(xb + T["xm"], 2)), fs=5.8, ha="center", va="bottom", color=col)
    sh.poly([Pp(x, y) for x, y in T["outline"]], fc="#e9eaec", ec="k", w=THICK)
    yt = T["g"] + T["R"]
    sh.L([Pp(-T["L_slot"] / 2.0, 0)[0], Pp(T["L_slot"] / 2.0, 0)[0]], [Pp(0, yt)[1]] * 2, w=XTHIN, c="k",
         geom=False, dashes=(3, 1.5))
    sh.L([Pp(-T["L_slot"] / 2.0, 0)[0], Pp(T["L_slot"] / 2.0, 0)[0]], [Pp(0, T["lim"])[1]] * 2, w=THIN, c=C_LIM,
         geom=False, dashes=(5, 1.5))
    for xd in T["div"]:
        sh.L([Pp(xd, 0)[0]] * 2, [Pp(0, yt + 0.8)[1], Pp(0, T["g"] + T["D"] - 1.2)[1]], w=XTHIN, c="#2e8b57",
             geom=False)
    # plan dimensions: chain pad | slot | pad, overall, depth; the slot width with a leader into the body
    yb = Pp(0, T["g"] + T["D"])[1]
    yc1, yc2 = yb - 6.0, yb - 12.0
    sh.dim_h(*Pp(T["x0"], T["g"] + T["D"]), *Pp(-T["L_slot"] / 2.0, T["g"]), yc1, n(T["pad"]), fs=6.0)
    sh.dim_h(*Pp(-T["L_slot"] / 2.0, T["g"]), *Pp(T["L_slot"] / 2.0, T["g"]), yc1,
             "%s = bend-gap slot length (frame)" % n(T["L_slot"]), fs=6.5)
    sh.dim_h(*Pp(T["L_slot"] / 2.0, T["g"]), *Pp(T["x1"], T["g"] + T["D"]), yc1, n(T["pad"]), fs=6.0)
    sh.dim_h(*Pp(T["x0"], T["g"] + T["D"]), *Pp(T["x1"], T["g"] + T["D"]), yc2, n(T["x1"] - T["x0"]), fs=6.5)
    xr = Pp(T["x1"], 0)[0]
    sh.dim_v(*Pp(T["x1"], 0), *Pp(T["x1"], T["g"] + T["D"]), xr + 5.0, n(T["g"] + T["D"]), fs=6.0, side="right")
    xg = -T["L_slot"] / 2.0 + 5.0
    sh.dim_v(*Pp(xg, 0), *Pp(xg, T["g"]), Pp(xg, 0)[0], None, arrows="out", c="k", ext=False)
    sh.leader(*Pp(xg, T["g"] + 0.2), Pp(xg + 4.0, 0)[0], Pp(0, T["g"] + 7.5)[1],
              "slot %s +%s/0 = g_bend (between the pad faces and the recess face)" % (n(T["g"]), n(tg["tol_g"][0])),
              fs=6.0, head="none", allow_geom=True)
    sh.T(*Pp(T["div"][1] + 2.0, T["g"] + T["D"] - 3.0), "engraved pair: divider rib x %s-%s (ref.)" % (
        n(T["div"][0] + T["xm"], 2), n(T["div"][1] + T["xm"], 2)), fs=5.6, color="#2e8b57", va="center")
    sh.T(Pp(T["x0"], 0)[0], yc2 - 6.0, "black dashed: end of the R%s nose on the top face;  red dashed: the %s line "
                                        "of the test = tail outer surface limit (slot %s - feeler %s; not cut)" % (
                                            n(T["R"]), n2(T["lim"]), n2(T["g"]), n2(T["fe"])), fs=5.8)
    # ---------------------------------------------------------------- section A-A 5:1 with the folded tails
    k = 5.0
    y0w, y1w, h0w, h1w = -7.0, T["g"] + T["D"] + 0.5, -1.0, 8.0
    sx0, sy0 = 238.0, 208.0
    S = lambda y, h: (sx0 + k * (y - y0w), sy0 + k * h)
    sh.T(214.0, 270.0, "SECTION A-A through the gauge, both tails folded (test set-up)   %g : 1" % k, fs=7.5,
         weight="bold")
    sh.poly([S(y0w, 0), S(y1w, 0), S(y1w, h0w), S(y0w, h0w)], fc="#dfe3e8", ec="k", w=THIN, hatch="////")
    sh.poly([S(y0w, 0), S(0, 0), S(0, T["panel_t"]), S(y0w, T["panel_t"])], fc="#f4c79a", ec="0.3", w=THIN)
    sh.poly([S(*p) for p in T["section"]], fc=C_G, ec="k", w=THIN, hatch="\\\\\\\\")
    for nm, col in (("CTP", C_CTP), ("TFT", C_TFT)):
        rt = []                                           # exit, straight, both bends (to S_end_y), then the leg
        for p in T["tails"][nm]["route"]:
            rt.append(p)
            if p[0] >= T["tails"][nm]["s_end"] - 1e-6:
                break
        rt.append((y1w - 0.3, rt[-1][1]))
        q = [S(*p) for p in rt]
        sh.L([p[0] for p in q], [p[1] for p in q], w=T["t"] * k, c=col, geom=False)
    xl = S(T["lim"], 0)[0]
    rc = T["R"] + T["fe"]                 # feeler line: gauge face and nose offset by the 0.70 feeler (fold_test)
    off = [(T["lim"], 0.0), (T["lim"], T["flat"])] + [
        (T["g"] + T["R"] - rc * math.cos(math.radians(a)), T["flat"] + rc * math.sin(math.radians(a)))
        for a in range(0, 91, 5)]
    q = [S(*p) for p in off]
    sh.L([p[0] for p in q], [p[1] for p in q], w=THIN, c=C_LIM, geom=False, dashes=(5, 1.5))
    sh.T(xl + 1.0, S(0, h0w)[1] - 3.2, "%s feeler line (tail outer surface within %s of the panel edge): the tail "
         "stays outside it" % (n2(T["fe"]), n2(T["lim"])), fs=6.0, ha="left", color=C_LIM)
    sh.dim_h(*S(0, T["panel_t"]), *S(T["g"], T["H"]), S(0, h1w)[1] + 6.5, "%s" % n(T["g"]), fs=6.0)
    sh.dim_h(*S(T["lim"], 0.5), *S(T["g"], 0.5), S(0, 0.5)[1], None, arrows="out", ext=False, c=C_LIM)
    xr2 = S(y1w, 0)[0]
    sh.dim_v(*S(y1w, 0), *S(y1w, T["H"]), xr2 + 3.0, "%s" % n(T["H"]), fs=6.0, side="right")
    an = math.radians(125.0)
    pn_ = S(T["g"] + T["R"] + T["R"] * math.cos(an), T["flat"] + T["R"] * math.sin(an))
    sh.leader(pn_[0], pn_[1], S(T["g"] + 7.5, 0)[0], S(0, T["H"] + 1.0)[1], "R%s ±%s nose, polished" % (
        n(T["R"]), n(tg["tol_R"])), fs=6.0, head="arrow")
    lab = [((-3.5, T["panel_t"] / 2.0), 6.2, "panel %s (CTP + LCM)" % n(T["panel_t"])),
           ((0.25, T["tails"]["TFT"]["h_exit"]), 3.3, "TFT exit %s above the CTP front [E]" % n(
               T["tails"]["TFT"]["h_exit"], 2)),
           ((0.25, T["tails"]["CTP"]["h_exit"]), 0.6, "CTP exit %s [E]" % n(T["tails"]["CTP"]["h_exit"], 2))]
    for (y, h), hy, t in lab:
        sh.leader(*S(y, h), S(y0w, 0)[0] - 2.0, S(0, hy)[1], t, fs=5.8, head="dot", ha="right")
    sh.T(S(T["g"] + T["D"] / 2.0 + 1.5, T["H"] / 2.0)[0], S(0, T["H"] / 2.0)[1],
         "GAUGE, %s" % tg["material"].split(",")[0], fs=6.0, ha="center", va="center", allow_geom=True, bg="white")
    sh.T(S(T["g"] + 4.5, 0)[0], S(0, 6.9)[1], "the tails run on over the top face (= bridge floor, %s above the CTP "
                                               "front)" % n(T["H"], 2), fs=5.6)
    # ---------------------------------------------------------------- notes, pass criteria, record sheet
    mat = tg["material"]
    gauge_notes = [
        "Material %s; all faces machined. Slot %s +%s/%s between the pad faces and the recess face (check with "
        "%s / %s gauge blocks); height %s ±%s = land-plate back above the CTP front (master levels); base flat %s; "
        "nose R%s ±%s tangent, polished Ra <= %s, no burr. Other edges broken 0.2." % (
            mat, n(T["g"]), n(tg["tol_g"][0]), ("%g" % tg["tol_g"][1]), n2(T["g"]), n2(T["g"] + tg["tol_g"][0]),
            n(T["H"], 2), n(tg["tol_h"]), n(tg["flat"]), n(T["R"]), n(tg["tol_R"]), n(tg["ra_nose"])),
        "Engrave on the top face: 'GF-D21 g %s R%s' and the divider-rib pair (ref.); the %s line (tail outer "
        "surface limit = slot - %s feeler) is NOT cut (reference for the feeler check). Keep the slot at %s (master "
        "fold_test)." % (n(T["g"]), n(T["R"]), n2(T["lim"]), n2(T["fe"]), n2(T["g"])),
        "A gauge made to the GF-2.0 sheet (slot %s) is NOT valid for %s: make the gauge new at slot %s (the gauge "
        "slot is g_bend)." % (n2(T["g_prev"]), P.revision, n2(T["g"])),
        "Also used in jig J2 as the fold former (GF-D30 sheet 2, step 3).",
    ]
    steps = [
        "Panel CTP face down on a clean flat plate (lint-free cloth, no pressure on the tails); tails flat as "
        "delivered. Wear gloves; ESD protection.",
        "Before folding, record: free straight l0 at each exit (panel edge face -> first bending point; FPC bond, "
        "glue bead or coverlay end), tail thickness in the bend zone (micrometer, 3 points per tail), layer count "
        "(back-light / maker drawing), exit heights above the CTP front, the panel bottom edge to the AA.",
        "Push the gauge against the panel edge face (end pads on the panel edge, recess over both tails).",
        "Fold each tail up and back towards the LCM, by hand and unforced, around the gauge's R%s edge and lay it "
        "over the top face; do not press the fold." % n(T["R"]),
        "Check the fit (criterion 1, master fold_test): with the panel held at its nominal position by the gauge, the "
        "%s feeler must pass between each tail's outer surface and the gauge face / nose over the whole tail width "
        "(tail outer surface within %s of the panel edge); record the largest feeler that passes (0.05 steps). "
        "Inspect the exit and the bond at %dx." % (n2(T["fe"]), n2(T["lim"]), ts["mag"]),
        "Unfold and fold %d times, then leave folded %d min; inspect again at %dx." % (ts["cycles"], ts["hold_min"],
                                                                                    ts["mag"]),
        "Then: full fit in a printed %s frame with display and touch running (concept_gf2.md 2.4)." % P.revision,
    ]
    sh.T(16.0, 196.0, "FOLD TEST on one real panel (gate before the frame tool is cut)", fs=7.2, weight="bold")
    y = sh.notes(16.0, 194.5, 190.0, steps, fs=5.9, gap=0.4)
    y = sh.notes(16.0, y - 1.5, 190.0, gauge_notes, fs=5.9, head="GAUGE (make)", head_fs=7.2, gap=0.4)
    meaning = ["PASS: %s." % T["ft"]["pass"], "FAIL: %s." % T["ft"]["fail"]]
    y = sh.notes(16.0, y - 1.5, 190.0, meaning, fs=5.8, head="WHAT PASS AND FAIL MEAN (master fold_test, as stated)",
                 head_fs=7.2, gap=0.4, numbered=False)
    # pass criteria
    crit = [["#", "criterion (each tail)", "pass"],
            ["1", "fold fit (master fold_test): %s" % T["ft"]["rule"],
             "PASS (%s passes): needed gap <= %s + %s + %s = %s <= g_bend %s (reserve %s) <= limit %s (reserve %s): "
             "border %s holds by the budget. FAIL (%s does not pass): criterion 8" % (
                 n2(T["fe"]), n2(T["lim"]), n2(T["clr"]), n2(T["pos"]), "%.3f" % T["need_lim"], n2(T["g"]),
                 "%.3f" % T["res_g"], n2(T["g_max"]), "%.3f" % T["res_lim"], n(P.d("border")), n2(T["fe"]))],
            ["2", "no lifting, peeling, whitening, crease or crack at the exit / bond after %d cycles + %d min" % (
                ts["cycles"], ts["hold_min"]), "none at %dx" % ts["mag"]],
            ["3", "free straight l0 at the exit", "<= %s assumed; record" % n(T["l0"])],
            ["4", "tail thickness in the bend zone", "<= %s (R_in %s >= %d x t); record" % (
                n(T["t"]), n(T["R_in"]), T["r_factor"])],
            ["5", "layers in the bend zone", "single layer as assumed (master g_bend note); double-sided = FAIL "
                                             "(outside the budget)"],
            ["6", "exit heights above the CTP front (estimated TFT %s, CTP %s)" % (
                n(T["tails"]["TFT"]["h_exit"], 2), n(T["tails"]["CTP"]["h_exit"], 2)),
             "record; within ±%s the route holds" % n(ts["exit_z_tol"])],
            ["7", "maker allows the fold back towards the LCM; parts / stiffeners on the TFT tail's wide part",
             "record (ask the maker)"],
            ["8", "border from the measured fit (master fold_test.fail): tail extent d = %s - largest passing "
                  "feeler; needed gap g = d + %s + %s; border = %s + g + %s (land %s = %s + %s + %s + break %s, A1 "
                  "measured to the break edge)" % (
                n2(T["g"]), n2(T["clr"]), n2(T["pos"]), n2(T["bezel"]), n2(T["land_a1"]), n2(T["land_a1"]),
                n(P.d("bead_edge")), n(P.d("bead_w")), n(P.d("bead_pocket_min")), n(P.d("land_break"))),
             "g <= %s: border %s holds (g_bend raised to g); else border = %s + g + %s (e.g. %s covers g <= %s); "
             "not a thinner bead" % (n2(T["g_max"]), n(P.d("border")), n2(T["bezel"]), n2(T["land_a1"]),
                                     n(T["border_next"]), n2(T["g_next"]))]]
    xc = 214.0
    sh.T(xc, 196.0, "PASS CRITERIA (master fold_test / g_bend / border / tail notes)", fs=7.2, weight="bold")
    yc = sh.table_wrapped(xc, 194.5, [6, 102, 86], crit, fs=5.8)
    res_en = ("Reserve: at the %s pass line the needed gap is %s, %s below g_bend %s and %s below the border-%s limit "
              "%s; the assumed tail (%s) passes with %s to spare." % (
                  n2(T["fe"]), "%.3f" % T["need_lim"], "%.3f" % T["res_g"], n2(T["g"]), "%.3f" % T["res_lim"],
                  n(P.d("border")), n2(T["g_max"]), n2(T["assumed"]), n2(T["spare"])))
    mar_en = ("Margin: at the full worst case the CTP tail keeps %s to the R%s nose against the concept's %s - a margin "
              "of only %s mm. Passing the gauge guarantees the RSS criterion (>= %s at the RSS panel position, > 0 at "
              "the worst case: tail up to %s / %s), NOT the %s full-worst-case intent, which holds only for a tail up "
              "to %s; no 0.05-step feeler can check that, because the assumed tail (%s) must pass." % (
                  "%.3f" % T["ctp_wc"], n(T["R"]), n2(T["clr"]), "%.3f" % T["margin"], n2(T["clr"]), n2(T["tail_rss"]),
                  n2(T["tail_wc"]), n2(T["clr"]), "%.3f" % T["tail_int"], n2(T["assumed"])))
    for txt, bold in ((res_en, True), (mar_en, True)):
        for ln in sh.wrap(txt, 194.0, 6.0):
            yc -= 2.7
            sh.T(xc, yc, ln, fs=6.0, weight="bold", color=C_LIM, va="center")
        yc -= 0.6
    fe_en = ("Feeler: the exact feeler for the budget is %s (= %s + %s RSS); %s is the next 0.05-step leaf at or above "
             "it (safe side). Master fold_test, open_findings.margins_note_GF-2.1." % (
                 "%.3f" % T["fe_x"], n2(T["clr"]), "%.3f" % T["pos"], n2(T["fe"])))
    for ln in sh.wrap(fe_en, 194.0, 5.8):
        yc -= 2.6
        sh.T(xc, yc, ln, fs=5.8, va="center")
    yc -= 1.0
    rec = [["record", "TFT", "CTP", "unit"],
           ["free straight l0", "", "", "mm"], ["thickness (3 points)", "", "", "mm"], ["layer count", "", "", "-"],
           ["exit height above the CTP front", "", "", "mm"],
           ["largest feeler that passes, tail outer surface -> gauge face / nose (pass >= %s)" % n2(T["fe"]), "", "",
            "mm"],
           ["tail extent = %s - largest feeler" % n2(T["g"]), "", "", "mm"],
           ["lifting / crease after the cycles (y / n)", "", "", "-"], ["needed gap (criterion 8)", "", "", "mm"],
           ["panel bottom edge to AA", "", "", "mm"]]
    sh.T(xc, yc - 3.0, "RECORD (panel serial ________   date ________   by ________)", fs=7.0, weight="bold")
    yr = sh.table_wrapped(xc, yc - 4.5, [80, 42, 42, 30], rec, fs=5.8)
    trn = [
        "Panel CTP yüzü aşağıda düz ve temiz bir plakada; kuyruklar teslim edildiği gibi düz. Katlamadan önce "
        "kaydedin: her çıkışta serbest düz kısım l0, büküm bölgesinde kuyruk kalınlığı (3 nokta), katman sayısı, "
        "CTP ön yüzünden çıkış yükseklikleri.",
        "Mastarı panel kenarına dayayın (panel nominal konumda); her kuyruğu elle, zorlamadan R%s burnu üzerinden "
        "geriye (LCM'ye doğru) katlayın. %s mm sentil, kuyruğun dış yüzeyi ile mastar yüzü / burnu arasından tüm "
        "kuyruk genişliği boyunca geçmeli (kuyruk dış yüzeyi panel kenarından en fazla %s mm); geçen en kalın "
        "sentili (0.05 adımlarla) kaydedin. Geçerse: gerekli boşluk <= %s <= g_bend %s (pay %s) <= sınır %s (pay %s), "
        "%s kenar boşluğu bütçeye göre geçerlidir; varsayılan kuyruk (%s) %s payla geçer. Geçmezse: kriter 8. "
        "Bütçeye tam karşılık gelen sentil %s'dir; %s bir sonraki 0.05 adımlı yaprak ve güvenli taraftadır. Çıkışı "
        "ve yapıştırmayı %dx büyütmeyle kontrol edin." % (
            n(T["R"]), n2(T["fe"]), n2(T["lim"]), "%.3f" % T["need_lim"], n2(T["g"]), "%.3f" % T["res_g"],
            n2(T["g_max"]), "%.3f" % T["res_lim"], n(P.d("border")), n2(T["assumed"]), n2(T["spare"]),
            "%.3f" % T["fe_x"], n2(T["fe"]), ts["mag"]),
        "%d kez açıp katlayın, %d dk katlı bırakın, yeniden kontrol edin: kalkma, soyulma, beyazlama, kırık yok." % (
            ts["cycles"], ts["hold_min"]),
        "Ölçülen kuyruk boyu d = %s - geçen en kalın sentil; gerekli boşluk g = d + %s + %s. g <= %s ise %s kenar "
        "boşluğu geçerli (g_bend g'ye yükseltilir); değilse kenar boşluğu = %s + g + %s (ör. %s, g <= %s için); daha "
        "ince kordon değil. Çift katlı kuyruk = RED." % (
            n2(T["g"]), n2(T["clr"]), n2(T["pos"]), n2(T["g_max"]), n(P.d("border")), n2(T["bezel"]),
            n2(T["land_a1"]), n(T["border_next"]), n2(T["g_next"])),
        "UYARI: en kötü durumda CTP kuyruğunun R%s burnuna mesafesi %s (hedef %s): pay yalnızca %s mm. Mastardan "
        "geçmek RSS kriterini garanti eder, %s en-kötü-durum hedefini garanti ETMEZ (o yalnızca %s'e kadar olan "
        "kuyruk için geçerlidir; varsayılan kuyruk %s geçmek zorunda olduğundan hiçbir 0.05 adımlı sentil bunu "
        "ölçemez)." % (n(T["R"]), "%.3f" % T["ctp_wc"], n2(T["clr"]), "%.3f" % T["margin"], n2(T["clr"]),
                       "%.3f" % T["tail_int"], n2(T["assumed"])),
        "Mastar: %s; yuva %s +%s/0, yükseklik %s, burun R%s parlatılmış. GF-2.0 resmine göre yapılmış mastar (yuva "
        "%s) %s için GEÇERSİZDİR: mastarı yuva %s ile yeniden yapın." % (
            "POM-C (asetal)", n(T["g"]), n(tg["tol_g"][0]), n(T["H"], 2), n(T["R"]), n2(T["g_prev"]), P.revision,
            n2(T["g"])),
    ]
    yt = sh.notes(16.0, y - 2.0, 190.0, [tr(x) for x in trn], fs=5.8, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.4)
    sh.title_block({
        "title": "TAIL FOLD GAUGE AND FOLD TEST - GF",
        "subtitle": "real-panel gate for the %s border and g_bend %s  /  FPC kuyruk katlama mastarı ve testi" % (
            n(P.d("border")), n(T["g"])),
        "source": "from %s (g_bend, bend_nose_R, bend_gap_slot, div_x, levels, tail_route, notes); gauge make: "
                  "drafting_choices.json" % master_ref(P),
        "project": "files: GF_TailFoldGauge.dxf (gauge plan + section, mm) + this sheet",
        "change": "%s. Gauge made new at slot %s (the GF-2.0 gauge, slot %s, is not valid); fold fit per master "
                  "fold_test: feeler %s, tail within %s, reserves %s / %s; CTP full-worst-case margin %s mm." % (
                      rev_note(P), n2(T["g"]), n2(T["g_prev"]), n2(T["fe"]), n2(T["lim"]), "%.3f" % T["res_g"],
                      "%.3f" % T["res_lim"], "%.3f" % T["margin"]),
        "dwg": "GF-D21", "rev": P.revision, "scale": "1:1, %g:1" % k, "date": datetime.date.today().isoformat(),
        "drawn": "make_tailgauge.py",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(base + ".pdf", base + ".png", dpi=200)
    return {"files": [base + ".dxf", base + ".pdf", base + ".png"], "layout_issues": issues,
            "params_used": dict(sorted(P.used.items())), "choices_used": C.used, "steps_en": steps, "notes_tr": trn,
            "criteria": crit, "gauge": {k_: (v if not isinstance(v, float) else round(v, 4))
                                        for k_, v in T.items() if k_ in ("g", "R", "H", "lim", "clr", "pos", "fe", "fe_x", "need_lim", "res_g", "res_lim", "margin", "pos_wc", "g_max",
                                                                         "border_next", "L_slot", "pad", "D", "xm",
                                                                         "div", "flat")},
            "lowest_y": [round(y, 1), round(yr, 1), round(yt, 1)]}


if __name__ == "__main__":
    r = make()
    print("issues:", len(r["layout_issues"]), r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
    print(r["gauge"])
