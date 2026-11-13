"""Shared helpers for the Rev3.0 parametric 3D models (CadQuery).

KiCad conventions used by every model:
  * millimetres, origin = footprint origin, +Z up from the board surface
  * model X = footprint x, model Y = -footprint y (KiCad footprints are y-down)
  * pins / terminals are separate solids tagged "pin:<pad number>" so that
    verify() can compare their XY centres with the footprint pads (pads.json,
    written by dump_pads.py with KiCad's Python).

Outputs:
  STEP  -> KiCad/ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/<name>.step
  WRL   -> same folder, scaled by 1/2.54 (KiCad VRML unit = 0.1 inch)
  PNG   -> $MODELS3D_RENDER_DIR (default: ./renders), iso + top view with the pads
  JSON  -> ./out/<name>.json  (bounding box and the pin-vs-pad table)
"""
import json
import math
import os
import sys

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES_DIR = os.path.normpath(os.path.join(
    HERE, r"..\..\..\..\KiCad\ComponentsLibrary\User Created\Rev3\Rev3.3dshapes"))
RENDER_DIR = os.environ.get("MODELS3D_RENDER_DIR", os.path.join(HERE, "renders"))
OUT_DIR = os.path.join(HERE, "out")
MODEL_PATH_FMT = "${KIPRJMOD}/../ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/%s.step"

COL = {
    "black": (0.10, 0.10, 0.10),
    "ferrite": (0.22, 0.22, 0.24),
    "copper": (0.80, 0.45, 0.20),
    "tin": (0.82, 0.82, 0.84),
    "gold": (0.85, 0.68, 0.25),
    "steel": (0.70, 0.70, 0.72),
    "alu_black": (0.13, 0.13, 0.15),
    "ivory": (0.93, 0.90, 0.80),
    "green": (0.30, 0.70, 0.35),
    "film_blue": (0.25, 0.40, 0.75),
    "film_grey": (0.55, 0.55, 0.58),
    "glass": (0.70, 0.82, 0.88),
    "screen": (0.05, 0.07, 0.12),
    "polyimide": (0.85, 0.55, 0.10),
    "white": (0.95, 0.95, 0.95),
    "wire_red": (0.75, 0.10, 0.10),
    "wire_blue": (0.10, 0.25, 0.75),
    "wire_black": (0.12, 0.12, 0.12),
}


