"""Stage 0: planar-order analysis of the U10 -> J10 RGB/sync fan-in for the two possible LDATA lane mappings."""
from handroute import Router
R = Router("geom_display.json", placed="rev3_placed_display.kicad_pcb")
# U10 perimeter order of the ribbon leaving the east side (north -> south): right column top->bottom (pin 96 -> 65),
# then bottom row east->west (64 -> 33), then left column bottom->top (32 -> 1)
perim = list(range(96, 64, -1)) + list(range(64, 32, -1)) + list(range(32, 0, -1))
# LDATA bit -> U10 pin
LD = {}
import re
s = open("rev3.net", encoding="utf-8").read()
for m in re.finditer(r'\(node\s+\(ref "U10"\)\s+\(pin "(\d+)"\)\s+\(pinfunction "LDATA(\d+)_\d+"\)', s):
    LD[int(m.group(2))] = int(m.group(1))
SYNC = {"PCLK": 45, "HSYNC": 44, "VSYNC": 43, "DE": 49}
# J10 pad x (pin 1 east) for each panel signal
JX = {}
for n, net, x, y in R.pads_of("J10"):
    if net.startswith("/Display/"): JX[net.split("/")[-1]] = x
def mapping(crossed):
    m = {}
    for b in range(8):
        m[LD[8 + b]] = "G%d" % b
        m[LD[16 + b]] = ("B%d" if crossed else "R%d") % b
        m[LD[b]] = ("R%d" if crossed else "B%d") % b
    for k, v in SYNC.items(): m[v] = k
    return m
def inversions(seq):
    return sum(1 for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] < seq[j])   # want x decreasing north->south
for crossed in (True, False):
    m = mapping(crossed)
    order = [m[p] for p in perim if p in m]
    xs = [JX[s] for s in order]
    inv = inversions(xs)
    # lines in a planar run (longest decreasing subsequence of J10 x along the ribbon)
    import bisect
    best = []; 
    for x in xs:
        k = bisect.bisect_left(best, -x)
        if k == len(best): best.append(-x)
        else: best[k] = -x
    print("crossed" if crossed else "uncrossed", "ribbon N->S:", " ".join(order))
    print("   pairwise crossings %d, largest planar subset %d of %d (=> %d lines must cross on B.Cu)" % (inv, len(best), len(xs), len(xs) - len(best)))
