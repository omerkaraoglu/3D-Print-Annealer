"""C_rf step 1 - export the routed geometry of the CURRENT board to JSON (run with KiCad 10's python.exe, on a COPY).

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" c1_export_geom.py <copy-of-board.kicad_pcb> <out.json>

Exports: tracks (segments and arcs, with arc mid points), vias, pads (position, size, layers, net, polygon),
footprints (ref, value, position, side), zones with their FILLED polygons per layer (fractured outlines), the board
outline polygon, the stack-up. Nothing is written to the board. Coordinates in mm, KiCad page frame (the tools in
tools/pcb subtract the 20 mm page offset for "local" coordinates; this export keeps absolute page mm and stores
the offset in the JSON so every report number can be traced back to KiCad's own coordinates)."""
import pcbnew, json, sys, math

src, out = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
LAY = {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu", pcbnew.B_Cu: "B.Cu"}
mm = lambda v: v / 1e6


def poly_out(ps):
    res = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        pts = [(round(mm(o.CPoint(k).x), 4), round(mm(o.CPoint(k).y), 4)) for k in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            holes.append([(round(mm(hh.CPoint(k).x), 4), round(mm(hh.CPoint(k).y), 4)) for k in range(hh.PointCount())])
        res.append({"outline": pts, "holes": holes})
    return res


tracks, vias = [], []
for t in b.GetTracks():
    c = t.GetClass()
    if c == "PCB_VIA":
        lays = [LAY[l] for l in LAY if t.IsOnLayer(l)]
        vias.append({"net": t.GetNetname(), "x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y),
                     "d": mm(t.GetWidth(pcbnew.F_Cu)), "drill": mm(t.GetDrillValue()), "layers": lays,
                     "type": str(t.GetViaType())})
    elif c == "PCB_ARC":
        tracks.append({"kind": "arc", "net": t.GetNetname(), "layer": LAY.get(t.GetLayer(), "?"), "w": mm(t.GetWidth()),
                       "x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y), "xm": mm(t.GetMid().x), "ym": mm(t.GetMid().y),
                       "x2": mm(t.GetEnd().x), "y2": mm(t.GetEnd().y), "len": mm(t.GetLength())})
    else:
        tracks.append({"kind": "seg", "net": t.GetNetname(), "layer": LAY.get(t.GetLayer(), "?"), "w": mm(t.GetWidth()),
                       "x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y), "x2": mm(t.GetEnd().x), "y2": mm(t.GetEnd().y),
                       "len": mm(t.GetLength())})

pads, fps = [], []
for fp in b.GetFootprints():
    fps.append({"ref": fp.GetReference(), "value": fp.GetValue(), "x": mm(fp.GetPosition().x), "y": mm(fp.GetPosition().y),
                "side": "B" if fp.IsFlipped() else "F", "rot": fp.GetOrientationDegrees(), "fpid": fp.GetFPIDAsString()})
    for p in fp.Pads():
        lays = [LAY[l] for l in LAY if p.IsOnLayer(l)]
        ps = pcbnew.SHAPE_POLY_SET()
        lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        p.TransformShapeToPolygon(ps, lay, 0, pcbnew.FromMM(0.01), pcbnew.ERROR_INSIDE)
        pads.append({"ref": fp.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(), "x": mm(p.GetPosition().x),
                     "y": mm(p.GetPosition().y), "sx": mm(p.GetSizeX()), "sy": mm(p.GetSizeY()), "layers": lays,
                     "tht": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "drill": mm(p.GetDrillSizeX()),
                     "poly": poly_out(ps)[0]["outline"] if ps.OutlineCount() else []})

zones = []
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    entry = {"net": z.GetNetname(), "name": z.GetZoneName(), "priority": z.GetAssignedPriority(), "fills": {}}
    for l in LAY:
        if z.IsOnLayer(l):
            fp_ = z.GetFilledPolysList(l)
            entry["fills"][LAY[l]] = poly_out(fp_)
    zones.append(entry)

outline = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(outline, True)
ds = b.GetDesignSettings()
stack = []
try:
    for item in ds.GetStackupDescriptor().GetList():
        stack.append({"type": item.GetTypeName(), "layer": item.GetLayerName(), "thickness_mm": mm(item.GetThickness()),
                      "epsr": item.GetEpsilonR(), "lossT": item.GetLossTangent()})
except Exception as e:
    stack = [{"error": str(e)}]

json.dump({"source": src, "tracks": tracks, "vias": vias, "pads": pads, "footprints": fps, "zones": zones,
           "outline": poly_out(outline), "stackup": stack,
           "nets": [b.GetNetInfo().GetNetItem(i).GetNetname() for i in range(b.GetNetCount())]}, open(out, "w"))
print("tracks", len(tracks), "vias", len(vias), "pads", len(pads), "footprints", len(fps), "zones", len(zones))
