"""Stage 2 - plan of the GND landing pads BP1..BPn (system python + shapely; local mm = KiCad abs - 20).

For every pad centre in PADS: copper 8.0 x 7.0 (bare 6.0 x 5.0), GND vias 0.6/0.3 on the masked rim (half-dims 3.5 x 3.0):
  1  free GND stitching vias whose centre lies within the copper + 1.0 mm are taken out; a non-free GND via inside the
     bare area + 0.35 is an error, one on the rim is kept and counted;
  2  eight rim positions (4 corners, 4 mid-sides): a kept via within 1.0 mm serves a position, otherwise a new via
     slides along the rim (+-1.5 mm, 0.125 steps) to the first point that passes the house stitching rules
     (pcb_smooth/stitch_plan.py `why`: 0.3 mm to all other copper, never on a pad, 1.35 mm via pitch, In2 web,
     >= 6.4 mm from mains copper, 0.8 mm from the edge, rule areas incl. the thermocouple QUIET box, inside the In1
     and an outer GND fill);
  3  stitching vias taken out in 1 that lie outside the copper and still pass the rules are put back.
Pad checks (hard): bare area >= 1.0 mm inside the frame's shelf window, copper inside the Cmts.User LV polygon,
>= 6.4 mm from mains copper, clear of the antenna / In1-inductor / washer keep-outs, the J10 / J11 courtyards + 1.0,
the QUIET box; no foreign B.Cu copper under the copper + 0.25 (GND through-hole pads only under the masked rim).
Labels: "BPn" on B.SilkS (0.8 / 0.7 / 0.10, the house S style), centred on one side of the copper (gap 0.3), the side
chosen free of vias / holes (+0.15), other pads' copper and other labels.
Usage: s2_plan.py gx.json vias.json geo.json plan.json"""
import json, sys, math, os
from shapely.geometry import Point, box, Polygon
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), "pcb_smooth", "stitch_plan.py") if os.path.exists(os.path.join(os.path.dirname(HERE), "pcb_smooth")) else \
    r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth/stitch_plan.py"
gx, vjson, geo, outp = sys.argv[1:5]
ARGV = list(sys.argv)
G0 = json.load(open(gx))
if "/Q1_A1" not in G0["mains"]: G0["mains"].append("/Q1_A1")
tmp = outp + ".gx.json"; json.dump(G0, open(tmp, "w"))
sys.argv = ["stitch_plan.py", tmp]
src = open(SP, encoding="utf-8").read().split("placed = []")[0]
exec(compile(src, SP, "exec"))
allv = [(x, y) for x, y, n, w in vias]
rej = {}
exec(compile("def why(" + open(SP, encoding="utf-8").read().split("def why(")[1].split("\ndef ok(")[0], SP, "exec"), globals())
os.remove(tmp)

W, H, MW, MH, RX, RY = 8.0, 7.0, 6.0, 5.0, 3.5, 3.0
PADS = [(18.5, 7.0), (18.5, 18.0), (18.5, 29.0), (36.0, 45.0), (45.0, 45.0), (146.0, 48.0), (155.5, 59.0), (155.5, 70.0),
        (155.5, 81.0), (155.5, 92.0), (116.5, 92.0), (108.0, 84.0), (91.5, 88.5), (59.0, 91.0), (29.5, 92.0), (16.0, 92.0),
        (21.0, 50.0), (137.0, 70.0)]
for a in ARGV[5:]:
    if a.startswith("pads="): PADS = [tuple(map(float, q.split(","))) for q in a[5:].split(";")]
VIAS = json.load(open(vjson))          # [x, y, net, free, uuid]
GEO = json.load(open(geo))
ALL = [(v[0], v[1]) for v in VIAS]
allv[:] = list(ALL)

def rm_from_allv(x, y):
    for i, (a, b) in enumerate(allv):
        if abs(a - x) < 1e-3 and abs(b - y) < 1e-3:
            allv.pop(i); return
    raise KeyError((x, y))

