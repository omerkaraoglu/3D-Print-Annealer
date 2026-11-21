"""Stage 2 - free-space notes for two stage-3 candidates (nothing is placed):
  x2  : 47 nF 275 Vac X2 film capacitor across the fan output (Net-(J4-Pin_1) to NEUT), body 13 x 5 (P10) or 18 x 5 (P15),
        THT pads 2.0 mm round; courtyard = body + 0.5 per side; pads >= 2.5 mm from other mains nets (house mains rule),
        >= 6.4 mm from SELV copper, body inside the Cmts mains band, clear of every courtyard and of the planned stage-3
        D6 / RV3 courtyards; K1 is ignored as an obstacle (being replaced) but reported.
  lug : M3 ring-lug earth-bond pad (copper dia 7.0, plated 3.2 hole, GND) in the LV corner at J20 / TH220: copper on both
        outer layers >= 0.2 mm from foreign copper, courtyard (dia 8.0 + lug tongue not modelled) clear of courtyards,
        outside the QUIET box, outside washer keep-outs, >= 6.4 mm from mains copper.
Usage: s2_free.py geo.json x2|lug"""
import json, sys, math
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree
G = json.load(open(sys.argv[1]))
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "/Q1_A1", "Net-(Q1-A2)", "Net-(Q1-G)",
         "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)",
         "unconnected-(U5-NC-Pad5)", "unconnected-(U1-Pad6)", "unconnected-(U5-NC-Pad3)", "unconnected-(HS1-Pad1)", "unconnected-(HS1-Pad2)"}
LV = Polygon([(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
              (126.0, 54.8), (130.0, 55.5), (130.0, 40.0), (163.5, 40.0), (163.5, 98.5), (0.5, 98.5)])
BAND = box(0.5, 0.5, 163.5, 98.5).difference(LV)
cu = []
for s in G["segs"]:
    cu.append((LineString([(s[0], s[1]), (s[2], s[3])]).buffer(s[4] / 2), s[5], s[6]))
for p in G["pads"]:
    if len(p["pts"]) > 2:
        for l in p["layers"]:
            if l in ("F.Cu", "B.Cu"): cu.append((Polygon(p["pts"]), p["net"], l))
for v in G["vias"]:
    cu.append((Point(v[0], v[1]).buffer(v[2] / 2), v[3], "via"))
T = STRtree([g for g, n, l in cu])
CRT = {r: box(*c) for r, c in G["crt"].items() if r not in ("D6", "RV3", "DS1")}
CRT["D6(stage3)"] = box(112.4 - 20, 29.55 - 20, 130.84 - 20, 35.45 - 20)
CRT["RV3(stage3)"] = box(30.0, 1.75, 46.0, 7.25)
mode = sys.argv[2]
if mode == "x2":
    res = []
    for L_, Wd, P in ((13.0, 5.0, 10.0), (18.0, 5.0, 15.0)):
        for rot in (0, 90):
            y = 1.0
            while y < 56:
                x = 26.0
                while x < 130:
                    hl, hw = (L_ / 2 + 0.5, Wd / 2 + 0.5) if rot == 0 else (Wd / 2 + 0.5, L_ / 2 + 0.5)
                    c = box(x - hl, y - hw, x + hl, y + hw)
                    if not BAND.buffer(1e-6).contains(c): x += 0.5; continue
                    hits = [r for r, g in CRT.items() if g.intersects(c) and g.intersection(c).area > 1e-6]
                    if [h for h in hits if h != "K1"]: x += 0.5; continue
                    pads = [((x - P / 2, y) if rot == 0 else (x, y - P / 2)), ((x + P / 2, y) if rot == 0 else (x, y + P / 2))]
                    ok = True; dmin = {}
                    for (px, py), net in zip(pads, ("Net-(J4-Pin_1)", "NEUT")):
                        pg = Point(px, py).buffer(1.0)
                        for i in T.query(pg.buffer(6.5)):
                            g, n, l = cu[i]
                            if n == net: continue
                            need = 2.5 if n in MAINS else 6.4
                            d = g.distance(pg)
                            if d < need: ok = False; break
                        if not ok: break
                        dmin[net] = round(min(cu[i][0].distance(pg) for i in T.query(pg.buffer(30)) if cu[i][1] == net), 2)
                    if ok:
                        res.append(dict(P=P, rot=rot, x=x, y=y, k1="K1" in hits, d_conn=dmin))
                    x += 0.5
                y += 0.5
    for P in (10.0, 15.0):
        r = [o for o in res if o["P"] == P]
        nk = [o for o in r if not o["k1"]]
        print("P%.0f: %d sites (%d not touching K1's present courtyard)" % (P, len(r), len(nk)))
        nk.sort(key=lambda o: o["d_conn"]["Net-(J4-Pin_1)"] + o["d_conn"]["NEUT"])
        for o in nk[:12]: print("   ", o)
    json.dump(res, open("s2/x2_sites.json", "w"))
else:
    QUIET = box(4.0, 77.5, 33.6, 87.5)
    res = []
    y = 60.0
    while y < 98.5:
        x = 0.5
        while x < 40:
            g = Point(x, y).buffer(3.5)
            crt = Point(x, y).buffer(4.0)
            if not box(0, 0, 164, 99).buffer(-0.5).contains(g): x += 0.25; continue
            if g.intersects(QUIET): x += 0.25; continue
            bad = False
            for i in T.query(g.buffer(6.5)):
                gg, n, l = cu[i]
                if n == "GND": continue
                if gg.distance(g) < (6.4 if n in MAINS else 0.2): bad = True; break
            hits = [r for r, c in CRT.items() if c.intersects(crt) and r not in ("H7", "H8")]
            if not bad and not hits:
                res.append((round(x, 2), round(y, 2)))
            x += 0.25
        y += 0.25
    print(len(res), res[:5], res[-5:])
    json.dump(res, open("s2/lug_sites.json", "w"))
