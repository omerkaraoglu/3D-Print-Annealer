"""2D drawing (PNG) of the carrier frame's main dimensions and the oven front-sheet cut-out / hole
pattern, plus a DXF of the sheet pattern. Views are FRONT views (as seen from in front of the oven):
u = -(x - x_c) to the right, v = -(y - y_c) up, datum = centre of the front-sheet window.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir

import frame as F

PEM_HOLE = 4.22          # sheet hole for a PEM FH-M4 self-clinching stud (+0.08 / -0)
PEG_HOLE = F.PEG_D + 0.2


def datum():
    co = F.cutout_rect()
    return (co[0] + co[1]) / 2, (co[2] + co[3]) / 2


def uv(x, y):
    xc, yc = datum()
    return -(x - xc), -(y - yc)


def section_polys(shape, z):
    """Faces of `shape` cut by the plane Z = z, as lists of model (X, Y) polygons (tessellated)."""
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1)), -1000, 1000, -1000, 1000).Face()
    op = BRepAlgoAPI_Common(s.wrapped, face)
    op.Build()
    res = cq.Shape.cast(op.Shape())
    tris = []
    for f in res.Faces():
        vs, ts = f.tessellate(0.02, 0.1)
        for t in ts:
            tris.append([(vs[i].x, vs[i].y) for i in t])
    return tris


def _dim(ax, p0, p1, off, text, horiz=True, fs=7, col="k"):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        y = off
        ax.plot([x0, x0], [y0, y], lw=0.4, color=col); ax.plot([x1, x1], [y1, y], lw=0.4, color=col)
        ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=0.6, color=col))
        ax.text((x0 + x1) / 2, y + 0.8, text, ha="center", va="bottom", fontsize=fs, color=col)
    else:
        x = off
        ax.plot([x0, x], [y0, y0], lw=0.4, color=col); ax.plot([x1, x], [y1, y1], lw=0.4, color=col)
        ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=0.6, color=col))
        ax.text(x - 0.8, (y0 + y1) / 2, text, ha="right", va="center", fontsize=fs, color=col, rotation=90)


def draw(frame_shape, path_png, path_dxf=None):
    xc, yc = datum()
    fig = plt.figure(figsize=(23.4, 16.5))          # A2 landscape
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1], wspace=0.08, hspace=0.12)

    # ---------------------------------------------------------------- 1. frame, front view
    ax = fig.add_subplot(gs[:, 0])
    for z, col, lab in ((F.Z_FRONT + 0.05, "#9aa3ad", "feet plane"), (F.Z_SEAT - 0.05, "#5d6875", "seat")):
        for tri in section_polys(frame_shape, z):
            ax.add_patch(Polygon([uv(x, -y) for x, y in tri], closed=True, fc=col, ec=col, lw=0.05))
    # panel outline, view area, active area
    for rect, st, lab in ((F.PANEL, "-", "panel outline 164.90 x 100.00"), (F.VA, "--", "cover view area"),
                          (F.cutout_rect(), "-", "sheet window")):
        (u0, v0), (u1, v1) = uv(rect[0], rect[2]), uv(rect[1], rect[3])
        ax.plot([u0, u1, u1, u0, u0], [v0, v0, v1, v1, v0], st, lw=0.8,
                color={"panel outline 164.90 x 100.00": "b", "cover view area": "g", "sheet window": "r"}[lab])
    for h, (x, y) in F.HOLES.items():
        u, v = uv(x, y)
        ax.add_patch(Circle((u, v), F.PILOT_D / 2, fc="w", ec="k", lw=0.5))
        ax.text(u + 2.6, v + 2.6, h, fontsize=7)
    for f, (x, y) in F.FEET.items():
        u, v = uv(x, y)
        ax.add_patch(Circle((u, v), F.FOOT_HOLE / 2, fc="w", ec="r", lw=0.8))
        ax.text(u + 3, v - 5.5, f, fontsize=8, color="r")
    for p, (x, y) in F.PEG_POS.items():
        u, v = uv(x, y)
        ax.add_patch(Circle((u, v), F.PEG_D / 2, fc="#333", ec="k", lw=0.5))
        ax.text(u + 2, v + 2, p, fontsize=7)
    O = F.OUTER
    (ou0, ov0), (ou1, ov1) = uv(O[1], O[3]), uv(O[0], O[2])
    (pu0, pv0), (pu1, pv1) = uv(F.POCKET[1], F.POCKET[3]), uv(F.POCKET[0], F.POCKET[2])
    _dim(ax, (ou0, ov1), (ou1, ov1), ov1 + 14, "frame body %.2f" % (O[1] - O[0]))
    _dim(ax, (pu0, pv1), (pu1, pv1), ov1 + 7, "panel pocket %.2f (+0.5 deg draft, 0.8x45 lead-in)" % (F.POCKET[1] - F.POCKET[0]))
    _dim(ax, (ou0, ov0), (ou0, ov1), ou0 - 10, "frame body %.2f" % (O[3] - O[2]), horiz=False)
    _dim(ax, (pu1, pv0), (pu1, pv1), pu1 + 12, "pocket %.2f" % (F.POCKET[3] - F.POCKET[2]), horiz=False)
    fx = [uv(x, y)[0] for x, y in F.FEET.values()]
    fy = [uv(x, y)[1] for x, y in F.FEET.values()]
    _dim(ax, (min(fx), min(fy)), (max(fx), min(fy)), min(fy) - 14, "feet span %.1f" % (max(fx) - min(fx)))
    (tu0, tv0), (tu1, tv1) = uv(F.TR_X1, F.TR_Y1), uv(F.TR_X0, F.TR_Y0)
    _dim(ax, (tu0, tv0), (tu1, tv0), tv0 - 7, "tail pocket %.1f x %.1f, R%.0f" % (F.TR_X1 - F.TR_X0, F.TR_Y1 - F.TR_Y0, F.TROUGH_R))
    ax.set_aspect("equal"); ax.grid(True, lw=0.2, alpha=0.4)
    ax.set_title("Carrier frame - FRONT view (from in front of the oven), datum = sheet-window centre\n"
                 "light: feet plane Z %.2f, dark: panel seat Z %.2f; red = M4 stud holes (dia %.1f), H1-H9 PCB screw pilots dia %.1f"
                 % (F.Z_FRONT, F.Z_SEAT, F.FOOT_HOLE, F.PILOT_D), fontsize=10)
    ax.set_xlabel("u (mm, + = right as seen from the front)"); ax.set_ylabel("v (mm, + = up)")

    # ---------------------------------------------------------------- 2. front-sheet pattern
    ax2 = fig.add_subplot(gs[0, 1])
    co = F.cutout_rect()
    (cu0, cv0), (cu1, cv1) = uv(co[1], co[3]), uv(co[0], co[2])
    ax2.add_patch(FancyBboxPatch((cu0 + F.CUTOUT_R, cv0 + F.CUTOUT_R), cu1 - cu0 - 2 * F.CUTOUT_R,
                                 cv1 - cv0 - 2 * F.CUTOUT_R, boxstyle="round,pad=%.2f" % F.CUTOUT_R,
                                 fc="#e8eef5", ec="r", lw=1.0))
    rows = []
    for f, (x, y) in F.FEET.items():
        u, v = uv(x, y)
        ax2.add_patch(Circle((u, v), PEM_HOLE / 2, fc="w", ec="k", lw=0.8))
        ax2.text(u + 3, v + 2, f, fontsize=8)
        rows.append((f, "PEM FH-M4-15 stud, hole dia %.2f +0.08" % PEM_HOLE, u, v))
    if F.PEGS:
        for p, (x, y) in F.PEG_POS.items():
            u, v = uv(x, y)
            ax2.add_patch(Circle((u, v), PEG_HOLE / 2, fc="w", ec="b", lw=0.8))
            ax2.text(u + 2.5, v - 5, p, fontsize=8, color="b")
            rows.append((p, "locating hole dia %.1f +0.1" % PEG_HOLE, u, v))
    _dim(ax2, (cu0, cv1), (cu1, cv1), cv1 + 8, "window %.2f" % (cu1 - cu0))
    _dim(ax2, (cu1, cv0), (cu1, cv1), cu1 + 30, "window %.2f" % (cv1 - cv0), horiz=False)
    ax2.plot([0], [0], "k+", ms=12)
    ax2.text(1, 1, "datum (0,0)", fontsize=7)
    ax2.set_aspect("equal"); ax2.grid(True, lw=0.2, alpha=0.4)
    ax2.set_xlim(min(r[2] for r in rows) - 15, max(r[2] for r in rows) + 40)
    ax2.set_ylim(min(r[3] for r in rows) - 15, max(r[3] for r in rows) + 20)
    ax2.set_title("Oven front sheet (steel %.1f-1.5 mm), FRONT view: window = cover view area + %.1f/side, corners R%.1f\n"
                  "window %.2f x %.2f; hole pattern below (u, v from the window centre)"
                  % (F.OVEN_SHEET_T, F.CUTOUT_MARGIN, F.CUTOUT_R, cu1 - cu0, cv1 - cv0), fontsize=10)

    # ---------------------------------------------------------------- 3. table + z stack
    ax3 = fig.add_subplot(gs[1, 1]); ax3.axis("off")
    lines = ["%-4s %-44s u = %8.2f   v = %8.2f" % r for r in rows]
    gas = (F.PX1 - F.PX0 - 2 * F.GASKET_OUT_INSET, F.PY1 - F.PY0 - 2 * F.GASKET_OUT_INSET,
           F.VA[1] - F.VA[0] + 2 * F.GASKET_IN_MARGIN, F.VA[3] - F.VA[2] + 2 * F.GASKET_IN_MARGIN)
    zs = [
        "", "Z STACK (Z = 0 at the PCB back, - towards the oven front):",
        "  PCB back / boss tops / support ribs / outer wall top   Z  0.00",
        "  shelf back face                                      Z %6.2f" % F.Z_SHELF_BACK,
        "  shelf front face = sheet back (Formex %.2f)           Z %6.2f" % (F.SHEET_T, F.Z_SEAT),
        "  panel back                                           Z %6.2f" % F.Z_PANEL_BACK,
        "  cover glass front                                    Z %6.2f" % F.Z_GLASS,
        "  feet plane = oven sheet inner face (gasket %.1f -> %.2f) Z %6.2f" % (F.GASKET_T, F.GASKET_T * (1 - F.GASKET_COMP), F.Z_FRONT),
        "  tail-pocket walls top (outside the board)            Z %6.2f" % F.Z_TROUGH_TOP,
        "", "GASKET (not moulded): closed-cell silicone sponge %.1f mm, outer %.2f x %.2f, inner %.2f x %.2f,"
            % (F.GASKET_T, gas[0], gas[1], gas[2], gas[3]),
        "  centred on the window; PSA on the sheet side.",
        "", "PCB screws: 9x ISO 7049-C ST2.9x9.5 A2 into dia %.1f pilots, 0.3-0.4 Nm." % F.PILOT_D,
        "Mounting: 8x PEM FH-M4-15 (or ISO 13918 weld stud M4x15) + DIN 9021 M4 washer + ISO 10511 M4 nyloc, 0.6 Nm.",
        "Frame: PA6-GF30 heat-stabilised, UL94 V-0, GWFI 960 C. General tolerance ISO 20457 TG5; draft 1 deg (0.5 deg pocket).",
    ]
    ax3.text(0.0, 1.0, "HOLE TABLE (front view, mm)\n" + "\n".join(lines) + "\n" + "\n".join(zs),
             family="monospace", fontsize=9, va="top", transform=ax3.transAxes)
    fig.suptitle("Rev3.0 OVEN CONTROLLER - carrier frame, main dimensions and front-sheet pattern (READARK, 2026-11-13)",
                 fontsize=13)
    fig.savefig(path_png, dpi=110, bbox_inches="tight")
    plt.close(fig)

    if path_dxf:
        import ezdxf
        doc = ezdxf.new("R2010"); doc.units = 4
        msp = doc.modelspace()
        r = F.CUTOUT_R
        u0, u1, v0, v1 = cu0, cu1, cv0, cv1
        pts = [(u0 + r, v0, 0), (u1 - r, v0, 0.4142), (u1, v0 + r, 0), (u1, v1 - r, 0.4142), (u1 - r, v1, 0),
               (u0 + r, v1, 0.4142), (u0, v1 - r, 0), (u0, v0 + r, 0.4142)]
        msp.add_lwpolyline([(p[0], p[1], 0, 0, p[2]) for p in pts], format="xyseb", close=True,
                           dxfattribs={"layer": "CUTOUT"})
        for name, _, u, v in rows:
            d = PEM_HOLE if name.startswith("F") else PEG_HOLE
            msp.add_circle((u, v), d / 2, dxfattribs={"layer": "HOLES"})
            msp.add_text(name, dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((u + 3, v + 3))
        doc.saveas(path_dxf)
    return rows
