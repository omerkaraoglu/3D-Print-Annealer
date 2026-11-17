"""Glass-front frame (GF-1.0 / GF-1.1 / GF-2.0 / GF-2.1) - independent verification toolchain, shared helpers.

GF-2.0 (2026-11-16): the params loader reads the GF-2.0 keys (g_bend, bend_nose_R, land_break, tail_*, div_*,
flange_y1_bottom, plan_rectangles bend_gap_slot / bridge / divider_rib, tail_route); fasteners are whatever the
params list (F1-F4 at GF-2.0). GF-2.1 (same keys, border 19.0 / g_bend 3.23): the previous release (PREV_TAG,
archive) is the second carry-over reference and the row-by-row comparison.

Nothing of the frame is modelled here. The frame is READ from its STEP; the specification is READ from the frozen
parameter file; the board from a kicad-cli STEP export (made from a COPY of the .kicad_pcb into a temp folder) and
from board_geom.json. Helpers are copied (not imported) from tools/frame_v2/common_v2.py and adapted.

COORDINATES (frame v2 convention, as the params file states):
  X = KiCad abs x, model Y = -(KiCad abs y), Z = 0 at the physical PCB back, -Z towards the oven front, pull = Z.
  Every plan value in the reports is KiCad abs (x, y down), tagged _abs. s = distance outward from the glass edge.
  The board STEP export lacks copper + mask: board moved by BOARD_DZ = +0.08 (physical PCB back at Z 0).
  The DS1 panel model sits at the v2 stand-off (panel back Z -5.0); GF hangs the panel on the glass, nominal panel
  back Z_PANEL_BACK (-5.80): every DS1 sub-part (incl. the folded tails) is moved by Z_PANEL_BACK - (-5.0).
"""
import hashlib
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.Bnd import Bnd_Box
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GProp import GProp_GProps
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Trsf, gp_Vec, gp_Pln, gp_Pnt, gp_Dir

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, r"..\..\..\..\.."))
GF_DIR = os.path.join(ROOT, r"Mechanical\Rev3.0_GlassFront")
GF_STEP = os.path.join(GF_DIR, "Rev3.0_GlassFront_Frame.step")
GF_PARAMS = os.path.join(GF_DIR, "Rev3.0_GlassFront_params.json")
GF11_STEP = os.path.join(GF_DIR, r"archive\GF-1.1\Rev3.0_GlassFront_Frame.step")
GF11_PARAMS = os.path.join(GF_DIR, r"archive\GF-1.1\Rev3.0_GlassFront_params.json")
# previous release (carry-over reference and row-by-row comparison): GF-2.0 for the GF-2.1 run
PREV_TAG = "GF-2.0"
PREV_STEP = os.path.join(GF_DIR, r"archive\GF-2.0\Rev3.0_GlassFront_Frame.step")
PREV_PARAMS = os.path.join(GF_DIR, r"archive\GF-2.0\Rev3.0_GlassFront_params.json")
V2_STEP = os.path.join(ROOT, r"Mechanical\Rev3.0_Frame\Rev3.0_Frame_v2.step")
V2_PARAMS = os.path.join(ROOT, r"Mechanical\Rev3.0_Frame\Rev3.0_Frame_v2_params.json")
BOARD_GEOM = os.path.join(ROOT, r"Design Reports\Rev3.0\tools\frame\out\board_geom.json")
CONCEPT_CALC = os.path.join(ROOT, r"Design Reports\Rev3.0\tools\glassfront\concept\concept_calc.py")
PCB_DIR = os.path.join(ROOT, r"KiCad\3dFilamentDryer")
PCB_FILE = os.path.join(PCB_DIR, "3dFilamentDryer.kicad_pcb")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
OUT = os.path.join(HERE, "out")
IMG = os.path.join(GF_DIR, r"renders\verify")
TMP = os.environ.get("GF_VERIFY_TMP", os.path.join(os.environ.get("TEMP", "."), "gf_verify"))

BOARD_DZ = 0.08          # KiCad STEP export lacks copper + mask
V2_PANEL_BACK = -5.0     # where the DS1 model sits in the board export (v2 stand-off 5.0)
Q1_TRIM = 2.5            # Q1 leads trimmed to <= 2.5 below the PCB back (v2 rule)
PANEL_TAIL_PARTS = ("tft_tail", "ctp_tail", "tft_fingers", "ctp_fingers")
Z_TOL = 0.01


def log(*a):
    print(*a, flush=True)


def Yc(y):
    """KiCad abs y (down) -> model Y (up)"""
    return -y


