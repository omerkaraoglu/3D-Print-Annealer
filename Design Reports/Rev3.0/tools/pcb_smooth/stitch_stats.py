"""Stitching statistics: GND via count, nearest-neighbour spacing, coverage (distance from every 0.5 mm sample point of the
outer GND pours to the nearest GND via), edge fence pitch, return-via distances.  Usage: stitch_stats.py geom.json stitch.json"""
import json, sys, math
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import vectorized
G = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2]))
V = np.array([t['s'] for t in G['tracks'] if t['cls'] == 'PCB_VIA' and t['net'] == 'GND'])
SIG = [(t['s'], t['net']) for t in G['tracks'] if t['cls'] == 'PCB_VIA' and t['net'] not in ('GND', '+3V3', '+5V', '+1V2')]
print("GND vias total", len(V), "of which stitching (this round)", len(plan['vias']))
from collections import Counter
print(Counter(k for _, _, k in plan['vias']))
d = np.sqrt(((V[:, None, :] - V[None, :, :]) ** 2).sum(-1)); np.fill_diagonal(d, 1e9)
nn = d.min(1)
print("nearest-neighbour GND via spacing: min %.2f median %.2f max %.2f mm" % (nn.min(), np.median(nn), nn.max()))
fill = []
for f in G['fills']:
    if f['net'] == 'GND' and f['layer'] in ('F.Cu', 'B.Cu') and not f['teardrop']:
        fill += [Polygon(p[0], p[1:]).buffer(0) for p in f['polys']]
A = unary_union(fill)
xs, ys = np.meshgrid(np.arange(0.25, 164, 0.5), np.arange(0.25, 99, 0.5))
m = vectorized.contains(A, xs, ys)
P = np.c_[xs[m], ys[m]]
dist = np.full(len(P), 1e9)
for i in range(0, len(V), 200):
    dd = np.sqrt(((P[:, None, :] - V[None, i:i + 200, :]) ** 2).sum(-1)).min(1)
    dist = np.minimum(dist, dd)
for q in (50, 90, 95, 99, 100):
    print("coverage: %3d %% of the outer GND pour area is within %.2f mm of a GND via" % (q, np.percentile(dist, q)))
print("  (a square grid of pitch p leaves at most p/sqrt(2) = %.2f mm for p = 4.5; %.2f mm for p = 5)" % (4.5 / 2 ** .5, 5 / 2 ** .5))
far = P[dist > 3.54]
if len(far):
    print("  sample points farther than 3.54 mm (5 mm grid equivalent):", len(far), "of", len(P))
# fence pitch along the edge
fence = np.array([(x, y) for x, y, k in plan['vias'] if k == 'edge fence'])
if len(fence):
    df = np.sqrt(((fence[:, None, :] - fence[None, :, :]) ** 2).sum(-1)); np.fill_diagonal(df, 1e9)
    print("edge fence: %d vias, nearest-neighbour pitch median %.2f, max %.2f mm" % (len(fence), np.median(df.min(1)), df.min(1).max()))
split = np.array([(x, y) for x, y, k in plan['vias'] if k == 'split fence'])
if len(split):
    ds = np.sqrt(((split[:, None, :] - split[None, :, :]) ** 2).sum(-1)); np.fill_diagonal(ds, 1e9)
    print("+5V split fence: %d vias, nearest-neighbour pitch median %.2f, max %.2f mm" % (len(split), np.median(ds.min(1)), ds.min(1).max()))
rd = []
for (s, n) in SIG:
    dd = np.sqrt(((V - np.array(s)) ** 2).sum(1)).min()
    rd.append((dd, n, s))
rd.sort()
print("signal vias %d: return GND via centre distance <= 1.6 mm (edge gap <= 1.0): %d, <= 2.1: %d, farther: %d" % (
    len(rd), sum(1 for x in rd if x[0] <= 1.605), sum(1 for x in rd if 1.605 < x[0] <= 2.105), sum(1 for x in rd if x[0] > 2.105)))
for x in rd:
    if x[0] > 2.105:
        print("   %-40s (%.2f,%.2f) nearest GND via %.2f mm" % (x[1][-40:], x[2][0], x[2][1], x[0]))
