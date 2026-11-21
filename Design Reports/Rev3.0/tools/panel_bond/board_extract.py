"""Panel bond, step 1: read the Rev3.0 board (read only) and extract
- the 18 landing pads BP1..BP18 (centre, copper, bare opening, vias),
- every through-hole pad (position, net, drill, size, footprint side),
- the Cmts.User mains boundary,
into out/board_pads.json.  Coordinates: local mm = KiCad absolute - 20 mm (spec 12.12).

Nothing is written to the board.  Run:  python -X utf8 board_extract.py
"""
import json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
PCB = os.path.join(ROOT, 'KiCad', '3dFilamentDryer', '3dFilamentDryer.kicad_pcb')
PRO = os.path.join(ROOT, 'KiCad', '3dFilamentDryer', '3dFilamentDryer.kicad_pro')
OUT = os.path.join(HERE, 'out')
OFF = 20.0


def tokenize(s):
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|([()])|([^\s()"]+)', s):
        if m.group(1) is not None:
            yield ('s', m.group(1))
        elif m.group(2):
            yield (m.group(2), None)
        else:
            yield ('a', m.group(3))


def parse(s):
    stack = [[]]
    for kind, val in tokenize(s):
        if kind == '(':
            stack.append([])
        elif kind == ')':
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(val)
    return stack[0][0]


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def rot(x, y, deg):
    a = math.radians(deg)
    # KiCad: y down, rotation counter-clockwise on screen
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def main():
    os.makedirs(OUT, exist_ok=True)
    tree = parse(open(PCB, encoding='utf8').read())
    pro = json.load(open(PRO, encoding='utf8'))
    mains_nets = {p['pattern']: p['netclass'] for p in pro['net_settings'].get('netclass_patterns', [])
                  if p['netclass'] in ('Mains', 'MainsHeater')}
    pads, bps, smd_m = [], {}, []
    for fp in kids(tree, 'footprint'):
        lib = fp[1]
        at = kid(fp, 'at')
        fx, fy = float(at[1]), float(at[2])
        frot = float(at[3]) if len(at) > 3 else 0.0
        layer = kid(fp, 'layer')[1]
        ref = None
        for p in kids(fp, 'property'):
            if p[1] == 'Reference':
                ref = p[2]
        for pd in kids(fp, 'pad'):
            num, ptype, shape = pd[1], pd[2], pd[3]
            pat = kid(pd, 'at')
            px, py = float(pat[1]), float(pat[2])
            prot = float(pat[3]) if len(pat) > 3 else 0.0
            rx, ry = rot(px, py, frot)
            ax, ay = fx + rx, fy + ry
            size = kid(pd, 'size')
            sx, sy = float(size[1]), float(size[2])
            drill = kid(pd, 'drill')
            dr = None
            if drill is not None:
                vals = [v for v in drill[1:] if isinstance(v, str) and re.match(r'^[\d.]+$', v)]
                dr = [float(v) for v in vals] if vals else None
            net = kid(pd, 'net')
            netname = net[2] if net is not None and len(net) > 2 else (net[1] if net is not None and len(net) > 1 else '')
            layers = kid(pd, 'layers')
            rec = dict(ref=ref, lib=lib, num=num, type=ptype, shape=shape, x=round(ax - OFF, 4), y=round(ay - OFF, 4),
                       sx=sx, sy=sy, pad_rot=prot + frot, drill=dr, net=netname, side=layer,
                       layers=[l for l in layers[1:]] if layers else [])
            if ref and ref.startswith('BP') and lib.startswith('Rev3:LandingPad'):
                bps.setdefault(ref, dict(ref=ref, lib=lib, x=round(fx - OFF, 4), y=round(fy - OFF, 4), rot=frot, pads=[]))
                bps[ref]['pads'].append(rec)
            if ptype == 'smd' and mains_nets.get(netname):
                rec['mains_net'] = mains_nets.get(netname)
                smd_m.append(rec)
            if ptype == 'thru_hole':
                rec['mains_net'] = mains_nets.get(netname)
                pads.append(rec)
    # FPC connectors (top side): pad extents
    conn = {}
    for fp in kids(tree, 'footprint'):
        ref = [p[2] for p in kids(fp, 'property') if p[1] == 'Reference'][0]
        if ref in ('J10', 'J11'):
            at = kid(fp, 'at')
            xs, ys = [], []
            for pd in kids(fp, 'pad'):
                pa = kid(pd, 'at')
                rx, ry = rot(float(pa[1]), float(pa[2]), float(at[3]) if len(at) > 3 else 0.0)
                xs.append(float(at[1]) + rx - OFF); ys.append(float(at[2]) + ry - OFF)
            conn[ref] = dict(lib=fp[1], side=kid(fp, 'layer')[1], pads_x=[round(min(xs), 2), round(max(xs), 2)],
                             pads_y=[round(min(ys), 2), round(max(ys), 2)])
    # mains copper tracks on B.Cu (the side facing the panel)
    netnames = {}
    for n in kids(tree, 'net'):
        if len(n) > 2:
            netnames[n[1]] = n[2]
    tracks = []
    for seg in kids(tree, 'segment') + kids(tree, 'arc'):
        ly = kid(seg, 'layer')
        net = kid(seg, 'net')
        nn = net[1] if net is not None else ''
        nn = netnames.get(nn, nn)
        if ly and nn in mains_nets:
            pts = [kid(seg, 'start')] + ([kid(seg, 'mid')] if seg[0] == 'arc' else []) + [kid(seg, 'end')]
            tracks.append(dict(net=nn, layer=ly[1], w=float(kid(seg, 'width')[1]),
                               pts=[[float(p[1]) - OFF, float(p[2]) - OFF] for p in pts]))
    # mains boundary on Cmts.User (lines/polys)
    cm = []
    for g in kids(tree, 'gr_line') + kids(tree, 'gr_poly'):
        ly = kid(g, 'layer')
        if ly and ly[1] == 'Cmts.User':
            if g[0] == 'gr_line':
                s, e = kid(g, 'start'), kid(g, 'end')
                cm.append([[float(s[1]) - OFF, float(s[2]) - OFF], [float(e[1]) - OFF, float(e[2]) - OFF]])
            else:
                pts = kid(g, 'pts')
                xy = [[float(p[1]) - OFF, float(p[2]) - OFF] for p in kids(pts, 'xy')]
                cm.append(xy)
    json.dump(dict(source=os.path.relpath(PCB, ROOT), local_offset_mm=OFF, mains_net_patterns=mains_nets,
                   landing_pads=[bps[k] for k in sorted(bps, key=lambda r: int(r[2:]))],
                   tht_pads=pads, connectors=conn, mains_smd_pads=smd_m, mains_tracks_bcu=tracks, cmts_user=cm), open(os.path.join(OUT, 'board_pads.json'), 'w', encoding='utf8'), indent=1)
    print('B.Cu mains tracks', len(tracks), 'SMD mains pads on B.Cu',
          sum(1 for fp in kids(tree, 'footprint') for pd in kids(fp, 'pad') if pd[2] == 'smd'
              and kid(fp, 'layer')[1] == 'B.Cu' and kid(pd, 'net') is not None and kid(pd, 'net')[-1] in mains_nets))
    print('BP', len(bps), 'THT pads', len(pads), 'mains-net THT pads', sum(1 for p in pads if p['mains_net']), 'Cmts items', len(cm))
    for k in sorted(bps, key=lambda r: int(r[2:])):
        b = bps[k]
        print(k, b['x'], b['y'], b['rot'], [(p['num'], p['type'], p['shape'], p['sx'], p['sy'], p['net'], p['layers']) for p in b['pads']][:3])


if __name__ == '__main__':
    main()