# =====================================================================================================
# file identity
# =====================================================================================================
def file_id(path):
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    st = os.stat(path)
    return {"file": path, "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)), "sha256": h}


# =====================================================================================================
# params (GF-1.0 master file; structure known, read directly - no tolerant adapter needed)
# =====================================================================================================
class GF:
    """the frozen specification, evaluated for one glass thickness (default: the params' own glass_t)"""

    def __init__(self, path=GF_PARAMS, glass_t=None):
        self.path = path
        self.raw = raw = json.load(open(path, encoding="utf8"))
        self.drv = {p["name"]: p["value"] for p in raw["driving_parameters"]}
        self.glass_t = float(glass_t if glass_t is not None else self.drv["glass_t"])
        lv = raw["derived_levels"]["evaluated_by_glass_t"]
        key = next(k for k in lv if abs(float(k) - self.glass_t) < 1e-6)
        self.L = {k: float(v) for k, v in lv[key].items()}
        self.rect = {r["name"]: r for r in raw["plan_rectangles"]}
        self.co = {p["name"]: p["value"] for p in raw["carried_over_from_v2"]}
        self.pips = {p["name"]: tuple(p["value"]) for p in raw["pips"] if p["name"].startswith("pip") and isinstance(p["value"], list)}
        self.fast = {f["name"]: f for f in raw["fasteners"]["positions"]}
        self.lands = raw["lands"]
        self.gaps = {g["name"]: g for g in raw["gaps"]}
        self.revision = raw.get("revision")
        d = self.drv
        for k in ("t_opt", "t_bond", "t_sheet", "t_gap", "g_bs", "g1", "g2", "lip_w", "seat_ring_w", "pocket_clr",
                  "bead_w", "bead_edge", "fast_off", "flange_beyond_glass", "flange_R", "flange_t", "slot_w", "slot_l",
                  "pad_d", "tube_h", "pip_d", "pip_h", "tape_w", "tape_margin", "trough_R", "R_glass", "border"):
            setattr(self, k, float(d[k]))
        c = self.co
        self.WALL, self.RIB, self.DRAFT, self.DRAFT_LOC = c["wall"], c["rib"], c["draft"], c["draft_loc"]
        self.FILLET, self.FORMEX_T, self.PANEL_T = c["fillet_root"], c["sheet_t"], c["panel_t"]
        self.PANEL = (c["panel_x0"], c["panel_x1"], c["panel_y0"], c["panel_y1"])
        self.VA = (c["va_x0"], c["va_x1"], c["va_y0"], c["va_y1"])
        self.SEAT_W, self.PCB_RIM_W = c["seat_w"], c["pcb_rim_w"]
        self.BOSS_OD, self.PILOT_D, self.PILOT_FLOOR = c["boss_od"], c["pilot_d"], c["pilot_floor"]
        self.CBORE_D, self.CBORE_H = c["cbore_d"], c["cbore_h"]
        self.HOLES = {"H%d" % i: (c["h%d_x" % i], c["h%d_y" % i]) for i in range(1, 10)}
        self.LOOP_CTP = (c["loop_ctp_x0"], c["loop_ctp_x1"], c["loop_ctp_y1"])
        self.LOOP_TFT = (c["loop_tft_x0"], c["loop_tft_x1"], c["loop_tft_y1"])
        self.LOOP_Z_TOP, self.LOOP_CLR = c["loop_z_top"], c["loop_clr"]
        self.TAIL_WALL_STEP_Y, self.CRIB_Y, self.CELL_R, self.CELL_RIB_H = (c["tail_wall_step_y"], c["crib_y"],
                                                                           c["cell_r"], c["cell_rib_h"])
        self.FRAME_R = c["frame_r"]
        self.SHELF_T = self.L["Z_SHELF_BACK"] - self.L["Z_SEAT"]
        self.GC = tuple(next(p["value"] for p in raw["plan_points"] if p["name"] == "glass_centre"))
        self.WC = tuple(next(p["value"] for p in raw["plan_points"] if p["name"] == "window_centre"))
        self.AA = self._r("AA")
        self.PRINT = self._r("print_window")
        self.GLASS = self._r("glass")
        self.LIP_IN = self._r("lip_in")
        self.LIP_OUT = self._r("lip_out")
        self.SEAT_OUT = self._r("seat_ring_out")
        self.CUT = self._r("cut")
        self.TAPE_IN = self._r("tape_in")
        self.TAPE_OUT = self._r("tape_out")
        self.FLINE = self._r("fastener_line")
        self.FLANGE = self._r("flange")
        self.POCKET = self._r("pocket")
        self.TAIL = self._r("tail_pocket")

        # ---- GF-1.1 additions (all optional so a GF-1.0 file still loads)
        self.R_frame = float(d.get("R_frame", d["R_glass"]))
        self.R_cut = float(d.get("R_cut", self.CUT[4]))
        self.lip_w_root_ad = d.get("lip_w_root_as_designed")
        self.lip_w_top_ad = d.get("lip_w_top_as_designed")
        fa = raw["fasteners"]
        self.cb = {p["name"]: p["value"] for p in fa.get("counterbore", [])}
        self.core = {p["name"]: p["value"] for p in fa.get("tube_coring", [])}
        self.hw = {p["name"]: p for p in fa.get("hardware", [])}
        self.h6 = {p["name"]: p["value"] for p in raw.get("corner_cell_H6", [])}
        self.change_log = raw.get("change_log")

        # ---- GF-2.0 additions (optional)
        self.gf2 = "g_bend" in d
        for k, dflt in (("g_bend", None), ("bend_nose_R", None), ("land_break", None), ("tail_R_in_min", None),
                        ("tail_straight_l0", None), ("tail_t", None), ("div_x", None), ("div_t", None),
                        ("flange_y1_bottom", None), ("border", None), ("bead_pocket_min", 1.0)):
            v = d.get(k, dflt)
            setattr(self, k, None if v is None else float(v))
        self.SLOT = self._r("bend_gap_slot") if "bend_gap_slot" in self.rect else None
        self.BRIDGE = self._r("bridge") if "bridge" in self.rect else None
        self.DIVIDER = self._r("divider_rib") if "divider_rib" in self.rect else None
        self.tail_route = raw.get("tail_route")
        tg = {p["name"]: p["value"] for p in raw.get("tape_and_gasket", [])}
        self.tape_s = tuple(tg.get("tape_s", (3.9, 15.9)))
        self.strip_lengths = tg.get("strip_lengths", {"top_bottom": 183.48, "sides": 145.83})

    def cb_floor_z(self, n):
        """Z of the counterbore floor at fastener n (None without counterbores)"""
        if not self.cb:
            return None
        k = "cb_floor_F1-F4" if n in ("F1", "F2", "F3", "F4") else "cb_floor_F5-F8"
        if k not in self.cb:
            return None
        return self.L["Z_SHEET_BACK"] + float(self.cb[k])

    def cb_open_z(self, n):
        return self.L["Z_SHEET_BACK"] if n in ("F1", "F2", "F3", "F4") else self.L["Z_FLANGE_FRONT"]

    def _r(self, n):
        r = self.rect[n]
        return (r["x0"], r["x1"], r["y0"], r["y1"], r["R"])

    def slot_axis(self, n):
        return tuple(self.fast[n]["slot_axis"])

    def fxy(self, n):
        f = self.fast[n]
        return f["x_abs"], f["y_abs_down"]

    def stud_names(self, variant="S4"):
        """fasteners used by a variant: S4 / R4 = F1-F4; at GF-2.0 the params list only F1-F4 (S8 withdrawn)"""
        if variant in ("S4", "R4"):
            return [n for n in ("F1", "F2", "F3", "F4") if n in self.fast]
        return sorted(self.fast)

    @property
    def variants(self):
        return ("S4", "R4") if self.gf2 else ("S4", "S8", "R4")


# =====================================================================================================
# STEP loading
# =====================================================================================================
def optimal_bbox(shape):
    s = shape.wrapped if hasattr(shape, "wrapped") else shape
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return x0, x1, y0, y1, z0, z1


def step_unit(path):
    """length unit declared in the STEP header (Fusion writes CENTI METRE); OCC converts to mm on import"""
    txt = open(path, "r", errors="ignore").read().replace(" ", "").replace("\n", "").replace("\r", "")
    for u in ("CENTI", "MILLI"):
        if "SI_UNIT(.%s.,.METRE.)" % u in txt:
            return {"CENTI": "cm", "MILLI": "mm"}[u]
    return "m?" if "SI_UNIT($,.METRE.)" in txt else "unknown"


def load_solid(path):
    t0 = time.time()
    w = cq.importers.importStep(path)
    solids = [s for v in w.vals() for s in v.Solids()]
    if not solids:
        raise RuntimeError("no solid in " + path)
    shape = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    bb = optimal_bbox(shape)
    vol = sum(s.Volume() for s in solids)
    info = file_id(path)
    info.update({"declared_unit": step_unit(path), "solids": len(solids),
                 "valid": all(s.isValid() for s in solids), "volume_mm3": round(vol, 3),
                 "faces": len(shape.Faces()), "edges": len(shape.Edges()),
                 "bbox_model": [round(v, 4) for v in bb],
                 "bbox_abs": {"x": [round(bb[0], 4), round(bb[1], 4)], "y_down": [round(-bb[3], 4), round(-bb[2], 4)],
                              "z": [round(bb[4], 4), round(bb[5], 4)]},
                 "size": [round(bb[1] - bb[0], 4), round(bb[3] - bb[2], 4), round(bb[5] - bb[4], 4)],
                 "read_s": round(time.time() - t0, 1)})
    return shape, info


# =====================================================================================================
# board (copied from v2 common_v2.py)
# =====================================================================================================
_BOARD_CACHE = {}


def _name(l):
    n = TDataStd_Name()
    return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"


def read_doc(path):
    doc = TDocStd_Document(TCollection_ExtendedString("board"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True); r.SetColorMode(True)
    if r.ReadFile(path) != 1:
        raise RuntimeError("cannot read " + path)
    r.Transfer(doc)
    return doc


def board_items(path, dz=BOARD_DZ, panel_dz=0.0):
    """[(ref, part, cq.Shape)] in frame coordinates; DS1 split into its sub-parts and moved by panel_dz in Z"""
    key = (os.path.abspath(path), dz, panel_dz)
    if key in _BOARD_CACHE:
        return _BOARD_CACHE[key]
    doc = read_doc(path)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labs = TDF_LabelSequence(); st.GetFreeShapes(labs)
    top = labs.Value(1)
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, dz))
    shift = TopLoc_Location(tr)
    trp = gp_Trsf(); trp.SetTranslation(gp_Vec(0, 0, dz + panel_dz))
    shift_p = TopLoc_Location(trp)
    out = []
    comps = TDF_LabelSequence(); st.GetComponents_s(top, comps)
    for i in range(1, comps.Length() + 1):
        c = comps.Value(i)
        ref = TDF_Label(); st.GetReferredShape_s(c, ref)
        rname = _name(c)
        if rname.startswith("=>") or "PCB" in _name(ref):
            rname = "PCB"
        if rname == "DS1" and st.IsAssembly_s(ref):
            loc = shift_p.Multiplied(st.GetLocation_s(c))
            sub = TDF_LabelSequence(); st.GetComponents_s(ref, sub)
            for k in range(1, sub.Length() + 1):
                sc = sub.Value(k); sref = TDF_Label(); st.GetReferredShape_s(sc, sref)
                shp = st.GetShape_s(sref).Moved(loc.Multiplied(st.GetLocation_s(sc)))
                out.append(("DS1", _name(sref), cq.Shape.cast(shp)))
        else:
            loc = shift.Multiplied(st.GetLocation_s(c))
            out.append((rname, _name(ref), cq.Shape.cast(st.GetShape_s(ref).Moved(loc))))
    _BOARD_CACHE[key] = out
    return out


