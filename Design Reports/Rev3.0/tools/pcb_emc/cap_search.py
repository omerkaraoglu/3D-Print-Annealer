"""Search 0402 + two-via (dog-bone) sites for the +5V-GND capacitors at the J10 re-sort via field.
Rules: pads/vias >= 0.2 mm from foreign copper (F.Cu for pads, every layer's tracks/pads for vias), +5V via >= 1.35 mm
from non-GND vias and >= 1.10 mm from GND vias; GND via >= 1.10 mm from non-GND vias, >= 0.9 mm from GND vias;
courtyards may not overlap.  Usage: cap_search.py geo.json"""
import json, sys, math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree
G = json.load(open(sys.argv[1]))
FIELD = {"/Display/B2": [(113.5, 62.9), (117.6, 76.65)], "/Display/B3": [(114.85, 63.4), (118.85, 77.25)],
         "/Display/DE": [(113.1, 73.65), (113.1, 84.2)], "/Display/PCLK": [(114.35, 74.25), (114.35, 80.95)],
         "/Display/HSYNC": [(115.6, 74.85), (115.6, 81.95)], "/Display/VSYNC": [(116.85, 75.45), (116.85, 82.95)]}
def geoms(layer):
    gs = []
    for s in G["segs"]:
        if s[6] == layer: gs.append((LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2), s[5]))
    for p in G["pads"]:
        if layer in p["layers"] and len(p["pts"]) >= 3: gs.append((Polygon(p["pts"]), p["net"]))
    for v in G["vias"]:
        gs.append((Point(v[0], v[1]).buffer(v[2] / 2), v[3]))
    return gs
F = geoms("F.Cu"); B = geoms("B.Cu")
FT = STRtree([g for g, n in F]); BT = STRtree([g for g, n in B])
def clear(shape, net, tree, items, c=0.2):
    for i in tree.query(shape.buffer(c)):
        g, n = items[i]
        if n != net and g.distance(shape) < c: return False
    return True
CRT = [box(*v) for v in G["crt"].values()]
# board silk graphics (QR code, legend maps, artwork): no part under them (0.15 mm margin)
SILK = [box(*v[:4]).buffer(0.15) for v in json.load(open("silk_boxes.json"))]
def ok(cx, cy, rot):
    ax = (1, 0) if rot == 0 else (0, 1)
    p1 = (cx - 0.48 * ax[0], cy - 0.48 * ax[1]); p2 = (cx + 0.48 * ax[0], cy + 0.48 * ax[1])
    v1 = (cx - 1.33 * ax[0], cy - 1.33 * ax[1]); v2 = (cx + 1.33 * ax[0], cy + 1.33 * ax[1])
    hw, hh = (0.295, 0.32) if rot == 0 else (0.32, 0.295)
    pad1 = box(p1[0] - hw, p1[1] - hh, p1[0] + hw, p1[1] + hh); pad2 = box(p2[0] - hw, p2[1] - hh, p2[0] + hw, p2[1] + hh)
    if not clear(pad1, "+5V", FT, F) or not clear(pad2, "GND", FT, F): return None
    for (vx, vy), net in ((v1, "+5V"), (v2, "GND")):
        c = Point(vx, vy).buffer(0.3)
        if not clear(c, net, FT, F) or not clear(c, net, BT, B): return None
        for v in G["vias"]:
            d = math.hypot(v[0] - vx, v[1] - vy)
            if net == "+5V" and ((v[3] != "GND" and d < 1.35) or (v[3] == "GND" and d < 1.10)): return None
            if net == "GND" and ((v[3] != "GND" and d < 1.10) or (v[3] == "GND" and d < 0.9)): return None
    cr = box(cx - (0.93 if rot == 0 else 0.48), cy - (0.48 if rot == 0 else 0.93), cx + (0.93 if rot == 0 else 0.48), cy + (0.48 if rot == 0 else 0.93))
    if any(cr.intersects(c) for c in CRT) or any(cr.intersects(c) for c in SILK): return None
    return (v1, v2)
fv = [p for ps in FIELD.values() for p in ps if p[1] > 73]
for side, xr in (("west", (106.0, 113.0)), ("east", (117.5, 126.0))):
    best = []
    x = xr[0]
    while x <= xr[1]:
        y = 64.0
        while y <= 88.0:
            for rot in (0, 90):
                r = ok(x, y, rot)
                if r:
                    d = min(math.hypot(x - a, y - b) for a, b in fv)
                    best.append((round(d, 2), round(x, 2), round(y, 2), rot, [tuple(round(c, 2) for c in v) for v in r]))
            y += 0.1
        x += 0.1
    best.sort()
    print(side, len(best), best[:8])
