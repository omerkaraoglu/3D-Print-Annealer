"""Stage-3 prep: RZ03-1A4 / HF115FD (KiCad Relay_SPST_Schrack-RT1-16A-FormA_RM5mm, rotated so the coil pins are south)
at local (cx, yc) against the board after stage 2: coil pads to mains copper, contact pads to SELV copper, contact pads
to other mains nets, courtyard overlaps. K1's own pads and the copper that is re-routed with it (+5V / Net-(D5-A) north of
y 56.5, LINE_FUSED / Net-(J4-Pin_1) / K1-Pad4 between x 58 and 80 south of y 24) are left out.
Usage: s3_k1check.py geo.json cx yc"""
import json, sys
from shapely.geometry import LineString, Polygon, Point, box
G = json.load(open(sys.argv[1])); cx, yc = float(sys.argv[2]), float(sys.argv[3])
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "/Q1_A1", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)",
         "unconnected-(U5-NC-Pad5)", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
def rer(net, g):
    b = g.bounds
    if net in ("+5V", "Net-(D5-A)") and b[1] < 56.5 and 58 < b[0] < 80: return True
    if net in ("LINE_FUSED", "Net-(J4-Pin_1)", "unconnected-(K1-Pad4)") and b[3] > 24 and 58 < b[0] < 80: return True
    return False
cu = []
for s in G["segs"]:
    g = LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2)
    if not rer(s[5], g): cu.append((g, s[5], "trk " + s[6]))
for p in G["pads"]:
    if p["ref"] in ("K1", "D6", "RV3") or len(p["pts"]) < 3: continue
    cu.append((Polygon(p["pts"]), p["net"], "pad %s.%s" % (p["ref"], p["num"])))
for v in G["vias"]:
    g = Point(v[0], v[1]).buffer(v[2] / 2)
    if not rer(v[3], g): cu.append((g, v[3], "via"))
def oval(x, y, w, h):
    r = min(w, h) / 2
    return LineString([(x - (w / 2 - r), y - (h / 2 - r)), (x + (w / 2 - r), y + (h / 2 - r))]).buffer(r)
coil = [oval(cx + dx, yc, 2.0, 3.0) for dx in (-3.75, 3.75)]
cont = [(oval(cx + dx, yc - dy, 3.0, 2.0), n) for dx in (-3.75, 3.75) for dy, n in ((20.3, "LINE_FUSED"), (25.34, "Net-(J4-Pin_1)"))]
def near(gs, pred, k=4):
    out = []
    for g0 in gs:
        for g, n, w in cu:
            if pred(n): out.append((round(g.distance(g0), 2), n, w))
    return sorted(set(out))[:k]
print("K1 local (%.2f, %.2f) = abs (%.2f, %.2f)" % (cx, yc, cx + 20, yc + 20))
print(" coil -> mains copper:", near(coil, lambda n: n in MAINS))
print(" contacts -> SELV copper:", near([g for g, n in cont], lambda n: n not in MAINS and n != ""))
for g0, net in cont:
    pass
print(" contacts -> other mains nets:", sorted(set((round(g.distance(g0), 2), n, w) for g0, net in cont for g, n, w in cu if n in MAINS and n != net))[:4])
crt = box(cx - 6.8, yc - 27.1, cx + 6.8, yc + 2.8)
ov = [(r, round(box(*c).intersection(crt).area, 2), round(box(*c).distance(crt), 2)) for r, c in G["crt"].items() if r not in ("K1", "D6", "RV3", "DS1") and box(*c).distance(crt) < 2.0]
print(" courtyards within 2 mm (ref, overlap mm2, gap):", ov)
LV = Polygon([(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
              (126.0, 54.8), (130.0, 55.5), (130.0, 40.0), (163.5, 40.0), (163.5, 98.5), (0.5, 98.5)])
print(" coil pads inside the present Cmts LV polygon:", [LV.contains(g) for g in coil], " contacts outside LV by:", [round(g.distance(LV), 2) for g, n in cont])