def board_step(explicit=None):
    """board STEP: --board / %GF_BOARD_STEP% / <TMP>/board_full.step; else export it with kicad-cli from a COPY of
    the .kicad_pcb (KIPRJMOD pointed at the real project folder so the project-relative 3D models resolve)"""
    for p in (explicit, os.environ.get("GF_BOARD_STEP"), os.path.join(TMP, "board_full.step")):
        if p and os.path.exists(p):
            return p
    import shutil
    import subprocess
    os.makedirs(TMP, exist_ok=True)
    for ext in (".kicad_pcb", ".kicad_pro"):
        shutil.copyfile(os.path.join(PCB_DIR, "3dFilamentDryer" + ext), os.path.join(TMP, "3dFilamentDryer" + ext))
    out = os.path.join(TMP, "board_full.step")
    cmd = [KICAD_CLI, "pcb", "export", "step", "--subst-models", "--user-origin", "0x0mm", "-D", "KIPRJMOD=" + PCB_DIR,
           "-f", "-o", out, os.path.join(TMP, "3dFilamentDryer.kicad_pcb")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("kicad-cli failed: " + r.stdout + r.stderr)
    return out


def board_geom():
    return json.load(open(BOARD_GEOM))


# =====================================================================================================
# OCC helpers (copied from v2 common_v2.py)
# =====================================================================================================
def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def dist_pts(a, b):
    """distance and the two nearest points (model coords)"""
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    if not d.IsDone() or d.NbSolution() < 1:
        return float("nan"), None, None
    p1, p2 = d.PointOnShape1(1), d.PointOnShape2(1)
    return d.Value(), (p1.X(), p1.Y(), p1.Z()), (p2.X(), p2.Y(), p2.Z())


SAMPLE_H = 0.5
SAMPLE_TOL = 0.02
_SAMPLES = {}


def surface_samples(shape, h=SAMPLE_H, tol=SAMPLE_TOL):
    key = (id(shape.wrapped), h)
    if key in _SAMPLES:
        return _SAMPLES[key][1]
    vs, ts = shape.tessellate(tol, 0.2)
    V = np.array([[v.x, v.y, v.z] for v in vs]) if vs else np.zeros((0, 3))
    out = [V]
    if ts:
        T = V[np.array(ts)]
        A, B = T, np.roll(T, -1, axis=1)
        L = np.linalg.norm(B - A, axis=2)
        ne = np.ceil(L / h).astype(int)
        for k in np.unique(ne):
            if k <= 1:
                continue
            m = ne == k
            t = (np.arange(1, k) / k)[None, :, None]
            out.append((A[m][:, None, :] + t * (B[m] - A[m])[:, None, :]).reshape(-1, 3))
        area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        ni = np.ceil(np.sqrt(2 * area) / h).astype(int)
        for k in np.unique(ni):
            if k <= 2:
                continue
            ij = np.array([(i, j) for i in range(1, k) for j in range(1, k - i)], float) / k
            if not len(ij):
                continue
            bary = np.column_stack([ij[:, 0], ij[:, 1], 1 - ij[:, 0] - ij[:, 1]])
            out.append(np.einsum("mk,tkd->tmd", bary, T[ni == k]).reshape(-1, 3))
    pts = np.vstack(out)
    _SAMPLES[key] = (shape, pts)
    return pts


class DistIndex:
    """fast exact distances from one solid (the frame) to many shapes (v2 method): KD-tree over the frame's
    surface samples gives an upper bound, then BRepExtrema against only the frame faces within it."""

    def __init__(self, shape, h=SAMPLE_H):
        from scipy.spatial import cKDTree
        self.shape = shape
        self.h = h
        self.faces = shape.Faces()
        bbs = [f.BoundingBox() for f in self.faces]
        self.fbb = np.array([[b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax] for b in bbs])
        self.tree = cKDTree(surface_samples(shape, h))

    def faces_near(self, other_bb, d):
        b = other_bb
        z = np.zeros(len(self.fbb))
        gx = np.maximum.reduce([self.fbb[:, 0] - b.xmax, b.xmin - self.fbb[:, 1], z])
        gy = np.maximum.reduce([self.fbb[:, 2] - b.ymax, b.ymin - self.fbb[:, 3], z])
        gz = np.maximum.reduce([self.fbb[:, 4] - b.zmax, b.zmin - self.fbb[:, 5], z])
        idx = np.nonzero(np.sqrt(gx * gx + gy * gy + gz * gz) <= d + 2 * SAMPLE_TOL + 1e-3)[0]
        return [self.faces[i] for i in idx]

    def distance(self, other, exact_below=8.0, skip_beyond=None, points=False):
        """-> (distance, approx_flag, overlap_mm3[, p_frame, p_other])"""
        def ret(*a):
            return a if points else a[:3]
        if skip_beyond is not None:
            g = bb_gap(self.shape, other)
            if g > skip_beyond:
                return ret(g, True, 0.0, None, None)
        pts = surface_samples(other, self.h)
        q = self.tree.query(pts)[0] if len(pts) else np.array([1e9])
        d_kd = float(q.min())
        if d_kd > exact_below and not self._inside(other):
            return ret(d_kd, True, 0.0, None, None)
        sel = self.faces_near(other.BoundingBox(), d_kd)
        if sel:
            d, p1, p2 = dist_pts(cq.Compound.makeCompound(sel), other)
        else:
            d, p1, p2 = d_kd, None, None
        if d < 1e-6 or self._inside(other):
            v = common_vol(self.shape, other)
            return ret(0.0 if v > 1e-4 else d, False, v, p1, p2)
        return ret(d, False, 0.0, p1, p2)

    def _inside(self, other):
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.TopAbs import TopAbs_IN
        v = other.Vertices()
        if not v or self.shape.ShapeType() != "Solid":
            return False
        c = BRepClass3d_SolidClassifier(self.shape.wrapped, gp_Pnt(*v[0].toTuple()), 1e-6)
        return c.State() == TopAbs_IN


def common_vol(a, b):
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    op.Build()
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(op.Shape(), g)
    return abs(g.Mass())


def common_shape(a, b):
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    op.Build()
    return cq.Shape.cast(op.Shape())


def cut_shape(a, b, fuzzy=0.0):
    """a - b; with fuzzy > 0 the boolean treats faces closer than that as coincident (needed when two models
    share most of their faces, e.g. GF vs v2)"""
    if fuzzy <= 0:
        op = BRepAlgoAPI_Cut(a.wrapped, b.wrapped)
        op.Build()
        return cq.Shape.cast(op.Shape())
    from OCP.TopTools import TopTools_ListOfShape
    op = BRepAlgoAPI_Cut()
    la = TopTools_ListOfShape(); la.Append(a.wrapped)
    lb = TopTools_ListOfShape(); lb.Append(b.wrapped)
    op.SetArguments(la); op.SetTools(lb)
    op.SetFuzzyValue(fuzzy)
    op.SetRunParallel(True)
    op.Build()
    return cq.Shape.cast(op.Shape())


def common_fuzzy(a, b, fuzzy=1e-4):
    from OCP.TopTools import TopTools_ListOfShape
    op = BRepAlgoAPI_Common()
    la = TopTools_ListOfShape(); la.Append(a.wrapped)
    lb = TopTools_ListOfShape(); lb.Append(b.wrapped)
    op.SetArguments(la); op.SetTools(lb)
    op.SetFuzzyValue(fuzzy)
    op.SetRunParallel(True)
    op.Build()
    return cq.Shape.cast(op.Shape())


def bb_gap(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    dx = max(A.xmin - B.xmax, B.xmin - A.xmax, 0)
    dy = max(A.ymin - B.ymax, B.ymin - A.ymax, 0)
    dz = max(A.zmin - B.zmax, B.zmin - A.zmax, 0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def trim_below(shape, zmin):
    bx = cq.Workplane("XY").box(1000, 1000, 500, centered=(True, True, False)).translate((0, 0, zmin)).val()
    return shape.intersect(bx)


def box(x0, x1, Y0, Y1, z0, z1):
    """axis-aligned box in MODEL coordinates (X, Y up, Z)"""
    return cq.Solid.makeBox(x1 - x0, Y1 - Y0, z1 - z0, cq.Vector(x0, Y0, z0))


def box_abs(x0, x1, y0, y1, z0, z1):
    """axis-aligned box, plan in KiCad abs (y down)"""
    return box(x0, x1, -y1, -y0, min(z0, z1), max(z0, z1))


def plane_section(shape, axis, value, half=2000.0):
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    bb = s.BoundingBox()
    lo, hi = {"x": (bb.xmin, bb.xmax), "y": (bb.ymin, bb.ymax), "z": (bb.zmin, bb.zmax)}[axis]
    if value < lo - 1e-6 or value > hi + 1e-6:
        return None
    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    p = {"x": (value, 0, 0), "y": (0, value, 0), "z": (0, 0, value)}[axis]
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*p), gp_Dir(*n)), -half, half, -half, half).Face()
    op = BRepAlgoAPI_Common(s.wrapped, face)
    op.Build()
    if not op.IsDone():
        return None
    r = cq.Shape.cast(op.Shape())
    return r if r.Faces() else None


