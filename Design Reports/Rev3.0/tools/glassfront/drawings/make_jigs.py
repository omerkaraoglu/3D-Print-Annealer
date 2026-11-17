"""Jig drawings for a local machinist (aluminium plate): J2 flush plate (GF-2.0: 2 sheets, the second one for the
FPC tail handling) and J1 optical-bonding alignment fixture. A3 sheets (PDF + PNG) and DXFs. Product positions come
from the master; jig values from drafting_choices.json.

  <venv>/Scripts/python.exe make_jigs.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Jig_J2.pdf (2 pages),
                                              GF_Jig_J2_p1.png, GF_Jig_J2_p2.png, GF_Jig_J2.dxf, GF_Jig_J1.*
"""
import datetime
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (Params, Choices, Rect, OUT_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text,
                       bulge_to_points, rev_note, master_ref, prev_rev)
from gf_geom import Geom
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT, lw, clip_poly

C_REF, C_PIN, C_STOP, C_VAC = "#3b6fb6", "#c0392b", "#2e8b57", "#7b4fa0"
C_TAIL, C_CTP, C_TFT, C_DIM = "#b35c00", "#6a5fb0", "#d35400", "#8a1c1c"


def stops_uv(G, C):
    """three glass stops (centre of the stop pin, front view): two on the top edge, one on the front-view left edge"""
    d = C("j2_stop_d")
    su = C("j2_stop_u")
    g = G.glass
    return {"S1": (su, g.y1 + d / 2.0), "S2": (-su, g.y1 + d / 2.0), "S3": (g.x0 - d / 2.0, 0.0)}


# ================================================================================================================ J2
def j2_tail_geom(P, C, G):
    """GF-2.0 tail handling in J2 (front view u, v; heights d above the plate = flush plane): tail holder post TH,
    guide card, tail spans, all from the master + drafting_choices (j2_tail_holder, j2_tail_card)"""
    th = C("j2_tail_holder")
    cd = C("j2_tail_card")
    fv = G.fv
    yv = G.tail_vertical_y()                                   # abs y of the vertical legs' centre line
    t = P.d("tail_t")
    y_in = yv - t / 2.0                                        # tail face on the panel side
    y_out = yv + t / 2.0                                       # tail face on the bridge side
    sl = P.rect("bend_gap_slot")
    panel_y1 = P.val("carried_over_from_v2", "panel_y1")
    tails = {}
    for nm in ("CTP", "TFT"):
        _, tr_ = G.tail_route(nm)
        od = tr_["outline_developed"]
        x0 = min(s[2] for s in od)
        x1 = max(s[3] for s in od)
        tails[nm] = dict(exit=tr_["x_exit"], x_all=(x0, x1), end=(od[-1][2], od[-1][3]), L=tr_["L"],
                         Z_exit=tr_["Z_exit"], R_c=tr_["R_centre"], straight=tr_["straight"])
    sx_c = 0.5 * (sl.x0 + sl.x1)                               # slot centre (abs x)
    card = dict(t=cd["t"], w=cd["w"], x=(sx_c - cd["w"] / 2.0, sx_c + cd["w"] / 2.0), y=(y_in - cd["t"], y_in),
                top=cd["top"], bottom=cd["bottom"], tab_w=cd["tab_w"], tab_min=cd["tab_min"])
    fl = G.flange
    post_uv = (0.0, fl.y0 - th["post_offset"])
    Zg = P.level("Z_GLASS_FRONT")
    d_back = P.level("Z_TROUGH_TOP") - Zg                      # frame back (bottom-wall top) above the plate
    tips = {nm: (T["Z_exit"] - Zg) + T["R_c"] + (T["L"] - T["straight"] - math.pi / 2.0 * T["R_c"])
            for nm, T in tails.items()}                        # tail end height when folded straight up
    return dict(th=th, card=card, tails=tails, y_vert=yv, y_in=y_in, y_out=y_out, slot=sl, panel_y1=panel_y1,
                post_uv=post_uv, post_d=th["post_d"], d_back=d_back, tips=tips, card_uv_v=fv.uv(0, y_in - cd["t"] / 2)[1],
                clear_face=sl.y1 - y_out, clear_shelf=(y_in - cd["t"]) - panel_y1)


def j2_dxf(path, P, C, G):
    pl = C("j2_plate")
    gw, gd_, gi, gp = C("j2_groove")
    M = lambda u, v: (-u, v)                       # plate view: seen from above, glass face down -> mirrored
    MR = lambda r: Rect(-r.x1, -r.x0, r.y0, r.y1, r.R, r.name)
    doc, msp = new_dxf([("PLATE", 7, "CONTINUOUS"), ("PIN_HOLES", 1, "CONTINUOUS"), ("STOP_HOLES", 3, "CONTINUOUS"),
                        ("TAIL_HOLDER", 4, "CONTINUOUS"), ("GROOVE_OPT", 200, "DASHED"), ("FLAT_ZONE", 6, "DASHDOT"),
                        ("REF", 5, "DASHED"), ("TEXT", 7, "CONTINUOUS")])
    dxf_rect(msp, Rect(-pl[0] / 2, pl[0] / 2, -pl[1] / 2, pl[1] / 2, 5.0), "PLATE")
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        msp.add_circle(M(f["u"], f["v"]), C("j2_pin_d") / 2.0, dxfattribs={"layer": "PIN_HOLES"})
        dxf_text(msp, "pin " + k, M(f["u"], f["v"])[0] + 4, M(f["u"], f["v"])[1] + 4, 2.5)
    for k, (u, v) in stops_uv(G, C).items():
        msp.add_circle(M(u, v), C("j2_stop_d") / 2.0, dxfattribs={"layer": "STOP_HOLES"})
        dxf_text(msp, k, M(u, v)[0] + 3, M(u, v)[1] + 3, 2.5)
    T = j2_tail_geom(P, C, G)
    msp.add_circle(M(*T["post_uv"]), T["post_d"] / 2.0, dxfattribs={"layer": "TAIL_HOLDER"})
    dxf_text(msp, "TH (tail-holder post hole)", M(*T["post_uv"])[0] + 8, M(*T["post_uv"])[1] - 1, 2.5)
    gr = MR(G.glass.offset(-gi))
    gr.R = max(gr.R, gw)
    dxf_rect(msp, gr.offset(gw / 2.0), "GROOVE_OPT")
    dxf_rect(msp, gr.offset(-gw / 2.0), "GROOVE_OPT")
    dxf_rect(msp, MR(G.lip_out.offset(3.0)), "FLAT_ZONE")
    for r in (G.glass, G.lip_out, G.flange, G.slot_bg):
        dxf_rect(msp, MR(r), "REF")
    dxf_text(msp, "GF JIG J2 FLUSH PLATE %s - working face seen from ABOVE (glass lies face 1 down: left/right mirrored "
             "to the front view). Origin = glass centre. mm." % P.revision, -pl[0] / 2, -pl[1] / 2 - 8, 3.0)
    doc.saveas(path)


