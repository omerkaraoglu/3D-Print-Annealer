"""Common helpers for the GlassFront (GF-1.0) supplier drawings.

* Params   - read-only access to Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json; every access is logged,
             so each deliverable can report exactly which master parameters it used.
* Choices  - drafting_choices.json (values that are NOT in the master: jig design, reference data from R1/R2,
             inspection limits). Every one of them is a judgement call listed in drawings_report.json.
* FrontView- u = -(x - xc), v = yc - y, origin = glass centre = cut-out centre (master "coordinates").
* rounded-rectangle maths (bulge polylines, exact area/bbox, signed distance), number formatting (EN / TR),
  DXF helpers (mm units, named layers, nothing on layer 0) and DXF verification.

No product dimension is typed in this folder: numbers come from the master file (or, for the jigs and the
reference data, from drafting_choices.json).
"""
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
PARAMS_PATH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
CHOICES_PATH = os.path.join(HERE, "drafting_choices.json")
OUT_DIR = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "drawings")
V2_SHEET_DXF = os.path.join(REPO, "Mechanical", "Rev3.0_Frame", "Rev3.0_FrontSheet_Pattern_v2.dxf")   # read-only
V2_V1PARAMS = os.path.join(REPO, "Design Reports", "Rev3.0", "tools", "frame_v2", "v1_params.json")    # read-only
BRAND_DIR = os.path.join(REPO, "Brand Logo")                                                            # read-only

BULGE90 = math.tan(math.pi / 8.0)          # bulge of a 90 deg arc


# ----------------------------------------------------------------------------------------------------------- params
class Rect:
    """axis-aligned rounded rectangle (any coordinate system): x0 < x1, y0 < y1, corner radius R"""

    def __init__(self, x0, x1, y0, y1, R=0.0, name=""):
        self.x0, self.x1, self.y0, self.y1 = float(x0), float(x1), float(y0), float(y1)
        self.R = float(R or 0.0)
        self.name = name

    @property
    def w(self):
        return self.x1 - self.x0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def c(self):
        return ((self.x0 + self.x1) / 2.0, (self.y0 + self.y1) / 2.0)

    def offset(self, d, name=""):
        """outward offset by d (negative = inward); the radius follows (min 0)"""
        return Rect(self.x0 - d, self.x1 + d, self.y0 - d, self.y1 + d, max(self.R + d, 0.0), name or self.name)

    def area(self):
        return self.w * self.h - (4.0 - math.pi) * self.R ** 2

    def perimeter(self):
        return 2.0 * (self.w + self.h) - 8.0 * self.R + 2.0 * math.pi * self.R

    def sdf(self, x, y):
        """signed distance (outside > 0) of point(s) to the boundary"""
        import numpy as np
        cx, cy = self.c
        hx, hy = self.w / 2.0 - self.R, self.h / 2.0 - self.R
        qx = np.abs(np.asarray(x, float) - cx) - hx
        qy = np.abs(np.asarray(y, float) - cy) - hy
        out = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
        ins = np.minimum(np.maximum(qx, qy), 0.0)
        return out + ins - self.R

    def boundary(self, n_arc=64, step=0.25):
        """dense points along the boundary (for checks and plotting), CCW from (x0 + R, y0)"""
        import numpy as np
        R = self.R
        pts = []

        def seg(a, b):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            k = max(int(L / step), 1)
            for i in range(k):
                t = i / k
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))

        def arc(cx, cy, a0):
            if R <= 0:
                return
            for i in range(n_arc):
                a = math.radians(a0 + 90.0 * i / n_arc)
                pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))

        seg((self.x0 + R, self.y0), (self.x1 - R, self.y0))
        arc(self.x1 - R, self.y0 + R, -90)
        seg((self.x1, self.y0 + R), (self.x1, self.y1 - R))
        arc(self.x1 - R, self.y1 - R, 0)
        seg((self.x1 - R, self.y1), (self.x0 + R, self.y1))
        arc(self.x0 + R, self.y1 - R, 90)
        seg((self.x0, self.y1 - R), (self.x0, self.y0 + R))
        arc(self.x0 + R, self.y0 + R, 180)
        return np.array(pts)

    def bulge_pts(self):
        """CCW vertices (x, y, bulge) for a closed LWPOLYLINE with true 90 deg arcs"""
        R, b = self.R, BULGE90
        if R <= 0:
            return [(self.x0, self.y0, 0), (self.x1, self.y0, 0), (self.x1, self.y1, 0), (self.x0, self.y1, 0)]
        return [(self.x0 + R, self.y0, 0), (self.x1 - R, self.y0, b), (self.x1, self.y0 + R, 0),
                (self.x1, self.y1 - R, b), (self.x1 - R, self.y1, 0), (self.x0 + R, self.y1, b),
                (self.x0, self.y1 - R, 0), (self.x0, self.y0 + R, b)]

    def __repr__(self):
        return "Rect(%s %.3f..%.3f x %.3f..%.3f R%.3f)" % (self.name, self.x0, self.x1, self.y0, self.y1, self.R)


