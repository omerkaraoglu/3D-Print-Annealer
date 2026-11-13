"""Rev3.0 carrier frame v2 - shared helpers for the verification toolchain.

The frame is NOT built here: it is read from a STEP file (v2: modelled in Fusion 360; --v1: the CadQuery v1
frame) together with a parameters JSON. Everything the checks need is read from those two files, the board
STEP (kicad-cli export with every 3D model, DS1 panel with folded tails) and out/board_geom.json
(dump_board.py: outline, pads, mains copper).

COORDINATE FRAME (same as v1, tools/frame/frame.py)
  X = KiCad absolute x, Y = -(KiCad absolute y), Z = 0 at the physical PCB back, +Z = component side,
  -Z = towards the oven front sheet, mould pull = Z. Plan values in the params JSON and in board_geom.json are
  KiCad absolute (x, y down); `Yc()` converts. The board STEP export has its core at z 0..1.47 with the
  copper + mask (0.08) missing, so it is moved by BOARD_DZ = +0.08 (physical PCB back at Z = 0).

PARAMS JSON READER
  Tolerant: the JSON is flattened into name -> value pairs from any nesting ({"name", "value", "unit"} records,
  plain "key": value pairs, "parent": {"key": value} -> also "parent_key"); names are matched ignoring case and
  every non-alphanumeric character. ADAPTER below lists the accepted aliases of every canonical name the tools
  use; if the Fusion agent used another key, add it to ADAPTER (one line). Rectangles may be given as a list
  [x0, x1, y0, y1] or as four scalars NAME_X0/X1/Y0/Y1 (or XMIN/XMAX/YMIN/YMAX). Units "cm"/"m"/"rad" are
  converted. Point tables (stud holes, PCB holes, pegs) may be lists of {name, x, y} or dicts name -> [x, y].
  Board/panel facts that are not frame design choices fall back to DEFAULTS (v1 values) and are reported.
"""
import json
import math
import os
import re
import sys
import time

sys.dont_write_bytecode = True
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
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
ROOT = os.path.normpath(os.path.join(HERE, r"..\..\..\.."))
MECH = os.path.join(ROOT, r"Mechanical\Rev3.0_Frame")
V2_STEP = os.path.join(MECH, "Rev3.0_Frame_v2.step")
V2_PARAMS = os.path.join(MECH, "Rev3.0_Frame_v2_params.json")
V1_STEP = os.path.join(MECH, "Rev3.0_Frame.step")
V1_PARAMS = os.path.join(HERE, "v1_params.json")
BOARD_GEOM = os.path.join(HERE, "out", "board_geom.json")
BOARD_GEOM_V1 = os.path.normpath(os.path.join(HERE, r"..\frame\out\board_geom.json"))
PCB_FILE = os.path.join(ROOT, r"KiCad\3dFilamentDryer\3dFilamentDryer.kicad_pcb")
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
BOARD_STEP_CANDIDATES = [   # first existing one wins (after --board and %FRAME_BOARD_STEP%)
    os.path.join(os.environ.get("FRAME_TMP", os.path.join(os.environ.get("TEMP", "."), "rev3_frame")), "board_full.step"),
    r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5\scratchpad\cad\Rev3.0_PCB_full.step",
]

BOARD_DZ = 0.08          # KiCad STEP export lacks copper + mask: physical PCB back = export z - 0.08
Q1_TRIM = 2.5            # Q1 leads trimmed to <= 2.5 mm below the PCB back after soldering (IPC-A-610 class 2)
PANEL_TAIL_PARTS = ("tft_tail", "ctp_tail", "tft_fingers", "ctp_fingers")
Z_TOL = 0.01             # a face lies "at" a level if within this


def log(*a):
    print(*a, flush=True)


def Yc(y):
    """KiCad absolute y (down) -> model Y (up)"""
    return -y


