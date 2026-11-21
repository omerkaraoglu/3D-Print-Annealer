"""Check candidate placements: courtyard box vs other courtyards (>= 0 overlap -> conflict), pads vs foreign-net copper
(tracks and pads, edge-to-edge) >= clearance."""
import json, math
G = json.load(open("geo.json")); F = json.load(open("pcb_fps.json"))
def seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)
def check(name, box, pads, ignore_refs=(), clr=2.5):
    print("==", name, "courtyard", [round(v, 2) for v in box])
    for r, (x0, y0, x1, y1) in G["fps"].items():
        if r in ignore_refs or r.startswith("DS") or (r.startswith("H") and r != "HS1"): continue
        if x0 < box[2] and x1 > box[0] and y0 < box[3] and y1 > box[1]:
            print("   courtyard overlap with", r)
    for (px, py, rad, net) in pads:
        worst = (99, None)
        for t in G["tracks"]:
            if t[5] == net: continue
            d = seg_pt(px, py, *t[:4]) - t[4] / 2 - rad
            if d < worst[0]: worst = (d, "track %s %s" % (t[5], t[6]))
        for r, f in F.items():
            if r in ignore_refs: continue
            for p in f["pads"]:
                if p[1] == net: continue
                d = math.hypot(p[2] - px, p[3] - py) - max(p[4], p[5]) / 2 - rad
                if d < worst[0]: worst = (d, "pad %s.%s %s" % (r, p[0], p[1]))
        print("   pad %s at (%.2f, %.2f): nearest foreign copper %.2f mm (%s) -> %s" % (net, px, py, worst[0], worst[1], "OK" if worst[0] >= clr else "VIOLATION < %.1f" % clr))
# D6 1.5KE440CA DO-201AD horizontal P15.24 (pads 2.6 mm? KiCad: see footprint), body 9.5 x 5.3 -> courtyard ~ 18.4 x 5.9
check("D6 at RV2's place, P15.24 horizontal", (116.75 - 1.6, 32.5 - 2.95, 131.99 + 1.6, 32.5 + 2.95),
      [(116.75, 32.5, 1.6, "LINE_FILT"), (131.99, 32.5, 1.6, "Net-(Q1-A1)")], ignore_refs=("RV2",))
# RV3 TVR14431 RV_Disc_D15.5mm_W5mm_P7.5mm (as RV1), standing, top-left strip above C40
check("RV3 top-left strip", (50.25 - 0.25, 22.0 - 0.25, 65.75 + 0.25, 27.0 + 0.25),
      [(54.25, 24.5, 0.9, "NEUT"), (61.75, 24.5, 0.9, "LINE_FUSED")])
# C9 0402 at U6 pin 2, C5 moved to U6 pin 5
check("C9 at U6 pin2 (0402, rot 0)", (138.5 - 0.95, 82.6 - 0.5, 139.5 + 0.95, 82.6 + 0.5),
      [(138.52, 82.6, 0.3, "Net-(R8-Pad2)"), (139.48, 82.6, 0.3, "GND")], clr=0.2)
check("C5 moved to U6 pin5 (0402, rot 0)", (143.12 - 0.95, 78.6 - 0.5, 144.08 + 0.95, 78.6 + 0.5),
      [(143.12, 78.6, 0.3, "+3V3"), (144.08, 78.6, 0.3, "GND")], ignore_refs=("C5",), clr=0.2)
print("\n#### D6 alternatives")
for x1, pitch in ((114.0, 15.24), (115.0, 15.24), (116.75, 12.7), (115.5, 12.7), (117.5, 12.7)):
    check("D6 pad1 x %.2f pitch %.2f" % (x1, pitch), (x1 - 1.6, 32.5 - 2.95, x1 + pitch + 1.6, 32.5 + 2.95),
          [(x1, 32.5, 1.6, "LINE_FILT"), (x1 + pitch, 32.5, 1.6, "Net-(Q1-A1)")], ignore_refs=("RV2",))
