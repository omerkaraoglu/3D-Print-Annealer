"""Teardrops in KiCad's own format (pcbnew's TEARDROP_MANAGER is not exposed to python, and ZONE.SetTeardropAreaType
cannot be called with its enum, so the zones are computed here and written as
`(zone ... (name "$teardrop_padvia$") (priority 30000) (attr (teardrop (type padvia|track_end))) ...)`).

Geometry = KiCad's board defaults (also kept in the .kicad_pro): length = 0.5 x pad/via size (max 1.0 mm) measured from
the pad edge along the track, width at the pad = 1.0 x size (max 2.0 mm, reduced to what fits inside the pad), filter:
only tracks narrower than 0.9 x size; curved flanks (cubic Bezier tangent to the track edge and to the track axis at
the pad).  Not generated: U10 / U20 pads and anything in the u10_escape / u20_escape rule areas (0.13 mm fine-pitch
escapes), pads / vias sitting in a same-net pour on that layer (KiCad's "prefer zone connections"), tracks whose straight
part is too short, arcs.  Track-to-track (track_end): collinear joints of two straight segments whose widths differ by
> 10 %, flare from the narrow track into the wide one.
A skip list (JSON list of "ref.pad|layer|x|y" / "via|..." keys from the DRC loop) removes or shrinks individual drops.
Usage: teardrops.py in.kicad_pcb out.kicad_pcb report.json [skip.json]"""
import sys, json, math, uuid, pcbnew
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
skip = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
LR, LMAX, WR, WMAX, FILT = 0.5, 1.0, 1.0, 2.0, 0.9
NSEG = 8
EXCL_FP = {'U10', 'U20'}
areas = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() in ('u10_escape', 'u20_escape')]


keepouts = [z for z in b.Zones() if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowZoneFills())]


def in_keepout(poly, layer):
    return any(z.IsOnLayer(layer) and any(z.Outline().Contains(V(*q)) for q in poly) for z in keepouts)


def in_escape(p):
    return any(z.Outline().Contains(V(*p)) for z in areas)


fills = {}
for z in b.Zones():
    if z.GetIsRuleArea() or not z.GetNetname() or z.IsTeardropArea():
        continue
    for lay in z.GetLayerSet().Seq():
        fills.setdefault((z.GetNetCode(), lay), []).append(z.GetFilledPolysList(lay))


def in_pour(net, lay, p):
    return any(f.Contains(V(*p)) for f in fills.get((net, lay), []))


def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(1, n):
        t = i / n
        a = (1 - t) ** 3; bb = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
        out.append((a * p0[0] + bb * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + bb * p1[1] + c * p2[1] + d * p3[1]))
    return out


def drop_poly(C, u, d_edge, L, w, W):
    """C pad/joint centre, u unit direction along the track (away from the pad), d_edge distance C -> pad edge,
    L teardrop length beyond the edge, w track width, W width at the pad (points P on the line through C)."""
    n = (-u[1], u[0])
    da = d_edge + L
    T1 = (C[0] + u[0] * da + n[0] * w / 2, C[1] + u[1] * da + n[1] * w / 2)
    T2 = (C[0] + u[0] * da - n[0] * w / 2, C[1] + u[1] * da - n[1] * w / 2)
    P1 = (C[0] + n[0] * W / 2, C[1] + n[1] * W / 2)
    P2 = (C[0] - n[0] * W / 2, C[1] - n[1] * W / 2)
    k = da / 2
    c1 = (T1[0] - u[0] * k, T1[1] - u[1] * k); c2 = (P1[0] + u[0] * k * 0.8, P1[1] + u[1] * k * 0.8)
    c3 = (P2[0] + u[0] * k * 0.8, P2[1] + u[1] * k * 0.8); c4 = (T2[0] - u[0] * k, T2[1] - u[1] * k)
    return [T1] + bez(T1, c1, c2, P1, NSEG) + [P1, P2] + bez(P2, c3, c4, T2, NSEG) + [T2]


def edge_dist(hit, C, u, maxd):
    lo, hi = 0.0, maxd
    if hit((C[0] + u[0] * hi, C[1] + u[1] * hi)):
        return None
    for _ in range(30):
        m = (lo + hi) / 2
        if hit((C[0] + u[0] * m, C[1] + u[1] * m)): lo = m
        else: hi = m
    return lo


