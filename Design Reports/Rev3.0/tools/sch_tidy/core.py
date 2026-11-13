"""Core of the Rev3.0 schematic tidy round (2026-11-13).

- loads a KiCad 10 sheet with sexp.py, keeps the symbol instances (UUIDs, refs, pins, instance paths),
  the sheet symbols and lib_symbols, drops every drawn item (wires, labels, junctions, no-connects,
  texts, rectangles, power symbols) and regenerates them through the Builder API;
- the target connectivity is the baseline netlist (kicadxml): every pin knows its net, so the drawing
  helpers only say *where* to wire/label, never *which* net (the names come from the baseline);
- an internal connectivity model (exact-point connections, T-joins split, labels by name, power by
  value) checks the drawing against the baseline before anything is written.
"""
import copy
import math
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sexp import parse, dump, find, first, Sym  # noqa: E402

PROJECT = "3dFilamentDryer"
ROOT_UUID = "ea3996f2-7d6b-4a86-86ab-4ed62213f41f"
SCRATCH = r"C:/Users/lenovo/AppData/Local/Temp/claude/dad0af2289ad5142/c8708701-d586-4d89-8e7b-a64a4af1e14d/scratchpad"
BASELINE = SCRATCH + "/sch_baseline"
BACKUP = SCRATCH + "/sch_tidy_backup"
REAL_PROJ = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer"
REAL_LIB = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3/Rev3.kicad_sym"
KICAD_CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"

FILES = {"root": "3dFilamentDryer.kicad_sch", "Display": "Rev3_Display.kicad_sch",
         "Thermocouple": "Rev3_Thermocouple.kicad_sch", "Power": "Rev3_Power.kicad_sch",
         "InputFilter": "Rev3_InputFilter.kicad_sch"}
# netlist sheet-path prefix of each sheet's local labels
NETPREFIX = {"root": "/", "Display": "/Display/", "Thermocouple": "/Thermocouple front end (K-type, ADS1115)/",
             "Power": "/Power/", "InputFilter": "/Mains input EMC filter/"}
PAGE = {"root": 1, "Display": 2, "Thermocouple": 3, "Power": 4, "InputFilter": 5}

G = 2.54
S = Sym


def fmt(v):
    r = round(float(v), 4)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return ("%.4f" % r).rstrip("0").rstrip(".")


def N(v):
    return S(fmt(v))


def key(p):
    return (round(p[0], 3), round(p[1], 3))


def U():
    return str(uuid.uuid4())


def xf(x, y, rot, mirror):
    """symbol-local (x right, y up) -> sheet offset (y down); rotation first, then mirror (KiCad semantics,
    as validated on Battery Sentinel and re-validated here against the baseline netlist)."""
    r = math.radians(rot)
    xr = x * math.cos(r) - y * math.sin(r)
    yr = x * math.sin(r) + y * math.cos(r)
    sx, sy = xr, -yr
    if mirror == "x":
        sy = -sy
    if mirror == "y":
        sx = -sx
    return round(sx, 6), round(sy, 6)


