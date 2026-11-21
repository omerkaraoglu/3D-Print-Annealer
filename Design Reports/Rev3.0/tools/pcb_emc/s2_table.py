"""Stage 2 pad table: centre (local / abs), vias, partial-inductance estimate of the via group, nearest mains copper,
frame-side feature (frame v2 params: support ribs, shelf window). Usage: s2_table.py plan.json geo.json frame_params.json"""
import json, sys, math
import numpy as np
from shapely.geometry import box, Point, LineString, Polygon
plan = json.load(open(sys.argv[1])); G = json.load(open(sys.argv[2])); FP = json.load(open(sys.argv[3], encoding="utf-8"))
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "/Q1_A1", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)",
         "unconnected-(U5-NC-Pad5)", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
mc = [(LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2), s[5]) for s in G["segs"] if s[5] in MAINS]
mc += [(Polygon(p["pts"]), p["ref"] + "." + p["num"] + " " + p["net"]) for p in G["pads"] if p["net"] in MAINS and len(p["pts"]) > 2]
ribs = [(r["rib"], box(r["x0"] - 20, r["y0"] - 20, r["x1"] - 20, r["y1"] - 20)) for r in FP["support_ribs"]["per_rib"]]
h, d = 1.27, 0.3        # B.Cu -> In1 (0.2 prepreg + In2 + 1.0 core + copper), via drill (plated barrel ~0.3)
def Lself(h, r):        # partial self inductance of a straight round conductor, nH (mm)
    return 0.2 * h * (math.log(2 * h / r) - 1 + r / h) if False else 0.2 * h * (math.log((h + math.sqrt(h * h + r * r)) / r) - math.sqrt(1 + (r / h) ** 2) + r / h)
def M(h, s):
    return 0.2 * h * (math.log(h / s + math.sqrt(1 + (h / s) ** 2)) - math.sqrt(1 + (s / h) ** 2) + s / h)
print("| pad | centre local | centre KiCad abs | GND vias | L(vias) nH | nearest mains copper | frame side |")
for p in plan["pads"]:
    cx, cy = p["x"], p["y"]; vs = p["kept"] + p["new"]; n = len(vs)
    Lm = np.array([[Lself(h, d / 2) if i == j else M(h, math.dist(vs[i], vs[j])) for j in range(n)] for i in range(n)])
    Leq = 1.0 / np.linalg.inv(Lm).sum()
    cu = box(cx - 4, cy - 3.5, cx + 4, cy + 3.5)
    dm, who = min((g.distance(cu), w) for g, w in mc)
    bare = box(cx - 3, cy - 2.5, cx + 3, cy + 2.5)
    rb = min((g.distance(bare), r) for r, g in ribs)
    win = min(cx - 3 - 2.62, 162.32 - (cx + 3), cy - 2.5 - 1.6, 96.4 - (cy + 2.5))
    p["L_nH"] = round(Leq, 2); p["mains_mm"] = round(dm, 1); p["mains_item"] = who; p["rib"] = rb; p["win"] = round(win, 1)
    print("| %s | (%.2f, %.2f) | (%.2f, %.2f) | %d (%d new) | %.2f | %.1f mm (%s) | window, bare area %.1f mm inside its edge; Formex opening needed; nearest support rib %d %.1f mm (on the shelf) |"
          % (p["ref"], cx, cy, cx + 20, cy + 20, n, len(p["new"]), Leq, dm, who, win, rb[1], rb[0]))
print("single via self L %.2f nH" % Lself(h, d / 2))
json.dump(plan, open(sys.argv[1].replace(".json", "_table.json"), "w"), indent=1)
