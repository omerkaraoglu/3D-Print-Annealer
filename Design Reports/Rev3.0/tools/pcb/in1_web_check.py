"""In1 (GND plane) anti-pad merging check: python.exe in1_web_check.py board.kicad_pcb [min_web]
Every non-GND via keeps its 0.6 mm pad on In1 and the GND zone keeps 0.25 mm clearance to it -> anti-pad 1.1 mm. Where two
anti-pads come closer than the zone minimum width (0.25 mm) the copper web between them is dropped and the plane gets a
slot under the via row (IPC-2221C 9.1.4.1, EMI rule 2). Reports merged groups (slots) with their extents and nets."""
import pcbnew, math, itertools, sys
b = pcbnew.LoadBoard(sys.argv[1]); minw = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
In1 = b.GetLayerID("In1.Cu"); clr = 0.25
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
pts = [(v.GetPosition().x / 1e6 - 20, v.GetPosition().y / 1e6 - 20, v.GetNetname(), v.GetWidth(In1) / 1e6) for v in vias]
def r(p): return p[3] / 2 + (clr if p[2] != "GND" else 0)
par = list(range(len(pts)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
bad = 0
for i, j in itertools.combinations(range(len(pts)), 2):
    a, c = pts[i], pts[j]
    if a[2] == "GND" and c[2] == "GND": continue
    d = math.hypot(a[0] - c[0], a[1] - c[1])
    if d > 3: continue
    if d - r(a) - r(c) < minw: par[f(i)] = f(j); bad += 1
groups = {}
for i in range(len(pts)): groups.setdefault(f(i), []).append(i)
chains = sorted([g for g in groups.values() if len(g) > 1], key=len, reverse=True)
print("via pairs with In1 web < %.2f mm: %d ; merged groups: %d ; vias involved: %d" % (minw, bad, len(chains), sum(len(g) for g in chains)))
for g in chains:
    xs = [pts[i][0] for i in g]; ys = [pts[i][1] for i in g]
    print("  %2d vias  x %.2f..%.2f  y %.2f..%.2f  nets %s" % (len(g), min(xs), max(xs), min(ys), max(ys), sorted(set(pts[i][2].split('/')[-1] for i in g))))