# =====================================================================================================
# PARAMS JSON
# =====================================================================================================
ADAPTER = {   # canonical name: accepted aliases (case / underscores / spaces ignored). Extend here if needed.
    # board / panel facts
    "PCB_T": ["PCB_T", "BOARD_T", "PCB_THICKNESS", "BOARD_THICKNESS"],
    "PANEL": ["PANEL", "PANEL_OUTLINE", "PANEL_RECT", "LCM_OUTLINE"],
    "PANEL_T": ["PANEL_T", "PANEL_THICKNESS"],
    "PANEL_T_TOL": ["PANEL_T_TOL", "PANEL_TOL", "LCM_T_TOL"],
    "STANDOFF": ["STANDOFF", "PANEL_STANDOFF", "STAND_OFF"],
    "VA": ["VA", "VIEW_AREA", "COVER_VIEW_AREA", "CVA"],
    "AA": ["AA", "ACTIVE_AREA"],
    # sheet, gasket, oven sheet
    "SHEET_T": ["SHEET_T", "FORMEX_T", "INSUL_SHEET_T", "INSULATION_T"],
    "SHEET_INSET": ["SHEET_INSET", "FORMEX_INSET"],
    "SHEET_R": ["SHEET_R", "FORMEX_R"],
    "GASKET_T": ["GASKET_T", "GASKET_THICKNESS"],
    "GASKET_COMP": ["GASKET_COMP", "GASKET_COMPRESSION"],
    "GASKET_IN_MARGIN": ["GASKET_IN_MARGIN", "GASKET_INNER_MARGIN"],
    "GASKET_OUT_INSET": ["GASKET_OUT_INSET", "GASKET_OUTER_INSET"],
    "OVEN_SHEET_T": ["OVEN_SHEET_T", "FRONT_SHEET_T", "SHEET_METAL_T", "OVEN_T"],
    "CUTOUT_MARGIN": ["CUTOUT_MARGIN", "WINDOW_MARGIN", "SHEET_WINDOW_MARGIN"],
    "CUTOUT_R": ["CUTOUT_R", "WINDOW_R", "SHEET_WINDOW_R"],
    # moulding rules / frame body
    "WALL": ["WALL", "WALL_T", "NOMINAL_WALL"],
    "RIB_T": ["RIB_T", "RIB_THICKNESS", "RIB"],
    "DRAFT": ["DRAFT", "DRAFT_ANGLE", "DRAFT_DEG"],
    "DRAFT_LOC": ["DRAFT_LOC", "DRAFT_POCKET", "POCKET_DRAFT"],
    "POCKET_CLR": ["POCKET_CLR", "POCKET_CLEARANCE"],
    "SEAT_W": ["SEAT_W", "SHELF_REACH", "SEAT_WIDTH"],
    "PCB_RIM_W": ["PCB_RIM_W", "RIB_REACH", "SUPPORT_RIB_REACH"],
    "SHELF_T": ["SHELF_T", "SEAT_T", "SHELF_THICKNESS"],
    "PAD_CLR": ["PAD_CLR", "PAD_CLEARANCE"],
    "SCREW_D": ["SCREW_D", "PCB_SCREW_D"],
    "PILOT_D": ["PILOT_D", "PCB_PILOT_D", "BOSS_HOLE_D", "BOSS_PILOT_D"],
    "BOSS_OD": ["BOSS_OD", "PCB_BOSS_OD", "BOSS_D"],
    "CBORE_D": ["CBORE_D", "RELIEF_D", "BOSS_RELIEF_D"],
    "CBORE_H": ["CBORE_H", "RELIEF_H", "RELIEF_DEPTH", "BOSS_RELIEF_H"],
    "TROUGH_R": ["TROUGH_R", "TAIL_POCKET_R"],
    "LOOP_CLR": ["LOOP_CLR", "TAIL_CLR", "LOOP_CLEARANCE"],
    "LOOP_Z": ["LOOP_Z", "TAIL_Z"],
    "LOOP_Z_BOT": ["LOOP_Z_BOT", "LOOP_Z0", "LOOP_ZMIN", "LOOP_Z_BOTTOM"],
    "LOOP_Z_TOP": ["LOOP_Z_TOP", "LOOP_Z1", "LOOP_ZMAX"],
    # mounting: studs + flange
    "STUD_HOLE_D": ["STUD_HOLE_D", "STUD_HOLE", "STUD_HOLE_DIA", "FOOT_HOLE", "M4_HOLE_D", "STUD_CLEARANCE_D"],
    "STUD_OD": ["STUD_OD", "STUD_BOSS_OD", "STUD_TUBE_OD", "TUBE_OD", "FOOT_OD"],
    "STUD_H": ["STUD_H", "STUD_BOSS_H", "STUD_TUBE_H", "TUBE_H", "FOOT_H"],
    "STUD_OFFSET": ["STUD_OFFSET", "STUD_OFS", "HOLE_OFFSET", "STUD_OFFSET_TOP_RIGHT_BOTTOM"],
    "STUD_OFFSET_L": ["STUD_OFFSET_L", "STUD_OFFSET_LEFT"],
    "STUD_OFFSET_R": ["STUD_OFFSET_R", "STUD_OFFSET_RIGHT"],
    "STUD_OFFSET_T": ["STUD_OFFSET_T", "STUD_OFFSET_TOP"],
    "STUD_OFFSET_B": ["STUD_OFFSET_B", "STUD_OFFSET_BOTTOM"],
    "STUD_SLOT": ["STUD_SLOT", "STUD_SLOT_LEN", "STUD_SLOT_L", "STUD_SLOT_LENGTH", "SLOT_LEN", "SLOT_LENGTH"],
    "RIB_PER_TUBE": ["RIB_PER_TUBE", "RIBS_PER_TUBE", "STUD_RIBS"],
    "PEGS_ON": ["PEGS_ON", "PEGS_ENABLED"],
    "DATUM_X": ["DATUM_X", "THERMAL_DATUM_X", "SLOT_DATUM_X", "DATUM_X_ABS"],
    "DATUM_Y": ["DATUM_Y", "THERMAL_DATUM_Y", "SLOT_DATUM_Y", "DATUM_Y_ABS", "DATUM_Y_ABS_DOWN"],
    "PEG_SLOT": ["PEG_SLOT", "PEG_SLOT_LEN", "PEG_SLOT_LENGTH"],
    "STUD_RIB_T": ["STUD_RIB_T", "RADIAL_RIB_T", "STUD_RIB", "TUBE_RIB_T"],
    "FLANGE_W": ["FLANGE_W", "FLANGE_WIDTH", "FLANGE_W_TOP_RIGHT_BOTTOM"],
    "FLANGE_W_L": ["FLANGE_W_L", "FLANGE_W_LEFT"],
    "FLANGE_W_R": ["FLANGE_W_R", "FLANGE_W_RIGHT"],
    "FLANGE_W_T": ["FLANGE_W_T", "FLANGE_W_TOP"],
    "FLANGE_W_B": ["FLANGE_W_B", "FLANGE_W_BOTTOM"],
    "FLANGE_T": ["FLANGE_T", "FLANGE_THICKNESS"],
    "FLANGE_R": ["FLANGE_R", "FLANGE_CORNER_R"],
    "PEG_D": ["PEG_D", "PEG_DIA", "LOCATING_PEG_D"],
    "PEG_H": ["PEG_H", "PEG_HEIGHT", "LOCATING_PEG_H"],
    # plan rectangles of the body (abs)
    "OUTER": ["OUTER", "BODY", "BODY_OUTLINE", "BODY_RECT", "OUTER_RECT"],
    "POCKET": ["POCKET", "PANEL_POCKET"],
    "TROUGH": ["TROUGH", "TAIL_POCKET", "TROUGH_RECT", "TR"],
    # Z levels
    "Z_PCB": ["Z_PCB", "Z_PCB_BACK", "Z_TOP"],
    "Z_SHELF_BACK": ["Z_SHELF_BACK", "Z_SHELF_TOP"],
    "Z_SEAT": ["Z_SEAT", "Z_SHELF_FRONT"],
    "Z_PANEL_BACK": ["Z_PANEL_BACK", "Z_PANEL"],
    "Z_GLASS": ["Z_GLASS", "Z_GLASS_FRONT", "Z_COVER_FRONT"],
    "Z_FRONT": ["Z_FRONT", "Z_FLANGE_FRONT", "Z_FLANGE", "Z_PARTING", "Z_FEET", "Z_SEAL", "Z_SHEET"],
    "Z_FLANGE_BACK": ["Z_FLANGE_BACK", "Z_FLANGE_TOP"],
    "Z_STUD_TOP": ["Z_STUD_TOP", "Z_TUBE_TOP", "Z_STUD_BOSS_TOP", "Z_NUT_SEAT", "Z_FOOT_TOP"],
    "Z_TROUGH_TOP": ["Z_TROUGH_TOP", "Z_TAIL_POCKET_TOP"],
}
TABLE_KEYS = {   # point tables: candidate keys (normalised), first match wins; regex fallback after
    "studs": (["STUDHOLES", "STUDS", "STUDHOLETABLE", "STUDTABLE", "MOUNTHOLES", "MOUNTINGHOLES", "FEET",
               "FLANGEHOLES", "HOLETABLE"], r"STUD|MOUNT|FEET|FOOT|FLANGEHOLE"),
    "pcb_holes": (["PCBHOLES", "PCBBOSSES", "BOSSES", "EARHOLES", "HOLES", "PCBSCREWS"], r"PCB.*HOLE|BOSS|EAR"),
    "pegs": (["PEGS", "PEGPOS", "PEGPOSITIONS", "LOCATINGPEGS"], r"PEG"),
}
DEFAULTS = {     # board / panel facts (from the board + panel models, v1 frame.py); frame design values are not here
    "PCB_T": 1.6, "PANEL": [20.02, 184.92, 19.00, 119.00], "PANEL_T": 5.32, "PANEL_T_TOL": 0.30, "STANDOFF": 5.0,
    "VA": [26.31, 181.39, 23.23, 110.15], "AA": [26.76, 180.94, 23.82, 109.84],
    "SHEET_T": 0.4, "SHEET_INSET": 0.5, "SHEET_R": 1.0, "GASKET_T": 1.0, "GASKET_COMP": 0.30,
    "GASKET_IN_MARGIN": 1.0, "GASKET_OUT_INSET": 0.3, "OVEN_SHEET_T": 1.0, "CUTOUT_MARGIN": 0.5, "CUTOUT_R": 1.0,
    "PEG_SLOT": 0.7, "SCREW_D": 2.9, "CBORE_D": 3.2, "CBORE_H": 0.5, "PAD_CLR": 1.0, "LOOP_CLR": 1.5, "LOOP_Z": [-9.06, 2.55],
    "Z_PCB": 0.0, "PEG_D": 3.0, "PEG_H": 0.8, "STUD_RIB_T": 0.0, "FLANGE_W": 0.0,
    "pcb_holes": {"H1": (30.0, 14.2), "H2": (93.0, 14.2), "H3": (174.0, 14.2), "H4": (189.8, 30.0),
                  "H5": (189.8, 109.0), "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0),
                  "H9": (15.2, 30.0)},
}
PT_X_KEYS = ("x", "X", "x_abs", "X_abs", "x_abs_mm")
PT_Y_KEYS = ("y", "Y", "y_abs", "y_abs_down", "y_down", "Y_abs")
SCALAR_TABLES = {"pcb_holes": (r"^H(\d+)(X|Y)$", "H"), "pegs": (r"^PEG(\d+)(X|Y)$", "P"),
                 "studs": (r"^FH(\d+)(X|Y)$", "FH")}       # h1_x / h1_y, peg1_x, fh1_x scalar parameters
