"""Oven front-sheet cut-out, variants S4 / R4 (GF-2.0: S8 withdrawn): DXF (1:1 mm, FRONT view, origin = cut-out
centre) and an A3 drawing sheet (PDF + PNG) with plan 1:2, hole table, section A-A 5:1, notes EN + TR.

  <venv>/Scripts/python.exe make_sheet.py            -> Mechanical/Rev3.0_GlassFront/drawings/GF_Sheet_{S4,R4}.*
"""
import datetime
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (Params, Choices, Rect, OUT_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text,
                       dxf_cross, stadium_pts, rev_note, master_ref, prev_rev)
from gf_geom import Geom
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT

VARIANTS = ("S4", "R4")                      # GF-2.0: S8 (GF-D02) withdrawn (master sheet_variants.S8_withdrawn)
DWG_NO = {"S4": "GF-D01", "R4": "GF-D03"}
WITHDRAWN = {"GF-D02": "S8"}
LAYERS = [("CUTOUT", 1, "CONTINUOUS"), ("HOLES", 7, "CONTINUOUS"), ("STUD_MARKS", 6, "CONTINUOUS"),
          ("GLASS_REF", 5, "DASHED"), ("LIP_REF", 8, "CONTINUOUS"), ("FLANGE_REF", 8, "PHANTOM"),
          ("TAPE_REF", 3, "CONTINUOUS"), ("TEXT", 7, "CONTINUOUS")]
C_REF = "#3b6fb6"     # glass reference colour
C_LIP = "0.45"
C_TAPE = "#2e8b57"
C_STUD = "#b0308f"
C_V2 = "#c0392b"


def f_mark(u0, v0, h):
    """orientation mark 'F' as line segments (bars point to +u); reads correctly in the FRONT view"""
    return [((u0, v0), (u0, v0 + h)), ((u0, v0 + h), (u0 + 0.6 * h, v0 + h)),
            ((u0, v0 + 0.55 * h), (u0 + 0.45 * h, v0 + 0.55 * h))]


def variant_data(P, C, G, var):
    """fastener list, hole size, tape/gasket description for a variant, all from the master"""
    S = P.raw["sheet_variants"]
    P._use("sheet_variants." + var, S[var])
    vtext = S[var]["value"]
    fl = P.fast_names()                                 # GF-2.0: F1-F4 only
    for f in fl:                                        # cross-check with the 'used_by' field of the master
        assert var in G.F[f]["used_by"], (var, f, G.F[f]["used_by"])
    stud = P.text("fasteners.hardware", "stud")
    stud_d = P.num("fasteners.hardware", r"M(\d+) x (\d+)", 1, name="stud")
    stud_l = P.num("fasteners.hardware", r"M(\d+) x (\d+)", 2, name="stud")
    d = dict(var=var, text=vtext, note=S[var]["note"], fast=fl, stud=stud, stud_d=stud_d, stud_l=stud_l)
    if var == "S4":
        # GF-1.1 round 3 (lead decision C5): weld-stud envelope after welding + axis position, from the stud note
        d["env_d"] = P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 1, name="stud")
        d["env_h"] = P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 2, name="stud")
        # requirement: stud axis to the cut-out (stud note = drawing_tolerances.sheet.stud_position_tol, round 4);
        # the template accuracy in the stud_position_tol note is the recommended means, not a second tolerance
        d["axis_tol"] = P.val("drawing_tolerances.sheet", "stud_position_tol")
        assert d["axis_tol"] == P.num("fasteners.hardware", r"stud axis must be within \+-([\d.]+) of its nominal "
                                                            r"position relative to the cut-out", name="stud")
        assert "REQUIREMENT" in P.item("drawing_tolerances.sheet", "stud_position_tol")["note"]
        d["templ_tol"] = P.num("drawing_tolerances.sheet", r"with \+-([\d.]+) accuracy is the recommended means",
                               name="stud_position_tol")
        d["perp"] = C("stud_perpendicularity_deg")                                   # [P]
        cb, _ = G.fastener_cuts()
        d["cb"] = (cb["cb_w"], cb["cb_l"])
    if var == "R4":
        d["hole"] = P.num("sheet_variants.R4.value", r"dia ([\d.]+) \+([\d.]+)/0 \(dia", 1)
        d["hole_tol_plus"] = P.num("sheet_variants.R4.value", r"dia ([\d.]+) \+([\d.]+)/0 \(dia", 2)
        d["hole_hw"] = P.num("fasteners.hardware", r"sheet hole dia ([\d.]+)", name="rivet")
        d["rivet_d"] = P.num("fasteners.hardware", r"dia ([\d.]+) LARGE-FLANGE blind rivet", name="rivet")
        assert d["rivet_d"] == P.num("sheet_variants.R4.value", r"\(dia ([\d.]+) LARGE-FLANGE blind rivet")
        d["proud"] = (P.num("sheet_variants.R4.value", r"heads ~([\d.]+)-([\d.]+) proud", 1),
                      P.num("sheet_variants.R4.value", r"heads ~([\d.]+)-([\d.]+) proud", 2))
        d["maker_hole"] = (P.num("sheet_variants.R4.value", r"GESIPA ([\d.]+)-([\d.]+)", 1),
                           P.num("sheet_variants.R4.value", r"GESIPA ([\d.]+)-([\d.]+)", 2))
        # GF-1.1 round 3: large-flange head dia 14 'K14' (DIN 7337 large-flange type)
        d["head_d"] = P.num("fasteners.hardware", r"head dia ([\d.]+) 'K\d+'", name="rivet")
        assert d["head_d"] == P.num("sheet_variants.R4.value", r"head dia ([\d.]+) 'K\d+'")
        d["head_k"] = re.search(r"'(K\d+)'", P.text("fasteners.hardware", "rivet")).group(1)
        d["head_std"] = re.search(r"\((DIN 7337 [^,]+),", P.text("fasteners.hardware", "rivet")).group(1)
        d["head_h"] = P.num("fasteners.hardware", r"modelled head height ([\d.]+) with an R([\d.]+) edge", 1,
                            name="rivet")
        d["head_edge_to_cut"] = P.num("sheet_variants.R4.note", r"dia-[\d.]+ head edge ([\d.]+) from the cut-out "
                                                                 r"corner arc")
        d["pad_face"] = P.num("sheet_variants.R4.note", r"pad face under the head ([\d.]+) mm2")
    d["tape"] = P.text("tape_and_gasket", "tape")
    return d


