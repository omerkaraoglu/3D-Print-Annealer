"""O4 probe: for each signal via without a return via, scan the 1.10-1.60 mm annulus and report, per candidate, the
blocking items at 0.2 mm (netclass) clearance.  Usage: o4_probe.py geom.json"""
import json, sys, math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
G = json.load(open(sys.argv[1]))
items = []
for p in G['pads']:
    for q in p['poly']:
        if len(q) > 2: items.append((Polygon(q).buffer(0), 'pad %s.%s %s' % (p['ref'], p['num'], p['net'][:12]), p['layers']))
for t in G['tracks']:
    for q in t['poly']:
        if len(q) > 2: items.append((Polygon(q).buffer(0), '%s %s %s' % (t['cls'][4:], t['net'][:14], t['layers']), t['layers']))
for f in G['fills']:
    if f['teardrop']:
        for p in f['polys']: items.append((Polygon(p[0], p[1:]).buffer(0), 'TD %s' % f['net'][:12], [f['layer']]))
GI = unary_union([Polygon(p[0], p[1:]).buffer(0) for f in G['fills'] if f['layer'] == 'GND' and f['net'] == 'GND' for p in f['polys']])
CLR = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
RMIN = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
targets = [(146.0, 93.5), (11.8, 40.0), (30.01, 58.0), (59.4, 79.6)]
for (x, y) in targets:
    print("== via", x, y)
    best = []
    for r in [RMIN + 0.05 * i for i in range(int(round((1.6 - RMIN) / 0.05)) + 1)]:
        for k in range(72):
            a = 2 * math.pi * k / 72; px, py = x + r * math.cos(a), y + r * math.sin(a)
            pt = Point(px, py); d = pt.buffer(0.3, 16)
            blk = [(round(g.distance(pt) - 0.3, 2), n) for g, n, l in items if g.distance(pt) < 0.3 + CLR and not ('GND' in n and 'VIA' in n)]
            vblk = [n for g, n, l in items if 'VIA' in n and g.distance(pt) < 1.10 - 0.3 + 0.0]
            inG = GI.contains(pt.buffer(0.35))
            best.append((len(blk) + (0 if inG else 5), round(px, 2), round(py, 2), round(r, 2), inG, blk[:3]))
    best.sort(key=lambda b: (b[0], b[3]))
    for b in best[:4]: print("  ", b)