RECT_SUFFIX = [("X0", "X1", "Y0", "Y1"), ("XMIN", "XMAX", "YMIN", "YMAX"), ("LEFT", "RIGHT", "TOP", "BOTTOM")]


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


_NUM = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([A-Za-z]*)\s*$")


def _num(v, unit=None):
    """value (+unit) -> float in mm / deg, or list of floats, or None"""
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        x = float(v)
    elif isinstance(v, str):
        m = _NUM.match(v)
        if not m:
            return None
        x = float(m.group(1))
        unit = unit or m.group(2)
    elif isinstance(v, (list, tuple)) and v and all(isinstance(e, (int, float)) and not isinstance(e, bool) for e in v):
        return [_num(e, unit) for e in v]
    else:
        return None
    u = (unit or "").strip().lower()
    if u == "cm":
        x *= 10.0
    elif u == "m":
        x *= 1000.0
    elif u == "rad":
        x = math.degrees(x)
    return x


class Params:
    """name lookup over the flattened params JSON (see the module docstring)."""

    def __init__(self, path):
        self.path = path
        self.raw = json.load(open(path, encoding="utf8"))
        self.flat = {}          # norm name -> (value, original key)
        self.tables = {}        # norm key -> {name: (x, y)}
        self.point_attrs = {}   # point name -> {slot_axis, slot_len, ...} as found in the tables
        self.used = {}          # canonical -> (value, source)
        self.defaults_used, self.derived, self.notes = [], [], []
        self._walk(self.raw, "")

    # ---------------------------------------------------------------- flattening
    def _put(self, name, value, src):
        k = norm(name)
        if k and k not in self.flat and value is not None:
            self.flat[k] = (value, src)

    @staticmethod
    def _xy(e):
        """(x, y) KiCad abs of a point record: x / x_abs, y / y_abs / y_abs_down, else -Y_model"""
        x = next((e[k] for k in PT_X_KEYS if k in e), None)
        y = next((e[k] for k in PT_Y_KEYS if k in e), None)
        if y is None and "Y_model" in e:
            y = -float(e["Y_model"])
        if x is None or y is None:
            return None
        return _num(x, e.get("unit")), _num(y, e.get("unit"))

    def _table(self, key, val):
        pts = {}
        if isinstance(val, list):
            for e in val:
                if isinstance(e, dict):
                    nm = e.get("name") or e.get("id") or e.get("label")
                    xy = self._xy(e)
                    if nm is not None and xy is not None:
                        pts[str(nm)] = xy
                        att = {k: e[k] for k in e if re.search(r"slot|reach", k, re.I)}
                        if att:
                            self.point_attrs[str(nm)] = att
        elif isinstance(val, dict):
            for nm, e in val.items():
                if isinstance(e, (list, tuple)) and len(e) >= 2 and all(isinstance(q, (int, float)) for q in e[:2]):
                    pts[str(nm)] = (float(e[0]), float(e[1]))
                elif isinstance(e, dict) and self._xy(e) is not None:
                    pts[str(nm)] = self._xy(e)
                    att = {k: e[k] for k in e if re.search(r"slot|reach", k, re.I)}
                    if att:
                        self.point_attrs[str(nm)] = att
        if pts and len(pts) == (len(val) if isinstance(val, (list, dict)) else 0):
            self.tables.setdefault(norm(key), pts)
            return True
        return False

    def _walk(self, node, parent):
        if isinstance(node, dict):
            if "name" in node and "value" in node:
                self._put(node["name"], _num(node["value"], node.get("unit") or node.get("units")), node["name"])
                return
            for k, v in node.items():
                if isinstance(v, (dict, list)) and self._table(k, v):
                    continue
                val = _num(v)
                if val is not None:
                    self._put(k, val, (parent + "." + k).strip("."))
                    if parent:
                        self._put(parent + "_" + k, val, parent + "." + k)
                elif isinstance(v, dict) and "value" in v and not isinstance(v["value"], (dict, list)):
                    self._put(k, _num(v["value"], v.get("unit")), k)
                    if parent:
                        self._put(parent + "_" + k, _num(v["value"], v.get("unit")), parent + "." + k)
                else:
                    self._walk(v, k)
        elif isinstance(node, list):
            for e in node:
                self._walk(e, parent)

    # ---------------------------------------------------------------- lookup
    def find(self, canon):
        for a in ADAPTER.get(canon, [canon]):
            k = norm(a)
            if k in self.flat:
                return self.flat[k]
        return None

    def get(self, canon, default="__none__", allow_default=True):
        if canon in self.used:
            return self.used[canon][0]
        r = self.find(canon)
        if r is not None:
            self.used[canon] = r
            return r[0]
        rect = self._rect_scalars(canon)
        if rect is not None:
            self.used[canon] = (rect, canon + "_X0..Y1")
            return rect
        if allow_default and canon in DEFAULTS:
            self.defaults_used.append(canon)
            self.used[canon] = (DEFAULTS[canon], "DEFAULT")
            return DEFAULTS[canon]
        if default != "__none__":
            self.used[canon] = (default, "fallback")
            return default
        raise KeyError("params JSON %s: no value for %s (aliases %s)" % (self.path, canon, ADAPTER.get(canon)))

    def _rect_scalars(self, canon):
        for al in ADAPTER.get(canon, [canon]):
            for sx in RECT_SUFFIX:
                ks = [norm(al + "_" + s) for s in sx]
                if all(k in self.flat for k in ks):
                    return [float(self.flat[k][0]) for k in ks]
        return None

    def find_str(self, rx):
        """first string value whose key / record name matches rx (e.g. the stud part number)"""
        def walk(n):
            if isinstance(n, dict):
                if "name" in n and isinstance(n.get("value"), str) and re.search(rx, str(n["name"]), re.I):
                    return n["value"]
                for k, v in n.items():
                    if isinstance(v, str) and re.search(rx, str(k), re.I):
                        return v
                    r = walk(v)
                    if r:
                        return r
            elif isinstance(n, list):
                for e in n:
                    r = walk(e)
                    if r:
                        return r
            return None
        return walk(self.raw)

    def has(self, canon):
        return self.find(canon) is not None or self._rect_scalars(canon) is not None

    @staticmethod
    def _names_fit(kind, t):
        """point names must fit the table kind: PCB holes H<n>, pegs P<n>, studs anything else"""
        ns = list(t)
        if kind == "pcb_holes":
            return all(re.match(r"^H\d+$", n) for n in ns)
        if kind == "pegs":
            return all(re.match(r"^P\d+$", n) for n in ns)
        return not all(re.match(r"^[HP]\d+$", n) for n in ns)

    def table(self, kind):
        keys, rx = TABLE_KEYS[kind]
        for k in keys:
            if k in self.tables and self._names_fit(kind, self.tables[k]):
                return self._fix_y(self.tables[k], kind)
        for k, t in self.tables.items():
            if re.search(rx, k) and self._names_fit(kind, t):
                return self._fix_y(t, kind)
        rx2, pre = SCALAR_TABLES[kind]
        sc = {}
        for k, (v, src) in self.flat.items():
            m = re.match(rx2, k)
            if m and isinstance(v, (int, float)):
                sc.setdefault(pre + m.group(1), {})[m.group(2)] = float(v)
        sc = {n: (d["X"], d["Y"]) for n, d in sc.items() if "X" in d and "Y" in d}
        if sc:
            self.notes.append("%s table built from scalar parameters %s<n>_x / _y" % (kind, pre.lower()))
            return dict(sorted(sc.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]))))
        if kind == "studs":                  # last resort: the one table whose names are not H<n> / P<n>
            cand = [(k, t) for k, t in self.tables.items() if self._names_fit("studs", t)]
            if len(cand) == 1:
                self.notes.append("stud table taken from key '%s' by its point names" % cand[0][0])
                return self._fix_y(cand[0][1], kind)
        if kind in DEFAULTS:
            self.defaults_used.append(kind)
            return dict(DEFAULTS[kind])
        return {}

    def _fix_y(self, t, kind):
        if t and all(y < 0 for x, y in t.values()):
            self.notes.append("%s table had negative y: read as model Y, converted to KiCad abs y" % kind)
            return {n: (x, -y) for n, (x, y) in t.items()}
        return dict(t)

    def report(self):
        return {"file": self.path, "used": {k: {"value": v[0], "source": v[1]} for k, v in sorted(self.used.items())},
                "defaults_used": sorted(set(self.defaults_used)), "derived": self.derived, "notes": self.notes}


