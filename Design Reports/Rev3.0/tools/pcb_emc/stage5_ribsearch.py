"""Stage 5 helper: is there a J5 position near the reservation where the B-side bare copper (dia 7.0 + 0.05 mask
clearance) also keeps the frame document's 1.0 mm from the support-rib contact faces (frame doc 1.2)?
Constraints per candidate centre (0.1 mm grid, local x 0..20, y 84..98):
  B copper dia 7.1 >= 1.0 mm from every rib; F courtyard dia 8.0 and B courtyard dia 7.5 clear of other courtyards;
  pad copper >= 0.25 mm from other-net copper on every layer (zones excluded: they clear themselves); >= 0.5 mm to the
  board edge; B copper not overlapping BP16's copper (landing pad kept intact); mains >= 6.4 mm (far, always true here).
    python stage5_ribsearch.py export.json frame_v2_params.json"""
import json
import math
import sys

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

X = json.load(open(sys.argv[1]))
FP = json.load(open(sys.argv[2], encoding="utf-8"))


def poly(pp):
    g = [Polygon(p, [h for h in hs if len(h) > 2]) for p, hs in pp if len(p) > 2]
    return unary_union([x if x.is_valid else x.buffer(0) for x in g]) if g else Polygon()


ribs = [box(r["x0"] - 20, r["y0"] - 20, r["x1"] - 20, r["y1"] - 20) for r in FP["support_ribs"]["per_rib"]]
cu = [(poly(c["poly"]), c) for c in X["cu"] if c["kind"] != "zone" and c["net"] != "GND" and c.get("ref") != "J5"]
cu = [(g, c) for g, c in cu if not g.is_empty and g.bounds[0] < 30 and g.bounds[1] > 70]
T = STRtree([g for g, c in cu])
crtF = [poly(v["F.CrtYd"]) for r, v in X["crt"].items() if r != "J5" and "F.CrtYd" in v]
crtB = [poly(v["B.CrtYd"]) for r, v in X["crt"].items() if r != "J5" and "B.CrtYd" in v]
bp16 = unary_union([poly(c["poly"]) for c in X["cu"] if c.get("ref") == "BP16"])
edge = unary_union([poly([e]) for e in X["edge"]])
ok = []
y = 84.0
while y <= 98.0:
    x = 0.0
    while x <= 20.0:
        c = Point(x, y)
        pad = c.buffer(3.5)
        good = min(r.distance(c.buffer(3.55)) for r in ribs) >= 1.0
        good = good and edge.distance(pad) >= 0.5 and not any(g.intersects(c.buffer(4.0)) for g in crtF)
        good = good and not any(g.intersects(c.buffer(3.75)) for g in crtB) and not bp16.intersects(pad)
        if good:
            for i in T.query(pad.buffer(0.25)):
                if cu[i][0].distance(pad) < 0.25:
                    good = False
                    break
        if good:
            ok.append((round(math.dist((x, y), (7.0, 92.5)), 2), round(x, 2), round(y, 2)))
        x += 0.1
    y += 0.1
ok.sort()
print("candidates:", len(ok), "nearest to the reservation (7.0, 92.5):", ok[:8])
