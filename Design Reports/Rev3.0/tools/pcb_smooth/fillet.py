"""Task 4: replace every bend between two straight track segments (exactly two track items of one net on one layer
meeting at a point, no via / pad / third item there) by a tangent PCB_ARC.

Radius: as large as the segments allow (a segment shared by two corners is split in proportion to their demand,
anchors of other items lying on a segment body are never trimmed away), capped at RCAP(w), target >= RMIN(w).
Corners whose largest possible radius is below RMIN keep that radius if >= RFLOOR (0.2 mm, fine-pitch escapes),
otherwise they stay sharp and are listed.  A JSON of per-corner radius caps in mm (written by the DRC loop) shrinks
individual corners (0 = keep sharp).
Usage: fillet.py in.kicad_pcb out.kicad_pcb corners.json [scale.json]
"""
import sys, json, math, pcbnew
from collections import Counter
from common import *

RFLOOR = 0.2
MAINS_NECK_R = 2.5
MAINS_NETS = {'LINE', 'LINE_FUSED', 'LINE_FILT', 'Net-(Q1-A1)', 'Net-(Q1-A2)', 'PSU_L', 'NEUT'}


def RMIN(w):
    return 2.5 if w >= 2.4 else max(2 * w, 0.3)


def RCAP(w):
    return min(max(8 * w, 1.5), 6.0)


b = pcbnew.LoadBoard(sys.argv[1])
scale = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
KEEP = []
SARCS = []


def key(net, lay, p):
    return "%s|%d|%.3f|%.3f" % (net, lay, p[0], p[1])


def kp(p):
    return (round(p[0], 4), round(p[1], 4))


SHORT = 0.35   # a segment shorter than this between two same-sense bends is folded into one compound corner


