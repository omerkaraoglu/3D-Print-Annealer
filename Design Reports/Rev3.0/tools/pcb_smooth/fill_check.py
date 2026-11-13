"""Task 5 checker on FILLED copper (system python + shapely).  Per zone layer:
- islands: fill polygons, their area, and whether a same-net pad / via / track touches them (connected) or not
- necks: places where an opening with r = 0.25 mm (i.e. copper narrower than 0.5 mm) splits a polygon in two
- slivers / spikes: copper narrower than 0.5 mm that is not a thermal spoke (not within 1.0 mm of a same-net pad or via)
  and larger than 0.05 mm^2
Usage: fill_check.py fills.json geom.json [verbose]"""
import json, sys
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
F = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2])); verbose = 'verbose' in sys.argv
LAYMAP = {'F.Cu': 'F.Cu', 'B.Cu': 'B.Cu', 'GND': 'GND', 'PWR': 'PWR'}


def mk(rings):
    return Polygon(rings[0], rings[1:]).buffer(0)


def parts(g):
    return list(g.geoms) if hasattr(g, 'geoms') else ([g] if not g.is_empty else [])


tot = dict(islands_unconnected=0, necks=0, slivers=0)
for z in F:
    lay = z['layer']
    net = z['net']
    polys = [mk(p) for p in z['polys']]
    if not polys:
        print("%-5s %-6s EMPTY" % (lay, net)); continue
    # same-net anchors on this layer
    anc = []
    for p in G['pads']:
        if p['net'] == net and lay in p['layers']:
            anc += [Polygon(q) for q in p['poly'] if len(q) > 2]
    for t in G['tracks']:
        if t['net'] == net and lay in t['layers']:
            anc += [Polygon(q) for q in t['poly'] if len(q) > 2]
    A = unary_union(anc) if anc else Polygon()
    spokes = A.buffer(1.0)
    isl = []
    for g in polys:
        con = g.intersects(A)
        if not con:
            isl.append((round(g.area, 2), round(g.centroid.x, 1), round(g.centroid.y, 1)))
    necks = []
    slv = []
    for g in polys:
        op = g.buffer(-0.25, join_style=2).buffer(0.25, join_style=2)
        np_ = len([q for q in parts(op) if q.area > 0.05])
        if np_ > 1:
            # the pieces of the opening that are not the biggest: report their centroids
            ps = sorted(parts(op), key=lambda q: -q.area)
            for q in ps[1:]:
                if q.area > 0.05:
                    necks.append((round(q.area, 2), round(q.centroid.x, 1), round(q.centroid.y, 1)))
        thin = g.difference(op.buffer(0.01))
        for q in parts(thin):
            if q.area < 0.05:
                continue
            if q.difference(spokes).area < 0.05:
                continue
            slv.append((round(q.area, 2), round(q.centroid.x, 1), round(q.centroid.y, 1)))
    tot['islands_unconnected'] += len(isl); tot['necks'] += len(necks); tot['slivers'] += len(slv)
    print("%-5s %-6s polygons %3d area %8.1f mm2 | unconnected islands %d | neck pieces %d | slivers %d" % (
        lay, net, len(polys), sum(g.area for g in polys), len(isl), len(necks), len(slv)))
    if verbose:
        for x in isl: print("     island", x)
        for x in necks: print("     neck-piece", x)
        for x in slv: print("     sliver", x)
print("TOTAL", tot)