plan = dict(pads=[], removed=[], added=[], errors=[])
removed_uuid = set()
for n, (cx, cy) in enumerate(PADS, 1):
    rec = dict(ref="BP%d" % n, x=cx, y=cy, kept=[], new=[], removed=[], back=[])
    rm = []
    for v in VIAS:
        if v[2] != "GND" or v[4] in removed_uuid: continue
        dx, dy = abs(v[0] - cx), abs(v[1] - cy)
        if dx < MW / 2 + 0.35 and dy < MH / 2 + 0.35:
            if v[3]: rm.append(v)
            else: plan["errors"].append("%s: non-free GND via in the bare area at %s" % (rec["ref"], v[:2]))
        elif dx < W / 2 + 1.0 and dy < H / 2 + 1.0:
            if v[3]: rm.append(v)
            elif dx < W / 2 and dy < H / 2: rec["kept"].append((v[0], v[1]))
    for v in rm:
        rm_from_allv(v[0], v[1]); removed_uuid.add(v[4])
    nom = [(-RX, -RY, "c"), (RX, -RY, "c"), (RX, RY, "c"), (-RX, RY, "c"), (0, -RY, "h"), (0, RY, "h"), (-RX, 0, "v"), (RX, 0, "v")]
    for dx, dy, t in nom:
        if any(math.hypot(cx + dx - a, cy + dy - b) < 1.0 for a, b in rec["kept"]): continue
        cand = []
        for k in range(0, 25):
            o = 0.125 * ((k + 1) // 2) * (1 if k % 2 else -1)
            if t == "h": cand.append((dx + o, dy))
            elif t == "v": cand.append((dx, dy + o))
            elif o >= 0: cand.append((dx - math.copysign(o, dx), dy))
            else: cand.append((dx, dy + math.copysign(o, dy)))
        for px, py in cand:
            x, y = round(cx + px, 3), round(cy + py, 3)
            if why(x, y) is None:
                rec["new"].append((x, y)); allv.append((x, y)); break
    # put back the stitching vias outside the copper that still pass
    for v in rm:
        dx, dy = abs(v[0] - cx), abs(v[1] - cy)
        if dx >= W / 2 + 0.3 or dy >= H / 2 + 0.3:
            if why(v[0], v[1]) is None:
                allv.append((v[0], v[1])); removed_uuid.discard(v[4]); rec["back"].append((v[0], v[1])); continue
        rec["removed"].append(dict(x=v[0], y=v[1], uuid=v[4]))
    vs = rec["kept"] + rec["new"]
    sides = [any(b <= cy - RY + 0.6 for a, b in vs), any(b >= cy + RY - 0.6 for a, b in vs),
             any(a <= cx - RX + 0.6 for a, b in vs), any(a >= cx + RX - 0.6 for a, b in vs)]
    if len(vs) < 5 or not all(sides): plan["errors"].append("%s: only %d vias / sides %s" % (rec["ref"], len(vs), sides))
    plan["pads"].append(rec)
    plan["removed"] += rec["removed"]; plan["added"] += rec["new"]

# ---- labels ----
TH, TW = 0.8, 0.7
def label_box(ref, x, y, ang):
    w = len(ref) * TW * 1.1 + 0.1; h = TH + 0.1
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2) if ang == 0 else box(x - h / 2, y - w / 2, x + h / 2, y + w / 2)
holes = [Point(a, b).buffer(0.3) for a, b in allv] + [Polygon(p["pts"]) for p in GEO["pads"] if "B.Cu" in p["layers"] and len(p["pts"]) > 2]
coppers = [box(p["x"] - W / 2, p["y"] - H / 2, p["x"] + W / 2, p["y"] + H / 2) for p in plan["pads"]]
labels = []
edge = box(0.5, 0.5, 163.5, 98.5)
for rec, cu in zip(plan["pads"], coppers):
    best = None
    for side, (lx, ly, ang) in (("T", (rec["x"], rec["y"] - H / 2 - 0.3 - 0.45, 0)), ("B", (rec["x"], rec["y"] + H / 2 + 0.3 + 0.45, 0)),
                                ("L", (rec["x"] - W / 2 - 0.3 - 0.45, rec["y"], 90)), ("R", (rec["x"] + W / 2 + 0.3 + 0.45, rec["y"], 90))):
        for sh in (0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0):
            x, y = (lx + sh, ly) if ang == 0 else (lx, ly + sh)
            g = label_box(rec["ref"], x, y, ang)
            if not edge.contains(g): continue
            if any(g.distance(h) < 0.15 for h in holes): continue
            if any(g.intersects(c) for c in coppers): continue
            if any(g.distance(l) < 0.3 for l in labels): continue
            cost = abs(sh) + (0.3 if ang else 0) + {"T": 0, "B": 0.1, "L": 0.2, "R": 0.2}[side]
            if best is None or cost < best[0]: best = (cost, x, y, ang, g)
            break
    if best is None: plan["errors"].append("%s: no label spot" % rec["ref"]); continue
    rec["label"] = [round(best[1], 3), round(best[2], 3), best[3]]; labels.append(best[4])
json.dump(plan, open(outp, "w"), indent=1)
print("pads %d, vias removed %d, added %d, put back %d" % (len(plan["pads"]), len(plan["removed"]), len(plan["added"]), sum(len(p["back"]) for p in plan["pads"])))
for p in plan["pads"]:
    print("%-5s (%6.2f,%6.2f) kept %d new %d removed %d label %s" % (p["ref"], p["x"], p["y"], len(p["kept"]), len(p["new"]), len(p["removed"]), p.get("label")))
for e in plan["errors"]: print("ERROR", e)
print("why() rejects:", rej)