def general_section(shape, origin, normal, half=2000.0):
    """section by an arbitrary plane (origin, normal in model coords)"""
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)), -half, half, -half, half).Face()
    op = BRepAlgoAPI_Common(s.wrapped, face)
    op.Build()
    r = cq.Shape.cast(op.Shape())
    return r if r.Faces() else None


def edge_polyline(edge, defl=0.002):
    e = edge.wrapped if hasattr(edge, "wrapped") else edge
    c = BRepAdaptor_Curve(e)
    d = GCPnts_QuasiUniformDeflection(c, defl)
    if not d.IsDone() or d.NbPoints() < 2:
        p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
        return np.array([[p0.X(), p0.Y(), p0.Z()], [p1.X(), p1.Y(), p1.Z()]])
    pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
    return np.array([[p.X(), p.Y(), p.Z()] for p in pts])


def wire_loop(wire, defl=0.002):
    ex = BRepTools_WireExplorer(wire.wrapped if hasattr(wire, "wrapped") else wire)
    out = []
    while ex.More():
        e = ex.Current()
        pts = edge_polyline(e, defl)
        if e.Orientation() == TopAbs_REVERSED:
            pts = pts[::-1]
        out.append(pts if not out else pts[1:])
        ex.Next()
    return np.vstack(out) if out else np.zeros((0, 3))