class Params:
    """read-only master parameters with an access log (key -> value used)"""

    def __init__(self, path=PARAMS_PATH):
        self.path = path
        with open(path, encoding="utf-8") as f:
            self.raw = json.load(f)
        self.used = {}
        self._drv = {d["name"]: d for d in self.raw["driving_parameters"]}
        self._rect = {r["name"]: r for r in self.raw["plan_rectangles"]}
        self._pt = {p["name"]: p for p in self.raw["plan_points"]}
        self._fast = {f["name"]: f for f in self.raw["fasteners"]["positions"]}

    def _use(self, key, val):
        self.used[key] = val
        return val

    # --- typed accessors
    def d(self, name):
        return self._use("driving_parameters." + name, self._drv[name]["value"])

    def dnote(self, name):
        return self._use("driving_parameters.%s.note" % name, self._drv[name]["note"])

    def rect(self, name):
        r = self._rect[name]
        self._use("plan_rectangles." + name, [r["x0"], r["x1"], r["y0"], r["y1"], r["R"]])
        return Rect(r["x0"], r["x1"], r["y0"], r["y1"], r["R"] or 0.0, name)

    def pt(self, name):
        return self._use("plan_points." + name, self._pt[name]["value"])

    def fast(self, name):
        return self._use("fasteners.positions." + name, self._fast[name])

    def fast_names(self):
        return [f["name"] for f in self.raw["fasteners"]["positions"]]

    def item(self, path, name):
        """entry `name` of the list at dotted `path` (returns the whole dict)"""
        node = self.get_node(path)
        for it in node:
            if it.get("name") == name:
                self._use("%s.%s" % (path, name), it.get("value"))
                return it
        raise KeyError("%s / %s not in the master file" % (path, name))

    def val(self, path, name):
        return self.item(path, name)["value"]

    def get_node(self, path):
        node = self.raw
        for k in path.split("."):
            node = node[k]
        return node

    def get(self, path):
        return self._use(path, self.get_node(path))

    def num(self, path, regex, group=1, name=None):
        """number parsed from a text value/note of the master (fails loudly if the text changed)"""
        node = self.get_node(path) if name is None else self.item(path, name)
        text = node if isinstance(node, str) else json.dumps(node, ensure_ascii=False)
        m = re.search(regex, text)
        if not m:
            raise ValueError("pattern %r not found in %s%s" % (regex, path, ("/" + name) if name else ""))
        v = float(m.group(group))
        self._use("%s%s ~ /%s/" % (path, ("." + name) if name else "", regex), v)
        return v

    def text(self, path, name=None, field="value"):
        node = self.get_node(path) if name is None else self.item(path, name)
        t = node if isinstance(node, str) else node[field]
        self._use("%s%s.%s" % (path, ("." + name) if name else "", field), t)
        return t

    def onesided(self, path, name):
        """(value, plus, minus, 'R6.25 +0.2/-0'-style text) of an entry whose note starts with '+a/-b'"""
        it = self.item(path, name)
        m = re.match(r"\s*\+([\d.]+)/-([\d.]+)", it["note"])
        if not m:
            raise ValueError("no one-sided '+a/-b' tolerance at the start of %s/%s note" % (path, name))
        a, b = float(m.group(1)), float(m.group(2))
        self._use("%s.%s.note ~ +a/-b" % (path, name), [a, b])
        return it["value"], a, b, "+%s/-%s" % (m.group(1), m.group(2))

    def change(self, path_prefix):
        """(old, new) of the first change_log entry whose path starts with path_prefix"""
        for c in self.raw.get("change_log", {}).get("changes", []):
            if c["path"].startswith(path_prefix):
                self._use("change_log." + c["path"], [c["old"], c["new"]])
                return c["old"], c["new"]
        raise KeyError(path_prefix)

    def level(self, name, glass_t=None):
        """evaluated Z level for a glass thickness (master table)"""
        gt = self.d("glass_t") if glass_t is None else glass_t
        key = "%.1f" % gt
        v = self.raw["derived_levels"]["evaluated_by_glass_t"][key][name]
        return self._use("derived_levels.evaluated_by_glass_t.%s.%s" % (key, name), v)

    @property
    def revision(self):
        return self._use("revision", self.raw["revision"]).split(" ")[0]

    @property
    def status(self):
        return self._use("status", self.raw["status"])


