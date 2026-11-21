"""Stage 3 - where can RV3 (RV_Disc_D15.5mm_W5mm_P7.5mm, LINE_FUSED / NEUT) go with 2.5 mm branches, 2.5 mm to other
mains nets, >= 6.4 mm (+ half width) from the low-voltage side, no vias, with K1 at its new place?
Copper that is re-routed in stage 3 (old K1 pads, LINE_FUSED trunk below L40.2, the fan route beyond J4.1 and the
old coil feeds) is taken out. A site passes when (1) its courtyard overlaps no courtyard (K1 new, D6 planned),
(2) its pads keep 2.5 mm to other mains nets and 6.4 mm to the LV polygon, (3) on F.Cu or B.Cu a 2.5 mm track can
reach each pad from existing copper of its own net (grid BFS, 0.25 mm, obstacles = other-net copper grown by
2.5 + 1.25 mm, the LV polygon grown by 6.4 + 1.25 mm, courtyard-free is not required for tracks).
Usage: s3_rv3search.py geo.json K1cx K1yc"""
import json, sys, math
import numpy as np
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union
from shapely import prepared
G = json.load(open(sys.argv[1])); kx, ky = float(sys.argv[2]), float(sys.argv[3])
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "Net-(J4-Pin_1)", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "/Q1_A1", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)",
         "unconnected-(U5-NC-Pad5)", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
LGRP = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "Net-(PS1-AC/L)"}
LV = Polygon([(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
              (126.0, 54.8), (130.0, 55.5), (130.0, 40.0), (163.5, 40.0), (163.5, 98.5), (0.5, 98.5)])
def rerouted(net, g):
    b = g.bounds
    if net == "LINE_FUSED" and b[1] > 15.3 and b[0] > 50: return True
    if net == "Net-(J4-Pin_1)" and b[1] > 13.9: return True
    return False
    b = g.bounds
    if net in ("LINE_FUSED",) and b[1] > 16.5 and 60 < b[0] < 80: return True
    if net == "Net-(J4-Pin_1)" and b[1] > 14.0: return True
    if net == "unconnected-(K1-Pad4)": return True
    return False
cu = {"F.Cu": [], "B.Cu": []}
for s in G["segs"]:
    if s[6] not in cu: continue
    g = LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2)
    if not rerouted(s[5], g): cu[s[6]].append((g, s[5]))
for p in G["pads"]:
    if p["ref"] in ("K1", "RV3", "D6") or len(p["pts"]) < 3: continue
    for l in ("F.Cu", "B.Cu"):
        if l in p["layers"]: cu[l].append((Polygon(p["pts"]), p["net"]))
for v in G["vias"]:
    g = Point(v[0], v[1]).buffer(v[2] / 2)
    for l in cu: cu[l].append((g, v[3]))
# new K1 pads (rotated +90, A1 east of A2)
def oval(x, y, w, h):
    r = min(w, h) / 2
    return LineString([(x - (w / 2 - r), y - (h / 2 - r)), (x + (w / 2 - r), y + (h / 2 - r))]).buffer(r)
K1P = [(oval(kx + 3.75, ky, 2, 3), "Net-(D5-A)"), (oval(kx - 3.75, ky, 2, 3), "+5V")]
for dx in (-3.75, 3.75):
    K1P += [(oval(kx + dx, ky - 20.3, 3, 2), "LINE_FUSED"), (oval(kx + dx, ky - 25.34, 3, 2), "Net-(J4-Pin_1)")]
for l in cu: cu[l] += K1P
CRT = {r: box(*c) for r, c in G["crt"].items() if r not in ("K1", "RV3", "D6", "DS1")}
CRT["K1new"] = box(kx - 6.8, ky - 27.1, kx + 6.8, ky + 2.8)
CRT["D6plan"] = box(92.4, 9.55, 110.84, 15.45)
D6P = [(Point(94.0, 12.5).buffer(1.3), "LINE_FILT"), (Point(109.24, 12.5).buffer(1.3), "/Q1_A1")]
for l in cu: cu[l] += D6P
LVg = LV
def need(a, b):
    if a == b: return 0
    if a in MAINS and b in MAINS:
        return 1.0 if (a in LGRP and b in LGRP) or {a, b} <= {"Net-(J4-Pin_1)", "Net-(PS1-AC/N)"} else 2.5
    return 6.4 if (a in MAINS or b in MAINS) else 0.2