def change_note(P, G, vd):
    """GF-2.0 revision note + what changed on this sheet (old cut-out size from the master change_log)"""
    old = P.change("plan_rectangles.cut")[0]
    F1 = G.F["F1"]
    return "%s. Cut-out %s x %s (%s %s x %s), centred on the glass; %s at u ±%s / v ±%s; %s." % (
        rev_note(P), n2(G.cut.w), n2(G.cut.h), prev_rev(P), n2(old[1] - old[0]), n2(old[3] - old[2]),
        "holes F1-F4" if vd["var"] == "R4" else "studs F1-F4", n(abs(F1["u"])), n(abs(F1["v"])),
        "GF-D02 (S8) withdrawn")


# ============================================================================================================== DXF
def write_dxf(path, P, C, G, vd):
    doc, msp = new_dxf(LAYERS)
    dxf_rect(msp, G.cut, "CUTOUT")
    hole_rows = []
    for f in vd["fast"]:
        F = G.F[f]
        if vd["var"] == "R4":
            msp.add_circle((F["u"], F["v"]), vd["hole"] / 2.0, dxfattribs={"layer": "HOLES"})
        else:
            dxf_cross(msp, F["u"], F["v"], vd["stud_d"], "STUD_MARKS")
            msp.add_circle((F["u"], F["v"]), vd["stud_d"] / 2.0, dxfattribs={"layer": "STUD_MARKS"})
        dxf_text(msp, f, F["u"] + 4.0, F["v"] + 4.0, 3.0)
        hole_rows.append(f)
    dxf_rect(msp, G.glass, "GLASS_REF")
    dxf_rect(msp, G.window, "GLASS_REF")
    for r in (G.lip_in, G.lip_out, G.seat_out):
        dxf_rect(msp, r, "LIP_REF")
    dxf_rect(msp, G.flange, "FLANGE_REF")
    for f in ("F1", "F2", "F3", "F4"):
        msp.add_circle((G.F[f]["u"], G.F[f]["v"]), G.pad_d / 2.0, dxfattribs={"layer": "FLANGE_REF"})
    for r in G.strips.values():
        dxf_rect(msp, r, "TAPE_REF")
    for k, pts in G.dabs.items():
        dxf_poly(msp, [(x, y, 0.0) for x, y in pts], "TAPE_REF")
    # texts
    fl = G.flange
    dxf_text(msp, "GF SHEET CUT-OUT %s - %s - FRONT VIEW (cosmetic face), origin = cut-out centre, mm" %
             (vd["var"], P.revision), fl.x0, fl.y0 - 10.0, 3.5)
    dxf_text(msp, "CUTOUT = laser path (true arcs). %s" % (
        "HOLES = through holes dia %s +%s/0." % (n(vd["hole"]), n(vd["hole_tol_plus"])) if vd["var"] == "R4" else
        "STUD_MARKS = weld-stud centres on the BACK face (do not mark the front)."), fl.x0, fl.y0 - 15.0, 2.5)
    dxf_text(msp, "GLASS_REF / LIP_REF / FLANGE_REF / TAPE_REF = reference only, not cut.", fl.x0, fl.y0 - 19.0, 2.5)
    # orientation mark (top-left in the front view)
    for a, b in f_mark(fl.x0 + 2.0, fl.y1 + 4.0, 8.0):
        msp.add_line(a, b, dxfattribs={"layer": "TEXT"})
    dxf_text(msp, "orientation mark: reads correctly seen from the FRONT; TOP of the oven front = +v",
             fl.x0 + 10.0, fl.y1 + 6.0, 2.5)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(path)
    return {"layers": [l[0] for l in LAYERS], "holes_or_marks": hole_rows}


