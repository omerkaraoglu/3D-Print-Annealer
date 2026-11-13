"""Export the filled polygons of every copper zone (as saved, or after a refill with 'refill') to JSON, local mm.
Usage: fills_export.py board.kicad_pcb out.json [refill]"""
import sys, json, pcbnew
from common import O, mm
b = pcbnew.LoadBoard(sys.argv[1])
if 'refill' in sys.argv[3:]:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
out = []
for z in b.Zones():
    if z.GetIsRuleArea() or not z.GetNetname():
        continue
    for lay in z.GetLayerSet().Seq():
        fp = z.GetFilledPolysList(lay)
        polys = []
        for i in range(fp.OutlineCount()):
            rings = []
            for h in range(-1, fp.HoleCount(i)):
                ch = fp.Outline(i) if h < 0 else fp.Hole(i, h)
                rings.append([(mm(ch.CPoint(j).x) - O, mm(ch.CPoint(j).y) - O) for j in range(ch.PointCount())])
            polys.append(rings)
        out.append(dict(net=z.GetNetname(), name=z.GetZoneName(), layer=b.GetLayerName(lay), polys=polys))
json.dump(out, open(sys.argv[2], 'w'))
print(len(out), "zone layers")
