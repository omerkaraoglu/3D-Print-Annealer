"""GF-D50 frame inspection drawing for the mould RFQ. Views and sections are taken from the frame STEP (CadQuery /
OCCT: hidden-line projection and plane sections), the dimensions and tolerances from the master (and from the
concept / design document; proposals marked [P] and listed in drafting_choices.json). The script also measures the
STEP at the critical places and compares with the master, so the drawing cannot silently disagree with the part.
GF-2.0: sections E-E (side), F-F (corner fastener), G-G (bridge / bend-gap slot), detail Y (nose, land break),
H-H (divider rib); F1-F4 only.

  <venv>/Scripts/python.exe make_frame.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Frame_Inspection.{dxf,pdf},
                                               GF_Frame_Inspection_p1.png, GF_Frame_Inspection_p2.png
"""
import datetime
import hashlib
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
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

from gf_common import (Params, Choices, Rect, OUT_DIR, REPO, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text,
                       stadium_pts, bulge_to_points, rev_note, master_ref, s8_withdrawn_rev)
from gf_geom import Geom
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT, lw

STEP_PATH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Frame.step")
C_SEC = "#a7acb3"
C_CTF = "#c0392b"


def tn(x):
    """tolerance number: 0 instead of 0.0"""
    return "0" if abs(x) < 1e-12 else n(x)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ===================================================================================================== STEP access
class StepFrame:
    def __init__(self, path=STEP_PATH):
        import cadquery as cq
        self.cq = cq
        self.path = path
        self.sha = sha256(path)
        self.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
        self.shape = cq.importers.importStep(path).val()
        bb = self.shape.BoundingBox()
        self.bbox = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
        self.volume = self.shape.Volume()
        self.n_faces = len(self.shape.Faces())

    @staticmethod
    def _edge_pts(e, step):
        from OCP.TopAbs import TopAbs_REVERSED
        cq_e = e
        L = cq_e.Length()
        if cq_e.geomType() == "LINE":
            ts = [0.0, 1.0]
        else:
            k = max(int(L / step), 6)
            ts = list(np.linspace(0.0, 1.0, k + 1))
        pts = [cq_e.positionAt(t) for t in ts]
        if cq_e.wrapped.Orientation() == TopAbs_REVERSED:
            pts = pts[::-1]
        return [(p.x, p.y, p.z) for p in pts]

    def _wire_pts(self, wire, step):
        from OCP.BRepTools import BRepTools_WireExplorer
        cq = self.cq
        exp = BRepTools_WireExplorer(wire.wrapped)
        out = []
        while exp.More():
            e = cq.Edge(exp.Current())
            p = self._edge_pts(e, step)
            if out and p and np.hypot(out[-1][0] - p[0][0], out[-1][1] - p[0][1]) < 1e-6 and \
                    abs(out[-1][2] - p[0][2]) < 1e-6:
                p = p[1:]
            out += p
            exp.Next()
        return out

    def hlr(self, view, step=0.6):
        """visible edges (sharp + smooth + silhouettes) projected; returns polylines in the view's (u, v)"""
        from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
        from OCP.HLRAlgo import HLRAlgo_Projector
        from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
        cq = self.cq
        if view == "front":       # viewer at -Z (sheet side); right = -X; u = -X + xc, v = Y + yc
            ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, -1), gp_Dir(-1, 0, 0))
        else:                     # back: viewer at +Z; right = +X
            ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))
        algo = HLRBRep_Algo()
        algo.Add(self.shape.wrapped)
        algo.Projector(HLRAlgo_Projector(ax))
        algo.Update()
        algo.Hide()
        h = HLRBRep_HLRToShape(algo)
        lines = []
        for comp in (h.VCompound(), h.Rg1LineVCompound(), h.OutLineVCompound()):
            if comp is None or comp.IsNull():
                continue
            for e in cq.Shape.cast(comp).Edges():
                p = self._edge_pts(e, step)
                lines.append([(q[0], q[1]) for q in p])
        return lines

    def section(self, origin, tdir, normal, size=700.0, step=0.05):
        """plane section: list of (outer, [inners]) with points in (t, Z); t = (p - origin) . tdir"""
        cq = self.cq
        face = cq.Face.makePlane(size, size, basePnt=cq.Vector(*origin), dir=cq.Vector(*normal))
        sec = self.shape.intersect(face)
        o = np.array(origin, float)
        td = np.array(tdir, float)
        res = []
        for f in sec.Faces():
            def conv(w):
                pts = np.array(self._wire_pts(w, step))
                return np.column_stack([(pts - o) @ td, pts[:, 2]])
            res.append((conv(f.outerWire()), [conv(w) for w in f.innerWires()]))
        return res

    def hsection(self, z, step=0.05):
        """horizontal section at Z: list of (outer, [inners]) in STEP (X, Y)"""
        cq = self.cq
        face = cq.Face.makePlane(700, 700, basePnt=cq.Vector(100, -80, z), dir=cq.Vector(0, 0, 1))
        sec = self.shape.intersect(face)
        res = []
        for f in sec.Faces():
            def conv(w):
                pts = np.array(self._wire_pts(w, step))
                return pts[:, :2]
            res.append((conv(f.outerWire()), [conv(w) for w in f.innerWires()]))
        return res


# ====================================================================================================== measuring
def _segs(polys):
    out = []
    for outer, inners in polys:
        for ring in [outer] + inners:
            q = np.vstack([ring, ring[:1]])
            out.append(np.column_stack([q[:-1], q[1:]]))
    return np.vstack(out) if out else np.zeros((0, 4))


def cross_h(polys, z, t0, t1):
    """t of the boundary crossings with the horizontal line Z = z, inside [t0, t1]"""
    s = _segs(polys)
    a, b = s[:, 1], s[:, 3]
    m = ((a - z) * (b - z) < 0)
    t = s[m, 0] + (z - a[m]) * (s[m, 2] - s[m, 0]) / (b[m] - a[m])
    return sorted(float(x) for x in t if t0 <= x <= t1)


def cross_v(polys, t, z0, z1):
    """Z of the boundary crossings with the vertical line t = t, inside [z0, z1]"""
    s = _segs(polys)
    a, b = s[:, 0], s[:, 2]
    m = ((a - t) * (b - t) < 0)
    z = s[m, 1] + (t - a[m]) * (s[m, 3] - s[m, 1]) / (b[m] - a[m])
    return sorted(float(x) for x in z if z0 <= x <= z1)


def hole_extent(hpolys, cx, cy, ax, ay):
    """inner ring containing (cx, cy): extent along (ax, ay) and across it"""
    from matplotlib.path import Path as MP
    for outer, inners in hpolys:
        for ring in inners:
            if MP(ring).contains_point((cx, cy)):
                d = ring - np.array([cx, cy])
                along = d @ np.array([ax, ay])
                across = d @ np.array([-ay, ax])
                return float(along.max() - along.min()), float(across.max() - across.min())
    return None, None


def bottom_sections(SF, P):
    """GF-2.0 sections at the bottom edge, t = abs y (outward): G-G through the bridge at the glass-centre x (TFT tail
    span), H-H along the divider rib (div_x)"""
    xc = P.pt("glass_centre")[0]
    secG = SF.section((xc, 0, 0), (0, -1, 0), (1, 0, 0))
    secH = SF.section((P.d("div_x"), 0, 0), (0, -1, 0), (1, 0, 0))
    return xc, secG, secH