# ============================================================================================================ sheet
def plan_view(sh, P, C, G, vd, ox, oy, sc):
    V = View(sh, ox, oy, sc)
    g = G.flange
    # references
    V.rrect(g, ec="0.55", w=XTHIN, ls=(0, (6, 1.5, 1, 1.5)), geom=False)
    for f in ("F1", "F2", "F3", "F4"):
        V.circle(G.F[f]["u"], G.F[f]["v"], G.pad_d / 2.0, ec="0.65", w=XTHIN, geom=False, ls=(0, (2, 1.5)))
    for r in G.strips.values():
        V.rrect(r, fc="#d9eedf", ec=C_TAPE, w=XTHIN, geom=False)
    for pts in G.dabs.values():
        V.poly(pts, fc="#f0a030", ec="none", geom=False)
    for r in (G.seat_out, G.lip_out, G.lip_in):
        V.rrect(r, ec=C_LIP, w=XTHIN, geom=False)
    V.rrect(G.glass, ec=C_REF, w=XTHIN, ls=(0, (4, 1.5)), geom=False)
    V.rrect(G.window, ec=C_REF, w=XTHIN, ls=(0, (1.5, 1.2)), geom=False)
    # the part: cut-out
    V.rrect(G.cut, ec="k", w=THICK)
    # holes / stud marks + labels diagonally outwards
    for f in vd["fast"]:
        F = G.F[f]
        x, y = V.P(F["u"], F["v"])
        if vd["var"] == "R4":
            sh.circle(x, y, vd["hole"] / 2.0 * sc, ec="k", w=THICK)
            sh.circle(x, y, vd["head_d"] / 2.0 * sc, ec="0.45", w=XTHIN, geom=False, ls=(0, (3, 1.5)))
            V.cross(F["u"], F["v"], 2.6, c="k")
        else:
            sh.circle(x, y, vd["stud_d"] / 2.0 * sc, ec=C_STUD, w=THIN)
            V.cross(F["u"], F["v"], 2.6, c=C_STUD)
        su = 0 if abs(F["u"]) < 1e-6 else (1 if F["u"] > 0 else -1)
        sv = 0 if abs(F["v"]) < 1e-6 else (1 if F["v"] > 0 else -1)
        if su and sv:
            tx, ty, ha, va = x + su * 3.4, y + sv * 3.4, ("left" if su > 0 else "right"), ("bottom" if sv > 0 else "top")
        elif sv:
            tx, ty, ha, va = x + 2.2, y + sv * 3.0, "left", ("bottom" if sv > 0 else "top")
        else:
            tx, ty, ha, va = x + su * 3.2, y + 1.4, ("left" if su > 0 else "right"), "bottom"
        sh.T(tx, ty, f, fs=7, ha=ha, va=va, color=C_STUD if vd["var"] != "R4" else "k", weight="bold")
    # datum and centre lines
    V.centreline((g.x0 - 4, 0), (g.x1 + 4, 0))
    V.centreline((0, g.y0 - 4), (0, g.y1 + 4))
    x0, y0 = V.P(0, 0)
    sh.T(x0 + 1.5, y0 - 3.6, "DATUM 0,0 = cut-out centre", fs=6.2)
    # GF-2.0: the v2 window centre (v2 datum) lies only a fraction of a mm above this datum -> stated in note 9,
    # not drawn (a 1:2 dimension of that size would be illegible)
    sh.T(x0 + 1.5, y0 - 6.6, "= glass centre = window centre", fs=6.2)
    # dimensions: cut-out
    c = G.cut
    tol = P.val("drawing_tolerances.sheet", "cut_out_tol")
    top = V.P(0, g.y1)[1]
    left = V.P(g.x0, 0)[0]
    (xa, ya), (xb, yb) = V.P(c.x0, c.y1), V.P(c.x1, c.y1)
    sh.dim_h(xa, ya, xb, yb, top + 6.0, "%s ±%s" % (n2(c.w), n(tol)), fs=7.5)
    (xa, ya), (xb, yb) = V.P(c.x0, c.y0), V.P(c.x0, c.y1)
    sh.dim_v(xa, ya, xb, yb, left - 6.0, "%s ±%s" % (n2(c.h), n(tol)), fs=7.5)
    cx, cy = V.P(c.x1 - c.R, c.y1 - c.R)
    cR, _, _, cRt = P.onesided("drawing_tolerances.sheet", "cut_out_corner_R")
    assert abs(cR - c.R) < 1e-9, (cR, c.R)
    sh.radius(cx, cy, c.R * sc, 45, "4x R%s %s" % (n(c.R), cRt), L=7.0, fs=7, inside=True)
    # fastener pattern
    F1, F2, F4 = G.F["F1"], G.F["F2"], G.F["F4"]
    (xa, ya), (xb, yb) = V.P(F2["u"], F2["v"]), V.P(F1["u"], F1["v"])
    sh.dim_h(xa, ya, xb, yb, top + 13.0, "%s  (F2-F1)" % n2(abs(F1["u"] - F2["u"])), fs=7)
    (xa, ya), (xb, yb) = V.P(F2["u"], F4["v"]), V.P(F2["u"], F1["v"])
    sh.dim_v(xa, ya, xb, yb, left - 14.0, "%s  (F2-F3)" % n2(abs(F1["v"] - F4["v"])), fs=7)
    # section A-A cutting line on the top edge (view direction -u)
    su_ = C("section_u")
    pa, pb = V.P(su_, G.glass.y1 - 10.0), V.P(su_, g.y1 + 2.0)
    sh.L([pa[0], pa[0]], [pa[1], pa[1] + 3.0], w=THICK, c="k", geom=False)
    sh.L([pb[0], pb[0]], [pb[1] - 3.0, pb[1]], w=THICK, c="k", geom=False)
    sh.L([pa[0], pb[0]], [pa[1], pb[1]], w=XTHIN, c="k", geom=False, dashes=(10, 2, 2, 2))
    for (px, py) in (pa, pb):
        sh.L([px, px - 4.0], [py, py], w=XTHIN, geom=False)
        sh.arrow(px - 4.0, py, math.pi, "k")
    sh.T(pa[0] - 6.5, pa[1] - 1.2, "A", fs=8, weight="bold", ha="center")
    sh.T(pb[0] - 6.5, pb[1] - 1.2, "A", fs=8, weight="bold", ha="center")
    # reference labels: short horizontal leaders to the right
    right = V.P(g.x1, 0)[0]
    lx = right + 8.0
    tape_lab = "VHB strip, back (ref.)"
    labs = [((G.glass.x1, 50.0), "glass (ref.)", C_REF),
            ((G.window.x1, 35.0), "print window (ref.)", C_REF),
            ((G.lip_out.x1, 20.0), "lip + seat ring (ref.)", "0.35"),
            ((G.strips["right"].x1 - 1.0, -8.0), tape_lab, C_TAPE),
            ((g.x1, -25.0), "flange outline (ref.)", "0.35")]
    f4 = G.F["F4"]
    labs.append(((f4["u"] + G.pad_d / 2.0 * 0.7071, f4["v"] + G.pad_d / 2.0 * 0.7071), "corner pad dia %s (ref.)" %
                 n(G.pad_d), "0.35"))
    dk = G.dabs["F4_v"]
    labs.append(((sum(p[0] for p in dk) / len(dk), sum(p[1] for p in dk) / len(dk)), "corner dab", "#c87800"))
    for i, ((u, v), t, col) in enumerate(labs):
        px, py = V.P(u, v)
        ty = py if i < 5 else (oy - 22.0 - (i - 5) * 6.5)
        sh.leader(px, py, lx, ty, t, fs=6.2, c=col, head="dot")
    # orientation mark (top-left of the front view)
    fx, fy = 20.0, top + 9.0
    for a, b in f_mark(0, 0, 7.0):
        sh.L([fx + a[0], fx + b[0]], [fy + a[1], fy + b[1]], w=THICK, c="k", geom=False)
    sh.T(fx + 0.0, fy - 3.6, "TOP", fs=6.5, weight="bold")
    return V


