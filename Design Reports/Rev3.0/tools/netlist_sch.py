"""Extract a flat netlist from a single KiCad schematic sheet (wires, junctions, labels, power symbols, pins)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import *

def r2(v):
    return round(float(v), 2)

def lib_pins(libsym):
    """Return list of (name, number, x, y, angle, length) for a lib symbol incl. sub-units."""
    pins = []
    def walk(node):
        for p in find(node, 'pin'):
            at = first(p, 'at'); ln = first(p, 'length')
            name = first(p, 'name')[1]; num = first(p, 'number')[1]
            pins.append((name, num, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, float(ln[1])))
        for s in find(node, 'symbol'):
            walk(s)
    walk(libsym)
    return pins

def transform(px, py, sym):
    at = first(sym, 'at'); sx, sy = float(at[1]), float(at[2])
    rot = float(at[3]) if len(at) > 3 else 0.0
    mirror = first(sym, 'mirror')
    x, y = px, py
    if mirror:
        if mirror[1] == 'x': y = -y
        elif mirror[1] == 'y': x = -x
    a = math.radians(rot)
    # KiCad schematic: y axis points down; symbol coords y up -> flip
    xr = x * math.cos(a) + y * math.sin(a)
    yr = -x * math.sin(a) + y * math.cos(a)
    return r2(sx + xr), r2(sy - yr)

def main(path):
    root = parse(open(path, encoding='utf-8').read())
    libs = {s[1]: s for s in find(first(root, 'lib_symbols'), 'symbol')}
    # nodes: coordinates -> set; edges from wires
    parent = {}
    def findp(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        parent[findp(a)] = findp(b)
    pts_on_wires = []
    wires = []
    for w in find(root, 'wire'):
        pts = first(w, 'pts'); xy = find(pts, 'xy')
        a = (r2(xy[0][1]), r2(xy[0][2])); b = (r2(xy[1][1]), r2(xy[1][2]))
        wires.append((a, b)); union(a, b)
    def on_segment(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > 0.05: return False
        return min(x1, x2) - 0.05 <= x <= max(x1, x2) + 0.05 and min(y1, y2) - 0.05 <= y <= max(y1, y2) + 0.05
    def attach(p):
        # connect point p to any wire it lies on (T-junctions)
        for a, b in wires:
            if on_segment(p, a, b):
                union(p, a)
    for j in find(root, 'junction'):
        at = first(j, 'at'); attach((r2(at[1]), r2(at[2])))
    names = {}   # point -> label name
    for l in find(root, 'label') + find(root, 'global_label') + find(root, 'hierarchical_label'):
        at = first(l, 'at'); p = (r2(at[1]), r2(at[2])); attach(p); names.setdefault(p, []).append(l[1])
    pinpts = {}  # point -> list of "REF.pin(name)"
    for s in find(root, 'symbol'):
        ref = prop(s, 'Reference'); lid = first(s, 'lib_id')[1]
        lib = libs.get(lid)
        if not lib: continue
        unit = first(s, 'unit'); unit = int(unit[1]) if unit else 1
        for (name, num, px, py, ang, ln) in lib_pins(lib):
            p = transform(px, py, s)
            attach(p)
            if ref.startswith('#PWR'):
                names.setdefault(p, []).append(prop(s, 'Value'))
            else:
                pinpts.setdefault(p, []).append(f"{ref}.{num}({name})")
    nets = {}
    for p in set(list(parent.keys()) + list(pinpts.keys()) + list(names.keys())):
        nets.setdefault(findp(p), set()).add(p)
    out = []
    for rootp, pts in nets.items():
        nm = sorted({n for p in pts for n in names.get(p, [])})
        pins = sorted({x for p in pts for x in pinpts.get(p, [])})
        if not pins and not nm: continue
        out.append((nm, pins))
    out.sort(key=lambda t: (t[0], t[1]))
    for nm, pins in out:
        print(f"{'/'.join(nm) or '(unnamed)':14} : {' '.join(pins)}")

if __name__ == '__main__':
    main(sys.argv[1])