tracks = [t for t in b.Tracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in b.Tracks() if t.GetClass() == 'PCB_VIA']
pads = [(fp.GetReference(), p) for fp in b.GetFootprints() for p in fp.Pads()]
drops = []   # dict(key, net, netname, layer, type, poly, owner)
stats = dict(padvia=0, track_end=0, skipped={})


def sk(why):
    stats['skipped'][why] = stats['skipped'].get(why, 0) + 1


def owner_size(o):
    if o[0] == 'via':
        return mm(o[1].GetWidth(pcbnew.F_Cu))
    p = o[1]
    s = p.GetSize(pcbnew.F_Cu)
    return min(mm(s.x), mm(s.y))


for t in tracks:
    lay, net = t.GetLayer(), t.GetNetCode()
    w = mm(t.GetWidth())
    s, e = L(t.GetStart()), L(t.GetEnd())
    ln = math.hypot(e[0] - s[0], e[1] - s[1])
    if ln < 1e-6:
        continue
    for C, F in ((s, e), (e, s)):
        owner = None
        for v in vias:
            if v.GetNetCode() == net and close(L(v.GetPosition()), C, 0.01):
                owner = ('via', v); break
        if owner is None:
            for ref, p in pads:
                if p.GetNetCode() == net and p.IsOnLayer(lay) and close(L(p.GetPosition()), C, 0.01):
                    owner = (ref, p); break
        if owner is None:
            continue
        if owner[0] in EXCL_FP or in_escape(C):
            sk('fine-pitch escape'); continue
        if in_pour(net, lay, C):
            sk('in same-net pour'); continue
        D = owner_size(owner)
        if w >= FILT * D:
            sk('track >= 0.9 x size'); continue
        u = ((F[0] - C[0]) / ln, (F[1] - C[1]) / ln)
        key = "%s|%d|%.3f|%.3f|%.3f|%.3f" % (owner[0] if owner[0] == 'via' else owner[0] + '.' + owner[1].GetNumber(), lay, C[0], C[1], u[0], u[1])
        f = skip.get(key, 1.0)
        if f <= 0:
            sk('removed by DRC loop'); continue
        if owner[0] == 'via':
            r = D / 2; hit = lambda q: math.hypot(q[0] - C[0], q[1] - C[1]) <= r
        else:
            pd = owner[1]; hit = lambda q, pd=pd: pd.HitTest(V(*q))
        dE = edge_dist(hit, C, u, D * 3)
        if dE is None:
            sk('pad edge not found'); continue
        L_ = min(LR * D, LMAX) * f
        if dE + L_ > ln - 0.02:
            L_ = ln - 0.02 - dE
            if L_ < 0.5 * min(LR * D, LMAX) * f:
                sk('straight part too short'); continue
        W = min(WR * D, WMAX) * (1.0 if f >= 1 else 0.9)
        n_ = (-u[1], u[0])
        while W > w * 1.1 and not (hit((C[0] + n_[0] * W / 2 * 0.98, C[1] + n_[1] * W / 2 * 0.98)) and hit((C[0] - n_[0] * W / 2 * 0.98, C[1] - n_[1] * W / 2 * 0.98))):
            W *= 0.95
        if W <= w * 1.1:
            sk('no room in pad'); continue
        poly = drop_poly(C, u, dE, L_, w, W)
        if in_keepout(poly, lay):
            sk('in keep-out area'); continue
        drops.append(dict(key=key, net=t.GetNetname(), layer=b.GetLayerName(lay), type='padvia',
                          poly=poly, owner=owner[0], L=round(L_, 3), W=round(W, 3), w=w))
        stats['padvia'] += 1

# track-to-track: collinear joints of two straight segments with different widths
ends = {}
for t in tracks:
    for p in (L(t.GetStart()), L(t.GetEnd())):
        ends.setdefault((t.GetNetCode(), t.GetLayer(), (round(p[0], 4), round(p[1], 4))), []).append(t)