def section_view(sh, P, C, G, vd, xs0, yd0, k):
    """section A-A through the top edge, s outward to the right, depth d down; scale k"""
    S = lambda s, d: (xs0 + k * s, yd0 - k * d)
    gt = P.d("glass_t")
    Zg = P.level("Z_GLASS_FRONT")
    D = lambda name: P.level(name) - Zg            # depth behind the flush plane
    d_sb, d_ff, d_fb = D("Z_SHEET_BACK"), D("Z_FLANGE_FRONT"), D("Z_FLANGE_BACK")
    d_gb, d_land, d_sw = D("Z_GLASS_BACK"), D("Z_LAND"), D("Z_STEPWALL_BACK")
    d_ctp = D("Z_CTP_FRONT")
    g2, lw_, g1 = G.g2, G.lip_w, G.g1
    s_lip0, s_lip1 = g2, g2 + lw_
    s_cut = s_lip1 + g1
    s_ring = s_lip1 + G.seat_w
    land = G.glass.y1 - G.pocket.y1                 # top edge land
    s_land = -land
    s_t0, s_t1 = G.tape_in.y1 - G.glass.y1, G.tape_out.y1 - G.glass.y1
    s_L, s_R = s_land - 2.5, s_t1 + 1.6
    d_bot = d_sw + 1.0
    panel_s = -(G.glass.y1 - G.panel.y1)
    poly = lambda pts, **kw: sh.poly([S(*p) for p in pts], **kw)
    a0 = P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 1, name="edge")
    a1 = P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 2, name="edge")
    ar = 0.5 * (a0 + a1)
    # glass, print on face 2, LOCA + panel stub, bead
    poly([(s_L, 0), (-ar, 0), (0, ar), (0, gt - ar), (-ar, gt), (s_L, gt)], fc="#cfe8f3", ec="k", w=THIN,
         closed=False)
    sh.L([S(s_L, gt)[0], S(-ar, gt)[0]], [S(s_L, gt)[1] - 0.35, S(-ar, gt)[1] - 0.35], w=0.7, c="k", geom=False)
    poly([(s_L, d_gb), (panel_s, d_gb), (panel_s, d_ctp), (s_L, d_ctp)], fc="#f6e7b4", ec="0.4", w=XTHIN, geom=False)
    poly([(s_L, d_ctp), (panel_s, d_ctp), (panel_s, d_bot), (s_L, d_bot)], fc="#e3e3e3", ec="0.4", w=XTHIN,
         geom=False)
    poly([(-(G.bead_edge + G.bead_w), d_gb), (-G.bead_edge, d_gb), (-G.bead_edge, d_land),
          (-(G.bead_edge + G.bead_w), d_land)], fc="#3a3a3a", ec="k", w=XTHIN, geom=False)
    # frame (typical section, no fastener): lip + step wall + flange + land plate
    fr = [(s_lip0, 0), (s_lip1, 0), (s_lip1, d_sb), (s_ring, d_sb), (s_ring, d_ff), (s_R, d_ff), (s_R, d_fb),
          (s_ring, d_fb), (s_ring, d_sw), (s_land, d_sw), (s_land, d_land), (s_lip0, d_land)]
    poly(fr, fc="#a7acb3", ec="k", w=THIN, hatch="\\\\\\\\", geom=True)
    # steel (this part) and tape / gasket
    poly([(s_cut, 0), (s_R, 0), (s_R, d_sb), (s_cut, d_sb)], fc="#d5d8dc", ec="k", w=THICK, hatch="////", geom=True)
    poly([(s_t0, d_sb), (s_t1, d_sb), (s_t1, d_ff), (s_t0, d_ff)], fc="#9fd4ac", ec=C_TAPE, w=XTHIN, geom=False)
    for s in (s_L, s_R):
        sh.L([S(s, -0.3)[0], S(s, d_bot)[0]], [S(s, -0.3)[1], S(s, d_bot)[1]], w=XTHIN, c="0.3", geom=False,
             dashes=(1, 1.5))
    # in-region labels (white background)
    inl = lambda s, d, t, fs=6.0: sh.T(*S(s, d), t, fs=fs, ha="center", va="center", allow_geom=True, bg="white")
    inl(s_L / 2.0 + 0.6, gt / 2.0, "GLASS %s, black print on face 2" % n(gt))
    inl((s_cut + s_R) / 2.0, d_sb / 2.0, "STEEL SHEET t %s  -  THIS PART" % n(d_sb), fs=6.2)
    inl((s_t0 + s_t1) / 2.0, (d_sb + d_ff) / 2.0, "VHB 12 x 1.1 -> %s  (gap t_gap)" % n(d_ff - d_sb))
    inl((s_ring + s_R) / 2.0, (d_ff + d_fb) / 2.0, "FLANGE (frame, PA6-GF30)")
    inl((s_land + s_lip0) / 2.0 - 0.6, (d_land + d_sw) / 2.0, "LAND (frame)")
    # flush plane
    xa, ya = S(s_L - 1.0, 0)
    xr = S(s_R, 0)[0] + 5.0
    sh.L([xa, xr + 6.0], [ya, ya], w=THIN, c=C_V2, geom=False, dashes=(14, 2, 2, 2))
    rss = P.get("checks")["flush_glass_vs_sheet_RSS"]
    wc = P.get("checks")["flush_glass_vs_sheet_WC"]
    tx = xr + 7.0
    sh.T(tx, ya + 0.6, "FLUSH PLANE", fs=6.6, color=C_V2, weight="bold")
    sh.T(tx, ya - 2.4, "glass front = lip top", fs=5.8, color=C_V2)
    sh.T(tx, ya - 4.9, "= sheet front", fs=5.8, color=C_V2)
    sh.T(tx, ya - 7.4, "±%s RSS / ±%s WC" % (n(round(rss, 2)), n(round(wc, 2))), fs=5.8, color=C_V2)
    # rows of dimensions above (projections from the flush plane); the chain g2 | lip | g1 is the top row so that
    # its texts can run to the right without crossing extension lines
    y0 = S(0, 0)[1]
    yd1, yd2, yd3 = y0 + 8.0, y0 + 15.0, y0 + 22.0
    sh.dim_h(*S(0, 0), *S(s_t0, 0), yd1, n(s_t0), fs=6.3, text_at=(S(0, 0)[0] - 6.0, yd1 - 2.6), ha="right")
    sh.dim_h(*S(s_t0, 0), *S(s_t1, 0), yd1, "tape %s" % n(s_t1 - s_t0), fs=6.3)
    sh.dim_h(*S(0, 0), *S(s_cut, 0), yd2, None)
    sh.T(S(0, 0)[0] - 6.0, yd2 - 0.9, "%s glass edge to cut edge" % n(s_cut), fs=6.3, ha="right", va="center")
    sh.dim_h(*S(s_cut, 0), *S(s_ring, 0), yd2, None, arrows="out")
    sh.T(S(s_ring, 0)[0] + 5.6, yd2 - 0.9, "%s overlap of the sheet on the seat ring" % n(s_ring - s_cut), fs=6.3,
         va="center")
    sh.dim_h(*S(0, 0), *S(s_lip0, 0), yd3, None, arrows="out")
    sh.T(S(0, 0)[0] - 5.6, yd3 - 0.9, "g2 %s" % n(g2), fs=6.3, ha="right", va="center")
    sh.dim_h(*S(s_lip0, 0), *S(s_lip1, 0), yd3, n(lw_), fs=6.3)
    sh.T(S((s_lip0 + s_lip1) / 2, 0)[0], yd3 + 3.6, "lip", fs=6.3, ha="center", va="bottom")
    sh.dim_h(*S(s_lip1, 0), *S(s_cut, 0), yd3, None, arrows="out")
    e0 = P.num("sheet_variants.common", r"deburr R([\d.]+)-([\d.]+)", 1, name="cut_out")
    e1 = P.num("sheet_variants.common", r"deburr R([\d.]+)-([\d.]+)", 2, name="cut_out")
    sh.T(S(s_cut, 0)[0] + 5.6, yd3 - 0.9, "g1 %s lip to the cut edge (edge deburred R%s-%s)" % (n(g1), n(e0), n(e1)),
         fs=6.3,
         va="center")
    # vertical dims right: sheet, gap, flange; left: glass, bond
    sh.dim_v(*S(s_R, 0), *S(s_R, d_sb), xr, n(d_sb), fs=6.3, side="right")
    sh.dim_v(*S(s_R, d_sb), *S(s_R, d_ff), xr, n(d_ff - d_sb), fs=6.3, side="right")
    sh.dim_v(*S(s_R, d_ff), *S(s_R, d_fb), xr, n(d_fb - d_ff), fs=6.3, side="right")
    xl = S(s_L, 0)[0] - 5.0
    sh.dim_v(*S(s_L, 0), *S(s_L, gt), xl, n(gt), fs=6.3)
    sh.dim_v(*S(s_L, gt), *S(s_L, d_land), xl, n(d_land - d_gb), fs=6.3)
    # bead width + edge distance below
    yb = S(0, d_bot)[1] - 4.0
    sh.dim_h(*S(-(G.bead_edge + G.bead_w), d_land), *S(-G.bead_edge, d_land), yb, "bead %s" % n(G.bead_w), fs=6.3)
    sh.dim_h(*S(-G.bead_edge, d_land), *S(0, gt), yb, None, arrows="out")
    sh.T(S(0, 0)[0] + 5.6, yb - 0.9, n(G.bead_edge), fs=6.3, va="center")
    # leaders below
    yl = yb - 6.0
    sh.leader(*S(panel_s - 0.8, d_ctp + 1.5), S(s_L, 0)[0] + 2.0, yl, "LOCA %s + CTP / panel (ref.)" %
              n(d_ctp - d_gb), fs=6.0, head="dot")
    sh.leader(*S((s_lip0 + s_ring) / 2.0, d_fb + 1.0), S(s_ring, 0)[0] + 9.0, yl,
              "step wall + seat ring: hard stop for the cut edge", fs=6.0, head="dot")
    return S


