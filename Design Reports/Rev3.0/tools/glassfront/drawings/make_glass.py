"""Cover glass: DXF (front view, layers OUTLINE / PRINT_BLACK / WINDOW / LOGO_ZONE / BEAD_ZONE_REF / TEXT),
A3 drawing sheet (PDF + PNG) and the 1:1 print artwork (vector PDF, seen from the printed face = mirrored).

  <venv>/Scripts/python.exe make_glass.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Glass.{dxf,pdf,png},
                                                GF_Glass_Print_1to1.pdf (+ previews/GF_Glass_Print_1to1_preview.png)
"""
import datetime
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

from gf_common import (Params, Choices, Rect, OUT_DIR, BRAND_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect,
                       dxf_text, bulge_to_points, rev_note, master_ref, prev_rev)
from gf_geom import Geom
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT, lw

LAYERS = [("OUTLINE", 7, "CONTINUOUS"), ("PRINT_BLACK", 250, "CONTINUOUS"), ("WINDOW", 1, "CONTINUOUS"),
          ("LOGO_ZONE", 4, "DASHED"), ("BEAD_ZONE_REF", 3, "DASHED"), ("TEXT", 7, "CONTINUOUS")]
F_MARK_H = 8.0


def f_mark(u0, v0, h):
    return [((u0, v0), (u0, v0 + h)), ((u0, v0 + h), (u0 + 0.6 * h, v0 + h)),
            ((u0, v0 + 0.55 * h), (u0 + 0.45 * h, v0 + 0.55 * h))]


def glass_data(P, C, G):
    d = {}
    d["setback"] = (P.num("print", r"setback ([\d.]+)-([\d.]+)", 1, name="print_layers"),
                    P.num("print", r"setback ([\d.]+)-([\d.]+)", 2, name="print_layers"))
    d["setback_nom"] = 0.5 * (d["setback"][0] + d["setback"][1])
    d["ink_t"] = (P.num("print", r"(\d+)-(\d+) um", 1, name="print_layers"),
                  P.num("print", r"(\d+)-(\d+) um", 2, name="print_layers"))
    d["layers_txt"] = P.text("print", "print_layers")
    d["ink_txt"] = P.text("print", "ink")
    # outline (GF-1.1 round 4): value = tolerance REQUESTED (CNC-ground); the accepted fallback is in the note
    d["outline_tol"] = P.val("drawing_tolerances.glass", "outline_tol")
    d["outline_fallback"] = P.num("drawing_tolerances.glass", r"\+-([\d.]+) is the accepted fallback",
                                  name="outline_tol")
    d["flat"] = P.val("drawing_tolerances.glass", "flatness")
    d["flat_zone"] = (P.num("drawing_tolerances.glass", r"over the (\d+) x (\d+) bond zone", 1, name="flatness"),
                      P.num("drawing_tolerances.glass", r"over the (\d+) x (\d+) bond zone", 2, name="flatness"))
    d["flat_pane"] = P.num("drawing_tolerances.glass", r"<= ([\d.]+) over the pane", name="flatness")
    # GF-1.1 round 3: one-sided corner radius from the master (drawing_tolerances.glass.corner_R)
    d["R_val"], d["R_plus"], d["R_minus"], d["R_tol_txt"] = P.onesided("drawing_tolerances.glass", "corner_R")
    assert abs(d["R_val"] - G.glass.R) < 1e-9, (d["R_val"], G.glass.R)
    d["rim"] = C("print_rim_max")
    d["ink_strength"] = (P.num("print", r"(\d+) -> about (\d+) MPa", 1, name="ink"),
                         P.num("print", r"(\d+) -> about (\d+) MPa", 2, name="ink"))
    d["glass_old"], d["glass_new"] = P.change("plan_rectangles.glass")     # previous -> current outline (abs)
    d["border"] = P.d("border")
    d["logo_glass_min"] = P.num("logo_zone", r">= ([\d.]+) from the glass edge", name="logo_h")
    d["edge_txt"] = P.text("drawing_tolerances.glass", "edge")
    d["edge_note"] = P.item("drawing_tolerances.glass", "edge")["note"]
    d["arris"] = (P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 1, name="edge"),
                  P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 2, name="edge"))
    d["win_tol"] = P.val("drawing_tolerances.print", "window_size_tol")
    d["p2e"] = P.num("drawing_tolerances.print", r"print-to-edge \+-([\d.]+)", name="window_position")
    d["win_pos_txt"] = P.text("drawing_tolerances.print", "window_position")
    d["types"] = P.raw["driving_parameters"][0]["types"]
    P._use("driving_parameters.glass_t.types", d["types"])
    d["allowed"] = P.raw["driving_parameters"][0]["allowed"]
    d["glass_t"] = P.d("glass_t")
    d["logo_h_note"] = P.item("logo_zone", "logo_h")["note"]
    d["stroke_min"] = P.num("logo_zone", r"strokes >= ([\d.]+)", name="logo_h")
    d["logo_gap"] = P.num("logo_zone", r">= ([\d.]+) from the window", name="logo_h")
    # the zone must meet the master's own logo_h rule (logo_centre corrected 2026-11-16)
    assert G.window.y0 - G.logo.y1 >= d["logo_gap"] - 1e-6 and \
        G.logo.y0 - G.glass.y0 >= d["logo_glass_min"] - 1e-6, ("logo zone violates the logo_h rule", G.logo)
    d["qty"] = C("qty_glass")
    d["ovens"] = C("qty_ovens")
    d["spare_pct"] = int(round(100.0 * (d["qty"] - d["ovens"]) / d["ovens"]))
    d["samples"] = C("glass_samples")
    d["px"] = C("display_px")
    d["outer_print"] = G.glass.offset(-d["setback_nom"], "print_outer")
    return d