def premerge():
    """fold short chamfer segments (e.g. 0.007 mm or 0.15 mm 45-degree pieces) into a virtual corner so the two bends
    become one arc; only where both joints are plain two-item joints and the outer segments are long enough"""
    segs = [t for t in b.Tracks() if t.GetClass() == 'PCB_TRACK']
    vpts = {(v.GetNetCode(), kp(L(v.GetPosition()))) for v in b.Tracks() if v.GetClass() == 'PCB_VIA'}
    pl = [(p, p.GetNetCode()) for fp in b.GetFootprints() for p in fp.Pads()]
    ends = {}
    for t in segs:
        for p in (L(t.GetStart()), L(t.GetEnd())):
            ends.setdefault((t.GetNetCode(), t.GetLayer(), kp(p)), []).append(t)
    done = set(); merged = []
    for s_ in segs:
        a, e = L(s_.GetStart()), L(s_.GetEnd())
        ln = math.hypot(e[0] - a[0], e[1] - a[1])
        if ln >= SHORT or id(s_) in done:
            continue
        n, lay = s_.GetNetCode(), s_.GetLayer()
        nb = []
        for p in (a, e):
            its = ends.get((n, lay, kp(p)), [])
            if len(its) != 2 or (n, kp(p)) in vpts or any(nn == n and pd.IsOnLayer(lay) and pd.HitTest(V(*p)) for pd, nn in pl):
                nb = None; break
            o = its[0] if its[1] is s_ else its[1]
            if id(o) in done or o.GetClass() != 'PCB_TRACK':
                nb = None; break
            nb.append(o)
        if not nb or nb[0] is nb[1]:
            continue
        A, B = nb
        def farpt(t, p):
            s0, e0 = L(t.GetStart()), L(t.GetEnd()); return e0 if kp(s0) == kp(p) else s0
        fa, fb = farpt(A, a), farpt(B, e)
        da = (a[0] - fa[0], a[1] - fa[1]); db = (e[0] - fb[0], e[1] - fb[1])
        cr = da[0] * db[1] - da[1] * db[0]
        # same sense: cross products of consecutive directions have the same sign
        ds = (e[0] - a[0], e[1] - a[1])
        c1 = da[0] * ds[1] - da[1] * ds[0]; c2 = ds[0] * (-db[1]) - ds[1] * (-db[0])
        if c1 * c2 <= 0:
            # opposite senses: a jog between two parallel runs -> straighten (tiny offset) or an S-curve of two arcs
            la0, lb0 = math.hypot(*da), math.hypot(*db)
            ua = (da[0] / la0, da[1] / la0); ub = (-db[0] / lb0, -db[1] / lb0)
            if abs(ua[0] * ub[1] - ua[1] * ub[0]) > 0.01 or ua[0] * ub[0] + ua[1] * ub[1] < 0.99:
                continue
            nrm = (-ua[1], ua[0])
            h = (e[0] - a[0]) * nrm[0] + (e[1] - a[1]) * nrm[1]
            sl = (e[0] - a[0]) * ua[0] + (e[1] - a[1]) * ua[1]
            if h < 0:
                nrm = (-nrm[0], -nrm[1]); h = -h
            if h < 0.02:
                for t, p in ((B, e),):
                    if kp(L(t.GetStart())) == kp(p): t.SetStart(V(*a))
                    else: t.SetEnd(V(*a))
                b.Remove(s_); KEEP.append(s_)
                done.update({id(s_), id(A), id(B)})
                merged.append((s_.GetNetname(), a, round(ln, 3), 'straightened'))
                continue
            w = mm(s_.GetWidth())
            # room on A / B: half of the run if its far end is a plain corner, else all but 0.05 mm
            def room(t, fp_, l0):
                its = ends.get((n, lay, kp(fp_)), [])
                return l0 / 2 if len(its) == 2 and all(i.GetClass() == 'PCB_TRACK' for i in its) else l0 - 0.05
            ra, rb = room(A, fa, la0), room(B, fb, lb0)
            best = None
            R = RCAP(w)
            while R >= RFLOOR:
                if 2 * R > h:
                    th = math.acos(1 - h / (2 * R))
                    Ls = 2 * R * math.sin(th)
                    d = (Ls - sl) / 2
                    if d >= 0 and d <= ra and d <= rb:
                        best = (R, th, d); break
                R *= 0.9
            if best is None:
                continue
            R, th, d = best
            Q1 = (a[0] - ua[0] * d, a[1] - ua[1] * d)
            Q2 = (e[0] + ua[0] * d, e[1] + ua[1] * d)
            C1 = (Q1[0] + nrm[0] * R, Q1[1] + nrm[1] * R)
            C2 = (Q2[0] - nrm[0] * R, Q2[1] - nrm[1] * R)
            M = ((Q1[0] + Q2[0]) / 2, (Q1[1] + Q2[1]) / 2)
            m1 = (C1[0] - nrm[0] * R * math.cos(th / 2) + ua[0] * R * math.sin(th / 2),
                  C1[1] - nrm[1] * R * math.cos(th / 2) + ua[1] * R * math.sin(th / 2))
            m2 = (C2[0] + nrm[0] * R * math.cos(th / 2) - ua[0] * R * math.sin(th / 2),
                  C2[1] + nrm[1] * R * math.cos(th / 2) - ua[1] * R * math.sin(th / 2))
            for t, p, q in ((A, a, Q1), (B, e, Q2)):
                if kp(L(t.GetStart())) == kp(p): t.SetStart(V(*q))
                else: t.SetEnd(V(*q))
            for (p0, pm, p1) in ((Q1, m1, M), (M, m2, Q2)):
                r = pcbnew.PCB_ARC(b); r.SetStart(V(*p0)); r.SetMid(V(*pm)); r.SetEnd(V(*p1))
                r.SetWidth(s_.GetWidth()); r.SetLayer(lay); r.SetNetCode(n); b.Add(r); KEEP.append(r); SARCS.append(r)
            b.Remove(s_); KEEP.append(s_)
            done.update({id(s_), id(A), id(B)})
            merged.append((s_.GetNetname(), M, round(ln, 3), 'S-curve R %.2f' % R))
            continue
        if abs(cr) < 1e-9:
            continue
        # intersection of line fa->a and fb->e
        tpar = ((fb[0] - fa[0]) * db[1] - (fb[1] - fa[1]) * db[0]) / cr
        X = (fa[0] + da[0] * tpar, fa[1] + da[1] * tpar)
        ea, eb = math.hypot(X[0] - a[0], X[1] - a[1]), math.hypot(X[0] - e[0], X[1] - e[1])
        la, lb = math.hypot(X[0] - fa[0], X[1] - fa[1]), math.hypot(X[0] - fb[0], X[1] - fb[1])
        if ea > 0.5 or eb > 0.5 or la < 3 * ea + 0.2 or lb < 3 * eb + 0.2:
            continue
        for t, p in ((A, a), (B, e)):
            if kp(L(t.GetStart())) == kp(p): t.SetStart(V(*X))
            else: t.SetEnd(V(*X))
        b.Remove(s_); KEEP.append(s_)
        done.update({id(s_), id(A), id(B)})
        merged.append((s_.GetNetname(), X, round(ln, 3), max(ea, eb)))
    return merged