def notes_text(P, C, G, vd):
    t_sheet = P.d("t_sheet")
    t_tol = P.val("drawing_tolerances.sheet", "thickness_tol")
    t_res = P.num("drawing_tolerances.sheet", r"\(([\d.]+) restricted\)", name="thickness_tol")
    cut_tol = P.val("drawing_tolerances.sheet", "cut_out_tol")
    r0 = P.num("sheet_variants.common", r"deburr R([\d.]+)-([\d.]+)", 1, name="cut_out")
    r1 = P.num("sheet_variants.common", r"deburr R([\d.]+)-([\d.]+)", 2, name="cut_out")
    flat = P.val("drawing_tolerances.sheet", "flatness_round_window")
    v2 = G.v2_window()
    dv2 = v2["centre_uv_from_VA"][1]
    c = G.cut
    gtol = C("sheet_general_tol")
    cg1 = G.corner_gap(G.lip_out, G.cut)
    _, _, _, cRt = P.onesided("drawing_tolerances.sheet", "cut_out_corner_R")
    en = [
        "Material: steel sheet t = %s ±%s (EN 10131, normal); order ±%s (restricted) if possible - the thickness is "
        "the visible step between lip and steel." % (n(t_sheet), n(t_tol), n(t_res)),
        "Cut-out %s x %s, laser cut, ±%s on size and position to the datum; closed contour, true arcs (layer "
        "CUTOUT). CORNER RADIUS R%s %s (one-sided): the cut corner must not come inside an R%s radius gauge - a "
        "smaller radius opens the corner gap to the frame lip and is accepted, a larger one closes it and is "
        "rejected." % (n2(c.w), n2(c.h), n(cut_tol), n(c.R), cRt, n(c.R)),
        "FINISHED PART: the cut-out size, its corner radius and the gaps to the frame lip (sides %s, corners about "
        "%s) apply AFTER coating - correct the laser path for the coat build-up on the cut edge. The sheet thickness "
        "INCLUDING the coating on both faces must equal the frame's lip height t_sheet = %s (as designed). Agree the "
        "finish and its thickness before the frame tool is cut (the lip height follows t_sheet)." % (
            n(G.g1), n(round(cg1, 2), 2), n(t_sheet)),
        "VISIBLE EDGE: no pierce point, lead-in / lead-out, micro-joint or tab on the cut-out edge. Pierce and lead in "
        "on the scrap (slug) side.",
        "NO SHARP EDGES: cut with the FRONT (cosmetic) face up (dross and burr on the BACK); the cut edge of the "
        "window is deburred on both faces and broken to R%s-%s on the front edge (brush / belt) BEFORE coating "
        "(master: 'deburr R%s-%s before coating')." % (n(r0), n(r1), n(r0), n(r1)),
    ]
    if vd["var"] == "R4":
        en.append("Holes F1-F4: dia %s +%s/0 through, after coating, for dia %s LARGE-FLANGE blind rivets (%s, head "
                  "dia %s '%s', black; tri-fold / bulb; maker's hole %s-%s). Deburr both sides. Heads %s-%s proud, "
                  "set from the front at assembly; head edge %s from the cut-out corner arc (dashed on the "
                  "plan)." % (n(vd["hole"]), n(vd["hole_tol_plus"]), n(vd["rivet_d"]), vd["head_std"],
                              ("%g" % vd["head_d"]), vd["head_k"], n(vd["maker_hole"][0]), n(vd["maker_hole"][1]),
                              n(vd["proud"][0]), n(vd["proud"][1]), n(vd["head_edge_to_cut"])))
    else:
        en.append("%d x M%d x %d CD (capacitor-discharge) weld studs ISO 13918 on the BACK face at %s, welded BEFORE "
                  "coating; mask the threads. AFTER WELDING: (a) the flange INCLUDING weld collar and flash lies "
                  "within dia %s x %s high (it sits in a %s x %s counterbore in the frame); (b) the stud axis is "
                  "within ±%s of nominal, measured relative to the cut-out - the only position tolerance; (c) the "
                  "stud is perpendicular to the sheet within %s deg [P]. Recommended means: a welding template that "
                  "locates on the cut-out, accurate to ±%s. No mark may show on the front after coating: release by "
                  "a test coupon (same sheet, same finish)." % (
                      len(vd["fast"]), vd["stud_d"], vd["stud_l"], "F1-F%d" % len(vd["fast"]), n(vd["env_d"]),
                      n(vd["env_h"]), n(vd["cb"][0]), n(vd["cb"][1]), n(vd["axis_tol"]), n(vd["perp"]),
                      n(vd["templ_tol"])))
    en += [
        "Flatness round the cut-out %s. Back face in the %s zone (TAPE_REF) flat, clean, free of silicone and release "
        "agent; VHB on powder coat needs 3M Primer 94 (confirm with the coater)." % (n(flat), "VHB"),
        "Reference layers GLASS_REF, LIP_REF, FLANGE_REF, TAPE_REF are not cut.%s" % (
            " STUD_MARKS are positions on the BACK face - never laser-mark the front." if vd["var"] != "R4" else ""),
        "Datum = cut-out centre = glass centre = print-window centre; pattern symmetric about both axes. The datum is "
        "%s below the v2 window centre (datum of Rev3.0_FrontSheet_Pattern_v2.dxf, window %s x %s R%s, superseded)."
        % (n(dv2, 2), n2(v2["w"]), n2(v2["h"]), n(v2["R"])),
        "Untoleranced dimensions %s. Dimensions in mm. Do not scale the drawing; use the DXF." % gtol,
    ]
    trn = [
        "Malzeme: çelik sac, t = %s ±%s mm (EN 10131); mümkünse ±%s (dar tolerans) sipariş edin." % (
            n(t_sheet), n(t_tol), n(t_res)),
        "Pencere: lazer kesim %s x %s mm; ölçü ve konum toleransı ±%s mm. KÖŞE RADYUSU R%s %s (tek yönlü): "
        "kesim köşesi R%s radyus mastarının içine girmemelidir - daha küçük radyus çerçeve dudağına köşe boşluğunu "
        "açar (kabul), daha büyük radyus boşluğu kapatır (red)." % (n2(c.w), n2(c.h), n(cut_tol), n(c.R), cRt,
                                                                   n(c.R)),
        "GÖRÜNÜR KESİM KENARINDA delme (piercing) noktası, giriş/çıkış izi, mikro bağlantı veya köprü "
        "OLMAYACAKTIR; delme ve giriş hurda (iç parça) tarafında yapılacaktır.",
        "BİTMİŞ PARÇA: pencere ölçüsü, köşe radyusu ve çerçeve dudağına boşluklar (kenarlarda %s, köşelerde yaklaşık "
        "%s) BOYADAN SONRA geçerlidir; lazer yolu kesim kenarındaki boya kalınlığına göre düzeltilecektir. Sac "
        "kalınlığı, iki yüzdeki boya DAHİL, çerçeve dudak yüksekliğine (t_sheet = %s) eşit olmalıdır. Kaplama ve "
        "kalınlığı, çerçeve kalıbı yapılmadan önce mutabık kalınacaktır." % (n(G.g1), n(round(cg1, 2), 2),
                                                                            n(t_sheet)),
        "KESKİN KENAR OLMAYACAK: kesim ön (görünür) yüz üstte yapılacak, çapak ve cüruf arka yüzde kalacaktır; pencere "
        "kesim kenarının boyadan ÖNCE iki yüzde çapağı alınacak ve ön kenarı R%s-%s kırılacaktır (fırça / bant)." % (
            n(r0), n(r1)),
    ]
    if vd["var"] == "R4":
        trn.append("Perçin delikleri F1-F4: Ø%s +%s/0, boyadan sonra; Ø%s GENİŞ BAŞLI kör perçin için (DIN 7337 "
                   "geniş başlı tip, baş Ø%s '%s', siyah; tri-fold / bulb). Delikler iki yüzden çapaksız olacaktır. "
                   "Perçin başı %s-%s mm çıkıntılı; baş kenarı pencere köşe yayından %s mm." % (
                       n(vd["hole"]), n(vd["hole_tol_plus"]), n(vd["rivet_d"]), ("%g" % vd["head_d"]), vd["head_k"],
                       n(vd["proud"][0]), n(vd["proud"][1]), n(vd["head_edge_to_cut"])))
    else:
        trn.append("%d adet M%d x %d kondansatör deşarjlı (CD) kaynak saplaması, ISO 13918, ARKA yüze F1-F%d, "
                   "boyadan ÖNCE kaynatılacak; dişler maskelenecek. KAYNAKTAN SONRA: (a) kaynak yakası ve çapak "
                   "DAHİL flanş Ø%s x %s yükseklik zarfı içinde kalacak (çerçevedeki %s x %s oval havşaya oturur); "
                   "(b) saplama ekseni, pencereye göre ölçülerek, nominal konumdan ±%s mm içinde - tek konum "
                   "toleransı budur; (c) saplama saca dik, sapma en fazla %s derece [P]. Önerilen yöntem: pencereye "
                   "oturan, ±%s mm hassasiyetli kaynak şablonu. Ön yüzde iz görünmeyecek - seri öncesi deneme "
                   "numunesi onaylanacaktır." % (len(vd["fast"]), vd["stud_d"], vd["stud_l"], len(vd["fast"]),
                                                 n(vd["env_d"]), n(vd["env_h"]), n(vd["cb"][0]), n(vd["cb"][1]),
                                                 n(vd["axis_tol"]), n(vd["perp"]), n(vd["templ_tol"])))
    trn += [
        "Pencere çevresi düzlemsellik %s mm. Arka yüzde %s bölgesi (TAPE_REF) düz, temiz, silikon ve kalıp "
        "ayırıcıdan arınmış olacaktır." % (n(flat), "bant"),
        "Referans katmanları kesilmez%s." % ("; saplama işaretleri (STUD_MARKS) ARKA yüz konumlarıdır, ön yüze "
                                              "markalama yapılmaz" if vd["var"] != "R4" else ""),
        "Toleransı belirtilmemiş ölçüler %s. Ölçüler mm. Resimden ölçü almayın; DXF dosyasını kullanın." % gtol,
    ]
    return en, [tr(x) for x in trn]