class Design:
    """All values the checks use, resolved once from the params JSON (+ derivations, + defaults)."""

    def __init__(self, P):
        self.P = P
        g = P.get
        self.PCB_T = g("PCB_T")
        self.PANEL = tuple(g("PANEL"))
        self.PX0, self.PX1, self.PY0, self.PY1 = self.PANEL
        self.PANEL_T, self.PANEL_T_TOL, self.STANDOFF = g("PANEL_T"), g("PANEL_T_TOL"), g("STANDOFF")
        self.VA, self.AA = tuple(g("VA")), tuple(g("AA"))
        for k in ("SHEET_T", "SHEET_INSET", "SHEET_R", "GASKET_T", "GASKET_COMP", "GASKET_IN_MARGIN",
                  "GASKET_OUT_INSET", "OVEN_SHEET_T", "CUTOUT_MARGIN", "CUTOUT_R", "WALL", "RIB_T", "DRAFT",
                  "POCKET_CLR", "SEAT_W", "PCB_RIM_W", "SHELF_T", "PAD_CLR", "SCREW_D", "PILOT_D", "BOSS_OD",
                  "CBORE_D", "CBORE_H", "STUD_HOLE_D", "STUD_OD", "PEG_D", "PEG_H", "LOOP_CLR"):
            setattr(self, k, float(g(k)))
        self.DRAFT_LOC = float(g("DRAFT_LOC", default=0.5))
        if not P.has("LOOP_Z") and P.has("LOOP_Z_BOT") and P.has("LOOP_Z_TOP"):
            self.LOOP_Z = (float(g("LOOP_Z_BOT")), float(g("LOOP_Z_TOP")))
            P.used["LOOP_Z"] = (list(self.LOOP_Z), "LOOP_Z_BOT / LOOP_Z_TOP")
        else:
            self.LOOP_Z = tuple(g("LOOP_Z"))
        self.TROUGH_R = float(g("TROUGH_R", default=5.0))
        self.FLANGE_W = float(g("FLANGE_W"))
        self.FLANGE_T = float(g("FLANGE_T", default=self.WALL))
        self.FLANGE_R = float(g("FLANGE_R", default=0.0))
        if not P.has("STUD_RIB_T") and P.has("RIB_PER_TUBE") and float(g("RIB_PER_TUBE")) >= 1:
            self.STUD_RIB_T = self.RIB_T                      # a radial rib per tube, of the general rib thickness
            P.derived.append("STUD_RIB_T")
            P.used["STUD_RIB_T"] = (self.RIB_T, "RIB_T (RIB_PER_TUBE >= 1)")
        else:
            self.STUD_RIB_T = float(g("STUD_RIB_T"))
        self.STUD_OFFSET = g("STUD_OFFSET", default=None)
        # per-side flange width / stud offset (sides: top, right, bottom, left; default = the general value)
        self.FLANGE_W_SIDE = {sd: float(g("FLANGE_W_" + sd[0].upper(), default=self.FLANGE_W))
                              for sd in ("top", "right", "bottom", "left")}
        self.STUD_OFFSET_SIDE = {sd: g("STUD_OFFSET_" + sd[0].upper(), default=self.STUD_OFFSET)
                                 for sd in ("top", "right", "bottom", "left")}
        # ---- Z levels: explicit if given, else derived exactly as v1 frame.py does
        self.Z_PCB = float(g("Z_PCB"))
        self.Z_PANEL_BACK = self._lev("Z_PANEL_BACK", self.Z_PCB - self.STANDOFF)
        self.Z_SEAT = self._lev("Z_SEAT", self.Z_PANEL_BACK + self.SHEET_T)
        self.Z_GLASS = self._lev("Z_GLASS", self.Z_PANEL_BACK - self.PANEL_T)
        self.Z_FRONT = self._lev("Z_FRONT", self.Z_GLASS - self.GASKET_T * (1 - self.GASKET_COMP))
        self.Z_SHELF_BACK = self._lev("Z_SHELF_BACK", self.Z_SEAT + self.SHELF_T)
        self.Z_FLANGE_BACK = self._lev("Z_FLANGE_BACK", self.Z_FRONT + self.FLANGE_T)
        sh = P.get("STUD_H", default=None)
        zst = self.Z_FLANGE_BACK + sh if (sh is not None and self.FLANGE_W > 0) else (
            self.Z_FRONT + sh if sh is not None else None)
        self.Z_STUD_TOP = self._lev("Z_STUD_TOP", zst)
        self.Z_TROUGH_TOP = self._lev("Z_TROUGH_TOP", self.LOOP_Z[1] + self.LOOP_CLR)
        # ---- plan rectangles (abs)
        self.POCKET = tuple(self._rect("POCKET", (self.PX0 - self.POCKET_CLR, self.PX1 + self.POCKET_CLR,
                                                  self.PY0 - self.POCKET_CLR, self.PY1 + self.POCKET_CLR)))
        self.OUTER = tuple(self._rect("OUTER", None))
        self.TROUGH = tuple(self._rect("TROUGH", None) or ())
        # ---- tables
        self.STUDS = P.table("studs")
        self.HOLES = P.table("pcb_holes")
        self.PEGS = P.table("pegs")
        if P.has("PEGS_ON") and float(g("PEGS_ON")) == 0:
            self.PEGS = {}
            P.notes.append("PEGS_ON = 0: no locating pegs")
        if not self.STUDS:
            raise KeyError("params JSON: no stud-hole table found (keys tried: %s)" % (TABLE_KEYS["studs"][0],))
        self.DATUM = ((float(g("DATUM_X")), float(g("DATUM_Y")))
                      if P.has("DATUM_X") and P.has("DATUM_Y") else None)
        self.SLOTS = self._slots()
        self.PEG_SLOTS = self._peg_slots()
        spec = P.find_str(r"stud_?(spec|type|part|pn)|pem_?stud")
        self.STUD_SPEC = spec or "PEM FH-M4-18"
        if not spec:
            P.defaults_used.append("STUD_SPEC")
        m = re.search(r"M4-(\d+(?:\.\d+)?)", self.STUD_SPEC)
        self.STUD_LEN = float(m.group(1)) if m else 15.0

    def edges_of(self, x, y):
        """which body edges (top / bottom / left / right) a point (abs) lies beyond; inside the body: the nearest
        corner's two edges"""
        x0, x1, y0, y1 = self.OUTER
        e = []
        if y < y0:
            e.append("top")
        if y > y1:
            e.append("bottom")
        if x < x0:
            e.append("left")
        if x > x1:
            e.append("right")
        if not e:
            e = ["top" if y - y0 < y1 - y else "bottom", "left" if x - x0 < x1 - x else "right"]
        return e

    @staticmethod
    def _axis(ax):
        """slot axis value -> unit vector (as given) or None: 'x' / 'y', [ux, uy], {x|ux: , y|uy: }, angle (deg)"""
        if isinstance(ax, dict):
            ux = next((ax[k] for k in ("x", "ux", "dx", "X") if k in ax), None)
            uy = next((ax[k] for k in ("y", "uy", "dy", "Y") if k in ax), None)
            ax = [ux, uy] if ux is not None and uy is not None else None
        if isinstance(ax, (list, tuple)) and len(ax) >= 2:
            h = math.hypot(float(ax[0]), float(ax[1])) or 1.0
            return float(ax[0]) / h, float(ax[1]) / h
        if isinstance(ax, str):
            t = ax.strip().lower()
            if t in ("x", "along x", "+x", "-x"):
                return 1.0, 0.0
            if t in ("y", "along y", "+y", "-y"):
                return 0.0, 1.0
            ax = _num(ax)
        if isinstance(ax, (int, float)) and not isinstance(ax, bool):
            r = math.radians(ax)
            return math.cos(r), math.sin(r)
        return None

    def _slots(self):
        """stud holes that are stadium slots: {name: {axis (ux, uy) KiCad abs, len, w}}. Per hole from the table
        (slot_axis as 'x' / 'y' / [ux, uy] / {x, y}, else slot_axis_deg; slot_len[_mm]; slot_width[_mm]), else the
        general STUD_SLOT (total length; a value smaller than the hole dia is read as the elongation) along the edge.
        With a DATUM, an axis that is radial only after flipping its y (given in model Y-up) is flipped."""
        P = self.P
        gen = float(P.get("STUD_SLOT")) if P.has("STUD_SLOT") else None
        out = {}
        for n, (x, y) in self.STUDS.items():
            a = P.point_attrs.get(n, {})
            vec = next((a[k] for k in a if re.search(r"slot_?(axis|dir|direction)(_unit|_vec|_vector)?$", k, re.I)), None)
            ang = next((a[k] for k in a if re.search(r"slot_?(axis|dir|direction)?_?(angle|deg)", k, re.I)), None)
            ln = next((a[k] for k in a if re.search(r"slot_?(len|length|l)(_mm)?$", k, re.I)), None)
            wd = next((a[k] for k in a if re.search(r"slot_?(w|width)(_mm)?$", k, re.I)), None)
            W = _num(wd) if wd is not None else self.STUD_HOLE_D
            L = _num(ln) if ln is not None else gen
            if L is None:
                continue
            if L < W:
                L = W + L
            if L <= W + 1e-6:
                continue
            u = self._axis(vec) if vec is not None else None
            if u is None and ang is not None:
                u = self._axis(_num(ang) if not isinstance(ang, (int, float)) else ang)
            if u is None:
                u = (1.0, 0.0) if {"top", "bottom"} & set(self.edges_of(x, y)) else (0.0, 1.0)
            if self.DATUM is not None:
                rx, ry = x - self.DATUM[0], y - self.DATUM[1]
                rh = math.hypot(rx, ry)
                if rh > 1e-6:
                    c0 = abs(u[0] * rx + u[1] * ry) / rh
                    c1 = abs(u[0] * rx - u[1] * ry) / rh
                    if c0 < 0.985 and c1 >= 0.985:                    # radial only with y flipped
                        u = (u[0], -u[1])
                        P.notes.append("slot axis of %s read as model Y-up and flipped to KiCad abs" % n)
            out[n] = {"axis": u, "len": L, "w": W}
        return out

    def _peg_slots(self):
        """locating holes in the SHEET for the pegs: {peg: None (round) | {axis, len}}. Per peg from the pegs table
        (slot_axis / slot_len[_mm]); otherwise with two pegs BOTH are slots along the line joining them (the frame
        is held across that line and self-centres along it), length = peg hole + PEG_SLOT (0 = both round)."""
        P = self.P
        out = {n: None for n in self.PEGS}
        explicit = False
        for n in self.PEGS:
            a = P.point_attrs.get(n, {})
            ln = next((a[k] for k in a if re.search(r"slot_?(len|length|l)(_mm)?$", k, re.I)), None)
            vec = next((a[k] for k in a if re.search(r"slot_?(axis|dir|direction)", k, re.I)), None)
            if ln is not None:
                explicit = True
                L = _num(ln)
                hole = self.PEG_D + PEG_HOLE_CLR
                if L is not None and L > hole + 1e-6:
                    out[n] = {"axis": self._axis(vec) or (1.0, 0.0), "len": L}
        if not explicit and len(self.PEGS) == 2:
            ps = float(self.P.get("PEG_SLOT"))
            if ps > 0:
                (n1, p1), (n2, p2) = sorted(self.PEGS.items())
                d = math.hypot(p2[0] - p1[0], p2[1] - p1[1]) or 1.0
                u = ((p2[0] - p1[0]) / d, (p2[1] - p1[1]) / d)
                for nn in (n1, n2):
                    out[nn] = {"axis": u, "len": self.PEG_D + PEG_HOLE_CLR + ps}
        return out

    def thermal_fixed_point(self):
        """where the frame is held against the sheet in the plane: (name, (x, y)) - the round peg if the other is a
        slot, the pegs' midpoint if both are round (over-constrained), the DATUM, else the stud-pattern centroid"""
        rnd = [n for n, s in self.PEG_SLOTS.items() if s is None]
        if self.PEGS and len(rnd) == 1 and len(self.PEGS) == 2:
            return "round peg %s" % rnd[0], self.PEGS[rnd[0]]
        if len(self.PEGS) == 2 and not rnd:            # both slotted along the peg line: held across it,
            pts = list(self.PEGS.values())             # self-centred along it -> about the datum / midpoint
            mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            return ("datum (both pegs slotted along the peg line: held across it, self-centred along it)",
                    self.DATUM or mid)
        if self.PEGS:
            pts = list(self.PEGS.values())
            return "pegs' midpoint (all pegs round)", (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        if self.DATUM:
            return "declared datum", self.DATUM
        pts = list(self.STUDS.values())
        return "stud-pattern centroid", (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def hole_arc_centres(self, name):
        """centres (abs) of the round ends of a stud hole: one for a round hole, two for a slot"""
        x, y = self.STUDS[name]
        s = self.SLOTS.get(name)
        if not s:
            return [(x, y)]
        h = (s["len"] - s["w"]) / 2
        return [(x - h * s["axis"][0], y - h * s["axis"][1]), (x + h * s["axis"][0], y + h * s["axis"][1])]

    def _lev(self, name, derived):
        if self.P.has(name):
            return float(self.P.get(name))
        if derived is None:
            return None
        self.P.derived.append(name)
        self.P.used[name] = (derived, "derived")
        return float(derived)

    def _rect(self, name, derived):
        if self.P.has(name):
            return [float(v) for v in self.P.get(name)]
        if derived is not None:
            self.P.derived.append(name)
            self.P.used[name] = (list(derived), "derived")
        return derived

    def cutout_rect(self):
        m = self.CUTOUT_MARGIN
        return (self.VA[0] - m, self.VA[1] + m, self.VA[2] - m, self.VA[3] + m)

    def window_datum(self):
        co = self.cutout_rect()
        return (co[0] + co[1]) / 2, (co[2] + co[3]) / 2

    def uv(self, x, y):
        """KiCad abs -> front-view sheet coordinates (u right, v up as seen from in front of the oven)"""
        xc, yc = self.window_datum()
        return -(x - xc), -(y - yc)

    def summary(self):
        keys = ["Z_PCB", "Z_SHELF_BACK", "Z_SEAT", "Z_PANEL_BACK", "Z_GLASS", "Z_FRONT", "Z_FLANGE_BACK",
                "Z_STUD_TOP", "Z_TROUGH_TOP", "OUTER", "POCKET", "TROUGH", "FLANGE_W", "FLANGE_T", "STUD_OD",
                "STUD_HOLE_D", "STUD_RIB_T", "STUD_OFFSET"]
        out = {k: getattr(self, k) for k in keys}
        out["stud_holes"] = self.STUDS
        out["stud_slots"] = self.SLOTS
        out["datum"] = self.DATUM
        out["peg_slots"] = self.PEG_SLOTS
        out["stud_spec"] = self.STUD_SPEC
        out["flange_w_side"] = self.FLANGE_W_SIDE
        out["stud_offset_side"] = self.STUD_OFFSET_SIDE
        out["pcb_holes"] = self.HOLES
        out["pegs"] = self.PEGS
        return out


# =====================================================================================================
# FRAME STEP
# =====================================================================================================
def optimal_bbox(shape):
    s = shape.wrapped if hasattr(shape, "wrapped") else shape
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return x0, x1, y0, y1, z0, z1


def load_frame(path):
    """-> (shape, info). shape = the single solid (or a compound of all solids if there are several)."""
    t0 = time.time()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    w = cq.importers.importStep(path)
    solids = [s for v in w.vals() for s in v.Solids()]
    if not solids:
        raise RuntimeError("no solid in " + path)
    shape = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    bb = optimal_bbox(shape)
    vol = sum(s.Volume() for s in solids)
    info = {"file": path, "bytes": os.path.getsize(path),
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path))),
            "solids": len(solids), "valid": all(s.isValid() for s in solids),
            "volume_cm3": round(vol / 1000, 3), "mass_g_1.36": round(vol / 1000 * 1.36, 1),
            "faces": len(shape.Faces()), "edges": len(shape.Edges()),
            "bbox_model": [round(v, 3) for v in bb],
            "size": [round(bb[1] - bb[0], 3), round(bb[3] - bb[2], 3), round(bb[5] - bb[4], 3)],
            "single_solid": len(solids) == 1, "read_s": round(time.time() - t0, 1)}
    return shape, info