arcends = {(a.GetNetCode(), a.GetLayer(), (round(L(q)[0], 4), round(L(q)[1], 4))) for a in b.Tracks() if a.GetClass() == 'PCB_ARC' for q in (a.GetStart(), a.GetEnd())}
for (net, lay, C), its in ends.items():
    if len(its) != 2 or (net, lay, C) in arcends:
        continue
    t1, t2 = its
    w1, w2 = mm(t1.GetWidth()), mm(t2.GetWidth())
    if abs(w1 - w2) < 0.1 * max(w1, w2):
        continue
    nar, wid = (t1, t2) if w1 < w2 else (t2, t1)
    def far(t):
        s, e = L(t.GetStart()), L(t.GetEnd()); return e if close(s, C, 1e-4) else s
    fn, fw = far(nar), far(wid)
    ln = math.hypot(fn[0] - C[0], fn[1] - C[1]); lw = math.hypot(fw[0] - C[0], fw[1] - C[1])
    u = ((fn[0] - C[0]) / ln, (fn[1] - C[1]) / ln); uw = ((fw[0] - C[0]) / lw, (fw[1] - C[1]) / lw)
    if u[0] * uw[0] + u[1] * uw[1] > -0.999:
        continue   # not collinear
    if any(close(L(v.GetPosition()), C, 0.01) for v in vias) or any(p.HitTest(V(*C)) and p.IsOnLayer(lay) for _, p in pads):
        continue
    Dw = max(w1, w2); w = min(w1, w2)
    key = "trk|%d|%.3f|%.3f" % (lay, C[0], C[1])
    f = skip.get(key, 1.0)
    if f <= 0 or w >= FILT * Dw:
        continue
    L_ = min(LR * Dw, LMAX) * f
    if L_ > ln - 0.02:
        continue
    W = min(WR * Dw, WMAX)
    drops.append(dict(key=key, net=nar.GetNetname(), layer=b.GetLayerName(lay), type='track_end',
                      poly=drop_poly(C, u, 0.0, L_, w, W), owner='track', L=round(L_, 3), W=round(W, 3), w=w))
    stats['track_end'] += 1

# per-item teardrop parameters on the pads / vias that got one (KiCad keeps them on the item)
owners = set(d['key'].split('|')[0] for d in drops if d['type'] == 'padvia')
for ref, p in pads:
    if ref + '.' + p.GetNumber() in owners:
        p.SetTeardropsEnabled(True); p.SetTeardropCurved(True)
via_pts = set((d['key'].split('|')[2], d['key'].split('|')[3]) for d in drops if d['owner'] == 'via')
for v in vias:
    q = L(v.GetPosition())
    if ("%.3f" % q[0], "%.3f" % q[1]) in via_pts:
        v.SetTeardropsEnabled(True); v.SetTeardropCurved(True)
pcbnew.SaveBoard(sys.argv[2], b)

# append the teardrop zones to the saved file (KiCad 10 s-expression)
def esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')
txt = []
for d in drops:
    pts = " ".join("(xy %.6f %.6f)" % (x + O, y + O) for x, y in d['poly'])
    txt.append('\t(zone\n\t\t(net "%s")\n\t\t(layer "%s")\n\t\t(uuid "%s")\n\t\t(name "$teardrop_%s$")\n'
               '\t\t(hatch full 0.1)\n\t\t(priority 30000)\n\t\t(attr\n\t\t\t(teardrop\n\t\t\t\t(type %s)\n\t\t\t)\n\t\t)\n'
               '\t\t(connect_pads yes\n\t\t\t(clearance 0)\n\t\t)\n\t\t(min_thickness 0.0254)\n\t\t(filled_areas_thickness no)\n'
               '\t\t(fill yes\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.5)\n\t\t\t(island_removal_mode 1)\n'
               '\t\t\t(island_area_min 10)\n\t\t)\n\t\t(polygon\n\t\t\t(pts\n\t\t\t\t%s\n\t\t\t)\n\t\t)\n\t)\n'
               % (esc(d['net']), d['layer'], uuid.uuid4(), 'padvia' if d['type'] == 'padvia' else 'track',
                  'padvia' if d['type'] == 'padvia' else 'track_end', pts))
s = open(sys.argv[2], encoding='utf-8').read().rstrip()
assert s.endswith(')')
s = s[:-1].rstrip() + '\n' + ''.join(txt) + ')\n'
open(sys.argv[2], 'w', encoding='utf-8', newline='\n').write(s)
json.dump(dict(stats=stats, drops=[{k: v for k, v in d.items() if k != 'poly'} for d in drops]), open(sys.argv[3], 'w'))
print("teardrops padvia %d track_end %d" % (stats['padvia'], stats['track_end']), stats['skipped'])
