"""Stage 2 - feasibility of GND landing-pad sites on B.Cu (local mm = KiCad abs - 20).
Pad model: copper W x H (default 8.0 x 7.0) with a 6.0 x 5.0 mask opening (bare landing area), GND vias 0.6/0.3 on the
copper rim (half-dims RX, RY), nominal 8 positions (4 corners + 4 mid-sides), each allowed to slide along its rim edge.
Hard limits (brief): inside the Cmts.User LV polygon, >= 6.4 mm from any mains copper (all layers), bare area >= 1.0 mm inside
the frame's shelf window (x 2.62-162.32, y 1.6-96.4), copper clear of the antenna keep-out, the In1 keep-outs under L30/L11,
the washer keep-outs, J10 / J11 courtyards + 1.0 (tented vias, FPC ends) and the thermocouple QUIET box (no vias there).
B.Cu under the copper (+0.25): no foreign-net tracks / pads / vias, no connected GND vias or GND tracks (free stitching vias
are removed).  Vias: >= 0.2 mm to foreign copper on F.Cu / B.Cu, >= 1.10 mm to non-GND vias, >= 0.9 to kept GND vias,
not on any F.Cu pad.
Usage: s2_sites.py geo.json scan out.json          -> grid scan of feasible centres (0.5 mm), with blocking B.Cu nets
       s2_sites.py geo.json eval x,y [x,y ...]       -> detailed report for given centres"""
import json, sys, math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree
from shapely.ops import unary_union
G = json.load(open(sys.argv[1]))
W, H, MW, MH = 8.0, 7.0, 6.0, 5.0
RX, RY = 3.5, 3.0
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "/Q1_A1", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)",
         "unconnected-(U5-NC-Pad5)", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
LV = Polygon([(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
              (126.0, 54.8), (130.0, 55.5), (130.0, 40.0), (163.5, 40.0), (163.5, 98.5), (0.5, 98.5)])
WIN = box(2.62, 1.6, 162.32, 96.4)
KEEP = [box(-1.0, 36.0, 7.6, 64.0), box(72.3, 86.0, 80.3, 94.0), box(80.9, 78.35, 86.9, 84.35)]
QUIET = box(4.0, 77.5, 33.6, 87.5)
for r in ("J10", "J11"):
    c = G["crt"][r]; KEEP.append(box(c[0] - 1.0, c[1] - 1.0, c[2] + 1.0, c[3] + 1.0))
# copper items
items = {"F.Cu": [], "B.Cu": []}
for s in G["segs"]:
    if s[6] in items: items[s[6]].append((LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2), s[5], "trk"))
for p in G["pads"]:
    if len(p["pts"]) < 3: continue
    g = Polygon(p["pts"])
    for l in ("F.Cu", "B.Cu"):
        if l in p["layers"]: items[l].append((g, p["net"], "pad:%s.%s" % (p["ref"], p["num"])))
tree = {l: STRtree([g for g, n, k in v]) for l, v in items.items()}
# vias: free (no track end on them) vs connected
ends = set()
for s in G["segs"]:
    ends.add((round(s[0], 2), round(s[1], 2))); ends.add((round(s[2], 2), round(s[3], 2)))
VIAS = []
for v in G["vias"]:
    free = (round(v[0], 2), round(v[1], 2)) not in ends
    VIAS.append(dict(x=v[0], y=v[1], d=v[2], net=v[3], free=free))
VT = STRtree([Point(v["x"], v["y"]) for v in VIAS])
mains = [g for l in items for g, n, k in items[l] if n in MAINS] + [Point(v["x"], v["y"]).buffer(v["d"] / 2) for v in VIAS if v["net"] in MAINS]
MT = STRtree(mains)

def mains_dist(g):
    best = 99.0
    for i in MT.query(g.buffer(40.0)):
        best = min(best, mains[i].distance(g))
    return best

def blockers(cu):
    """B.Cu copper under the pad (+0.25) that is not removable.  GND through-hole pads (e.g. U3's thermal vias) are
    accepted under the masked copper rim, never under the bare area (+0.35)."""
    out = []
    c = cu.centroid; bare = box(c.x - MW / 2 - 0.35, c.y - MH / 2 - 0.35, c.x + MW / 2 + 0.35, c.y + MH / 2 + 0.35)
    for i in tree["B.Cu"].query(cu.buffer(0.25)):
        g, n, k = items["B.Cu"][i]
        if g.distance(cu) < 0.25:
            if n == "GND" and k.startswith("pad") and not g.intersects(bare): continue
            out.append((n, k))
    for i in VT.query(cu.buffer(0.6)):
        v = VIAS[i]
        if Point(v["x"], v["y"]).buffer(v["d"] / 2).distance(cu) < 0.25 and v["net"] != "GND":
            out.append((v["net"], "via(%.2f,%.2f)" % (v["x"], v["y"])))
    return out