# ----------------------------------------------------------------------------------- lib symbols
class LibSym:
    def __init__(self, node):
        self.node = node
        self.name = node[1]
        base = self.name.split(":")[-1]
        self.pins = []           # dicts: num, name, x, y, ang, len, type, unit, hidden
        self.gfx = defaultdict(list)   # unit -> list of (x, y) points of the body graphics
        self.power = any(isinstance(x, list) and x and x[0] == "power" for x in node)
        for sub in find(node, "symbol"):
            m = re.match(re.escape(base) + r"_(\d+)_(\d+)$", sub[1])
            if not m:
                m = re.match(r".*_(\d+)_(\d+)$", sub[1])
            unit, style = int(m.group(1)), int(m.group(2))
            if style == 2:
                continue
            for p in find(sub, "pin"):
                at = first(p, "at")
                ln = first(p, "length")
                hidden = any(isinstance(x, list) and x and x[0] == "hide" and (len(x) < 2 or x[1] == "yes") for x in p) or S("hide") in p
                self.pins.append(dict(num=str(first(p, "number")[1]), name=str(first(p, "name")[1]), x=float(at[1]), y=float(at[2]),
                                      ang=float(at[3]) if len(at) > 3 else 0.0, len=float(ln[1]), type=str(p[1]), unit=unit,
                                      hidden=hidden))
            for g in sub:
                if not isinstance(g, list) or not g:
                    continue
                if g[0] == "rectangle":
                    a, b = first(g, "start"), first(g, "end")
                    self.gfx[unit] += [(float(a[1]), float(a[2])), (float(b[1]), float(b[2]))]
                elif g[0] == "polyline" or g[0] == "bezier":
                    for xy in find(first(g, "pts"), "xy"):
                        self.gfx[unit].append((float(xy[1]), float(xy[2])))
                elif g[0] == "circle":
                    c = first(g, "center"); r = float(first(g, "radius")[1])
                    self.gfx[unit] += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
                elif g[0] == "arc":
                    for k in ("start", "mid", "end"):
                        q = first(g, k)
                        if q:
                            self.gfx[unit].append((float(q[1]), float(q[2])))

    def unit_pins(self, unit):
        return [p for p in self.pins if p["unit"] in (0, unit)]

    def body(self, unit):
        pts = self.gfx.get(0, []) + self.gfx.get(unit, [])
        if not pts:
            return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)


def prop_node(sym, name):
    for p in find(sym, "property"):
        if p[1] == name:
            return p
    return None


def getprop(sym, name):
    p = prop_node(sym, name)
    return None if p is None else p[2]


# ----------------------------------------------------------------------------------- target netlist
# round 2 (2026-11-13): auto-named nets of the programmer / auto-boot block get root-local labels (approved rename;
# connectivity unchanged, "Update PCB from Schematic" renames these nets only)
RENAME = {"Net-(Q3-C)": "/EN", "Net-(Q2-C)": "/IO0", "Net-(J2-Pin_2)": "/RTS", "Net-(J2-Pin_3)": "/DTR",
          "Net-(J2-Pin_4)": "/RXD0", "Net-(J2-Pin_5)": "/TXD0"}


class Target:
    """baseline connectivity: pin -> net, net -> pins, plus how each net is named"""

    def __init__(self, xml_path, sheets_dir, rename=None):
        root = ET.parse(xml_path).getroot()
        self.pin_net = {}
        self.net_pins = {}
        for n in root.find("nets"):
            name = n.get("name")
            pins = set()
            for nd in n.findall("node"):
                pins.add((nd.get("ref"), nd.get("pin")))
                self.pin_net[(nd.get("ref"), nd.get("pin"))] = name
            self.net_pins[name] = pins
        for a, b in (rename or {}).items():
            self.net_pins[b] = self.net_pins.pop(a)
            for pn in self.net_pins[b]:
                self.pin_net[pn] = b
        self.comp_fields = {}
        for c in root.find("components"):
            self.comp_fields[c.get("ref")] = c
        # power and global names, global label shapes from the baseline drawings
        self.power_names = set()
        self.global_shapes = {}
        for k, f in FILES.items():
            t = parse(open(os.path.join(sheets_dir, f), encoding="utf-8").read())
            for s in find(t, "symbol"):
                lid = first(s, "lib_id")[1]
                if lid.startswith("power:") and lid != "power:PWR_FLAG":
                    self.power_names.add(getprop(s, "Value"))
            for g in find(t, "global_label"):
                self.global_shapes[g[1]] = str(first(g, "shape")[1])

    def kind(self, net, sheet):
        """('power', name) | ('global', name) | ('local', name) | ('auto', None) | ('nc', None)"""
        if net in self.power_names:
            return "power", net
        if net in self.global_shapes:
            return "global", net
        if net.startswith("unconnected-"):
            return "nc", None
        if "Net-(" in net:
            return "auto", None
        pre = NETPREFIX[sheet]
        assert net.startswith(pre), (net, sheet)
        return "local", net[len(pre):]