def make_variant(var, out_dir=OUT_DIR):
    P, C = Params(), Choices()
    G = Geom(P)
    vd = variant_data(P, C, G, var)
    base = os.path.join(out_dir, "GF_Sheet_%s" % var)
    dxf_info = write_dxf(base + ".dxf", P, C, G, vd)

    sh = Sheet()
    sh.frame()
    # ---- plan 1:2
    V = plan_view(sh, P, C, G, vd, ox=104.0, oy=192.0, sc=0.5)
    sh.T(16.0, 279.0, "PLAN - FRONT VIEW (cosmetic face, seen from in front of the oven)   1 : 2", fs=8.5,
         weight="bold")
    sh.T(16.0, 274.5, "Laser path = thick line. %s" % (
        "Holes dia %s through; dashed dia %s = rivet head (ref.)." % (n(vd["hole"]), ("%g" % vd["head_d"]))
        if var == "R4" else
        "Weld studs (magenta) are on the BACK face - positions only."), fs=6.5)
    # ---- section A-A 5:1
    sh.T(214.0, 279.0, "SECTION A-A  (typical edge, top; glass_t %s)   5 : 1" % n(P.d("glass_t")), fs=8.5,
         weight="bold")
    section_view(sh, P, C, G, vd, xs0=272.0, yd0=240.0, k=5.0)
    # ---- hole table
    rows = [["ID", "u", "v", "feature", "face", "to cut edge"]]
    for f in vd["fast"]:
        F = G.F[f]
        d = float(G.cut.sdf(F["u"], F["v"]))
        feat = ("hole dia %s +%s/0" % (n(vd["hole"]), n(vd["hole_tol_plus"]))) if var == "R4" else \
            ("weld stud M%d x %d, axis ±%s" % (vd["stud_d"], vd["stud_l"], n(vd["axis_tol"])))
        rows.append([f, n(F["u"]), n(F["v"]), feat, "through" if var == "R4" else "BACK", n2(d)])
    y = 133.0
    sh.T(16.0, y, "HOLE / STUD TABLE  (front view: u right, v up, from the datum; mm)", fs=7.5, weight="bold")
    y = sh.table(16.0, y - 1.0, [0, 12, 32, 52, 102, 122], rows, fs=6.8, widths=150)
    # the R4 note's dia-10 comparison is design history -> not printed
    vtxt = vd["text"].replace("+-", "±")
    assert "template +-" not in vd["text"] or "recommended" in vd["text"], vd["text"]
    vnote = vd["note"].split("; pad face")[0].replace(" (GF-2.0)", ", GF-2.0")
    var_txt = "VARIANT %s: %s (%s)." % (var, vtxt, vnote)
    for ln in sh.wrap(var_txt, 192.0, 6.6):
        y -= 3.2
        sh.T(16.0, y, ln, fs=6.6, weight="bold")
    sl = G.strip_len
    extra = ("Tape (frame side, ref.): %s; strips top/bottom %s, sides %s long, ending %s before the corner "
             "pads; corner dabs of bead adhesive close the 8 strip-end gaps." % (
                 vd["tape"], n2(sl["top_bottom"]), n2(sl["sides"]), n(G.tape_margin)))
    for ln in sh.wrap(extra, 192.0, 6.2):
        y -= 3.0
        sh.T(16.0, y, ln, fs=6.2)
    # ---- reference outlines table
    y -= 5.0
    sh.T(16.0, y, "OUTLINES IN THE DXF (front view, centred on the datum)", fs=7.0, weight="bold")
    ref_rows = [["layer", "outline", "size", "R"],
                ["CUTOUT", "sheet cut-out (laser)", "%s x %s" % (n2(G.cut.w), n2(G.cut.h)), n(G.cut.R)],
                ["GLASS_REF", "glass / print window", "%s x %s / %s x %s" % (n2(G.glass.w), n2(G.glass.h),
                                                                            n2(G.window.w), n2(G.window.h)),
                 "%s / %s" % (n(G.glass.R), n(G.window.R))],
                ["LIP_REF", "lip inner / outer / seat ring", "%s x %s / %s x %s / %s x %s" % (
                    n2(G.lip_in.w), n2(G.lip_in.h), n2(G.lip_out.w), n2(G.lip_out.h), n2(G.seat_out.w),
                    n2(G.seat_out.h)), "%s / %s / %s" % (n(G.lip_in.R), n(G.lip_out.R), n(G.seat_out.R))],
                ["FLANGE_REF", "frame flange / corner pads", "%s x %s / dia %s" % (n2(G.flange.w), n2(G.flange.h),
                                                                                n(G.pad_d)), n(G.flange.R)],
                ["TAPE_REF", "tape band (back face)",
                 "%s ... %s outside the glass edge" % (n(G.tape_in.y1 - G.glass.y1), n(G.tape_out.y1 - G.glass.y1)),
                 "-"]]
    y = sh.table(16.0, y - 0.5, [0, 22, 66, 148], ref_rows, fs=6.3, widths=192)
    y -= 3.4
    sh.T(16.0, y, "Gaps (20 C, finished parts): glass-lip g2 sides %s / corners %s; lip-cut-out g1 sides %s / corners %s "
                  "(cut-out R%s and glass R%s are not concentric with the lip R%s / R%s)." % (
                      n(G.g2), n(round(G.corner_gap(G.glass, G.lip_in), 3), 3), n(G.g1),
                      n(round(G.corner_gap(G.lip_out, G.cut), 3), 3), n(G.cut.R), n(G.glass.R), n(G.lip_out.R),
                      n(G.lip_in.R)), fs=6.0)
    # ---- notes
    en, trn = notes_text(P, C, G, vd)
    ytop = 186.0
    ye = sh.notes(212.0, ytop, 95.0, en, fs=6.2, head="NOTES", head_fs=7.5)
    yt = sh.notes(312.0, ytop, 94.0, trn, fs=6.2, head="NOTLAR (Türkçe)", head_fs=7.5)
    # ---- title block
    today = datetime.date.today().isoformat()
    sh.title_block({
        "title": "OVEN FRONT SHEET - CUT-OUT %s" % var,
        "subtitle": "Rev3.0 OVEN CONTROLLER, glass-front module GF  /  fırın ön sacı pencere kesimi",
        "source": "all dimensions from %s; border and g_bend gated by the real-panel fold test GF-D21" % master_ref(P),
        "project": "files: GF_Sheet_%s.dxf (1:1, front view, origin = cut-out centre) + this sheet" % var,
        "change": change_note(P, G, vd),
        "dwg": DWG_NO[var], "rev": P.revision, "scale": "1:2, 5:1", "date": today,
        "drawn": "make_sheet.py", "size": "A3  mm",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(base + ".pdf", base + ".png", dpi=200)
    return {"variant": var, "files": [base + ".dxf", base + ".pdf", base + ".png"], "dxf": dxf_info,
            "layout_issues": issues, "params_used": dict(sorted(P.used.items())), "choices_used": C.used,
            "notes_en": en, "notes_tr": trn,
            "hole_table": [dict(zip(rows[0], r)) for r in rows[1:]],
            "lowest_note_y": [round(ye, 1), round(yt, 1), round(y, 1)]}


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    return {v: make_variant(v) for v in VARIANTS}


if __name__ == "__main__":
    import json
    res = run()
    for v, r in res.items():
        print(v, "issues:", len(r["layout_issues"]), "notes bottom", r["lowest_note_y"])
        for i in r["layout_issues"]:
            print("   ", i)