def face_loops_abs(face, defl=0.002):
    """[outer, inner...] loops of a planar face (N x 2) in KiCad abs (x, y down)"""
    loops = [wire_loop(face.outerWire(), defl)]
    loops += [wire_loop(w, defl) for w in face.innerWires()]
    return [np.column_stack([l[:, 0], -l[:, 1]]) for l in loops if len(l) >= 3]


def face_loops_3d(face, defl=0.002):
    loops = [wire_loop(face.outerWire(), defl)]
    loops += [wire_loop(w, defl) for w in face.innerWires()]
    return [l for l in loops if len(l) >= 3]


def densify(loop, step=0.05):
    a = np.asarray(loop)
    b = np.roll(a, -1, axis=0)
    seg = np.linalg.norm(b - a, axis=1)
    pts = []
    for i in range(len(a)):
        n = max(1, int(np.ceil(seg[i] / step)))
        t = np.arange(n)[:, None] / n
        pts.append(a[i] + t * (b[i] - a[i]))
    return np.vstack(pts)


def is_plane_z(f, sign=None, tol=1e-4):
    if f.geomType() != "PLANE":
        return False
    nz = f.normalAt().z
    if sign is None:
        return abs(nz) > 1 - tol
    return nz * sign > 1 - tol


def faces_at_z(shape, z, sign=+1, tol=Z_TOL):
    out = []
    for f in shape.Faces():
        if not is_plane_z(f, sign):
            continue
        bb = f.BoundingBox()
        if abs(bb.zmin - z) <= tol and abs(bb.zmax - z) <= tol:
            out.append(f)
    return out


