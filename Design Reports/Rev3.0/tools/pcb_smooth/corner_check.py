"""Task 4 checker: every point where exactly two track items (segment or arc) of one net meet on one layer; reports
the ones whose tangent directions are not collinear (a corner).  Points on a pad or a via, junctions of >= 3 items and
track ends are allowed and only counted.  Usage: corner_check.py board.kicad_pcb [tol_deg=0.5]"""
import sys, math, pcbnew
from collections import Counter
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
tol = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5


def kp(p):
    return (round(p[0], 4), round(p[1], 4))


def outdir(t, p):
    """unit direction leaving point p along item t"""
    s, e = L(t.GetStart()), L(t.GetEnd())
    if t.GetClass() == 'PCB_ARC':
        c = L(t.GetCenter())
        m = L(t.GetMid())
        r = (p[0] - c[0], p[1] - c[1])
        d1, d2 = (-r[1], r[0]), (r[1], -r[0])
        # choose the tangent that points towards the mid point
        pick = d1 if (d1[0] * (m[0] - p[0]) + d1[1] * (m[1] - p[1])) > 0 else d2
        n = math.hypot(*pick)
        return (pick[0] / n, pick[1] / n)
    q = e if kp(s) == kp(p) else s
    n = math.hypot(q[0] - p[0], q[1] - p[1])
    return ((q[0] - p[0]) / n, (q[1] - p[1]) / n) if n > 1e-9 else None


ends = {}
for t in b.Tracks():
    if t.GetClass() in ('PCB_TRACK', 'PCB_ARC'):
        for p in (L(t.GetStart()), L(t.GetEnd())):
            ends.setdefault((t.GetNetCode(), t.GetLayer(), kp(p)), []).append(t)
ends_nl = {}
for (n_, l_, p_) in ends:
    ends_nl.setdefault((n_, l_), []).append(p_)
vias = {(v.GetNetCode(), kp(L(v.GetPosition()))) for v in b.Tracks() if v.GetClass() == 'PCB_VIA'}
pads = [(p, p.GetNetCode()) for fp in b.GetFootprints() for p in fp.Pads()]
cnt = Counter()
bad = []
for (n, lay, p), its in ends.items():
    if len(its) != 2:
        cnt['junction>=3' if len(its) > 2 else 'end'] += 1
        continue
    d1, d2 = outdir(its[0], p), outdir(its[1], p)
    if d1 is None or d2 is None:
        cnt['zero-length'] += 1
        continue
    ang = math.degrees(math.acos(max(-1, min(1, d1[0] * d2[0] + d1[1] * d2[1]))))
    if ang >= 180 - tol:
        cnt['smooth'] += 1
        continue
    if (n, p) in vias:
        cnt['corner on via (allowed)'] += 1
        continue
    if any(nn == n and pd.IsOnLayer(lay) and pd.HitTest(V(*p)) for pd, nn in pads):
        cnt['corner on pad (allowed)'] += 1
        continue
    # another track of the net ends on one of the two items near this point (a T-junction drawn as end-on-body)
    w = max(mm(its[0].GetWidth()), mm(its[1].GetWidth()))
    if any(q != p and math.hypot(q[0] - p[0], q[1] - p[1]) < w for q in ends_nl.get((n, lay), [])):
        tee = [q for q in ends_nl[(n, lay)] if q != p and math.hypot(q[0] - p[0], q[1] - p[1]) < w
               and not any(it in ends[(n, lay, q)] for it in its)]
        if tee:
            cnt['T-junction (track end on body, allowed)'] += 1
            continue
    bad.append((its[0].GetNetname(), b.GetLayerName(lay), p, round(ang, 1), round(mm(its[0].GetWidth()), 2),
                round(mm(its[1].GetWidth()), 2)))
cls = Counter(t.GetClass() for t in b.Tracks())
print("items", dict(cls))
print(dict(cnt))
print("REMAINING CORNERS between two track items:", len(bad))
for x in bad:
    print("  %-40s %-5s (%.3f,%.3f) interior %.1f  w %.2f/%.2f" % (x[0][:40], x[1], x[2][0], x[2][1], x[3], x[4], x[5]))
