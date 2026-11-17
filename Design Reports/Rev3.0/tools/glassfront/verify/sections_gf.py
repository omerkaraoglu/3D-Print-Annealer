"""Dimensioned section plots from REAL STEP sections (matplotlib). Every dimension is measured on the STEP with the
exact line probe in the section plane (snapped to the nearest face crossing), not typed from the params; the
independently built assembly parts (glass, bead, oven sheet, VHB, LOCA, panel envelope, Formex, PCB, studs, tails)
are sectioned by the same plane and drawn in colour.

  <venv>\\Scripts\\python.exe sections_gf.py [--frame f.step] [--img dir]

Section_side_left_y60, Section_top_x80, Section_chin_x103.85, Section_F1_slot_axis, Section_F8_tube_y82.085,
Plan_lip_Z-14.1, Plan_corner_cells_Z-6.0 -> Mechanical/Rev3.0_GlassFront/renders/verify/
"""
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import cadquery as cq

import vcommon as C

FC = {"frame": "#5a5f68", "glass": "#7fb3d5", "bead": "#e74c3c", "sheet": "#b0b6bd", "tape": "#f4c542", "loca": "#aee3f5",
      "panel": "#9aa0a6", "formex": "#efe6b0", "pcb": "#2e8b57", "hw": "#c8b98a", "tail": "#e08e0b", "board": "#444444"}


class Plane:
    """a vertical section plane and its 2D coordinates (h, Z)"""

    def __init__(self, kind, val=None, origin=None, axis=None):
        self.kind, self.val, self.origin, self.axis = kind, val, origin, axis

    def section(self, shape):
        if self.kind == "x":
            return C.plane_section(shape, "x", self.val)
        if self.kind == "y":
            return C.plane_section(shape, "y", -self.val)
        x, y = self.origin
        ux, uy = self.axis
        return C.general_section(shape, (x, -y, 0.0), (uy, ux, 0.0))

    def h(self, P3):
        """model points (N x 3) -> h"""
        if self.kind == "x":
            return -P3[:, 1]
        if self.kind == "y":
            return P3[:, 0]
        x, y = self.origin
        return (P3[:, 0] - x) * self.axis[0] + (-P3[:, 1] - y) * self.axis[1]

    def model_point(self, h, z):
        if self.kind == "x":
            return (self.val, -h, z)
        if self.kind == "y":
            return (h, -self.val, z)
        x, y = self.origin
        return (x + h * self.axis[0], -(y + h * self.axis[1]), z)

    def hdir(self):
        if self.kind == "x":
            return (0.0, -1.0, 0.0)
        if self.kind == "y":
            return (1.0, 0.0, 0.0)
        return (self.axis[0], -self.axis[1], 0.0)


def polys(plane, shape):
    sec = plane.section(shape)
    out = []
    if sec is None:
        return out
    for f in sec.Faces():
        loops = [np.column_stack([plane.h(l), l[:, 2]]) for l in C.face_loops_3d(f, 0.002)]
        out.append(loops)
    return out


def draw(ax, plist, fc, ec="k", lw=0.6, alpha=1.0, z=2, hatch=None):
    for loops in plist:
        outer = loops[0]
        p = MPoly(outer, closed=True, fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z, hatch=hatch)
        ax.add_patch(p)
        for hole in loops[1:]:
            ax.add_patch(MPoly(hole, closed=True, fc="white", ec=ec, lw=lw, zorder=z + 0.1))


class Meas:
    """exact probe boundaries in the plane"""

    def __init__(self, plane, probe):
        self.pl, self.P = plane, probe

    def hb(self, z):
        p0 = self.pl.model_point(0.0, z)
        d = self.pl.hdir()
        iv = self.P.intervals(p0, d, -400, 400)
        return sorted(set([round(a, 5) for a, b in iv] + [round(b, 5) for a, b in iv]))

    def vb(self, h):
        p = self.pl.model_point(h, 0.0)
        iv = self.P.intervals((p[0], p[1], 0.0), (0, 0, 1), -100, 100)
        return sorted(set([round(a, 5) for a, b in iv] + [round(b, 5) for a, b in iv]))

    @staticmethod
    def snap(vals, guess, tol=0.7):
        if not vals:
            return None
        v = min(vals, key=lambda q: abs(q - guess))
        return v if abs(v - guess) <= tol else None


