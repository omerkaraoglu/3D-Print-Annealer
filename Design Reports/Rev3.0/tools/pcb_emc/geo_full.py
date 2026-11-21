"""Export copper geometry (local mm) for the placement searches: tracks/arcs as segment chains, vias, pads (polygon),
courtyards, zones' net/layer bboxes.  Usage: geo_full.py board out.json"""
import pcbnew, sys, json, math
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
out = {"segs": [], "vias": [], "pads": [], "crt": {}}
for t in b.Tracks():
    c = t.GetClass(); net = t.GetNetname()
    if c == "PCB_VIA":
        out["vias"].append([*L(t.GetPosition()), mm(t.GetWidth(pcbnew.F_Cu)), net])
    elif c == "PCB_ARC":
        s, m, e = L(t.GetStart()), L(t.GetMid()), L(t.GetEnd()); cc = L(t.GetCenter()); r = math.hypot(s[0]-cc[0], s[1]-cc[1])
        a0 = math.atan2(s[1]-cc[1], s[0]-cc[0]); a1 = math.atan2(e[1]-cc[1], e[0]-cc[0]); am = math.atan2(m[1]-cc[1], m[0]-cc[0])
        # choose sweep through mid
        def norm(x): return (x + 2*math.pi) % (2*math.pi)
        sw = norm(a1 - a0)
        if not (norm(am - a0) < sw): sw = sw - 2*math.pi
        pts = [(cc[0] + r*math.cos(a0 + sw*k/8), cc[1] + r*math.sin(a0 + sw*k/8)) for k in range(9)]
        for p, q in zip(pts, pts[1:]):
            out["segs"].append([p[0], p[1], q[0], q[1], mm(t.GetWidth()), net, t.GetLayerName()])
    else:
        s, e = L(t.GetStart()), L(t.GetEnd())
        out["segs"].append([s[0], s[1], e[0], e[1], mm(t.GetWidth()), net, t.GetLayerName()])
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox(); out["crt"][fp.GetReference()] = [mm(bb.GetLeft())-20, mm(bb.GetTop())-20, mm(bb.GetRight())-20, mm(bb.GetBottom())-20]
    for p in fp.Pads():
        poly = p.GetEffectivePolygon(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
        o = poly.Outline(0)
        pts = [L(o.CPoint(i)) for i in range(o.PointCount())]
        layers = [ln for ln in ("F.Cu", "B.Cu", "In1.Cu", "In2.Cu") if p.IsOnLayer(b.GetLayerID(ln))]
        out["pads"].append(dict(ref=fp.GetReference(), num=p.GetNumber(), net=p.GetNetname(), pts=pts, layers=layers, pos=L(p.GetPosition())))
json.dump(out, open(sys.argv[2], "w"))
print(len(out["segs"]), len(out["vias"]), len(out["pads"]))
