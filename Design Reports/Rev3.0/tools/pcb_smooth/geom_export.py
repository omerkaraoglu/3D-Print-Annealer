"""Export copper / courtyard / fab / edge geometry of a board as JSON (local mm) for the shapely checkers.
Usage: geom_export.py board.kicad_pcb out.json"""
import sys, json, pcbnew
from common import O, mm
b = pcbnew.LoadBoard(sys.argv[1])
MAINS = {"LINE", "LINE_FUSED", "LINE_FILT", "Net-(Q1-A1)", "Net-(Q1-A2)", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)",
         "Net-(Q1-G)", "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N", "unconnected-(K1-Pad4)",
         "unconnected-(U1-NC-Pad3)", "unconnected-(U5-NC-Pad5)"}
def polys(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ol = sps.Outline(i); out.append([(mm(ol.CPoint(j).x) - O, mm(ol.CPoint(j).y) - O) for j in range(ol.PointCount())])
    return out
def shp(item, layer, clr=0):
    s = pcbnew.SHAPE_POLY_SET(); item.TransformShapeToPolygon(s, layer, pcbnew.FromMM(clr), pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE); return polys(s)
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
G = dict(pads=[], tracks=[], fps={}, edges=[], mains=sorted(MAINS))
for fp in b.GetFootprints():
    ref = fp.GetReference(); rec = dict(side='F' if fp.GetLayer() == pcbnew.F_Cu else 'B', pos=[mm(fp.GetPosition().x) - O, mm(fp.GetPosition().y) - O],
                                        crt=polys(fp.GetCourtyard(pcbnew.F_CrtYd)), mains=False, fab=[])
    for p in fp.Pads():
        lays = [b.GetLayerName(l) for l in CU if p.IsOnLayer(l)]
        if p.GetNetname() in MAINS: rec['mains'] = True
        G['pads'].append(dict(ref=ref, num=p.GetNumber(), net=p.GetNetname(), layers=lays, x=mm(p.GetPosition().x) - O, y=mm(p.GetPosition().y) - O,
                              drill=mm(p.GetDrillSize().x), poly=shp(p, pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)))
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == 'PCB_SHAPE':
            rec['fab'] += shp(g, pcbnew.F_Fab)
    G['fps'][ref] = rec
for t in b.GetTracks():
    lays = [b.GetLayerName(l) for l in CU if t.IsOnLayer(l)]
    G['tracks'].append(dict(cls=t.GetClass(), net=t.GetNetname(), layers=lays, w=mm(t.GetWidth(pcbnew.F_Cu) if t.GetClass() == 'PCB_VIA' else t.GetWidth()),
                            s=[mm(t.GetStart().x) - O, mm(t.GetStart().y) - O], e=[mm(t.GetEnd().x) - O, mm(t.GetEnd().y) - O],
                            poly=shp(t, t.GetLayer() if t.GetClass() != 'PCB_VIA' else pcbnew.F_Cu)))
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        G['edges'] += shp(d, pcbnew.Edge_Cuts)
G['rules'] = []
for z in b.Zones():
    if not z.GetIsRuleArea():
        continue
    G['rules'].append(dict(name=z.GetZoneName(), layers=[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],
                           no_vias=bool(z.GetDoNotAllowVias()), no_tracks=bool(z.GetDoNotAllowTracks()),
                           no_pour=bool(z.GetDoNotAllowZoneFills()), poly=polys(z.Outline())))
G['fills'] = []
for z in b.Zones():
    if z.GetIsRuleArea() or not z.GetNetname():
        continue
    for lay in z.GetLayerSet().Seq():
        fp = z.GetFilledPolysList(lay)
        rings = []
        for i in range(fp.OutlineCount()):
            r = [[(mm(fp.Outline(i).CPoint(j).x) - O, mm(fp.Outline(i).CPoint(j).y) - O) for j in range(fp.Outline(i).PointCount())]]
            for h in range(fp.HoleCount(i)):
                ch = fp.Hole(i, h); r.append([(mm(ch.CPoint(j).x) - O, mm(ch.CPoint(j).y) - O) for j in range(ch.PointCount())])
            rings.append(r)
        G['fills'].append(dict(net=z.GetNetname(), name=z.GetZoneName(), teardrop=bool(z.IsTeardropArea()), layer=b.GetLayerName(lay), polys=rings))
json.dump(G, open(sys.argv[2], 'w'))
print("pads", len(G['pads']), "tracks", len(G['tracks']), "fps", len(G['fps']))
