"""Stage-3 barrier figures (RV3 pads included since the RV3 move) on the built board (geom_export JSON): coil side (K1 A1/A2 pads, the +5V / Net-(D5-A) feeds in the
notch) to any mains copper, and contact side (K1 11/14 pads, the LINE_FUSED trunk and fan route of stage 3) to any
low-voltage copper per layer, outer and inner (fills included). Straight-line distances: on the outer layers they are
also the creepage path length (no slot or obstacle shortens a surface path below the straight line).
Usage: s3_barrier.py gx.json"""
import json, sys
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
G = json.load(open(sys.argv[1]))
M = set(G["mains"]) | {"/Q1_A1", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
M.discard("unconnected-(K1-Pad4)")
LAY = ["F.Cu", "GND", "PWR", "B.Cu"]
NAME = {"GND": "In1.Cu", "PWR": "In2.Cu"}
def P(q): return Polygon(q).buffer(0)
items = []          # (layer, net, kind, geom)
for p in G["pads"]:
    for q in p["poly"]:
        if len(q) > 2:
            for l in (p["layers"] or ["F.Cu"]):
                ln = {"In1.Cu": "GND", "In2.Cu": "PWR"}.get(l, l)
                items.append((ln, p["net"], "pad %s.%s" % (p["ref"], p["num"]), P(q)))
for t in G["tracks"]:
    for q in t["poly"]:
        if len(q) > 2:
            for l in t["layers"]:
                ln = {"In1.Cu": "GND", "In2.Cu": "PWR"}.get(l, l)
                items.append((ln, t["net"], t["cls"][4:].lower(), P(q)))
for f in G["fills"]:
    for q in f["polys"]:
        items.append((f["layer"], f["net"], "fill" + (" teardrop" if f["teardrop"] else ""), Polygon(q[0], q[1:]).buffer(0)))
NOTCH = box(61.5, 45.0, 77.0, 56.3)
coil = [(l, n, k, g) for l, n, k, g in items if (k.startswith("pad K1.A") or (n in ("+5V", "Net-(D5-A)") and k in ("track", "arc") and g.within(box(60, 44, 82.7, 56.4))))]
cont = [(l, n, k, g) for l, n, k, g in items if k in ("pad K1.11", "pad K1.14", "pad RV3.1", "pad RV3.2") or (n in ("LINE_FUSED", "Net-(J4-Pin_1)") and k in ("track", "arc") and g.intersects(box(47, 12, 82, 33)))]
print("coil side -> nearest mains copper (any layer):")
best = sorted((g.distance(h), lc, kc, n, k, l) for lc, nc, kc, g in coil for l, n, k, h in items if n in M and l == lc)[:3]
for b in best: print("   %.2f mm  %s %s  <->  %s %s (%s)" % (b[0], b[1], b[2], b[3], b[4], b[5]))
best = sorted((g.distance(h), lc, kc, n, k, l) for lc, nc, kc, g in coil for l, n, k, h in items if n in M)[:3]
print("   (across layers, through the laminate) %.2f mm %s" % (best[0][0], best[0][3]))
print("contact side -> nearest low-voltage copper, per layer:")
for L in LAY:
    cand = [(g.distance(h), kc, n, k) for lc, nc, kc, g in cont if lc in (L, "F.Cu", "B.Cu") for l, n, k, h in items if l == L and n not in M and n != ""]
    if L in ("GND", "PWR"):
        cand = [(g.distance(h), kc, n, k) for lc, nc, kc, g in cont for l, n, k, h in items if l == L and n not in M and n != ""]
    c = min(cand)
    print("   %-6s %.2f mm  %s <-> %s %s" % (NAME.get(L, L), c[0], c[1], c[2], c[3]))
print("coil side -> nearest mains net copper, HS1 pins excluded:")
b = min((g.distance(h), kc, n, k, l) for lc, nc, kc, g in coil for l, n, k, h in items if n in M and not n.startswith("unconnected-(HS1"))
print("   %.2f mm  %s <-> %s %s (%s)" % b)
print("K1 contact pads only -> low-voltage copper per layer:")
for L in LAY:
    c = min((g.distance(h), kc, n, k) for lc, nc, kc, g in cont if kc.startswith("pad") and lc == L for l, n, k, h in items if l == L and n not in M and n != "")
    print("   %-6s %.2f mm  %s <-> %s %s" % (NAME.get(L, L), c[0], c[1], c[2], c[3]))
print("notch: In1 / In2 fill inside the notch vs contact pads / new mains tracks:")
for L in ("GND", "PWR"):
    fills = [h for l, n, k, h in items if l == L and k == "fill" and n not in M and h.intersects(NOTCH)]
    U = unary_union(fills).intersection(box(55, 38, 82, 56.3))
    c1 = min(g.distance(U) for lc, nc, kc, g in cont if kc.startswith("pad"))
    c2 = min(g.distance(U) for lc, nc, kc, g in cont if not kc.startswith("pad"))
    print("   %s  edge y_min in notch %.2f; to contact pads %.2f mm, to LINE_FUSED / fan tracks %.2f mm" % (NAME[L], U.bounds[1], c1, c2))