class Choices:
    """drafting_choices.json: values not defined by the master"""

    def __init__(self, path=CHOICES_PATH):
        with open(path, encoding="utf-8") as f:
            self.raw = json.load(f)
        self._it = {c["name"]: c for c in self.raw["items"]}
        self.used = {}

    def __call__(self, name):
        c = self._it[name]
        self.used[name] = {"value": c["value"], "source": c.get("source", "")}
        return c["value"]

    def note(self, name):
        return self._it[name].get("note", "")


# ------------------------------------------------------------------------------------------------------- front view
class FrontView:
    """u = -(x - xc), v = yc - y; origin at the glass centre (= cut-out centre), seen from in front of the oven"""

    def __init__(self, P):
        self.xc, self.yc = P.pt("glass_centre")
        self.P = P

    def uv(self, x, y):
        return (-(x - self.xc), self.yc - y)

    def vec(self, ax, ay):
        """direction (abs, y down) -> direction (u, v)"""
        return (-ax, -ay)

    def rect(self, r: Rect, name=None):
        return Rect(-(r.x1 - self.xc), -(r.x0 - self.xc), self.yc - r.y1, self.yc - r.y0, r.R, name or r.name)

    def check_against_master_text(self):
        """the master states the transform in words; parse it and compare"""
        t = self.P.get("coordinates")
        m = re.search(r"u = -\(x - ([\d.]+)\), v = ([\d.]+) - y", t)
        ok = bool(m) and abs(float(m.group(1)) - self.xc) < 1e-9 and abs(float(m.group(2)) - self.yc) < 1e-9
        return {"text": m.group(0) if m else None, "glass_centre": [self.xc, self.yc], "consistent": ok}


# ------------------------------------------------------------------------------------------------------- formatting
def n(x, nd=3):
    """compact number: up to nd decimals, trailing zeros removed, at least one decimal"""
    s = ("%." + str(nd) + "f") % x
    if nd == 0:
        return "0" if s == "-0" else s
    s = s.rstrip("0")
    if s.endswith("."):
        s += "0"
    if s == "-0.0":
        s = "0.0"
    return s


def n2(x):
    return "%.2f" % x


def tr(s):
    """Turkish decimal comma for numbers inside a string ('0.4' -> '0,4'); keeps standard names like 'ISO 2409'"""
    return re.sub(r"(?<=\d)\.(?=\d)", ",", s)