def hdim(ax, M, z, a, b, zd, label, fixed=(False, False), col="#c0392b", fs=10, tol=0.7):
    hb = M.hb(z)
    ha = a if fixed[0] else Meas.snap(hb, a, tol)
    hbv = b if fixed[1] else Meas.snap(hb, b, tol)
    if ha is None or hbv is None:
        return None
    ax.annotate("", xy=(ha, zd), xytext=(hbv, zd), arrowprops=dict(arrowstyle="<->", color=col, lw=0.9, shrinkA=0, shrinkB=0), zorder=9)
    for hh in (ha, hbv):
        ax.plot([hh, hh], [z, zd], color=col, lw=0.4, ls=":", zorder=8)
    ax.text((ha + hbv) / 2, zd, "%s %.3f" % (label, abs(hbv - ha)), ha="center", va="bottom", fontsize=fs, color=col, zorder=10,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    return abs(hbv - ha)


def vdim(ax, M, h, a, b, hd, label, col="#1f4e9c", fs=10, side="right", tol=0.7):
    vb = M.vb(h)
    za, zb = Meas.snap(vb, a, tol), Meas.snap(vb, b, tol)
    if za is None or zb is None:
        return None
    ax.annotate("", xy=(hd, za), xytext=(hd, zb), arrowprops=dict(arrowstyle="<->", color=col, lw=0.9, shrinkA=0, shrinkB=0), zorder=9)
    for zz in (za, zb):
        ax.plot([h, hd], [zz, zz], color=col, lw=0.4, ls=":", zorder=8)
    ax.text(hd + (0.12 if side == "right" else -0.12), (za + zb) / 2, "%s %.3f" % (label, abs(zb - za)), ha="left" if side == "right" else "right",
            va="center", fontsize=fs, color=col, rotation=0, zorder=10, bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    return abs(zb - za)


def hdim2(ax, M, A, B, zd, label, col="#c0392b", fs=10, tol=0.7):
    """horizontal dimension between point A = (z_a, h_a guess[, fixed]) and B, each snapped at its own height"""
    def end(P):
        z, h = P[0], P[1]
        if len(P) > 2 and P[2]:
            return h, z
        v = Meas.snap(M.hb(z), h, tol)
        return v, z
    (ha, za), (hb, zb) = end(A), end(B)
    if ha is None or hb is None:
        return None
    ax.annotate("", xy=(ha, zd), xytext=(hb, zd), arrowprops=dict(arrowstyle="<->", color=col, lw=0.9, shrinkA=0, shrinkB=0), zorder=9)
    ax.plot([ha, ha], [za, zd], color=col, lw=0.4, ls=":", zorder=8)
    ax.plot([hb, hb], [zb, zd], color=col, lw=0.4, ls=":", zorder=8)
    ax.text((ha + hb) / 2, zd, "%s %.3f" % (label, abs(hb - ha)), ha="center", va="bottom", fontsize=fs, color=col, zorder=10,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    return abs(hb - ha)


def vdim2(ax, M, A, B, hd, label, col="#1f4e9c", fs=10, side="right", tol=0.7):
    """vertical dimension between A = (h_a, z_a guess) and B, each snapped on its own vertical line"""
    za = Meas.snap(M.vb(A[0]), A[1], tol)
    zb = Meas.snap(M.vb(B[0]), B[1], tol)
    if za is None or zb is None:
        return None
    ax.annotate("", xy=(hd, za), xytext=(hd, zb), arrowprops=dict(arrowstyle="<->", color=col, lw=0.9, shrinkA=0, shrinkB=0), zorder=9)
    ax.plot([A[0], hd], [za, za], color=col, lw=0.4, ls=":", zorder=8)
    ax.plot([B[0], hd], [zb, zb], color=col, lw=0.4, ls=":", zorder=8)
    ax.text(hd + (0.08 if side == "right" else -0.08), (za + zb) / 2, "%s %.3f" % (label, abs(zb - za)),
            ha="left" if side == "right" else "right", va="center", fontsize=fs, color=col, zorder=10,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    return abs(zb - za)


def level_lines(ax, G, xlim, keys):
    for k in keys:
        z = G.L[k]
        ax.axhline(z, color="#999999", lw=0.35, ls="--", zorder=1)
        ax.text(xlim[0] + 0.1, z + 0.04, "%s %.2f" % (k, z), fontsize=7, va="bottom", ha="left", color="#555555", zorder=11,
                bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.75))


def assembly_polys(plane, A, hw, extras):
    out = []
    for key, col, alpha in (("sheet", FC["sheet"], 0.9), ("glass", FC["glass"], 0.75), ("loca", FC["loca"], 0.9),
                            ("bead", FC["bead"], 0.9), ("formex", FC["formex"], 0.95), ("panel_env", FC["panel"], 0.45),
                            ("tape_top", FC["tape"], 0.95), ("tape_bottom", FC["tape"], 0.95), ("tape_left", FC["tape"], 0.95),
                            ("tape_right", FC["tape"], 0.95)):
        out.append((polys(plane, A[key]), col, alpha, key))
    for k, s in hw.items():
        out.append((polys(plane, s), FC["hw"], 0.95, k))
    for k, s, col in extras:
        out.append((polys(plane, s), col, 0.85, k))
    return out


def setup(title, xlim, ylim, figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.25, color="#dddddd", zorder=0)
    ax.set_title(title, fontsize=12)
    return fig, ax


def legend(ax, extra=(), tape=True, loc="lower left", anchor=None):
    from matplotlib.patches import Patch
    items = [Patch(fc=FC["frame"], label="frame (STEP section)"), Patch(fc=FC["glass"], label="glass (params)"),
             Patch(fc=FC["bead"], label="bead"), Patch(fc=FC["sheet"], label="oven sheet")] + (
            [Patch(fc=FC["tape"], label="VHB 12 x 1.0")] if tape else []) + [
             Patch(fc=FC["panel"], alpha=0.5, label="panel envelope"), Patch(fc=FC["formex"], label="Formex"),
             Patch(fc=FC["hw"], label="stud / washer / nut" if tape else "stud / shim / washer / nut")] + list(extra)
    ax.legend(handles=items, loc=loc, bbox_to_anchor=anchor, fontsize=8, framealpha=0.9, ncol=2)


def save(fig, path):
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def edge_section(ctx, A, hw, board, name, plane, xlim, ylim, s_of_h, figsize, title, extra_dims=None, tails=None,
                 land_s=-8.9, tape=True, legend_kw=None):
    """generic edge profile with a zoom panel on the lip: s_of_h converts s (outward from the glass edge) to h"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    P = C.Probe(fr)
    M = Meas(plane, P)
    S = s_of_h
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.6, 1.0], wspace=0.12)
    ax = fig.add_subplot(gs[0]); az = fig.add_subplot(gs[1])
    zx = sorted((S(-1.6), S(3.6)))
    for a_, xl, yl in ((ax, xlim, ylim), (az, zx, (-15.6, -11.8))):
        a_.set_xlim(*xl); a_.set_ylim(*yl); a_.set_aspect("equal"); a_.grid(True, lw=0.25, color="#dddddd", zorder=0)
    ax.set_title(title, fontsize=11)
    az.set_title("zoom: lip, gaps, seat ring (measured on the STEP)", fontsize=10)
    extras = [("pcb", board["PCB"], FC["pcb"])] if board.get("PCB") is not None else []
    for k, s in (tails or []):
        extras.append((k, s, FC["tail"]))
    apolys = assembly_polys(plane, A, hw, extras)
    fpolys = polys(plane, fr)
    for a_ in (ax, az):
        for pl_, col, alpha, key in apolys:
            if key.startswith("tape") and not tape:     # S8 sections: no VHB (foam gasket between the spacers)
                continue
            draw(a_, pl_, col, ec="#333333", lw=0.4, alpha=alpha, z=3 if key != "panel_env" else 1.5)
        draw(a_, fpolys, FC["frame"], ec="k", lw=0.7, z=2)
    level_lines(ax, G, xlim, ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_FLANGE_BACK", "Z_LANDPLATE_BACK",
                              "Z_TUBE_TOP", "Z_PANEL_BACK", "Z_SEAT", "Z_SHELF_BACK", "Z_PCB"])
    zg, zsb, zff, zl, zfb, zlb = L["Z_GLASS_FRONT"], L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"], L["Z_LAND"], L["Z_FLANGE_BACK"], L["Z_LANDPLATE_BACK"]
    d = {}
    # zoom panel: lip and gaps 0.31 behind the flush plane (below the R0.3 rounds), root, seat ring
    d["g2 (Z+0.31)"] = hdim2(az, M, (zg + 0.31, S(0.0), True), (zg + 0.31, S(0.4)), zg - 0.25, "g2", fs=9)
    d["g1 (Z+0.31)"] = hdim2(az, M, (zg + 0.31, S(1.4)), (zg + 0.31, S(1.8), True), zg - 0.25, "g1", fs=9)
    d["lip at Z+0.31"] = hdim2(az, M, (zg + 0.31, S(0.4)), (zg + 0.31, S(1.4)), zg - 0.62, "lip", fs=9)
    d["lip root (Z_SHEET_BACK-0.22)"] = hdim2(az, M, (zsb - 0.22, S(0.4)), (zsb - 0.22, S(1.4)), zsb + 0.12, "lip root", fs=9)
    d["seat ring (lip root -> ring edge)"] = hdim2(az, M, (zsb - 0.22, S(1.4)), (zsb + 0.5, S(2.9)), zsb + 0.55, "seat ring", fs=9)
    d["lip height"] = vdim2(az, M, (S(0.9), zg), (S(2.2), zsb), S(2.2) if S(2.2) > S(0.9) else S(2.2), "lip h", fs=9,
                            side="right" if S(2.2) > S(0.9) else "left")
    d["seat ring -> flange front"] = vdim2(az, M, (S(2.2), zsb), (S(3.4), zff), S(3.4), "ring step", fs=9,
                                           side="right" if S(3.4) > S(2.2) else "left")
    # main panel
    d["recess depth (lip top -> land)"] = vdim2(ax, M, (S(0.9), zg), (S(-2.0), zl), S(-1.2), "recess", side="left" if S(-1.2) < S(0.9) else "right")
    d["land (pocket face -> recess wall)"] = hdim2(ax, M, (zl + 0.02, S(land_s)), (zl - 0.6, S(0.35)), zl - 0.75, "land", tol=1.2)
    d["flange edge s at Z_FLANGE_FRONT+0.05"] = hdim2(ax, M, (zff + 0.05, S(0.0), True), (zff + 0.05, S(21.0)), zff + 0.15, "glass edge -> flange edge")
    d["flange t"] = vdim2(ax, M, (S(10.0), zff), (S(10.0), zfb), S(10.0), "flange t")
    d["land plate t"] = vdim2(ax, M, (S(-2.0), zl), (S(-2.0), zlb), S(-2.0), "land plate")
    d["step wall height (seat ring -> step-wall back)"] = vdim2(ax, M, (S(2.0), zsb), (S(2.0), zlb), S(2.3), "step wall", fs=9,
                                                             side="right" if S(2.3) > S(2.0) else "left")
    if extra_dims:
        extra_dims(ax, M, d)
    legend(ax, tape=tape, **(legend_kw or {}))
    return fig, ax, d


def bridge_section(ctx, A, hw, board, tails, x, fname, title, fit=None):
    """GF-2.0 bottom section at x (h = y abs): glass, bead, panel envelope, Formex, sheet, VHB, PCB, J10/J11, the tails built
    here, the frame; dimensions measured on the STEP (bend gap, break, nose, land plate, flange plate, bottom wall)"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    gy1 = G.GLASS[3]
    P = C.Probe(fr)
    pl = Plane("x", x)
    M = Meas(pl, P)
    fig = plt.figure(figsize=(26, 11))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.3, 1.0], wspace=0.10)
    ax = fig.add_subplot(gs[0]); az = fig.add_subplot(gs[1])
    for a_, xl, yl in ((ax, (112.0, 152.5), (-16.5, 5.5)), (az, (118.0, 126.0), (-11.8, -4.4))):
        a_.set_xlim(*xl); a_.set_ylim(*yl); a_.set_aspect("equal"); a_.grid(True, lw=0.25, color="#dddddd", zorder=0)
    ax.set_title(title, fontsize=11)
    az.set_title("zoom: bend gap, 0.3 x 45 break, R%.1f nose, tails (built here)" % G.bend_nose_R, fontsize=10)
    extras = [("pcb", board["PCB"], FC["pcb"])] if board.get("PCB") is not None else []
    for k, s in board.items():
        if k != "PCB" and s is not None:
            extras.append((k, s, FC["board"]))
    for k, s in tails:
        extras.append((k, s, FC["tail"]))
    apolys = assembly_polys(pl, A, hw, extras)
    fpolys = polys(pl, fr)
    for a_ in (ax, az):
        for pl_, col, alpha, key in apolys:
            draw(a_, pl_, col, ec="#333333", lw=0.4, alpha=alpha, z=3 if key != "panel_env" else 1.5)
        draw(a_, fpolys, FC["frame"], ec="k", lw=0.7, z=2)
    level_lines(ax, G, (112.0, 152.5), ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_FLANGE_BACK", "Z_LANDPLATE_BACK",
                                        "Z_PANEL_BACK", "Z_SEAT", "Z_SHELF_BACK", "Z_PCB", "Z_TAIL_LEG"])
    zl, zlb, zff, zfb = L["Z_LAND"], L["Z_LANDPLATE_BACK"], L["Z_FLANGE_FRONT"], L["Z_FLANGE_BACK"]
    d = {}
    on_bridge = G.TAIL[0] < x < G.TAIL[1] and abs(x - G.div_x) > 2.0
    if on_bridge or abs(x - G.div_x) <= 2.0:
        d["bend gap: panel edge -> pocket face at Z_LAND + 0.5"] = hdim2(az, M, (zl + 0.5, G.PANEL[3], True), (zl + 0.5, G.BRIDGE[2] + 0.01), zl - 0.35, "g_bend", fs=9)
        d["land plate t"] = vdim2(ax, M, (125.6, zl), (125.6, zlb), 125.6, "land plate", fs=9)
        az.text(118.2, -5.0, "pocket face y %.2f at Z_LAND (1 deg, wider to the back); 0.3 x 45 break; R%.1f nose tangent to the face and the "
                "land-plate back Z %.2f\n(all measured: spec rows 'bridge / slot')" % (G.BRIDGE[2], G.bend_nose_R, zlb), fontsize=8, va="top",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999999"), zorder=12)
    d["flange plate t (y 140)"] = vdim2(ax, M, (140.0, zff), (140.0, L.get("Z_FLOOR_LOW", zfb)), 140.0, "flange plate", fs=9)
    d["bottom wall at Z -3"] = hdim2(ax, M, (-3.0, 147.75), (-3.0, 150.1), -2.4, "bottom wall", fs=9)
    d["bottom wall height (flange front -> trough top)"] = vdim2(ax, M, (149.0, zff), (149.0, L["Z_TROUGH_TOP"]), 151.6, "wall", fs=9)
    d["glass edge -> flange edge (bottom)"] = hdim2(ax, M, (zff + 0.05, gy1, True), (zff + 0.05, 150.2), zff - 0.7, "glass edge -> flange edge", fs=9)
    d["land (pocket face -> recess wall) at Z_LAND - 0.6"] = hdim2(ax, M, (zl + 0.6, G.BRIDGE[2] + 0.01), (zl - 0.6, gy1 + 0.4), zl - 1.4, "land", fs=9, tol=1.0)
    if fit and fit.get("tails"):
        nom = fit["tails"]["cases"]["nominal (params polylines)"]
        txt = []
        for n in ("TFT", "CTP"):
            fb = nom[n]["frame_by_class"]
            txt.append("%s: nose %.3f, pocket face %.3f, break %.3f, land-plate back %.3f, rib %.3f, bottom wall %.3f, glass print %.3f, PCB body %.3f" % (
                n, fb["bridge nose R1.5"]["min"], fb["bridge pocket face (+ rib front)"]["min"], fb["land break 0.3 x 45"]["min"],
                fb["land-plate back (bridge floor, Z -7.92)"]["min"], fb["divider rib (sides, top, roots)"]["min"],
                fb["pocket bottom face y 147.7 / bottom wall"]["min"], nom[n]["assembly"]["glass (printed back face = glass print)"]["min"],
                nom[n]["pcb_body"]["min"]))
        ax.text(112.5, 4.6, "3D minimum clearances of the tails (whole length, fit check):\n" + "\n".join(txt), fontsize=8.5, va="top",
                bbox=dict(boxstyle="round,pad=0.25", fc="#fff4e0", ec="#e0a050"), zorder=12)
    from matplotlib.patches import Patch
    items = [Patch(fc=FC["frame"], label="frame (STEP section)"), Patch(fc=FC["glass"], label="glass (params)"), Patch(fc=FC["bead"], label="bead"),
             Patch(fc=FC["sheet"], label="oven sheet"), Patch(fc=FC["tape"], label="VHB 12 x 1.0"), Patch(fc=FC["panel"], alpha=0.5, label="panel envelope"),
             Patch(fc=FC["formex"], label="Formex"), Patch(fc=FC["tail"], label="FPC tail (GF-2.0 route, built here)"),
             Patch(fc=FC["pcb"], label="PCB"), Patch(fc=FC["board"], label="J10 / J11 models")]
    ax.legend(handles=items, loc="upper left", bbox_to_anchor=(0.645, 0.80), fontsize=8, framealpha=0.95, ncol=1)
    return save(fig, os.path.join(ctx.imgdir, fname)), d


def plan_bottom(ctx, A, tails_by_name, fit=None):
    """plan of the frame at Z -9.0 (above the tail-pocket floor) with the glass, panel, bend-gap slot, bridge face and the
    tails' plan footprints (built here); and a whole-frame plan at the flange front with the flange outline"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    fig, axs = plt.subplots(2, 1, figsize=(22, 24), gridspec_kw={"height_ratios": [1.6, 1.0]})
    ax = axs[0]
    for z, fc, lab in ((L["Z_FLANGE_FRONT"] + 0.01, "#c9ccd1", "Z %.2f (flange front)" % (L["Z_FLANGE_FRONT"] + 0.01)),
                       (-9.0, FC["frame"], "Z -9.00 (bridge / tail pocket)")):
        for l in C.plan_loops(fr, z):
            ax.add_patch(MPoly(l["pts"], closed=True, fc=fc if l["outer"] else "white", ec="k", lw=0.5,
                               zorder=(2 if z < -10 else 3) if l["outer"] else (2.5 if z < -10 else 3.5), alpha=0.9))
    gp = C.rrect_wire_pts(*G.GLASS, n=40)
    ax.plot(np.append(gp[:, 0], gp[0, 0]), np.append(gp[:, 1], gp[0, 1]), color="#1f4e79", lw=1.4, label="glass outline", zorder=7)
    px0, px1, py0, py1 = G.PANEL
    ax.plot([px0, px1, px1, px0, px0], [py0, py0, py1, py1, py0], color="#d35400", lw=1.2, ls="--", label="panel outline", zorder=7)
    sx0, sx1, sy0, sy1, _ = G.SLOT
    ax.add_patch(MPoly([(sx0, sy0), (sx1, sy0), (sx1, sy1), (sx0, sy1)], closed=True, fc="none", ec="#c0392b", lw=1.2, ls="-", zorder=6,
                       label="bend-gap slot (params)"))
    for n, sol in tails_by_name.items():
        for lab, s, seg in sol:
            bb = s.BoundingBox()
            ax.add_patch(MPoly([(bb.xmin, -bb.ymax), (bb.xmax, -bb.ymax), (bb.xmax, -bb.ymin), (bb.xmin, -bb.ymin)], closed=True,
                               fc=FC["tail"], ec="#7a3e00", lw=0.6, alpha=0.35, zorder=5))
        ax.text(np.mean([s.BoundingBox().xmin for _, s, _ in sol]), 135.0, "%s tail" % n, fontsize=11, color="#7a3e00", zorder=7)
    for n in G.fast:
        x, y = G.fxy(n)
        ax.plot(x, y, "k+", ms=12, zorder=8)
        ax.text(x + 1.2, y - 1.2, n, fontsize=10, zorder=8)
    fx0, fx1, fy0, fy1, _ = G.FLANGE
    ax.set_xlim(fx0 - 3, fx1 + 3); ax.set_ylim(fy1 + 3, fy0 - 3); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Plan (y abs down): flange at the flange front (light), frame at Z -9.0 (dark), glass / panel outlines, bend-gap slot, "
                 "tail plan footprints (built here), F1-F4", fontsize=12)
    ax = axs[1]
    for z, fc in ((-9.0, FC["frame"]),):
        for l in C.plan_loops(fr, z):
            ax.add_patch(MPoly(l["pts"], closed=True, fc=fc if l["outer"] else "white", ec="k", lw=0.5, zorder=3 if l["outer"] else 3.5))
    for l in C.plan_loops(fr, L["Z_LAND"] + 0.15):
        ax.plot(np.append(l["pts"][:, 0], l["pts"][0, 0]), np.append(l["pts"][:, 1], l["pts"][0, 1]), color="#1f4e9c", lw=0.6, zorder=4)
    for n, sol in tails_by_name.items():
        for lab, s, seg in sol:
            bb = s.BoundingBox()
            ax.add_patch(MPoly([(bb.xmin, -bb.ymax), (bb.xmax, -bb.ymax), (bb.xmax, -bb.ymin), (bb.xmin, -bb.ymin)], closed=True,
                               fc=FC["tail"], ec="#7a3e00", lw=0.6, alpha=0.35, zorder=5))
    ax.plot([px0, px1], [py1, py1], color="#d35400", lw=1.2, ls="--", zorder=7)
    ax.text(100, py1 - 0.4, "panel edge y %.2f" % py1, fontsize=10, color="#d35400", zorder=7)
    ax.axhline(G.BRIDGE[2], color="#c0392b", lw=0.8, ls=":", zorder=7)
    ax.text(41, G.BRIDGE[2] - 0.3, "bridge pocket face y %.2f (g_bend %.2f from the panel edge %.2f)" % (G.BRIDGE[2], G.g_bend, G.PANEL[3]),
            fontsize=10, color="#c0392b")
    P = C.Probe(fr)
    for yy in (126.0, 140.0):
        for a, b in P.x_intervals(yy, -9.0):
            if b - a < 4 and 30 < a < 180:
                ax.annotate("", xy=(a, yy), xytext=(b, yy), arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=0.8))
                ax.text((a + b) / 2, yy - 0.5, "%.2f" % (b - a), ha="center", fontsize=9, color="#c0392b",
                        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    ax.set_xlim(14, 194); ax.set_ylim(152, 112); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
    ax.set_title("Bottom zone: frame at Z -9.0 (grey), the land edge at Z_LAND + 0.15 (blue line: the 0.3 break over the tail span), "
                 "tail plan footprints, rib / wall widths at Z -9.0", fontsize=12)
    return save(fig, os.path.join(ctx.imgdir, "Plan_frame_and_bottom_zone_tails.png"))


def connector_figure(ctx, tails_by_name, fit=None):
    """y-Z sections of J10 / J11 at the tail's mid x: the connector model, my tail end, the DS1 model's own fingers (unmoved)"""
    G = ctx.G
    items0 = C.board_items(ctx.board_path, C.BOARD_DZ, 0.0)
    conn = {r: s for r, p, s in ctx.items if r in ("J10", "J11")}
    pcb = next(s for r, p, s in ctx.items if r == "PCB")
    fig, axs = plt.subplots(1, 2, figsize=(22, 8))
    for ax, (n, ref) in zip(axs, (("TFT", "J10"), ("CTP", "J11"))):
        T = G.raw["tail_route"][n]
        seg = T["outline_developed"][-1]
        xm = (seg[2] + seg[3]) / 2
        pl = Plane("x", xm)
        draw(ax, polys(pl, pcb), FC["pcb"], ec="#333333", lw=0.4, alpha=0.9, z=2)
        draw(ax, polys(pl, conn[ref]), FC["board"], ec="k", lw=0.5, alpha=0.75, z=3)
        for r, p, s in items0:
            if r == "DS1" and p.startswith(C.PANEL_TAIL_PARTS) and C.bb_gap(s, conn[ref]) < 0.5:
                draw(ax, polys(pl, s), "#9b59b6", ec="#4a235a", lw=0.4, alpha=0.55, z=4)
        for lab, s, sg in tails_by_name[n]:
            draw(ax, polys(pl, s), FC["tail"], ec="#7a3e00", lw=0.5, alpha=0.8, z=5)
        ax.set_xlim(T["y_end"] - 2.0, 122.0); ax.set_ylim(-0.5, 4.5); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
        ce = (fit or {}).get("connector_entry", {}).get(ref, {})
        ax.set_title("%s at x %.2f (y-Z section): model (dark), PCB (green), my %s tail end (orange), DS1 model's own tail / fingers "
                     "at the unmoved GF-1.1 position (purple)\noverlap my tail / model %.4f mm3; DS1 own bodies %s" % (
                         ref, xm, n, ce.get("overlap_my_tail_mm3", float("nan")), ce.get("overlap_DS1_own_bodies_unmoved_GF11_mm3")), fontsize=9)
        ax.set_xlabel("y abs (mm)"); ax.set_ylabel("Z (mm)")
    return save(fig, os.path.join(ctx.imgdir, "Connector_entry_J10_J11_tail_ends.png"))


def run(ctx, log=C.log, fit=None):
    import fit_check as F
    G, fr = ctx.G, ctx.frame
    L = G.L
    if G.gf2:
        return run_gf2(ctx, log, fit)
    A = F.build(G)
    hw = F.hardware(G, "S8")
    board = {"PCB": next((s for r, p, s in ctx.items if r == "PCB"), None)}
    tails = [(p, s) for r, p, s in ctx.items if r == "DS1" and p.startswith(C.PANEL_TAIL_PARTS)]
    gx0, gx1, gy0, gy1, gR = G.GLASS
    os.makedirs(ctx.imgdir, exist_ok=True)
    out, dims = {}, {}

    # 1. top edge, x 80
    pl = Plane("x", 80.0)
    title = "Section x = 80 (top edge, mid-top) - STEP %s; h = y abs (down), Z up = towards the PCB" % ctx.frame_info["mtime"]
    zpb = L["Z_PANEL_BACK"]
    def panel_dims(ax, M, d, pface, pedge, wall):
        d["pocket face -> panel at Z_PANEL_BACK"] = hdim2(ax, M, (zpb - 0.05, pface), (zpb - 0.05, pedge, True), zpb + 0.25, "pocket->panel", fs=9, tol=0.5)
        d["pocket face -> panel at Z_LAND"] = hdim2(ax, M, (L["Z_LAND"] + 0.05, pface - 0.1 * np.sign(pedge - pface)),
                                                    (L["Z_LAND"] + 0.05, pedge, True), L["Z_LAND"] + 0.3, "pocket->panel", fs=9, tol=0.5)
        d["wall at Z 0"] = hdim2(ax, M, (-0.3, wall[0]), (-0.3, wall[1]), 0.6, "wall at Z 0", fs=9)
        d["shelf"] = vdim(ax, M, pedge + 1.5 * np.sign(pedge - pface), -4.6, -2.1, pedge + 3.0 * np.sign(pedge - pface), "shelf", fs=9)
    fig, ax, d = edge_section(ctx, A, hw, board, "top", pl, (-12.5, 24.0), (-16.5, 2.0), lambda s: gy0 - s, (24, 9.5), title,
                              extra_dims=lambda ax, M, d: panel_dims(ax, M, d, 18.2, G.PANEL[2], (15.9, 18.15)), land_s=-7.93)
    out["Section_top_x80"] = save(fig, os.path.join(ctx.imgdir, "Section_top_x80.png"))
    dims["top x80"] = d

    # 2. side edge (left) near mid-height, y 60
    pl = Plane("y", 60.0)
    title = "Section y = 60 (left side edge, near mid-height, clear of the F8 tube) - h = x abs"
    fig, ax, d = edge_section(ctx, A, hw, board, "left", pl, (-9.5, 26.0), (-16.5, 2.0), lambda s: gx0 - s, (24, 9.5), title,
                              extra_dims=lambda ax, M, d: panel_dims(ax, M, d, 19.22, G.PANEL[0], (16.9, 19.18)), land_s=-6.01)
    out["Section_side_left_y60"] = save(fig, os.path.join(ctx.imgdir, "Section_side_left_y60.png"))
    dims["side y60"] = d

    # 3. chin on the centreline, x 103.85 (bottom part, through F7 and the tail pocket)
    pl = Plane("x", G.GC[0])
    title = "Section x = 103.85 (centreline, chin, tail pocket, F7 slot; S8 hardware, no VHB) - h = y abs; tails moved %.2f with the panel" % ctx.panel_dz
    def chin_dims(ax, M, d):
        d["TFT loop envelope y1 (146.2) -> beam face"] = hdim2(ax, M, (-6.0, 146.2, True), (-6.0, 147.7), -6.6, "loop env. -> beam", fs=9)
        d["beam"] = hdim2(ax, M, (-3.0, 147.75), (-3.0, 150.1), -2.4, "beam", fs=9)
        d["beam height (land -> trough top)"] = vdim2(ax, M, (148.9, L["Z_LAND"]), (148.9, 4.05), 146.9, "beam", fs=9, side="left")
        if G.cb:
            y7 = G.fxy("F7")[1]
            zfl7 = G.cb_floor_z("F7")
            d["F7 counterbore at the flange front"] = hdim2(ax, M, (L["Z_FLANGE_FRONT"] + 0.02, y7 - 4.5), (L["Z_FLANGE_FRONT"] + 0.02, y7 + 4.5),
                                                            -15.3, "F7 counterbore (at the flange front)", fs=9)
            d["F7 slot at the counterbore floor"] = hdim2(ax, M, (zfl7 + 0.02, y7 - 3.5), (zfl7 + 0.02, y7 + 3.5), zfl7 + 0.3, "F7 slot", fs=9)
        else:
            d["F7 slot at the flange front"] = hdim2(ax, M, (L["Z_FLANGE_FRONT"] + 0.01, 161.5), (L["Z_FLANGE_FRONT"] + 0.01, 168.5), -11.9, "F7 slot", fs=9)
    fig, ax, d = edge_section(ctx, A, hw, board, "bottom", pl, (110.0, 177.5), (-16.5, 6.0), lambda s: gy1 + s, (26, 8.5), title,
                              extra_dims=chin_dims, tails=tails, land_s=-6.3, tape=not G.cb,
                              legend_kw={"loc": "upper center", "anchor": (0.36, 1.0)})
    out["Section_chin_x103.85"] = save(fig, os.path.join(ctx.imgdir, "Section_chin_x103.85.png"))
    dims["chin x103.85"] = d

    # 4. F1 along its slot axis (t from F1 towards the glass centre)
    x1, y1 = G.fxy("F1")
    u = G.slot_axis("F1")
    pl = Plane("axis", origin=(x1, y1), axis=u)
    P = C.Probe(fr)
    M = Meas(pl, P)
    fig, ax = setup("Section through F1 along its slot axis (t from F1 towards the glass centre, %.2f deg) - pad, slot, tube, rib" %
                    math.degrees(math.atan2(u[1], u[0])), (-14, 30), (-16.5, 4.0), (19, 10))
    for pl_, col, alpha, key in assembly_polys(pl, A, hw, [("pcb", board["PCB"], FC["pcb"])] if board["PCB"] is not None else []):
        draw(ax, pl_, col, ec="#333333", lw=0.4, alpha=alpha, z=3 if key != "panel_env" else 1.5)
    draw(ax, polys(pl, fr), FC["frame"], ec="k", lw=0.7, z=2)
    level_lines(ax, G, (-14, 30), ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_FLANGE_BACK", "Z_LANDPLATE_BACK", "Z_TUBE_TOP", "Z_PCB"])
    d = {}
    zf, zt = L["Z_FLANGE_FRONT"], L["Z_TUBE_TOP"]
    d["slot_front"] = hdim(ax, M, zf, -3.5, 3.5, zf - 0.45, "slot @ flange front")
    d["slot_back"] = hdim(ax, M, zt - 0.05, -3.5, 3.5, zt + 1.8, "slot @ tube top")
    d["tube"] = hdim(ax, M, zt - 0.05, -9.0, 9.0, zt + 3.0, "tube dia")
    d["stack"] = vdim(ax, M, -6.0, L["Z_SHEET_BACK"], zt, -12.5, "pad+flange+tube", side="right")
    d["pad step"] = vdim2(ax, M, (6.0, L["Z_SHEET_BACK"]), (12.0, zf), 11.0, "pad", fs=9, side="left")
    d["flange t"] = vdim2(ax, M, (12.0, zf), (12.0, L["Z_FLANGE_BACK"]), 12.6, "flange", fs=9)
    ax.text(10.0, -5.6, "the tube rib is NOT in this plane:\nit runs 1.25 mm beside the slot axis, 5.8 deg off it\n(measured; see spec rows F1-F4 tube rib)",
            fontsize=9, color="#7a3e00", bbox=dict(boxstyle="round,pad=0.2", fc="#fff4e0", ec="#e0a050"))
    legend(ax)
    out["Section_F1_slot_axis"] = save(fig, os.path.join(ctx.imgdir, "Section_F1_slot_axis.png"))
    dims["F1 slot axis"] = d

    # 5. F8 mid-side tube (y 82.085, along its slot axis = x)
    pl = Plane("y", G.GC[1])
    title = "Section y = 82.085 through the mid-side tube F8 (slot axis = x%s) - h = x abs" % ("; S8 hardware, no VHB" if G.cb else "")
    def f8_dims(ax, M, d):
        zf, zt = L["Z_FLANGE_FRONT"], L["Z_TUBE_TOP"]
        x8 = G.fxy("F8")[0]
        if G.cb:
            zfl = G.cb_floor_z("F8")
            d["F8 counterbore at the flange front"] = hdim2(ax, M, (zf + 0.02, x8 - 4.5), (zf + 0.02, x8 + 4.5), zf - 0.45, "counterbore", fs=9)
            d["F8 slot at the counterbore floor"] = hdim2(ax, M, (zfl + 0.02, x8 - 3.5), (zfl + 0.02, x8 + 3.5), zfl + 0.3, "slot", fs=9)
        else:
            d["F8 slot at the flange front"] = hdim2(ax, M, (zf + 0.01, -1.39), (zf + 0.01, 5.61), zf - 0.45, "slot @ flange front", fs=9)
        if G.core:
            d["F8 outer skin at the tube top"] = hdim2(ax, M, (zt - 0.05, x8 - 9.0), (zt - 0.05, x8 - 7.5), zt + 0.5, "skin", fs=9)
            d["F8 inner sleeve (slot end -> groove), tube top - 1"] = hdim2(ax, M, (zt - 1.0, x8 - 6.2), (zt - 1.0, x8 - 3.5), zt - 0.75, "sleeve", fs=9)
        else:
            d["F8 tube outer edge -> slot"] = hdim2(ax, M, (zt - 0.05, -6.89), (zt - 0.05, -1.39), zt + 0.5, "tube wall", fs=9)
        hx = x8 - 8.3 if G.core else -4.5          # GF-1.1: in the outer skin (r 7.5-9.0), clear of the groove
        d["flange + tube"] = vdim2(ax, M, (hx, zf), (hx, zt), hx if G.core else -8.6, "flange + tube", fs=9)
    fig, ax, d = edge_section(ctx, A, hw, board, "left", pl, (-9.5, 26.0), (-16.5, 4.0), lambda s: gx0 - s, (24, 9.5), title,
                              extra_dims=f8_dims, land_s=-6.01, tape=not G.cb)
    out["Section_F8_tube_y82.085"] = save(fig, os.path.join(ctx.imgdir, "Section_F8_tube_y82.085.png"))
    dims["F8 y82"] = d

    # 6. plan section through the lip (Z -14.1) with the glass and the cut-out, whole ring + corner zoom
    z = L["Z_GLASS_FRONT"] + 0.32
    loops = C.plan_loops(fr, z)
    fig, axs = plt.subplots(1, 2, figsize=(22, 9), gridspec_kw={"width_ratios": [1.5, 1]})
    for ax, (xl, yl) in zip(axs, (((-12, 220), (180, -14)), ((8.5, 30.0), (27.0, 5.5)))):
        for l in loops:
            p = l["pts"]
            ax.add_patch(MPoly(p, closed=True, fc=FC["frame"] if l["outer"] else "white", ec="k", lw=0.6, zorder=3 if not l["outer"] else 2))
        gp = C.rrect_wire_pts(*G.GLASS, n=60)
        cp = C.rrect_wire_pts(*G.CUT, n=60)
        # above the white hole patch of the lip section (zorder 3), the glass never overlaps the lip
        ax.add_patch(MPoly(gp, closed=True, fc=FC["glass"], ec="#1f4e79", lw=0.6, alpha=0.6, zorder=3.5))
        ax.plot(np.append(cp[:, 0], cp[0, 0]), np.append(cp[:, 1], cp[0, 1]), color="#555555", lw=0.8, ls="-", zorder=4)
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
    ax = axs[1]
    from scipy.spatial import cKDTree
    lipface = next(l["face"] for l in loops if l["outer"] and 180 < np.ptp(l["pts"][:, 0]) < 186)
    inner = next(l["pts"] for l in loops if l["face"] == lipface and not l["outer"])
    outer = next(l["pts"] for l in loops if l["face"] == lipface and l["outer"])
    ti, to = cKDTree(C.densify(inner, 0.01)), cKDTree(C.densify(outer, 0.01))
    cx, cy = gx0 + gR, gy0 + gR                          # glass corner centre
    ccx, ccy = G.CUT[0] + G.CUT[4], G.CUT[2] + G.CUT[4]   # cut-out corner centre (not concentric with the glass in GF-1.1)
    for ang, lab in ((225, "corner"), (180, "side")):
        a = math.radians(ang)
        if lab == "corner":
            pg = (cx + gR * math.cos(a), cy + gR * math.sin(a))
            pc = (ccx + G.CUT[4] * math.cos(a), ccy + G.CUT[4] * math.sin(a))
        else:
            pg = (gx0, 24.0); pc = (G.CUT[0], 24.0)
        d2, i2 = ti.query(pg); d1, i1 = to.query(pc)
        q2, q1 = ti.data[i2], to.data[i1]
        ax.annotate("g2 %.3f" % d2, xy=pg, xytext=(pg[0] + 2.5, pg[1] + 2.0 if lab == "corner" else pg[1] + 1.2), fontsize=10, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))
        ax.annotate("g1 %.3f" % d1, xy=pc, xytext=(pc[0] - 0.5, pc[1] - 2.2 if lab == "corner" else pc[1] - 1.2), fontsize=10, color="#1f4e9c",
                    arrowprops=dict(arrowstyle="->", color="#1f4e9c", lw=0.8))
        ax.plot([pg[0], q2[0]], [pg[1], q2[1]], color="#c0392b", lw=1.2)
        ax.plot([pc[0], q1[0]], [pc[1], q1[1]], color="#1f4e9c", lw=1.2)
    axs[0].set_title("Plan section Z %.2f (0.32 behind the flush plane): lip ring (grey), glass (blue), sheet cut-out (line); y abs down" % z, fontsize=11)
    axs[1].set_title("Top-left corner: glass R%.2f, lip R%.1f / R%.1f, cut-out R%.2f - gaps on the STEP section at the diagonal / side" % (
        gR, G.LIP_IN[4], G.LIP_OUT[4], G.CUT[4]), fontsize=11)
    out["Plan_lip_Z-14.1"] = save(fig, os.path.join(ctx.imgdir, "Plan_lip_Z-14.1.png"))

    # 7. plan section through the corner cells (Z -6.0), bottom region
    z = -6.0
    loops = C.plan_loops(fr, z)
    fig, axs = plt.subplots(1, 2, figsize=(22, 10))
    P = C.Probe(fr)
    for ax, (xl, lab) in zip(axs, (((10.0, 45.0), "bottom-left cell (H7)"), ((162.0, 197.0), "bottom-right cell (H6)"))):
        for l in loops:
            p = l["pts"]
            ax.add_patch(MPoly(p, closed=True, fc=FC["frame"] if l["outer"] else "white", ec="k", lw=0.6, zorder=3 if not l["outer"] else 2))
        ax.set_xlim(*xl); ax.set_ylim(156.0, 112.0); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
        ax.set_title("Plan section Z %.1f - %s; y abs down" % (z, lab), fontsize=11)
        # measured wall widths along a few probe lines
        for yy in (126.0, 135.0, 143.0):
            iv = P.x_intervals(yy, z)
            for a, b in iv:
                if xl[0] < (a + b) / 2 < xl[1] and b - a < 4:
                    ax.annotate("", xy=(a, yy), xytext=(b, yy), arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=0.8))
                    ax.text((a + b) / 2, yy - 0.4, "%.2f" % (b - a), ha="center", fontsize=9, color="#c0392b",
                            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
        for xx in ((15.0, 23.0, 33.0) if xl[0] < 50 else (172.0, 182.0, 190.0)):
            iv = P.y_intervals(xx, z)
            for a, b in iv:
                if 112 < (a + b) / 2 < 156 and b - a < 4:
                    ax.annotate("", xy=(xx, a), xytext=(xx, b), arrowprops=dict(arrowstyle="<->", color="#1f4e9c", lw=0.8))
                    ax.text(xx + 0.3, (a + b) / 2, "%.2f" % (b - a), va="center", fontsize=9, color="#1f4e9c",
                            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    out["Plan_corner_cells_Z-6.0"] = save(fig, os.path.join(ctx.imgdir, "Plan_corner_cells_Z-6.0.png"))
    # 8. GF-1.1: section along the F5 slot axis (x 103.85, top) - counterbore, slot, coring groove, tube
    if G.cb or G.core:
        pl = Plane("x", G.GC[0])
        P = C.Probe(fr)
        M = Meas(pl, P)
        fig, ax = setup("Section x = 103.85 along the F5 slot axis, S8 variant (no VHB): counterbore, slot, coring groove, tube; "
                        "DIN 988 shim, weld stud (flange 5.7 x 1.4), washer, nut",
                        (-12.5, 14.0), (-15.0, -5.0), (20, 9))
        ax.set_xlabel("y abs (mm, down = right)"); ax.set_ylabel("Z (mm)")
        hw8 = F.hardware(G, "S8")
        for pl_, col, alpha, key in assembly_polys(pl, A, hw8, []):
            if key.startswith("tape"):
                continue
            draw(ax, pl_, col, ec="#333333", lw=0.4, alpha=alpha, z=3 if key != "panel_env" else 1.5)
        draw(ax, polys(pl, fr), FC["frame"], ec="k", lw=0.7, z=2)
        level_lines(ax, G, (-12.5, 14.0), ["Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_FLANGE_BACK", "Z_LANDPLATE_BACK", "Z_TUBE_TOP"])
        x5, y5 = G.fxy("F5")
        d = {}
        zfl = G.cb_floor_z("F5") if G.cb else None
        if G.cb:
            d["counterbore length at the flange front"] = hdim2(ax, M, (L["Z_FLANGE_FRONT"] + 0.02, y5 - 4.5), (L["Z_FLANGE_FRONT"] + 0.02, y5 + 4.5),
                                                                  L["Z_FLANGE_FRONT"] - 0.55, "counterbore", fs=9)
            d["slot length at its front end"] = hdim2(ax, M, (zfl + 0.02, y5 - 3.5), (zfl + 0.02, y5 + 3.5), zfl + 0.25, "slot", fs=9)
            d["counterbore depth"] = vdim2(ax, M, (y5 - 3.0, L["Z_FLANGE_FRONT"]), (y5 + 4.0, zfl), y5 + 5.6, "counterbore", fs=9)
        if G.core:
            zc = L["Z_TUBE_TOP"] - float(G.core["core_depth"])
            d["groove width at the tube top"] = hdim2(ax, M, (L["Z_TUBE_TOP"] - 0.05, y5 + 6.2), (L["Z_TUBE_TOP"] - 0.05, y5 + 7.5),
                                                      L["Z_TUBE_TOP"] + 0.3, "groove", fs=9)
            d["groove depth"] = vdim2(ax, M, (y5 + 5.6, L["Z_TUBE_TOP"]), (y5 + 6.85, zc), y5 + 8.4, "groove", fs=9)
            d["floor under the groove"] = vdim2(ax, M, (y5 + 6.85, zc), (y5 + 6.85, L["Z_FLANGE_FRONT"]), y5 + 6.85, "floor", fs=9)
            d["inner sleeve (slot end -> groove)"] = hdim2(ax, M, (L["Z_TUBE_TOP"] - 1.0, y5 + 3.5), (L["Z_TUBE_TOP"] - 1.0, y5 + 6.2),
                                                           L["Z_TUBE_TOP"] - 0.75, "sleeve", fs=9)
        legend(ax, tape=False)
        out["Section_F5_slot_axis_x103.85"] = save(fig, os.path.join(ctx.imgdir, "Section_F5_slot_axis_x103.85.png"))
        dims["F5 slot axis"] = d
    # 9. GF-1.1: plan of the counterbores with the weld-stud flange at the extreme positions the slot allows
    if G.cb:
        fig, axs = plt.subplots(1, 2, figsize=(20, 9.5))
        for ax, n in zip(axs, ("F1", "F5")):
            x, y = G.fxy(n)
            zo, zf = G.cb_open_z(n), G.cb_floor_z(n)
            for z, col, lab in ((zo + 0.02, "k", "counterbore at its opening"), (zf - 0.35, "#1f4e9c", "counterbore above the floor round"),
                                (zf + 0.05, "#c0392b", "slot at its front end")):
                for l in C.plan_loops(fr, z):
                    p = l["pts"]
                    if np.hypot(p[:, 0].mean() - x, p[:, 1].mean() - y) > 6 or np.ptp(p[:, 0]) > 15:
                        continue
                    ax.plot(np.append(p[:, 0], p[0, 0]), np.append(p[:, 1], p[0, 1]), color=col, lw=1.0, label=lab)
                    lab = None
            pos, dmax = F._positions(G, n, F.STUD_D / 2)
            for k_, (lab_, a, b) in enumerate(pos):
                px, py = F._xy(G, n, a, b)
                t = np.linspace(0, 2 * np.pi, 120)
                ax.plot(px + F.WELD_FLANGE[0] / 2 * np.cos(t), py + F.WELD_FLANGE[0] / 2 * np.sin(t), color="#e08e0b", lw=0.8,
                        label="weld flange dia %.1f (7 positions)" % F.WELD_FLANGE[0] if k_ == 0 else None)
                ax.plot(px + F.STUD_D / 2 * np.cos(t), py + F.STUD_D / 2 * np.sin(t), color="#7a7a7a", lw=0.6, ls="--",
                        label="shank dia 4 (against the slot wall)" if k_ == 0 else None)
            ax.set_aspect("equal"); ax.grid(True, lw=0.25)
            ax.set_xlim(x - 6.5, x + 6.5); ax.set_ylim(y + 6.5, y - 6.5)
            ax.set_title("%s: counterbore %.1f x %.1f, floor Z %.2f; stud flange at centre and at the slot extremes (offset %.3f)" % (
                n, float(G.cb["cb_w"]), float(G.cb["cb_l"]), zf, dmax), fontsize=10)
            ax.legend(loc="lower left", fontsize=8)
        out["Plan_counterbore_stud_flange"] = save(fig, os.path.join(ctx.imgdir, "Plan_counterbore_stud_flange.png"))
    for k, v in out.items():
        log("  section", k)
    return {"images": out, "dims_measured": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in dims.items()}}


def run_gf2(ctx, log=C.log, fit=None):
    """GF-2.0 image set (names say what they show; no chin / F5-F8 sections any more)"""
    import json
    import fit_check as F
    import tails_gf2 as TG
    G, fr = ctx.G, ctx.frame
    L = G.L
    if fit is None and os.path.exists(ctx.out("fitcheck.json")):
        fit = json.load(open(ctx.out("fitcheck.json")))
    A = F.build(G)
    hw = F.hardware(G, "S4")
    board = {"PCB": next((s for r, p, s in ctx.items if r == "PCB"), None)}
    for r, p, s in ctx.items:
        if r in ("J10", "J11"):
            board[r] = s
    tails_by_name = {n: TG.tail_solids(G, n) for n in ("TFT", "CTP")}
    tails = [("%s tail %s" % (n, lab), s) for n, sol in tails_by_name.items() for lab, s, _ in sol]
    gx0, gx1, gy0, gy1, gR = G.GLASS
    os.makedirs(ctx.imgdir, exist_ok=True)
    out, dims = {}, {}
    zpb = L["Z_PANEL_BACK"]

    def panel_dims(ax, M, d, pface, pedge, wall):
        d["pocket face -> panel at Z_PANEL_BACK"] = hdim2(ax, M, (zpb - 0.05, pface), (zpb - 0.05, pedge, True), zpb + 0.25, "pocket->panel", fs=9, tol=0.5)
        d["pocket face -> panel at Z_LAND"] = hdim2(ax, M, (L["Z_LAND"] + 0.05, pface - 0.1 * np.sign(pedge - pface)),
                                                    (L["Z_LAND"] + 0.05, pedge, True), L["Z_LAND"] + 0.3, "pocket->panel", fs=9, tol=0.5)
        d["wall at Z 0"] = hdim2(ax, M, (-0.3, wall[0]), (-0.3, wall[1]), 0.6, "wall at Z 0", fs=9)
        d["shelf"] = vdim(ax, M, pedge + 1.5 * np.sign(pedge - pface), -4.6, -2.1, pedge + 3.0 * np.sign(pedge - pface), "shelf", fs=9)
    # 1. top edge x 80
    title = "Section x = 80 (top edge, mid-top) - STEP %s; h = y abs (down), Z up = towards the PCB; S4 hardware, VHB" % ctx.frame_info["mtime"]
    fig, ax, d = edge_section(ctx, A, hw, board, "top", Plane("x", 80.0), (-17.5, 24.0), (-16.5, 2.0), lambda s: gy0 - s, (24, 9.5), title,
                              extra_dims=lambda ax, M, d: panel_dims(ax, M, d, G.POCKET[2], G.PANEL[2], (G.POCKET[2] - 2.35, G.POCKET[2] - 0.05)),
                              land_s=-(gy0 - G.POCKET[2]) + 0.1)
    out["Section_top_edge_x80"] = save(fig, os.path.join(ctx.imgdir, "Section_top_edge_x80.png"))
    dims["top x80"] = d
    # 2. side edge (left) y 60
    title = "Section y = 60 (left side edge, mid-height) - h = x abs; S4 hardware, VHB"
    fig, ax, d = edge_section(ctx, A, hw, board, "left", Plane("y", 60.0), (-14.5, 26.0), (-16.5, 2.0), lambda s: gx0 - s, (24, 9.5), title,
                              extra_dims=lambda ax, M, d: panel_dims(ax, M, d, G.POCKET[0], G.PANEL[0], (G.POCKET[0] - 2.35, G.POCKET[0] - 0.05)),
                              land_s=-(gx0 - G.POCKET[0]) + 0.1)
    out["Section_side_edge_left_y60"] = save(fig, os.path.join(ctx.imgdir, "Section_side_edge_left_y60.png"))
    dims["side y60"] = d
    # 3. the bridge: x 60 (CTP tail), 79.92 (divider rib), 103.85 (TFT tail), 150 (TFT wide part)
    for x, fn, lab in ((60.0, "Section_bridge_CTP_tail_x60.png", "bridge at the CTP tail"),
                       (G.div_x, "Section_divider_rib_x79.92.png", "through the divider rib"),
                       (G.GC[0], "Section_bridge_TFT_tail_x103.85.png", "bridge at the TFT tail (centreline)"),
                       (150.0, "Section_bridge_TFT_wide_part_x150.png", "bridge at the TFT tail's wide part")):
        title = "Section x = %.2f, %s - STEP %s; h = y abs; tails on the %s route built here; S4 hardware, VHB" % (
            x, lab, ctx.frame_info["mtime"], G.revision.split(" ")[0])
        p, d = bridge_section(ctx, A, hw, board, tails, x, fn, title, fit)
        out[fn[:-4]] = p
        dims[fn[:-4]] = d
    # 4. F1 along its slot axis (corner fastener)
    x1, y1 = G.fxy("F1")
    u = G.slot_axis("F1")
    pl = Plane("axis", origin=(x1, y1), axis=u)
    P = C.Probe(fr)
    M = Meas(pl, P)
    fig, ax = setup("Corner F1 along its slot axis (t from F1 towards the glass centre, %.2f deg) - pad, counterbore, slot, tube, coring; "
                    "S4 stud with the dia %.1f x %.1f flange + collar envelope, washer, nut" % (math.degrees(math.atan2(u[1], u[0])), F.WELD_ENV[0], F.WELD_ENV[1]),
                    (-14, 30), (-16.5, 4.0), (19, 10))
    for pl_, col, alpha, key in assembly_polys(pl, A, hw, [("pcb", board["PCB"], FC["pcb"])] if board["PCB"] is not None else []):
        draw(ax, pl_, col, ec="#333333", lw=0.4, alpha=alpha, z=3 if key != "panel_env" else 1.5)
    draw(ax, polys(pl, fr), FC["frame"], ec="k", lw=0.7, z=2)
    level_lines(ax, G, (-14, 30), ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_FLANGE_BACK", "Z_LANDPLATE_BACK", "Z_TUBE_TOP", "Z_PCB"])
    d = {}
    zf, zt = L["Z_FLANGE_FRONT"], L["Z_TUBE_TOP"]
    zcb = G.cb_floor_z("F1")
    d["counterbore at the pad face"] = hdim(ax, M, L["Z_SHEET_BACK"] + 0.02, -4.5, 4.5, L["Z_SHEET_BACK"] - 0.55, "counterbore @ pad face")
    d["slot at the counterbore floor"] = hdim(ax, M, zcb + 0.02, -3.5, 3.5, zcb + 0.3, "slot @ cb floor", fs=9)
    d["slot_back"] = hdim(ax, M, zt - 0.05, -3.5, 3.5, zt + 1.8, "slot @ tube top")
    d["tube"] = hdim(ax, M, zt - 0.05, -9.0, 9.0, zt + 3.0, "tube dia")
    d["stack"] = vdim(ax, M, -6.0, L["Z_SHEET_BACK"], zt, -12.5, "pad+flange+tube", side="right")
    d["counterbore depth"] = vdim2(ax, M, (5.0, L["Z_SHEET_BACK"]), (0.0, zcb), 4.2, "cb depth", fs=9, side="left")
    d["groove depth"] = vdim2(ax, M, (5.6, zt), (6.85, zt - float(G.core["core_depth"])), 8.4, "groove", fs=9)
    legend(ax)
    out["Section_corner_F1_slot_axis"] = save(fig, os.path.join(ctx.imgdir, "Section_corner_F1_slot_axis.png"))
    dims["F1 slot axis"] = d
    # 5. plan through the lip, glass, cut-out
    from scipy.spatial import cKDTree
    z = L["Z_GLASS_FRONT"] + 0.32
    loops = C.plan_loops(fr, z)
    fig, axs = plt.subplots(1, 2, figsize=(22, 9), gridspec_kw={"width_ratios": [1.5, 1]})
    for ax, (xl, yl) in zip(axs, (((-14, 222), (152, -17)), ((gx0 - 1.5, gx0 + 20.0), (gy0 + 20.0, gy0 - 1.5)))):
        for l in loops:
            ax.add_patch(MPoly(l["pts"], closed=True, fc=FC["frame"] if l["outer"] else "white", ec="k", lw=0.6, zorder=3 if not l["outer"] else 2))
        gp = C.rrect_wire_pts(*G.GLASS, n=60)
        cp = C.rrect_wire_pts(*G.CUT, n=60)
        ax.add_patch(MPoly(gp, closed=True, fc=FC["glass"], ec="#1f4e79", lw=0.6, alpha=0.6, zorder=3.5))
        ax.plot(np.append(cp[:, 0], cp[0, 0]), np.append(cp[:, 1], cp[0, 1]), color="#555555", lw=0.8, ls="-", zorder=4)
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
    ax = axs[1]
    lf = F.lip_face(G, loops)
    inner = next(l["pts"] for l in loops if l["face"] == lf and not l["outer"])
    outer = next(l["pts"] for l in loops if l["face"] == lf and l["outer"])
    ti, to = cKDTree(C.densify(inner, 0.01)), cKDTree(C.densify(outer, 0.01))
    cx, cy = gx0 + gR, gy0 + gR
    ccx, ccy = G.CUT[0] + G.CUT[4], G.CUT[2] + G.CUT[4]
    for ang, lab in ((225, "corner"), (180, "side")):
        a = math.radians(ang)
        if lab == "corner":
            pg = (cx + gR * math.cos(a), cy + gR * math.sin(a))
            pc = (ccx + G.CUT[4] * math.cos(a), ccy + G.CUT[4] * math.sin(a))
        else:
            pg = (gx0, gy0 + 14.0); pc = (G.CUT[0], gy0 + 14.0)
        d2, i2 = ti.query(pg); d1, i1 = to.query(pc)
        q2, q1 = ti.data[i2], to.data[i1]
        ax.annotate("g2 %.3f" % d2, xy=pg, xytext=(pg[0] + 2.5, pg[1] + 2.0 if lab == "corner" else pg[1] + 1.2), fontsize=10, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))
        ax.annotate("g1 %.3f" % d1, xy=pc, xytext=(pc[0] - 0.5, pc[1] - 2.2 if lab == "corner" else pc[1] - 1.2), fontsize=10, color="#1f4e9c",
                    arrowprops=dict(arrowstyle="->", color="#1f4e9c", lw=0.8))
        ax.plot([pg[0], q2[0]], [pg[1], q2[1]], color="#c0392b", lw=1.2)
        ax.plot([pc[0], q1[0]], [pc[1], q1[1]], color="#1f4e9c", lw=1.2)
    axs[0].set_title("Plan section Z %.2f (0.32 behind the flush plane): lip ring + pads (grey), glass (blue), sheet cut-out (line); y abs down" % z, fontsize=11)
    axs[1].set_title("Top-left corner: glass R%.2f, lip R%.1f / R%.1f, cut-out R%.2f - gaps on the STEP section" % (gR, G.LIP_IN[4], G.LIP_OUT[4], G.CUT[4]), fontsize=11)
    out["Plan_lip_glass_cutout_Z-14.10"] = save(fig, os.path.join(ctx.imgdir, "Plan_lip_glass_cutout_Z-14.10.png"))
    # 6. plan of the frame and the bottom zone with the tails
    out["Plan_frame_and_bottom_zone_tails"] = plan_bottom(ctx, A, tails_by_name, fit)
    # 7. corner cells at Z -6.0
    z = -6.0
    loops = C.plan_loops(fr, z)
    fig, axs = plt.subplots(1, 2, figsize=(22, 10))
    for ax, (xl, lab) in zip(axs, (((10.0, 45.0), "bottom-left cell (H7)"), ((162.0, 197.0), "bottom-right cell (H6)"))):
        for l in loops:
            ax.add_patch(MPoly(l["pts"], closed=True, fc=FC["frame"] if l["outer"] else "white", ec="k", lw=0.6, zorder=3 if not l["outer"] else 2))
        ax.set_xlim(*xl); ax.set_ylim(152.0, 112.0); ax.set_aspect("equal"); ax.grid(True, lw=0.25)
        ax.set_title("Plan section Z %.1f - %s; y abs down" % (z, lab), fontsize=11)
        for yy in (126.0, 135.0, 143.0):
            for a, b in P.x_intervals(yy, z):
                if xl[0] < (a + b) / 2 < xl[1] and b - a < 4:
                    ax.annotate("", xy=(a, yy), xytext=(b, yy), arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=0.8))
                    ax.text((a + b) / 2, yy - 0.4, "%.2f" % (b - a), ha="center", fontsize=9, color="#c0392b",
                            bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    out["Plan_corner_cells_Z-6.0"] = save(fig, os.path.join(ctx.imgdir, "Plan_corner_cells_Z-6.0.png"))
    # 8. counterbores F1 / F4 with the weld-stud envelope (centred, +-0.3, slot limits)
    fig, axs = plt.subplots(1, 2, figsize=(20, 9.5))
    for ax, n in zip(axs, ("F1", "F4")):
        x, y = G.fxy(n)
        zo, zfl = G.cb_open_z(n), G.cb_floor_z(n)
        for zz, col, lab in ((zo + 0.02, "k", "counterbore at its opening (pad face)"), (zfl - 0.35, "#1f4e9c", "counterbore above the floor round"),
                             (zfl + 0.05, "#c0392b", "slot at its front end")):
            for l in C.plan_loops(fr, zz):
                p = l["pts"]
                if np.hypot(p[:, 0].mean() - x, p[:, 1].mean() - y) > 6 or np.ptp(p[:, 0]) > 15:
                    continue
                ax.plot(np.append(p[:, 0], p[0, 0]), np.append(p[:, 1], p[0, 1]), color=col, lw=1.0, label=lab)
                lab = None
        t = np.linspace(0, 2 * np.pi, 120)
        slot_pos, dmax = F._positions(G, n, F.STUD_D / 2)
        for k_, (lab_, a, b) in enumerate(F._tol_positions() + slot_pos[1:]):
            px, py = F._xy(G, n, a, b)
            tol = k_ < 9
            ax.plot(px + F.WELD_ENV[0] / 2 * np.cos(t), py + F.WELD_ENV[0] / 2 * np.sin(t), color="#e08e0b" if tol else "#9b59b6", lw=0.8,
                    label=("envelope dia %.1f, centred and +-0.3" % F.WELD_ENV[0]) if k_ == 0 else ("envelope at the slot limits" if k_ == 9 else None))
        ax.set_aspect("equal"); ax.grid(True, lw=0.25)
        ax.set_xlim(x - 6.5, x + 6.5); ax.set_ylim(y + 6.5, y - 6.5)
        sres = (fit or {}).get("stud_seat", {})
        key = next((k for k in sres if k.startswith("dia %.1f" % F.WELD_ENV[0]) and "slot limits" in k), None)
        mm = sres[key]["min"] if key else {}
        ax.set_title("%s: counterbore %.1f x %.1f, floor Z %.2f; weld-stud envelope dia %.1f x %.1f\nslot limits: wall %s / floor round %s / floor %s" % (
            n, float(G.cb["cb_w"]), float(G.cb["cb_l"]), zfl, F.WELD_ENV[0], F.WELD_ENV[1], mm.get("wall"), mm.get("floor round"), mm.get("floor")), fontsize=10)
        ax.legend(loc="lower left", fontsize=8)
    out["Plan_counterbores_F1_F4_stud_envelope"] = save(fig, os.path.join(ctx.imgdir, "Plan_counterbores_F1_F4_stud_envelope.png"))
    # 9. connector entry
    out["Connector_entry_J10_J11_tail_ends"] = connector_figure(ctx, tails_by_name, fit)
    for k in out:
        log("  section", k)
    return {"images": out, "dims_measured": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in dims.items()}}


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    _ = ctx.frame
    r = run(ctx)
    print(r["dims_measured"])
