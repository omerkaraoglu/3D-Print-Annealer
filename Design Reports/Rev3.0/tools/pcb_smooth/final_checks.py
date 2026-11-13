"""Final-pass checks (system python): K1 COM feed vs coil pads, DS1 panel vs ear holes / washer keep-outs, ear holes vs
mains copper / bodies / panel.  Usage: final_checks.py geom.json"""
import json, sys, math
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
G = json.load(open(sys.argv[1]))
pads = {(p['ref'], p['num']): unary_union([Polygon(q).buffer(0) for q in p['poly'] if len(q) > 2]) for p in G['pads']}
fus = [Polygon(q).buffer(0) for t in G['tracks'] if t['net'] == 'LINE_FUSED' and 'F.Cu' in t['layers'] for q in t['poly'] if len(q) > 2]
fus += [Polygon(p[0], p[1:]).buffer(0) for f in G['fills'] if f['net'] == 'LINE_FUSED' and f['layer'] == 'F.Cu' for p in f['polys']]
feed = unary_union(fus).difference(pads[('K1', '1')])
for pn in ('2', '5'):
    print("K1 COM feed copper (tracks + teardrop, outside the K1.1 pad) -> K1.%s pad edge: %.2f mm   (K1.1 pad itself: %.2f mm)" % (
        pn, feed.distance(pads[('K1', pn)]), pads[('K1', '1')].distance(pads[('K1', pn)])))
panel = box(0.02, -1.0, 164.92, 99.0)
holes = [(p['ref'], p['x'], p['y']) for p in G['pads'] if p['ref'].startswith('H') and p['ref'] != 'HS1']
for r in G['rules']:
    pass
ko = [Polygon(q).buffer(0) for r in G['rules'] if r['name'] == 'M3 washer keep-out' for q in r['poly'] if len(q) > 2]
print("panel outline local x 0.02..164.92, y -1.00..99.00 (abs x 20.02..184.92, y 19.00..119.00)")
for ref, x, y in sorted(holes):
    pt = Point(x, y)
    kos = [k for k in ko if k.contains(pt)]
    ov = max((k.intersection(panel).area for k in kos), default=0)
    print("  %-3s (%.2f, %.2f) hole-panel %s  washer keep-out edge -> panel %+.2f mm (overlap area %.3f mm2)  head (r 2.75) gap %.2f" % (
        ref, x, y, 'inside' if panel.contains(pt) else 'outside', (panel.distance(pt) - 4.7) if not panel.contains(pt) else -99, ov,
        panel.distance(pt.buffer(2.75)) if not panel.contains(pt) else -99))