# grid for BFS
X0, X1, Y0, Y1, S = 25.0, 132.0, 0.5, 56.5, 0.25
nx, ny = int((X1 - X0) / S) + 1, int((Y1 - Y0) / S) + 1
xs = X0 + S * np.arange(nx); ys = Y0 + S * np.arange(ny)
def free_mask(layer, net, extra=()):
    obs = [g.buffer(need(n, net) + 1.25) for g, n in cu[layer] + list(extra) if need(n, net) > 0]
    obs.append(LV.buffer(6.4 + 1.25))
    obs.append(box(-5, -5, 200, 1.0 + 1.25).difference(box(-5, 1.0 + 1.25 - 0.01, 200, 1.0 + 1.25)))   # edge 1.0
    U = prepared.prep(unary_union(obs))
    m = np.zeros((ny, nx), bool)
    from shapely import points, contains_xy
    UU = unary_union(obs)
    XX, YY = np.meshgrid(xs, ys)
    m = ~contains_xy(UU, XX, YY)
    return m
def sources(layer, net, mask):
    src = np.zeros_like(mask)
    gs = [g for g, n in cu[layer] if n == net]
    if not gs: return src
    UU = unary_union(gs).buffer(0.3)
    from shapely import contains_xy
    XX, YY = np.meshgrid(xs, ys)
    return contains_xy(UU, XX, YY) & mask
from scipy import ndimage
def reach(layer, net):
    m = free_mask(layer, net)
    lab, n = ndimage.label(m)
    s = sources(layer, net, m)
    ids = set(np.unique(lab[s])) - {0}
    return np.isin(lab, list(ids)) if ids else np.zeros_like(m)
R = {(l, n): reach(l, n) for l in ("F.Cu", "B.Cu") for n in ("LINE_FUSED", "Net-(J4-Pin_1)")}
def ok_at(net, x, y):
    i, j = int(round((y - Y0) / S)), int(round((x - X0) / S))
    if not (0 <= i < ny and 0 <= j < nx): return []
    return [l for l in ("F.Cu", "B.Cu") if R[(l, net)][i, j]]
from shapely import contains_xy
from shapely.strtree import STRtree
XX, YY = np.meshgrid(xs, ys)
PADOK = {}
for net in ("LINE_FUSED", "Net-(J4-Pin_1)"):
    obs = [g.buffer(need(n, net) + 0.9) for l in cu for g, n in cu[l] if need(n, net) > 0] + [LV.buffer(6.4 + 0.9)]
    PADOK[net] = ~contains_xy(unary_union(obs), XX, YY)
CT = STRtree(list(CRT.values())); CL = list(CRT.values())
def at(mask, x, y):
    i, j = int(round((y - Y0) / S)), int(round((x - X0) / S))
    return 0 <= i < ny and 0 <= j < nx and mask[i, j]
res = []
for rot in (0, 90, 180, 270):
    a = math.radians(rot)
    def T(px, py):
        return (px * math.cos(a) + py * math.sin(a), -px * math.sin(a) + py * math.cos(a))
    c = [T(-2.5, -1.8), T(10.0, -1.8), T(10.0, 4.5), T(-2.5, 4.5)]
    p2 = T(7.5, 2.7)
    for x in np.arange(40, 90, 0.25):
        for y in np.arange(1, 56, 0.25):
            pads = [(x, y), (x + p2[0], y + p2[1])]
            for order in (("LINE_FUSED", "Net-(J4-Pin_1)"), ("Net-(J4-Pin_1)", "LINE_FUSED")):
                if not all(at(PADOK[n], px, py) for (px, py), n in zip(pads, order)): continue
                ra = [[l for l in ("F.Cu", "B.Cu") if at(R[(l, n)], px, py)] for (px, py), n in zip(pads, order)]
                if not all(ra): continue
                crt = Polygon([(x + u, y + v) for u, v in c])
                if not box(0.5, 0.5, 163.5, 98.5).contains(crt): continue
                if any(CL[i].intersection(crt).area > 1e-6 for i in CT.query(crt)): continue
                res.append(dict(rot=rot, x=float(x), y=float(y), pads=[(round(px, 2), round(py, 2), n) for (px, py), n in zip(pads, order)], layers=ra))
print(len(res))
for r in res[:60]: print(r)
json.dump(res, open("s3/rv3k_sites.json", "w"))
