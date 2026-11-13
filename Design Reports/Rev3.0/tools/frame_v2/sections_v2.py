"""2D section drawings (matplotlib) of the assembly through the frame STEP - v1 sections.py, plus hatching and
outlines. Every part is cut by a plane (BRepAlgoAPI_Common with a planar face), the section faces are filled
(tessellated), the frame is hatched, all section outlines are drawn, and the Z stack is dimensioned.

  <venv>/Scripts/python.exe sections_v2.py [--v1] [--frame f.step] [--params p.json] [--board b.step]

  A  x = a top-edge stud hole (the one nearest the middle): wall, flange, tube, radial rib, sheet, gasket, panel, PCB
  B  x = 30 through the PCB bosses H1 / H7
  C  x = 125 through the tail pocket and the TFT tail loop
  D  plan section at Z_FRONT + 1.25 (inside the flange), front view from the oven side: ring, bosses, holes
  E  y = a side stud hole (left or right, the one nearest mid-height)
Output: PNGs in the renders folder (renders_v2/, --v1: renders_v2/v1_regression/).
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
from matplotlib.collections import LineCollection
import cadquery as cq

import common_v2 as C
from calc_v2 import edges_of

COLS = {"frame PA6-GF30": (0.62, 0.64, 0.68), "Formex sheet": (0.85, 0.80, 0.30),
        "gasket (compressed)": (0.85, 0.15, 0.12), "oven front sheet (patch)": (0.70, 0.72, 0.75),
        "M4 stud": (0.55, 0.50, 0.40), "PCB": (0.10, 0.42, 0.20), "panel": (0.45, 0.55, 0.65),
        "panel: tails": (0.90, 0.55, 0.10), "components": (0.30, 0.30, 0.33)}
plt.rcParams["hatch.linewidth"] = 0.5


def cut(shape, axis, value):
    """-> (triangles [(p, p, p)], boundary polylines [N x 3]) of the section of `shape` by axis = value"""
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    sec = C.plane_section(s, axis, value)
    if sec is None:
        return [], []
    tris, lines = [], []
    for f in sec.Faces():
        vs, ts = f.tessellate(0.01, 0.1)
        for t in ts:
            tris.append([(vs[i].x, vs[i].y, vs[i].z) for i in t])
        for e in f.Edges():
            lines.append(C.edge_polyline(e, 0.005))
    return tris, lines


def section(parts, axis, value, fname, proj, title, xlim=None, ylim=None, dims=(), notes=(), figsize=(16, 7),
            insets=()):
    """parts: [(label, shape, rgb, hatch)]; proj: (x, y, z) -> (h, v) screen coordinates.
    dims: [(p0, p1, offset, text, horiz)] screen coords; insets: [(xlim, ylim, rect=[l, b, w, h])]."""
    if insets:                                   # zoom panels in their own row below the full section
        fig = plt.figure(figsize=(figsize[0], figsize[1] * 1.6))
        gs = fig.add_gridspec(2, len(insets), height_ratios=[1, 1.4])
        ax = fig.add_subplot(gs[0, :])
        zax = [fig.add_subplot(gs[1, i]) for i in range(len(insets))]
    else:
        fig, ax = plt.subplots(figsize=figsize)
        zax = []
    cache = []
    for lbl, shp, rgb, hatch in parts:
        tris, lines = cut(shp, axis, value)
        if not tris:
            continue
        polys = [[proj(*p) for p in t] for t in tris]
        segs = [np.array([proj(*p) for p in l]) for l in lines]
        cache.append((polys, segs, rgb, lbl, hatch))
    handles = {}

    def paint(a, lw=0.5):
        for polys, segs, rgb, lbl, hatch in cache:
            for pp in polys:
                a.add_patch(Polygon(pp, closed=True, fc=rgb, ec=rgb, lw=0.35))     # lw hides tessellation seams
                if hatch:
                    a.add_patch(Polygon(pp, closed=True, fill=False, hatch="////", lw=0, ec="0.25"))
            a.add_collection(LineCollection(segs, colors="k", linewidths=lw))
            handles[lbl] = (rgb, hatch)
    paint(ax)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.2, alpha=0.4)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    if not xlim or not ylim:
        ax.autoscale_view()
    for dd in dims:
        _dim(ax, *dd)
    for (x, y, txt) in notes:
        ax.annotate(txt, (x, y), fontsize=7, xytext=(8, 8), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", lw=0.4), bbox=dict(fc="w", ec="none", alpha=0.8, pad=0.5))
    ax.legend(handles=[Patch(fc=c, hatch="////" if h else None, ec="0.25" if h else c, label=l)
                       for l, (c, h) in handles.items()], fontsize=7, loc="upper right", ncol=2, framealpha=0.9)
    for (xl, yl, rect), ia in zip(insets, zax):
        paint(ia, lw=0.4)
        ia.set_xlim(*xl); ia.set_ylim(*yl); ia.set_aspect("equal"); ia.grid(True, lw=0.2, alpha=0.4)
        ia.tick_params(labelsize=7)
        ia.set_title("zoom %.0f..%.0f" % xl, fontsize=8)
        for dd in dims:
            if xl[0] <= dd[0][0] <= xl[1] and yl[0] <= dd[0][1] <= yl[1]:
                _dim(ia, *dd, fs=7)
        ax.add_patch(plt.Rectangle((xl[0], yl[0]), xl[1] - xl[0], yl[1] - yl[0], fill=False, ec="0.4", lw=0.6, ls="--"))
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(fname, dpi=140)
    plt.close(fig)
    return fname


def _dim(ax, p0, p1, off, text, horiz=True, left=False, fs=7):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        ax.plot([x0, x0], [y0, off], lw=0.3, color="m"); ax.plot([x1, x1], [y1, off], lw=0.3, color="m")
        ax.annotate("", (x0, off), (x1, off), arrowprops=dict(arrowstyle="<->", lw=0.5, color="m"))
        ax.text((x0 + x1) / 2, off, text, ha="center", va="bottom", fontsize=fs, color="m")
    else:
        ax.plot([x0, off], [y0, y0], lw=0.3, color="m"); ax.plot([x1, off], [y1, y1], lw=0.3, color="m")
        ax.annotate("", (off, y0), (off, y1), arrowprops=dict(arrowstyle="<->", lw=0.5, color="m"))
        if left:                                     # text on the left of the dimension line (off the part)
            ax.text(off, (y0 + y1) / 2, text + " ", ha="right", va="center", fontsize=fs, color="m")
        else:
            ax.text(off, (y0 + y1) / 2, " " + text, ha="left", va="center", fontsize=fs, color="m")


def pick_studs(D):
    """(top-edge stud nearest the top edge's middle, side stud nearest mid-height)"""
    x0, x1, y0, y1 = D.OUTER
    top = [(abs(x - (x0 + x1) / 2), n) for n, (x, y) in D.STUDS.items() if "top" in edges_of(D, x, y)]
    side = [(abs(y - (D.PY0 + D.PY1) / 2), n) for n, (x, y) in D.STUDS.items()
            if {"left", "right"} & set(edges_of(D, x, y)) and not {"top", "bottom"} & set(edges_of(D, x, y))]
    return (min(top)[1] if top else None), (min(side)[1] if side else None)


def z_dims(D, h, side=1):
    """Z-stack dimension chain at screen h (vertical dims): list for section()"""
    out = [((h, D.Z_FRONT), (h, D.Z_PCB), h + 1.0 * side, "%.2f" % (D.Z_PCB - D.Z_FRONT), False),
           ((h + 3 * side, D.Z_PANEL_BACK), (h + 3 * side, D.Z_PCB), h + 4 * side,
            "%.2f stand-off" % (D.Z_PCB - D.Z_PANEL_BACK), False),
           ((h + 3 * side, D.Z_GLASS), (h + 3 * side, D.Z_PANEL_BACK), h + 4 * side, "%.2f panel" % D.PANEL_T, False),
           ((h + 3 * side, D.Z_FRONT), (h + 3 * side, D.Z_GLASS), h + 4 * side,
            "%.2f gasket" % (D.Z_GLASS - D.Z_FRONT), False)]
    return out


def run(ctx, log=C.log):
    D, aux = ctx.D, ctx.aux
    os.makedirs(ctx.imgdir, exist_ok=True)
    import glob                                   # Section A / E names carry the stud position: drop old ones
    for old in glob.glob(os.path.join(ctx.imgdir, "Section_A_stud_*.png")) +             glob.glob(os.path.join(ctx.imgdir, "Section_E_stud_*.png")):
        os.remove(old)
    parts = [("frame PA6-GF30", ctx.frame, COLS["frame PA6-GF30"], True),
             ("Formex sheet", aux["sheet"], COLS["Formex sheet"], False),
             ("gasket (compressed)", aux["gasket"], COLS["gasket (compressed)"], False),
             ("oven front sheet (patch)", aux["oven"], COLS["oven front sheet (patch)"], False),
             ("M4 stud", cq.Compound.makeCompound(aux["studs"]), COLS["M4 stud"], False)]
    grp = {}
    for ref, part, s in ctx.items:
        lab = "PCB" if ref == "PCB" else ("panel: tails" if (ref == "DS1" and "tail" in part.lower()) else
                                          ("panel" if ref == "DS1" else "components"))
        grp.setdefault(lab, []).append(s)
    for lab, ss in grp.items():
        parts.append((lab, cq.Compound.makeCompound(ss), COLS[lab], False))
    hv = lambda x, y, z: (-y, z)            # horizontal = board y (abs, top edge at the left), vertical = Z
    out = {}
    tagt = "" if not ctx.v1 else " [v1 regression run]"
    sA, sE = pick_studs(D)
    zf, z0 = D.Z_FRONT, D.Z_PCB
    x0, x1, y0, y1 = D.OUTER
    # ---- A: top-edge stud
    if sA:
        xA, yA = D.STUDS[sA]
        fl = y0 - D.FLANGE_W_SIDE["top"] if D.FLANGE_W_SIDE["top"] > 0 else yA - D.STUD_OD / 2
        p = os.path.join(ctx.imgdir, "Section_A_stud_%s_x%.1f.png" % (sA, xA))
        dims = z_dims(D, y0 + 9.5) + [
            ((yA, zf - 2.2), (y0, zf - 2.2), zf - 2.6, "%.2f" % (y0 - yA), True),
            ((fl, zf - 3.6), (y0, zf - 3.6), zf - 4.0, "flange %.1f" % (y0 - fl), True)]
        if D.Z_STUD_TOP is not None:
            dims.append(((yA - 5.5, D.Z_STUD_TOP), (yA - 5.5, zf), yA - 8.5, "tube top %.2f" % (D.Z_STUD_TOP - zf),
                         False, True))
            dims.append(((yA - 7.5, D.Z_FLANGE_BACK), (yA - 7.5, zf), yA - 11.0,
                         "flange %.2f" % (D.Z_FLANGE_BACK - zf), False, True))
        section(parts, "x", xA, p, hv,
                "Section A-A at board x = %.2f through stud %s (top edge): wall, flange, stud tube, radial rib, M4 stud, "
                "oven sheet, gasket, panel, PCB; left = outside (top), down = oven front%s" % (xA, sA, tagt),
                xlim=(yA - 17, y0 + 22), ylim=(zf - 5, 6), dims=dims, figsize=(16, 9))
        out["Section_A"] = p
    # ---- B: PCB bosses H1 / H7 (x = 30)
    xB = D.HOLES.get("H1", (30.0, 0))[0]
    p = os.path.join(ctx.imgdir, "Section_B_pcb_bosses_x%.0f.png" % xB)
    yb0 = min(y for n, (x, y) in D.STUDS.items()) - 8
    section(parts, "x", xB, p, hv,
            "Section B-B at board x = %.1f through the PCB bosses H1 (top) and H7 (bottom); left = top edge, "
            "down = oven front%s" % (xB, tagt),
            xlim=(yb0, max(y1 + D.FLANGE_W, D.TROUGH[3] if D.TROUGH else y1) + 6), ylim=(zf - 6, 8),
            dims=z_dims(D, D.PY0 + 6) + [((10.2, 3.5), (18.2, 3.5), 4.5, "boss %.1f" % D.BOSS_OD, True)],
            insets=[((yb0, yb0 + 30), (zf - 3, 6), None),
                    ((110, 140), (zf - 3, 6), None)], figsize=(18, 6))
    out["Section_B"] = p
    # ---- C: tail pocket (x = 125)
    xC = 125.0
    p = os.path.join(ctx.imgdir, "Section_C_tail_pocket_x%.0f.png" % xC)
    dims = []
    if D.TROUGH:
        dims = [((D.TROUGH[3], D.LOOP_Z[1]), (D.TROUGH[3], D.Z_TROUGH_TOP), D.TROUGH[3] - 3.0,
                 "%.2f wall top over the loop top" % (D.Z_TROUGH_TOP - D.LOOP_Z[1]), False, True),
                ((D.PY1 + 9.0, zf), (D.PY1 + 9.0, D.LOOP_Z[0]), D.PY1 + 9.0,
                 "%.2f loop bottom to the sheet" % (D.LOOP_Z[0] - zf), False)]
    section(parts, "x", xC, p, hv,
            "Section C-C at board x = %.0f through the TFT tail U-loop and the tail pocket%s" % (xC, tagt),
            xlim=(100, y1 + max(D.FLANGE_W, 2) + 6), ylim=(zf - 6, 10), dims=dims, figsize=(16, 7))
    out["Section_C"] = p
    # ---- D: plan section in the flange, front view
    zD = D.Z_FRONT + 1.25
    xc, yc = D.window_datum()
    p = os.path.join(ctx.imgdir, "Section_D_flange_plan_Z%.2f.png" % zD)
    notes = [(-(x - xc), -(y - yc), n) for n, (x, y) in D.STUDS.items()]
    section(parts, "z", zD, p, lambda x, y, z: (-(x - xc), y + yc),
            "Section D-D: plan at Z = %.2f (flange front + 1.25), seen from the oven front (u right, v up, datum = "
            "sheet-window centre): flange ring, stud holes, PCB bosses, gasket%s" % (zD, tagt),
            notes=notes, figsize=(16, 13))
    out["Section_D"] = p
    # ---- E: side stud
    if sE:
        xE, yE = D.STUDS[sE]
        left = "left" in edges_of(D, xE, yE)
        p = os.path.join(ctx.imgdir, "Section_E_stud_%s_y%.1f.png" % (sE, yE))
        wall = x0 if left else x1
        fwE = D.FLANGE_W_SIDE["left" if left else "right"]
        dims = [((xE, zf - 2.2), (wall, zf - 2.2), zf - 2.6, "%.2f" % abs(wall - xE), True)]
        if fwE > 0:
            fe = wall - fwE if left else wall + fwE
            dims.append(((fe, zf - 3.6), (wall, zf - 3.6), zf - 4.0, "flange %.1f" % fwE, True))
        if D.Z_STUD_TOP is not None:
            dims.append(((xE + (-5.5 if left else 5.5), D.Z_STUD_TOP), (xE + (-5.5 if left else 5.5), zf),
                         xE + (-8.5 if left else 8.5), "tube top %.2f" % (D.Z_STUD_TOP - zf), False, left))
        section(parts, "y", -yE, p, lambda x, y, z: (x, z),
                "Section E-E at board y = %.2f through stud %s (%s edge): wall, flange, stud tube, rib; horizontal = "
                "board x, down = oven front%s" % (yE, sE, "left" if left else "right", tagt),
                xlim=((xE - 17, x0 + 22) if left else (x1 - 22, xE + 17)), ylim=(zf - 5, 6), dims=dims, figsize=(16, 9))
        out["Section_E"] = p
    for k, v in out.items():
        log("  section", os.path.basename(v))
    return out


if __name__ == "__main__":
    run(C.Context(sys.argv[1:]))