# =====================================================================================================
# BOARD (copied from v1 fitcheck.py so v2 runs without the v1 folder)
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


def board_items(path, dz=BOARD_DZ):
    """[(ref, part, cq.Shape)] in frame coordinates; DS1 split into its sub-parts. Cached per process."""
    key = (os.path.abspath(path), dz)
    if key in _BOARD_CACHE:
        return _BOARD_CACHE[key]
    doc = read_doc(path)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labs = TDF_LabelSequence(); st.GetFreeShapes(labs)
    top = labs.Value(1)
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, dz))
    shift = TopLoc_Location(tr)
    out = []
    comps = TDF_LabelSequence(); st.GetComponents_s(top, comps)
    for i in range(1, comps.Length() + 1):
        c = comps.Value(i)
        ref = TDF_Label(); st.GetReferredShape_s(c, ref)
        loc = shift.Multiplied(st.GetLocation_s(c))
        rname = _name(c)
        if rname.startswith("=>") or "PCB" in _name(ref):
            rname = "PCB"
        if rname == "DS1" and st.IsAssembly_s(ref):
            sub = TDF_LabelSequence(); st.GetComponents_s(ref, sub)
            for k in range(1, sub.Length() + 1):
                sc = sub.Value(k); sref = TDF_Label(); st.GetReferredShape_s(sc, sref)
                shp = st.GetShape_s(sref).Moved(loc.Multiplied(st.GetLocation_s(sc)))
                out.append(("DS1", _name(sref), cq.Shape.cast(shp)))
        else:
            out.append((rname, _name(ref), cq.Shape.cast(st.GetShape_s(ref).Moved(loc))))
    _BOARD_CACHE[key] = out
    return out


