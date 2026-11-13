"""Task 6: plan GND stitching vias (system python + shapely) from a geometry JSON written by geom_export.py.
Via 0.6 / 0.3 mm (GND is in the Default net class: 0.6 / 0.3; IPC-6012 class 2 / IPC-2221B annular ring: (0.6 - 0.3) / 2
= 0.15 mm nominal, >= 0.05 mm after drill tolerance).

A position is valid when
  - it lies in the SELV GND area: inside the In1 GND fill and inside the F.Cu or B.Cu GND fill, the via disc plus
    0.25 mm fully inside that fill (no new sliver at a pour edge)
  - copper of every other item (pads of any net, tracks / arcs of any net, vias, teardrops, other-net fills on the
    outer layers) >= 0.3 mm from the via edge; never on a pad
  - not in a rule area that forbids vias (washer rings, antenna, inner-layer keep-outs, mains band, heatsink, U10
    corner), not in the u20_escape area (ADS1115) nor the opto / relay / triac fan-out rule areas, not in the
    thermocouple quiet area (vias inside u10_escape are allowed, with the same 0.3 mm clearance: they stitch the
    F.Cu ground under the SSD1963 body)
  - >= 6.4 mm from any Mains / MainsHeater copper and from the HS1 pins (reinforced creepage; clearance 4 mm is
    then met too), >= 0.8 mm from the board edge (0.5 mm edge clearance + 0.3 mm)
  - In2: the 0.55 mm anti-pad (0.3 + 0.25 zone clearance) plus a 0.5 mm web lies entirely inside one In2 fill
    polygon (+3V3 or +5V) or entirely outside all of them (no slivers / islands in the power planes)
  - >= 1.35 mm centre-to-centre from every other via (so In1 / In2 anti-pads keep a >= 0.25 mm web, pass-3 rule)
Placement order: return vias next to every signal via (1.35-1.6 mm centre distance, i.e. <= 1.0 mm edge gap), rings at
U10, at the GND pads of J10 / J11, along the 8080 bus and the RGB ribbon, a 3 mm fence along the SELV board edge and
along the +5V island split in In2, one via into every GND fill piece that has no via yet (islands), then a grid of
<= 4.5 mm pitch (a node is skipped if a GND via is already within 2.5 mm; otherwise the nearest valid point within
1.5 mm is used).
Round 3: run again on a board that already carries the stitching, the planner only adds vias where coverage is
missing (every step skips points with a GND via nearby; the hand-placed O4 vias are not duplicated).
`region=x0,y0,x1,y1` (local mm, repeatable) restricts new vias to those boxes (round 3: the J11 area and the four
former hole areas).
Usage: stitch_plan.py geom.json out.json [skip.json] [region=...]"""
import json, sys, math
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
REGION = [tuple(map(float, a[7:].split(','))) for a in sys.argv if a.startswith('region=')]
sys.argv = [a for a in sys.argv if not a.startswith('region=')]
G = json.load(open(sys.argv[1]))
skip = set(tuple(x) for x in json.load(open(sys.argv[3]))) if len(sys.argv) > 3 else set()
M = set(G['mains'])
RV, RD = 0.3, 0.15
CLR = 0.3
VIA_SP = 1.35


def P(r):
    return Polygon(r[0], r[1:]).buffer(0) if isinstance(r[0][0], (list, tuple)) and isinstance(r[0][0][0], (int, float)) else Polygon(r).buffer(0)


def fill_union(layer, net, teardrop=False):
    gs = []
    for f in G['fills']:
        if f['layer'] == layer and f['net'] == net and f['teardrop'] == teardrop:
            gs += [Polygon(p[0], p[1:]).buffer(0) for p in f['polys']]
    return unary_union(gs) if gs else Polygon()


GF, GB, GI = fill_union('F.Cu', 'GND'), fill_union('B.Cu', 'GND'), fill_union('GND', 'GND')
PWR = [Polygon(p[0], p[1:]).buffer(0) for f in G['fills'] if f['layer'] == 'PWR' and not f['teardrop'] for p in f['polys']]
PWRU = unary_union(PWR)
P5 = fill_union('PWR', '+5V')
# obstacles: all pads, tracks, arcs, existing vias, teardrop fills, other-net outer fills
obst = []
mains_cu = []
for p in G['pads']:
    for q in p['poly']:
        if len(q) > 2:
            g = Polygon(q).buffer(0); obst.append(g)
            if p['net'] in M or p['ref'] == 'HS1': mains_cu.append(g)
vias = []
for t in G['tracks']:
    for q in t['poly']:
        if len(q) > 2:
            g = Polygon(q).buffer(0); obst.append(g)
            if t['net'] in M: mains_cu.append(g)
    if t['cls'] == 'PCB_VIA':
        vias.append((t['s'][0], t['s'][1], t['net'], t['w']))
for f in G['fills']:
    if f['teardrop'] or (f['layer'] in ('F.Cu', 'B.Cu') and f['net'] != 'GND'):
        obst += [Polygon(p[0], p[1:]).buffer(0) for p in f['polys']]