merged = premerge()
segs = [t for t in b.Tracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in b.Tracks() if t.GetClass() == 'PCB_VIA']
arcs0 = [t for t in b.Tracks() if t.GetClass() == 'PCB_ARC']
ends = {}
for t in segs + arcs0:
    for p in (L(t.GetStart()), L(t.GetEnd())):
        ends.setdefault((t.GetNetCode(), t.GetLayer(), kp(p)), []).append(t)
viapts = {(v.GetNetCode(), kp(L(v.GetPosition()))) for v in vias}
pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
padinfo = [(p, p.GetNetCode(), L(p.GetPosition())) for p in pads]


def pad_at(net, lay, p):
    for pd, n, _ in padinfo:
        if n == net and pd.IsOnLayer(lay) and pd.HitTest(V(*p)):
            return True
    return False


ends_by_nl = {}
for (n, lay, p) in ends:
    ends_by_nl.setdefault((n, lay), []).append(p)


def body_anchors(t):
    """distances along t (from its start) of other items' anchors lying on t's body"""
    s, e = L(t.GetStart()), L(t.GetEnd())
    n, lay, w = t.GetNetCode(), t.GetLayer(), mm(t.GetWidth())
    dx, dy = e[0] - s[0], e[1] - s[1]
    ln = math.hypot(dx, dy)
    out = []
    if ln < 1e-9:
        return out
    ux, uy = dx / ln, dy / ln
    cand = list(ends_by_nl.get((n, lay), [])) + [q for (nn, q) in viapts if nn == n]
    cand += [q for pd, nn, q in padinfo if nn == n and pd.IsOnLayer(lay)]
    for q in cand:
        rx, ry = q[0] - s[0], q[1] - s[1]
        a = rx * ux + ry * uy
        d = abs(-rx * uy + ry * ux)
        if 1e-3 < a < ln - 1e-3 and d <= w / 2 + 1e-3:
            out.append(a)
    return out


corners = []
for (n, lay, p), items in ends.items():
    if len(items) != 2 or any(it.GetClass() != 'PCB_TRACK' for it in items):
        continue
    if (n, p) in viapts:
        continue
    t1, t2 = items

    def far(t):
        s, e = L(t.GetStart()), L(t.GetEnd())
        return e if kp(s) == p else s
    f1, f2 = far(t1), far(t2)
    v1 = (f1[0] - p[0], f1[1] - p[1])
    v2 = (f2[0] - p[0], f2[1] - p[1])
    l1, l2 = math.hypot(*v1), math.hypot(*v2)
    if l1 < 1e-6 or l2 < 1e-6:
        continue
    cosint = (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)
    interior = math.degrees(math.acos(max(-1, min(1, cosint))))
    if interior > 179.5:
        continue
        # a neck corner takes the narrower width (the arc must not come closer to the neighbouring pins than the neck did);
    # on the mains trunks its radius is capped at 2.5 mm (MAINS_NECK_R) so the neck grows by only R*tan(phi/2)
    wsel = min
    corners.append(dict(p=p, n=n, lay=lay, t=[t1, t2], far=[f1, f2], len=[l1, l2], w=mm(wsel(t1.GetWidth(), t2.GetWidth())),
                        phi=math.radians(180 - interior), interior=interior, onpad=pad_at(n, lay, p),
                        neck=abs(t1.GetWidth() - t2.GetWidth()) > 1000,
                        net=t1.GetNetname()))

byseg = {}
for i, c in enumerate(corners):
    for j in (0, 1):
        byseg.setdefault(id(c['t'][j]), []).append((i, j))
segobj = {id(t): t for t in segs}
for c in corners:
    c['key'] = key(c['net'], c['lay'], c['p'])
    c['tan'] = math.tan(c['phi'] / 2)
    cap = MAINS_NECK_R if (c.get('neck') and c['net'] in MAINS_NETS) else 99.0
    c['want'] = 0 if c['onpad'] else min(RCAP(c['w']), scale.get(c['key'], 99.0), cap) * c['tan']
tmax = {}
for sid, lst in byseg.items():
    t = segobj[sid]
    s, e = L(t.GetStart()), L(t.GetEnd())
    ln = math.hypot(e[0] - s[0], e[1] - s[1])
    anch = body_anchors(t)
    for (i, j) in lst:
        c = corners[i]
        atstart = kp(s) == c['p']
        a = [x if atstart else ln - x for x in anch]
        lim = min(a) - 0.05 if a else ln
        if len(lst) == 2:
            o = corners[lst[1][0]] if lst[0][0] == i else corners[lst[0][0]]
            tot = c['want'] + o['want']
            share = c['want'] if tot <= ln else (ln * c['want'] / tot if tot > 0 else 0)
            lim = min(lim, share)
        tmax[(i, j)] = max(lim, 0)

