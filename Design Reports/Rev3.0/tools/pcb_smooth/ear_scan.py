"""Scan ear-hole candidate positions along the top and right edges: distance from the hole centre to the nearest
mains copper (pads/tracks of Mains/MainsHeater nets + HS1 pins) and to the nearest mains component body (courtyard,
F.Fab if none).  System python + shapely.  Usage: ear_scan.py geom.json [off=5]"""
import json, sys
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
G = json.load(open(sys.argv[1])); M = set(G['mains']); off = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
cu = []
for p in G['pads']:
    if p['net'] in M or p['ref'] == 'HS1': cu += [Polygon(q) for q in p['poly'] if len(q) > 2]
for t in G['tracks']:
    if t['net'] in M: cu += [Polygon(q) for q in t['poly'] if len(q) > 2]
CU = unary_union(cu)
bodies = {}
for r, f in G['fps'].items():
    if f['mains'] or r == 'HS1':
        ps = [Polygon(q) for q in (f['crt'] or f['fab']) if len(q) > 2]
        if ps: bodies[r] = unary_union(ps)
def ev(x, y):
    pt = Point(x, y); dc = pt.distance(CU)
    db = min((g.distance(pt), r) for r, g in bodies.items())
    return dc, db
if __name__ == '__main__':
    print("top edge, hole y = %.1f" % -off)
    for x in range(4, 162, 2):
        dc, (db, r) = ev(x, -off); print("  x %5.1f  cu %5.2f  body %5.2f (%s)%s" % (x, dc, db, r, "  OK" if dc >= 8 and db >= 4 else ""))
    print("right edge, hole x = %.1f" % (164 + off))
    for y in range(4, 97, 2):
        dc, (db, r) = ev(164 + off, y); print("  y %5.1f  cu %5.2f  body %5.2f (%s)%s" % (y, dc, db, r, "  OK" if dc >= 8 and db >= 4 else ""))
