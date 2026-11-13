"""Dimensioned drawing (PNG) of the frame v2 and the oven front-sheet pattern (PNG + DXF), from the STEP + params.

  <venv>/Scripts/python.exe drawing_v2.py [--v1] [--frame f.step] [--params p.json]

Views are FRONT views (as seen from in front of the oven): u = -(x - x_c) to the right, v = -(y - y_c) up,
datum = centre of the sheet window (cover view area + CUTOUT_MARGIN per side), as v1 drawing.py.
PNG: frame front view (flange-plane and seat sections from the STEP), overall / body / pocket / flange / stud
pattern dimensions; sheet pattern; stud-hole table (PEM stud from the params, default FH-M4-18: round dia
4.22 +0.08/-0 holes in the sheet even where the frame has slots); peg holes round, or a slot (PEG_SLOT); Z stack.
DXF (R2010, mm): layers CUTOUT (window, R), HOLES (stud + peg holes), TEXT, FLANGE_REF (flange outline at the
sheet, from the STEP, reference only), BODY_REF (frame body outline at the sheet, reference only).
Output: Rev3.0_Frame_Drawing_v2.png in the renders folder, Rev3.0_FrontSheet_Pattern_v2.dxf in Mechanical/Rev3.0_Frame
(--v1: both into renders_v2/v1_regression/ with a v1check name).
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
from matplotlib.patches import FancyBboxPatch, Circle, Polygon

import common_v2 as C

PEM_HOLE = C.PEM_HOLE
PEM_TOL = "+0.08/-0"


def section_polys(shape, z):
    """triangles (abs x, y) and face loops (abs) of the section of `shape` by Z = z"""
    sec = C.plane_section(shape, "z", z)
    if sec is None:
        return [], []
    tris, loops = [], []
    for f in sec.Faces():
        vs, ts = f.tessellate(0.02, 0.1)
        for t in ts:
            tris.append([(vs[i].x, -vs[i].y) for i in t])
        loops.append(C.face_loops_abs(f, 0.005))
    return tris, loops


def _dim(ax, p0, p1, off, text, horiz=True, fs=7, col="k"):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        ax.plot([x0, x0], [y0, off], lw=0.4, color=col); ax.plot([x1, x1], [y1, off], lw=0.4, color=col)
        ax.annotate("", (x0, off), (x1, off), arrowprops=dict(arrowstyle="<->", lw=0.6, color=col))
        ax.text((x0 + x1) / 2, off + 0.8, text, ha="center", va="bottom", fontsize=fs, color=col)
    else:
        ax.plot([x0, off], [y0, y0], lw=0.4, color=col); ax.plot([x1, off], [y1, y1], lw=0.4, color=col)
        ax.annotate("", (off, y0), (off, y1), arrowprops=dict(arrowstyle="<->", lw=0.6, color=col))
        ax.text(off - 0.8, (y0 + y1) / 2, text, ha="right", va="center", fontsize=fs, color=col, rotation=90)


def stadium_uv(D, c_abs, axis_abs, L, W, n=16):
    """closed outline (front-view u, v) of a slot L x W centred at c_abs with its axis along axis_abs (KiCad abs)"""
    cu, cv = D.uv(*c_abs)
    au, av = -axis_abs[0], -axis_abs[1]                 # u = -x, v = -y
    h, r = (L - W) / 2, W / 2
    pts = []
    for end, sgn in ((1, 1), (-1, -1)):
        ex, ey = cu + end * h * au, cv + end * h * av
        base = math.atan2(av, au) if end == 1 else math.atan2(-av, -au)
        for k in range(n + 1):
            t = base - math.pi / 2 + math.pi * k / n
            pts.append((ex + r * math.cos(t), ey + r * math.sin(t)))
    return pts


def dxf_slot(msp, D, c_abs, axis_abs, L, W, layer):
    """stadium as an LWPOLYLINE with two 180 deg bulges (front-view u, v)"""
    cu, cv = D.uv(*c_abs)
    au, av = -axis_abs[0], -axis_abs[1]
    h, r = (L - W) / 2, W / 2
    nu, nv = -av * r, au * r                           # left normal
    p1 = (cu - h * au + nu, cv - h * av + nv)
    p2 = (cu + h * au + nu, cv + h * av + nv)
    p3 = (cu + h * au - nu, cv + h * av - nv)
    p4 = (cu - h * au - nu, cv - h * av - nv)
    pts = [p1, p2, p3, p4]
    area = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
    b = 1.0 if area > 0 else -1.0                      # half circles bulge outwards for either winding
    msp.add_lwpolyline([(p1[0], p1[1], 0, 0, 0), (p2[0], p2[1], 0, 0, b), (p3[0], p3[1], 0, 0, 0),
                        (p4[0], p4[1], 0, 0, b)], format="xyseb", close=True, dxfattribs={"layer": layer})


def outer_outline(loops):
    """largest outer loop among the section faces (abs)"""
    best = None
    for fl in loops:
        o = fl[0]
        a = 0.5 * abs(np.dot(o[:, 0], np.roll(o[:, 1], -1)) - np.dot(o[:, 1], np.roll(o[:, 0], -1)))
        if best is None or a > best[0]:
            best = (a, o)
    return best[1] if best else None


def draw(ctx, path_png, path_dxf=None, log=C.log):
    D, fr = ctx.D, ctx.frame
    uv = D.uv
    fig = plt.figure(figsize=(23.4, 16.5))          # A2 landscape
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1], wspace=0.08, hspace=0.12)
    tag = "v2" if not ctx.v1 else "v1 (regression run of the v2 toolchain)"

    # ------------------------------------------------------------------ 1. frame, front view
    ax = fig.add_subplot(gs[:, 0])
    flange_tris, flange_loops = section_polys(fr, D.Z_FRONT + 0.05)
    seat_tris, _ = section_polys(fr, D.Z_SEAT - 0.05)
    for tris, col in ((flange_tris, "#9aa3ad"), (seat_tris, "#5d6875")):
        for tri in tris:
            ax.add_patch(Polygon([uv(x, y) for x, y in tri], closed=True, fc=col, ec=col, lw=0.35))
    for loops in flange_loops:
        for l in loops:
            q = np.array([uv(x, y) for x, y in l])
            ax.plot(q[:, 0], q[:, 1], "k-", lw=0.4)
    for rect, st, col in ((D.PANEL, "-", "b"), (D.VA, "--", "g"), (D.cutout_rect(), "-", "r")):
        (u0, v0), (u1, v1) = uv(rect[0], rect[2]), uv(rect[1], rect[3])
        ax.plot([u0, u1, u1, u0, u0], [v0, v0, v1, v1, v0], st, lw=0.8, color=col)
    for h, (x, y) in D.HOLES.items():
        u, v = uv(x, y)
        ax.add_patch(Circle((u, v), D.PILOT_D / 2, fc="w", ec="k", lw=0.5))
        ax.text(u + 2.6, v + 2.6, h, fontsize=7)
    for f, (x, y) in D.STUDS.items():
        u, v = uv(x, y)
        sl = D.SLOTS.get(f)
        if sl:                                             # stud slot at any angle (e.g. radial from a datum)
            ax.add_patch(Polygon(stadium_uv(D, (x, y), sl["axis"], sl["len"], sl["w"]), closed=True, fc="w", ec="r",
                                 lw=0.8))
        else:
            ax.add_patch(Circle((u, v), D.STUD_HOLE_D / 2, fc="w", ec="r", lw=0.8))
        ax.text(u + 3, v - 5.5, f, fontsize=8, color="r")
    for p, (x, y) in D.PEGS.items():
        u, v = uv(x, y)
        ax.add_patch(Circle((u, v), D.PEG_D / 2, fc="#333", ec="k", lw=0.5))
        ax.text(u + 2, v + 2, p, fontsize=7)
    fo = outer_outline(flange_loops)
    fu = np.array([uv(x, y) for x, y in fo]) if fo is not None else None
    O, PK = D.OUTER, D.POCKET
    (ou0, ov0), (ou1, ov1) = uv(O[1], O[3]), uv(O[0], O[2])
    (pu0, pv0), (pu1, pv1) = uv(PK[1], PK[3]), uv(PK[0], PK[2])
    top = max(ov1, fu[:, 1].max() if fu is not None else ov1)
    left = min(ou0, fu[:, 0].min() if fu is not None else ou0)
    if fu is not None:
        _dim(ax, (fu[:, 0].min(), top), (fu[:, 0].max(), top), top + 21,
             "overall at the sheet %.2f" % (fu[:, 0].max() - fu[:, 0].min()))
        _dim(ax, (left, fu[:, 1].min()), (left, fu[:, 1].max()), left - 17,
             "overall %.2f" % (fu[:, 1].max() - fu[:, 1].min()), horiz=False)
    _dim(ax, (ou0, ov1), (ou1, ov1), top + 14, "frame body %.2f" % (O[1] - O[0]))
    _dim(ax, (pu0, pv1), (pu1, pv1), top + 7, "panel pocket %.2f (+%.1f deg draft)" % (PK[1] - PK[0], D.DRAFT_LOC))
    _dim(ax, (ou0, ov0), (ou0, ov1), left - 10, "frame body %.2f" % (O[3] - O[2]), horiz=False)
    _dim(ax, (pu0, pv0), (pu0, pv1), pu0 + 9, "pocket %.2f" % (PK[3] - PK[2]), horiz=False)
    if D.FLANGE_W > 0 and fu is not None:
        _dim(ax, (ou1, 0), (fu[:, 0].max(), 0), 4, "flange %.1f" % (fu[:, 0].max() - ou1), fs=7, col="b")
    su = [uv(x, y) for x, y in D.STUDS.values()]
    us, vs = [p[0] for p in su], [p[1] for p in su]
    bottom = min(vs + ([fu[:, 1].min()] if fu is not None else []))
    _dim(ax, (min(us), min(vs)), (max(us), min(vs)), bottom - 10, "stud pattern %.2f" % (max(us) - min(us)))
    _dim(ax, (max(us), min(vs)), (max(us), max(vs)), max(us) + 14, "stud pattern %.2f" % (max(vs) - min(vs)),
         horiz=False)
    if D.TROUGH:
        (tu0, tv0), (tu1, tv1) = uv(D.TROUGH[1], D.TROUGH[3]), uv(D.TROUGH[0], D.TROUGH[2])
        _dim(ax, (tu0, tv0), (tu1, tv0), tv0 + 3, "tail pocket %.1f x %.1f" % (
            D.TROUGH[1] - D.TROUGH[0], D.TROUGH[3] - D.TROUGH[2]))
    ax.set_aspect("equal"); ax.grid(True, lw=0.2, alpha=0.4)
    ax.set_title("Carrier frame %s - FRONT view (from in front of the oven), datum = sheet-window centre\n"
                 "light: flange / sheet plane Z %.2f, dark: panel seat Z %.2f; red = stud holes dia %.2f%s, H1-H9 PCB "
                 "screw pilots dia %.1f" % (tag, D.Z_FRONT, D.Z_SEAT, D.STUD_HOLE_D,
                                            (" (slots %.2f long)" % max(s["len"] for s in D.SLOTS.values()))
                                            if D.SLOTS else "", D.PILOT_D), fontsize=10)
    ax.set_xlabel("u (mm, + = right as seen from the front)"); ax.set_ylabel("v (mm, + = up)")

    # ------------------------------------------------------------------ 2. front-sheet pattern
    ax2 = fig.add_subplot(gs[0, 1])
    co = D.cutout_rect()
    (cu0, cv0), (cu1, cv1) = uv(co[1], co[3]), uv(co[0], co[2])
    ax2.add_patch(FancyBboxPatch((cu0 + D.CUTOUT_R, cv0 + D.CUTOUT_R), cu1 - cu0 - 2 * D.CUTOUT_R,
                                 cv1 - cv0 - 2 * D.CUTOUT_R, boxstyle="round,pad=%.2f" % D.CUTOUT_R,
                                 fc="#e8eef5", ec="r", lw=1.0))
    if fu is not None:
        ax2.plot(np.append(fu[:, 0], fu[0, 0]), np.append(fu[:, 1], fu[0, 1]), "-", color="0.6", lw=0.6)
    rows = []
    for f, (x, y) in D.STUDS.items():
        u, v = uv(x, y)
        ax2.add_patch(Circle((u, v), PEM_HOLE / 2, fc="w", ec="k", lw=0.8))
        ax2.text(u + 3, v + 2, f, fontsize=8)
        rows.append((f, "%s stud, hole dia %.2f %s" % (D.STUD_SPEC, PEM_HOLE, PEM_TOL), u, v))
    hole = D.PEG_D + C.PEG_HOLE_CLR
    for p, (x, y) in D.PEGS.items():
        u, v = uv(x, y)
        ps = D.PEG_SLOTS.get(p)
        if ps:
            ax2.add_patch(Polygon(stadium_uv(D, (x, y), ps["axis"], ps["len"], hole), closed=True, fc="w", ec="b",
                                  lw=0.8))
            ang = math.degrees(math.atan2(ps["axis"][1], ps["axis"][0]))
            what = "locating slot %.2f x %.2f %s +0.1/-0" % (
                hole, ps["len"], "along X" if abs(math.sin(math.radians(ang))) < 1e-3 else
                "along Y" if abs(math.cos(math.radians(ang))) < 1e-3 else "at %.1f deg (abs)" % ang)
        else:
            ax2.add_patch(Circle((u, v), hole / 2, fc="w", ec="b", lw=0.8))
            what = "locating hole dia %.1f +0.1/-0" % hole
        ax2.text(u + 2.5, v - 5, p, fontsize=8, color="b")
        rows.append((p, what, u, v))
    _dim(ax2, (cu0, cv1), (cu1, cv1), cv1 + 8, "window %.2f" % (cu1 - cu0))
    _dim(ax2, (cu1, cv0), (cu1, cv1), cu1 + 30, "window %.2f" % (cv1 - cv0), horiz=False)
    ax2.plot([0], [0], "k+", ms=12)
    ax2.text(1, 1, "datum (0,0)", fontsize=7)
    ax2.set_aspect("equal"); ax2.grid(True, lw=0.2, alpha=0.4)
    ax2.set_xlim(min(r[2] for r in rows) - 15, max(r[2] for r in rows) + 40)
    ax2.set_ylim(min(r[3] for r in rows) - 15, max(r[3] for r in rows) + 20)
    ax2.set_title("Oven front sheet (steel %.1f mm), FRONT view: window = cover view area + %.1f/side, R%.1f; "
                  "grey = flange outline (ref.)\nwindow %.2f x %.2f; hole pattern below (u, v from the window centre)"
                  % (D.OVEN_SHEET_T, D.CUTOUT_MARGIN, D.CUTOUT_R, cu1 - cu0, cv1 - cv0), fontsize=10)

    # ------------------------------------------------------------------ 3. table + Z stack
    ax3 = fig.add_subplot(gs[1, 1]); ax3.axis("off")
    lines = ["%-5s %-46s u = %8.2f   v = %8.2f" % r for r in rows]
    gas = (D.PX1 - D.PX0 - 2 * D.GASKET_OUT_INSET, D.PY1 - D.PY0 - 2 * D.GASKET_OUT_INSET,
           D.VA[1] - D.VA[0] + 2 * D.GASKET_IN_MARGIN, D.VA[3] - D.VA[2] + 2 * D.GASKET_IN_MARGIN)
    zl = lambda v: ("%6.2f" % v) if v is not None else "   n/a"
    zs = [
        "", "Z STACK (Z = 0 at the PCB back, - towards the oven front):",
        "  PCB back / boss tops / support ribs / wall top           Z %s" % zl(D.Z_PCB),
        "  shelf back face                                          Z %s" % zl(D.Z_SHELF_BACK),
        "  shelf front face = sheet back (Formex %.2f)               Z %s" % (D.SHEET_T, zl(D.Z_SEAT)),
        "  panel back                                               Z %s" % zl(D.Z_PANEL_BACK),
        "  stud tube top = washer seat                              Z %s" % zl(D.Z_STUD_TOP),
        "  flange back face                                         Z %s" % zl(D.Z_FLANGE_BACK),
        "  cover glass front                                        Z %s" % zl(D.Z_GLASS),
        "  flange front = oven sheet inner face (gasket %.1f -> %.2f) Z %s" % (
            D.GASKET_T, D.GASKET_T * (1 - D.GASKET_COMP), zl(D.Z_FRONT)),
        "  tail-pocket walls top (outside the board)                Z %s" % zl(D.Z_TROUGH_TOP),
        "", "GASKET (not moulded): closed-cell silicone sponge %.1f mm, outer %.2f x %.2f, inner %.2f x %.2f,"
            % (D.GASKET_T, gas[0], gas[1], gas[2], gas[3]),
        "  centred on the window; PSA on the sheet side.",
        "", "PCB screws: %dx ISO 7049-C ST2.9x9.5 A2 into dia %.1f pilots, 0.3-0.4 Nm." % (len(D.HOLES), D.PILOT_D),
        "Mounting: %dx %s + DIN 9021 M4 washer + ISO 10511 M4 nyloc, 0.6 Nm; stud holes in the frame dia %.2f%s."
        % (len(D.STUDS), D.STUD_SPEC, D.STUD_HOLE_D,
           (" (slots %.2f long)" % max(s["len"] for s in D.SLOTS.values())) if D.SLOTS else ""),
        "Frame: PA6-GF30 heat-stabilised, UL94 V-0, GWFI 960 C. General tolerance ISO 20457 TG5; draft %.1f deg (%.1f deg pocket)."
        % (D.DRAFT, D.DRAFT_LOC),
    ]
    ax3.text(0.0, 1.0, "HOLE TABLE (front view, mm, datum = window centre)\n" + "\n".join(lines) + "\n" + "\n".join(zs),
             family="monospace", fontsize=9, va="top", transform=ax3.transAxes)
    fig.suptitle("Rev3.0 OVEN CONTROLLER - carrier frame %s, main dimensions and front-sheet pattern (READARK)" % tag,
                 fontsize=13)
    fig.savefig(path_png, dpi=110, bbox_inches="tight")
    plt.close(fig)

    if path_dxf:
        import ezdxf
        doc = ezdxf.new("R2010"); doc.units = 4
        for name, col in (("CUTOUT", 1), ("HOLES", 7), ("TEXT", 3), ("FLANGE_REF", 8), ("BODY_REF", 9)):
            doc.layers.add(name, color=col)
        msp = doc.modelspace()
        r = D.CUTOUT_R
        u0, u1, v0, v1 = cu0, cu1, cv0, cv1
        b = 0.41421356                       # bulge of a 90 deg arc
        pts = [(u0 + r, v0, 0), (u1 - r, v0, b), (u1, v0 + r, 0), (u1, v1 - r, b), (u1 - r, v1, 0),
               (u0 + r, v1, b), (u0, v1 - r, 0), (u0, v0 + r, b)]
        msp.add_lwpolyline([(p[0], p[1], 0, 0, p[2]) for p in pts], format="xyseb", close=True,
                           dxfattribs={"layer": "CUTOUT"})
        for name, _, u, v in rows:
            ps = D.PEG_SLOTS.get(name) if name in D.PEGS else None
            if ps:
                dxf_slot(msp, D, D.PEGS[name], ps["axis"], ps["len"], hole, "HOLES")
            else:
                d = PEM_HOLE if name in D.STUDS else hole
                msp.add_circle((u, v), d / 2, dxfattribs={"layer": "HOLES"})
            msp.add_text(name, dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((u + 3, v + 3))
        if fu is not None:
            msp.add_lwpolyline([tuple(p) for p in fu[::2]], close=True, dxfattribs={"layer": "FLANGE_REF"})
        (bu0, bv0), (bu1, bv1) = uv(O[1], O[3]), uv(O[0], O[2])
        msp.add_lwpolyline([(bu0, bv0), (bu1, bv0), (bu1, bv1), (bu0, bv1)], close=True,
                           dxfattribs={"layer": "BODY_REF"})
        msp.add_text("datum = window centre; front view (u right, v up); stud holes dia %.2f %s for %s" % (
            PEM_HOLE, PEM_TOL, D.STUD_SPEC), dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((cu0, cv0 - 30))
        doc.saveas(path_dxf)
    log("  drawing %s%s" % (os.path.basename(path_png), (", " + os.path.basename(path_dxf)) if path_dxf else ""))
    return {"hole_table_uv": [{"name": r[0], "what": r[1], "u": round(r[2], 3), "v": round(r[3], 3)} for r in rows],
            "window": [round(cu1 - cu0, 3), round(cv1 - cv0, 3)],
            "overall_at_sheet": [round(fu[:, 0].max() - fu[:, 0].min(), 2), round(fu[:, 1].max() - fu[:, 1].min(), 2)]
            if fu is not None else None}


def run(ctx, log=C.log):
    os.makedirs(ctx.imgdir, exist_ok=True)
    png = os.path.join(ctx.imgdir, "Rev3.0_Frame_Drawing_v1check.png" if ctx.v1 else "Rev3.0_Frame_Drawing_v2.png")
    res = draw(ctx, png, ctx.dxf_path, log)
    res["png"], res["dxf"] = png, ctx.dxf_path
    return res


if __name__ == "__main__":
    run(C.Context(sys.argv[1:]))