def measure(SF, P, G, secG=None, secH=None):
    """measure the STEP at the critical places; every row = (what, measured, expected, tol, ok)"""
    Zg = P.level("Z_GLASS_FRONT")
    Zs = P.level("Z_SHEET_BACK")
    Zff, Zfb = P.level("Z_FLANGE_FRONT"), P.level("Z_FLANGE_BACK")
    Zl, Ztt = P.level("Z_LAND"), P.level("Z_TUBE_TOP")
    Zseat, Zlpb = P.level("Z_SEAT"), P.level("Z_LANDPLATE_BACK")
    tan1 = math.tan(math.radians(P.val("carried_over_from_v2", "draft")))
    rows = []

    def row(what, meas, exp, tol, group=""):
        ok = meas is not None and abs(meas - exp) <= tol
        rows.append({"what": what, "measured": None if meas is None else round(meas, 4), "expected": round(exp, 4),
                     "tol": tol, "ok": bool(ok), "group": group})

    # section E-E: abs y 60, abs left side; t = s = glass x0 - X (outward)
    gx0 = P.rect("glass").x0
    secA = SF.section((gx0, -60.0, 0), (-1, 0, 0), (0, 1, 0))
    s_li, s_lo = gx0 - P.rect("lip_in").x0, gx0 - P.rect("lip_out").x0
    s_so = gx0 - P.rect("seat_ring_out").x0
    zs = cross_v(secA, (s_li + s_lo) / 2.0, Zg - 1, Zg + 2)
    row("lip top Z = Z_GLASS_FRONT (flush plane)", zs[0] if zs else None, Zg, 0.005, "E-E")
    zs = cross_v(secA, (s_lo + s_so) / 2.0, Zg - 1, Zg + 3)
    row("seat ring Z = datum A (Z_SHEET_BACK)", zs[0] if zs else None, Zs, 0.005, "E-E")
    zs = cross_v(secA, 10.0, Zg - 1, Zg + 6)
    row("flange front Z", zs[0] if zs else None, Zff, 0.005, "E-E")
    row("flange back Z", zs[1] if len(zs) > 1 else None, Zfb, 0.005, "E-E")
    zs = cross_v(secA, -3.0, Zg - 1, Zg + 6)
    row("land Z (recess floor)", zs[0] if zs else None, Zl, 0.005, "E-E")
    zm = (Zg + Zs) / 2.0
    ts = cross_h(secA, zm, 0.0, 2.0)
    if len(ts) >= 2:
        e_in, e_out = s_li - (zm - Zg) * tan1, s_lo - (Zs - zm) * tan1
        row("lip inner face s at mid-height (1 deg)", ts[0], e_in, 0.01, "E-E")
        row("lip outer face s at mid-height (1 deg)", ts[-1], e_out, 0.01, "E-E")
        row("lip width at mid-height", ts[-1] - ts[0], e_out - e_in, 0.01, "E-E")
    # horizontal sections through the F1 pad / counterbore / slot / coring (GF-2.0: F1-F4 only, all alike)
    cb, co = G.fastener_cuts()
    f1 = P.fast("F1")
    meas_cb = {}
    for nm, f, floor in (("F1", f1, cb["cb_floor_F1-F4"]),):
        ax_, ay_ = f["slot_axis"][0], -f["slot_axis"][1]          # STEP Y = -y
        cx, cy = f["x_abs"], -f["y_abs_down"]
        tcb = math.tan(math.radians(cb["cb_draft"]))
        h0 = SF.hsection(Zs + 0.02)
        L, W = hole_extent(h0, cx, cy, ax_, ay_)
        dz0 = 0.02
        meas_cb[nm] = (None if W is None else W + 2 * dz0 * tcb, None if L is None else L + 2 * dz0 * tcb)
        row("counterbore width at A + 0.02", W, cb["cb_w"] - 2 * dz0 * tcb, 0.02, nm)
        row("counterbore length at A + 0.02", L, cb["cb_l"] - 2 * dz0 * tcb, 0.02, nm)
        zb = floor - cb["cb_r"] - 0.05                                     # above the R floor round
        L2, W2 = hole_extent(SF.hsection(Zs + zb), cx, cy, ax_, ay_)
        L3, W3 = hole_extent(SF.hsection(Zs + floor + 0.05), cx, cy, ax_, ay_)
        row("counterbore width %s above the floor %s" % (n(cb["cb_r"] + 0.05), n(floor)), W2,
            cb["cb_w"] - 2 * zb * tcb, 0.03, nm)
        row("slot width 0.05 behind the counterbore floor", W3,
            G.slot_w + 2 * (floor + 0.05 - (Zff - Zs)) * math.tan(math.radians(0.5))
            if Zs + floor + 0.05 > Zff else G.slot_w, 0.03, nm)
        L4, W4 = hole_extent(SF.hsection(Zfb - 0.3), cx, cy, ax_, ay_)
        exp_w = G.slot_w + 2 * (Zfb - 0.3 - Zff) * math.tan(math.radians(0.5))
        row("slot width 0.3 before the flange back (0.5 deg)", W4, exp_w, 0.02, nm)
        row("slot length 0.3 before the flange back", L4, G.slot_l + (exp_w - G.slot_w), 0.02, nm)
        hc = SF.hsection(Ztt - 0.2)
        rr = None
        for outer, inners in hc:
            for ring in [outer] + inners:
                c = ring.mean(axis=0)
                if np.hypot(c[0] - cx, c[1] - cy) < 0.5:
                    r = np.hypot(ring[:, 0] - cx, ring[:, 1] - cy)
                    if 5.5 < r.mean() < 8.5:
                        rr = (rr or []) + [float(r.mean())]
        if rr and len(rr) >= 2:
            dd = 0.2 * math.tan(math.radians(co["core_draft"]))
            row("coring groove r_in 0.2 below the tube top", min(rr), co["core_r_in"] + dd, 0.03, nm)
            row("coring groove r_out 0.2 below the tube top", max(rr), co["core_r_out"] - dd, 0.03, nm)
    # clearance pocket + bend-gap slot at the land level (one opening in the land plate)
    from matplotlib.path import Path as MP
    hl = SF.hsection(Zl + 0.02)
    pk, sl = P.rect("pocket"), P.rect("bend_gap_slot")
    xc_, yc_ = P.pt("glass_centre")
    dr = (Zseat - (Zl + 0.02)) * tan1      # pocket size is defined at Z_SEAT, 1 deg
    for outer, inners in hl:
        for ring in inners:
            if MP(ring).contains_point((xc_, -yc_)):
                ya = -ring[:, 1]
                row("clearance pocket x0 at the land (defined at Z_SEAT)", float(ring[:, 0].min()), pk.x0 - dr, 0.03,
                    "plan")
                row("clearance pocket x1 at the land (defined at Z_SEAT)", float(ring[:, 0].max()), pk.x1 + dr, 0.03,
                    "plan")
                row("clearance pocket y0 at the land (defined at Z_SEAT)", float(ya.min()), pk.y0 - dr, 0.03, "plan")
                Ym = -(sl.y0 + sl.y1) / 2.0
                q = np.vstack([ring, ring[:1]])
                xs = []
                for i in range(len(q) - 1):
                    (xa, ya_), (xb, yb) = q[i], q[i + 1]
                    if (ya_ - Ym) * (yb - Ym) < 0:
                        xs.append(xa + (Ym - ya_) * (xb - xa) / (yb - ya_))
                row("bend-gap slot x0 at the land (tail span)", min(xs) if xs else None, sl.x0, 0.03, "plan")
                row("bend-gap slot x1 at the land (tail span)", max(xs) if xs else None, sl.x1, 0.03, "plan")
    # ---------------------------------------------------------------- GF-2.0 bottom zone (sections G-G, H-H)
    if secG is None or secH is None:
        _, secG, secH = bottom_sections(SF, P)
    y_face, R, b = sl.y1, P.d("bend_nose_R"), P.d("land_break")
    py1 = P.val("carried_over_from_v2", "panel_y1")
    ts = cross_h(secG, Zl + 0.5, 120.0, 123.5)
    face = ts[0] if ts else None
    row("bridge pocket face y, 0.5 behind the land (1 deg)", face, y_face + 0.5 * tan1, 0.01, "G-G")
    ts = cross_h(secG, Zseat + 0.5, 116.0, 120.5)
    shelf = ts[-1] if ts else None
    row("shelf end (slot front face) y, 0.5 behind Z_SEAT", shelf, py1 - 0.5 * tan1, 0.01, "G-G")
    row("bend-gap slot = g_bend (face at Z_LAND - shelf end at Z_SEAT)",
        None if face is None or shelf is None else (face - 0.5 * tan1) - (shelf + 0.5 * tan1), P.d("g_bend"), 0.01,
        "G-G")
    zs = cross_v(secG, y_face + b / 2.0, Zl - 0.5, Zl + 0.6)
    row("land break: surface Z at face + %s (%s x 45 deg)" % (n(b / 2.0), n(b)), zs[0] if zs else None,
        Zl + b / 2.0, 0.01, "G-G")
    zs = cross_v(secG, y_face + 3.0, Zl - 0.5, Zl + 0.6)
    row("bottom land Z at face + 3.0", zs[0] if zs else None, Zl, 0.005, "G-G")
    flat = (Zlpb - Zl) - R                                         # flat part of the pocket face below the nose
    cy, cz = y_face + flat * tan1 + R, Zlpb - R
    yq = y_face + 0.5
    zs = cross_v(secG, yq, Zl + 0.6, Zlpb + 0.5)
    row("nose R%s: surface Z at face + 0.5" % n(R), zs[0] if zs else None,
        cz + math.sqrt(R * R - (cy - yq) ** 2), 0.01, "G-G")
    zs = cross_v(secG, y_face + 4.0, Zl - 0.5, 0.0)
    row("bridge floor Z (land-plate back) at face + 4.0", zs[-1] if zs else None, Zlpb, 0.005, "G-G")
    tp = P.rect("tail_pocket")
    ym = 0.5 * (P.rect("seat_ring_out").y1 + tp.y1)
    zs = cross_v(secG, ym, Zff - 0.5, 0.0)
    row("tail-pocket floor Z (flange plate back) at y %s" % n(ym, 1), zs[-1] if zs else None,
        P.level("Z_FLOOR_LOW"), 0.005, "G-G")
    ts = cross_h(secG, -4.0, tp.y1 - 3.0, tp.y1 + 5.0)
    row("bottom wall inner face y at Z -4.0 (1 deg)", ts[0] if ts else None, tp.y1 + (-4.0 - Zl) * tan1, 0.01,
        "G-G")
    wall = P.val("carried_over_from_v2", "wall")
    ts = cross_h(secG, Zl + 0.02, tp.y1, tp.y1 + 5.0)
    row("bottom wall outer face y at the land (+0.02)", ts[-1] if ts else None, tp.y1 + wall - 0.02 * tan1, 0.01,
        "G-G")
    ts = cross_h(secG, Zff + 0.02, tp.y1, tp.y1 + 5.0)
    row("flange bottom edge y at the flange front (+0.02)", ts[-1] if ts else None,
        P.d("flange_y1_bottom") - 0.02 * tan1, 0.01, "G-G")
    zs = cross_v(secG, tp.y1 + wall / 2.0, Zff - 0.5, 6.0)
    row("bottom wall top Z (Z_TROUGH_TOP)", zs[-1] if zs else None, P.level("Z_TROUGH_TOP"), 0.005, "G-G")
    stp = P.val("carried_over_from_v2", "tail_wall_step_y")
    zs = cross_v(secH, y_face + 3.0, Zl - 0.5, 6.0)
    row("divider rib top Z at face + 3.0 (y < %s: Z_PCB)" % n(stp, 1), zs[-1] if zs else None, P.level("Z_PCB"),
        0.005, "H-H")
    zs = cross_v(secH, ym, Zl - 0.5, 6.0)
    row("divider rib top Z at y %s (Z_TROUGH_TOP)" % n(ym, 1), zs[-1] if zs else None, P.level("Z_TROUGH_TOP"),
        0.005, "H-H")
    ts = cross_h(secH, -4.0, 120.0, 124.0)
    row("divider rib front face y at Z -4.0 (= bridge face, 1 deg)", ts[0] if ts else None,
        y_face + (-4.0 - Zl) * tan1, 0.01, "H-H")
    zr = Zlpb + 1.5
    s_ = _segs(SF.hsection(zr))
    Y = -ym
    a, b_ = s_[:, 1], s_[:, 3]
    m = ((a - Y) * (b_ - Y) < 0)
    xs = sorted(float(x) for x in s_[m, 0] + (Y - a[m]) * (s_[m, 2] - s_[m, 0]) / (b_[m] - a[m])
                if abs(x - P.d("div_x")) < 5.0)
    row("divider rib thickness 1.5 behind its floor (1 deg)", (xs[-1] - xs[0]) if len(xs) >= 2 else None,
        P.d("div_t") - 2 * 1.5 * tan1, 0.01, "H-H")
    row("divider rib centre x", 0.5 * (xs[-1] + xs[0]) if len(xs) >= 2 else None, P.d("div_x"), 0.01, "H-H")
    return rows, meas_cb


