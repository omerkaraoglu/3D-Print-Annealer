"""Appearance sheet for the owner: to-scale colour front view of the glass front in the oven sheet.
Two panels: S4 (hidden weld studs), R4 (four rivets, true head size and position), GF-2.0 equal borders; 3.5:1
zoom of one corner (+ the same corner on black-painted steel). Every outline comes from the master; colours are
indicative.

  <venv>/Scripts/python.exe make_appearance.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Appearance.{png,pdf}
"""
import datetime
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, PathPatch
from matplotlib.path import Path

from gf_common import Params, Choices, Rect, OUT_DIR, n, n2, rev_note, master_ref
from gf_geom import Geom, gap_temperatures
from gf_draft import Sheet, View, THIN, XTHIN, MM_PER_PT, lw

STEEL_LIGHT = np.array([0.72, 0.735, 0.75])
STEEL_BLACK = np.array([0.095, 0.095, 0.10])
C_G1 = np.array([0.035, 0.035, 0.037])        # seat ring seen in the 0.4 slot, in shadow
C_LIP = np.array([0.135, 0.135, 0.14])        # matte black GF-PA
C_LIP_EDGE = np.array([0.20, 0.20, 0.21])     # R0.3 rounded lip edges catch light
C_G2 = np.array([0.018, 0.018, 0.02])         # 4 mm deep slot onto the black land / bead
C_GLASS = np.array([0.045, 0.047, 0.055])     # glossy black border (print behind 3 mm glass)
C_ARRIS = np.array([0.16, 0.165, 0.175])      # polished arris
C_UI_BG = np.array([0.055, 0.075, 0.10])
C_BLACK = np.array([0.0, 0.0, 0.0])