# ----------------------------------------------------------------------------------- sheet document
class Doc:
    def __init__(self, path, sheet):
        self.path = path
        self.sheet = sheet
        self.text = open(path, encoding="utf-8", newline="").read()
        self.tree = parse(self.text)
        self.libs = {}
        for s in find(first(self.tree, "lib_symbols"), "symbol"):
            self.libs[s[1]] = LibSym(s)
        self.symbols = {}         # ref -> node (real parts only)
        self.power_syms = []
        for s in find(self.tree, "symbol"):
            ref = getprop(s, "Reference")
            if ref.startswith("#"):
                self.power_syms.append(s)
            else:
                assert ref not in self.symbols, ref
                self.symbols[ref] = s
        self.sheets = find(self.tree, "sheet")
        # instance path of this sheet (from any symbol)
        anys = next(iter(self.symbols.values()))
        self.inst_path = first(first(first(anys, "instances"), "project"), "path")[1]

    def lib_of(self, ref):
        return self.libs[first(self.symbols[ref], "lib_id")[1]]

    def placement(self, node):
        at = first(node, "at")
        m = first(node, "mirror")
        unit = first(node, "unit")
        return float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, (str(m[1]) if m else None), int(unit[1]) if unit else 1

    def pins_of(self, node):
        """[(num, (x, y), (ux, uy) outward, pin dict)]"""
        lib = self.libs[first(node, "lib_id")[1]]
        x, y, rot, mir, unit = self.placement(node)
        out = []
        for p in lib.unit_pins(unit):
            dx, dy = xf(p["x"], p["y"], rot, mir)
            a = math.radians(p["ang"])
            ox, oy = xf(-math.cos(a), -math.sin(a), rot, mir)
            out.append((p["num"], (round(x + dx, 4), round(y + dy, 4)), (round(ox), round(oy)), p))
        return out


# ----------------------------------------------------------------------------------- connectivity model
class Conn:
    """exact-point connectivity of one sheet: wires (T-joins on wire interiors count), pins, labels, power."""

    def __init__(self):
        self.parent = {}

    def f(self, a):
        while self.parent.setdefault(a, a) != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def u(self, a, b):
        ra, rb = self.f(a), self.f(b)
        if ra != rb:
            self.parent[ra] = rb


def on_seg(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if abs(x1 - x2) < 1e-6 and abs(x - x1) < 1e-6:
        return min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6
    if abs(y1 - y2) < 1e-6 and abs(y - y1) < 1e-6:
        return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6
    return False


def sheet_clusters(wires, points, junctions=()):
    """wires: [(a, b)]; points: [(pt, tag)] (pins, labels, power pins, junctions).
    returns dict tag -> cluster id (points connected by coincidence or through wires)."""
    c = Conn()
    jset = set(key(j) for j in junctions)
    allpts = set(key(p) for p, _ in points) | jset
    for a, b in wires:
        allpts.add(key(a)); allpts.add(key(b))
    for i, (a, b) in enumerate(wires):
        w = ("W", i)
        c.u(w, ("P", key(a)))
        c.u(w, ("P", key(b)))
        for p in allpts:
            if p != key(a) and p != key(b) and p in jset and on_seg(p, a, b):
                # a point on a wire interior connects only through a junction dot (KiCad connection graph)
                c.u(w, ("P", p))
    res = {}
    for p, tag in points:
        res[tag] = c.f(("P", key(p)))
    return res, c


def interior_hits(wires, pts):
    """connection points lying strictly inside a wire (T without split) -> list"""
    hits = []
    for a, b in wires:
        for p in pts:
            if key(p) != key(a) and key(p) != key(b) and on_seg(p, a, b):
                hits.append((p, a, b))
    return hits
