"""JSON-level replica of in1_web_check.py (same radii/rule) with the source file of each via.
python web_json.py [files...]   (default: the four region files)  -> prints merged groups, tagged by file"""
import json, math, itertools, sys, os
SCR = os.path.dirname(os.path.abspath(__file__))
files = sys.argv[1:] or ["tracks_display.json", "tracks_signals.json", "tracks_power.json", "tracks_mains.json"]
pts = []
for f in files:
    for t in json.load(open(os.path.join(SCR, f))):
        if t["via"]: pts.append((t["x"] - 20, t["y"] - 20, t["net"], t["d"], f.replace("tracks_", "").replace(".json", "")))
def r(p): return p[3] / 2 + (0.25 if p[2] != "GND" else 0)
def groups(pts, minw=0.25):
    par = list(range(len(pts)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    bad = []
    for i, j in itertools.combinations(range(len(pts)), 2):
        a, c = pts[i], pts[j]
        if a[2] == "GND" and c[2] == "GND": continue
        d = math.hypot(a[0] - c[0], a[1] - c[1])
        if d > 3: continue
        if d - r(a) - r(c) < minw - 1e-9: par[f(i)] = f(j); bad.append((i, j, d))
    gs = {}
    for i in range(len(pts)): gs.setdefault(f(i), []).append(i)
    return sorted([g for g in gs.values() if len(g) > 1], key=len, reverse=True), bad
if __name__ == "__main__":
    ch, bad = groups(pts)
    print("pairs %d groups %d vias %d" % (len(bad), len(ch), sum(map(len, ch))))
    for g in ch:
        xs = [pts[i][0] for i in g]; ys = [pts[i][1] for i in g]
        print("  %2d vias x %.2f..%.2f y %.2f..%.2f %s %s" % (len(g), min(xs), max(xs), min(ys), max(ys),
              sorted(set(pts[i][4] for i in g)), sorted(set(pts[i][2].split('/')[-1] for i in g))))
        if "-v" in os.environ.get("WEBV", ""):
            for i in g: print("      %.3f %.3f %s %.1f %s" % pts[i])
