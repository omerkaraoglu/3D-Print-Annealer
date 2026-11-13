"""Round 3 checks (system python + shapely) on a geometry JSON from geom_export.py:
- hole table: every M3 hole, local / absolute, centre -> nearest Mains / MainsHeater copper (+ HS1 pins), -> nearest mains
  body (courtyard), Ø 5.5 screw head edge -> panel, 9.4 mm washer keep-out edge -> panel, -> display tail loops
- board envelope (Edge.Cuts bounding box)
- former hole areas (r 4.7 around the old holes): outer / inner pour coverage and the farthest pour point from a GND via
- J11 pad row inside the DS1 CTP finger zone (local x 38.22..41.82)
Usage: r3_checks.py geom.json"""
import json, sys, math
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
G = json.load(open(sys.argv[1])); M = set(G['mains'])
PANEL = box(0.02, -1.0, 164.92, 99.0)
LOOPS = {'CTP loop': box(20.67, 98.95, 55.87, 118.83), 'TFT loop': box(63.97, 98.95, 145.95, 127.69)}   # DS1 Dwgs.User
cu = [Polygon(q).buffer(0) for p in G['pads'] if p['net'] in M or p['ref'] == 'HS1' for q in p['poly'] if len(q) > 2]
cu += [Polygon(q).buffer(0) for t in G['tracks'] if t['net'] in M for q in t['poly'] if len(q) > 2]
CU = unary_union(cu)
bodies = {}
for r, f in G['fps'].items():
    if f['mains'] or r == 'HS1':
        ps = [Polygon(q).buffer(0) for q in (f['crt'] or f['fab']) if len(q) > 2]
        if ps: bodies[r] = unary_union(ps)
holes = sorted(((p['ref'], p['x'], p['y']) for p in G['pads'] if p['ref'][:1] == 'H' and p['ref'][1:].isdigit()), key=lambda h: int(h[0][1:]))
print("| Hole | local (x, y) | absolute (x, y) | centre -> mains copper | -> mains body | head edge -> panel | keep-out edge -> panel | head edge -> tail loop |")
print("|---|---|---|---|---|---|---|---|")
for ref, x, y in holes:
    pt = Point(x, y)
    db = min((g.distance(pt), r) for r, g in bodies.items())
    dl = min((g.distance(pt) - 2.75, n) for n, g in LOOPS.items())
    print("| %s | (%.2f, %.2f) | (%.2f, %.2f) | %.2f mm | %.2f mm (%s) | %.2f mm | %+.2f mm | %.2f mm (%s) |" % (
        ref, x, y, x + 20, y + 20, CU.distance(pt), db[0], db[1], PANEL.distance(pt) - 2.75, PANEL.distance(pt) - 4.7, dl[0], dl[1]))
E = unary_union([Polygon(q).buffer(0) for q in G['edges'] if len(q) > 2])
x0, y0, x1, y1 = E.bounds
print("Edge.Cuts bounding box (with the 0.1 mm stroke): local x %.2f..%.2f, y %.2f..%.2f -> %.2f x %.2f mm; abs x %.2f..%.2f, y %.2f..%.2f" % (
    x0, x1, y0, y1, x1 - x0, y1 - y0, x0 + 20, x1 + 20, y0 + 20, y1 + 20))
print("  outline only (stroke centre): %.1f x %.1f mm" % (x1 - x0 - 0.1, y1 - y0 - 0.1))
gv = [(t['s'][0], t['s'][1]) for t in G['tracks'] if t['cls'] == 'PCB_VIA' and t['net'] == 'GND']
for (hx, hy) in ((4, 4), (4, 95), (97, 95.5), (160, 95)):
    c = Point(hx, hy).buffer(4.7, 64)
    line = []
    for lay in ('F.Cu', 'GND', 'B.Cu'):
        fill = unary_union([Polygon(p[0], p[1:]).buffer(0) for f in G['fills'] if f['net'] == 'GND' and f['layer'] == lay and not f['teardrop'] for p in f['polys']])
        a = fill.intersection(c)
        far = 0.0
        if lay != 'GND' and not a.is_empty:
            mnx, mny, mxx, mxy = a.bounds
            yy = mny
            while yy <= mxy:
                xx = mnx
                while xx <= mxx:
                    if a.contains(Point(xx, yy)):
                        far = max(far, min(math.hypot(xx - vx, yy - vy) for vx, vy in gv))
                    xx += 0.25
                yy += 0.25
        line.append("%s GND %.1f mm2 (%.0f %% of the circle in the board)%s" % (lay, a.area, 100 * a.area / max(c.intersection(box(0, 0, 164, 99)).area, 1e-9),
                                                                         ", farthest point -> GND via %.2f mm" % far if lay != 'GND' else ''))
    nv = sum(1 for vx, vy in gv if math.hypot(vx - hx, vy - hy) <= 4.7)
    print("former hole (%g, %g): %d GND vias within r 4.7 | %s" % (hx, hy, nv, " | ".join(line)))
j = [p for p in G['pads'] if p['ref'] == 'J11' and p['num'] != 'MP']
xs = [x for p in j for q in p['poly'] for x, _ in q]
print("J11 signal pads x %.3f..%.3f (centre row %.3f..%.3f); DS1 CTP finger zone x 38.22..41.82 -> %s" % (
    min(xs), max(xs), min(p['x'] for p in j), max(p['x'] for p in j), 'inside' if min(xs) >= 38.22 and max(xs) <= 41.82 else 'OUTSIDE'))