# ============================================================================================================== DXF
def write_dxf(path, P, C, G, gd):
    import ezdxf
    doc, msp = new_dxf(LAYERS)
    dxf_rect(msp, G.glass, "OUTLINE")
    po = gd["outer_print"]
    dxf_rect(msp, po, "PRINT_BLACK")
    dxf_rect(msp, G.window, "PRINT_BLACK")
    h = msp.add_hatch(color=250, dxfattribs={"layer": "PRINT_BLACK"})
    h.set_solid_fill(color=250)
    h.paths.add_polyline_path([(x, y, b) for x, y, b in po.bulge_pts()], is_closed=True, flags=1)
    h.paths.add_polyline_path([(x, y, b) for x, y, b in G.window.bulge_pts()], is_closed=True, flags=16)
    dxf_rect(msp, G.window, "WINDOW")
    dxf_rect(msp, G.logo, "LOGO_ZONE")
    dxf_rect(msp, G.bead_out, "BEAD_ZONE_REF")
    dxf_rect(msp, G.bead_inn, "BEAD_ZONE_REF")
    g = G.glass
    dxf_text(msp, "GF COVER GLASS - %s - FRONT VIEW (seen from face 1, the user side); PRINT ON FACE 2 (back)" %
             P.revision, g.x0, g.y0 - 8.0, 3.0)
    dxf_text(msp, "PRINT_BLACK = black ink area (outer boundary %s inside the outline, window removed; solid hatch "
             "for film output). Mirror for the printing screen (see GF_Glass_Print_1to1.pdf)." %
             n(gd["setback_nom"]), g.x0, g.y0 - 12.0, 2.2)
    dxf_text(msp, "LOGO_ZONE = reserved %s x %s max, %s from the window, %s from the glass edge (artwork not "
             "released). BEAD_ZONE_REF = adhesive bond band (reference)." % (
                 n(G.logo.w), n(G.logo.h), n(G.window.y0 - G.logo.y1), n(G.logo.y0 - g.y0)), g.x0, g.y0 - 15.5, 2.2)
    for a, b in f_mark(g.x0 + 12.0, g.y1 + 5.0, F_MARK_H):
        msp.add_line(a, b, dxfattribs={"layer": "TEXT"})
    dxf_text(msp, "TOP - orientation mark reads correctly from the FRONT", g.x0 + 20.0, g.y1 + 7.0, 2.5)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(path)