OB = STRtree(obst)
MAINS = unary_union(mains_cu)
EDGE = unary_union([Polygon(q).buffer(0) for q in G['edges'] if len(q) > 2])   # edge cut strokes (thin polygons)
# board area: from the GND plane outline region; edge distance via edge strokes
forbid = []
for r in G['rules']:
    if r['no_vias'] or r['name'] in ('u20_escape', 'q1_fanout', 'k1_pins', 'u1_pins', 'u5_pins'):
        forbid += [Polygon(q).buffer(0) for q in r['poly'] if len(q) > 2]
QUIET = box(4.0, 77.5, 33.6, 87.5)          # thermocouple pair + RC filter + ADS1115 inputs (spec 6 / 12.3)
forbid.append(QUIET)
FORB = unary_union(forbid)
MAINS_KO = MAINS.buffer(6.4 + RV)
placed = []          # (x, y, kind)
allv = [(x, y) for x, y, n, w in vias]
gndv = [(x, y) for x, y, n, w in vias if n == 'GND']
rej = {}


def why(x, y, outer=True):
    pt = Point(x, y)
    d = pt.buffer(RV, 16)
    if (round(x, 3), round(y, 3)) in skip: return 'skip'
    if REGION and not any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in REGION): return 'outside region'
    if EDGE.distance(pt) < 0.5 + RV: return 'edge'
    if FORB.intersects(d): return 'rule area'
    if MAINS_KO.contains(pt) or MAINS.distance(pt) < 6.4 + RV: return 'mains 6.4'
    if not GI.contains(pt.buffer(RV + 0.1, 16)): return 'not in In1 GND'
    dd = pt.buffer(RV + 0.25, 16)
    if outer and not (GF.contains(dd) or GB.contains(dd)): return 'not in outer GND pour'
    hits = OB.query(pt.buffer(RV + CLR, 16))
    for i in hits:
        if obst[i].distance(pt) < RV + CLR - 1e-6: return 'copper'
    ap = pt.buffer(0.55 + 0.5, 16)
    if PWRU.intersects(ap) and not any(g.contains(ap) for g in PWR): return 'In2 web'
    for (vx, vy) in allv:
        if (vx - x) ** 2 + (vy - y) ** 2 < VIA_SP ** 2: return 'via spacing'
    return None


def ok(x, y, outer=True):
    w = why(x, y, outer)
    if w: rej[w] = rej.get(w, 0) + 1
    return w is None


def add(x, y, kind):
    placed.append((round(x, 3), round(y, 3), kind)); allv.append((x, y)); gndv.append((x, y))


def near_gnd(x, y, r):
    return any((vx - x) ** 2 + (vy - y) ** 2 < r * r for vx, vy in gndv)


def try_around(x, y, kind, rmax=1.5, step=0.25, need_free=None):
    if ok(x, y) and (need_free is None or not near_gnd(x, y, need_free)):
        add(x, y, kind); return True
    r = step
    while r <= rmax + 1e-9:
        n = max(8, int(2 * math.pi * r / step))
        for k in range(n):
            a = 2 * math.pi * k / n
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            if ok(px, py) and (need_free is None or not near_gnd(px, py, need_free)):
                add(px, py, kind); return True
        r += step
    return False


# 0) final pass (O4): return vias placed by hand at the four signal vias the automatic search could not serve
#    (positions from o4_probe.py: >= 0.3 mm from all other copper, 1.0-1.5 mm from the signal via, edge gap <= 1.0 mm)
FORCED = [(147.35, 93.5, 'return O4 VLED_N'), (12.43, 38.64, 'return O4 J2 TXD0/RXD0'),
          (29.12, 58.46, 'return O4 Q4-B'), (60.67, 80.06, 'return O4 BL_PWM')]
for fx, fy, fk in FORCED:
    if not any(math.hypot(vx - fx, vy - fy) < 0.05 for vx, vy in gndv):   # round 3: already on the board -> keep, no copy
        add(fx, fy, fk)
# 1) return vias at signal vias
SUP = {'GND', '+3V3', '+5V', '+1V2'}
ret_ok, ret_miss = 0, []
# a return via only has to reach the In1 ground the signal referenced on F.Cu, so it need not sit in an outer pour
for (x, y, n, w) in vias:
    if n in SUP or n in M: continue
    if any(math.hypot(vx - x, vy - y) <= 1.6 + 1e-6 for vx, vy in gndv):
        ret_ok += 1; continue
    done = False
    for r in (1.35, 1.45, 1.55, 1.6):
        for k in range(36):
            a = 2 * math.pi * k / 36
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            if ok(px, py, outer=False):
                add(px, py, 'return'); done = True; break
        if done: break
    if done: ret_ok += 1
    else: ret_miss.append((n, round(x, 2), round(y, 2)))