def find_board_step(explicit=None):
    for p in [explicit, os.environ.get("FRAME_BOARD_STEP")] + BOARD_STEP_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


def export_board_step(path):
    """kicad-cli pcb export step (read-only on the .kicad_pcb), as v1 build.py. Only with --export-board."""
    import subprocess
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [KICAD_CLI, "pcb", "export", "step", "--subst-models", "--user-origin", "0x0mm", "-f", "-o", path, PCB_FILE]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path):
        raise RuntimeError("kicad-cli failed: " + r.stdout + r.stderr)
    return path


def board_geom():
    """out/board_geom.json (copied from v1 on first use; dump_board.py re-creates it with KiCad's Python)."""
    if not os.path.exists(BOARD_GEOM):
        if os.path.exists(BOARD_GEOM_V1):
            import shutil
            os.makedirs(os.path.dirname(BOARD_GEOM), exist_ok=True)
            shutil.copyfile(BOARD_GEOM_V1, BOARD_GEOM)
        else:
            raise FileNotFoundError(BOARD_GEOM + " missing: run dump_board.py with KiCad's python.exe")
    return json.load(open(BOARD_GEOM))


# =====================================================================================================
# OCC helpers
# =====================================================================================================
def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


SAMPLE_H = 0.5           # mm: surface sample spacing of the distance index (an upper bound; the exact distance
                         # is then computed with BRepExtrema against the frame faces within that bound)
