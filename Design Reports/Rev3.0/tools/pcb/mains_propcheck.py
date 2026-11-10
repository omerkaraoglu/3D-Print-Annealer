"""check a mains placement proposal: courtyards, heatsink box, creepage to the LV polygon, pad clearances, edge/hole"""
import json, math, sys, itertools
from shapely.geometry import Polygon, Point, box
from shapely import affinity
src = sys.argv[1] if len(sys.argv) > 1 else "mains_placement_proposal.py"
ns = {}; exec(open(src).read(), ns); P = ns["P"]; HS = ns["HEATSINK"]; LVB = ns["LV_BOUNDARY"]
FP = json.load(open("mains_fp.json")); G = json.load(open("geom.json"))
LV = Polygon([(0.5, 0.5)] + LVB + [(161.0, 80.0), (161.0, 98.5), (0.5, 98.5)])
FALLBACK = {"J3": (-2.7, -2.5, 10.5, 2.5), "R1": (-2.7, -2.5, 10.5, 2.5), "J4": (-2.5, -2.3, 9.5, 2.3), "L1": (-6.8, -8.55, 6.8, 8.55)}
def rot(x, y, deg):
    t = math.radians(deg); return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "Net-(Q1-A1)", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "Net-(D1-A)", "Net-(D1-K)", "Net-(D2-K)", "Net-(D3-A)",
         "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)", "unconnected-(U5-NC-Pad5)"}
LCH = {"LINE", "LINE_FUSED", "LINE_FILT", "Net-(PS1-AC/L)"}; NCH = {"NEUT", "Net-(PS1-AC/N)"}
def clr(a, b):
    if a == b: return 0
    if a in MAINS and b in MAINS:
        if (a in LCH and b in LCH) or (a in NCH and b in NCH): return 1.0
        if {a, b} == {"Net-(D1-A)", "Net-(D2-K)"}: return 0.5
        return 2.5
    if a in MAINS or b in MAINS: return 4.0
    return 0.2
pads, crts = [], {}
for ref, (x, y, r, side) in P.items():
    f = FP[ref]
    for num, lx, ly, w, h, net in f["pads"]:
        dx, dy = rot(lx, ly, r); pads.append(dict(ref=ref, num=num, net=net, x=x + dx, y=y + dy, r=max(w, h) / 2))
    if ref == "L40":
        crts[ref] = Point(x, y).buffer(11.74, 32); continue
    c = f["crt"] if f["crt"] and ref not in FALLBACK else FALLBACK.get(ref, f["crt"])
    poly = Polygon([(c[0], c[1]), (c[2], c[1]), (c[2], c[3]), (c[0], c[3])])
    poly = Polygon([rot(px, py, r) for px, py in poly.exterior.coords])
    crts[ref] = affinity.translate(poly, x, y)
moved = set(P)
for p in G["pads"]:
    if p["ref"] in moved: continue
    pads.append(dict(ref=p["ref"], num=p["num"], net=p["net"] or "", x=p["x"] - 20, y=p["y"] - 20, r=max(p["w"], p["h"]) / 2))
# fixed courtyards near the band (from the current board)
for ref in ("PS1", "U1", "U5"):
    f = FP[ref]; c = f["crt"]; poly = Polygon([(c[0], c[1]), (c[2], c[1]), (c[2], c[3]), (c[0], c[3])])
    poly = Polygon([rot(px, py, f["rot"]) for px, py in poly.exterior.coords]); crts[ref] = affinity.translate(poly, *f["pos"])
print("== courtyard overlaps")
for a, b in itertools.combinations(crts, 2):
    i = crts[a].intersection(crts[b]).area
    if i > 0.01: print("  OVERLAP", a, b, round(i, 2))
hs = box(*HS)
for ref, c in crts.items():
    if ref != "Q1" and c.intersection(hs).area > 0.01: print("  IN HEATSINK BOX", ref, round(c.intersection(hs).area, 2))
print("== mains pads vs LV polygon (need >= 6.4 mm creepage, pad edge)")
for p in pads:
    if p["net"] not in MAINS: continue
    if p["ref"] == "K1" and p["num"] in ("2", "5"): continue
    d = Point(p["x"], p["y"]).distance(LV) - p["r"]
    if d < 6.4 and not (p["ref"] in ("U1", "U5")): print("  CREEP", p["ref"], p["num"], p["net"], round(p["x"], 2), round(p["y"], 2), "d=%.2f" % d)
print("== SELV pads inside the mains region")
for p in pads:
    if p["net"] in MAINS or p["ref"] == "K1": continue
    if not LV.buffer(0.01).contains(Point(p["x"], p["y"])) and p["y"] < 99 and p["ref"] not in ("PS1",): print("  SELV IN MAINS", p["ref"], p["num"], p["net"], round(p["x"], 2), round(p["y"], 2))
print("== pad-pad clearance (mains)")
for a, b in itertools.combinations([p for p in pads if p["net"] in MAINS or p["ref"] in moved], 2):
    if a["ref"] == b["ref"] and a["ref"] in ("Q1", "U1", "U5", "K1", "F1", "F3"): continue
    c = clr(a["net"], b["net"])
    d = math.hypot(a["x"] - b["x"], a["y"] - b["y"]) - a["r"] - b["r"]
    if d < c - 0.01: print("  PADCLR", a["ref"], a["num"], a["net"][:12], b["ref"], b["num"], b["net"][:12], "d=%.2f need %.1f" % (d, c))
print("== edge / hole")
for p in pads:
    if p["net"] in MAINS:
        e = min(p["x"], p["y"], 164 - p["x"], 99 - p["y"]) - p["r"]
        if e < 1.0: print("  EDGE", p["ref"], p["num"], round(e, 2))
    if math.hypot(p["x"] - 4, p["y"] - 4) - p["r"] < 3 + 1.6: print("  HOLE", p["ref"], p["num"])
json.dump([dict(ref=p["ref"], num=p["num"], net=p["net"], x=round(p["x"], 3), y=round(p["y"], 3)) for p in pads if p["ref"] in moved], open("mains_prop_pads.json", "w"))
print("done")
