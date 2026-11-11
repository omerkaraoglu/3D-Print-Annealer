"""Dump every footprint's position / rotation / side / courtyard outline(s) in local mm (KiCad python): dump_crt.py board.kicad_pcb out.json"""
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); out = {}
for f in b.GetFootprints():
    poly = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    crt = []
    for i in range(poly.OutlineCount()):
        o = poly.Outline(i); crt.append([[o.CPoint(k).x / 1e6 - 20, o.CPoint(k).y / 1e6 - 20] for k in range(o.PointCount())])
    p = f.GetPosition()
    out[f.GetReference()] = {"pos": [p.x / 1e6 - 20, p.y / 1e6 - 20], "rot": f.GetOrientationDegrees(), "side": "B" if f.IsFlipped() else "F", "crt": crt}
json.dump(out, open(sys.argv[2], "w")); print("courtyards", len(out), "->", sys.argv[2])