report = dict(filleted=[], small=[], sharp=[])
newsegs = {}
for i, c in enumerate(corners):
    if c['onpad']:
        report['sharp'].append(dict(key=c['key'], why='on pad', w=c['w']))
        continue
    t = min(c['want'], tmax[(i, 0)], tmax[(i, 1)])
    R = t / c['tan']
    if R < RFLOOR - 1e-6:
        report['sharp'].append(dict(key=c['key'], why='R max %.3f' % R, w=c['w']))
        continue
    if R < RMIN(c['w']) - 1e-6:
        report['small'].append(dict(key=c['key'], R=round(R, 3), rmin=RMIN(c['w']), w=c['w']))
    p = c['p']
    u = [((c['far'][j][0] - p[0]) / c['len'][j], (c['far'][j][1] - p[1]) / c['len'][j]) for j in (0, 1)]
    a = (p[0] + u[0][0] * t, p[1] + u[0][1] * t)
    bb = (p[0] + u[1][0] * t, p[1] + u[1][1] * t)
    # a run eaten completely up to a non-corner end: end exactly on that end point
    if abs(t - c['len'][0]) < 0.005: a = c['far'][0]
    if abs(t - c['len'][1]) < 0.005: bb = c['far'][1]
    bis = (u[0][0] + u[1][0], u[0][1] + u[1][1])
    bl = math.hypot(*bis)
    bis = (bis[0] / bl, bis[1] / bl)
    dc = R / math.cos(c['phi'] / 2)
    cen = (p[0] + bis[0] * dc, p[1] + bis[1] * dc)
    mid = (cen[0] - bis[0] * R, cen[1] - bis[1] * R)
    c['arc'] = (a, mid, bb)
    c['R'] = R
    for j, q in ((0, a), (1, bb)):
        tt = c['t'][j]
        ns = newsegs.setdefault(id(tt), [L(tt.GetStart()), L(tt.GetEnd())])
        if kp(L(tt.GetStart())) == p:
            ns[0] = q
        else:
            ns[1] = q
    report['filleted'].append(dict(key=c['key'], R=round(R, 3), w=c['w'], interior=round(c['interior'], 1)))

umap = {}
for c in corners:
    if 'arc' in c:
        for tt in c['t']:
            umap.setdefault(tt.m_Uuid.AsString(), []).append(c['key'])
removed = 0
for sid, (s, e) in newsegs.items():
    t = segobj[sid]
    if math.hypot(e[0] - s[0], e[1] - s[1]) < 0.001:
        b.Remove(t)
        KEEP.append(t)
        removed += 1
    else:
        t.SetStart(V(*s))
        t.SetEnd(V(*e))
# a segment eaten completely by its two corners: both arcs must end on exactly the same nanometre point
snap = []
for sid, (s, e) in newsegs.items():
    if math.hypot(e[0] - s[0], e[1] - s[1]) < 0.001:
        snap.append((s, ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2)))
        snap.append((e, ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2)))


def snapped(p):
    for o, n in snap:
        if abs(o[0] - p[0]) < 1e-9 and abs(o[1] - p[1]) < 1e-9:
            return n
    return p


for c in corners:
    if 'arc' not in c:
        continue
    a, m, q = c['arc']
    a, q = snapped(a), snapped(q)
    r = pcbnew.PCB_ARC(b)
    r.SetStart(V(*a)); r.SetMid(V(*m)); r.SetEnd(V(*q))
    r.SetWidth(pcbnew.FromMM(c['w'])); r.SetLayer(c['lay']); r.SetNetCode(c['n'])
    b.Add(r)
    KEEP.append(r)
    umap.setdefault(r.m_Uuid.AsString(), []).append(c['key'])
report['uuid'] = umap
report['merged'] = [list(map(str, m)) for m in merged]
for r in SARCS:
    umap.setdefault(r.m_Uuid.AsString(), []).append('S|' + r.GetNetname())
report['necks'] = [c['key'] for c in corners if c.get('neck') and 'arc' in c]
report['removed_segments'] = removed
json.dump(report, open(sys.argv[3], 'w'))
pcbnew.SaveBoard(sys.argv[2], b)
print("compound corners", len(merged), "neck corners", len(report['necks']), "corners", len(corners), "filleted", len(report['filleted']), "below target", len(report['small']),
      "sharp", len(report['sharp']), "segments removed", removed)
print(Counter(s['why'][:5] for s in report['sharp']))