# -------------------------------------------------------------------------------------------------------- geometry
def stadium_pts(cu, cv, au, av, L, W):
    """closed stadium (slot) as bulge vertices: centre (cu, cv), axis (au, av) unit, length L, width W"""
    h, r = (L - W) / 2.0, W / 2.0
    nu, nv = -av * r, au * r
    p1 = (cu - h * au + nu, cv - h * av + nv)
    p2 = (cu + h * au + nu, cv + h * av + nv)
    p3 = (cu + h * au - nu, cv + h * av - nv)
    p4 = (cu - h * au - nu, cv - h * av - nv)
    pts = [p1, p2, p3, p4]
    a = sum(pts[i][0] * pts[(i + 1) % 4][1] - pts[(i + 1) % 4][0] * pts[i][1] for i in range(4))
    b = 1.0 if a > 0 else -1.0     # CCW polygon: outward half circles are CCW arcs (positive bulge)
    return [(p1[0], p1[1], 0.0), (p2[0], p2[1], b), (p3[0], p3[1], 0.0), (p4[0], p4[1], b)]


def bulge_to_points(vertices, closed=True, seg_deg=2.0):
    """expand (x, y, bulge) vertices into a dense point list (arcs flattened) for plotting / checks"""
    out = []
    m = len(vertices)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        x0, y0, b = vertices[i]
        x1, y1, _ = vertices[(i + 1) % m]
        out.append((x0, y0))
        if abs(b) > 1e-12:
            th = 4.0 * math.atan(b)
            c = math.hypot(x1 - x0, y1 - y0)
            r = c / (2.0 * math.sin(abs(th) / 2.0))
            mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            d = math.sqrt(max(r * r - (c / 2.0) ** 2, 0.0))
            ux, uy = (x1 - x0) / c, (y1 - y0) / c
            # centre is to the left of the chord for a positive bulge < 180 deg
            s = 1.0 if (b > 0) == (abs(th) < math.pi) else -1.0
            cx, cy = mx - s * uy * d, my + s * ux * d
            a0 = math.atan2(y0 - cy, x0 - cx)
            k = max(int(abs(math.degrees(th)) / seg_deg), 2)
            for j in range(1, k):
                a = a0 + th * j / k
                out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if not closed:
        out.append(vertices[-1][:2])
    return out


def poly_area_bulge(vertices):
    """exact signed area of a closed polyline with bulges"""
    m = len(vertices)
    a = 0.0
    for i in range(m):
        x0, y0, b = vertices[i]
        x1, y1, _ = vertices[(i + 1) % m]
        a += 0.5 * (x0 * y1 - x1 * y0)
        if abs(b) > 1e-12:
            th = 4.0 * math.atan(b)
            c = math.hypot(x1 - x0, y1 - y0)
            r = c / (2.0 * math.sin(abs(th) / 2.0))
            seg = 0.5 * r * r * (abs(th) - math.sin(abs(th)))
            a += seg if b > 0 else -seg
    return a


def bulge_arcs(vertices):
    """[(included angle deg, radius)] for every arc segment of a closed bulge polyline"""
    out = []
    m = len(vertices)
    for i in range(m):
        x0, y0, b = vertices[i]
        x1, y1, _ = vertices[(i + 1) % m]
        if abs(b) > 1e-12:
            th = 4.0 * math.atan(b)
            c = math.hypot(x1 - x0, y1 - y0)
            out.append((math.degrees(th), c / (2.0 * math.sin(abs(th) / 2.0))))
    return out


def bbox_points(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), max(xs), min(ys), max(ys))


# ------------------------------------------------------------------------------------------------------------- DXF
def new_dxf(layers):
    """R2010 document in mm with the given layers [(name, colour, linetype)]; returns (doc, msp)"""
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    for name, col, lt in layers:
        doc.layers.add(name, color=col, linetype=lt)
    return doc, doc.modelspace()