def clip_box(poly, x0, x1, y0, y1):
    """Sutherland-Hodgman clip of a convex polygon (list of (x, y)) by an axis-aligned box"""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def iy(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    pts = [tuple(p) for p in poly]
    pts = clip(pts, lambda p: p[0] >= x0, ix(x0))
    pts = clip(pts, lambda p: p[0] <= x1, ix(x1)) if pts else pts
    pts = clip(pts, lambda p: p[1] >= y0, iy(y0)) if pts else pts
    pts = clip(pts, lambda p: p[1] <= y1, iy(y1)) if pts else pts
    return pts


def cov(sdf, pix):
    return np.clip(0.5 - sdf / pix, 0.0, 1.0)[..., None]


def render(G, P, C, u0, u1, v0, v1, ppm, steel, rivets=False, rivet_d=None, seed=1, shank_d=None):
    """RGB image of the front for the model window u0..u1 x v0..v1 at ppm pixels per mm"""
    nx, ny = int(round((u1 - u0) * ppm)), int(round((v1 - v0) * ppm))
    us = u0 + (np.arange(nx) + 0.5) / ppm
    vs = v1 - (np.arange(ny) + 0.5) / ppm
    U, Vv = np.meshgrid(us, vs)
    pix = 1.0 / ppm
    rng = np.random.default_rng(seed)
    if steel == "brushed":
        row = rng.normal(0, 1, ny)
        row = np.convolve(row, np.ones(3) / 3, mode="same")
        low = np.cumsum(rng.normal(0, 1, nx))
        low = (low - low.mean()) / (low.std() + 1e-9)
        tex = 0.022 * row[:, None] + 0.006 * low[None, :] + 0.006 * rng.normal(0, 1, (ny, nx))
        img = STEEL_LIGHT[None, None, :] + tex[..., None]
        img = img + 0.035 * ((Vv - v0) / (v1 - v0) - 0.5)[..., None]
    else:
        tex = 0.006 * rng.normal(0, 1, (ny, nx))
        img = STEEL_BLACK[None, None, :] + tex[..., None]
        img = img + 0.03 * ((Vv - v0) / (v1 - v0) - 0.5)[..., None]
    s_cut = G.cut.sdf(U, Vv)
    s_lo, s_li = G.lip_out.sdf(U, Vv), G.lip_in.sdf(U, Vv)
    s_g, s_w = G.glass.sdf(U, Vv), G.window.sdf(U, Vv)
    # deburred steel edge (R0.2-0.5): a thin lighter / darker band on the steel just outside the cut
    band = np.clip(1.0 - np.abs(s_cut - 0.18) / 0.18, 0, 1)[..., None]
    light = np.where(Vv < 0, 1.0, -0.6)[..., None]                       # lower edges face the light
    img = img + band * light * (0.10 if steel == "brushed" else 0.06)
    lay = [(s_cut, C_G1), (s_lo, C_LIP), (s_li, C_G2), (s_g, C_GLASS)]
    for s, col in lay:
        a = cov(s, pix)
        img = img * (1 - a) + col[None, None, :] * a
    # rounded lip edges
    e1 = np.clip(1.0 - np.abs(s_lo + 0.15) / 0.15, 0, 1) + np.clip(1.0 - np.abs(s_li - 0.15) / 0.15, 0, 1)
    img = img * (1 - 0.6 * e1[..., None]) + C_LIP_EDGE[None, None, :] * 0.6 * e1[..., None]
    # glass arris
    ar = np.clip(1.0 - np.abs(s_g + 0.2) / 0.2, 0, 1)[..., None] * cov(s_g, pix)
    img = img * (1 - 0.7 * ar) + C_ARRIS[None, None, :] * 0.7 * ar
    # window (UI background drawn later as vector) -> leave black here
    aw = cov(s_w, pix)
    img = img * (1 - aw) + C_BLACK[None, None, :] * aw
    # gloss on the glass: soft diagonal sheen
    ag = cov(s_g, pix)[..., 0]
    t = (U - G.glass.x0) / G.glass.w - (Vv - G.glass.y0) / G.glass.h * 0.6
    sheen = 0.045 * np.exp(-((t - 0.15) / 0.12) ** 2) + 0.018 * (Vv - G.glass.y0) / G.glass.h
    img = img + (sheen * ag * (1 - aw[..., 0]))[..., None]
    if rivets:
        r = rivet_d / 2.0
        for k in ("F1", "F2", "F3", "F4"):
            f = G.F[k]
            du, dv = U - f["u"], Vv - f["v"]
            rr = np.hypot(du, dv)
            sh_ = np.clip(1 - np.hypot(du - 0.5, dv + 0.6) / (r + 0.9), 0, 1) ** 1.5 * 0.35
            img = img * (1 - sh_[..., None])
            a = np.clip(0.5 - (rr - r) / pix, 0, 1)[..., None]
            hl = np.exp(-(((du + 0.35 * r) ** 2 + (dv - 0.35 * r) ** 2) / (0.28 * r) ** 2))
            rim = np.clip((rr / r) ** 6, 0, 1)
            shade = 0.07 + 0.30 * hl - 0.04 * rim
            hole = np.clip(0.5 - (rr - 0.3 * shank_d) / pix, 0, 1)        # mandrel hole about 0.6 x shank
            shade = shade * (1 - hole) + 0.01 * hole
            img = img * (1 - a) + np.stack([shade] * 3, -1) * a
    return np.clip(img, 0, 1), (u0, u1, v0, v1)


def draw_ui(ax, V, G, P, C, clip):
    """dark GUI placeholder in the window (vector), clipped to `clip` (paper path patch)"""
    px = C("display_px")
    aa = G.aa
    pxh, pxv = aa.w / px[0], aa.h / px[1]
    gui = int(re.search(r"outer (\d+) px black", P.item("print", "alignment")["note"]).group(1))
    inner = Rect(aa.x0 + gui * pxh, aa.x1 - gui * pxh, aa.y0 + gui * pxv, aa.y1 - gui * pxv, 0.0)
    arts = []
    q = V.Pa([(inner.x0, inner.y0), (inner.x1, inner.y0), (inner.x1, inner.y1), (inner.x0, inner.y1)])
    arts.append(ax.add_patch(plt.Polygon(q, closed=True, fc=C_UI_BG, ec="none", zorder=5)))
    s = V.s
    X = lambda fx: inner.x0 + fx * inner.w
    Y = lambda fy: inner.y0 + fy * inner.h
    pt = lambda h_mm: h_mm * s / MM_PER_PT / 0.73          # cap height (model mm) -> font size on paper

    def txt(fx, fy, t, h, col, ha="left", weight="normal", va="baseline"):
        x, y = V.P(X(fx), Y(fy))
        arts.append(ax.text(x, y, t, fontsize=pt(h), color=col, ha=ha, va=va, fontweight=weight, zorder=6))

    def box(fx0, fy0, fx1, fy1, col, r=1.2):
        (x0, y0), (x1, y1) = V.P(X(fx0), Y(fy0)), V.P(X(fx1), Y(fy1))
        arts.append(ax.add_patch(FancyBboxPatch((x0 + r * s, y0 + r * s), (x1 - x0) - 2 * r * s,
                                                (y1 - y0) - 2 * r * s, boxstyle="round,pad=%f" % (r * s), fc=col,
                                                ec="none", zorder=6)))
    txt(0.03, 0.90, "DRYING  ·  PETG", 2.6, "#9aa7b4")
    txt(0.97, 0.90, "14:32", 2.6, "#9aa7b4", ha="right")
    box(0.0, 0.855, 1.0, 0.858, "#1f2a36", r=0.0)
    txt(0.04, 0.47, "65.0", 15.0, "#f0a030", weight="bold")
    txt(0.40, 0.66, "°C", 5.0, "#f0a030")
    txt(0.04, 0.36, "target 65 °C   ·   2 h 40 min left", 2.4, "#8796a5")
    box(0.04, 0.27, 0.50, 0.30, "#1f2a36", r=0.6)
    box(0.04, 0.27, 0.33, 0.30, "#2bb3a3", r=0.6)
    # small graph
    (gx0, gy0), (gx1, gy1) = V.P(X(0.58), Y(0.32)), V.P(X(0.96), Y(0.80))
    arts.append(ax.add_patch(Rectangle((gx0, gy0), gx1 - gx0, gy1 - gy0, fc="#0b1016", ec="#1f2a36",
                                       lw=lw(0.1), zorder=6)))
    tt = np.linspace(0, 1, 60)
    yy = 0.15 + 0.7 * (1 - np.exp(-tt * 5)) + 0.02 * np.sin(tt * 30)
    arts.append(ax.plot(gx0 + tt * (gx1 - gx0), gy0 + yy * (gy1 - gy0), color="#2bb3a3", lw=lw(0.25),
                        zorder=7)[0])
    for i, lab in enumerate(("STOP", "PROFILE", "MENU")):
        fx0 = 0.04 + i * 0.32
        box(fx0, 0.05, fx0 + 0.28, 0.19, "#1c2631")
        txt(fx0 + 0.14, 0.10, lab, 2.4, "#c9d3dc", ha="center")
    for a in arts:
        a.set_clip_on(True)
        a.set_clip_path(clip)
    return inner, gui, (pxh, pxv)


def panel(sh, P, C, G, ox, oy, sc, margin, steel, rivets, title, rivet_d=None, seed=1, shank_d=None):
    V = View(sh, ox, oy, sc)
    c = G.cut
    u0, u1, v0, v1 = c.x0 - margin, c.x1 + margin, c.y0 - margin, c.y1 + margin
    img, ext = render(G, P, C, u0, u1, v0, v1, 9.0, steel, rivets, rivet_d, seed, shank_d)
    (x0, y0), (x1, y1) = V.P(u0, v0), V.P(u1, v1)
    sh.ax.imshow(img, extent=(x0, x1, y0, y1), origin="upper", interpolation="bilinear", zorder=1)
    w = G.window
    wp = V.Pa(w.boundary(n_arc=8, step=2.0))
    clip = plt.Polygon(wp, closed=True, transform=sh.ax.transData)
    inner = draw_ui(sh.ax, V, G, P, C, clip)
    lz = V.Pa(G.logo.boundary(step=2.0))
    sh.ax.add_patch(plt.Polygon(lz, closed=True, fc="none", ec="#4a4f57", lw=lw(0.15), ls=(0, (3, 2)), zorder=6))
    xl, yl = V.P(0, G.logo.c[1])
    sh.ax.text(xl, yl, "logo zone (not designed)", fontsize=5.0, color="#5a6068", ha="center", va="center",
               zorder=6)
    sh.L([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], w=XTHIN, c="0.5", geom=False)
    sh.T(x0, y1 + 2.0, title, fs=8.0, weight="bold")
    return V, (x0, x1, y0, y1), inner


def zoom(sh, P, C, G, x0p, y0p, k, size, steel, title, seed=3):
    """k:1 zoom of the front-view top-left corner of the cut-out"""
    c = G.cut
    u0, v1 = c.x0 - 4.0, c.y1 + 4.0
    u1, v0 = u0 + size, v1 - size
    V = View(sh, x0p - k * u0, y0p - k * v0, k)
    img, _ = render(G, P, C, u0, u1, v0, v1, 70.0, steel, False, None, seed)
    (xa, ya), (xb, yb) = V.P(u0, v0), V.P(u1, v1)
    sh.ax.imshow(img, extent=(xa, xb, ya, yb), origin="upper", interpolation="bilinear", zorder=1)
    wp = V.Pa(G.window.boundary(n_arc=8, step=0.5))
    cp = clip_box(list(wp), xa, xb, ya, yb)
    if len(cp) >= 3:
        from matplotlib.transforms import Bbox, TransformedBbox
        clip2 = plt.Polygon(cp, closed=True, transform=sh.ax.transData)
        n_txt = len(sh.ax.texts)
        draw_ui(sh.ax, V, G, P, C, clip2)
        box = TransformedBbox(Bbox([[xa, ya], [xb, yb]]), sh.ax.transData)
        for t in list(sh.ax.texts[n_txt:]):          # text ignores clip paths: drop / box-clip it
            x, y = t.get_position()
            if not (xa <= x <= xb and ya <= y <= yb):
                t.remove()
            else:
                t.set_clip_box(box)
    sh.L([xa, xb, xb, xa, xa], [ya, ya, yb, yb, ya], w=THIN, c="0.3", geom=False)
    sh.T(xa, yb + 2.0, title, fs=7.5, weight="bold")
    return V, (xa, xb, ya, yb), (u0, u1, v0, v1)


def make(out_dir=OUT_DIR):
    P, C = Params(), Choices()
    G = Geom(P)
    sh = Sheet()
    sh.frame(zones=False)
    sc = 2.0 / 3.0
    # GF-1.1 round 3: large-flange rivet head from the master (fasteners.hardware.rivet / sheet_variants.R4)
    rd = P.num("fasteners.hardware", r"head dia ([\d.]+) 'K\d+'", name="rivet")
    rk = __import__("re").search(r"'(K\d+)'", P.text("fasteners.hardware", "rivet")).group(1)
    rsh = P.num("fasteners.hardware", r"dia ([\d.]+) LARGE-FLANGE blind rivet", name="rivet")
    rh = P.num("fasteners.hardware", r"modelled head height ([\d.]+) with an R([\d.]+) edge", 1, name="rivet")
    rer = P.num("fasteners.hardware", r"modelled head height ([\d.]+) with an R([\d.]+) edge", 2, name="rivet")
    head_edge = P.num("sheet_variants.R4.note", r"dia-[\d.]+ head edge ([\d.]+) from the cut-out corner arc")
    # panel margin round the cut-out: the whole head must show (head edge + 0.8)
    F1_ = G.F["F1"]
    margin = math.ceil(max(F1_["u"] - G.cut.x1, F1_["v"] - G.cut.y1) + rd / 2.0 + 0.8)
    proud = (P.num("sheet_variants.R4.value", r"heads ~([\d.]+)-([\d.]+) proud", 1),
             P.num("sheet_variants.R4.value", r"heads ~([\d.]+)-([\d.]+) proud", 2))
    c = G.cut
    pw = (c.w + 2 * margin) * sc
    ph = (c.h + 2 * margin) * sc
    ytop = 270.0
    oy = ytop - ph / 2.0
    ox1 = 18.0 + pw / 2.0
    ox2 = ox1 + pw + 4.0
    V1, b1, inner = panel(sh, P, C, G, ox1, oy, sc, margin, "brushed", False,
                          "1  S4 - hidden weld studs: no fastener visible", seed=1)
    V2, b2, _ = panel(sh, P, C, G, ox2, oy, sc, margin, "brushed", True,
                      "2  R4 - four large-flange blind rivets, black heads dia %s" % ("%g" % rd), rivet_d=rd, seed=2,
                      shank_d=rsh)
    # dims under panel 1 and 2
    yb = b1[2]
    g, w = G.glass, G.window
    X1 = lambda u: V1.P(u, 0)[0]
    Y1 = lambda v: V1.P(0, v)[1]
    sh.dim_h(X1(c.x0), yb, X1(c.x1), yb, yb - 6.0, "visible module (cut-out) %s" % n2(c.w), fs=6.5, gap=0.3)
    sh.dim_h(X1(g.x0), yb, X1(g.x1), yb, yb - 12.0, "glass %s" % n2(g.w), fs=6.5, gap=0.3)
    sh.dim_h(X1(w.x0), yb, X1(w.x1), yb, yb - 18.0, "image (window) %s" % n2(w.w), fs=6.5, gap=0.3)
    sh.dim_v(b1[0], Y1(c.y0), b1[0], Y1(c.y1), b1[0] - 4.0, n2(c.h), fs=6.5, gap=0.3)
    Y2 = lambda v: V2.P(0, v)[1]
    sh.dim_v(b2[1], Y2(w.y0), b2[1], Y2(w.y1), b2[1] + 3.0, "image %s" % n2(w.h), fs=6.0, side="right", gap=0.3)
    F1, F2, F4 = G.F["F1"], G.F["F2"], G.F["F4"]
    sh.dim_h(V2.P(F2["u"], 0)[0], yb, V2.P(F1["u"], 0)[0], yb, yb - 6.0, "rivets %s x %s" % (
        n2(abs(F1["u"] - F2["u"])), n2(abs(F1["v"] - F4["v"]))), fs=6.5)
    sh.T(b2[0], yb - 13.0, "heads dia %s '%s', %s-%s proud of the steel (not flush); head edge %s from the cut-out "
                           "corner arc" % (("%g" % rd), rk, n(proud[0]), n(proud[1]), n(head_edge)), fs=6.2)
    bds = (g.y1 - w.y1, w.x0 - g.x0, g.x1 - w.x1, w.y0 - g.y0)
    assert max(bds) - min(bds) < 1e-6, bds                      # GF-2.0: one border on all four sides
    sh.T(b2[0], yb - 17.0, "border %s on all four sides (window centred in the glass); logo zone %s x %s max in "
                           "the bottom border," % (n(bds[0]), n(G.logo.w), n(G.logo.h)), fs=6.2)
    sh.T(b2[0], yb - 21.0, "%s from the window and %s from the glass edge (master logo_zone)" % (
        n(G.window.y0 - G.logo.y1), n(G.logo.y0 - G.glass.y0)), fs=6.2)
    # zooms (right column)
    k = 3.5                           # the GF-2.x panels are wide -> 3.5:1 keeps the zoom inside the frame
    size = 20.0                       # zoom window (mm of product); 3.5:1 -> 70 mm on paper (GF-2.1: panels 1 mm wider)
    zx = ox2 + pw / 2.0 + 7.0         # 7 mm right of panel 2: room for its 'image' dimension
    assert zx + size * k <= sh.W - sh.m - 2.0, ("zoom column runs into the frame line", zx, size * k)
    zy = ytop - size * k
    Vz, bz, win = zoom(sh, P, C, G, zx, zy, k, size, "brushed", "3  corner %s : 1 (light steel)" % n(k), seed=3)
    # labels inside the zoom: points on the left edge bands, horizontal leaders to texts on the glass border
    cl = "#ffbf5e"
    c0 = G.cut
    feats = [(c0.x0 - 2.0, "steel (sheet front)"),
             ((c0.x0 + G.lip_out.x0) / 2.0, "%s slot onto the seat ring (g1)" % n(G.g1)),
             ((G.lip_out.x0 + G.lip_in.x0) / 2.0, "%s matte black lip" % n(G.lip_w)),
             ((G.lip_in.x0 + G.glass.x0) / 2.0, "%s slot, black on black (g2)" % n(G.g2)),
             (G.glass.x0 + 2.5, "glossy black glass border")]
    ut = G.glass.x0 + 4.5
    for i, (u, t) in enumerate(feats):
        v = c0.y1 - 9.0 - 1.5 * i
        px, py = Vz.P(u, v)
        tx, _ = Vz.P(ut, v)
        sh.L([px, tx - 0.8], [py, py], w=XTHIN, c=cl, geom=False)
        sh.ax.add_patch(plt.Circle((px, py), 0.4, fc=cl, ec="none", zorder=8))
        sh.T(tx, py, t, fs=5.6, va="center", color=cl, allow_geom=True)
    Vz2, bz2, _ = zoom(sh, P, C, G, zx, zy - size * k - 22.0, k, size, "black",
                       "4  same corner on black-painted steel", seed=4)
    # notes
    gt_ = gap_temperatures(P)                     # GF-2.0 verified values (master gaps notes, 2026-11-16)
    rss = P.get("checks")["flush_glass_vs_sheet_RSS"]
    notes = [
        "True proportions from the master file (panels %s, zooms %s:1 when printed on A3 at 100 %%). Colours, gloss "
        "and the UI are indicative." % ("1 : 1.5", n(k)),
        "Gaps at 20 C: %s / %s lip / %s at the sides, about %s / %s at the corners (%s corner radii). They breathe "
        "with temperature (nominal sides, 50 / 70 ppm, master values verified at %s): glass-lip -20 C %s / %s, "
        "+70 C %s / %s; lip-steel hot (frame +70 C, sheet +50 C) %s / %s, -20 C %s / %s. At the tolerance limits "
        "with 70 ppm they can just touch (glass-lip cold, lip-steel hot) - harmless." % (
            n(G.g1), n(G.lip_w), n(G.g2), n(round(G.corner_gap(G.lip_out, G.cut), 2), 2),
            n(round(G.corner_gap(G.glass, G.lip_in), 2), 2), P.revision, P.revision,
            n2(gt_["g2_cold_50"]), n2(gt_["g2_cold_70"]), n2(gt_["g2_hot_50"]), n2(gt_["g2_hot_70"]),
            n2(gt_["g1_hot_50"]), n2(gt_["g1_hot_70"]), n2(gt_["g1_cold_50"]), n2(gt_["g1_cold_70"])),
        "All front faces in one plane within ±%s (RSS) - but the lip (matte black PA) and the glass (glossy black) "
        "read as two different blacks: a thin dark frame line round the glass." % n(round(rss, 2)),
        "Window = active area - %s per side; the GUI keeps the outer %d px black, so a %s mm black band shows "
        "inside the window edge. Display off: the window reads grey-black against the border (about 13 %% vs 4-6 %% "
        "reflectance, R1 sec. 3.5)." % (n(P.d("print_inset")), inner[1], n(inner[1] * inner[2][0] - P.d("print_inset"),
                                                                            2)),
        "R4: four black large-flange heads dia %s ('%s', low: modelled %s high with an R%s edge) on the steel, %s-%s "
        "proud, not flush; S4 shows no fastener (CD stud welds can leave a faint witness mark on %s sheet - check "
        "the coupon)." % (("%g" % rd), rk, n(rh), n(rer), n(proud[0]), n(proud[1]), n(P.d("t_sheet"))),
        "%s: the border is %s on all four sides - the window sits in the middle of the glass and of the cut-out "
        "(%s x %s visible module, %s x %s glass); the logo zone (dashed) is in the bottom border." % (
            P.revision, n(bds[0]), n2(c.w), n2(c.h), n2(g.w), n2(g.h)),
    ]
    yN = sh.notes(14.0, 88.0, 218.0, notes, fs=6.2, head="WHAT THE USER SEES - honest notes", head_fs=7.5, gap=0.5)
    sh.title_block({
        "title": "APPEARANCE - GLASS FRONT IN THE OVEN SHEET",
        "subtitle": "for the owner: S4 hidden studs vs R4 rivets, corner detail; colour front view, to scale",
        "source": "outlines and rivet head from %s" % master_ref(P),
        "project": "files: GF_Appearance.png (300 dpi) + GF_Appearance.pdf",
        "change": "%s. Front views S4 / R4 with the equal border, visible module %s x %s; corner zoom %s:1." % (
            rev_note(P), n2(c.w), n2(c.h), n(k)),
        "dwg": "GF-D40", "rev": P.revision, "scale": "1:1.5, %s:1" % n(k), "date": datetime.date.today().isoformat(),
        "drawn": "make_appearance.py",
    }, w=160.0, h=40.0)
    issues = sh.check_layout()
    base = os.path.join(out_dir, "GF_Appearance")
    sh.save(base + ".pdf", base + ".png", dpi=300)
    return {"files": [base + ".png", base + ".pdf"], "layout_issues": issues, "params_used": dict(sorted(P.used.items())),
            "choices_used": C.used, "notes": notes, "lowest_y": round(yN, 1)}


if __name__ == "__main__":
    r = make()
    print("issues:", len(r["layout_issues"]), r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