# ============================================================================================================ sheet
def plan(sh, P, C, G, gd, ox, oy):
    V = View(sh, ox, oy, 1.0)
    g, w = G.glass, G.window
    # print area (seen through the glass from the front): grey with the clear window
    outer = V.Pa(gd["outer_print"].boundary(n_arc=24, step=2.0))
    inner = V.Pa(w.boundary(n_arc=8, step=2.0))[::-1]
    verts = list(outer) + [outer[0]] + list(inner) + [inner[0]]
    codes = [Path.MOVETO] + [Path.LINETO] * (len(outer) - 1) + [Path.CLOSEPOLY] + \
            [Path.MOVETO] + [Path.LINETO] * (len(inner) - 1) + [Path.CLOSEPOLY]
    sh.ax.add_patch(PathPatch(Path(verts, codes), fc="#c8c8c8", ec="none", zorder=1))
    V.rrect(g, ec="k", w=THICK)
    V.rrect(w, ec="k", w=THIN)
    V.rrect(G.logo, ec="#1f77b4", w=THIN, ls=(0, (4, 2)), geom=False)
    for r in (G.bead_out, G.bead_inn):
        V.rrect(r, ec="#2e8b57", w=XTHIN, ls=(0, (2, 1.5)), geom=False)
    V.rrect(G.panel, ec="0.45", w=XTHIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    # centre lines, datum, window centre
    V.centreline((g.x0 - 5, 0), (g.x1 + 5, 0))
    V.centreline((0, g.y0 - 2), (0, g.y1 + 5))
    x0, y0 = V.P(0, 0)
    wc = w.c
    xw, yw = V.P(*wc)
    sh.circle(xw, yw, 1.0, ec="k", w=XTHIN, geom=False)
    if abs(wc[0]) < 1e-6 and abs(wc[1]) < 1e-6:
        # GF-2.0: equal borders -> the window centre IS the glass centre (master plan_points)
        sh.T(x0 + 1.8, y0 + 1.2, "glass centre = window centre (datum)", fs=6.0, allow_geom=True)
    else:
        sh.T(x0 + 1.5, y0 + 1.2, "glass centre (datum)", fs=6.0, allow_geom=True)
        sh.dim_v(x0, y0, xw, yw, x0 - 8.0, None)
        sh.T(x0 - 9.5, (y0 + yw) / 2, "%s" % n(wc[1]), fs=6.5, ha="right", va="center", rot=90)
        sh.T(xw + 1.8, yw + 1.2, "window centre", fs=6.0)
    # labels inside
    sh.T(*V.P(w.x0 + 6.0, w.y1 - 8.0), "WINDOW (clear, no ink)  %s x %s ±%s, R%s" % (
        n2(w.w), n2(w.h), n(gd["win_tol"]), n(w.R)), fs=7, ha="left")
    sh.T(*V.P(w.x0 + 6.0, (w.y1 + g.y1) / 2.0), "BLACK PRINT on face 2 (seen through the glass)", fs=6.5,
         ha="left", va="center")
    sh.T(*V.P(G.logo.x0 + 3.0, G.logo.c[1] + 4.3), "LOGO ZONE (reserved, max)", fs=6.3, ha="left",
         color="#1f77b4", va="center")
    sh.T(*V.P(G.logo.x0 + 3.0, G.logo.c[1] + 1.3), "%s from the window, %s from the glass edge; artwork: note 11" % (
        n(w.y0 - G.logo.y1), n(G.logo.y0 - g.y0)), fs=6.0, ha="left", color="#1f77b4", va="center",
         bg="#c8c8c8")                  # print-grey box: the vertical centre line does not run through the text
    # top chain: border | window | border; overall
    top = V.P(0, g.y1)[1]
    xa, xb = V.P(g.x0, 0)[0], V.P(g.x1, 0)[0]
    xwa, xwb = V.P(w.x0, 0)[0], V.P(w.x1, 0)[0]
    yg, ywt = V.P(0, g.y1)[1], V.P(0, w.y1)[1]
    sh.dim_h(xa, yg, xwa, ywt, top + 7.0, "%s ±%s" % (n(w.x0 - g.x0), n(gd["p2e"])), fs=7)
    sh.dim_h(xwa, ywt, xwb, ywt, top + 7.0, "%s ±%s" % (n2(w.w), n(gd["win_tol"])), fs=7)
    sh.dim_h(xwb, ywt, xb, yg, top + 7.0, "%s ±%s" % (n(g.x1 - w.x1), n(gd["p2e"])), fs=7)
    sh.dim_h(xa, yg, xb, yg, top + 14.0, "%s ±%s  (±%s fallback, note 3)" % (
        n2(g.w), n(gd["outline_tol"]), n(gd["outline_fallback"])), fs=7.5)
    # left chain: top border | window | bottom border (GF-2.0: all four borders equal); overall
    left = V.P(g.x0, 0)[0]
    yb, ywb = V.P(0, g.y0)[1], V.P(0, w.y0)[1]
    sh.dim_v(left, yg, xwa, ywt, left - 7.0, "%s ±%s" % (n(g.y1 - w.y1), n(gd["p2e"])), fs=7)
    sh.dim_v(xwa, ywt, xwa, ywb, left - 7.0, "%s ±%s" % (n2(w.h), n(gd["win_tol"])), fs=7)
    sh.dim_v(xwa, ywb, left, yb, left - 7.0, "%s ±%s" % (n(w.y0 - g.y0), n(gd["p2e"])), fs=7)
    sh.dim_v(left, yb, left, yg, left - 14.0, "%s ±%s  (±%s fallback, note 3)" % (
        n2(g.h), n(gd["outline_tol"]), n(gd["outline_fallback"])), fs=7.5)
    # radii
    cx, cy = V.P(g.x1 - g.R, g.y1 - g.R)
    sh.radius(cx, cy, g.R, 45, "4x R%s %s (note 4)" % (n(g.R), gd["R_tol_txt"]), L=6.0, fs=7)
    cx, cy = V.P(w.x1 - w.R, w.y1 - w.R)
    sh.radius(cx, cy, w.R, 45, "4x R%s (window)" % n(w.R), L=6.0, fs=6.5, inside=True)
    # logo zone dims
    lz = G.logo
    yl = V.P(0, g.y0)[1] - 4.5                      # below the glass edge (the zone is only 2.5 above it)
    sh.dim_h(*V.P(lz.x0, lz.y0), *V.P(lz.x1, lz.y0), yl, "%s max" % n(lz.w), fs=6.5,
             text_at=(V.P(-lz.w / 4.0, 0)[0], yl + 0.6))
    sh.dim_v(*V.P(lz.x1, lz.y0), *V.P(lz.x1, lz.y1), V.P(lz.x1, 0)[0] + 5.0, "%s max" % n(lz.h), fs=6.5,
             side="right")
    sh.dim_v(*V.P(lz.x0, lz.c[1]), *V.P(lz.x0, g.y0), V.P(lz.x0, 0)[0] - 6.0, n(lz.c[1] - g.y0), fs=6.5)
    sh.T(V.P(lz.x0, 0)[0] - 8.0, V.P(0, lz.c[1])[1] + 0.8, "zone centre", fs=5.6, ha="right", va="bottom",
         color="0.3")
    # orientation mark
    fx, fy = 15.0, top + 9.0
    for a_, b_ in f_mark(0, 0, 7.0):
        sh.L([fx + a_[0], fx + b_[0]], [fy + a_[1], fy + b_[1]], w=THICK, geom=False)
    sh.T(fx + 0.0, fy - 3.4, "TOP", fs=6.5, weight="bold")
    return V


def legend_right(sh, V, G, gd, x, y):
    """short legend for the three right-side leaders (kept outside the plan)"""
    items = [("#2e8b57", "bead zone %s-%s inside the edge (ref.): adhesive bond band, ink must pass the peel test" %
              (n(G.bead_edge), n(G.bead_edge + G.bead_w))),
             ("k", "black print to the edge: setback %s-%s (film boundary %s inside the outline)" % (
                 n(gd["setback"][0]), n(gd["setback"][1]), n(gd["setback_nom"]))),
             ("0.45", "optical bond zone = panel outline %s x %s (ref.): flatness <= %s here" % (
                 n(G.panel.w), n(G.panel.h), n(gd["flat"])))]
    return items


def edge_detail(sh, P, gd, xs0, yf, k):
    """edge profile, 10:1: s = distance from the outline (<0 inside), d = depth from face 1"""
    S = lambda s, d: (xs0 + k * s, yf - k * d)
    gt = gd["glass_t"]
    a = 0.5 * (gd["arris"][0] + gd["arris"][1])
    sL = -6.5
    pts = [(sL, 0), (-a, 0), (0, a), (0, gt - a), (-a, gt), (sL, gt)]
    sh.poly([S(*p) for p in pts], closed=False, fc="#cfe8f3", ec="k", w=THICK)
    sh.L([S(sL, 0)[0], S(sL, gt)[0]], [S(sL, 0)[1], S(sL, gt)[1]], w=XTHIN, c="0.4", geom=False, dashes=(3, 2))
    # ink on face 2 (thickness exaggerated)
    yi = S(0, gt)[1]
    sh.poly([(S(sL, 0)[0], yi), (S(-a, 0)[0], yi), (S(-a, 0)[0], yi - 0.7), (S(sL, 0)[0], yi - 0.7)],
            fc="k", ec="k", w=XTHIN, geom=False)
    # film boundary tick
    xb = S(-gd["setback_nom"], 0)[0]
    sh.L([xb, xb], [yi - 0.7, yi - 6.0], w=XTHIN, c="k", geom=False, dashes=(2, 1.5))
    sh.T(xb + 1.0, yi - 7.8, "film boundary %s (setback %s-%s)" % (n(gd["setback_nom"]), n(gd["setback"][0]),
                                                                    n(gd["setback"][1])), fs=6.0, va="center")
    # labels
    sh.T(S(sL, 0)[0], S(0, 0)[1] + 4.0, "face 1 = FRONT (user side), not printed", fs=6.3)
    sh.arrow(S(-3.0, 0)[0], S(0, 0)[1] + 0.3, -math.pi / 2)
    sh.L([S(-3.0, 0)[0], S(-3.0, 0)[0]], [S(0, 0)[1] + 0.3 + 2.2, S(0, 0)[1] + 3.2], w=XTHIN, geom=False)
    sh.T(S(sL, 0)[0], yi - 4.2, "face 2 = PRINTED face (bonded)", fs=6.3)
    sh.T(S(sL, 0)[0], yi - 7.2, "ink %s-%s µm (not to scale)" % (n(gd["ink_t"][0], 0), n(gd["ink_t"][1], 0)),
         fs=6.0)
    sh.T(*S(sL / 2.0 - 0.3, gt / 2.0), "GLASS  t = %s ±%s (default; options in the table)" % (
        n(gt), n(gd["types"]["%.1f" % gt]["thickness_tol_mm"])), fs=6.2, ha="center", va="center", allow_geom=True)
    xr = S(0, 0)[0] + 8.0
    sh.leader(*S(-a / 2.0, a / 2.0), xr, S(0, 0)[1] + 3.0, "arris %s-%s x 45 deg, face 1 and face 2" % (
        n(gd["arris"][0]), n(gd["arris"][1])), fs=6.2, head="arrow")
    sh.leader(*S(0, gt / 2.0), xr, S(0, gt / 2.0)[1], "flat-polished edge (C-edge allowed)", fs=6.2, head="arrow")
    sh.leader(*S(-a / 2.0, gt - a / 2.0), xr, S(0, gt)[1] - 3.0, "no frosted arris: it shows as a white line",
              fs=6.2, head="arrow")
    sh.dim_v(*S(sL, 0), *S(sL, gt), S(sL, 0)[0] - 5.0, "%s" % n(gt), fs=6.5)
    return S


def thickness_table(sh, P, C, gd, x, y):
    std = C("glass_standards")
    enamel = C("enamel_strength")
    rows = [["glass_t (kalınlık)", "type (master)", "strengthening / standard", "ink on face 2", "char. strength",
             "use"]]
    use = {"1.1": "only if the touch test forces it (mechanically marginal, concept 11.7)",
           "2.0": "fallback for touch (GT911 through less glass)",
           "3.0": "DEFAULT (owner to confirm after the touch / 0.5 J tests)",
           "4.0": "valid; worse touch, stronger"}
    for t in gd["allowed"]:
        k = "%.1f" % t
        ty = gd["types"][k]
        if "thermally" in ty["type"]:
            strg = std["thermal"] + "; base " + std["base"]
            ink = ("2K organic (epoxy / PU) screen ink after tempering - PREFERRED; fired enamel only as the "
                   "alternative (strength %s -> about %s MPa)" % (n(gd["ink_strength"][0], 0),
                                                                  n(gd["ink_strength"][1], 0)))
            cs = "%s MPa (%s MPa if enamelled)" % (n(ty["char_strength_MPa"], 0), n(enamel, 0))
            if "CS if" in ty["type"]:
                strg += "; if the supplier cannot temper below 3.2: chemically strengthened, " + std["chemical_sl"]
        else:
            strg = std["chemical_sl"] + ("; or " + std["chemical_as"] if "aluminosilicate" in ty["type"] else "")
            ink = "2K organic ink, cured per ink TDS (no enamel on CS glass)"
            cs = "%s MPa" % n(ty["char_strength_MPa"], 0)
        rows.append(["%s ±%s" % (k, n(ty["thickness_tol_mm"])), ty["type"], strg, ink, cs, use[k]])
    bold = [i + 1 for i, t in enumerate(gd["allowed"]) if abs(t - gd["glass_t"]) < 1e-9]
    return sh.table_wrapped(x, y, [20, 33, 58, 40, 22, 33], rows, fs=5.8, bold_rows=bold)


def notes_text(P, C, G, gd):
    g, w = G.glass, G.window
    cos = C("glass_cosmetic")
    samp = C("glass_sampling")
    inkb = C("ink_black")
    inkt = C("ink_tests")
    en = [
        "VIEW: this drawing and GF_Glass.dxf show the glass seen from the FRONT (face 1, user side). The PRINT is on "
        "FACE 2 (back, bonded face). GF_Glass_Print_1to1.pdf is the print seen from face 2 (mirrored). All four "
        "borders are %s (%s); the logo zone is at the BOTTOM, the orientation mark F at the top left." % (
            n(gd["border"]), P.revision),
        "Glass: %s; thickness and strengthening per the option table (default %s). One thickness lot "
        "per batch." % (C("glass_standards")["base"], n(gd["glass_t"])),
        "Outline %s x %s: ±%s on length and width requested (CNC-ground edge); ±%s acceptable if ±%s cannot be "
        "offered - state which in the quotation (sector ±1 mm NOT acceptable). No holes or notches; all edge work "
        "before strengthening." % (n2(g.w), n2(g.h), n(gd["outline_tol"]), n(gd["outline_fallback"]),
                                   n(gd["outline_tol"])),
        "CORNER RADIUS R%s %s, one-sided (overrides any general or sector tolerance): the corner must not stand "
        "outside an R%s corner template; larger radius accepted, smaller rejected. Reason: with independent outline "
        "and radius tolerances a large glass with a small radius brings the corner closer to the lip than the "
        "sides." % (n(g.R), gd["R_tol_txt"], n(g.R)),
        "Edge: %s (%s)." % (gd["edge_txt"], gd["edge_note"]),
        "Flatness <= %s over the %s x %s optical bond zone, <= %s over the pane (free on a surface plate, feeler)."
        % (n(gd["flat"]), n(gd["flat_zone"][0], 0), n(gd["flat_zone"][1], 0), n(gd["flat_pane"])),
        "Print order: %s. Black: %s." % (gd["layers_txt"], inkb),
        "Window %s x %s ±%s, R%s; window to the glass edges ±%s (borders %s / %s / %s / %s, equal on all four "
        "sides). The window is aligned to the display at bonding, not to the glass edges." % (
            n2(w.w), n2(w.h), n(gd["win_tol"]), n(w.R), n(gd["p2e"]), n(w.x0 - g.x0), n(g.x1 - w.x1),
            n(g.y1 - w.y1), n(w.y0 - g.y0)),
        "Ink: %s. Tests: %s. Supply %d printed coupons per ink lot." % (gd["ink_txt"], inkt, gd["samples"][1]),
        "PRINT RIM AT THE ARRIS: the %s-%s x 45 deg arris on face 2 cannot carry ink. An unprinted rim up to %s wide, "
        "measured from the outline, is allowed at the arris; the black must be continuous on the flat face up to the "
        "arris line. Supplier to confirm print-to-edge capability (setback %s-%s on the flat face) on the first "
        "samples." % (n(gd["arris"][0]), n(gd["arris"][1]), n(gd["rim"]), n(gd["setback"][0]),
                      n(gd["setback"][1])),
        "Logo (layer 1, colour): zone %s x %s max in the bottom border, %s from the window and %s from the glass "
        "edge (master logo_zone); strokes >= %s. Artwork to follow - quote one extra screen." % (
            n(G.logo.w), n(G.logo.h), n(w.y0 - G.logo.y1), n(G.logo.y0 - g.y0), n(gd["stroke_min"])),
        "Face 2 is a bond surface (LOCA and silicone bead): no silicone, release agent, tape or protective film on "
        "face 2. A protective film on face 1 is allowed (removed before bonding).",
        "Cosmetics (%s): window: %s; border: %s; edge: %s." % (cos["view"], cos["window_A"], cos["border_B"],
                                                              cos["edge"]),
        "Inspection: %s." % samp,
        "Quantity %d pcs (%d + %d %% spares); first %d samples for approval. Packing: interleaved (paper / foam), "
        "edges protected, label with thickness, lot and ink lot." % (gd["qty"], gd["ovens"], gd["spare_pct"],
                                                                    gd["samples"][0]),
    ]
    trn = [
        "GÖRÜNÜŞ: Resim ve DXF camı ÖN yüzden (1. yüz, kullanıcı tarafı) gösterir. BASKI 2. YÜZE (iç yüz, "
        "yapıştırılan yüz) yapılır; GF_Glass_Print_1to1.pdf baskıyı 2. yüzden (ayna/ters) gösterir. Dört kenar "
        "boşluğu eşit, %s mm; logo bölgesi ALTTA." % n(gd["border"]),
        "Ölçü %s x %s: boy ve en ±%s mm istenir (CNC taşlanmış kenar); ±%s verilemiyorsa ±%s mm kabul edilir - "
        "teklifte hangisini verdiğinizi belirtiniz (sektör toleransı ±1 mm KABUL EDİLMEZ). Delik ve çentik yok. "
        "Tüm kenar işlemleri temperden önce." % (n2(g.w), n2(g.h), n(gd["outline_tol"]), n(gd["outline_tol"]),
                                                 n(gd["outline_fallback"])),
        "KÖŞE RADYUSU R%s %s mm (tek yönlü, açık tolerans; genel veya sektör toleransının yerine geçer): cam köşesi "
        "R%s köşe şablonunun dışına taşmamalıdır - daha büyük radyus kabul, daha küçük radyus red (köşe, kenarlardan "
        "daha fazla çerçeve dudağına yaklaşmamalıdır)." % (n(g.R), gd["R_tol_txt"], n(g.R)),
        "Kenar: düz rodaj parlak (C rodaj olabilir), iki yüzde %s-%s mm x 45° pah; buzlu (mat) pah görünmemeli."
        % (n(gd["arris"][0]), n(gd["arris"][1])),
        "Kalınlık ve sertleştirme seçenek tablosuna göre: 3,0 ısıl temperli (EN 12150-1, kırılma testi) varsayılan; "
        "2,0 veya 1,1 kimyasal temperli. Her seçenek için ayrı fiyat veriniz.",
        "Düzlemsellik: %s x %s yapıştırma bölgesinde <= %s mm, tüm camda <= %s mm." % (
            n(gd["flat_zone"][0], 0), n(gd["flat_zone"][1], 0), n(gd["flat"]), n(gd["flat_pane"])),
        "Baskı (serigrafi, 2. yüz): önce logo rengi, sonra pencere hariç her yer siyah (RAL 9005 / Pantone Black 6 C, "
        "OD >= 4), toplam %s-%s µm; cam kenarına kadar (kenardan geri çekme %s-%s mm)." % (
            n(gd["ink_t"][0], 0), n(gd["ink_t"][1], 0), n(gd["setback"][0]), n(gd["setback"][1])),
        "Pencere %s x %s ±%s mm, R%s; pencere-kenar toleransı ±%s mm (dört kenarda %s mm)." % (
            n2(w.w), n2(w.h), n(gd["win_tol"]), n(w.R), n(gd["p2e"]), n(gd["border"])),
        "Logo (1. katman, renkli): ayrılmış bölge en fazla %s x %s mm, alt kenar boşluğunda; pencereden %s mm, cam "
        "kenarından %s mm; çizgi >= %s. Logo çizimi ayrıca verilecek - bir ek elek fiyatlayınız." % (
            n(G.logo.w), n(G.logo.h), n(w.y0 - G.logo.y1), n(G.logo.y0 - g.y0), n(gd["stroke_min"])),
        "PAH ÜZERİNDE BASKI: 2. yüzdeki %s-%s mm x 45° pah boya tutmaz; pahta, cam kenarından ölçülen en fazla %s mm "
        "baskısız şerit kabul edilir. Siyah, düz yüzeyde pah çizgisine kadar kesintisiz olmalıdır. Kenara kadar baskı "
        "yeteneğini (düz yüzeyde %s-%s mm geri çekme) ilk numunelerde teyit ediniz." % (
            n(gd["arris"][0]), n(gd["arris"][1]), n(gd["rim"]), n(gd["setback"][0]), n(gd["setback"][1])),
        "Boya: 2K organik (epoksi / PU) serigrafi boyası TERCİH EDİLİR; fırınlanmış seramik (emaye) boya yalnız "
        "alternatiftir (cam dayanımı %s'den yaklaşık %s MPa'ya düşer). Testler: "
        "ISO 2409 çapraz kesim GT0-1 (kuru ve 1 saat kaynar su sonrası); her boya partisi için %d adet baskılı "
        "numune gönderiniz." % (n(gd["ink_strength"][0], 0), n(gd["ink_strength"][1], 0), gd["samples"][1]),
        "2. yüz yapıştırma yüzeyidir: silikon, kalıp ayırıcı, bant veya koruyucu film OLMAYACAK. 1. yüzde koruyucu "
        "film olabilir.",
        "Adet: %d (%d + %%%d yedek); önce %d adet numune onayı. Ambalaj: ara kâğıt/köpük, kenar koruma, etikette "
        "kalınlık, parti ve boya partisi." % (gd["qty"], gd["ovens"], gd["spare_pct"], gd["samples"][0]),
    ]
    return en, [tr(t) for t in trn]


def make_sheet(P, C, G, gd, base):
    sh = Sheet()
    sh.frame()
    V = plan(sh, P, C, G, gd, ox=128.0, oy=170.0)
    sh.T(16.0, 279.0, "COVER GLASS - FRONT VIEW (seen from face 1, the user side)   1 : 1", fs=8.5, weight="bold")
    sh.T(16.0, 274.5, "Print on FACE 2 (back). Grey = black ink seen through the glass; white = clear window.",
         fs=6.5)
    # line legend (no leaders into the plan)
    ly = 270.0
    for (col, t), st in zip(legend_right(sh, V, G, gd, 0, 0), ((0, (2, 1.5)), "-", (0, (8, 1.5, 1.5, 1.5)))):
        sh.L([60.0, 70.0], [ly + 0.8, ly + 0.8], w=THIN, c=col, geom=False, dashes=None) if st == "-" else             sh.ax.plot([60.0, 70.0], [ly + 0.8, ly + 0.8], color=col, lw=lw(THIN), ls=st)
        sh.T(72.0, ly, t, fs=5.9, color=col if col != "k" else "k")
        ly -= 2.9
    # edge detail 10:1
    sh.T(262.0, 279.0, "EDGE PROFILE  10 : 1", fs=8.5, weight="bold")
    edge_detail(sh, P, gd, xs0=338.0, yf=268.0, k=10.0)
    # thickness options
    sh.T(16.0, 93.0, "THICKNESS / STRENGTHENING OPTIONS (not yet decided - quote all)  -  Kalınlık seçenekleri "
                     "(henüz karar verilmedi - hepsine fiyat veriniz)", fs=7.0, weight="bold")
    yt = thickness_table(sh, P, C, gd, 16.0, 91.0)
    # notes
    en, trn = notes_text(P, C, G, gd)
    ye = sh.notes(232.0, 224.0, 87.0, en, fs=5.7, head="NOTES", head_fs=7.2, gap=0.4)
    yr = sh.notes(322.0, 224.0, 88.0, trn, fs=5.7, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.4)
    today = datetime.date.today().isoformat()
    sh.title_block({
        "title": "COVER GLASS, PRINTED - GF",
        "subtitle": "Rev3.0 OVEN CONTROLLER glass front  /  serigrafi baskılı temperli ön cam, %d adet" % gd["qty"],
        "source": "all dimensions from %s; border and g_bend gated by the real-panel fold test GF-D21" % master_ref(P),
        "project": "files: GF_Glass.dxf (front view) + GF_Glass_Print_1to1.pdf (artwork, face 2 view) + this sheet",
        "change": "%s. Glass %s x %s (%s %s x %s), window unchanged, centred; logo zone %s x %s max, centre y %s." % (
            rev_note(P), n2(G.glass.w), n2(G.glass.h), prev_rev(P), n2(gd["glass_old"][1] - gd["glass_old"][0]),
            n2(gd["glass_old"][3] - gd["glass_old"][2]), n(G.logo.w), n(G.logo.h),
            n2(P.val("logo_zone", "logo_centre")[1])),
        "dwg": "GF-D10", "rev": P.revision, "scale": "1:1, 10:1", "date": today, "drawn": "make_glass.py",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(base + ".pdf", base + ".png", dpi=200)
    return issues, en, trn, [round(ye, 1), round(yr, 1), round(yt, 1)]


# ========================================================================================================= artwork
def make_artwork(P, C, G, gd, path_pdf, path_png):
    """1:1 vector artwork seen from the PRINTED face (x = -u): black = ink. A4 landscape."""
    W, H = 297.0, 210.0
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    cx, cy = W / 2.0, H / 2.0 + 4.0
    M = lambda pts: [(cx - u, cy + v) for u, v in pts]          # mirror: seen from face 2
    outer = M(bulge_to_points(gd["outer_print"].bulge_pts(), seg_deg=1.0))
    inner = M(bulge_to_points(G.window.bulge_pts(), seg_deg=5.0))[::-1]
    verts = outer + [outer[0]] + inner + [inner[0]]
    codes = [Path.MOVETO] + [Path.LINETO] * (len(outer) - 1) + [Path.CLOSEPOLY] + \
            [Path.MOVETO] + [Path.LINETO] * (len(inner) - 1) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc="black", ec="none", lw=0))
    gl = M(bulge_to_points(G.glass.bulge_pts(), seg_deg=1.0))
    gl.append(gl[0])
    ax.plot([p[0] for p in gl], [p[1] for p in gl], color="#ff00ff", lw=lw(0.1))
    lz = M(G.logo.boundary(step=1.0))
    lz.append(lz[0])
    ax.plot([p[0] for p in lz], [p[1] for p in lz], color="#00b0f0", lw=lw(0.15), ls=(0, (3, 2)))
    # crop marks
    g = G.glass
    for su in (-1, 1):
        for sv in (-1, 1):
            x, y = cx - su * g.x1, cy + sv * g.y1
            ax.plot([x + su * (-3), x + su * (-8)], [y, y], color="k", lw=lw(0.1))
            ax.plot([x, x], [y + sv * 3, y + sv * 8], color="k", lw=lw(0.1))
    # mirrored orientation mark (outside the glass, at the front-view top-left = here top-right)
    for a, b in f_mark(g.x0 + 12.0, g.y1 + 5.0, F_MARK_H):
        (xa, ya), (xb, yb) = M([a, b])
        ax.plot([xa, xb], [ya, yb], color="#0050a0", lw=lw(0.5))
    # 100 mm scale bar
    ax.plot([20, 120], [12, 12], color="k", lw=lw(0.3))
    for xx in (20, 120):
        ax.plot([xx, xx], [10.5, 13.5], color="k", lw=lw(0.3))
    ax.text(70, 14.0, "100 mm - check after printing at 100 %", fontsize=6, ha="center", color="0.3")
    txt = [
        "GF-D11 PRINT ARTWORK 1:1 - %s - seen from the PRINTED face (face 2): MIRRORED, reads correctly from the "
        "front; %s" % (P.revision, master_ref(P)),
        "BLACK = ink (layer 2, black, printed after the logo colour). Magenta = glass outline (cut line, not "
        "printed). Cyan dashed = logo zone (layer 1, %s x %s max, artwork not released)." % (n(G.logo.w),
                                                                                          n(G.logo.h)),
        "Window %s x %s R%s; black outer edge %s inside the outline (setback %s-%s); glass %s x %s R%s." % (
            n2(G.window.w), n2(G.window.h), n(G.window.R), n(gd["setback_nom"]), n(gd["setback"][0]),
            n(gd["setback"][1]), n2(g.w), n2(g.h), n(g.R)),
        "Baskı 2. yüzden görünüş (AYNA / TERS baskı). Siyah = boya. Ölçek 1:1 - %100 yazdırın.",
    ]
    for i, t in enumerate(txt):
        ax.text(10, H - 8 - i * 4.2, tr(t) if i == 3 else t, fontsize=6.5, color="0.2")
    # label to the left of the mirrored F (the F's bars point to -x on this page)
    ax.text(cx - (g.x0 + 12.0) - 0.6 * F_MARK_H - 2.5, cy + g.y1 + 5 + 0.5 * F_MARK_H,
            "orientation mark (mirrored F) = front-view TOP-LEFT", fontsize=5.5, color="#0050a0", ha="right",
            va="center")
    extra = ["Print rim: on the %s-%s x 45 deg arris of face 2 an unprinted rim up to %s from the outline" % (
                 n(gd["arris"][0]), n(gd["arris"][1]), n(gd["rim"])),
             "is allowed; confirm print-to-edge capability on the first samples.",
             "%s: glass %s x %s (%s %s x %s), equal %s border; logo zone %s x %s max; the black outer" % (
                 P.revision, n2(g.w), n2(g.h), prev_rev(P), n2(gd["glass_old"][1] - gd["glass_old"][0]),
                 n2(gd["glass_old"][3] - gd["glass_old"][2]), n(gd["border"]), n(G.logo.w), n(G.logo.h)),
             "edge follows the glass outline (%s inside); window and its position to the AA unchanged." %
             n(gd["setback_nom"])]
    for i, t in enumerate(extra):
        ax.text(132, 24.0 - i * 3.6, t, fontsize=5.6, color="0.2")
    fig.savefig(path_pdf)
    fig.savefig(path_png, dpi=150)
    plt.close(fig)
    # register the artwork page with the sheet index, so make_all scans its texts as well (it is no Sheet)
    import gf_draft

    class _Art:
        dwg, title, rev, issues = "GF-D11", "PRINT ARTWORK 1:1 (face 2, mirrored)", P.revision, []

        @staticmethod
        def all_text():
            return [t.get_text() for t in ax.texts if t.get_text().strip()]
    gf_draft.ALL_SHEETS.append(_Art)
    return {"page_mm": [W, H], "glass_centre_on_page": [cx, cy], "mirrored": True}


def brand_inventory():
    out = []
    if os.path.isdir(BRAND_DIR):
        from PIL import Image
        for f in sorted(os.listdir(BRAND_DIR)):
            p = os.path.join(BRAND_DIR, f)
            e = {"file": f, "bytes": os.path.getsize(p)}
            if f.lower().endswith(".png"):
                with Image.open(p) as im:
                    e["kind"] = "raster PNG %dx%d %s" % (im.size[0], im.size[1], im.mode)
            elif f.lower().endswith(".html"):
                s = open(p, encoding="utf-8", errors="ignore").read()
                fonts = sorted(set(__import__("re").findall(r"font-family: '([^']+)'", s)))
                e["kind"] = "HTML design export: %d <svg> element(s), live text in fonts %s (not outlined)" % (
                    s.count("<svg"), ", ".join(fonts))
            out.append(e)
    return out


def run(out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    prev = os.path.join(out_dir, "previews")
    os.makedirs(prev, exist_ok=True)
    P, C = Params(), Choices()
    G = Geom(P)
    gd = glass_data(P, C, G)
    base = os.path.join(out_dir, "GF_Glass")
    write_dxf(base + ".dxf", P, C, G, gd)
    issues, en, trn, ylow = make_sheet(P, C, G, gd, base)
    art = make_artwork(P, C, G, gd, os.path.join(out_dir, "GF_Glass_Print_1to1.pdf"),
                       os.path.join(prev, "GF_Glass_Print_1to1_preview.png"))
    return {"files": [base + ".dxf", base + ".pdf", base + ".png", os.path.join(out_dir, "GF_Glass_Print_1to1.pdf")],
            "layout_issues": issues, "params_used": dict(sorted(P.used.items())), "choices_used": C.used,
            "notes_en": en, "notes_tr": trn, "artwork": art, "brand_logo_folder": brand_inventory(),
            "lowest_y": ylow, "print_outer": [gd["outer_print"].x0, gd["outer_print"].x1, gd["outer_print"].y0,
                                              gd["outer_print"].y1, gd["outer_print"].R]}


if __name__ == "__main__":
    r = run()
    print("issues:", len(r["layout_issues"]), r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
