"""Helpers for route_display.py: a Router wrapper with a local shapely clearance model (pads, other regions' copper,
keep-outs) so candidate vias/tracks can be tested before they are committed.  Local board mm."""
import json, os, math
from shapely.geometry import Polygon, LineString, Point, box
from shapely.strtree import STRtree
from handroute import Router, SCR, OX, OY

BUS = lambda n: n.startswith(("LCD_", "/Display/SSD_")) or n.split("/")[-1] in (
    ["%s%d" % (c, i) for c in "RGB" for i in range(8)] + ["PCLK", "HSYNC", "VSYNC", "DE"])

class Grid:
    """list-like obstacle store with a 1 mm bucket index"""
    def __init__(self): self.items = []; self.cells = {}
    def append(self, o):
        i = len(self.items); self.items.append(o)
        x0, y0, x1, y1 = o[0].bounds
        for cx in range(int(math.floor(x0)), int(math.floor(x1)) + 1):
            for cy in range(int(math.floor(y0)), int(math.floor(y1)) + 1):
                self.cells.setdefault((cx, cy), []).append(i)
    def near(self, b, m):
        seen = set()
        for cx in range(int(math.floor(b[0] - m)), int(math.floor(b[2] + m)) + 1):
            for cy in range(int(math.floor(b[1] - m)), int(math.floor(b[3] + m)) + 1):
                for i in self.cells.get((cx, cy), ()):
                    if i not in seen and self.items[i] is not None: seen.add(i); yield self.items[i]
    def remove_tag(self, tag):
        for i, o in enumerate(self.items):
            if o is not None and o[1] == tag: self.items[i] = None
    def __iter__(self): return (o for o in self.items if o is not None)

class DR(Router):
    def __init__(self, extra=("tracks_power.json", "_signals_noRST.json", "tracks_mains.json")):
        super().__init__("geom.json")
        g = json.load(open(os.path.join(SCR, "geom.json")))
        self.obs = {"F": Grid(), "B": Grid()}  # (geom, net) with a 1 mm grid index
        for p in g["pads"]:
            poly = Polygon([(x - OX, y - OY) for x, y in p["poly"]])
            for L in (("F", "B") if p["tht"] else p["layers"]):
                if L in ("F", "B"): self.obs[L].append((poly, p["net"] or "<np>"))
        for z in g["zones"]:
            if z["keepout"] and (z.get("no_tracks") or z.get("no_vias")) and z["layers"][0] in ("F", "B"):
                self.obs[z["layers"][0]].append((Polygon([(x - OX, y - OY) for x, y in z["poly"]]), "<keepout>"))
        for fn in extra:
            fp = os.path.join(SCR, fn)
            if not os.path.exists(fp): continue
            for t in json.load(open(fp)):
                self._add_obs(t)
        self.mine = []

    def _geom(self, t):
        if t["via"]: return Point(t["x"] - OX, t["y"] - OY).buffer(t["d"] / 2, 16)
        return LineString([(t["x1"] - OX, t["y1"] - OY), (t["x2"] - OX, t["y2"] - OY)]).buffer(t["w"] / 2, 8)
    def _add_obs(self, t):
        g = self._geom(t)
        for L in (("F", "B") if t["via"] else (t["layer"],)): self.obs[L].append((g, t["net"]))

    def clr(self, a, b):
        if b == "<keepout>": return 0.0
        if b == "<bis>": return 0.13
        if BUS(a) and (BUS(b)): return 0.15
        return 0.2

    def conflicts(self, net, L, geom, esc=False):
        out = []
        for g, n in self.obs[L].near(geom.bounds, 0.3):
            if n == net: continue
            c = self.clr(net, n) if (not esc or n == "<bis>") else 0.13
            if n == "<keepout>":
                if geom.intersects(g) and geom.intersection(g).area > 1e-6: out.append(n)
            elif geom.distance(g) < c - 1e-4: out.append(n)
        return out

    # committed drawing (also becomes an obstacle for later items)
    def track(self, net, layer, pts, w=0.25, strict45=True):
        n0 = len(self.items); super().track(net, layer, pts, w, strict45)
        for t in self.items[n0:]: self._add_obs(t)
    def via(self, net, x, y, d=0.6, drill=0.3):
        super().via(net, x, y, d, drill); self._add_obs(self.items[-1])

    def try_via(self, net, x, y, d=0.6, esc=False):
        g = Point(x, y).buffer(d / 2, 16)
        return not self.conflicts(net, "F", g, esc) and not self.conflicts(net, "B", g, esc)
    def try_track(self, net, L, pts, w=0.25, esc=False):
        g = LineString(pts).buffer(w / 2, 8)
        return not self.conflicts(net, L, g, esc)

def chamfer(pts, c=0.5):
    """not used for exact geometry; routes are written with explicit 45-degree points"""
    return pts

def length(items, net):
    s = 0.0
    for t in items:
        if t["net"] == net and not t["via"]: s += math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"])
    return s