def via_ok(x, y, removed):
    c = Point(x, y).buffer(0.3)
    for l in ("F.Cu", "B.Cu"):
        for i in tree[l].query(c.buffer(0.2)):
            g, n, k = items[l][i]
            if g.distance(c) < 0.2 and (n != "GND" or (l == "F.Cu" and k.startswith("pad"))): return False
    if any(c.intersects(k) for k in KEEP) or c.intersects(QUIET): return False
    for i in VT.query(Point(x, y).buffer(1.5)):
        v = VIAS[i]
        if i in removed: continue
        d = math.hypot(v["x"] - x, v["y"] - y)
        if v["net"] != "GND" and d < 1.10: return False
        if v["net"] == "GND" and d < 0.9: return False
    return True

def rim_vias(cx, cy, removed, kept):
    """8 nominal rim positions (4 corners + 4 mid-sides). A kept GND via within 1.0 mm of a nominal position serves it;
    otherwise a new via slides along the rim up to +-1.5 mm to the first legal spot (>= 1.2 mm from the other pad vias)."""
    nom = [(-RX, -RY, "c"), (RX, -RY, "c"), (RX, RY, "c"), (-RX, RY, "c"), (0, -RY, "h"), (0, RY, "h"), (-RX, 0, "v"), (RX, 0, "v")]
    got, new = list(kept), []
    for dx, dy, t in nom:
        if any(math.hypot(cx + dx - a, cy + dy - b) < 1.0 for a, b in kept): continue
        cand = []
        for k in range(0, 13):
            o = 0.125 * ((k + 1) // 2) * (1 if k % 2 else -1)
            if t == "h": cand.append((dx + 2 * o, dy))
            elif t == "v": cand.append((dx, dy + 2 * o))
            else:
                if o >= 0: cand.append((dx - math.copysign(2 * o, dx), dy))
                else: cand.append((dx, dy + math.copysign(2 * o, dy)))
        for px, py in cand:
            x, y = cx + px, cy + py
            if all(math.hypot(x - a, y - b) >= 1.2 for a, b in got) and via_ok(x, y, removed):
                got.append((x, y)); new.append((x, y)); break
    return got, new

def evaluate(cx, cy):
    cu = box(cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2)
    bare = box(cx - MW / 2, cy - MH / 2, cx + MW / 2, cy + MH / 2)
    r = dict(x=cx, y=cy, why=[])
    if not WIN.buffer(-1.0).contains(bare): r["why"].append("window")
    if not LV.contains(cu): r["why"].append("LV")
    md = mains_dist(cu); r["mains"] = round(md, 2)
    if md < 6.4: r["why"].append("mains")
    if any(cu.intersects(k) for k in KEEP): r["why"].append("keepout")
    if cu.intersects(QUIET): r["why"].append("quiet")
    bl = blockers(cu); r["block"] = sorted(set(n for n, k in bl)); r["blockk"] = bl
    if r["why"] and FAST:
        r["vias"] = []; return r
    removed, kept = set(), []
    for i in VT.query(cu.buffer(1.0)):
        v = VIAS[i]
        if v["net"] != "GND": continue
        dx, dy = abs(v["x"] - cx), abs(v["y"] - cy)
        inbare = dx < MW / 2 + 0.35 and dy < MH / 2 + 0.35
        incu = dx < W / 2 and dy < H / 2
        if inbare:
            if v["free"]: removed.add(i)
            else: r["why"].append("gndvia_in_bare")
        elif incu:
            kept.append((v["x"], v["y"]))
        elif Point(v["x"], v["y"]).distance(cu) < 0.95 and v["free"]:
            removed.add(i)          # free stitching via crowding the rim: re-placed by the pad vias
    kept = [k for k in kept]
    r["removed"] = [(round(VIAS[i]["x"], 3), round(VIAS[i]["y"], 3)) for i in sorted(removed)]
    vs, new = rim_vias(cx, cy, removed, kept); r["vias"] = [(round(a, 3), round(b, 3)) for a, b in vs]
    r["new"] = [(round(a, 3), round(b, 3)) for a, b in new]; r["kept"] = [(round(a, 3), round(b, 3)) for a, b in kept]
    sides = [any(b <= cy - RY + 0.6 for a, b in vs), any(b >= cy + RY - 0.6 for a, b in vs),
             any(a <= cx - RX + 0.6 for a, b in vs), any(a >= cx + RX - 0.6 for a, b in vs)]
    if len(vs) < 6 or not all(sides): r["why"].append("vias%d" % len(vs))
    return r

FAST = False
if __name__ == "__main__":
    if sys.argv[2] == "scan":
        FAST = True
        out = []
        y = 2.0
        while y <= 96.0:
            x = 2.0
            while x <= 163.0:
                r = evaluate(x, y)
                hard = [w for w in r["why"]]
                out.append(dict(x=x, y=y, hard=hard, block=r["block"], nv=len(r["vias"]), mains=r["mains"]))
                x += 0.5
            y += 0.5
        json.dump(out, open(sys.argv[3], "w"))
        ok = [o for o in out if not o["hard"] and not o["block"]]
        okb = [o for o in out if not o["hard"] and o["block"]]
        print("feasible (no moves):", len(ok), " feasible if tracks move:", len(okb))
    else:
        for a in sys.argv[3:]:
            x, y = map(float, a.split(","))
            r = evaluate(x, y); r.pop("blockk")
            print(json.dumps(r))
