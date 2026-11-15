"""GF-D50 frame inspection drawing for the mould RFQ. Views and sections are taken from the frame STEP (CadQuery /
OCCT: hidden-line projection and plane sections), the dimensions and tolerances from the master (and from the
concept / design document; proposals marked [P] and listed in drafting_choices.json). The script also measures the
STEP at the critical places and compares with the master, so the drawing cannot silently disagree with the part.

  <venv>/Scripts/python.exe make_frame.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Frame_Inspection.{dxf,pdf},
                                               GF_Frame_Inspection_p1.png, GF_Frame_Inspection_p2.png
"""
import datetime
import hashlib
import math
import os
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
                       stadium_pts, bulge_to_points)
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


def measure(SF, P, G):
    """measure the STEP at the critical places; every row = (what, measured, expected, tol, ok)"""
    Zg = P.level("Z_GLASS_FRONT")
    Zs = P.level("Z_SHEET_BACK")
    Zff, Zfb = P.level("Z_FLANGE_FRONT"), P.level("Z_FLANGE_BACK")
    Zl, Ztt = P.level("Z_LAND"), P.level("Z_TUBE_TOP")
    tan1 = math.tan(math.radians(P.val("carried_over_from_v2", "draft")))
    rows = []

    def row(what, meas, exp, tol, unit="mm"):
        ok = meas is not None and abs(meas - exp) <= tol
        rows.append({"what": what, "measured": None if meas is None else round(meas, 4), "expected": round(exp, 4),
                     "tol": tol, "ok": bool(ok)})

    # section E-E: Y = -60 (abs y 60), left side; t = s = 13.11 - X (outward)
    gx0 = P.rect("glass").x0
    secA = SF.section((gx0, -60.0, 0), (-1, 0, 0), (0, 1, 0))
    s_li, s_lo = gx0 - P.rect("lip_in").x0, gx0 - P.rect("lip_out").x0
    s_so = gx0 - P.rect("seat_ring_out").x0
    zs = cross_v(secA, (s_li + s_lo) / 2.0, Zg - 1, Zg + 2)
    row("E-E lip top Z (= Z_GLASS_FRONT, flush plane)", zs[0] if zs else None, Zg, 0.005)
    zs = cross_v(secA, (s_lo + s_so) / 2.0, Zg - 1, Zg + 3)
    row("E-E seat ring Z (datum A = Z_SHEET_BACK)", zs[0] if zs else None, Zs, 0.005)
    zs = cross_v(secA, 10.0, Zg - 1, Zg + 6)
    row("E-E flange front Z", zs[0] if zs else None, Zff, 0.005)
    row("E-E flange back Z", zs[1] if len(zs) > 1 else None, Zfb, 0.005)
    zs = cross_v(secA, -3.0, Zg - 1, Zg + 6)
    row("E-E land Z (recess floor)", zs[0] if zs else None, Zl, 0.005)
    zm = (Zg + Zs) / 2.0
    ts = cross_h(secA, zm, 0.0, 2.0)
    if len(ts) >= 2:
        e_in, e_out = s_li - (zm - Zg) * tan1, s_lo - (Zs - zm) * tan1
        row("E-E lip inner face at mid-height (s, 1 deg)", ts[0], e_in, 0.01)
        row("E-E lip outer face at mid-height (s, 1 deg)", ts[-1], e_out, 0.01)
        row("E-E lip width at mid-height", ts[-1] - ts[0], e_out - e_in, 0.01)
    # horizontal sections through the pads / counterbores / slots / coring
    cb, co = G.fastener_cuts()
    f1, f5 = P.fast("F1"), P.fast("F5")
    meas_cb = {}
    for nm, f, floor in (("F1", f1, cb["cb_floor_F1-F4"]), ("F5", f5, cb["cb_floor_F5-F8"])):
        ax_, ay_ = f["slot_axis"][0], -f["slot_axis"][1]          # STEP Y = -y
        cx, cy = f["x_abs"], -f["y_abs_down"]
        tcb = math.tan(math.radians(cb["cb_draft"]))
        z_open = Zs if f["front_pad"].startswith("moulded") else Zff     # F5-F8: no pad, the cb opens at Zff
        h0 = SF.hsection(z_open + 0.02)
        L, W = hole_extent(h0, cx, cy, ax_, ay_)
        dz0 = z_open + 0.02 - Zs
        meas_cb[nm] = (None if W is None else W + 2 * dz0 * tcb, None if L is None else L + 2 * dz0 * tcb)
        where = "seat plane A" if z_open == Zs else "flange front (no pad)"
        row("%s counterbore width at the %s (+0.02)" % (nm, where), W, cb["cb_w"] - 2 * dz0 * tcb, 0.02)
        row("%s counterbore length at the %s (+0.02)" % (nm, where), L, cb["cb_l"] - 2 * dz0 * tcb, 0.02)
        zb = floor - cb["cb_r"] - 0.05                                     # above the R floor round
        hb = SF.hsection(Zs + zb)
        L2, W2 = hole_extent(hb, cx, cy, ax_, ay_)
        ha = SF.hsection(Zs + floor + 0.05)
        L3, W3 = hole_extent(ha, cx, cy, ax_, ay_)
        row("%s counterbore floor %s above A: still counterbore %s above the floor (width)" % (
            nm, n(floor), n(cb["cb_r"] + 0.05)), W2, cb["cb_w"] - 2 * zb * tcb, 0.03)
        row("%s ... and slot 0.05 behind the floor (width)" % nm, W3, G.slot_w + 2 * (floor + 0.05 - (Zff - Zs))
            * math.tan(math.radians(0.5)) if Zs + floor + 0.05 > Zff else G.slot_w, 0.03)
        hs = SF.hsection(Zfb - 0.3)
        L4, W4 = hole_extent(hs, cx, cy, ax_, ay_)
        exp_w = G.slot_w + 2 * (Zfb - 0.3 - Zff) * math.tan(math.radians(0.5))
        row("%s slot width 0.3 in front of the flange back (0.5 deg draft)" % nm, W4, exp_w, 0.02)
        row("%s slot length 0.3 in front of the flange back" % nm, L4, G.slot_l + (exp_w - G.slot_w), 0.02)
        hc = SF.hsection(Ztt - 0.2)
        # coring groove: annulus around the tube -> look for the ring whose bbox is centred on F
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
            row("%s coring groove inner radius 0.2 below the tube top" % nm, min(rr), co["core_r_in"] + dd, 0.03)
            row("%s coring groove outer radius 0.2 below the tube top" % nm, max(rr), co["core_r_out"] - dd, 0.03)
    # tail pocket + clearance pocket at the land level
    hl = SF.hsection(Zl + 0.02)
    tp, pk = P.rect("tail_pocket"), P.rect("pocket")
    from matplotlib.path import Path as MP
    for outer, inners in hl:
        for ring in inners:
            if MP(ring).contains_point((103.85, -(tp.y0 + tp.y1) / 2.0)):
                ya = -ring[:, 1]
                dr = (P.level("Z_SEAT") - (Zl + 0.02)) * tan1      # pocket size is defined at Z_SEAT, 1 deg
                row("clearance pocket x0 at the land (defined at Z_SEAT, 1 deg)", float(ring[:, 0].min()),
                    pk.x0 - dr, 0.03)
                row("clearance pocket x1 at the land (defined at Z_SEAT, 1 deg)", float(ring[:, 0].max()),
                    pk.x1 + dr, 0.03)
                row("clearance pocket y0 at the land (defined at Z_SEAT, 1 deg)", float(ya.min()), pk.y0 - dr, 0.03)
                Ym = -(tp.y0 + tp.y1) / 2.0
                q = np.vstack([ring, ring[:1]])
                xs = []
                for i in range(len(q) - 1):
                    (xa, ya_), (xb, yb) = q[i], q[i + 1]
                    if (ya_ - Ym) * (yb - Ym) < 0:
                        xs.append(xa + (Ym - ya_) * (xb - xa) / (yb - ya_))
                row("tail pocket x0 at the land (GF-1.1)", min(xs) if xs else None, tp.x0, 0.03)
                row("tail pocket x1 at the land (GF-1.1)", max(xs) if xs else None, tp.x1, 0.03)
                row("tail pocket bottom y1 at the land", float(ya.max()), tp.y1, 0.03)
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
    rows, meas_cb = measure(SF, P, G)
    xc, yc = G.fv.xc, G.fv.yc
    Zg = P.level("Z_GLASS_FRONT")
    Zs, Zff, Zfb = P.level("Z_SHEET_BACK"), P.level("Z_FLANGE_FRONT"), P.level("Z_FLANGE_BACK")
    Zl, Ztt, Zpcb = P.level("Z_LAND"), P.level("Z_TUBE_TOP"), P.level("Z_PCB")
    Zlpb, Zseat = P.level("Z_LANDPLATE_BACK"), P.level("Z_SEAT")
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
    # venting / exclusion zones from the master (GF-1.1 round 3): drawing_tolerances.frame.vent_witness_lip_top
    # and the cad_rules entry on the moulding exclusion zones
    vent_it = P.item("drawing_tolerances.frame", "vent_witness_lip_top")
    vent_w = vent_it["value"]
    assert "toolmaker to propose" in vent_it["note"]
    vent_rule_i = [i for i, r in enumerate(P.get("cad_rules")) if "vent witness on the lip top" in r]
    assert len(vent_rule_i) == 1, vent_rule_i
    vent_rule_i = vent_rule_i[0]
    # counterbore reference plane (master cb_w / cb_l notes): F5-F8 open at the flange front, 1.0 behind A
    cb_rx = r"opens at the flange front \(([\d.]+) deeper\), where it measures ([\d.]+) x ([\d.]+)"
    cb5_dz = P.num("fasteners.counterbore", cb_rx, 1, name="cb_w")
    cb5_w = P.num("fasteners.counterbore", cb_rx, 2, name="cb_w")
    cb5_l = P.num("fasteners.counterbore", cb_rx, 3, name="cb_w")
    assert (cb5_w, cb5_l) == (P.num("fasteners.counterbore", cb_rx, 2, name="cb_l"),
                              P.num("fasteners.counterbore", cb_rx, 3, name="cb_l"))
    _tcb = math.tan(math.radians(cb["cb_draft"]))
    assert abs(cb["cb_w"] - 2 * cb5_dz * _tcb - cb5_w) < 0.0006 and abs(cb["cb_l"] - 2 * cb5_dz * _tcb - cb5_l) < 0.0006
    assert abs(cb5_dz - (Zff - Zs)) < 1e-6, (cb5_dz, Zff - Zs)
    lip_root = P.d("lip_w_root_as_designed")
    lip_top = P.d("lip_w_top_as_designed")

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
    f5 = P.fast("F5")
    secC = SF.section((f5["x_abs"], -f5["y_abs_down"], 0), (0, 1, 0), (1, 0, 0))
    xD = 125.0
    secD = SF.section((xD, -P.rect("glass").y1, 0), (0, -1, 0), (1, 0, 0))

    # ================================================================== page 1: views + tables
    s1 = Sheet()
    s1.frame()
    k1 = 0.5
    V1 = View(s1, 82.0, 205.0, k1)
    for ln in fv:
        q = V1.Pa(ln)
        s1.L(q[:, 0], q[:, 1], w=XTHIN, c="k", geom=False)
    V2 = View(s1, 212.0, 205.0, k1)
    for ln in bv:
        q = V2.Pa(ln)
        s1.L(q[:, 0], q[:, 1], w=XTHIN, c="k", geom=False)
    fl = G.flange
    s1.T(18.0, 279.0, "FRONT VIEW (sheet side, seen from in front of the oven)   1 : 2", fs=8.0, weight="bold")
    s1.T(150.0, 268.0, "BACK VIEW (PCB side, seen from behind)   1 : 2", fs=8.0, weight="bold")
    s1.T(18.0, 274.5, "Views = hidden-line projection of the STEP (geometry master). Red = section lines / datums.",
         fs=6.0)
    # overall dims (front view)
    top = V1.P(0, fl.y1)[1]
    s1.dim_h(*V1.P(fl.x0, fl.y1), *V1.P(fl.x1, fl.y1), top + 5.0, "%s (TG5)" % n2(fl.w), fs=6.5)
    s1.dim_v(*V1.P(fl.x0, fl.y0), *V1.P(fl.x0, fl.y1), V1.P(fl.x0, 0)[0] - 5.0, "%s" % n2(fl.h), fs=6.5)
    # datum B (recess centre) and section lines on the front view
    x0p, y0p = V1.P(0, 0)
    s1.circle(x0p, y0p, 1.2, ec=C_CTF, w=THIN, geom=False)
    s1.T(x0p + 2.0, y0p + 1.0, "B", fs=7, weight="bold", color=C_CTF)

    def cut_line(V, p0, p1, lab):
        (xa, ya), (xb, yb) = V.P(*p0), V.P(*p1)
        s1.L([xa, xb], [ya, yb], w=XTHIN, c=C_CTF, geom=False, dashes=(8, 2, 2, 2))
        for (x, y) in ((xa, ya), (xb, yb)):
            s1.circle(x, y, 0.6, fc=C_CTF, ec=C_CTF, geom=False)
        s1.T(xb + 1.0, yb + 1.0, lab, fs=7, weight="bold", color=C_CTF)
    vA = yc - 60.0
    cut_line(V1, (G.pocket.x1 - 2, vA), (fl.x1 + 3, vA), "E")
    F1 = G.F["F1"]
    cut_line(V1, (F1["u"] + F1["au"] * 28, F1["v"] + F1["av"] * 28), (F1["u"] - F1["au"] * 11, F1["v"] - F1["av"] * 11),
             "F")
    cut_line(V1, (0, G.pocket.y1 - 2), (0, fl.y1 + 2), "G")
    uD = -(xD - xc)
    cut_line(V1, (uD, G.pocket.y0 + 2), (uD, fl.y0 - 2), "H")
    # fastener table (right column)
    xt, yt = 278.0, 268.0
    s1.T(xt, yt, "FASTENER FEATURES (positions to datum B, front view)", fs=7.0, weight="bold")
    frows = [["F", "u", "v", "axis deg", "front pad", "cb floor"]]
    for k_, f in G.F.items():
        frows.append([k_, n(f["u"]), n(f["v"]), n(math.degrees(math.atan2(f["av"], f["au"])) + 0.0, 2),
                      ("dia %s" % n(G.pad_d)) if f["pad"] else "none",
                      n(cb["cb_floor_F1-F4"] if f["pad"] else cb["cb_floor_F5-F8"])])
    yt = s1.table(xt, yt - 1.0, [0, 8, 26, 46, 66, 90], frows, fs=6.0, widths=128)
    for ln in s1.wrap("All eight: slot %s +%s/%s x %s ±%s (stadium at the flange front, %s deg draft wider to the back, "
                      "long axis to datum B), position ±%s. Counterbore %s x %s +%s/%s stadium, coaxial, size defined at "
                      "datum A (Z_SHEET_BACK = the pad face at F1-F4); at F5-F8 (no pad) it opens at the flange "
                      "front, %s behind A, where it measures %s x %s (%s deg draft). Floor above A as listed +%s/%s, "
                      "R%s. Tube top dia %s, %s behind A ±%s [P]; coring "
                      "groove r %s-%s (r_in +%s/-%s [P]), %s deep from the tube top, R%s, %s deg." % (
                          n(G.slot_w), tn(slT[0]), tn(slT[1]), n(G.slot_l), tn(slT[2]), n(draft_loc), n(t_slot),
                          n(cb["cb_w"]), n(cb["cb_l"]), tn(cbT[0]), tn(cbT[1]), n(cb5_dz), n(cb5_w), n(cb5_l),
                          n(cb["cb_draft"]), tn(cbT[2]), tn(cbT[3]), n(cb["cb_r"]),
                          n(P.d("pad_d")), n(Ztt - Zs), n(ttT), n(co["core_r_in"]),
                          n(co["core_r_out"]), tn(crT[0]), tn(crT[1]), n(co["core_depth"]), n(co["core_floor_r"]),
                          n(co["core_draft"])), 128.0, 5.9):
        yt -= 2.7
        s1.T(xt, yt, ln, fs=5.9)
    yt -= 5.0
    s1.T(xt, yt, "DATUMS", fs=7.0, weight="bold")
    for ln in s1.wrap("A = seat plane: seat-ring top + the 4 corner pads (all at Z_SHEET_BACK), coplanar %s. "
                      "B = centre of the recess wall (lip inner face) = glass centre = cut-out centre; axes along the "
                      "recess sides. Z values below are distances behind A (towards the PCB) unless noted." %
                      n(t_cop), 128.0, 5.9):
        yt -= 2.7
        s1.T(xt, yt, ln, fs=5.9)
    # CTF table (bottom)
    ctf = [["#", "critical-to-function feature", "nominal", "tolerance", "source"],
           ["1", "seat plane A (seat ring + pads F1-F4)", "Z_SHEET_BACK", "coplanar %s" % n(t_cop), "master"],
           ["2", "lip top above A (lip height = t_sheet)", n2(Zs - Zg), "±%s" % n(t_lip), "master"],
           ["3", "land below the lip top (recess depth = glass_t + t_bond)", n2(Zl - Zg),
            "±%s (land flat within %s)" % (n(t_land), n(2 * t_land)), "master"],
           ["4", "recess wall = lip inner face at the lip top", "%s x %s R%s" % (n2(G.lip_in.w), n2(G.lip_in.h),
                                                                                 n(G.lip_in.R)),
            "±%s, R ±%s, %s deg" % (n(lipT), n(lipT), n(draft)), "[P]"],
           ["5", "lip outer face at the lip root (A)", "%s x %s R%s" % (n2(G.lip_out.w), n2(G.lip_out.h),
                                                                       n(G.lip_out.R)),
            "±%s, R ±%s, %s deg" % (n(lipT), n(lipT), n(draft)), "[P]"],
           ["6", "lip width (root / top as designed)", "%s (%s / %s)" % (n(G.lip_w), n(lip_root, 4),
                                                                        n(lip_top, 4)),
            "±%s; top edges R0.3, root R0.2" % n(lipW), "[P] / design doc 8.1"],
           ["7", "seat-ring outer edge", "%s x %s R%s" % (n2(G.seat_out.w), n2(G.seat_out.h), n(G.seat_out.R)),
            gtol, "master"],
           ["8", "slots F1-F8 (see table above)", "%s x %s" % (n(G.slot_w), n(G.slot_l)),
            "+%s/%s x ±%s; position ±%s" % (tn(slT[0]), tn(slT[1]), tn(slT[2]), n(t_slot)), "[P] / master"],
           ["9", "counterbores (stud weld flange); size at datum A (Z_SHEET_BACK); F5-F8 open at the flange "
                 "front, %s behind A" % n(cb5_dz),
            "%s x %s at A (F5-F8: %s x %s at the flange front), floor %s / %s" % (
               n(cb["cb_w"]), n(cb["cb_l"]), n(cb5_w), n(cb5_l), n(cb["cb_floor_F1-F4"]), n(cb["cb_floor_F5-F8"])),
            "+%s/%s; floor +%s/%s" % (tn(cbT[0]), tn(cbT[1]), tn(cbT[2]), tn(cbT[3])), "[P]"],
           ["10", "tube tops (washer / rivet seats)", "%s behind A" % n(Ztt - Zs), "±%s" % n(ttT), "[P]"],
           ["11", "pips P1-P8 above the land", "dia %s x %s" % (n(P.d("pip_d")), n(P.d("pip_h"))),
            "height ±%s" % n(pip_tol), "master"],
           ["12", "panel clearance pocket at the shelf front (Z_SEAT); %s deg draft, %s per side larger at the "
                  "land" % (n(draft), "%.2f" % ((P.level("Z_SEAT") - Zl) * math.tan(math.radians(draft)))),
            "%s x %s R%s" % (n2(G.pocket.w), n2(G.pocket.h), n(G.pocket.R)), gtol, "master + STEP"],
           ["13", "tail pocket at the land", "x %s-%s abs, to y %s, R%s" % (
               n(P.rect("tail_pocket").x0), n(P.rect("tail_pocket").x1), n(P.rect("tail_pocket").y1),
               n(P.rect("tail_pocket").R)), gtol, "master"],
           ["14", "PCB boss tops H1-H9 (Z_PCB)", "%s behind A" % n2(Zpcb - Zs),
            "coplanar %s, ±%s" % (n(bsT[0]), n(bsT[1])), "[P] (v2 geometry)"],
           ["15", "flange (parting line on its outline, front plane)", "%s x %s R%s, t %s" % (
               n2(fl.w), n2(fl.h), n(fl.R), n(P.d("flange_t"))), "flatness unclamped %s" % n(t_pp), "master"],
           ["16", "all other dimensions", "STEP", gtol, "master"]]
    s1.T(16.0, 141.0, "CRITICAL-TO-FUNCTION DIMENSIONS  (nominal from the master params, glass_t %s; [P] = tolerance "
                      "proposed by the drafter)" % n(P.d("glass_t")), fs=7.0, weight="bold")
    yc_ = s1.table_wrapped(16.0, 139.0, [9, 150, 90, 100, 45], ctf, fs=6.0)
    # measured table (right)

    s1.title_block({
        "title": "FRAME (GlassFront) - INSPECTION DRAWING, sheet 1/2",
        "subtitle": "for the mould RFQ: geometry master = STEP; this sheet = what matters + tolerances",
        "source": "STEP %s (sha256 %s..., %s); params %s" % (os.path.basename(SF.path), SF.sha[:16], SF.mtime,
                                                             P.revision),
        "project": "files: GF_Frame_Inspection.pdf (2 pages) / _p1.png / _p2.png / .dxf",
        "change": "%s round 3: counterbore size referred to datum A (F5-F8: %s x %s at the flange front); venting "
                  "per the master (flush within %s, no longer [P])." % (P.revision, n(cb5_w), n(cb5_l), n(vent_w)),
        "dwg": "GF-D50", "rev": P.revision, "scale": "1:2", "date": datetime.date.today().isoformat(),
        "drawn": "make_frame.py",
    }, h=42.0)
    iss1 = s1.check_layout()

    # ================================================================== page 2: sections + notes
    s2 = Sheet()
    s2.frame()
    # E-E 4:1 (side, abs left / front-view right), s outward to the right
    kA = 4.0
    tA0, tA1, dA0, dA1 = -12.0, 22.5, -0.6, 12.6
    PA = section_block(s2, secA, 22.0, 268.0, kA, tA0, tA1, dA0, dA1, Zg,
                       "SECTION E-E  side (abs y 60), s outward from the glass edge   4 : 1")
    # datums / dims on E-E from the master (nominal); positions of the features along s
    s_li, s_lo = gx0 - P.rect("lip_in").x0, gx0 - P.rect("lip_out").x0
    s_so = gx0 - P.rect("seat_ring_out").x0
    dz = lambda Z: Z - Zg
    xr = PA(tA1, 0)[0] + 4.0
    s2.dim_v(*PA(-9.5, dz(Zl)), *PA(-9.5, dz(Zg)), PA(-9.5, 0)[0], "%s ±%s" % (n2(Zl - Zg), n(t_land)),
             fs=6.3, c=C_CTF)
    s2.dim_v(*PA(tA1, dz(Zff)), *PA(tA1, dz(Zfb)), xr, "%s" % n(Zfb - Zff), fs=6.3, side="right")
    s2.dim_v(*PA(tA1, dz(Zs)), *PA(tA1, dz(Zff)), xr, "%s" % n(Zff - Zs), fs=6.3, side="right")
    # datum A triangle on the seat ring top
    xa_, ya_ = PA((s_lo + s_so) / 2.0, dz(Zs))
    s2.poly([(xa_ - 1.6, ya_ - 3.0), (xa_ + 1.6, ya_ - 3.0), (xa_, ya_)], fc=C_CTF, ec=C_CTF, w=XTHIN, geom=False,
            z=6)
    s2.L([xa_, xa_], [ya_ - 3.0, ya_ - 5.0], w=XTHIN, c=C_CTF, geom=False)
    s2.T(xa_ + 1.8, ya_ - 6.6, "A", fs=7.5, weight="bold", color=C_CTF)
    yA = PA(0, dA1)[1]
    s2.dim_h(*PA(-(P.rect("pocket").x0 - gx0), dz(Zl)),
             *PA(0.0, dz(Zl)), yA - 5.0, "land %s" % n2(P.rect("pocket").x0 - gx0), fs=6.0)
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
    # G-G 3:1 mid-side fastener F5
    tC0, tC1 = -22.0, 11.0
    PC = section_block(s2, secC, 22.0, 140.0, kB, tC0, tC1, dB0, dB1, Zg,
                       "SECTION G-G  mid-side fastener F5 (no pad; outward to the right)   3 : 1", title_dy=10.0)
    s2.dim_v(*PC(-G.slot_l / 2, dz(Zs + cb["cb_floor_F5-F8"])), *PC(-G.slot_l / 2, dz(Zs)), PC(-1.0, 0)[0], None,
             c=C_CTF)
    s2.T(PC(-0.6, 0)[0], PC(0, dz(Zs) + 0.4)[1], "%s +%s/%s" % (n(cb["cb_floor_F5-F8"]), tn(cbT[2]),
                                                                       tn(cbT[3])), fs=5.8, color=C_CTF, va="top")
    s2.dim_v(*PC(tC1, dz(Zs)), *PC(tC1, dz(Zff)), PC(tC1, 0)[0] + 2.0, None)
    s2.T(PC(tC1, 0)[0] + 3.0, PC(0, dz(Zs) + 0.5)[1], "flange front %s behind A (no pad at F5-F8)" % n(Zff - Zs),
         fs=5.8, va="center")
    # H-H 2:1 chin / tail pocket
    kD = 2.0
    tD0, tD1 = -36.0, 22.0
    dD1 = 4.05 - Zg + 0.5
    PD = section_block(s2, secD, 22.0, 92.0, kD, tD0, tD1, -0.6, dD1, Zg,
                       "SECTION H-H  chin / tail pocket at abs x %s (bottom edge, outward to the right)   2 : 1" %
                       n(xD), title_dy=10.0)
    tp = P.rect("tail_pocket")
    for i_, ln in enumerate(("tail pocket: open to the back, no floor", "(the glass chin closes the front)")):
        s2.T(*PD(-21.0, 7.0 + 1.6 * i_), ln, fs=5.8, ha="center", va="center")
    s2.dim_h(*PD(-(P.rect("glass").y1 - tp.y1), dz(Zl)), *PD(0.0, dz(Zl)), PD(0, -0.6)[1] + 4.0,
             "bottom land %s" % n2(P.rect("glass").y1 - tp.y1), fs=6.0,
             text_at=(PD(-(P.rect("glass").y1 - tp.y1), 0)[0] - 1.0, PD(0, -0.6)[1] + 4.6), ha="right")
    # notes
    notes = [
        "GEOMETRY MASTER: %s (sha256 %s, %s; the file is written in cm, read in mm). This sheet gives what matters "
        "and the tolerances; anything not listed follows the STEP within %s. Nominal values = master params %s "
        "(glass_t %s); STEP checked against them (sheet 1)." % (os.path.basename(SF.path), SF.sha[:16], SF.mtime,
                                                                gtol, P.revision, n(P.d("glass_t"))),
        "Material: %s - heat-stabilised, halogen-free FR, UL94 V-0, GWFI 960 C, GWIT >= 775 C, RTI >= 105 C (e.g. "
        "Durethan BKV30FN04) - design document 8.1. UL CARD: %s (master material.UL_card; %s)." % (
            P.val("material", "frame_material"), P.val("material", "UL_card"),
            P.item("material", "UL_card")["note"].replace(" (GF-1.1 round 4)", "")),
        "Tool: single cavity, two plates, ONE PULL along Z, no slides or lifters. Parting line on the flange outline "
        "in the flange-front plane. Fixed half (A, sheet side): lip, seat ring, pads, counterbores, glass recess, "
        "pips. Gates and ejectors on the B side (back), weld lines off the bosses and tubes (master cad_rules, v2 7).",
        "EXCLUSION ZONES (master cad_rules[%d]): no gate, ejector mark, parting line or flash on the lip top, the "
        "lip outer and inner faces, the seat ring, the four pad faces, the land (bead band) and the pip tops; vent "
        "witness see note 8." % vent_rule_i,
        "Draft %s deg on every face along Z unless noted; %s deg on the slots and locating faces; counterbores and "
        "coring grooves %s deg. Inside corners left sharp on purpose (pip roots, pad and seat-ring roots, v2 tail "
        "and shelf corners, pilot floors): the toolmaker may break them <= 0.2 (design document 8.1)." % (
            n(draft), n(draft_loc), n(cb["cb_draft"])),
        "Seat plane A (seat ring + pads) coplanar %s; parting plane flat within %s unclamped (the bonded glass "
        "flattens the frame in jig J2)." % (n(t_cop), n(t_pp)),
        "Visible lip: %s." % tex,
        "Venting: the lip ring fills last. A vent witness on the lip top is allowed only if flush within %s - "
        "toolmaker to propose the venting (master drawing_tolerances.frame.vent_witness_lip_top = %s and "
        "cad_rules[%d]; this replaces the concept text 'vents at the lip top every ~50 mm')." % (
            n(vent_w), n(vent_w), vent_rule_i),
        "Shrinkage about 0.3 % along the flow / 0.5 % across (design document); run a fill / warp study before "
        "steel. Marking >PA6-GF30 FR< and cavity number on the flange back.",
        "T1 report: CMM of the table on sheet 1 (frame free, then clamped on A for items 2, 3 and 11); 3 parts.",
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
        "flanş ön düzleminde.",
        "YASAK BÖLGELER: dudak üstü, dudak iç ve dış yüzleri, oturma halkası, dört ped yüzü, yapıştırma yüzeyi ve "
        "pim tepeleri üzerinde yolluk, itici izi, ayırma çizgisi veya çapak OLMAYACAKTIR. Dudak üstünde hava "
        "tahliye izi yalnız yüzeyle %s mm içinde aynı seviyede ise kabul edilir; tahliyeyi kalıpçı önersin." % n(vent_w),
        "Çıkma açısı Z yönündeki tüm yüzeylerde %s°, yuvalarda ve konum yüzeylerinde %s°." % (n(draft),
                                                                                               n(draft_loc)),
        "Oturma düzlemi A (halka + pedler) düzlemsellik %s mm; ayırma düzlemi serbest halde %s mm." % (n(t_cop),
                                                                                                    n(t_pp)),
        "Görünen dudak: siyah, boyasız kalıp yüzeyi; VDI 3400 Ref 24 doku opsiyon olarak fiyatlandırılsın.",
        "[P] işaretli toleranslar teklif amaçlı önerimizdir; genel tolerans %s." % gtol,
    ]
    yN = s2.notes(240.0, 282.0, 168.0, notes, fs=5.8, head="NOTES", head_fs=7.0, gap=0.35)
    fname = os.path.basename(SF.path)
    trn = [tr(x).replace(tr(fname), fname) for x in trn]
    yT = s2.notes(240.0, yN - 1.5, 168.0, trn, fs=5.8, head="NOTLAR (Türkçe)", head_fs=7.0, gap=0.35)
    s2.T(240.0, yT - 4.0, "STEP vs MASTER (measured on the STEP by make_frame.py)", fs=7.0, weight="bold")
    mrows = [["check", "measured", "expected", "ok"]]
    for r in rows:
        mrows.append([r["what"], "-" if r["measured"] is None else n(r["measured"], 3), n(r["expected"], 3),
                      "yes" if r["ok"] else "NO"])
    ym = s2.table_wrapped(240.0, yT - 5.5, [118, 18, 18, 14], mrows, fs=5.0, pad=0.8)
    s2.title_block({
        "title": "FRAME (GlassFront) - INSPECTION DRAWING, sheet 2/2",
        "subtitle": "sections from the STEP, notes for the toolmaker  /  çerçeve kontrol resmi (kalıp teklifi için)",
        "source": "STEP %s (sha256 %s...); params %s" % (os.path.basename(SF.path), SF.sha[:16], P.revision),
        "project": "files: GF_Frame_Inspection.pdf (2 pages) / _p1.png / _p2.png / .dxf",
        "change": "%s round 3: note 8 venting cites the master (vent witness on the lip top flush within %s, "
                  "toolmaker to propose); exclusion zones cite cad_rules[%d]." % (P.revision, n(vent_w), vent_rule_i),
        "dwg": "GF-D50", "rev": P.revision, "scale": "4:1, 10:1, 3:1, 2:1",
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
    for r in (G.lip_in, G.lip_out, G.seat_out, G.flange, G.pocket):
        dxf_rect(msp, r, "CTF_OUTLINES")
    for k_, f in G.F.items():
        dxf_poly(msp, G.slot(k_), "CTF_OUTLINES")
        dxf_poly(msp, stadium_pts(f["u"], f["v"], f["au"], f["av"], cb["cb_l"], cb["cb_w"]), "CTF_OUTLINES")
    yoff = fl.y0 - 40.0
    for i, (nm, sec, xo) in enumerate((("E-E", secA, 0.0), ("F-F", secB, 60.0), ("G-G", secC, 120.0),
                                       ("H-H", secD, 180.0))):
        for outer, inners in sec:
            for ring in [outer] + inners:
                pts = [(xo + t, yoff - (z - Zg)) for t, z in ring]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "SECTIONS"})
        dxf_text(msp, "SECTION %s (t, depth behind the flush plane), 1:1" % nm, xo, yoff + 6.0, 2.0)
    dxf_text(msp, "GF-D50 frame: FRONT_VIEW = hidden-line projection of %s (front view, origin = datum B); BACK_VIEW "
             "offset %s in u; CTF_OUTLINES = nominal outlines from the params %s" % (
                 os.path.basename(SF.path), n(offB), P.revision), fl.x0, fl.y1 + 8.0, 3.0)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(base + ".dxf")
    return {"files": [base + ".dxf", base + ".pdf", base + "_p1.png", base + "_p2.png"],
            "layout_issues": iss1 + iss2, "params_used": sorted(P.used.keys()), "choices_used": C.used,
            "step": {"path": SF.path, "sha256": SF.sha, "mtime": SF.mtime, "bbox": [round(x, 4) for x in SF.bbox],
                     "volume_mm3": round(SF.volume, 1), "faces": SF.n_faces},
            "counterbore_params": {"cb_w": cb["cb_w"], "cb_l": cb["cb_l"]},
            "counterbore_measured": {k_: {"w": None if v[0] is None else round(v[0], 3),
                                          "l": None if v[1] is None else round(v[1], 3)} for k_, v in meas_cb.items()},
            "step_vs_master": rows, "notes_en": notes, "notes_tr": trn,
            "lowest_y": [round(yc_, 1), round(ym, 1), round(yN, 1), round(yT, 1)]}


if __name__ == "__main__":
    r = make()
    print("issues:", len(r["layout_issues"]), r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
    print(r["step"])
    print(r["counterbore_params"], r["counterbore_measured"])
    for x in r["step_vs_master"]:
        print(("OK " if x["ok"] else "NO ") + x["what"], x["measured"], x["expected"])