# ---------------------------------------------------------------- primitives
def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from min/max coordinates (model frame)."""
    return (cq.Workplane("XY")
            .box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))


def cyl(xc, yc, z0, z1, d):
    """Vertical cylinder of diameter d from z0 to z1."""
    return (cq.Workplane("XY").workplane(offset=z0).center(xc, yc)
            .circle(d / 2).extrude(z1 - z0))


def fillet_edges(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


# ---------------------------------------------------------------- model
class Model:
    def __init__(self, name, footprint, descr=""):
        self.name = name
        self.footprint = footprint
        self.descr = descr
        self.parts = []        # (label, Workplane, colour key)

    def add(self, label, wp, colour):
        self.parts.append((label, wp, colour))

    def pin(self, num, wp, colour="tin"):
        self.parts.append(("pin:%s" % num, wp, colour))

    def shapes(self):
        return [(lbl, wp.val() if isinstance(wp, cq.Workplane) else wp, c) for lbl, wp, c in self.parts]


def _assembly(model, scale=1.0):
    assy = cq.Assembly(name=model.name)
    for i, (lbl, shp, c) in enumerate(model.shapes()):
        if scale != 1.0:
            shp = shp.scale(scale)
        safe = lbl.replace(":", "_").replace(" ", "_")
        assy.add(shp, name="%s_%d" % (safe, i), color=cq.Color(*COL[c]))
    return assy


def export(model, wrl=True):
    os.makedirs(SHAPES_DIR, exist_ok=True)
    step = os.path.join(SHAPES_DIR, model.name + ".step")
    _assembly(model).save(step, exportType="STEP")
    out = {"step": step}
    if wrl:
        p = os.path.join(SHAPES_DIR, model.name + ".wrl")
        try:
            _assembly(model, 1 / 2.54).save(p, exportType="VRML")
            out["wrl"] = p
        except Exception as e:  # pragma: no cover
            out["wrl_error"] = str(e)
    return out


# ---------------------------------------------------------------- checks
def bbox(model):
    comp = cq.Compound.makeCompound([s for _, s, _ in model.shapes()])
    b = comp.BoundingBox()
    return {"xmin": b.xmin, "xmax": b.xmax, "ymin": b.ymin, "ymax": b.ymax, "zmin": b.zmin, "zmax": b.zmax}


def pin_centres(model):
    res = []
    for lbl, s, _ in model.shapes():
        if lbl.startswith("pin:"):
            b = s.BoundingBox()
            res.append((lbl[4:], (b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2, b.zmin))
    return res


def verify(model, tol=0.05):
    pads = json.load(open(os.path.join(HERE, "pads.json")))[model.footprint]["pads"]
    pins = pin_centres(model)
    rows, ok = [], True
    used = set()
    for pad in pads:
        px, py = pad["x"], -pad["y"]   # pad in model frame
        cands = [(i, p) for i, p in enumerate(pins) if p[0] == pad["num"] and i not in used]
        if not cands:
            rows.append({"pad": pad["num"], "pad_xy": [px, py], "pin_xy": None, "d": None, "ok": False})
            ok = False
            continue
        i, p = min(cands, key=lambda c: math.hypot(c[1][1] - px, c[1][2] - py))
        used.add(i)
        d = math.hypot(p[1] - px, p[2] - py)
        good = d <= tol
        ok &= good
        rows.append({"pad": pad["num"], "pad_xy": [round(px, 3), round(py, 3)],
                     "pin_xy": [round(p[1], 3), round(p[2], 3)], "d": round(d, 3), "ok": good})
    extra = [p[0] for i, p in enumerate(pins) if i not in used]
    return {"ok": ok and not extra, "rows": rows, "unmatched_pins": extra}


def table(v):
    lines = ["| pad | pad (x, y) model | pin centre (x, y) | delta | ok |", "|---|---|---|---|---|"]
    for r in v["rows"]:
        lines.append("| %s | %s | %s | %s | %s |" % (
            r["pad"], "(%.3f, %.3f)" % tuple(r["pad_xy"]),
            "-" if r["pin_xy"] is None else "(%.3f, %.3f)" % tuple(r["pin_xy"]),
            "-" if r["d"] is None else "%.3f" % r["d"], "yes" if r["ok"] else "NO"))
    return "\n".join(lines)


# ---------------------------------------------------------------- render
def render(model, extra_lines=None, views=("iso", "top", "front"), fname=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    os.makedirs(RENDER_DIR, exist_ok=True)
    tris, cols = [], []
    light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    b = bbox(model)
    size = max(b["xmax"] - b["xmin"], b["ymax"] - b["ymin"], b["zmax"] - b["zmin"])
    tol = max(0.02, size / 400)
    for lbl, s, c in model.shapes():
        vs, ts = s.tessellate(tol, 0.3)
        V = np.array([[v.x, v.y, v.z] for v in vs])
        base = np.array(COL[c])
        for t in ts:
            p = V[list(t)]
            n = np.cross(p[1] - p[0], p[2] - p[0]); ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            n /= ln
            k = 0.35 + 0.65 * abs(float(n @ light))
            tris.append(p); cols.append(np.clip(base * k, 0, 1))
    pads = json.load(open(os.path.join(HERE, "pads.json"))).get(model.footprint, {}).get("pads", [])

    fig = plt.figure(figsize=(6 * len(views), 6))
    view_def = {"iso": (28, -60), "top": (90, -90), "front": (0, -90), "side": (0, 0), "iso2": (25, 120)}
    cx, cy, cz = (b["xmin"] + b["xmax"]) / 2, (b["ymin"] + b["ymax"]) / 2, (b["zmin"] + b["zmax"]) / 2
    h = size * 0.55
    for k, v in enumerate(views):
        ax = fig.add_subplot(1, len(views), k + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))
        for pad in pads:   # pads in red at z=0
            x, y, w, hh = pad["x"], -pad["y"], pad["w"], pad["h"]
            ax.plot([x - w / 2, x + w / 2, x + w / 2, x - w / 2, x - w / 2],
                    [y - hh / 2, y - hh / 2, y + hh / 2, y + hh / 2, y - hh / 2], [0] * 5, "r-", lw=0.8)
        for ln in (extra_lines or []):
            xs, ys, zs = zip(*ln)
            ax.plot(xs, ys, zs, "m-", lw=0.8)
        ax.set_xlim(cx - h, cx + h); ax.set_ylim(cy - h, cy + h); ax.set_zlim(cz - h, cz + h)
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
        ax.view_init(*view_def[v])
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.set_title("%s - %s" % (model.name, v), fontsize=9)
    fig.tight_layout()
    path = os.path.join(RENDER_DIR, (fname or model.name) + ".png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def render_ortho(parts, view, fname, clip=None, title="", hlines=(), vlines=(), notes=(), width_in=14, dpi=130):
    """Orthographic 2D render with true aspect ratio (painter's algorithm), for fit checks.

    parts : list of (label, cq Shape/Workplane, colour key)
    view  : "front" = look along +Y (screen x = X, y = Z); "back" = look along -Y (screen x = -X);
            "side"  = look along -X (screen x = Y, y = Z);   "top" = look along -Z (x = X, y = Y)
    clip  : (x0, x1, y0, y1, z0, z1) box in model coordinates; shapes are intersected with it
    hlines/vlines : (value, label, style) reference lines in screen coordinates
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import numpy as np

    os.makedirs(RENDER_DIR, exist_ok=True)
    proj = {"front": (lambda P: (P[:, 0], P[:, 2], P[:, 1]), np.array([0, -1.0, 0])),
            "back": (lambda P: (-P[:, 0], P[:, 2], -P[:, 1]), np.array([0, 1.0, 0])),
            "side": (lambda P: (P[:, 1], P[:, 2], P[:, 0]), np.array([1.0, 0, 0])),
            "top": (lambda P: (P[:, 0], P[:, 1], -P[:, 2]), np.array([0, 0, 1.0]))}[view]
    light = np.array([0.35, -0.55, 0.75]); light /= np.linalg.norm(light)
    cbox = None
    if clip is not None:
        x0, x1, y0, y1, z0, z1 = clip
        cbox = box(x0, x1, y0, y1, z0, z1).val()
    polys, cols, depth = [], [], []
    for lbl, s, c in parts:
        if isinstance(s, cq.Workplane):
            s = s.val()
        if cbox is not None:
            bb = s.BoundingBox()
            if bb.xmax < x0 or bb.xmin > x1 or bb.ymax < y0 or bb.ymin > y1 or bb.zmax < z0 or bb.zmin > z1:
                continue
            try:
                s = s.intersect(cbox)
            except Exception:
                continue
            if s is None or not s.Faces():
                continue
        vs, ts = s.tessellate(0.05, 0.2)
        if not ts:
            continue
        V = np.array([[v.x, v.y, v.z] for v in vs])
        T = np.array([list(t) for t in ts])
        P = V[T]                                       # (n, 3, 3)
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
        P, n = P[ok], n[ok] / ln[ok, None]
        k = 0.35 + 0.65 * np.abs(n @ light)
        base = np.array(COL[c])
        for tri, kk in zip(P, k):
            sx, sy, sd = proj[0](tri)
            polys.append(np.column_stack([sx, sy])); cols.append(np.clip(base * kk, 0, 1)); depth.append(sd.mean())
    order = np.argsort(depth)[::-1]                    # far first
    allp = np.vstack(polys) if polys else np.zeros((1, 2))
    (xa, ya), (xb, yb) = allp.min(0), allp.max(0)
    pad = 0.04 * max(xb - xa, yb - ya)
    asp = (yb - ya + 2 * pad) / max(xb - xa + 2 * pad, 1e-6)
    fig, ax = plt.subplots(figsize=(width_in, min(width_in, max(2.5, width_in * asp * 0.95 + 1.2))))
    ax.add_collection(PolyCollection([polys[i] for i in order], facecolors=[cols[i] for i in order],
                                     edgecolors=[cols[i] for i in order], linewidths=0.15))
    ax.set_xlim(xa - pad, xb + pad); ax.set_ylim(ya - pad, yb + pad)
    for v, lab, st in hlines:
        ax.axhline(v, ls=st, lw=0.7, color="m"); ax.text(xa - pad * 0.9, v + 0.15, lab, fontsize=7, color="m")
    for v, lab, st in vlines:
        ax.axvline(v, ls=st, lw=0.7, color="b"); ax.text(v + 0.2, yb + pad * 0.3, lab, fontsize=7, color="b", rotation=90, va="top")
    for x, y, txt in notes:
        ax.annotate(txt, (x, y), fontsize=7, color="k", xytext=(5, 5), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", lw=0.4))
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.set_xlabel({"front": "model X (mm)", "back": "-model X (mm)", "side": "model Y (mm)", "top": "model X (mm)"}[view])
    ax.set_ylabel("model Z (mm)" if view != "top" else "model Y (mm)")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    path = os.path.join(RENDER_DIR, fname + ".png")
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- driver
def run(model, render_views=("iso", "top", "front"), verify_pins=True, extra_lines=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    files = export(model)
    bb = bbox(model)
    res = {"name": model.name, "footprint": model.footprint, "descr": model.descr,
           "model_path": MODEL_PATH_FMT % model.name, "files": files,
           "bbox": {k: round(v, 3) for k, v in bb.items()}}
    if verify_pins:
        res["verify"] = verify(model)
    res["png"] = render(model, extra_lines=extra_lines, views=render_views)
    json.dump(res, open(os.path.join(OUT_DIR, model.name + ".json"), "w"), indent=1)
    print("==", model.name, "->", files.get("step"))
    print("   bbox X %(xmin).2f..%(xmax).2f  Y %(ymin).2f..%(ymax).2f  Z %(zmin).2f..%(zmax).2f" % bb)
    if verify_pins:
        print(table(res["verify"]))
        print("   pins vs pads:", "PASS" if res["verify"]["ok"] else "FAIL", res["verify"]["unmatched_pins"] or "")
    print("   png:", res["png"])
    return res