def j2_sheet(P, C, G):
    sh = Sheet()
    sh.frame()
    pl = C("j2_plate")
    gw, gd_, gi, gp = C("j2_groove")
    flat, ra, tolp = C("j2_flatness"), C("j2_ra"), C("j2_pos_tol")
    pin_d, pin_h, pin_p = C("j2_pin_d"), C("j2_pin_proud"), C("j2_pin_press")
    st_d, st_h = C("j2_stop_d"), C("j2_stop_proud")
    pdt = C("j2_pin_detail")
    shim = C("j2_shim")                                   # shim body w x h, count per size (drafting choice)
    shim_sizes = P.val("jig_and_mounting_shims", "J2_glass_centring_shims")    # GF-1.1 round 4
    rule = {"en": P.val("jig_and_mounting_shims", "shim_rule") + "; " + C("shim_rule")["en_extra"],
            "tr": C("shim_rule")["tr"]}
    sizes = " / ".join("%.2f" % x for x in shim_sizes)
    T = j2_tail_geom(P, C, G)
    V = View(sh, 100.0, 176.0, 0.5, mirror=True)       # x = -u
    plate = Rect(-pl[0] / 2, pl[0] / 2, -pl[1] / 2, pl[1] / 2, 5.0)
    V.rrect(plate, ec="k", w=THICK)
    fz = G.lip_out.offset(3.0)
    V.rrect(fz, ec="#b0308f", w=THIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    for r, st in ((G.flange, (0, (6, 2))), (G.lip_out, (0, (2, 1.5))), (G.glass, (0, (4, 1.5)))):
        V.rrect(r, ec=C_REF, w=XTHIN, ls=st, geom=False)
    V.rrect(G.slot_bg, ec=C_TAIL, w=XTHIN, geom=False, fc="#f7e2c8")
    gr = G.glass.offset(-gi)
    gr.R = max(gr.R, gw)
    V.rrect(gr, ec=C_VAC, w=THIN, ls=(0, (3, 1.5)), geom=False)
    V.centreline((-pl[0] / 2 - 3, 0), (pl[0] / 2 + 3, 0))
    V.centreline((0, -pl[1] / 2 - 3), (0, pl[1] / 2 + 3))
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        x, y = V.P(f["u"], f["v"])
        sh.circle(x, y, pin_d / 2.0 * 0.5 + 0.4, ec=C_PIN, w=THIN, fc="#f6d4d0")
        sh.T(x + (2.5 if x > 100 else -2.5), y + (2.5 if y > 176 else -4.6), "pin " + k, fs=6.3, color=C_PIN,
             ha="left" if x > 100 else "right")
    for k, (u, v) in stops_uv(G, C).items():
        x, y = V.P(u, v)
        sh.circle(x, y, st_d / 2.0 * 0.5 + 0.3, ec=C_STOP, w=THIN, fc="#d4efdc")
        if k == "S3":
            sh.T(x + 2.6, y + 1.2, k, fs=6.5, color=C_STOP, weight="bold")
        else:
            sh.T(x, y - 4.2, k, fs=6.5, color=C_STOP, weight="bold", ha="center")
    # tail-holder post hole TH (GF-2.0)
    xt, yt_ = V.P(*T["post_uv"])
    sh.circle(xt, yt_, T["post_d"] / 2.0 * 0.5, ec=C_TAIL, w=THIN, fc="#f7e2c8")
    sh.T(xt + 4.0, yt_ - 1.0, "TH (sheet 2)", fs=6.5, color=C_TAIL, weight="bold", va="center")
    xs_, ys_ = V.P(G.slot_bg.x1, G.slot_bg.y1)        # plate view is mirrored: front-view x1 = left end on paper
    sh.T(xs_ + 0.8, ys_ + 1.2, "bend-gap slot (frame, ref.)", fs=5.8, color=C_TAIL)
    # dims (paper), positions to the datum
    F1, F2, F4 = G.F["F1"], G.F["F2"], G.F["F4"]
    top = V.P(0, plate.y1)[1]
    xa, ya = V.P(F1["u"], F1["v"])
    xb, yb = V.P(F2["u"], F2["v"])
    sh.dim_h(xa, ya, xb, yb, top + 6.0, "%s ±%s" % (n2(abs(F1["u"] - F2["u"])), n(tolp)), fs=7)
    left = V.P(plate.x1, 0)[0]
    xa, ya = V.P(F1["u"], F4["v"])
    xb, yb = V.P(F1["u"], F1["v"])
    sh.dim_v(xa, ya, xb, yb, left - 6.0, "%s ±%s" % (n2(abs(F1["v"] - F4["v"])), n(tolp)), fs=7)
    S = stops_uv(G, C)
    xa, ya = V.P(*S["S1"])
    xb, yb = V.P(*S["S2"])
    sh.dim_h(xa, ya, xb, yb, top + 13.0, "S1-S2 %s ±%s" % (n(abs(S["S1"][0] - S["S2"][0])), n(tolp)), fs=7)
    bot = V.P(0, plate.y0)[1]
    x0, y0 = V.P(0, 0)
    xs, ys = V.P(*S["S3"])
    sh.dim_h(x0, y0, xs, ys, bot - 7.0, "%s ±%s (S3 centre to datum)" % (n(abs(S["S3"][0])), n(tolp)), fs=6.5)
    right = V.P(plate.x0, 0)[0]
    sh.dim_v(*V.P(0, 0), *V.P(*S["S1"]), right + 6.0, "%s ±%s" % (n(S["S1"][1]), n(tolp)), fs=6.5, side="right")
    sh.dim_h(*V.P(plate.x1, plate.y1), *V.P(plate.x0, plate.y1), top + 20.0, "%s (free)" % n(pl[0], 0), fs=6.5)
    sh.dim_v(*V.P(plate.x0, plate.y0), *V.P(plate.x0, plate.y1), right + 14.0, "%s (free)" % n(pl[1], 0), fs=6.5,
             side="right")
    sh.T(x0 + 1.2, y0 + 1.2, "datum = glass centre", fs=6.0)
    sh.T(16.0, 279.0, "J2 FLUSH PLATE - working face seen from ABOVE   1 : 2", fs=8.5, weight="bold")
    sh.T(16.0, 274.5, "Glass lies face 1 (front) DOWN, so left / right are mirrored to the front view; the pattern is "
                      "symmetric. Tail side (bend-gap slot, tail holder TH) towards the operator (bottom).", fs=6.2)
    # legend
    yl = 99.0
    for col, ls, t in ((C_REF, (0, (4, 1.5)), "glass / lip outer / flange outlines (reference, frame lowered "
                                                "face down)"),
                       ("#b0308f", (0, (8, 1.5, 1.5, 1.5)), "FLAT ZONE = lip outer + 3: flatness %s, Ra %s" % (
                           n(flat), n(ra))),
                       (C_VAC, (0, (3, 1.5)), "OPTIONAL vacuum groove %s wide x %s deep, %s inside the glass edge, "
                                              "port dia %s" % (n(gw), n(gd_), n(gi), n(gp)))):
        sh.ax.plot([16, 26], [yl + 0.8, yl + 0.8], color=col, lw=lw(THIN), ls=ls)
        sh.T(28.0, yl, t, fs=6.0, color=col)
        yl -= 3.2
    # hole table
    rows = [["ID", "x (plate)", "y (plate)", "feature", "tol."]]
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        rows.append(["pin " + k, n(-f["u"]), n(f["v"]), "pin dia %s h6 x %s proud, pressed %s deep (hole N7)" % (
            n(pin_d), n(pin_h), n(pin_p)), "±%s" % n(tolp)])
    for k, (u, v) in S.items():
        rows.append([k, n(-u), n(v), "hole dia %s H7 x %s; stop pin ISO 2338 %s h8 x %s, %s proud, removable" % (
            n(st_d), n(pdt[2], 0), n(st_d, 0), n(pdt[3], 0), n(st_h)), "±%s" % n(tolp)])
    rows.append(["TH", n(-T["post_uv"][0] + 0.0), n(T["post_uv"][1]),
                 "hole dia %s H7 x %s for the removable tail-holder post (sheet 2)" % (
                     n(T["post_d"], 0), n(T["th"]["post_hole_depth"], 0)), "±0.5"])
    sh.T(16.0, 86.0, "HOLES (plate coordinates: x = -u, y = v, from the datum)", fs=7, weight="bold")
    y = sh.table(16.0, 85.0, [0, 16, 34, 52, 172], rows, fs=6.2, widths=185)
    # section B-B (schematic, 3:1): through a corner fastener, unrolled; plate at the bottom, depth d upwards
    k2 = 3.0
    xs0, yp = 248.0, 222.0
    Sx = lambda s, d: (xs0 + k2 * s, yp + k2 * d)
    gt = P.d("glass_t")
    Zg = P.level("Z_GLASS_FRONT")
    D = lambda nm: P.level(nm) - Zg
    d_sb, d_ff, d_fb, d_gb, d_land, d_sw, d_ctp, d_tube = (D("Z_SHEET_BACK"), D("Z_FLANGE_FRONT"),
                                                            D("Z_FLANGE_BACK"), D("Z_GLASS_BACK"), D("Z_LAND"),
                                                            D("Z_STEPWALL_BACK"), D("Z_CTP_FRONT"), D("Z_TUBE_TOP"))
    g2, lw_ = G.g2, G.lip_w
    s_lip1, s_ring = g2 + lw_, g2 + lw_ + G.seat_w
    land = G.glass.y1 - G.pocket.y1
    sF = G.fast_off
    rp = G.pad_d / 2.0
    sL, sR = -min(land, 9.0) - 1.5, sF + rp + 1.0          # GF-2.0: the 12.5 top land drawn cut at 9 (break)
    poly = lambda pts, **kw: sh.poly([Sx(*p) for p in pts], **kw)
    poly([(sL - 1, 0), (sR + 1, 0), (sR + 1, -3.0), (sL - 1, -3.0)], fc="#dfe3e8", ec="k", w=THICK, hatch="////")
    ps = -(G.glass.y1 - G.panel.y1)
    poly([(sL, 0), (0, 0), (0, gt), (sL, gt)], fc="#cfe8f3", ec="k", w=THIN)
    if ps > sL:
        poly([(sL, gt), (ps, gt), (ps, d_ctp), (sL, d_ctp)], fc="#f6e7b4", ec="0.4", w=XTHIN, geom=False)
        poly([(sL, d_ctp), (ps, d_ctp), (ps, d_sw + 1.0), (sL, d_sw + 1.0)], fc="#e3e3e3", ec="0.4", w=XTHIN,
             geom=False)
    poly([(-(G.bead_edge + G.bead_w), gt), (-G.bead_edge, gt), (-G.bead_edge, d_land),
          (-(G.bead_edge + G.bead_w), d_land)], fc="#3a3a3a", ec="k", w=XTHIN, geom=False)
    # frame: lip, step wall, land plate, flange with the corner pad and the tube, cut by the slot (section along
    # the slot axis: slot half-length, counterbore half-length, coring groove r_in..r_out from the tube top)
    cb, co = G.fastener_cuts()
    hl, cl = G.slot_l / 2.0, cb["cb_l"] / 2.0
    d_cb = d_sb + cb["cb_floor_F1-F4"]
    s_lp = max(-land, sL)
    fr = [(g2, 0), (s_lip1, 0), (s_lip1, d_sb), (sF - cl, d_sb), (sF - cl, d_cb), (sF - hl, d_cb),
          (sF - hl, d_tube), (sF - rp, d_tube), (sF - rp, d_fb), (s_ring, d_fb), (s_ring, d_sw), (s_lp, d_sw),
          (s_lp, d_land), (g2, d_land)]
    poly(fr, fc="#a7acb3", ec="k", w=THIN, hatch="\\\\\\\\")
    poly([(sF + cl, d_sb), (sF + rp, d_sb), (sF + rp, d_ff), (sR, d_ff), (sR, d_fb), (sF + rp, d_fb),
          (sF + rp, d_tube), (sF + hl, d_tube), (sF + hl, d_cb), (sF + cl, d_cb)], fc="#a7acb3", ec="k", w=THIN,
         hatch="\\\\\\\\")
    for sg in (-1, 1):
        a_, b_ = sF + sg * co["core_r_in"], sF + sg * co["core_r_out"]
        poly([(a_, d_tube - co["core_depth"]), (b_, d_tube - co["core_depth"]), (b_, d_tube + 0.05),
              (a_, d_tube + 0.05)], fc="white", ec="k", w=XTHIN)
    pr = pin_d / 2.0
    poly([(sF - pr, -2.6), (sF + pr, -2.6), (sF + pr, pin_h - 0.5), (sF + pr - 0.5, pin_h),
          (sF - pr + 0.5, pin_h), (sF - pr, pin_h - 0.5)], fc="#f6d4d0", ec=C_PIN, w=THIN)
    for s in (sL, sR):
        sh.L([Sx(s, -3.3)[0]] * 2, [Sx(s, -3.3)[1], Sx(s, d_sw + 1.0)[1]], w=XTHIN, c="0.3", geom=False,
             dashes=(1, 1.5))
    sh.T(*Sx(sL + 0.4, -1.5), "J2 PLATE: working face = flush plane", fs=6.0, allow_geom=True, bg="white",
         va="center")
    sh.T(*Sx(sL / 2.0, gt / 2.0), "glass, face 1 down", fs=6.0, ha="center", va="center", allow_geom=True)
    sh.T(*Sx(sF + 3.0, d_tube + 1.2), "pad, counterbore %s x %s, slot %s x %s, tube with coring groove" % (
        n(cb["cb_w"]), n(cb["cb_l"]), n(G.slot_w), n(G.slot_l)), fs=6.0, ha="center")
    # leaders to the right
    xr = Sx(sR + 1, 0)[0] + 4.0
    lead = [((sF + pr, pin_h * 0.55), 6.0, "pin dia %s, %s proud, in the radial slot" % (n(pin_d), n(pin_h))),
            ((sF + rp - 2.0, d_sb), 3.0, "corner pad %s above the plate (sheet back later)" % n(d_sb))]
    for (s, d), dy, txt in lead:
        sh.leader(*Sx(s, d), xr, Sx(0, dy)[1], txt, fs=6.0, head="arrow")
    yb_ = Sx(0, -3.0)[1]
    sh.leader(*Sx(0.9, 0.0), Sx(3.5, 0)[0], yb_ - 5.0, "lip top ON the plate", fs=6.0, head="arrow")
    sh.leader(*Sx(-0.4, 0.0), Sx(-1.5, 0)[0], yb_ - 5.0, "glass front ON the plate", fs=6.0, head="arrow",
              ha="right")
    sh.leader(*Sx(-2.9, (gt + d_land) / 2.0), Sx(sL, 0)[0] + 2.0, Sx(0, d_sw + 1.8)[1],
              "bead: gap set by the plate", fs=6.0, head="arrow")
    sh.dim_v(*Sx(sL, 0), *Sx(sL, d_sb), Sx(sL, 0)[0] - 3.0, n(d_sb), fs=6.0)
    sh.dim_v(*Sx(sL, d_sb), *Sx(sL, d_ff), Sx(sL, 0)[0] - 3.0, None, arrows="out")
    sh.T(Sx(sL, 0)[0] - 5.0, Sx(0, d_ff + 2.2)[1], "flange %s" % n(d_ff), fs=6.0, ha="right")
    sh.T(Sx(sL, 0)[0], Sx(0, d_sw + 5.5)[1], "SECTION B-B through a corner fastener (schematic)  3 : 1", fs=7.5,
         weight="bold")
    # notes
    J2_en = [
        "AUTHORITATIVE for J2: this sheet supersedes the jig text in concept sec. 6 - pins dia %s in the %s x %s radial "
        "slots (not dia 6 holes), a GRADED set of PTFE glass-centring shims %s (not a single 0.40 or 0.30), glass "
        "stops removable (a fixed stop stands where the lip lands); %s: tail handling on sheet 2." % (
            n(pin_d), n(G.slot_w), n(G.slot_l), sizes, P.revision),
        "Material: %s, %s thick (free, >= 15); outline free (flange + >= 25 per side), corners free." % (
            C("j2_plate_material"), n(pl[2], 0)),
        "WORKING FACE = FLUSH PLANE: the glass front AND the frame lip top rest on it. Flatness %s over the FLAT "
        "ZONE, Ra <= %s (fly-cut or surface ground); no dents or scratches in the zone." % (n(flat), n(ra)),
        "No film, tape or label on the zone (or one film of constant thickness under BOTH glass and lip): anything "
        "under the glass only becomes a flush error. Remove the glass's protective film before bonding.",
        "4 pins at F1-F4: dia %s h6 (turned steel), %s proud ±%s, %s x 45 chamfer, pressed %s deep; they only "
        "locate the frame roughly in its radial slots (%s per side across)." % (
            n(pin_d), n(pin_h), n(pdt[0]), n(pdt[1]), n(pin_p), n((G.slot_w - pin_d) / 2.0)),
        "3 stop holes S1-S3: dia %s H7 x %s for removable stop pins (%s proud). Place the glass against S1-S3, then "
        "PULL the pins before the frame comes down (the lip lands where the stops stand)." % (
            n(st_d), n(pdt[2], 0), n(st_h)),
        "Hole TH: dia %s H7 x %s for the removable tail-holder post, %s beyond the flange bottom edge (sheet 2)." % (
            n(T["post_d"], 0), n(T["th"]["post_hole_depth"], 0), n(T["th"]["post_offset"])),
        "Positions of pins and stop holes ±%s to the datum (glass centre); everything else free, ISO 2768-m." %
        n(tolp),
        "Use: glass + panel face down against S1-S3 (vacuum on if fitted), pull the stops, stand 8 PTFE shims "
        "%s x %s against the glass edges (2 per side), from the set %s (%d of each size): %s. Fold the tails and "
        "thread the frame per sheet 2, lower it on the pins until the lip lands on the plate, %s kg ring weight on "
        "the flange back, cure, check g2 against the acceptance limits on GF-D20." % (
            n(shim["w"], 0), n(shim["h"], 0), sizes, shim["per_size"], rule["en"].upper(), n(C("j2_weight"), 0)),
    ]
    J2_tr = [
        "Bu resim J2 için GEÇERLİ olandır; konsept §6 metninin yerine geçer: Ø6 delik değil, %s x %s radyal yuvalarda "
        "Ø%s pim; kademeli PTFE şim takımı %s; sökülebilir cam dayamaları; FPC kuyrukları: sayfa 2." % (
            n(G.slot_w), n(G.slot_l), n(pin_d), sizes),
        "Malzeme: %s, kalınlık %s (serbest, >= 15); dış ölçüler ve köşeler serbest." % (
            C("j2_plate_material").replace("cast tooling plate", "döküm kalıp plakası").replace(
                "stress-relieved", "gerilim giderilmiş").replace("or", "veya"), n(pl[2], 0)),
        "ÇALIŞMA YÜZEYİ: cam ön yüzü ve çerçeve dudağı aynı yüzeye oturur. DÜZ BÖLGEDE düzlemsellik %s mm, Ra <= %s "
        "(alın frezesi veya taşlama); çizik ve ezik olmayacak." % (n(flat), n(ra)),
        "4 pim (F1-F4): Ø%s h6, %s ±%s mm dışarıda, %s x 45° pah, %s mm preslenmiş." % (
            n(pin_d), n(pin_h), n(pdt[0]), n(pdt[1]), n(pin_p)),
        "3 dayama deliği S1-S3: Ø%s H7 x %s, sökülebilir dayama pimleri (%s mm dışarıda)." % (
            n(st_d), n(pdt[2], 0), n(st_h)),
        "TH deliği: Ø%s H7 x %s, sökülebilir kuyruk tutucu direği için (sayfa 2)." % (
            n(T["post_d"], 0), n(T["th"]["post_hole_depth"], 0)),
        "Pim ve delik konumları referansa göre ±%s mm; diğer ölçüler serbest, ISO 2768-m." % n(tolp),
        "Kullanım: cam kenarlarına 8 PTFE şim %s x %s (her kenarda 2), %s takımından (her ölçüden %d adet): %s." % (
            n(shim["w"], 0), n(shim["h"], 0), sizes, shim["per_size"], rule["tr"].replace("i", "İ").upper()),
    ]
    ye = sh.notes(212.0, 185.0, 98.0, J2_en, fs=6.0, head="NOTES", head_fs=7.2, gap=0.45)
    yt = sh.notes(313.0, 185.0, 96.0, [tr(t) for t in J2_tr], fs=6.0, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.45)
    fp_old = P.change("plan_rectangles.fastener_line")[0]          # previous revision's pin pattern (history)
    sh.title_block({
        "title": "JIG J2 - FLUSH PLATE (glass + panel -> frame), sheet 1/2",
        "subtitle": "aluminium plate for a local machinist  /  yapıştırma fikstürü J2 (alüminyum plaka)",
        "source": "product positions from %s; jig values: drafting_choices.json" % master_ref(P),
        "project": "files: GF_Jig_J2.pdf (2 sheets) / _p1.png / _p2.png + GF_Jig_J2.dxf (plate view, mm)",
        "change": "%s. Pins at F1-F4 %s x %s (%s %s x %s), stops S1-S3 moved with the glass; hole TH for the tail "
                  "holder (sheet 2)." % (rev_note(P), n2(abs(F1["u"] - F2["u"])), n2(abs(F1["v"] - F4["v"])),
                                         prev_rev(P), n2(fp_old[1] - fp_old[0]), n2(fp_old[3] - fp_old[2])),
        "dwg": "GF-D30", "rev": P.revision, "scale": "1:2, 3:1", "date": datetime.date.today().isoformat(),
        "drawn": "make_jigs.py",
    }, h=42.0)
    issues = sh.check_layout()
    return sh, issues, J2_en, J2_tr, [round(ye, 1), round(yt, 1), round(y, 1)]


def bottom_profile(P, G):
    """schematic frame profile at the bottom edge over the tail span (abs y, depth d above the flush plane), from
    the master levels and plan values (drafts and the R0.5 roots left out): lip, seat ring, flange plate, bottom
    wall, tail-pocket floor, step wall, land plate with the R nose and the 45 deg land break"""
    Zg = P.level("Z_GLASS_FRONT")
    D = lambda nm: P.level(nm) - Zg
    d_sb, d_ff, d_land, d_lpb = D("Z_SHEET_BACK"), D("Z_FLANGE_FRONT"), D("Z_LAND"), D("Z_LANDPLATE_BACK")
    d_floor, d_top = D("Z_FLOOR_LOW"), D("Z_TROUGH_TOP")
    y_face = P.rect("bend_gap_slot").y1
    y_li, y_lo, y_so = P.rect("lip_in").y1, P.rect("lip_out").y1, P.rect("seat_ring_out").y1
    y_tp = P.rect("tail_pocket").y1
    wall = P.val("carried_over_from_v2", "wall")
    y_out = P.d("flange_y1_bottom")
    R = P.d("bend_nose_R")
    b = P.d("land_break")
    nose = [(y_face + R - R * math.cos(a), d_lpb - R + R * math.sin(a))
            for a in [math.radians(90.0 * i / 16) for i in range(17)]]       # from (y_face, d_lpb - R) to the top
    pts = [(y_face + b, d_land), (y_li, d_land), (y_li, 0.0), (y_lo, 0.0), (y_lo, d_sb), (y_so, d_sb), (y_so, d_ff),
           (y_out, d_ff), (y_tp + wall, d_top), (y_tp, d_top), (y_tp, d_floor), (y_so, d_floor), (y_so, d_lpb)]
    pts += nose[::-1]
    pts += [(y_face, d_land + b)]
    shelf_y0 = P.val("carried_over_from_v2", "panel_y1") - P.val("carried_over_from_v2", "seat_w")
    shelf = [(shelf_y0, D("Z_SEAT")), (P.val("carried_over_from_v2", "panel_y1"), D("Z_SEAT")),
             (P.val("carried_over_from_v2", "panel_y1"), D("Z_SHELF_BACK")), (shelf_y0, D("Z_SHELF_BACK"))]
    return pts, shelf, dict(d_land=d_land, d_lpb=d_lpb, d_floor=d_floor, d_top=d_top, y_face=y_face, R=R, b=b,
                            d_sb=d_sb, d_ff=d_ff)


def j2_sheet2(P, C, G):
    """GF-D30 sheet 2: tail handling (GF-2.0) - section T-T through the bend gap in J2, plan detail of the tail
    holder TH and the guide card, the sequence"""
    sh = Sheet()
    sh.frame()
    T = j2_tail_geom(P, C, G)
    Zg = P.level("Z_GLASS_FRONT")
    D = lambda nm: P.level(nm) - Zg
    gt = P.d("glass_t")
    g = P.rect("glass")
    py1 = T["panel_y1"]
    # ---------------------------------------------------------------- section T-T 5:1 (abs y right, d up)
    k = 5.0
    ys0, ys1, dd0, dd1 = 114.0, 133.5, -3.0, 25.0
    X0, Y0 = 92.0, 128.0
    S = lambda y, d: (X0 + k * (y - ys0), Y0 + k * d)
    poly = lambda pts, **kw: sh.poly([S(*p) for p in pts], **kw)
    sh.T(16.0, 279.0, "SECTION T-T  tail handling in J2 at abs x %s (schematic, frame at its final position)  5 : 1" %
         n(G.fv.xc), fs=8.0, weight="bold")
    sh.T(16.0, 274.5, "Plate at the bottom, glass face 1 down; heights d above the plate; tails as the master "
                      "tail_route (both projected), held vertical by the guide card until the frame is down.", fs=6.0)
    poly([(ys0, 0), (ys1, 0), (ys1, dd0), (ys0, dd0)], fc="#dfe3e8", ec="k", w=THICK, hatch="////")
    poly([(ys0, 0), (g.y1, 0), (g.y1, gt), (ys0, gt)], fc="#cfe8f3", ec="k", w=THIN)
    sh.L([S(ys0, gt)[0], S(g.y1 - 0.5, gt)[0]], [S(0, gt)[1] + 0.35] * 2, w=0.6, c="k", geom=False)
    d_gb, d_ctp, d_pb = D("Z_GLASS_BACK"), D("Z_CTP_FRONT"), D("Z_PANEL_BACK")
    poly([(ys0, d_gb), (py1, d_gb), (py1, d_ctp), (ys0, d_ctp)], fc="#f6c342", ec="none", w=XTHIN, geom=False)
    poly([(ys0, d_ctp), (py1, d_ctp), (py1, d_pb), (ys0, d_pb)], fc="#f4c79a", ec="0.3", w=THIN)
    fm = P.rect("formex")
    poly([(ys0, D("Z_FORMEX_FRONT")), (fm.y1, D("Z_FORMEX_FRONT")), (fm.y1, D("Z_SEAT")), (ys0, D("Z_SEAT"))],
         fc="#c9c3e6", ec="0.4", w=XTHIN, geom=False)
    prof, shelf, pv = bottom_profile(P, G)
    poly(clip_poly(prof, ys0, ys1, dd0, dd1), fc="#a7acb3", ec="k", w=THIN, hatch="\\\\\\\\")   # cut at the window
    poly(shelf, fc="#a7acb3", ec="k", w=THIN, hatch="\\\\\\\\")
    bi, bo = g.y1 - G.bead_edge - G.bead_w, g.y1 - G.bead_edge
    poly([(bi, d_gb), (bo, d_gb), (bo, pv["d_land"]), (bi, pv["d_land"])], fc="#3a3a3a", ec="k", w=XTHIN)
    for s in (ys0, ys1):
        sh.L([S(s, dd0)[0]] * 2, [S(s, dd0)[1], S(s, dd1)[1]], w=XTHIN, c="0.3", geom=False, dashes=(1, 1.5))
    # tails (master centre lines up to the vertical leg, then straight up to the top of the window)
    yv = T["y_vert"]
    for nm, col in (("CTP", C_CTP), ("TFT", C_TFT)):
        pts, _ = G.tail_route(nm)
        out = []
        for (y, Z) in pts:
            out.append((y, Z - Zg))
            if abs(y - yv) < 1e-3 and abs(Z - (P.level("Z_TAIL_TFT_EXIT") + T["tails"][nm]["R_c"])) < 1e-3:
                break
        out.append((yv, dd1 - 0.4))
        q = [S(*p) for p in out]
        sh.L([p[0] for p in q], [p[1] for p in q], w=P.d("tail_t") * k, c=col, geom=False)
    # guide card + Kapton tabs
    cy0, cy1 = T["card"]["y"]
    poly([(cy0, T["card"]["bottom"]), (cy1, T["card"]["bottom"]), (cy1, dd1 - 0.4), (cy0, dd1 - 0.4)],
         fc="#4a90c2", ec="#1f5f8b", w=XTHIN, geom=False)
    tab_d = T["card"]["tab_min"]
    # break symbol at the top of the window (tails and card continue to the clip)
    xa, xb = S(cy0 - 1.2, 0)[0], S(yv + 1.2, 0)[0]
    yb = S(0, dd1 - 0.4)[1]
    sh.L([xa, xa + 1.5, xa + 3.0, xb - 1.5, xb], [yb, yb + 1.0, yb - 1.0, yb + 1.0, yb], w=XTHIN, geom=False)
    # labels (leaders to the left / right of the section)
    xl = S(ys0, 0)[0] - 3.0
    xr = S(ys1, 0)[0] + 3.0
    L_ = [((g.y1 - 6.0, gt / 2.0), -1.6, "glass %s, face 1 on the plate" % n(gt), "r"),
          ((py1 - 3.0, (d_ctp + d_pb) / 2.0), 6.0, "panel (CTP + LCM), bonded in J1", "l"),
          ((py1 - 1.0, (D("Z_FORMEX_FRONT") + D("Z_SEAT")) / 2.0), 9.6, "Formex", "l"),
          ((py1 - 1.0, (D("Z_SEAT") + D("Z_SHELF_BACK")) / 2.0), 12.4, "shelf end = slot front face", "l"),
          ((yv, 16.0), 16.0, "tails vertical on the slot line (CTP blue-violet, TFT orange)", "l"),
          ((0.5 * (cy0 + cy1), 20.5), 20.5, "guide card %s (PET), panel side of the tails" % n(T["card"]["t"]), "l"),
          ((bi + 3.4, d_gb + 0.15), 1.5, "bead %s x %s (fresh)" % (n(G.bead_w), n(pv["d_land"] - d_gb)), "r"),
          ((pv["y_face"] + 0.12, pv["d_land"] + 0.12), 5.4, "land break %s x 45 deg (no snag)" % n(pv["b"]), "r"),
          ((pv["y_face"] + pv["R"] * (1 - math.cos(math.radians(50))),
            pv["d_lpb"] - pv["R"] + pv["R"] * math.sin(math.radians(50))), 7.2,
           "bridge nose R%s (the tails are folded over it after the cure)" % n(pv["R"]), "r"),
          ((0.5 * (pv["y_face"] + bi), (d_gb + pv["d_land"]) / 2.0), 3.6,
           "bead inner edge %s behind the bridge face" % n(bi - pv["y_face"]), "r"),
          ((ys1 - 1.5, 12.5), 12.5, "tail pocket (open to the back); its floor and bottom wall: GF-D50 G-G", "r")]
    for (y, d), dy, t, side in L_:
        px, py = S(y, d)
        if side == "l":
            sh.leader(px, py, xl, S(0, dy)[1], t, fs=5.9, head="dot", ha="right")
        else:
            sh.leader(px, py, xr, S(0, dy)[1], t, fs=5.9, head="dot")
    # dimensions: g_bend (panel edge = shelf end -> bridge face), tail -> face, bead -> face
    yd = S(0, 23.0)[1]
    sh.dim_h(*S(py1, D("Z_SHELF_BACK")), *S(pv["y_face"], pv["d_land"] + 1.0), yd, None, c=C_DIM)
    sh.T(S(pv["y_face"], 0)[0] + 3.0, yd - 0.9, "%s = g_bend: panel edge -> bridge pocket face" % n(G.g_bend),
         fs=6.0, va="center", color=C_DIM)
    yd2 = S(0, 11.0)[1]
    sh.dim_h(*S(T["y_out"], 11.0), *S(pv["y_face"], 11.0), yd2, None, arrows="out", c=C_DIM, ext=False)
    sh.T(S(pv["y_face"], 0)[0] + 6.0, yd2 - 0.9, "%s tail -> face" % n(T["clear_face"], 2), fs=6.0, va="center",
         color=C_DIM)
    dm3 = (d_gb + pv["d_land"]) / 2.0
    yd3 = S(0, dm3)[1]
    sh.dim_h(*S(pv["y_face"], dm3), *S(bi, dm3), yd3, None, arrows="out", c=C_DIM, ext=False)

    # ---------------------------------------------------------------- plan detail 1:1 (plate view from above)
    k1 = 1.0
    PX0, PY0 = 338.0, 262.0                                           # paper position of the datum u = 0, v = 0 ...
    vref = G.fv.uv(0, py1)[1]                                         # ... shifted: v of the panel edge at PY0
    Pp = lambda u, v: (PX0 - k1 * u, PY0 + k1 * (v - vref))           # x = -u (mirrored), y = v
    sh.T(270.0, 279.0, "PLAN DETAIL - tail side of J2 seen from ABOVE (mirrored)  1 : 1", fs=8.0, weight="bold")
    fv = G.fv

    def rect_abs(x0, x1, y0, y1, **kw):
        (u0, v0), (u1, v1) = fv.uv(x0, y0), fv.uv(x1, y1)
        pts = [Pp(u0, v0), Pp(u1, v0), Pp(u1, v1), Pp(u0, v1)]
        return sh.poly(pts, **kw)

    def line_abs(pts, **kw):
        q = [Pp(*fv.uv(x, y)) for x, y in pts]
        sh.L([p[0] for p in q], [p[1] for p in q], **kw)
    sl = T["slot"]
    wx0, wx1 = sl.x0 - 3.0, sl.x1 + 3.0                               # detail window (abs x), lines clipped to it
    line_abs([(wx0, g.y1), (wx1, g.y1)], w=XTHIN, c=C_REF, geom=False, dashes=(4, 1.5))
    sh.T(Pp(*fv.uv(wx0, g.y1))[0] - 1.5, Pp(*fv.uv(wx0, g.y1))[1], "glass bottom edge", fs=5.6, color=C_REF,
         va="center", ha="right")
    line_abs([(wx0, py1), (wx1, py1)], w=THIN, c="0.3", geom=False)
    sh.T(Pp(*fv.uv(wx0, py1))[0] - 1.5, Pp(*fv.uv(wx0, py1))[1] + 0.4, "panel bottom edge", fs=5.6, color="0.3",
         va="bottom", ha="right")
    rect_abs(sl.x0, sl.x1, sl.y0, sl.y1, fc="none", ec=C_TAIL, w=XTHIN, geom=False, ls=(0, (3, 1.5)))
    fl = P.rect("flange")
    line_abs([(wx0, fl.y1), (wx1, fl.y1)], w=XTHIN, c=C_REF, geom=False, dashes=(6, 2))
    sh.T(Pp(*fv.uv(wx0, fl.y1))[0] - 1.5, Pp(*fv.uv(wx0, fl.y1))[1], "flange bottom edge (frame lowered)", fs=5.6,
         color=C_REF, va="center", ha="right")
    for nm, col in (("CTP", C_CTP), ("TFT", C_TFT)):
        x0_, x1_ = T["tails"][nm]["x_all"]
        line_abs([(x0_, yv), (x1_, yv)], w=0.9, c=col, geom=False)
        ex = T["tails"][nm]["exit"]
        line_abs([(ex[0], py1), (ex[0], yv)], w=XTHIN, c=col, geom=False)
        line_abs([(ex[1], py1), (ex[1], yv)], w=XTHIN, c=col, geom=False)
    rect_abs(T["card"]["x"][0], T["card"]["x"][1], cy0, cy1, fc="#4a90c2", ec="#1f5f8b", w=XTHIN, geom=False)
    pu, pv_ = T["post_uv"]
    xp, yp = Pp(pu, pv_)
    sh.circle(xp, yp, T["post_d"] / 2.0 * k1, ec=C_TAIL, w=THIN, fc="#f7e2c8")
    xc, yc = Pp(*fv.uv(0.5 * (T["card"]["x"][0] + T["card"]["x"][1]), 0.5 * (cy0 + cy1)))
    sh.L([xp, xc], [yp + T["post_d"] / 2.0, yc - 1.6], w=0.7, c=C_TAIL, geom=False, dashes=(8, 1.5, 1.5, 1.5))
    sh.poly([(xc - 3.0, yc - 1.6), (xc + 3.0, yc - 1.6), (xc + 3.0, yc + 1.6), (xc - 3.0, yc + 1.6)], fc="#f7e2c8",
            ec=C_TAIL, w=THIN, geom=False)
    # plan labels (outside the tail band)
    sh.T(xp + T["post_d"] / 2.0 + 2.0, yp + 1.4, "post TH dia %s (hole TH, sheet 1)," % n(T["post_d"], 0), fs=5.8,
         va="center", color=C_TAIL)
    sh.T(xp + T["post_d"] / 2.0 + 2.0, yp - 1.6, "%s beyond the flange edge" % n(T["th"]["post_offset"]), fs=5.8,
         va="center", color=C_TAIL)
    sh.T(xc - 4.5, yc - 9.0, "swing arm + clip (PTFE jaws) on the card top,", fs=5.8, color=C_TAIL, ha="right",
         bg="white")
    sh.T(xc - 4.5, yc - 11.8, "%s-%s above the plate; swings away to thread" % (
        n(T["th"]["clip_height"][0], 0), n(T["th"]["clip_height"][1], 0)), fs=5.8, color=C_TAIL, ha="right",
        bg="white")
    for nm, col in (("CTP", C_CTP), ("TFT", C_TFT)):
        x0_, x1_ = T["tails"][nm]["x_all"]
        xa_, ya_ = Pp(*fv.uv(0.5 * (x0_ + x1_), yv))
        sh.T(xa_, ya_ + 4.6, "%s tail x %s-%s" % (nm, n(x0_, 2), n(x1_, 2)), fs=5.8, color=col, ha="center",
             weight="bold")
    xa_, ya_ = Pp(*fv.uv(sl.x0, sl.y1))
    sh.T(xa_ - 1.5, ya_ - 0.4, "bend-gap slot %s x %s (frame)" % (n(sl.y1 - sl.y0), n(sl.x1 - sl.x0)), fs=5.6,
         color=C_TAIL, va="top", ha="right")
    xa_, ya_ = Pp(*fv.uv(T["tails"]["CTP"]["x_all"][0], sl.y1))
    sh.T(xa_, ya_ - 1.4, "guide card %s x %s on the panel side of the tails" % (n(T["card"]["t"]),
                                                                              n(T["card"]["w"], 0)),
         fs=5.8, color="#1f5f8b", va="top")
    # ---------------------------------------------------------------- sequence + parts
    tw = C("j2_tail_card")
    seq = [
        "BEFORE J2: panel bonded to the glass in J1 (GF-D31), tails flat and untouched since; bead dispensed on the "
        "frame land (GF-D20); the frame stays bead UP until step 5.",
        "Glass + panel face 1 down against S1-S3, pull the stops, set the 8 PTFE centring shims (sheet 1).",
        "FOLD: hold the GF-D21 gauge against the panel edge (end pads outside the tail span) and fold each tail up "
        "over its R%s edge: about %s free straight, inner radius >= %s, tail vertical; remove the gauge. Never crease, "
        "never pull." % (n(P.d("bend_nose_R")), n(P.d("tail_straight_l0")), n(P.d("tail_R_in_min"))),
        "CARD: stand the guide card (%s x %s, top %s above the plate) on the PANEL side of both tails, its bottom "
        "%s above the plate (above both bends); tack each tail to it with %s mm Kapton tabs, all >= %s above the "
        "plate (above the frame back, %s); clip the card top in TH: tails vertical on the slot line, %s out from the "
        "panel edge." % (n(tw["t"]), n(tw["w"], 0), n(tw["top"], 0), n(tw["bottom"], 0), n(tw["tab_w"], 0),
                         n(tw["tab_min"], 0), n(T["d_back"], 2), n(T["y_vert"] - py1, 2)),
        "THREAD: open the clip and swing the arm away, hold the card top by hand; hold the frame bead DOWN over the "
        "pins and lower it until the card top passes the %s x %s bend-gap slot from the front (the stiff card finds "
        "the slot); swing the arm back and clip the card top above the frame." % (n(sl.y1 - sl.y0),
                                                                              n(sl.x1 - sl.x0)),
        "LOWER the frame on the 4 pins: card and tails slide through the slot, the tails %s from the bridge face, "
        "the bead a further %s behind it - nothing touches the bead. Watch through the open tail pocket. Lip on the "
        "plate, ring weight on the flange." % (n(T["clear_face"], 2), n(bi - pv["y_face"])),
        "Open the clip, peel the Kapton tabs from behind, pull the card out upward, remove the post; check g2 "
        "(GF-D20); cure in the jig.",
        "AFTER THE CURE: fold each tail over the R%s bridge nose into its compartment (seen from the back: CTP "
        "left of the divider rib, TFT right), never tighter than the nose; PCB and connectors (GF-D20)." % (
            n(P.d("bend_nose_R"))),
        "STOP if a tail or the card touches the land edge or the bead: lift the frame straight up, clean the land, "
        "re-dispense (GF-D20), start again at step 4.",
    ]
    seq_tr = [
        "J2 ÖNCESİ: panel J1'de (GF-D31) cama yapıştırılmış, kuyruklar düz ve dokunulmamış; çerçeve yapıştırma "
        "yüzeyine kordon sürülmüş (GF-D20); çerçeve 5. adıma kadar kordon YUKARIDA durur.",
        "Cam + panel 1. yüzü aşağıda S1-S3'e dayalı; dayama pimlerini çekin, 8 PTFE şimi yerleştirin (sayfa 1).",
        "KATLAMA: GF-D21 mastarını panel kenarına dayayın (uç pabuçlar kuyruk bölgesinin dışında), her kuyruğu "
        "R%s kenarı üzerinden yukarı katlayın: yaklaşık %s düz kısım, iç radyus >= %s, kuyruk dik; mastarı alın. "
        "Kırmayın, çekmeyin." % (n(P.d("bend_nose_R")), n(P.d("tail_straight_l0")), n(P.d("tail_R_in_min"))),
        "KART: kılavuz kartı (%s x %s) iki kuyruğun PANEL tarafına, alt kenarı plakadan %s yukarıda olacak şekilde "
        "dikin; her kuyruğu plakadan en az %s yukarıda %s mm Kapton bantlarla karta tutturun; kart üstünü TH "
        "kıskacına takın: kuyruklar yuva hattında dik." % (n(tw["t"]), n(tw["w"], 0), n(tw["bottom"], 0),
                                                         n(tw["tab_min"], 0), n(tw["tab_w"], 0)),
        "GEÇİRME: kıskacı açın, kolu çevirin, kart üstünü elle tutun; çerçeveyi kordon AŞAĞIDA pimlerin üzerinde "
        "tutup kart üstü %s x %s büküm yuvasından önden geçene kadar indirin; kolu geri çevirip kart üstünü "
        "çerçevenin üstünde kıskaca takın." % (n(sl.y1 - sl.y0), n(sl.x1 - sl.x0)),
        "İNDİRME: çerçeveyi 4 pim üzerinde indirin; kart ve kuyruklar yuvadan kayar, kuyruklar köprü yüzünden %s, "
        "kordon bunun %s gerisinde - kordona hiçbir şey değmez. Dudak plakaya oturur, flanşa halka ağırlık." % (
            n(T["clear_face"], 2), n(bi - pv["y_face"])),
        "Kıskacı açın, Kapton bantları arkadan sökün, kartı yukarı çekin, direği alın; g2 kontrolü (GF-D20); "
        "fikstürde kürleme.",
        "KÜRDEN SONRA: her kuyruğu R%s köprü burnu üzerinden kendi bölmesine katlayın (arkadan bakışta CTP ayırıcı "
        "kaburganın solunda, TFT sağında); burundan daha dar bükmeyin. Sonra PCB ve konnektörler." % (
            n(P.d("bend_nose_R"))),
        "DUR: kuyruk veya kart yapıştırma kenarına ya da kordona değerse çerçeveyi dik kaldırın, temizleyin, "
        "kordonu yeniden sürün, 4. adımdan başlayın.",
    ]
    ye = sh.notes(16.0, 106.0, 205.0, seq, fs=5.9, head="SEQUENCE - J2 with the tails (%s)" % P.revision,
                  head_fs=7.2, gap=0.4)
    yt = sh.notes(272.0, 205.0, 134.0, [tr(x) for x in seq_tr], fs=5.7, head="SIRA (Türkçe)", head_fs=7.2, gap=0.35)
    rows = [["item", "description (free unless stated)", "qty"],
            ["TH post", "steel rod dia %s g6, about %s long, in hole TH (sheet 1); swing arm with a spring clip, "
                        "PTFE-faced jaws, clip height %s-%s above the plate" % (
                            n(T["post_d"], 0), n(T["th"]["post_h"], 0), n(T["th"]["clip_height"][0], 0),
                            n(T["th"]["clip_height"][1], 0)), "1"],
            ["guide card", "PET (or PEEK) %s x %s x %s high (top %s above the plate), edges deburred" % (
                n(tw["t"]), n(tw["w"], 0), n(tw["top"] - tw["bottom"], 0), n(tw["top"], 0)), "2"],
            ["Kapton tabs", "polyimide tape %s wide, low-residue silicone adhesive, never on the ZIF contacts" % (
                n(tw["tab_w"], 0)), "4 / module"],
            ["fold gauge", "GF-D21 tail fold gauge (used as the fold former in step 3)", "1"]]
    sh.T(272.0, yt - 3.0, "TAIL-HANDLING PARTS (drafting_choices.json)", fs=7.0, weight="bold")
    yp_ = sh.table_wrapped(272.0, yt - 4.5, [22, 98, 14], rows, fs=5.7)
    sh.title_block({
        "title": "JIG J2 - TAIL HANDLING, sheet 2/2",
        "subtitle": "fold, hold and thread the FPC tails through the bend-gap slot  /  FPC kuyruklarının yuvadan "
                    "geçirilmesi",
        "source": "product values from %s (tail_route, g_bend, bend_nose_R, land_break, levels); jig values: "
                  "drafting_choices.json" % master_ref(P),
        "project": "files: GF_Jig_J2.pdf (2 sheets) / _p1.png / _p2.png + GF_Jig_J2.dxf",
        "change": "%s. Section T-T at g_bend %s: tails %s from the bridge face, bead %s behind it; tail holder TH, "
                  "guide card and threading sequence as before (concept_gf2.md 5.3 / risk 3)." % (
                      rev_note(P), n2(G.g_bend), n(T["clear_face"], 2), n(bi - pv["y_face"])),
        "dwg": "GF-D30", "rev": P.revision, "scale": "5:1, 1:1", "date": datetime.date.today().isoformat(),
        "drawn": "make_jigs.py",
    }, h=42.0)
    issues = sh.check_layout()
    return sh, issues, seq, seq_tr, [round(ye, 1), round(yt, 1), round(yp_, 1)], T


# ================================================================================================================ J1
def j1_geom(P, C, G):
    base = C("j1_base")
    top = C("j1_top")
    gd, gu, gv = C("j1_guide")
    cm = C("j1_carrier_margin")
    pc = G.panel
    carrier = pc.offset(cm, "carrier")
    carrier.R = 3.0
    nest = pc.offset(C("j1_nest_clr"), "nest")
    om = C("j1_opening_margin")
    opening = G.window.offset(om, "opening")
    opening.R = 2.0
    tp = G.tail_pocket
    fpc = Rect(tp.x0, tp.x1, carrier.y0 - 2.0, pc.y0 + 1.0, 0.0, "fpc_slot")
    gi = C("j1_groove_inset")
    groove = G.glass.offset(-gi, "groove")
    groove.R = max(groove.R, 2.0)
    guides = [(su * gu, sv * gv) for su in (1, -1) for sv in (1, -1)]
    return dict(base=Rect(-base[0] / 2, base[0] / 2, -base[1] / 2, base[1] / 2, 5.0, "base"),
                top=Rect(-top[0] / 2, top[0] / 2, -top[1] / 2, top[1] / 2, 5.0, "top_plate"), guide_d=gd,
                guides=guides, carrier=carrier, nest=nest, opening=opening, fpc=fpc, groove=groove)


def j1_dxf(path, P, C, G, J):
    doc, msp = new_dxf([("BASE", 7, "CONTINUOUS"), ("GUIDES", 1, "CONTINUOUS"), ("TOP_PLATE", 4, "CONTINUOUS"),
                        ("TOP_STOPS", 3, "CONTINUOUS"), ("TOP_GROOVE", 200, "DASHED"), ("CARRIER", 6, "CONTINUOUS"),
                        ("REF", 5, "DASHED"), ("TEXT", 7, "CONTINUOUS")])
    dxf_rect(msp, J["base"], "BASE")
    for (u, v) in J["guides"]:
        msp.add_circle((u, v), J["guide_d"] / 2.0, dxfattribs={"layer": "GUIDES"})
    dxf_rect(msp, J["top"], "TOP_PLATE")
    dxf_rect(msp, J["opening"], "TOP_PLATE")
    for k, (u, v) in stops_uv(G, C).items():
        msp.add_circle((u, v), C("j2_stop_d") / 2.0, dxfattribs={"layer": "TOP_STOPS"})
        dxf_text(msp, k, u + 3, v + 3, 2.5)
    dxf_rect(msp, J["groove"], "TOP_GROOVE")
    for r in (J["carrier"], J["nest"], J["fpc"]):
        dxf_rect(msp, r, "CARRIER")
    for r in (G.glass, G.window, G.panel, G.aa):
        dxf_rect(msp, r, "REF")
    dxf_text(msp, "GF JIG J1 OPTICAL-BONDING FIXTURE - plan seen from ABOVE = FRONT VIEW (glass face 1 up). Origin = "
             "glass centre (top-plate datum). mm.", J["base"].x0, J["base"].y0 - 8, 3.0)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(path)


def j1_sheet(path_base, P, C, G, J):
    sh = Sheet()
    sh.frame()
    V = View(sh, 100.0, 178.0, 0.5)
    b, t, car, nest, op = J["base"], J["top"], J["carrier"], J["nest"], J["opening"]
    V.rrect(b, ec="k", w=THICK)
    V.rrect(car, ec="#b0308f", w=THIN, fc="#f7e9f4", geom=False)
    V.rrect(nest, ec="#b0308f", w=XTHIN, geom=False)
    V.rrect(J["fpc"], ec="#b0308f", w=XTHIN, fc="white", geom=False)
    V.rrect(t, ec="#1f77b4", w=THIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    V.rrect(op, ec="#1f77b4", w=THIN, geom=False)
    V.rrect(J["groove"], ec=C_VAC, w=XTHIN, ls=(0, (3, 1.5)), geom=False)
    V.rrect(G.glass, ec=C_REF, w=XTHIN, ls=(0, (4, 1.5)), geom=False)
    V.rrect(G.window, ec=C_REF, w=XTHIN, ls=(0, (1.5, 1.2)), geom=False)
    for (u, v) in J["guides"]:
        V.circle(u, v, J["guide_d"] / 2.0, ec="k", w=THIN, fc="#dddddd")
    for k, (u, v) in stops_uv(G, C).items():
        V.circle(u, v, C("j2_stop_d") / 2.0 + 0.6, ec=C_STOP, w=THIN, fc="#d4efdc")
        x, y = V.P(u, v)
        sh.T(x - 2.8 if k == "S3" else x + 2.8, y + (1.8 if k == "S3" else 0.0), k, fs=6.3, color=C_STOP,
             weight="bold", ha="right" if k == "S3" else "left", va="center")
    # micrometers: X on the front-view left side of the carrier, Y1 / Y2 on the top side
    mic = [("X", (car.x0, car.c[1]), (-1, 0)), ("Y1", (-40.0, car.y1), (0, 1)), ("Y2", (40.0, car.y1), (0, 1))]
    for name, (u, v), (du, dv) in mic:
        x, y = V.P(u, v)
        L = 12.0
        sh.poly([(x + du * 0.5 - dv * 1.2, y + dv * 0.5 + du * 1.2), (x + du * L - dv * 1.2, y + dv * L + du * 1.2),
                 (x + du * L + dv * 1.2, y + dv * L - du * 1.2), (x + du * 0.5 + dv * 1.2, y + dv * 0.5 - du * 1.2)],
                fc="#ffd27f", ec="k", w=XTHIN, geom=False)
        if dv:          # Y1 / Y2: label beyond the micrometer end
            sh.T(x, y + dv * (L + 1.5), "micrometer " + name, fs=6.0, ha="center", va="bottom")
        else:           # X: label below the bar end, clear of the centre line (GF-2.0: carrier centred on it)
            sh.T(x + du * L, V.P(0, 0)[1] - 3.0, "micrometer " + name, fs=6.0, ha="center", va="top",
                 bg="white")
    for (u, v), (du, dv) in (((car.x1, car.c[1]), (1, 0)), ((-40.0, car.y0), (0, -1)), ((40.0, car.y0), (0, -1))):
        x, y = V.P(u, v)
        sh.L([x, x + du * 6.0], [y, y + dv * 6.0], w=THIN, c="0.3", geom=False)
        sh.circle(x + du * 6.0, y + dv * 6.0, 1.0, ec="0.3", w=XTHIN, geom=False)
    x, y = V.P(car.x1, car.c[1])
    sh.T(x + 1.0, V.P(0, 0)[1] + 1.8, "spring", fs=5.8, va="bottom", color="0.3")   # clear of the centre line
    # microscopes over two diagonal window corners
    for (u, v) in ((G.window.x0, G.window.y1), (G.window.x1, G.window.y0)):
        x, y = V.P(u, v)
        sh.circle(x, y, 3.0, ec="#d35400", w=THIN, geom=False)
        sh.L([x - 4, x + 4], [y, y], w=XTHIN, c="#d35400", geom=False)
        sh.L([x, x], [y - 4, y + 4], w=XTHIN, c="#d35400", geom=False)
    xm, ym = V.P(G.window.x0, G.window.y1)
    sh.T(xm + 4.0, ym - 5.5, "USB microscope 1", fs=5.8, color="#d35400")
    xm, ym = V.P(G.window.x1, G.window.y0)
    sh.T(xm - 4.0, ym + 3.5, "USB microscope 2", fs=5.8, color="#d35400", ha="right")
    V.centreline((b.x0 - 3, 0), (b.x1 + 3, 0))
    V.centreline((0, b.y0 - 3), (0, b.y1 + 3))
    # dims: guide pattern, opening, stops, nest offset
    topy = V.P(0, b.y1)[1]
    gu, gv = J["guides"][0]
    sh.dim_h(*V.P(-gu, gv), *V.P(gu, gv), topy + 6.0, "guides %s" % n(2 * gu, 0), fs=6.5)
    lft = V.P(b.x0, 0)[0]
    sh.dim_v(*V.P(-gu, -gv), *V.P(-gu, gv), lft - 6.0, "guides %s" % n(2 * gv, 0), fs=6.5)
    sh.dim_h(*V.P(op.x0, op.y1), *V.P(op.x1, op.y1), topy + 13.0, "opening %s x %s (window + %s)" % (
        n(op.w), n(op.h), n(C("j1_opening_margin"))), fs=6.5)
    sh.T(16.0, 279.0, "J1 OPTICAL-BONDING FIXTURE - plan seen from ABOVE (= front view, glass face 1 up)   1 : 2",
         fs=8.5, weight="bold")
    sh.T(16.0, 274.5, "Base with the XY-theta panel carrier (magenta); top plate (blue, dash-dot) holds the glass by "
                      "vacuum on face 1, against stops S1-S3; it slides down 4 guide pins onto height stops.", fs=6.0)
    # extra plan dims: stops and opening position (same stop pattern as J2)
    S_ = stops_uv(G, C)
    tolp = C("j2_pos_tol")
    sh.dim_h(*V.P(*S_["S2"]), *V.P(*S_["S1"]), topy + 20.0, "S1-S2 %s ±%s" % (n(abs(S_["S1"][0] - S_["S2"][0])), n(C("j1_stop_tol"))),
             fs=6.5)
    boty = V.P(0, b.y0)[1]
    sh.dim_h(*V.P(*S_["S3"]), *V.P(0, 0), boty - 6.0, "%s ±%s (S3 to datum)" % (n(abs(S_["S3"][0])), n(C("j1_stop_tol"))),
             fs=6.5)
    pcx, pcy = G.panel.c
    sh.T(16.0, 101.0, "Carrier nominal position: panel outline centre at u %s, v %s from the datum (= AA under the "
                      "window); travel ±%s, all carrier dimensions free." % (n(pcx), n(pcy), n(C("j1_travel")[0])),
         fs=6.0)
    # section (schematic, 2:1, not every part to scale): top edge
    k2 = 2.0
    xs0, yb0 = 308.0, 216.0          # GF-2.0: guide pins 28.8 from the glass edge -> section shifted left
    Sx = lambda s, h: (xs0 + k2 * s, yb0 + k2 * h)
    poly = lambda pts, **kw: sh.poly([Sx(*p) for p in pts], **kw)
    t_opt = P.d("t_opt")
    gt = P.d("glass_t")
    panel_t = [c["value"] for c in P.raw["carried_over_from_v2"] if c["name"] == "panel_t"][0]
    P._use("carried_over_from_v2.panel_t", panel_t)
    hb, h_car, h_pk, h_top = 5.0, 6.0, 3.0, 8.0          # drawn thicknesses (free)
    s_pe = -(G.glass.y1 - G.panel.y1)
    s_op = -(G.glass.y1 - op.y1)                          # opening edge (top side) from the glass edge
    s_win = -(G.glass.y1 - G.window.y1)
    gvs = gv - G.glass.y1                                 # guide pin axis from the glass edge (top side)
    gd2 = J["guide_d"] / 2.0
    s0, s1 = s_pe - 12.0, gvs + gd2 + 3.0
    poly([(s0, -hb), (s1, -hb), (s1, 0), (s0, 0)], fc="#dfe3e8", ec="k", w=THICK, hatch="////")
    poly([(s0, 0.6), (s_pe + 15.0, 0.6), (s_pe + 15.0, 0.6 + h_car), (s_pe + 0.3, 0.6 + h_car),
          (s_pe + 0.3, 0.6 + h_car - h_pk), (s0, 0.6 + h_car - h_pk)], fc="#f7e9f4", ec="#b0308f", w=THIN)
    yb = 0.6 + h_car - h_pk
    poly([(s0, yb), (s_pe, yb), (s_pe, yb + panel_t), (s0, yb + panel_t)], fc="#e3e3e3", ec="0.3", w=THIN)
    yc = yb + panel_t
    poly([(s0, yc), (s_pe, yc), (s_pe, yc + t_opt), (s0, yc + t_opt)], fc="#f6c342", ec="none", w=XTHIN)
    yg = yc + t_opt
    poly([(s0, yg), (0, yg), (0, yg + gt), (s0, yg + gt)], fc="#cfe8f3", ec="k", w=THIN)
    sh.L([Sx(s0, 0)[0], Sx(s_win, 0)[0]], [Sx(0, yg)[1] + 0.3] * 2, w=0.6, c="k", geom=False)
    yt = yg + gt
    gi = C("j1_groove_inset")
    poly([(s_op, yt), (-gi - 1.0, yt), (-gi - 1.0, yt + 1.5), (-gi + 1.0, yt + 1.5), (-gi + 1.0, yt),
          (gvs - gd2 - 0.5, yt), (gvs - gd2 - 0.5, yt + h_top), (s_op, yt + h_top)], fc="#d6e6f5", ec="#1f77b4",
         w=THIN, hatch="\\\\")
    poly([(gvs + gd2 + 0.5, yt), (s1, yt), (s1, yt + h_top), (gvs + gd2 + 0.5, yt + h_top)], fc="#d6e6f5",
         ec="#1f77b4", w=THIN, hatch="\\\\")
    st_x = C("j2_stop_d") / 2.0
    poly([(st_x - 2.0, yt), (st_x + 2.0, yt), (st_x + 2.0, yt - 2.0), (st_x - 2.0, yt - 2.0)], fc="#d4efdc",
         ec=C_STOP, w=XTHIN)
    poly([(gvs - gd2, -hb + 1.0), (gvs + gd2, -hb + 1.0), (gvs + gd2, yt + h_top + 3.0),
          (gvs - gd2, yt + h_top + 3.0)], fc="#cccccc", ec="k", w=THIN)
    # microscope view
    xm = Sx(s_win, 0)[0]
    sh.L([xm, xm], [Sx(0, yt + h_top + 7.0)[1], Sx(0, yg + gt + 0.4)[1]], w=THIN, c="#d35400", geom=False)
    sh.arrow(xm, Sx(0, yg + gt + 0.4)[1], -math.pi / 2, "#d35400")
    sh.T(xm - 1.0, Sx(0, yt + h_top + 7.5)[1], "microscope looks at the window edge through the opening", fs=5.8,
         color="#d35400", ha="right", va="bottom")
    sh.T(*Sx(s_op + 0.6, yt + h_top / 2.0 + 1.0), "TOP PLATE", fs=6.0, allow_geom=True, bg="white", va="center")
    sh.T(*Sx(s0 + 0.5, -hb / 2.0), "BASE", fs=6.0, allow_geom=True, bg="white", va="center")
    xl = Sx(s0, 0)[0] - 3.0
    labs = [((s_pe + 8.0, 0.6 + h_car * 0.5), 2.5, "carrier on PTFE pads (XY-theta)"),
            ((s_pe - 4.0, yb + panel_t / 2), 6.5, "panel %s, CTP up" % n(panel_t)),
            ((s_pe - 2.0, yc + t_opt / 2), 10.0, "LOCA %s ±%s (hard stops)" % (
                n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1))),
            ((s_win - 3.0, yg + gt / 2), 13.5, "glass, print (face 2) down"),
            ((-gi, yt + 0.8), 17.5, "vacuum groove (face 1)")]
    for (s, h), hy, txt in labs:
        sh.leader(*Sx(s, h), xl, Sx(0, hy)[1], txt, fs=5.8, head="dot", ha="right")
    xr = Sx(s1, 0)[0] + 3.0
    sh.leader(*Sx(st_x + 2.0, yt - 1.0), xr, Sx(0, yt - 3.0)[1], "stop S1", fs=5.8, head="dot")
    sh.leader(*Sx(gvs + gd2, yt + h_top + 1.0), xr, Sx(0, yt + h_top + 2.0)[1], "guide %s" % n(J["guide_d"], 0),
              fs=5.8, head="dot")
    sh.T(214.0, 279.0, "SECTION C-C, top edge (schematic)  2 : 1", fs=7.5, weight="bold")
    # alignment target: magnified window corner
    kz = 20.0
    ax0, ay0 = 236.0, 178.0
    pxh = G.aa.w / C("display_px")[0]
    pxv = G.aa.h / C("display_px")[1]
    pin = P.d("print_inset")
    al_txt = P.text("print", "alignment")
    al_note = P.item("print", "alignment")["note"]
    m = re.search(r"window edge (\d+)-(\d+) px inside", al_note)
    p_lo, p_hi = int(m.group(1)), int(m.group(2))
    gui_px = int(re.search(r"outer (\d+) px black", al_note).group(1))
    Z = lambda a, c: (ax0 + kz * a, ay0 + kz * c)
    n_px = 5
    for i in range(n_px):
        for j in range(n_px):
            lit = (i == 0 or j == 0)
            x, y = Z(i * pxh, -j * pxv)
            sh.poly([(x, y), (x + kz * pxh * 0.9, y), (x + kz * pxh * 0.9, y - kz * pxv * 0.9),
                     (x, y - kz * pxv * 0.9)], fc="#ffffff" if lit else "#8a9599", ec="0.4", w=0.1, geom=False)
    sh.poly([Z(-0.45, 0.45), Z(n_px * pxh, 0.45), Z(n_px * pxh, 0), Z(0, 0), Z(0, -n_px * pxv),
             Z(-0.45, -n_px * pxv)], fc="#1b1b1b", ec="none", geom=False)
    sh.L([Z(pin, 0)[0]] * 2, [Z(0, -pin)[1], Z(0, -n_px * pxv)[1]], w=THICK, c="#c0392b", geom=False)
    sh.L([Z(pin, 0)[0], Z(n_px * pxh, 0)[0]], [Z(0, -pin)[1]] * 2, w=THICK, c="#c0392b", geom=False)
    for pp in (p_lo, p_hi):
        sh.L([Z(pp * pxh, 0)[0]] * 2, [Z(0, 0)[1], Z(0, -n_px * pxv)[1]], w=XTHIN, c="#2e8b57", geom=False,
             dashes=(2, 1.5))
        sh.L([Z(0, 0)[0], Z(n_px * pxh, 0)[0]], [Z(0, -pp * pxv)[1]] * 2, w=XTHIN, c="#2e8b57", geom=False,
             dashes=(2, 1.5))
    sh.T(ax0 - 12.0, ay0 + 14.0, "ALIGNMENT TARGET: top-left window corner, front view  %s : 1" % n(kz, 0), fs=7.0,
         weight="bold")
    tx = Z(n_px * pxh, 0)[0] + 4.0
    for i, (t, col) in enumerate((("white = lit 1-px border on the outermost AA pixels", "k"),
                                  ("grey = image; black = LCD matrix outside the AA", "k"),
                                  ("red = print window edge (face 2): print_inset %s = %s px h, %s px v" % (
                                      n(pin), n(pin / pxh, 2), n(pin / pxv, 2)), "#c0392b"),
                                  ("green dashed = %d px and %d px inside the border: accept band" % (p_lo, p_hi),
                                   "#2e8b57"),
                                  ("1 px = %s mm h x %s mm v (AA / %d x %d px)" % (
                                      n(pxh, 4), n(pxv, 4), C("display_px")[0], C("display_px")[1]), "k"))):
        sh.T(tx, ay0 + 4.0 - i * 3.4, t, fs=5.9, color=col)
    # notes
    rngs = C("j1_travel")
    J1_en = [
        "AUTHORITATIVE for J1: this sheet supersedes concept sec. 6 (glass on the base, panel lowered): the panel "
        "sits on the XY-theta carrier and the glass hangs from the top plate so the microscopes see the window edge "
        "from the user side (R1 sec. 3.3).",
        "ALIGN the print window edge (glass face 2) to the lit 1-px border of the active area (AA): window edge %d-%d "
        "px inside the border on all four sides, left = right and top = bottom within 1 px (1 px = %s x %s mm). "
        "Nominal = print_inset %s = %s px h / %s px v (master: %s)." % (
            p_lo, p_hi, n(pxh, 4), n(pxv, 4), n(pin), n(pin / pxh, 2), n(pin / pxv, 2), al_txt),
        "Glass and panel are NOT aligned by their outlines: the glass sits on stops S1-S3 (±%s), the panel floats "
        "in the carrier (nest = panel + %s per side) and is moved by the micrometers: XY ±%s, theta ±%s deg." % (
            n(C("j1_stop_tol")), n(C("j1_nest_clr")), n(rngs[0]), n(rngs[1])),
        "Gap glass face 2 -> CTP front: LOCA %s ±%s, set by 4 height stops between top plate and base (fine-thread "
        "stop screws with lock nuts or ground shims). Per panel: measure the CTP height in the nest, set the stops "
        "to CTP + %s + measured glass thickness." % (n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1),
                                                    n(t_opt, 2)),
        "Top plate glass face parallel to the base within %s over the panel area; guides %s g6 pins / H7 bushings, "
        "no play that tilts the plate." % (n(C("j1_parallel")), n(J["guide_d"], 0)),
        "Top plate: opening = print window + %s per side, %s (window edge visible everywhere, UV tack through it); "
        "vacuum groove loop %s inside the glass edge (black border only)." % (
            n(C("j1_opening_margin")),
            "centred on the datum (%s: window centre = glass centre)" % P.revision if abs(op.c[1]) < 1e-6 and
            abs(op.c[0]) < 1e-6 else "centred %s above the datum" % n(op.c[1]), n(C("j1_groove_inset"))),
        "Micrometers: %s. Carrier: panel pocket POM-lined, FPC slot at the tail exit, test connector for the lit "
        "border pattern (GUI: outer %d px black in normal use). The tails stay FLAT in J1; they are folded only in "
        "J2 (GF-D30 sheet 2)." % (C("j1_micrometer"), gui_px),
        "LOCA volume = panel outline %s x %s x %s = %s mL (R1: dispense ~5 %% more, dog-bone pattern)." % (
            n(G.panel.w), n(G.panel.h, 0), n(t_opt, 2), n(G.panel.w * G.panel.h * t_opt / 1000.0, 2)),
        "Free (machinist's choice): plate sizes, thicknesses, carrier size, stop-screw type, handles, feet; "
        "general tolerance ISO 2768-m. Al plate, anodised or bare; POM where glass or panel touch.",
    ]
    J1_tr = [
        "Bu resim J1 için GEÇERLİ olandır; konsept §6 metninin yerine geçer (panel XY-açı taşıyıcıda, cam üst plakada).",
        "Hizalama: cam 2. yüzündeki baskı penceresinin kenarı, ekranın aktif alanının yanan 1 piksellik çerçevesinin "
        "%d-%d piksel içinde olacak; dört kenarda eşit (±1 piksel)." % (p_lo, p_hi),
        "Cam S1-S3 dayamalarına (±%s) oturur; panel taşıyıcıda serbesttir ve mikrometrelerle hareket ettirilir: XY "
        "±%s mm, açı ±%s°." % (n(C("j1_stop_tol")), n(rngs[0]), n(rngs[1])),
        "Cam 2. yüzü ile CTP ön yüzü arası %s ±%s mm (4 yükseklik dayaması: ince dişli ayar vidası + kontra somun "
        "veya taşlanmış şim)." % (n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1)),
        "Üst plaka cam yüzeyi tabana paralel: %s mm; kılavuz pimleri Ø%s g6, burçlar H7." % (
            n(C("j1_parallel")), n(J["guide_d"], 0)),
        "Ölçüsü verilmeyen her şey serbest; genel tolerans ISO 2768-m. Cam ve panele değen yüzeyler POM.",
        "FPC kuyrukları J1'de DÜZ kalır; yalnız J2'de katlanır (GF-D30 sayfa 2).",
    ]
    ye = sh.notes(212.0, 152.0, 98.0, J1_en, fs=5.8, head="NOTES", head_fs=7.2, gap=0.4)
    yt_ = sh.notes(313.0, 152.0, 96.0, [tr(x) for x in J1_tr], fs=5.8, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.4)
    # bottom-left: what is aligned to what (table)
    rows = [["what", "aligned to", "how", "tolerance"],
            ["print window edge (glass face 2)", "lit 1-px AA border", "micrometers X / Y1 / Y2, 2 microscopes",
             "%d-%d px inside, sides equal ±1 px" % (p_lo, p_hi)],
            ["glass outline", "top plate stops S1-S3", "by hand, vacuum on", "±%s (only coarse)" % n(C("j1_stop_tol"))],
            ["glass face 2 height", "CTP front", "4 height stops", "%s ±%s" % (
                n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1))],
            ["top plate", "base", "4 guide pins", "parallel %s" % n(C("j1_parallel"))]]
    sh.T(16.0, 92.0, "WHAT IS ALIGNED TO WHAT", fs=7.2, weight="bold")
    ytab = sh.table_wrapped(16.0, 90.0, [48, 36, 54, 52], rows, fs=6.0)
    sh.title_block({
        "title": "JIG J1 - OPTICAL-BONDING ALIGNMENT FIXTURE",
        "subtitle": "panel -> glass, LOCA, active alignment  /  optik yapıştırma hizalama fikstürü J1",
        "source": "product positions from %s; jig values: drafting_choices.json" % master_ref(P),
        "project": "files: GF_Jig_J1.dxf (plan = front view, mm) + this sheet",
        "change": "%s. Glass %s x %s: stops S1-S3 moved with the outline (S1-S2 %s, S3 %s), opening on the datum; "
                  "plates and guide pins unchanged." % (rev_note(P), n2(G.glass.w), n2(G.glass.h),
                                          n(abs(S_["S1"][0] - S_["S2"][0])), n(abs(S_["S3"][0]))),
        "dwg": "GF-D31", "rev": P.revision, "scale": "1:2, 2:1, %s:1" % n(kz, 0),
        "date": datetime.date.today().isoformat(), "drawn": "make_jigs.py",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(path_base + ".pdf", path_base + ".png", dpi=200)
    return issues, J1_en, J1_tr, [round(ye, 1), round(yt_, 1), round(ytab, 1)]


def run(out_dir=OUT_DIR):
    res = {}
    P, C = Params(), Choices()
    G = Geom(P)
    b2 = os.path.join(out_dir, "GF_Jig_J2")
    j2_dxf(b2 + ".dxf", P, C, G)
    sh1, iss, en, trn, yl = j2_sheet(P, C, G)
    sh2, iss2, seq, seq_tr, yl2, T = j2_sheet2(P, C, G)
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    with PdfPages(b2 + ".pdf") as pdf:
        pdf.savefig(sh1.fig, dpi=300)
        pdf.savefig(sh2.fig, dpi=300)
    sh1.fig.savefig(b2 + "_p1.png", dpi=200)
    sh2.fig.savefig(b2 + "_p2.png", dpi=200)
    plt.close(sh1.fig)
    plt.close(sh2.fig)
    res["J2"] = {"files": [b2 + ".dxf", b2 + ".pdf", b2 + "_p1.png", b2 + "_p2.png"], "layout_issues": iss + iss2,
                 "notes_en": en, "notes_tr": trn, "sequence_en": seq, "sequence_tr": seq_tr,
                 "lowest_y": yl + yl2,
                 "tail_handling": {"y_vertical_leg_abs": T["y_vert"], "card_y_abs": list(T["card"]["y"]),
                                   "card_x_abs": list(T["card"]["x"]), "post_uv": list(T["post_uv"]),
                                   "tail_to_bridge_face": round(T["clear_face"], 4),
                                   "card_to_shelf_end": round(T["clear_shelf"], 4),
                                   "tail_end_heights_above_plate": {k: round(v, 2) for k, v in T["tips"].items()},
                                   "frame_back_above_plate": round(T["d_back"], 3)}}
    P2, C2 = Params(), Choices()
    G2 = Geom(P2)
    J = j1_geom(P2, C2, G2)
    b1 = os.path.join(out_dir, "GF_Jig_J1")
    j1_dxf(b1 + ".dxf", P2, C2, G2, J)
    iss, en, trn, yl = j1_sheet(b1, P2, C2, G2, J)
    res["J1"] = {"files": [b1 + ".dxf", b1 + ".pdf", b1 + ".png"], "layout_issues": iss, "notes_en": en,
                 "notes_tr": trn, "lowest_y": yl}
    res["J2"]["params_used"], res["J2"]["choices_used"] = dict(sorted(P.used.items())), C.used
    res["J1"]["params_used"], res["J1"]["choices_used"] = dict(sorted(P2.used.items())), C2.used
    return res


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        print(k, "issues:", len(v["layout_issues"]), v["lowest_y"])
        for i in v["layout_issues"]:
            print("   ", i)