# ============================================================================================================ draw
def fill_polys(ax, polys, M, fc=C_SEC, hatch="\\\\\\\\", ec="k", lw_=THIN, clip=None, z=3):
    for outer, inners in polys:
        verts, codes = [], []
        for ring in [outer] + inners:
            q = M(ring)
            verts += list(q) + [q[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(q) - 1) + [Path.CLOSEPOLY]
        p = PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw(lw_), hatch=hatch, zorder=z)
        ax.add_patch(p)
        if clip is not None:
            p.set_clip_path(clip)


def section_block(sh, polys, ox, oy, k, t0, t1, d0, d1, Zg, title, flip=False, title_dy=3.0):
    """draw a section: paper x = ox + k (t - t0), y = oy - k (Z - Zg - d0) (front at the top); clipped window"""
    def M(ring):
        r = np.asarray(ring)
        return np.column_stack([ox + k * (r[:, 0] - t0), oy - k * (r[:, 1] - Zg - d0)])
    w, h = k * (t1 - t0), k * (d1 - d0)
    clip = Rectangle((ox, oy - h), w, h, transform=sh.ax.transData)
    fill_polys(sh.ax, polys, M, clip=clip)
    for x in (ox, ox + w):
        sh.L([x, x], [oy - h, oy], w=XTHIN, c="0.4", geom=False, dashes=(1, 1.5))
    sh.T(ox, oy + title_dy, title, fs=7.5, weight="bold")
    P_ = lambda t, d: (ox + k * (t - t0), oy - k * (d - d0))
    return P_