_SAMPLES = {}


SAMPLE_TOL = 0.02        # mm tessellation deflection of the samples (the cut-off below adds it)


def surface_samples(shape, h=SAMPLE_H, tol=SAMPLE_TOL):
    """points on (or within `tol` of) the surface of `shape`: tessellation vertices, points every <= h along every
    triangle edge, and an interior barycentric grid sized by the triangle's area (sliver triangles are covered by
    their edge points)"""
    key = (id(shape.wrapped), h)
    if key in _SAMPLES:
        return _SAMPLES[key][1]
    vs, ts = shape.tessellate(tol, 0.2)
    V = np.array([[v.x, v.y, v.z] for v in vs]) if vs else np.zeros((0, 3))
    out = [V]
    if ts:
        T = V[np.array(ts)]                                   # (n, 3, 3)
        A, B = T, np.roll(T, -1, axis=1)
        L = np.linalg.norm(B - A, axis=2)                     # (n, 3) edge lengths
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
    _SAMPLES[key] = (shape, pts)        # keep the shape alive so id() stays unique
    return pts


class DistIndex:
    """fast exact distances from one solid (the frame) to many shapes.
    1. KD-tree over the frame's surface samples -> d_kd >= true distance (both sides sampled)
    2. exact BRepExtrema against only the frame faces whose bbox lies within d_kd of the other shape's bbox
       (the face holding the true nearest point is always among them) -> exact value.
    Beyond `exact_below` the sampled value is returned (flagged approx, error < SAMPLE_H)."""

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
        gx = np.maximum.reduce([self.fbb[:, 0] - b.xmax, b.xmin - self.fbb[:, 1], np.zeros(len(self.fbb))])
        gy = np.maximum.reduce([self.fbb[:, 2] - b.ymax, b.ymin - self.fbb[:, 3], np.zeros(len(self.fbb))])
        gz = np.maximum.reduce([self.fbb[:, 4] - b.zmax, b.zmin - self.fbb[:, 5], np.zeros(len(self.fbb))])
        idx = np.nonzero(np.sqrt(gx * gx + gy * gy + gz * gz) <= d + 2 * SAMPLE_TOL + 1e-3)[0]
        return [self.faces[i] for i in idx]

    def distance(self, other, exact_below=8.0, skip_beyond=None):
        """-> (distance, approx_flag, overlap_mm3). With skip_beyond, a shape whose bbox lies further than that from
        the indexed shape's bbox is not sampled: its bbox gap (a lower bound) is returned, flagged approx."""
        if skip_beyond is not None:
            g = bb_gap(self.shape, other)
            if g > skip_beyond:
                return g, True, 0.0
        pts = surface_samples(other, self.h)
        d_kd = float(self.tree.query(pts)[0].min()) if len(pts) else 1e9
        if d_kd > exact_below:
            inside = self._inside(other)
            if not inside:
                return d_kd, True, 0.0
        sel = self.faces_near(other.BoundingBox(), d_kd)
        d = dist(cq.Compound.makeCompound(sel), other) if sel else d_kd
        if d < 1e-6 or self._inside(other):
            v = common_vol(self.shape, other)
            return (0.0 if v > 1e-4 else d), False, v
        return d, False, 0.0

    def _inside(self, other):
        """True if a vertex of `other` lies inside the frame (catches a part wholly inside, no face contact)"""
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


