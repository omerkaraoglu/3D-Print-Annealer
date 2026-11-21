"""Search the mains band for an RC1415U-size inductor (body D16.5 -> courtyard 17.5 x 17.5, pads D2.4 7.5 mm apart)."""
import json, math
from matplotlib.path import Path
G = json.load(open("geo.json")); F = json.load(open("pcb_fps.json"))
band = Path([(45.5,20.5),(45.5,55.5),(72,55.5),(72,58.8),(78,59.81),(78,76),(116,76),(116,74.8),(146,74.8),(150,75.5),(150,60),(183.5,60),(183.5,20.5)])
def seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(x1 + t * dx - px, y1 + t * dy - py)
def ok(cx, cy, half=8.75, ignore=(), allow_net=("Net-(Q1-A1)",)):
    box = (cx - half, cy - half, cx + half, cy + half)
    if not all(band.contains_point(p) for p in ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3]))): return None
    if box[1] < 21.0: return None
    for r, (x0, y0, x1, y1) in G["fps"].items():
        if r in ignore or r.startswith("DS") or (r.startswith("H") and r != "HS1"): continue
        m = 1.0 if r == "HS1" else 0.0
        if x0 - m < box[2] and x1 + m > box[0] and y0 - m < box[3] and y1 + m > box[1]: return None
    worst = 99
    for px in (cx - 3.75, cx + 3.75):
        for t in G["tracks"]:
            if t[5] in allow_net: continue
            worst = min(worst, seg_pt(px, cy, *t[:4]) - t[4] / 2 - 1.2)
        for r, f in F.items():
            if r in ignore: continue
            for p in f["pads"]:
                if p[1] in allow_net: continue
                worst = min(worst, math.hypot(p[2] - px, p[3] - cy) - max(p[4], p[5]) / 2 - 1.2)
    return worst
hits = []
x = 46
while x < 184:
    y = 21
    while y < 76:
        w = ok(x, y)
        if w is not None and w >= 2.5: hits.append((round(x, 1), round(y, 1), round(w, 2)))
        y += 0.5
    x += 0.5
print("sites (as the board is):", len(hits), hits[:20])
# with RV2 removed / D6 placed and RV3 placed: treat as blocked boxes
G["fps"]["D6new"] = [112.4, 29.55, 130.84, 35.45]; G["fps"]["RV3new"] = [50.0, 21.75, 66.0, 27.25]; G["fps"].pop("RV2", None)
hits2 = []
x = 46
while x < 184:
    y = 21
    while y < 76:
        w = ok(x, y)
        if w is not None and w >= 2.5: hits2.append((round(x, 1), round(y, 1), round(w, 2)))
        y += 0.5
    x += 0.5
print("sites with D6 + RV3:", len(hits2), hits2[:20])
print("\nwhat blocks (D6 + RV3 placed): sites when these parts are ignored")
for ign in (("C1", "RV1"), ("C40",), ("J4",), ("R3", "R5", "C4"), ("F1",), ("U5", "R4"), ("U1", "R6", "R7"), ("C1", "RV1", "C40"), ("RV3new", "J4")):
    hs = []
    x = 46
    while x < 184:
        y = 21
        while y < 76:
            w = ok(x, y, ignore=ign)
            if w is not None and w >= 2.5: hs.append((round(x, 1), round(y, 1), round(w, 2)))
            y += 0.5
        x += 0.5
    print(ign, len(hs), hs[:3], hs[-3:] if hs else "")