def make(out_dir=OUT_DIR):
    P, C = Params(), Choices()
    G = Geom(P)
    SF = StepFrame()
    xG, secG, secH = bottom_sections(SF, P)
    rows, meas_cb = measure(SF, P, G, secG, secH)
    xc, yc = G.fv.xc, G.fv.yc
    Zg = P.level("Z_GLASS_FRONT")
    Zs, Zff, Zfb = P.level("Z_SHEET_BACK"), P.level("Z_FLANGE_FRONT"), P.level("Z_FLANGE_BACK")
    Zl, Ztt, Zpcb = P.level("Z_LAND"), P.level("Z_TUBE_TOP"), P.level("Z_PCB")
    Zlpb, Zseat = P.level("Z_LANDPLATE_BACK"), P.level("Z_SEAT")
    Zfl, Ztr = P.level("Z_FLOOR_LOW"), P.level("Z_TROUGH_TOP")
    cb, co = G.fastener_cuts()
    gtol = P.val("drawing_tolerances.frame", "general")
    t_lip = P.val("drawing_tolerances.frame", "lip_above_seat_ring")
    t_land = P.val("drawing_tolerances.frame", "land_Z_to_lip_top")
    t_cop = P.val("drawing_tolerances.frame", "seat_ring_and_pads_coplanar")
    t_slot = P.val("drawing_tolerances.frame", "slot_position")
    t_pp = P.val("drawing_tolerances.frame", "parting_plane_flatness_unclamped")
    pip_tol = float(__import__("re").search(r"\+-([\d.]+)", P.dnote("pip_h")).group(1))
    draft, draft_loc = P.val("carried_over_from_v2", "draft"), P.val("carried_over_from_v2", "draft_loc")
    lipT = C("frame_lip_outline_tol")
    lipW = C("frame_lip_width_tol")
    slT = C("frame_slot_tol")
    cbT = C("frame_cb_tol")
    ttT = C("frame_tube_top_tol")
    crT = C("frame_core_r_in_tol")
    bsT = C("frame_boss_tol")
    tex = C("frame_lip_texture")
    bfT = C("frame_bend_face_tol")                      # GF-2.0 proposals [P]
    nRT = C("frame_nose_R_tol")
    lbT = C("frame_land_break_tol")
    rbT = C("frame_rib_pos_tol")
    # venting / exclusion zones / GF-2.0 shut-off from the master cad_rules
    vent_it = P.item("drawing_tolerances.frame", "vent_witness_lip_top")
    vent_w = vent_it["value"]
    assert "toolmaker to propose" in vent_it["note"]
    rules = P.get("cad_rules")
    vent_rule_i = [i for i, r in enumerate(rules) if "vent witness on the lip top" in r]
    assert len(vent_rule_i) == 1, vent_rule_i
    vent_rule_i = vent_rule_i[0]
    so_rule_i = [i for i, r in enumerate(rules) if "shut-off A/B is NOT a flat face" in r]
    assert len(so_rule_i) == 1, ("master cad_rules: stepped / telescopic shut-off rule not found", so_rule_i)
    so_rule_i = so_rule_i[0]
    m_so = re.search(r"top of the land break \(y ([\d.]+), Z_LAND \+ land_break = (-?[\d.]+)\).*?shelf corner "
                     r"\(y ([\d.]+), Z_SEAT (-?[\d.]+)\), so it rises ([\d.]+) over the ([\d.]+) slot width.*?"
                     r"A-side ledge ([\d.]+) x ([\d.]+) across.*?>= ([\d.]+) deg on that face.*?steel angles B "
                     r"([\d.]+) deg / A ([\d.]+) deg", rules[so_rule_i])
    assert m_so, rules[so_rule_i]
    SO = [float(m_so.group(i)) for i in range(1, 12)]
    m_so2 = re.search(r"up to ([\d.]+) deg fits in the slot.*?would leave a ([\d.]+) deg B-steel knife edge",
                      rules[so_rule_i])
    assert m_so2, rules[so_rule_i]
    SO_max, SO_knife = float(m_so2.group(1)), float(m_so2.group(2))
    P._use("cad_rules[%d] ~ shut-off numbers" % so_rule_i, SO + [SO_max, SO_knife])
    sr_rule_i = [i for i, r in enumerate(rules) if "R0.5 vertical rounds in the two inside corners shelf end" in r]
    assert len(sr_rule_i) == 1, sr_rule_i
    sr_rule_i = sr_rule_i[0]
    m_sr = re.search(r"R([\d.]+) vertical rounds .*?shelf end \(y ([\d.]+)\) x tail-pocket side walls \(x ([\d.]+) / "
                     r"([\d.]+)\)", rules[sr_rule_i])
    SR = [float(m_sr.group(i)) for i in range(1, 5)]
    P._use("cad_rules[%d] ~ shelf-end rounds" % sr_rule_i, SR)
    lip_root = P.d("lip_w_root_as_designed")
    lip_top = P.d("lip_w_top_as_designed")
    sl, br, rib = P.rect("bend_gap_slot"), P.rect("bridge"), P.rect("divider_rib")
    tp = P.rect("tail_pocket")
    gy1 = P.rect("glass").y1
    py1 = P.val("carried_over_from_v2", "panel_y1")
    g_bend, nose_R, brk = P.d("g_bend"), P.d("bend_nose_R"), P.d("land_break")
    div_x, div_t = P.d("div_x"), P.d("div_t")
    land_b = G.lands()["bottom over the tail span"]
    flat_land = land_b - brk
    stp_y = P.val("carried_over_from_v2", "tail_wall_step_y")
    v_face = G.fv.uv(0, sl.y1)[1]
    # the shut-off numbers of cad_rules (parsed above) must follow from the levels and the plan values
    tanD = math.tan(math.radians(P.val("carried_over_from_v2", "draft")))
    assert abs(SO[0] - round(sl.y1 + brk * tanD, 3)) < 6e-4 and abs(SO[1] - (Zl + brk)) < 6e-3, SO
    assert abs(SO[2] - py1) < 1e-6 and abs(SO[3] - Zseat) < 1e-6 and abs(SO[4] - (Zseat - Zl - brk)) < 6e-3, SO
    # GF-2.1: the slot width at the break top (3.235 = y 122.235 - 119.00) is g_bend 3.23 at Z_LAND plus the 1 deg
    # draft over the 0.3 break; the ledge spans that width. Plan slot / g_bend stays 3.23 everywhere else.
    w_brk = SO[0] - SO[2]
    assert abs(SO[5] - round(w_brk, 3)) < 6e-4 and abs(SO[6] - SO[5]) < 1e-9 and abs(SO[7] - brk) < 1e-6, SO
    assert abs(SO[5] - round(g_bend + brk * tanD, 3)) < 6e-4, (SO, g_bend)
    # the largest telescopic angle that fits: atan(slot width at the break / rise)
    assert abs(round(math.degrees(math.atan(SO[5] / SO[4])), 1) - SO_max) < 0.051, (SO, SO_max)
    assert abs(SR[1] - py1) < 1e-6 and abs(SR[2] - tp.x0) < 1e-6 and abs(SR[3] - tp.x1) < 1e-6, SR
    bm = G.bridge_bead_margins()                      # measured at Z_LAND + 0.01 (pocket note)
    be = G.break_edge_notes()                         # land plane (A1) / measured / face plane, each vs geometry
    assert be["ok"], be
    of2 = P._use("open_findings.2_bead_to_land_break.status", P.raw["open_findings"]["2_bead_to_land_break"]["status"])
    assert of2.startswith("CLOSED at %s" % P.revision), of2

    # ------------------------------------------------------------------ geometry from the STEP
    front = SF.hlr("front")
    back = SF.hlr("back")
    fv = [[(x + xc, y + yc) for x, y in ln] for ln in front]                  # x2d = -X -> u = x2d + xc
    bv = [[(x - xc, y + yc) for x, y in ln] for ln in back]                    # back view: u_b = X - xc
    gx0 = P.rect("glass").x0
    secA = SF.section((gx0, -60.0, 0), (-1, 0, 0), (0, 1, 0))
    f1 = P.fast("F1")
    a1 = (-f1["slot_axis"][0], f1["slot_axis"][1], 0.0)                      # outward along the slot, STEP coords
    secB = SF.section((f1["x_abs"], -f1["y_abs_down"], 0), a1, (a1[1], -a1[0], 0.0))

    # ================================================================== page 1: views + tables
    s1 = Sheet()
    s1.frame()
    k1 = 0.5
    V1 = View(s1, 82.0, 205.0, k1)
    for ln in fv:
        q = V1.Pa(ln)
        s1.L(q[:, 0], q[:, 1], w=XTHIN, c="k", geom=False)
    V2 = View(s1, 214.0, 205.0, k1)
    for ln in bv:
        q = V2.Pa(ln)
        s1.L(q[:, 0], q[:, 1], w=XTHIN, c="k", geom=False)
    fl = G.flange
    s1.T(18.0, 279.0, "FRONT VIEW (sheet side, seen from in front of the oven)   1 : 2", fs=8.0, weight="bold")
    s1.T(152.0, 262.0, "BACK VIEW (PCB side, seen from behind)   1 : 2", fs=8.0, weight="bold")
    s1.T(18.0, 274.5, "Views = hidden-line projection of the STEP (geometry master). Red = section lines / datums.",
         fs=6.0)
    top = V1.P(0, fl.y1)[1]
    s1.dim_h(*V1.P(fl.x0, fl.y1), *V1.P(fl.x1, fl.y1), top + 5.0, "%s (TG5)" % n2(fl.w), fs=6.5)
    s1.dim_v(*V1.P(fl.x0, fl.y0), *V1.P(fl.x0, fl.y1), V1.P(fl.x0, 0)[0] - 5.0, "%s" % n2(fl.h), fs=6.5)
    x0p, y0p = V1.P(0, 0)
    s1.circle(x0p, y0p, 1.2, ec=C_CTF, w=THIN, geom=False)
    s1.T(x0p + 2.0, y0p + 1.0, "B", fs=7, weight="bold", color=C_CTF)

    def cut_line(V, p0, p1, lab, dx=1.0, dy=1.0):
        (xa, ya), (xb, yb) = V.P(*p0), V.P(*p1)
        s1.L([xa, xb], [ya, yb], w=XTHIN, c=C_CTF, geom=False, dashes=(8, 2, 2, 2))
        for (x, y) in ((xa, ya), (xb, yb)):
            s1.circle(x, y, 0.6, fc=C_CTF, ec=C_CTF, geom=False)
        s1.T(xb + dx, yb + dy, lab, fs=7, weight="bold", color=C_CTF)
    vA = yc - 60.0
    cut_line(V1, (G.pocket.x1 - 2, vA), (fl.x1 + 3, vA), "E")
    F1 = G.F["F1"]
    cut_line(V1, (F1["u"] + F1["au"] * 28, F1["v"] + F1["av"] * 28), (F1["u"] - F1["au"] * 11, F1["v"] - F1["av"] * 11),
             "F")
    uG, uH = -(xG - xc), -(div_x - xc)
    cut_line(V1, (uG, G.pocket.y0 + 6), (uG, fl.y0 - 3), "G", dx=-3.6, dy=-3.0)
    cut_line(V1, (uH, G.pocket.y0 + 6), (uH, fl.y0 - 3), "H", dx=1.0, dy=-3.0)
    # fastener table (right column)
    xt, yt = 280.0, 268.0
    s1.T(xt, yt, "FASTENER FEATURES (positions to datum B, front view)", fs=7.0, weight="bold")
    frows = [["F", "u", "v", "axis deg", "front pad", "cb floor"]]
    for k_, f in G.F.items():
        frows.append([k_, n(f["u"]), n(f["v"]), n(math.degrees(math.atan2(f["av"], f["au"])) + 0.0, 2),
                      "dia %s" % n(G.pad_d), n(cb["cb_floor_F1-F4"])])
    yt = s1.table(xt, yt - 1.0, [0, 8, 26, 46, 66, 90], frows, fs=6.0, widths=126)
    for ln in s1.wrap("F1-F4 (no other fastener positions: S8 withdrawn at %s): slot %s +%s/%s x %s ±%s (stadium "
                      "at the flange front, %s deg draft wider to the back, long axis to datum B), position ±%s. "
                      "Counterbore %s x %s +%s/%s stadium, coaxial, size defined at datum A (the pad face), %s deg; "
                      "floor %s above A +%s/%s, R%s. Tube top dia %s, %s behind A ±%s [P]; coring groove r %s-%s "
                      "(r_in +%s/-%s [P]), %s deep from the tube top, R%s, %s deg." % (
                          s8_withdrawn_rev(P), n(G.slot_w), tn(slT[0]), tn(slT[1]), n(G.slot_l), tn(slT[2]), n(draft_loc),
                          n(t_slot), n(cb["cb_w"]), n(cb["cb_l"]), tn(cbT[0]), tn(cbT[1]), n(cb["cb_draft"]),
                          n(cb["cb_floor_F1-F4"]), tn(cbT[2]), tn(cbT[3]), n(cb["cb_r"]), n(P.d("pad_d")),
                          n(Ztt - Zs), n(ttT), n(co["core_r_in"]), n(co["core_r_out"]), tn(crT[0]), tn(crT[1]),
                          n(co["core_depth"]), n(co["core_floor_r"]), n(co["core_draft"])), 126.0, 5.9):
        yt -= 2.7
        s1.T(xt, yt, ln, fs=5.9)
    yt -= 5.0
    s1.T(xt, yt, "DATUMS", fs=7.0, weight="bold")
    for ln in s1.wrap("A = seat plane: seat-ring top + the 4 corner pads (all at Z_SHEET_BACK), coplanar %s. "
                      "B = centre of the recess wall (lip inner face) = glass centre = cut-out centre; axes along the "
                      "recess sides. Z values below are distances behind A (towards the PCB) unless noted." %
                      n(t_cop), 126.0, 5.9):
        yt -= 2.7
        s1.T(xt, yt, ln, fs=5.9)
    # CTF table (bottom)
    ctf = [["#", "critical-to-function feature", "nominal", "tolerance", "source"],
           ["1", "seat plane A (seat ring + pads F1-F4)", "Z_SHEET_BACK", "coplanar %s" % n(t_cop), "master"],
           ["2", "lip top above A (lip height = t_sheet)", n2(Zs - Zg), "±%s" % n(t_lip), "master"],
           ["3", "land below the lip top (recess depth = glass_t + t_bond), all four sides incl. the bottom land "
                 "over the bridge", n2(Zl - Zg), "±%s (land flat within %s)" % (n(t_land), n(2 * t_land)), "master"],
           ["4", "recess wall = lip inner face at the lip top", "%s x %s R%s" % (n2(G.lip_in.w), n2(G.lip_in.h),
                                                                                 n(G.lip_in.R)),
            "±%s, R ±%s, %s deg" % (n(lipT), n(lipT), n(draft)), "[P]"],
           ["5", "lip outer face at the lip root (A)", "%s x %s R%s" % (n2(G.lip_out.w), n2(G.lip_out.h),
                                                                       n(G.lip_out.R)),
            "±%s, R ±%s, %s deg" % (n(lipT), n(lipT), n(draft)), "[P]"],
           ["6", "lip width (root / top as designed)", "%s (%s / %s)" % (n(G.lip_w), n(lip_root, 4), n(lip_top, 4)),
            "±%s; top edges R0.3, root R0.2" % n(lipW), "[P] / design doc 8.1"],
           ["7", "seat-ring outer edge", "%s x %s R%s" % (n2(G.seat_out.w), n2(G.seat_out.h), n(G.seat_out.R)),
            gtol, "master"],
           ["8", "slots F1-F4 (table above)", "%s x %s" % (n(G.slot_w), n(G.slot_l)),
            "+%s/%s x ±%s; position ±%s" % (tn(slT[0]), tn(slT[1]), tn(slT[2]), n(t_slot)), "[P] / master"],
           ["9", "counterbores F1-F4 (stud weld flange), size at datum A", "%s x %s, floor %s" % (
               n(cb["cb_w"]), n(cb["cb_l"]), n(cb["cb_floor_F1-F4"])),
            "+%s/%s; floor +%s/%s" % (tn(cbT[0]), tn(cbT[1]), tn(cbT[2]), tn(cbT[3])), "[P]"],
           ["10", "tube tops (washer / rivet seats)", "%s behind A" % n(Ztt - Zs), "±%s" % n(ttT), "[P]"],
           ["11", "pips P1-P8 above the land (P2 / P4 on the bottom land)", "dia %s x %s" % (
               n(P.d("pip_d")), n(P.d("pip_h"))), "height ±%s" % n(pip_tol), "master"],
           ["12", "panel clearance pocket at the shelf front (Z_SEAT); %s deg, %s per side larger at the land" % (
               n(draft), n2((Zseat - Zl) * math.tan(math.radians(draft)))),
            "%s x %s R%s" % (n2(G.pocket.w), n2(G.pocket.h), n(G.pocket.R)), gtol, "master + STEP"],
           ["13", "BEND-GAP SLOT width = g_bend: panel edge line (= shelf end, y %s at Z_SEAT) -> bridge pocket face "
                  "(at Z_LAND); over the tail span x %s-%s (%s long); the only through-opening at the bottom" % (
                      n2(py1), n(sl.x0), n(sl.x1), n(sl.x1 - sl.x0)), "%s" % n2(g_bend),
            "from CTF 14 (face) and TG5 (shelf end)", "master"],
           ["14", "BRIDGE POCKET FACE (land-plate inner face) at Z_LAND, flat %s to the nose, %s deg widening to the "
                  "back" % (n((Zlpb - Zl) - nose_R), n(draft)),
            "y %s abs (v %s to B)" % (n2(sl.y1), n2(v_face)), "±%s" % n(bfT), "[P]"],
           ["15", "NOSE radius on the land-plate back x pocket face (B side)", "R%s" % n(nose_R),
            "+%s/%s (never smaller)" % (n(nRT[0]), tn(nRT[1])), "[P] / master"],
           ["16", "BOTTOM LAND over the tail span: pocket face -> glass edge; land break on its inner edge (A side); "
                  "flat after the break. Sizes are %s at border %s, still subject to the real-panel fold test "
                  "(GF-D21) before glass, sheet or mould are ordered" % (P.revision, n(P.d("border"))),
            "%s; %s x 45 deg; flat %s; bead -> break edge %s (land plane, A1 >= %s)" % (
                n2(land_b), n(brk), n2(flat_land), n2(be["land_plane"]), n(bm["rule"])),
            "break +%s/-%s; land per CTF 3 / 14" % (n(lbT[0]), n(lbT[1])), "[P] / master"],
           ["17", "tail pocket (x at Z_LAND, bottom face); floor behind the bridge = land-plate back (to the step "
                  "wall) + flange plate (Z_FLOOR_LOW)", "x %s-%s, to y %s, R%s" % (n(tp.x0), n(tp.x1), n(tp.y1),
                                                                                  n(tp.R)), gtol, "master"],
           ["18", "divider rib between the tails: x, thickness at the bridge floor, %s deg both sides; top Z_PCB for "
                  "y < %s, Z_TROUGH_TOP beyond; front face = bridge face" % (n(draft), n(stp_y, 1)),
            "x %s, t %s" % (n(div_x), n(div_t)), "position ±%s; TG5" % n(rbT), "[P] / master"],
           ["19", "PCB boss tops H1-H9 (Z_PCB)", "%s behind A" % n2(Zpcb - Zs),
            "coplanar %s, ±%s" % (n(bsT[0]), n(bsT[1])), "[P] (v2 geometry)"],
           ["20", "flange (parting line on its outline, front plane); bottom edge = bottom-wall outer face, flush",
            "%s x %s R%s, t %s" % (n2(fl.w), n2(fl.h), n(fl.R), n(P.d("flange_t"))),
            "flatness unclamped %s" % n(t_pp), "master"],
           ["21", "all other dimensions", "STEP", gtol, "master"]]
    s1.T(16.0, 144.0, "CRITICAL-TO-FUNCTION DIMENSIONS  (nominal from the master params, glass_t %s; [P] = tolerance "
                      "proposed by the drafter)" % n(P.d("glass_t")), fs=7.0, weight="bold")
    yc_ = s1.table_wrapped(16.0, 142.0, [9, 168, 72, 100, 45], ctf, fs=5.8, bold_rows=(13, 14, 15, 16))
    s1.title_block({
        "title": "FRAME (GlassFront) - INSPECTION DRAWING, sheet 1/2",
        "subtitle": "for the mould RFQ: geometry master = STEP; this sheet = what matters + tolerances",
        "source": "STEP %s (sha256 %s..., %s); params %s" % (os.path.basename(SF.path), SF.sha[:16], SF.mtime,
                                                             master_ref(P)),
        "project": "files: GF_Frame_Inspection.pdf (2 pages) / _p1.png / _p2.png / .dxf",
        "change": "%s. Flange %s x %s; CTF 13-18 at %s (slot %s, bridge face y %s, bottom land %s, break +%s/-%s "
                  "[P])." % (rev_note(P), n2(fl.w), n2(fl.h), P.revision, n2(g_bend), n2(sl.y1), n2(land_b),
                             n(lbT[0]), n(lbT[1])),
        "dwg": "GF-D50", "rev": P.revision, "scale": "1:2", "date": datetime.date.today().isoformat(),
        "drawn": "make_frame.py",
    }, h=42.0)
    iss1 = s1.check_layout()

    # ================================================================== page 2: sections + notes
    s2 = Sheet()
    s2.frame()
    dz = lambda Z: Z - Zg
    # E-E 4:1 (side, abs left / front-view right), s outward to the right
    kA = 4.0
    tA0, tA1, dA0, dA1 = -12.0, 22.5, -0.6, 12.6
    PA = section_block(s2, secA, 22.0, 268.0, kA, tA0, tA1, dA0, dA1, Zg,
                       "SECTION E-E  side (abs y 60), s outward from the glass edge   4 : 1")
    s_li, s_lo = gx0 - P.rect("lip_in").x0, gx0 - P.rect("lip_out").x0
    s_so = gx0 - P.rect("seat_ring_out").x0
    xr = PA(tA1, 0)[0] + 4.0
    s2.dim_v(*PA(-9.5, dz(Zl)), *PA(-9.5, dz(Zg)), PA(-9.5, 0)[0], "%s ±%s" % (n2(Zl - Zg), n(t_land)),
             fs=6.3, c=C_CTF)
    s2.dim_v(*PA(tA1, dz(Zff)), *PA(tA1, dz(Zfb)), xr, "%s" % n(Zfb - Zff), fs=6.3, side="right")
    s2.dim_v(*PA(tA1, dz(Zs)), *PA(tA1, dz(Zff)), xr, "%s" % n(Zff - Zs), fs=6.3, side="right")
    xa_, ya_ = PA((s_lo + s_so) / 2.0, dz(Zs))
    s2.poly([(xa_ - 1.6, ya_ - 3.0), (xa_ + 1.6, ya_ - 3.0), (xa_, ya_)], fc=C_CTF, ec=C_CTF, w=XTHIN, geom=False,
            z=6)
    s2.L([xa_, xa_], [ya_ - 3.0, ya_ - 5.0], w=XTHIN, c=C_CTF, geom=False)
    s2.T(xa_ + 1.8, ya_ - 6.6, "A", fs=7.5, weight="bold", color=C_CTF)
    yA = PA(0, dA1)[1]
    s2.dim_h(*PA(-(P.rect("pocket").x0 - gx0), dz(Zl)), *PA(0.0, dz(Zl)), yA - 5.0,
             "land %s" % n2(P.rect("pocket").x0 - gx0), fs=6.0)
    s2.T(PA(2.6, 0)[0], PA(0, dz(Zg) - 0.3)[1], "lip and seat ring: DETAIL Z", fs=5.8, color=C_CTF)
    for lab, s_, d_ in (("recess wall (lip inner face) %s deg" % n(draft), s_li - 0.3, dz(Zg) + 1.0),
                        ("flange", 15.0, dz((Zff + Zfb) / 2.0)), ("land plate", -2.0, dz(Zl) + 1.2)):
        s2.T(*PA(s_, d_), lab, fs=5.8, ha="right" if s_ < 1 else "center", va="center", allow_geom=True,
             bg="white")
    # detail Z: the lip at 10:1
    kZ = 10.0
    tZ0, tZ1, dZ0, dZ1 = -0.8, 4.0, -0.4, 2.2
    PZ = section_block(s2, secA, 167.0, 264.0, kZ, tZ0, tZ1, dZ0, dZ1, Zg, "DETAIL Z (from E-E)   10 : 1",
                       title_dy=12.0)
    s2.dim_h(*PZ(s_lo, dz(Zs)), *PZ(s_so, dz(Zs)), PZ(0, dZ0)[1] + 4.0, "seat ring %s" % n(P.d("seat_ring_w")),
             fs=6.0)
    s2.dim_v(*PZ(s_lo + 0.2, dz(Zs)), *PZ(s_lo + 0.2, dz(Zg)), PZ(tZ1, 0)[0] + 3.0, None, c=C_CTF)
    s2.T(PZ(tZ1, 0)[0] + 4.5, PZ(0, (dz(Zs) + dz(Zg)) / 2.0)[1], "%s ±%s" % (n2(Zs - Zg), n(t_lip)), fs=6.5,
         color=C_CTF, va="center")
    s2.dim_h(*PZ(s_li, dz(Zg) + 0.5), *PZ(s_lo, dz(Zg) + 0.5), PZ(0, dZ1)[1] - 2.0, None, arrows="out")
    s2.T(PZ(s_lo, 0)[0] + 5.5, PZ(0, dZ1)[1] - 2.9, "%s at mid-height ±%s" % (n(G.lip_w), n(lipW)), fs=6.3,
         color=C_CTF, va="center")
    for ln_i, ln in enumerate(("lip: %s deg both faces; R0.3 top edges, R0.2 root;" % n(draft),
                               "root %s / top %s as designed" % (n(lip_root, 4), n(lip_top, 4)),
                               "NO gate, ejector, parting line or vent witness",
                               "on the lip top, lip faces, seat ring, pads, land")):
        s2.T(167.0, PZ(0, dZ1)[1] - 8.0 - ln_i * 2.8, ln, fs=5.8, color=C_CTF if ln_i >= 2 else "k")
    # F-F 3:1 corner fastener along the slot axis
    kB = 3.0
    tB0, tB1, dB0, dB1 = -27.0, 11.0, -0.6, Ztt - Zg + 0.6
    PB = section_block(s2, secB, 22.0, 194.0, kB, tB0, tB1, dB0, dB1, Zg,
                       "SECTION F-F  corner fastener F1 along its slot axis (outward to the right)   3 : 1",
                       title_dy=10.0)
    s2.dim_h(*PB(-cb["cb_l"] / 2, dz(Zs)), *PB(cb["cb_l"] / 2, dz(Zs)), PB(0, dB0)[1] + 5.0,
             "cb %s +%s/%s" % (n(cb["cb_l"]), tn(cbT[0]), tn(cbT[1])), fs=6.0, c=C_CTF)
    s2.dim_h(*PB(-G.slot_l / 2, dz(Zfb)), *PB(G.slot_l / 2, dz(Zfb)), PB(0, dB1)[1] - 4.0,
             "slot %s ±%s" % (n(G.slot_l), tn(slT[2])), fs=6.0, c=C_CTF)
    s2.dim_v(*PB(-G.slot_l / 2, dz(Zs + cb["cb_floor_F1-F4"])), *PB(-G.slot_l / 2, dz(Zs)), PB(-1.0, 0)[0], None,
             c=C_CTF)
    s2.T(PB(-0.6, 0)[0], PB(0, dz(Zs) + 0.4)[1], "%s +%s/%s" % (n(cb["cb_floor_F1-F4"]), tn(cbT[2]), tn(cbT[3])),
         fs=5.8, color=C_CTF, va="top")
    s2.dim_v(*PB(tB1, dz(Zs)), *PB(tB1, dz(Ztt)), PB(tB1, 0)[0] + 2.0, None, c=C_CTF)
    s2.T(PB(tB1, 0)[0] + 3.0, PB(0, (dz(Zs) + dz(Ztt)) / 2.0)[1], "tube top %s ±%s [P]" % (n(Ztt - Zs), n(ttT)),
         fs=5.8, color=C_CTF, va="center")
    s2.T(*PB(co["core_r_out"] + 0.3, dz(Ztt) - 1.2), "coring r %s-%s x %s" % (n(co["core_r_in"]),
                                                                          n(co["core_r_out"]), n(co["core_depth"])),
         fs=5.8, va="center", allow_geom=True, bg="white")
    # G-G 2.5:1 bottom edge through the bridge (t = abs y, outward to the right)
    kG = 2.5
    tG0, tG1, dG0, dG1 = 115.0, 151.5, -0.6, dz(Ztr) + 0.6
    PG = section_block(s2, secG, 22.0, 150.0, kG, tG0, tG1, dG0, dG1, Zg,
                       "SECTION G-G  bridge at abs x %s   %s : 1" % (n(xG), n(kG)), title_dy=7.0)
    ytop, ybot = PG(0, dG0)[1], PG(0, dG1)[1]          # front (flush plane) at the top, depth downwards
    s2.dim_h(*PG(py1, dz(P.level("Z_SHELF_BACK"))), *PG(sl.y1, dz(Zl) + 0.3), ytop + 2.5, n(g_bend), fs=6.0,
             c=C_CTF)
    s2.dim_h(*PG(sl.y1, dz(Zl) + 0.3), *PG(gy1, dz(Zl)), ytop + 2.5, n2(land_b), fs=6.0, c=C_CTF)
    s2.T(PG(gy1, 0)[0] + 2.5, ytop + 3.1, "bend-gap slot (CTF 13) | bottom land to the glass edge (CTF 16)",
         fs=5.8, color=C_CTF)
    wl = P.val("carried_over_from_v2", "wall")
    s2.dim_h(*PG(tp.y1, dz(Ztr)), *PG(tp.y1 + wl, dz(Ztr)), ybot - 3.5, None, arrows="out")
    s2.T(PG(tp.y1, 0)[0] - 6.0, ybot - 4.4, "bottom wall %s" % n(wl), fs=5.8, ha="right", va="center")
    s2.T(22.0, ybot - 9.0, "flange bottom edge y %s at the flange front = bottom-wall outer face, flush (master "
                           "flange_y1_bottom)" % n(P.d("flange_y1_bottom")), fs=5.6)
    for lab, (y_, d_), ha in (("shelf end", (py1 - 1.3, dz(P.level("Z_SHELF_BACK")) + 1.2), "center"),
                              ("tail pocket (open to the back)", (139.0, dz(Zfl) + 4.0), "center"),
                              ("flange plate = pocket floor", (139.0, dz(Zfl) - 1.25), "center"),
                              ("bridge", (127.0, dz(Zlpb) - 1.1), "center")):
        s2.T(*PG(y_, d_), lab, fs=5.6, ha=ha, va="center", allow_geom=True, bg="white")
    # detail Y 10:1: the bend gap (pocket face, land break, nose) with the panel edge line (ref.)
    kY = 10.0
    tY0, tY1, dY0, dY1 = 118.4, 124.7, dz(Zl) - 0.55, dz(Zlpb) + 0.5
    PY = section_block(s2, secG, 140.0, 150.0, kY, tY0, tY1, dY0, dY1, Zg,
                       "DETAIL Y (from G-G): bend gap, A/B parting   10 : 1", title_dy=7.0)
    xpe = PY(py1, 0)[0]
    s2.L([xpe, xpe], [PY(0, dY0)[1], PY(0, dY1)[1]], w=XTHIN, c="0.35", geom=False, dashes=(8, 1.5, 1.5, 1.5))
    s2.T(xpe - 1.0, PY(0, dY1)[1] - 2.0, "panel edge line y %s (ref.)" % n2(py1), fs=5.6, color="0.35",
         va="center", ha="right")
    # stepped / telescopic shut-off of master cad_rules[15] (schematic): ledge across the slot at the break top,
    # then the telescopic face along y 119.0 down to the shelf corner at Z_SEAT (beyond this window)
    C_PL = "#1f6fbf"
    pts = [PY(SO[0], dz(SO[1])), PY(SO[2], dz(SO[1])), PY(SO[2], dY1)]
    s2.L([p[0] for p in pts], [p[1] for p in pts], w=0.6, c=C_PL, geom=False, dashes=(4, 1.2))
    s2.arrow(pts[2][0], pts[2][1], -math.pi / 2, C_PL)
    s2.T(*PY(0.5 * (SO[0] + SO[2]), dz(SO[1]) - 0.3), "A", fs=6.5, weight="bold", color=C_PL, ha="center",
         va="center")
    s2.T(*PY(0.5 * (SO[0] + SO[2]), dz(SO[1]) + 0.5), "B", fs=6.5, weight="bold", color=C_PL, ha="center",
         va="center")
    s2.T(*PY(0.5 * (tY0 + SO[2]), dz(SO[1]) + 1.3), "A", fs=6.5, weight="bold", color=C_PL, ha="center",
         va="center")
    s2.T(PY(SO[2], 0)[0] + 1.2, PY(0, dY1)[1] - 2.0, "A/B parting (note 4): ledge %s x %s, then telescopic face" % (
        n(SO[6]), n(SO[7])), fs=5.6, color=C_PL, va="center")
    s2.T(PY(SO[2], 0)[0] + 1.2, PY(0, dY1)[1] - 4.6, "along y %s to Z_SEAT (%s deeper, beyond this view), >= %s "
         "deg" % (n2(SO[2]), n2(SO[4]), n(SO[8])), fs=5.6, color=C_PL, va="center")
    dmid = dY0 + 0.22
    s2.dim_h(xpe, PY(0, dmid)[1], *PY(sl.y1, dmid), PY(0, dmid)[1], None, c=C_CTF, ext=False)
    s2.T(0.5 * (xpe + PY(sl.y1, 0)[0]), PY(0, dmid)[1] + 0.7, "g_bend %s, face ±%s [P]" % (n2(g_bend), n(bfT)),
         fs=6.0, ha="center", va="bottom", color=C_CTF)
    s2.radius(*PY(sl.y1 + ((Zlpb - Zl) - nose_R) * math.tan(math.radians(draft)) + nose_R, dz(Zlpb) - nose_R),
              nose_R * kY, 225, "R%s +%s/%s [P]" % (n(nose_R), n(nRT[0]), tn(nRT[1])), L=5.0, fs=6.0, c=C_CTF)
    s2.leader(*PY(sl.y1 + brk / 2.0, dz(Zl) + brk / 2.0), PY(tY1, 0)[0] + 1.0, PY(0, dz(Zl) + 0.1)[1],
              "%s x 45 +%s/-%s [P] (A)" % (n(brk), n(lbT[0]), n(lbT[1])), fs=6.0, c=C_CTF)
    s2.dim_v(*PY(sl.y1, dz(Zl)), *PY(sl.y1, dz(Zl) + (Zlpb - Zl) - nose_R), PY(sl.y1, 0)[0] - 3.0, None,
             c="k")                                            # 1.0 at 10:1 = 10 mm: arrows inside
    s2.T(PY(sl.y1, 0)[0] - 4.0, PY(0, dz(Zl) + 0.5 * ((Zlpb - Zl) - nose_R))[1], "flat %s" %
         n((Zlpb - Zl) - nose_R), fs=5.8, ha="right", va="center")
    s2.T(PY(tY1, 0)[0] - 2.0, PY(0, dz(Zl) + 1.2)[1], "land plate (bridge)", fs=5.6, ha="right", va="center",
         allow_geom=True, bg="white")
    # H-H 2:1 along the divider rib
    kH = 2.0
    tH0, tH1 = 115.0, 151.5
    PH = section_block(s2, secH, 22.0, 77.0, kH, tH0, tH1, dG0, dG1, Zg,
                       "SECTION H-H  along the divider rib at abs x %s (outward to the right)   %s : 1" % (
                           n(div_x), n(kH)), title_dy=7.0)
    hb = PH(0, dG1)[1]
    s2.dim_h(*PH(rib.y0, dz(Zpcb)), *PH(stp_y, dz(Ztr)), hb - 3.5, n(stp_y - rib.y0), fs=5.8)
    s2.T(PH(stp_y, 0)[0] + 2.0, hb - 3.0, "rib top steps at y %s (Z_PCB -> Z_TROUGH_TOP)" % n(stp_y, 1), fs=5.8)
    xh, yh = PH(tH1, 0)[0] + 4.0, PH(0, dG0)[1] - 2.0
    for i_, (ln, col) in enumerate((("divider rib x %s ±%s [P] (CTF 18)" % (n(div_x), n(rbT)), C_CTF),
                                    ("%s thick at its floor, %s deg both sides," % (n(div_t), n(draft)), "k"),
                                    ("R0.5 roots; front face = bridge pocket face;", "k"),
                                    ("between the tails: CTP left, TFT right", "k"),
                                    ("(seen from the back)", "k"))):
        s2.T(xh, yh - 2.8 * i_, ln, fs=5.8, va="top", color=col)
    # notes
    notes = [
        "GEOMETRY MASTER: %s (sha256 %s, %s; written in cm, read in mm). This sheet gives what matters and the "
        "tolerances; anything not listed follows the STEP within %s. Nominal values = master params %s (glass_t %s); "
        "STEP checked against them (table below)." % (os.path.basename(SF.path), SF.sha[:16], SF.mtime, gtol,
                                                      P.revision, n(P.d("glass_t"))),
        "Material: %s - heat-stabilised, halogen-free FR, UL94 V-0, GWFI 960 C, GWIT >= 775 C, RTI >= 105 C (e.g. "
        "Durethan BKV30FN04) - design document 8.1. UL CARD: %s (master material.UL_card; %s)." % (
            P.val("material", "frame_material"), P.val("material", "UL_card"),
            P.item("material", "UL_card")["note"].replace(" (GF-1.1 round 4)", "")),
        "Tool: single cavity, two plates, ONE PULL along Z, no slides or lifters. Parting line on the flange outline "
        "in the flange-front plane. Fixed half (A, sheet side): lip, seat ring, pads, counterbores, glass recess, "
        "pips, land break. Gates and ejectors on the B side (back), ejectors on the tail-pocket floor, not on the "
        "land; weld lines off the bosses and tubes (master cad_rules, v2 7).",
        "SHUT-OFF AT THE BEND-GAP SLOT (master cad_rules[%d]): the %s x %s slot is the only through-opening at the "
        "bottom. Its A/B shut-off is NOT a flat face at Z_LAND: the parting runs at the top of the land break on "
        "the bridge side (y %s, Z %s) and at the shelf corner on the front side (y %s, Z_SEAT %s), rising %s over "
        "the %s slot width at the break top (%s = g_bend %s at Z_LAND + the %s deg draft over the %s break - both "
        "are right, do not round one into the other). Build it as an A-side ledge %s x %s across the slot at the "
        "break level, then a telescopic shut-off face along y %s rising to Z_SEAT at >= %s deg (up to %s deg fits); "
        "stepped steel angles B %s deg / A %s deg at the break top - no knife edge (a straight shut-off would leave "
        "a %s deg B-steel knife edge; detail Y). Land break on A, nose R%s on B, slot faces %s deg. No flash on this "
        "shut-off (it would stand in the tail path next to the bead edge); toolmaker to state the final shut-off "
        "design." % (
            so_rule_i, n(g_bend), n(sl.x1 - sl.x0), "%.3f" % SO[0], n2(SO[1]), n2(SO[2]), n2(SO[3]), n2(SO[4]),
            n(SO[5]), n(SO[5]), n2(g_bend), n(draft), n(brk), n(SO[6]), n(SO[7]), n2(SO[2]), n(SO[8]), n(SO_max),
            n(SO[9], 0), n(SO[10], 0), n(SO_knife), n(nose_R), n(draft)),
        "BRIDGE: its inner edge (pocket face, y %s) carries the bond line over %s mm; the bottom land is part of "
        "CTF 3 (flat within %s). Toolmaker to propose gating and venting so that the bridge and the divider rib fill "
        "without weld lines on the land and the bridge stays straight; run a fill / warp study with the bridge." % (
            n2(sl.y1), n(br.x1 - br.x0), n(2 * t_land)),
        "EXCLUSION ZONES (master cad_rules[%d]): no gate, ejector mark, parting line or flash on the lip top, the "
        "lip faces, the seat ring, the four pad faces, the land incl. the bottom land over the bridge (bead band) and "
        "the pip tops; vent witness see note 10." % vent_rule_i,
        "Draft %s deg on every face along Z unless noted; %s deg on the slots and locating faces; counterbores and "
        "coring grooves %s deg. Inside corners left sharp on purpose (pip roots, pad and seat-ring roots, v2 tail "
        "corners, pilot floors): the toolmaker may break them <= 0.2 (design document 8.1). Not sharp: the two "
        "inside corners shelf end (y %s) x tail-pocket side walls (x %s / %s) carry R%s vertical rounds between "
        "Z_SEAT and Z_SHELF_BACK (master cad_rules[%d])." % (
            n(draft), n(draft_loc), n(cb["cb_draft"]), n(SR[1]), n(SR[2]), n(SR[3]), n(SR[0]), sr_rule_i),
        "Seat plane A (seat ring + pads) coplanar %s; parting plane flat within %s unclamped (the bonded glass "
        "flattens the frame in jig J2)." % (n(t_cop), n(t_pp)),
        "Visible lip: %s." % tex,
        "Venting: the lip ring fills last. A vent witness on the lip top is allowed only if flush within %s - "
        "toolmaker to propose the venting (master drawing_tolerances.frame.vent_witness_lip_top = %s and "
        "cad_rules[%d])." % (n(vent_w), n(vent_w), vent_rule_i),
        "Shrinkage about 0.3 % along the flow / 0.5 % across (design document); run a fill / warp study before "
        "steel. Marking >PA6-GF30 FR< and cavity number on the flange back.",
        "T1 report: CMM of the table on sheet 1 (frame free, then clamped on A for items 2, 3, 11, 14, 16); 3 parts.",
        "Tolerances marked [P] are the drafter's proposals (no source states them) - to be confirmed. General "
        "tolerance %s." % gtol,
    ]
    trn = [
        "GEOMETRİ ESASI STEP dosyasıdır (%s); bu resim yalnız önemli ölçüleri ve toleransları verir; diğer her şey "
        "STEP'e göre, %s." % (os.path.basename(SF.path), gtol),
        "Malzeme: PA6-GF30, ısıl stabilize, halojensiz alev geciktirici, UL94 V-0, GWFI 960 °C, GWIT >= 775 °C, siyah. "
        "UL sarı kartında V-0 ve kızdırma teli değerleri (GWFI / GWIT) <= %s mm kalınlıkta yer almalıdır (yalnız "
        "1,5 mm değil)." % P.num("material", r"at <= ([\d.]+) mm", name="UL_card"),
        "Kalıp: tek göz, iki plaka, Z yönünde TEK AÇILMA, maça / sürgü yok. Ayırma çizgisi flanş dış hattında, "
        "flanş ön düzleminde. İticiler kuyruk cebinin tabanında, yapıştırma yüzeyinde değil.",
        "BÜKÜM YUVASINDA KAPAMA: %s x %s yuva alttaki tek açıklıktır. A/B kapaması Z_LAND'de düz bir yüzey "
        "DEĞİLDİR: ayırma, köprü tarafında pah üst kenarında (y %s, Z %s), ön tarafta raf köşesinde (y %s, Z_SEAT %s) "
        "olup pah üst kenarındaki %s yuva genişliği boyunca %s yükselir (%s = Z_LAND'deki g_bend %s + %s pah üzerinde "
        "%s° çıkma; ikisi de doğrudur, biri diğerine yuvarlanmasın). Uygulanabilir şekil: pah seviyesinde yuva "
        "boyunca A tarafında %s x %s basamak, sonra y %s boyunca Z_SEAT'e çıkan, en az %s° (en çok %s°) açılı "
        "teleskopik kapama yüzeyi; pah üst kenarında kademeli çelik açıları B %s° / A %s° - bıçak ağzı yok. Bu "
        "kapamada çapak OLMAYACAKTIR; son kapama tasarımını kalıpçı belirtsin." % (
            n(g_bend), n(sl.x1 - sl.x0), "%.3f" % SO[0], n2(SO[1]), n2(SO[2]), n2(SO[3]), n(SO[5]), n2(SO[4]),
            n(SO[5]), n2(g_bend), n(brk), n(draft), n(SO[6]), n(SO[7]), n2(SO[2]), n(SO[8]), n(SO_max),
            n(SO[9], 0), n(SO[10], 0)),
        "KÖPRÜ: iç kenarı %s mm boyunca yapıştırma hattını taşır; köprü ve ayırıcı kaburga kaynak izi olmadan "
        "dolmalı ve köprü düz kalmalıdır - yolluk ve hava tahliyesini kalıpçı önersin (dolum / çarpılma analizi)." %
        n(br.x1 - br.x0),
        "YASAK BÖLGELER: dudak üstü, dudak iç ve dış yüzleri, oturma halkası, dört ped yüzü, köprü üstündeki alt "
        "yapıştırma yüzeyi dahil tüm yapıştırma yüzeyi ve pim tepeleri üzerinde yolluk, itici izi, ayırma çizgisi "
        "veya çapak OLMAYACAKTIR. Dudak üstünde hava tahliye izi yalnız yüzeyle %s mm içinde aynı seviyede ise "
        "kabul edilir." % n(vent_w),
        "Çıkma açısı Z yönündeki tüm yüzeylerde %s°, yuvalarda ve konum yüzeylerinde %s°. Raf ucu (y %s) ile kuyruk "
        "cebi yan duvarları (x %s / %s) arasındaki iki iç köşe, Z_SEAT ile Z_SHELF_BACK arasında R%s dikey "
        "radyusludur." % (n(draft), n(draft_loc), n(SR[1]), n(SR[2]), n(SR[3]), n(SR[0])),
        "Oturma düzlemi A (halka + pedler) düzlemsellik %s mm; ayırma düzlemi serbest halde %s mm." % (n(t_cop),
                                                                                                    n(t_pp)),
        "[P] işaretli toleranslar teklif amaçlı önerimizdir; genel tolerans %s." % gtol,
    ]
    yN = s2.notes(240.0, 282.0, 168.0, notes, fs=5.6, head="NOTES", head_fs=7.0, gap=0.3)
    fname = os.path.basename(SF.path)
    trn = [tr(x).replace(tr(fname), fname) for x in trn]
    yT = s2.notes(240.0, yN - 1.0, 168.0, trn, fs=5.6, head="NOTLAR (Türkçe)", head_fs=7.0, gap=0.3)
    s2.T(240.0, yT - 3.6, "STEP vs MASTER (measured on the STEP by make_frame.py; all %d within tolerance: %s)" % (
        len(rows), "yes" if all(r["ok"] for r in rows) else "NO"), fs=6.6, weight="bold")
    half = (len(rows) + 1) // 2
    ym = yT - 5.0
    for j, part in enumerate((rows[:half], rows[half:])):
        mrows = [["sec.", "check", "meas.", "exp.", "ok"]]
        for r in part:
            mrows.append([r["group"], r["what"], "-" if r["measured"] is None else n(r["measured"], 3),
                          n(r["expected"], 3), "yes" if r["ok"] else "NO"])
        yy = s2.table_wrapped(240.0 + j * 85.0, ym, [7, 50, 11, 11, 5], mrows, fs=4.4, pad=0.6)
        if j == 0:
            ym_low = yy
        else:
            ym_low = min(ym_low, yy)
    s2.title_block({
        "title": "FRAME (GlassFront) - INSPECTION DRAWING, sheet 2/2",
        "subtitle": "sections from the STEP, notes for the toolmaker  /  çerçeve kontrol resmi (kalıp teklifi için)",
        "source": "STEP %s (sha256 %s...); params %s" % (os.path.basename(SF.path), SF.sha[:16], master_ref(P)),
        "project": "files: GF_Frame_Inspection.pdf (2 pages) / _p1.png / _p2.png / .dxf",
        "change": "%s. Sections G-G, detail Y (nose, break, A/B parting), H-H; note 4 stepped / telescopic shut-off "
                  "(cad_rules[%d]); note 7 R%s shelf-end corners." % (rev_note(P), so_rule_i, n(SR[0])),
        "dwg": "GF-D50", "rev": P.revision, "scale": "4:1, 10:1, 3:1, 2.5:1, 2:1",
        "date": datetime.date.today().isoformat(), "drawn": "make_frame.py",
    }, h=42.0)
    iss2 = s2.check_layout()

    base = os.path.join(out_dir, "GF_Frame_Inspection")
    with PdfPages(base + ".pdf") as pdf:
        pdf.savefig(s1.fig, dpi=300)
        pdf.savefig(s2.fig, dpi=300)
    s1.fig.savefig(base + "_p1.png", dpi=200)
    s2.fig.savefig(base + "_p2.png", dpi=200)
    plt.close(s1.fig)
    plt.close(s2.fig)

    # ------------------------------------------------------------------ DXF (front view 1:1 + sections + CTF outlines)
    doc, msp = new_dxf([("FRONT_VIEW", 7, "CONTINUOUS"), ("BACK_VIEW", 8, "CONTINUOUS"),
                        ("CTF_OUTLINES", 1, "DASHED"), ("SECTIONS", 5, "CONTINUOUS"), ("TEXT", 7, "CONTINUOUS")])
    for ln in fv:
        if len(ln) >= 2:
            msp.add_lwpolyline(ln, dxfattribs={"layer": "FRONT_VIEW"})
    offB = fl.w + 40.0
    for ln in bv:
        if len(ln) >= 2:
            msp.add_lwpolyline([(x + offB, y) for x, y in ln], dxfattribs={"layer": "BACK_VIEW"})
    for r in (G.lip_in, G.lip_out, G.seat_out, G.flange, G.pocket, G.slot_bg, G.rib):
        dxf_rect(msp, r, "CTF_OUTLINES")
    for k_, f in G.F.items():
        dxf_poly(msp, G.slot(k_), "CTF_OUTLINES")
        dxf_poly(msp, stadium_pts(f["u"], f["v"], f["au"], f["av"], cb["cb_l"], cb["cb_w"]), "CTF_OUTLINES")
    # full plane sections, stacked below the views (each one spans the whole frame), 1:1
    dxf_text(msp, "SECTIONS 1:1: x = t (E-E / F-F: s outward from the glass edge; G-G / H-H: abs y - %s), "
             "y = -(depth behind the flush plane)" % n(gy1), fl.x0, fl.y0 - 22.0, 2.5)
    for i, (nm, sec, t_off) in enumerate((("E-E", secA, 0.0), ("F-F", secB, 0.0), ("G-G", secG, -gy1),
                                          ("H-H", secH, -gy1))):
        yoff = fl.y0 - 40.0 - 35.0 * i
        for outer, inners in sec:
            for ring in [outer] + inners:
                pts = [(t + t_off, yoff - (z - Zg)) for t, z in ring]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SECTIONS"})
        dxf_text(msp, "SECTION %s" % nm, fl.x1 + 30.0, yoff - 8.0, 3.0)
    dxf_text(msp, "GF-D50 frame %s: FRONT_VIEW = hidden-line projection of %s (front view, origin = datum B); BACK_VIEW "
             "offset %s in u; CTF_OUTLINES = nominal outlines from the params" % (
                 P.revision, os.path.basename(SF.path), n(offB)), fl.x0, fl.y1 + 8.0, 3.0)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(base + ".dxf")
    return {"files": [base + ".dxf", base + ".pdf", base + "_p1.png", base + "_p2.png"],
            "layout_issues": iss1 + iss2, "params_used": dict(sorted(P.used.items())), "choices_used": C.used,
            "step": {"path": SF.path, "sha256": SF.sha, "mtime": SF.mtime, "bbox": [round(x, 4) for x in SF.bbox],
                     "volume_mm3": round(SF.volume, 1), "faces": SF.n_faces,
                     "sha256_matches_master_as_modelled":
                         SF.sha == P._use("as_modelled_%s/frame_step/sha256" % P.revision,
                                          P.raw["as_modelled_%s" % P.revision]["frame_step"]["sha256"])},
            "counterbore_params": {"cb_w": cb["cb_w"], "cb_l": cb["cb_l"]},
            "counterbore_measured": {k_: {"w": None if v[0] is None else round(v[0], 3),
                                          "l": None if v[1] is None else round(v[1], 3)} for k_, v in meas_cb.items()},
            "step_vs_master": rows, "notes_en": notes, "notes_tr": trn, "ctf": ctf,
            "lowest_y": [round(yc_, 1), round(ym_low, 1), round(yN, 1), round(yT, 1)]}


if __name__ == "__main__":
    r = make()
    print("issues:", len(r["layout_issues"]), r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
    print(r["step"])
    print(r["counterbore_params"], r["counterbore_measured"])
    for x in r["step_vs_master"]:
        print(("OK " if x["ok"] else "NO ") + x["what"], x["measured"], x["expected"])