# second pass for the misses: up to 2.1 mm centre distance (<= 1.5 mm edge gap)
ret_far, still = [], []
for (n, x, y) in ret_miss:
    if any(math.hypot(vx - x, vy - y) <= 2.1 + 1e-6 for vx, vy in gndv):
        ret_far.append((n, x, y, 'existing')); continue
    done = False
    for r in (1.7, 1.8, 1.9, 2.0, 2.1):
        for k in range(48):
            a = 2 * math.pi * k / 48
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            if ok(px, py, outer=False):
                add(px, py, 'return (<=1.5 gap)'); done = True; break
        if done: break
    (ret_far if done else still).append((n, x, y))
print("return vias: <=1.0 mm gap", ret_ok, "| <=1.5 mm gap", len(ret_far), "| none", len(still), still)
ret_miss = still


# helper: vias along a polyline at pitch
def along(line, pitch, kind, rmax=1.0, free=None):
    L = line.length
    if L < 1e-6: return
    k = max(1, int(L // pitch))
    for i in range(k + 1):
        q = line.interpolate(i * L / k)
        try_around(q.x, q.y, kind, rmax=rmax, need_free=free)


# 2) U10 ring (QFP body 14 x 14 + 1.0 mm leads -> ring 1.6 mm outside the pad ring), J10 / J11 GND pads
fp = G['fps']
u10 = fp['U10']['pos']
ring = box(u10[0] - 9.6, u10[1] - 9.6, u10[0] + 9.6, u10[1] + 9.6).exterior
along(ring, 2.5, 'ring U10', rmax=0.8, free=1.3)
for p in G['pads']:
    if p['ref'] in ('J10', 'J11') and p['net'] == 'GND':
        try_around(p['x'], p['y'] - 2.2, 'ring J10/J11', rmax=1.2, need_free=1.3)
        try_around(p['x'], p['y'] + 2.2, 'ring J10/J11', rmax=1.2, need_free=1.3)
# 8080 bus / RGB ribbon: vias beside the bundles every 4 mm (a via 1 mm outside the outermost track of a bundle
# is found by the grid; here: along each bus / RGB track at 4 mm, offset 1.2 mm to either side, if room)
for t in G['tracks']:
    n = t['net']
    if t['cls'] == 'PCB_VIA' or not (n.startswith('/Display/SSD_') or n.endswith('_T') or n.split('/')[-1][:1] in 'RGB' and n.startswith('/Display/') and n.split('/')[-1][1:].isdigit()):
        continue
    s, e = t['s'], t['e']
    Lr = math.hypot(e[0] - s[0], e[1] - s[1])
    if Lr < 4: continue
    ux, uy = (e[0] - s[0]) / Lr, (e[1] - s[1]) / Lr
    for i in range(1, int(Lr // 4) + 1):
        cx, cy = s[0] + ux * 4 * i - ux * 2, s[1] + uy * 4 * i - uy * 2
        for side in (1, -1):
            px, py = cx - uy * 1.2 * side, cy + ux * 1.2 * side
            if not near_gnd(px, py, 2.5) and ok(px, py):
                add(px, py, 'bus/RGB lane')
# 3) edge fence: 1.2 mm inside the board outline (outline = GND plane fill hull of the board rectangle)
W, H = 164.0, 99.0
frame = box(0, 0, W, H).buffer(-3.0).buffer(3.0 - 1.2, join_style=1).exterior   # rounded rectangle 1.2 mm inside
along(frame, 3.0, 'edge fence', rmax=0.6, free=2.2)
# +5V island split edges (In2): 1.2 mm outside the island outline, 3 mm pitch
for g in (list(P5.geoms) if hasattr(P5, 'geoms') else [P5]):
    if g.is_empty: continue
    along(g.buffer(1.2, join_style=1).exterior, 3.0, 'split fence', rmax=0.6, free=2.2)
# 4) islands: every outer GND fill piece without a GND via / GND pad gets vias (one per 25 mm2, at least one)
for lay, U in (('F.Cu', GF), ('B.Cu', GB)):
    for g in (list(U.geoms) if hasattr(U, 'geoms') else [U]):
        has = any(g.contains(Point(x, y)) for x, y in gndv)
        if has: continue
        inner = g.buffer(-(RV + 0.3))
        if inner.is_empty: continue
        pts = []
        c = inner.representative_point(); pts.append((c.x, c.y))
        minx, miny, maxx, maxy = inner.bounds
        yy = miny
        while yy <= maxy:
            xx = minx
            while xx <= maxx:
                if inner.contains(Point(xx, yy)): pts.append((xx, yy))
                xx += 1.0
            yy += 1.0
        for (x, y) in pts:
            if ok(x, y):
                add(x, y, 'island ' + lay); break
# 5) grid 4.5 mm
pitch = 4.5
y = 1.5
while y < H:
    x = 1.5
    while x < W:
        if not near_gnd(x, y, 2.5):
            try_around(x, y, 'grid', rmax=1.5, need_free=2.0)
        x += pitch
    y += pitch
from collections import Counter
print("placed", len(placed), Counter(k for _, _, k in placed))
print("signal vias with a return via:", ret_ok, "missing:", ret_miss)
print("rejections", rej)
json.dump(dict(vias=placed, ret_missing=ret_miss), open(sys.argv[2], 'w'))