def axis_z_feature(face):
    """(kind, cx, cy (model), radius at mid-height, z0, z1, semi-angle deg, opening sign) for cylinders / cones
    whose axis is parallel to Z, else None. radius_at(z) can be evaluated with the returned tuple via cone_r()."""
    gt = face.geomType()
    if gt not in ("CYLINDER", "CONE"):
        return None
    ad = BRepAdaptor_Surface(face.wrapped)
    if gt == "CYLINDER":
        g = ad.Cylinder()
        ax = g.Axis()
        r0, ang = g.Radius(), 0.0
    else:
        g = ad.Cone()
        ax = g.Axis()
        r0, ang = g.RefRadius(), math.degrees(g.SemiAngle())
    d = ax.Direction()
    if abs(abs(d.Z()) - 1.0) > 1e-6:
        return None
    loc = ax.Location()
    bb = face.BoundingBox()
    zm = (bb.zmin + bb.zmax) / 2
    sgn = 1 if d.Z() > 0 else -1
    r = r0 + (zm - loc.Z()) * math.tan(math.radians(ang)) * sgn if gt == "CONE" else r0
    # dr/dz (radius change per +Z) for cones
    drdz = math.tan(math.radians(ang)) * sgn if gt == "CONE" else 0.0
    return gt, loc.X(), loc.Y(), r, bb.zmin, bb.zmax, ang, drdz