def dxf_poly(msp, vertices, layer, closed=True):
    return msp.add_lwpolyline([(x, y, 0, 0, b) for x, y, b in vertices], format="xyseb", close=closed,
                              dxfattribs={"layer": layer})


def dxf_rect(msp, r: Rect, layer):
    return dxf_poly(msp, r.bulge_pts(), layer)


def dxf_text(msp, s, x, y, h=2.5, layer="TEXT", align=None, rot=0.0):
    t = msp.add_text(s, dxfattribs={"layer": layer, "height": h, "rotation": rot})
    if align:
        from ezdxf.enums import TextEntityAlignment
        t.set_placement((x, y), align=getattr(TextEntityAlignment, align))
    else:
        t.set_placement((x, y))
    return t


def dxf_cross(msp, x, y, a, layer):
    msp.add_line((x - a, y), (x + a, y), dxfattribs={"layer": layer})
    msp.add_line((x, y - a), (x, y + a), dxfattribs={"layer": layer})


def dxf_preview(path_dxf, path_png):
    """render a DXF with ezdxf's own drawing add-on (independent of the matplotlib drawing sheets)"""
    import ezdxf
    from ezdxf.addons.drawing import matplotlib as dm
    doc = ezdxf.readfile(path_dxf)
    dm.qsave(doc.modelspace(), path_png, bg="#FFFFFF", dpi=200)


def dxf_inventory(path):
    """re-open a DXF and return a structured inventory + generic checks"""
    import ezdxf
    from collections import Counter
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    cnt = Counter()
    on0 = 0
    open_polys = []
    polys = {}
    for e in msp:
        cnt[(e.dxftype(), e.dxf.layer)] += 1
        if e.dxf.layer == "0":
            on0 += 1
        if e.dxftype() == "LWPOLYLINE":
            v = [(p[0], p[1], p[2]) for p in e.get_points("xyb")]
            polys.setdefault(e.dxf.layer, []).append({"closed": bool(e.closed), "v": v})
            if not e.closed:
                open_polys.append(e.dxf.layer)
    return {
        "doc": doc,
        "units_ok": doc.units == 4 and doc.header.get("$INSUNITS", 0) == 4,
        "entities_on_layer_0": on0,
        "open_polylines": open_polys,
        "counts": {"%s@%s" % k: v for k, v in sorted(cnt.items())},
        "layers": sorted(l.dxf.name for l in doc.layers),
        "polys": polys,
    }


def check_rrect_poly(vertices, r: Rect, tol=1e-3):
    """compare a closed bulge polyline with the rounded rectangle r: area, bbox, every arc 90 deg with radius R"""
    area = abs(poly_area_bulge(vertices))
    pts = bulge_to_points(vertices, seg_deg=0.5)
    # exact bbox: rounded rectangle extremes lie on the straight edges
    bb = bbox_points([(v[0], v[1]) for v in vertices] + pts)
    arcs = bulge_arcs(vertices)
    ok_arcs = (len(arcs) == 4 and all(abs(abs(a) - 90.0) < 1e-6 and abs(rr - r.R) < tol for a, rr in arcs)) \
        if r.R > 0 else len(arcs) == 0
    res = {
        "area": round(area, 4), "area_expected": round(r.area(), 4), "area_ok": abs(area - r.area()) < tol,
        "bbox": [round(b, 4) for b in bb], "bbox_expected": [round(r.x0, 4), round(r.x1, 4), round(r.y0, 4), round(r.y1, 4)],
        "arcs": [[round(a, 4), round(rr, 4)] for a, rr in arcs], "arcs_ok": ok_arcs,
    }
    res["bbox_ok"] = all(abs(a - b) < tol for a, b in zip(bb, (r.x0, r.x1, r.y0, r.y1)))
    res["ok"] = res["area_ok"] and res["bbox_ok"] and res["arcs_ok"]
    return res


def jdump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
