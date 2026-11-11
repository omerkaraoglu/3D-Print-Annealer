"""Pass-2 mains placement checker (agent "mains").  Works on the BUILT board (real KiCad pads/courtyards):
    python mains2_check.py geom_mains.json crt_mains.json [selv_tracks.json,...]
Checks: courtyard overlaps in the band, HS1 heatsink envelope (45 x 12.7 box around the plate centre, 63.5 mm tall) vs
tall parts (>= 1 mm) and vs any other courtyard, pad-pad clearance with the mains rules (2.5 / 1.0 L,N chains / 0.5 DC pair,
4.0+6.4 to SELV), HS1 pins (>= 2.5 to mains copper, >= 6.4 to SELV copper), mains pads vs the LV polygon (6.4 creepage
proxy), mains pads vs other regions' SELV tracks (6.4), 1.0 mm to the board edge."""
import json, math, sys, itertools
from shapely.geometry import Polygon, Point, box, LineString
G = json.load(open(sys.argv[1])); C = json.load(open(sys.argv[2]))
TJ = [f for f in (sys.argv[3].split(",") if len(sys.argv) > 3 else []) if f]
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "Net-(Q1-A1)", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "Net-(D1-A)", "Net-(D1-K)", "Net-(D2-K)", "Net-(D3-A)",
         "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)", "unconnected-(U5-NC-Pad5)"}
LCH = {"LINE", "LINE_FUSED", "LINE_FILT", "Net-(PS1-AC/L)"}; NCH = {"NEUT", "Net-(PS1-AC/N)"}
TALL = ("L40", "C40", "K1", "L1", "PS1")
LV = Polygon([(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
              (126.0, 54.8), (130.0, 55.5), (130.0, 80.0), (161.0, 80.0), (161.0, 98.5), (0.5, 98.5)])
def clr(a, b):
    if a == b: return 0
    am, bm = a in MAINS, b in MAINS
    if am and bm:
        if (a in LCH and b in LCH) or (a in NCH and b in NCH): return 1.0
        if {a, b} == {"Net-(D1-A)", "Net-(D2-K)"}: return 0.5
        if {a, b} == {"Net-(Q1-G)", "unconnected-(U1-NC-Pad3)"}: return 0.5   # rule gate_vs_u1_nc (floating pin)
        return 2.5
    if am or bm: return 6.4
    return 0.2
pads = []
for p in G["pads"]:
    if p["ref"] == "H" or p["npth"]: continue
    poly = Polygon([(x - 20, y - 20) for x, y in p["poly"]]) if len(p["poly"]) > 2 else Point(p["x"] - 20, p["y"] - 20).buffer(max(p["w"], p["h"]) / 2)
    pads.append(dict(ref=p["ref"], num=p["num"], net=p["net"] or "", x=p["x"] - 20, y=p["y"] - 20, g=poly))
crt = {r: Polygon(c["crt"][0]) for r, c in C.items() if c["crt"] and c["side"] == "F"}
inband = lambda r: r in crt and crt[r].intersects(box(25, 0, 164, 58))
nviol = 0
def bad(*a):
    global nviol; nviol += 1; print("  ", *a)
print("== courtyard overlaps (mains band, HS1/Q1 intended)")
for a, b in itertools.combinations(sorted(r for r in crt if inband(r)), 2):
    if {a, b} == {"HS1", "Q1"}: continue
    i = crt[a].intersection(crt[b]).area
    if i > 0.001: bad("OVERLAP", a, b, round(i, 3))
hx, hy = C["HS1"]["pos"]; ENV = box(hx - 22.5, hy - 6.35, hx + 22.5, hy + 6.35)
b_ = ENV.bounds; print("== HS1 envelope x %.2f..%.2f, y %.2f..%.2f" % (b_[0], b_[2], b_[1], b_[3]))
L1x, L1y = C["L1"]["pos"]; body = {"L1": box(L1x - 6.75, L1y - 8.5, L1x + 6.75, L1y + 8.5)}
for r in TALL:
    g = body.get(r, crt.get(r)); d = g.distance(ENV)
    print("   tall %-4s gap %.2f %s" % (r, d, "" if d >= 1.0 - 1e-6 else "<-- < 1.0 mm")); nviol += d < 1.0 - 1e-6
for r, g in crt.items():
    if r in ("HS1", "Q1") or r in TALL: continue
    if g.intersects(ENV) and g.intersection(ENV).area > 0.001: bad("PART IN HEATSINK ENVELOPE", r)
print("== pad clearances")
SAMEFP = ("Q1", "U1", "U5", "K1", "F1", "F3")
EXC_K1 = lambda a, b: ({a["net"], b["net"]} & {"+5V", "Net-(D5-A)"}) and (a["ref"] == "K1" or b["ref"] == "K1" or {a["net"], b["net"]} & {"LINE", "unconnected-(K1-Pad4)"})
near = [p for p in pads if p["y"] < 62 and p["x"] > 24]
for a, b in itertools.combinations(near, 2):
    if a["ref"] == b["ref"] and a["ref"] in SAMEFP: continue
    hs = "HS1" in (a["ref"], b["ref"])
    if hs:
        o = b if a["ref"] == "HS1" else a
        if o["ref"] == "HS1" or not o["net"]: continue
        need = 2.5 if o["net"] in MAINS else 6.4
    else:
        if not (a["net"] in MAINS or b["net"] in MAINS): continue
        need = clr(a["net"], b["net"])
        if need == 0: continue
        if need == 6.4 and EXC_K1(a, b): continue
        if {a["ref"], b["ref"]} <= {"U1", "U5"} or (need == 6.4 and a["ref"] == b["ref"]): continue
    d = a["g"].distance(b["g"])
    if d < need - 0.005: bad("PADCLR %s.%s %s | %s.%s %s  d=%.2f need %.1f" % (a["ref"], a["num"], a["net"][:14], b["ref"], b["num"], b["net"][:14], d, need))
print("== mains pads vs LV polygon (6.4 creepage proxy; U1/U5 straddle by design)")
for p in pads:
    if p["net"] not in MAINS or p["ref"] in ("U1", "U5"): continue
    d = p["g"].distance(LV)
    if d < 6.4 - 0.005: bad("CREEP %s.%s %s (%.2f,%.2f) d=%.2f" % (p["ref"], p["num"], p["net"], p["x"], p["y"], d))
print("== mains pads vs SELV tracks of other regions (6.4)")
for f in TJ:
    for t in json.load(open(f)):
        if t["net"] in MAINS: continue
        g = Point(t["x"] - 20, t["y"] - 20).buffer(t["d"] / 2) if t["via"] else LineString([(t["x1"] - 20, t["y1"] - 20), (t["x2"] - 20, t["y2"] - 20)]).buffer(t["w"] / 2)
        for p in pads:
            if p["net"] in MAINS or p["ref"] == "HS1":
                if p["ref"] in ("U1", "U5", "K1"): continue
                need = 6.4
                d = p["g"].distance(g)
                if d < need - 0.005: bad("SELVTRK %s.%s %s vs %s %s d=%.2f" % (p["ref"], p["num"], p["net"][:12], t["net"][:14], f, d))
print("== edge 1.0 mm (mains + HS1 pads)")
for p in pads:
    if p["net"] in MAINS or p["ref"] == "HS1":
        minx, miny, maxx, maxy = p["g"].bounds; e = min(minx, miny, 164 - maxx, 99 - maxy)
        if e < 1.0: bad("EDGE %s.%s %.2f" % (p["ref"], p["num"], e))
print("SUMMARY: %d issue(s)" % nviol)