def bb_gap(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    dx = max(A.xmin - B.xmax, B.xmin - A.xmax, 0)
    dy = max(A.ymin - B.ymax, B.ymin - A.ymax, 0)
    dz = max(A.zmin - B.zmax, B.zmin - A.zmax, 0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def trim_below(shape, zmin):
    box = cq.Workplane("XY").box(1000, 1000, 500, centered=(True, True, False)).translate((0, 0, zmin)).val()
    return shape.intersect(box)


def box(x0, x1, Y0, Y1, z0, z1):
    """axis-aligned box in MODEL coordinates (X, Y up, Z)"""
    return cq.Solid.makeBox(x1 - x0, Y1 - Y0, z1 - z0, cq.Vector(x0, Y0, z0))


def plane_section(shape, axis, value, half=2000.0):
    """faces of `shape` cut by the plane axis = value (model coordinates) as a cq.Shape (compound) or None"""
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


def edge_polyline(edge, defl=0.002):
    """points (N x 3) along an edge, chord deflection <= defl, in the edge's own parameter direction"""
    e = edge.wrapped if hasattr(edge, "wrapped") else edge
    c = BRepAdaptor_Curve(e)
    d = GCPnts_QuasiUniformDeflection(c, defl)
    if not d.IsDone() or d.NbPoints() < 2:
        p0, p1 = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
        return np.array([[p0.X(), p0.Y(), p0.Z()], [p1.X(), p1.Y(), p1.Z()]])
    pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
    return np.array([[p.X(), p.Y(), p.Z()] for p in pts])


def wire_loop(wire, defl=0.002):
    """ordered closed polyline (N x 3) of a wire (edges walked in wire order, orientation respected)"""
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
    """[outer, inner...] loops of a planar face as (N x 2) arrays in KiCad abs (x, y down)"""
    loops = [wire_loop(face.outerWire(), defl)]
    loops += [wire_loop(w, defl) for w in face.innerWires()]
    return [np.column_stack([l[:, 0], -l[:, 1]]) for l in loops if len(l) >= 3]


def densify(loop, step=0.05):
    """closed polyline -> points every <= step along it"""
    a = np.asarray(loop)
    b = np.roll(a, -1, axis=0)
    seg = np.linalg.norm(b - a, axis=1)
    pts = []
    for i in range(len(a)):
        n = max(1, int(np.ceil(seg[i] / step)))
        t = np.arange(n)[:, None] / n
        pts.append(a[i] + t * (b[i] - a[i]))
    return np.vstack(pts)


def faces_at_z(shape, z, sign=+1, tol=Z_TOL):
    """planar faces whose outward normal is sign*Z and that lie at Z = z (+-tol)"""
    out = []
    for f in shape.Faces():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        if n.z * sign < 0.9999:
            continue
        bb = f.BoundingBox()
        if abs(bb.zmin - z) <= tol and abs(bb.zmax - z) <= tol:
            out.append(f)
    return out


def axis_z_feature(face):
    """(kind, cx, cy (model), radius at mid-height, z0, z1, half_angle_deg) for cylinders / cones whose axis is
    parallel to Z, else None"""
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
    # cone radius at zm: r = r0 + (zm - z_loc) * tan(semi) * sign(dir)
    r = r0 + (zm - loc.Z()) * math.tan(math.radians(ang)) * (1 if d.Z() > 0 else -1) if gt == "CONE" else r0
    return gt, loc.X(), loc.Y(), r, bb.zmin, bb.zmax, ang


# =====================================================================================================
# auxiliary parts (not moulded): Formex sheet, gasket, oven-sheet patch, M4 studs, PEM tool socket
# =====================================================================================================
def prism(x0, x1, y0, y1, z0, z1, taper=0.0, r=0.0):
    """rectangle (KiCad abs x0..x1, y0..y1), optional corner radius r, extruded from z0 to z1 (as v1)"""
    up = z1 > z0
    pl = cq.Plane(origin=(0, 0, z0), xDir=(1, 0, 0), normal=(0, 0, 1 if up else -1))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ly = Yc(cy) if up else -Yc(cy)
    w, h = abs(x1 - x0), abs(y1 - y0)
    sk = cq.Sketch().rect(w, h)
    if r > 0:
        sk = sk.vertices().fillet(min(r, w / 2 - 1e-3, h / 2 - 1e-3))
    return cq.Workplane(pl).center(cx, ly).placeSketch(sk).extrude(abs(z1 - z0), taper=taper)


def tube(x, y, z0, z1, od, idia=0.0):
    up = z1 > z0
    pl = cq.Plane(origin=(0, 0, z0), xDir=(1, 0, 0), normal=(0, 0, 1 if up else -1))
    ly = Yc(y) if up else -Yc(y)
    s = cq.Workplane(pl).center(x, ly).circle(od / 2).extrude(abs(z1 - z0))
    if idia > 0:
        s = s.cut(cq.Workplane(pl).center(x, ly).circle(idia / 2).extrude(abs(z1 - z0)))
    return s


def build_sheet(D):
    """Formex-type insulating sheet: panel outline - 2 x SHEET_INSET, between the panel back and the shelf"""
    i = D.SHEET_INSET
    return prism(D.PX0 + i, D.PX1 - i, D.PY0 + i, D.PY1 - i, D.Z_PANEL_BACK, D.Z_SEAT, r=D.SHEET_R).val()


def build_gasket(D):
    """compressed silicone-sponge gasket between the glass and the oven sheet"""
    o = (D.PX0 + D.GASKET_OUT_INSET, D.PX1 - D.GASKET_OUT_INSET, D.PY0 + D.GASKET_OUT_INSET, D.PY1 - D.GASKET_OUT_INSET)
    m = D.GASKET_IN_MARGIN
    i = (D.VA[0] - m, D.VA[1] + m, D.VA[2] - m, D.VA[3] + m)
    a = prism(*o, D.Z_FRONT, D.Z_GLASS, r=1.0)
    b = prism(*i, D.Z_FRONT - 1, D.Z_GLASS + 1, r=1.0)
    return a.cut(b).val()


PEM_HOLE = 4.22      # sheet hole for a PEM FH-M4 self-clinching stud (+0.08 / -0), PEM bulletin FH
PEG_HOLE_CLR = 0.2   # sheet peg hole = peg dia + this


def build_oven_sheet(D, frame_bb, margin=20.0):
    """patch of the steel front sheet (OVEN_SHEET_T) under the frame: window, stud holes (PEM), peg holes"""
    x0, x1 = frame_bb[0] - margin, frame_bb[1] + margin
    y0, y1 = -frame_bb[3] - margin, -frame_bb[2] + margin          # model Y -> abs y
    s = prism(x0, x1, y0, y1, D.Z_FRONT, D.Z_FRONT - D.OVEN_SHEET_T, r=3.0)
    tools = [prism(*D.cutout_rect(), D.Z_FRONT + 1, D.Z_FRONT - D.OVEN_SHEET_T - 1, r=D.CUTOUT_R)]
    for n, (x, y) in D.STUDS.items():
        tools.append(tube(x, y, D.Z_FRONT + 1, D.Z_FRONT - D.OVEN_SHEET_T - 1, PEM_HOLE))
    for n, (x, y) in D.PEGS.items():
        tools.append(tube(x, y, D.Z_FRONT + 1, D.Z_FRONT - D.OVEN_SHEET_T - 1, D.PEG_D + PEG_HOLE_CLR))
    for t in tools:
        s = s.cut(t)
    return s.val()


def build_studs(D):
    """M4 studs (plain cylinders d 4, length from the stud spec, e.g. FH-M4-18) standing on the sheet's inner face"""
    return [tube(x, y, D.Z_FRONT, D.Z_FRONT + D.STUD_LEN, 4.0).val() for x, y in D.STUDS.values()]


# =====================================================================================================
# run context: resolves the input files, loads frame / params / board once
# =====================================================================================================
class Context:
    def __init__(self, argv=()):
        argv = list(argv)

        def opt(name, default=None):
            if name in argv:
                i = argv.index(name)
                return argv[i + 1]
            return default
        self.v1 = "--v1" in argv
        self.tag = "v1" if self.v1 else "v2"
        self.frame_path = opt("--frame", V1_STEP if self.v1 else V2_STEP)
        self.params_path = opt("--params", V1_PARAMS if self.v1 else V2_PARAMS)
        self.board_path = find_board_step(opt("--board"))
        if self.board_path is None and "--export-board" in argv:
            self.board_path = export_board_step(BOARD_STEP_CANDIDATES[0])
        self.render = "--no-render" not in argv
        # outputs: v2 -> out/, renders_v2/; --v1 regression -> out/v1/, renders_v2/v1_regression/
        self.outdir = opt("--out", os.path.join(HERE, "out", "v1") if self.v1 else os.path.join(HERE, "out"))
        self.imgdir = opt("--img", os.path.join(MECH, "renders_v2", "v1_regression") if self.v1 else
                          os.path.join(MECH, "renders_v2"))
        if self.v1:
            dxf_default = os.path.join(self.imgdir, "Rev3.0_FrontSheet_Pattern_v1check.dxf")
        elif "--img" in argv:          # a run with its own picture folder never overwrites the released DXF
            dxf_default = os.path.join(self.imgdir, "Rev3.0_FrontSheet_Pattern_v2.dxf")
        else:
            dxf_default = os.path.join(MECH, "Rev3.0_FrontSheet_Pattern_v2.dxf")
        self.dxf_path = opt("--dxf", dxf_default)
        os.makedirs(self.outdir, exist_ok=True)
        self._frame = self._D = self._items = None
        self._aux = None

    @property
    def frame(self):
        if self._frame is None:
            self._frame, self.frame_info = load_frame(self.frame_path)
        return self._frame

    @property
    def D(self):
        if self._D is None:
            self.P = Params(self.params_path)
            self._D = Design(self.P)
        return self._D

    @property
    def items(self):
        if self._items is None:
            if not self.board_path:
                raise FileNotFoundError("board STEP not found: pass --board <step>, set FRAME_BOARD_STEP, or use "
                                        "--export-board (kicad-cli, read-only)")
            self._items = board_items(self.board_path)
        return self._items

    @property
    def aux(self):
        """{'sheet', 'gasket', 'oven', 'studs'} built from the params (the oven patch sized to the frame bbox)"""
        if self._aux is None:
            D = self.D
            bb = optimal_bbox(self.frame)
            self._aux = {"sheet": build_sheet(D), "gasket": build_gasket(D), "oven": build_oven_sheet(D, bb),
                         "studs": build_studs(D)}
        return self._aux

    def out(self, name):
        return os.path.join(self.outdir, name)


def dump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=_jsonable)
    return path


def _jsonable(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (tuple, set)):
        return list(o)
    return str(o)
