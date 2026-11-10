"""Dump board geometry (pads, keep-outs, edge, existing tracks) to JSON for the external router."""
import pcbnew, json, sys, math
src = sys.argv[1]; out = sys.argv[2]
b = pcbnew.LoadBoard(src)
LAYERS = {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B", pcbnew.In1_Cu: "I1", pcbnew.In2_Cu: "I2"}
def mm(v): return v / 1e6
pads = []
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        layers = [LAYERS[l] for l in LAYERS if p.IsOnLayer(l)]
        sh = p.GetShape()
        poly = pcbnew.SHAPE_POLY_SET()
        p.TransformShapeToPolygon(poly, pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu, 0, pcbnew.FromMM(0.01), pcbnew.ERROR_INSIDE)
        pts = []
        if poly.OutlineCount():
            o = poly.Outline(0)
            for i in range(o.PointCount()):
                v = o.CPoint(i); pts.append((mm(v.x), mm(v.y)))
        pads.append({"ref": ref, "num": p.GetNumber(), "net": p.GetNetname(), "x": mm(p.GetPosition().x), "y": mm(p.GetPosition().y),
                     "layers": layers, "tht": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "npth": p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                     "drill": mm(p.GetDrillSizeX()), "poly": pts, "w": mm(p.GetSizeX()), "h": mm(p.GetSizeY())})
zones = []
for z in b.Zones():
    pts = []
    o = z.Outline().Outline(0)
    for i in range(o.PointCount()):
        v = o.CPoint(i); pts.append((mm(v.x), mm(v.y)))
    zones.append({"name": z.GetZoneName(), "net": z.GetNetname(), "layers": [LAYERS[l] for l in LAYERS if z.IsOnLayer(l)],
                  "keepout": z.GetIsRuleArea(), "no_tracks": z.GetDoNotAllowTracks(), "no_vias": z.GetDoNotAllowVias(), "poly": pts})
edges = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        edges.append([mm(d.GetStart().x), mm(d.GetStart().y), mm(d.GetEnd().x), mm(d.GetEnd().y)])
tracks = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        tracks.append({"via": True, "net": t.GetNetname(), "x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y), "d": mm(t.GetWidth())})
    else:
        tracks.append({"via": False, "net": t.GetNetname(), "layer": LAYERS.get(t.GetLayer(), "?"), "x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y),
                       "x2": mm(t.GetEnd().x), "y2": mm(t.GetEnd().y), "w": mm(t.GetWidth())})
nets = [b.GetNetInfo().GetNetItem(i).GetNetname() for i in range(b.GetNetCount())]
json.dump({"pads": pads, "zones": zones, "edges": edges, "tracks": tracks, "nets": nets}, open(out, "w"))
print("exported", len(pads), "pads", len(zones), "zones", len(edges), "edges", len(tracks), "tracks")