# =====================================================================================================
# exact line probes (OCC) - material intervals along a line through the solid
# =====================================================================================================
class Probe:
    """material intervals of a solid along straight lines (IntCurvesFace_ShapeIntersector, exact on the B-rep;
    each span between two consecutive hits is classified by its midpoint, so edge / tangent hits are harmless)"""

    def __init__(self, shape):
        from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        self.shape = shape
        self.si = IntCurvesFace_ShapeIntersector()
        self.si.Load(shape.wrapped, 1e-7)
        self.cls = BRepClass3d_SolidClassifier(shape.wrapped)

    def _inside(self, p):
        from OCP.TopAbs import TopAbs_IN
        self.cls.Perform(gp_Pnt(*p), 1e-7)
        return self.cls.State() == TopAbs_IN

    def intervals(self, p0, d, t0=-1000.0, t1=1000.0):
        """[(ta, tb)] parameters along p0 + t*d (d unit) where the line is inside the material"""
        from OCP.gp import gp_Lin
        self.si.Perform(gp_Lin(gp_Pnt(*p0), gp_Dir(*d)), t0, t1)
        ts = sorted([t0, t1] + [self.si.WParameter(i) for i in range(1, self.si.NbPnt() + 1)])
        u = []
        for t in ts:
            if not u or t - u[-1] > 1e-6:
                u.append(t)
        out = []
        for a, b in zip(u[:-1], u[1:]):
            m = (a + b) / 2
            if self._inside((p0[0] + m * d[0], p0[1] + m * d[1], p0[2] + m * d[2])):
                if out and abs(out[-1][1] - a) < 1e-6:
                    out[-1] = (out[-1][0], b)
                else:
                    out.append((a, b))
        return out

    def intervals_fast(self, p0, d, t0=-1000.0, t1=1000.0):
        """as intervals(), from the In / Out transitions of the hits (no classifier calls); falls back to the
        classified version when the transitions are inconsistent (tangent hits, odd sequences)"""
        from OCP.gp import gp_Lin
        from OCP.IntCurveSurface import IntCurveSurface_In, IntCurveSurface_Out
        self.si.Perform(gp_Lin(gp_Pnt(*p0), gp_Dir(*d)), t0, t1)
        hits = sorted((self.si.WParameter(i), self.si.Transition(i)) for i in range(1, self.si.NbPnt() + 1))
        ev = []
        for t, tr in hits:
            if tr not in (IntCurveSurface_In, IntCurveSurface_Out):
                return self.intervals(p0, d, t0, t1)
            if ev and abs(ev[-1][0] - t) < 1e-6:
                if ev[-1][1] == tr:
                    continue                     # same crossing reported by two faces sharing an edge
                ev.pop()                         # In + Out at one point: grazing, no span
                continue
            ev.append((t, tr))
        out, start = [], None
        for t, tr in ev:
            if tr == IntCurveSurface_In:
                if start is not None:
                    return self.intervals(p0, d, t0, t1)
                start = t
            else:
                if start is None:
                    return self.intervals(p0, d, t0, t1)
                out.append((start, t))
                start = None
        if start is not None:
            return self.intervals(p0, d, t0, t1)
        return out

    def z_intervals(self, x, y_abs):
        """material Z intervals on the vertical line at (x, y abs)"""
        return self.intervals((x, -y_abs, 0.0), (0, 0, 1))

    def z_intervals_fast(self, x, y_abs):
        return self.intervals_fast((x, -y_abs, 0.0), (0, 0, 1))

    def x_intervals(self, y_abs, z):
        """material x intervals on the line along X at (y abs, z)"""
        return self.intervals((0.0, -y_abs, z), (1, 0, 0))

    def y_intervals(self, x, z):
        """material y_abs intervals (sorted) on the line along Y at (x, z)"""
        iv = self.intervals((x, 0.0, z), (0, 1, 0))
        return sorted((-b, -a) for a, b in iv)

    def s_boundaries(self, edge, along, z, s_lo=-30.0, s_hi=30.0, G=None):
        """face positions crossed by a line normal to a glass edge at height z, as s values (outward from the
        glass edge). edge in top/bottom/left/right; along = x (top/bottom) or y abs (left/right)."""
        gx0, gx1, gy0, gy1 = G.GLASS[:4]
        if edge in ("top", "bottom"):
            iv = self.y_intervals(along, z)
            conv = (lambda y: gy0 - y) if edge == "top" else (lambda y: y - gy1)
        else:
            iv = self.x_intervals(along, z)
            conv = (lambda x: gx0 - x) if edge == "left" else (lambda x: x - gx1)
        out = []
        for a, b in iv:
            sa, sb = conv(a), conv(b)
            out.append((min(sa, sb), max(sa, sb)))
        return sorted(o for o in out if o[1] > s_lo and o[0] < s_hi)


def fit_circle(P):
    """least-squares circle through points P (N x 2) -> (cx, cy, r, rms)"""
    P = np.asarray(P, float)
    A = np.column_stack([2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))])
    b = (P ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0], sol[1]
    r = math.sqrt(sol[2] + cx * cx + cy * cy)
    rms = float(np.sqrt(np.mean((np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r) ** 2)))
    return cx, cy, r, rms


def plan_loops(shape, z, defl=0.002):
    """all loops (abs x, y down) of the plan section at Z = z, with their face index and outer/inner flag"""
    sec = plane_section(shape, "z", z)
    out = []
    if sec is None:
        return out
    for i, f in enumerate(sec.Faces()):
        for k, l in enumerate(face_loops_abs(f, defl)):
            out.append({"face": i, "outer": k == 0, "pts": l, "area": f.Area() if k == 0 else None})
    return out


def rrect_fit(pts, nominal, tol_find=1.5):
    """measure a rounded-rectangle loop: bbox and the four corner arcs (circle fits on the loop points within
    tol_find of the nominal corner arc). nominal = (x0, x1, y0, y1, R) abs."""
    P = np.asarray(pts)
    x0, x1, y0, y1, R = nominal
    res = {"x0": float(P[:, 0].min()), "x1": float(P[:, 0].max()), "y0": float(P[:, 1].min()),
           "y1": float(P[:, 1].max()), "corners": {}}
    if R:
        for name, (cx, cy, qx, qy) in {"TL": (x0 + R, y0 + R, -1, -1), "TR": (x1 - R, y0 + R, 1, -1),
                                        "BR": (x1 - R, y1 - R, 1, 1), "BL": (x0 + R, y1 - R, -1, 1)}.items():
            d = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
            sel = P[(np.abs(d - R) < tol_find) & ((P[:, 0] - cx) * qx > 0.15 * R) & ((P[:, 1] - cy) * qy > 0.15 * R)]
            if len(sel) >= 6:
                fx, fy, fr, rms = fit_circle(sel)
                res["corners"][name] = {"cx": fx, "cy": fy, "R": fr, "rms": rms, "n": int(len(sel))}
    return res


