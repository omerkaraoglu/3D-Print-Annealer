"""2D section drawings (matplotlib) of the assembly: every part is cut by a plane with
BRepAlgoAPI_Common(solid, plane face), the section faces are tessellated and filled.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir

AX = {"x": (0, (0, 1, 2)), "y": (1, (0, 1, 2)), "z": (2, (0, 1, 2))}


def cut_faces(shape, axis, value):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    bb = s.BoundingBox()
    lo, hi = {"x": (bb.xmin, bb.xmax), "y": (bb.ymin, bb.ymax), "z": (bb.zmin, bb.zmax)}[axis]
    if value < lo - 1e-6 or value > hi + 1e-6:
        return []
    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    p = {"x": (value, 0, 0), "y": (0, value, 0), "z": (0, 0, value)}[axis]
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*p), gp_Dir(*n)), -2000, 2000, -2000, 2000).Face()
    op = BRepAlgoAPI_Common(s.wrapped, face)
    op.Build()
    if not op.IsDone():
        return []
    res = cq.Shape.cast(op.Shape())
    tris = []
    for f in res.Faces():
        vs, ts = f.tessellate(0.01, 0.1)
        for t in ts:
            tris.append([(vs[i].x, vs[i].y, vs[i].z) for i in t])
    return tris


def section(parts, axis, value, fname, proj, title, xlim=None, ylim=None, dims=(), notes=(), figsize=(16, 7),
            insets=()):
    """parts: [(label, shape, rgb)]; proj: function (x, y, z) -> (h, v) screen coordinates.
    dims: [(p0, p1, offset, text, horiz)] in screen coords; insets: [(xlim, ylim, rect=[l, b, w, h])]."""
    fig, ax = plt.subplots(figsize=figsize)
    cache = []
    for lbl, shp, rgb in parts:
        tris = cut_faces(shp, axis, value)
        if not tris:
            continue
        polys = [[proj(*p) for p in t] for t in tris]
        cache.append((polys, rgb, lbl))
    handles = {}

    def paint(a):
        for polys, rgb, lbl in cache:
            for pp in polys:
                a.add_patch(Polygon(pp, closed=True, fc=rgb, ec=rgb, lw=0.05))
            handles[lbl] = rgb
    paint(ax)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.2, alpha=0.4)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    if not xlim or not ylim:
        ax.autoscale_view()
    for (p0, p1, off, text, horiz) in dims:
        _dim(ax, p0, p1, off, text, horiz)
    for (x, y, txt) in notes:
        ax.annotate(txt, (x, y), fontsize=7, xytext=(8, 8), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", lw=0.4), bbox=dict(fc="w", ec="none", alpha=0.8, pad=0.5))
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=c, label=l) for l, c in handles.items()], fontsize=7, loc="upper right",
              ncol=2, framealpha=0.9)
    for (xl, yl, rect) in insets:
        ia = ax.inset_axes(rect)
        paint(ia)
        ia.set_xlim(*xl); ia.set_ylim(*yl); ia.set_aspect("equal"); ia.grid(True, lw=0.2, alpha=0.4)
        ia.tick_params(labelsize=6)
        for (p0, p1, off, text, horiz) in dims:
            if xl[0] <= p0[0] <= xl[1] and yl[0] <= p0[1] <= yl[1]:
                _dim(ia, p0, p1, off, text, horiz, fs=6)
        ax.indicate_inset_zoom(ia, edgecolor="0.3")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(fname, dpi=140)
    plt.close(fig)
    return fname


def _dim(ax, p0, p1, off, text, horiz=True, fs=7):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        ax.plot([x0, x0], [y0, off], lw=0.3, color="m"); ax.plot([x1, x1], [y1, off], lw=0.3, color="m")
        ax.annotate("", (x0, off), (x1, off), arrowprops=dict(arrowstyle="<->", lw=0.5, color="m"))
        ax.text((x0 + x1) / 2, off, text, ha="center", va="bottom", fontsize=fs, color="m")
    else:
        ax.plot([x0, off], [y0, y0], lw=0.3, color="m"); ax.plot([x1, off], [y1, y1], lw=0.3, color="m")
        ax.annotate("", (off, y0), (off, y1), arrowprops=dict(arrowstyle="<->", lw=0.5, color="m"))
        ax.text(off, (y0 + y1) / 2, " " + text, ha="left", va="center", fontsize=fs, color="m")