# =====================================================================================================
# simple solids for the independent assembly
# =====================================================================================================
def rrect_wire_pts(x0, x1, y0, y1, r, n=24):
    """closed polyline (abs) of a rounded rectangle"""
    pts = []
    cs = [(x1 - r, y0 + r, -90, 0), (x1 - r, y1 - r, 0, 90), (x0 + r, y1 - r, 90, 180), (x0 + r, y0 + r, 180, 270)]
    for cx, cy, a0, a1 in cs:
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def prism(x0, x1, y0, y1, z0, z1, r=0.0):
    """rounded rectangle (abs), extruded between z0 and z1 (as a cq Solid)"""
    lo, hi = min(z0, z1), max(z0, z1)
    w, h = abs(x1 - x0), abs(y1 - y0)
    sk = cq.Sketch().rect(w, h)
    if r and r > 0:
        sk = sk.vertices().fillet(min(r, w / 2 - 1e-3, h / 2 - 1e-3))
    wp = cq.Workplane("XY", origin=(0, 0, lo)).center((x0 + x1) / 2, -(y0 + y1) / 2).placeSketch(sk).extrude(hi - lo)
    return wp.val()


def ring(outer, inner, z0, z1):
    """outer / inner = (x0, x1, y0, y1, R) abs"""
    a = prism(*outer[:4], z0, z1, r=outer[4] or 0)
    b = prism(*inner[:4], min(z0, z1) - 1, max(z0, z1) + 1, r=inner[4] or 0)
    return a.cut(b)


def cyl(x, y, z0, z1, d):
    lo, hi = min(z0, z1), max(z0, z1)
    return cq.Workplane("XY", origin=(0, 0, lo)).center(x, -y).circle(d / 2).extrude(hi - lo).val()


def tube(x, y, z0, z1, od, idia=0.0):
    s = cyl(x, y, z0, z1, od)
    if idia > 0:
        s = s.cut(cyl(x, y, z0 - 1, z1 + 1, idia))
    return s


def stadium(x, y, ax, L, W, z0, z1):
    """stadium W x L (overall), long axis ax=(ux, uy) in abs (y down), centred at (x, y)"""
    lo, hi = min(z0, z1), max(z0, z1)
    ang = math.degrees(math.atan2(-ax[1], ax[0]))       # model Y up
    s = cq.Workplane("XY", origin=(0, 0, lo)).center(x, -y).slot2D(L, W, ang).extrude(hi - lo)
    return s.val()


# =====================================================================================================
# JSON
# =====================================================================================================
def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), indent=1, default=_jsonable)
    return path


def _jsonable(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (tuple, set)):
        return list(o)
    return str(o)


def r3(v):
    return None if v is None else round(float(v), 3)


def verdict(ok, info=False):
    if info:
        return "INFO"
    return "PASS" if ok else "FAIL"


class Context:
    """loads the frame STEP, the params, the v2 STEP and the board once per process"""

    def __init__(self, argv=()):
        argv = list(argv)

        def opt(name, default=None):
            return argv[argv.index(name) + 1] if name in argv else default
        self.frame_path = opt("--frame", GF_STEP)
        self.params_path = opt("--params", GF_PARAMS)
        self.v2_path = opt("--v2", V2_STEP)
        self.board_opt = opt("--board")
        self.outdir = opt("--out", OUT)
        self.imgdir = opt("--img", IMG)
        self.render = "--no-render" not in argv
        os.makedirs(self.outdir, exist_ok=True)
        os.makedirs(self.imgdir, exist_ok=True)
        self.gf11_path = opt("--gf11", GF11_STEP)
        self.prev_path = opt("--prev", PREV_STEP)
        self.G = GF(self.params_path)
        self._frame = self._v2 = self._items = self._gf11 = self._prev = None

    @property
    def prev(self):
        """the previous release frame (archive, PREV_TAG) - carry-over reference for the change list"""
        if self._prev is None:
            self._prev, self.prev_info = load_solid(self.prev_path)
        return self._prev

    @property
    def frame(self):
        if self._frame is None:
            self._frame, self.frame_info = load_solid(self.frame_path)
        return self._frame

    @property
    def gf11(self):
        """the GF-1.1 release frame (archive) - second carry-over reference"""
        if self._gf11 is None:
            self._gf11, self.gf11_info = load_solid(self.gf11_path)
        return self._gf11

    @property
    def v2(self):
        if self._v2 is None:
            self._v2, self.v2_info = load_solid(self.v2_path)
        return self._v2

    @property
    def panel_dz(self):
        return self.G.L["Z_PANEL_BACK"] - V2_PANEL_BACK

    @property
    def items(self):
        if self._items is None:
            self.board_path = board_step(self.board_opt)
            self._items = board_items(self.board_path, BOARD_DZ, self.panel_dz)
        return self._items

    def out(self, name):
        return os.path.join(self.outdir, name)
