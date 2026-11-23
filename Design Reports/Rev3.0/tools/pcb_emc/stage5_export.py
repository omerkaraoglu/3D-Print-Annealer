"""Stage 5 check, part 1 (KiCad python): export of everything the J5 checks need, local mm.
  - copper of every net on every copper layer (pads as effective polygons, tracks / arcs / vias as polygons, zone fills)
    with net, net class and layer; holes (centre, radius); mask openings (F / B) of pads; silk polygons (F / B);
    courtyards; board outline
  - the J5 pad, reference and earth-mark geometry
Usage: stage5_export.py board.kicad_pcb out.json"""
import json
import sys

import pcbnew

O = 20.0
b = pcbnew.LoadBoard(sys.argv[1])
CU = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}
ERR = pcbnew.FromMM(0.005)


def polys(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ring = sps.Outline(i)
        pts = [(pcbnew.ToMM(ring.CPoint(k).x) - O, pcbnew.ToMM(ring.CPoint(k).y) - O) for k in range(ring.PointCount())]
        holes = []
        for h in range(sps.HoleCount(i)):
            hr = sps.Hole(i, h)
            holes.append([(pcbnew.ToMM(hr.CPoint(k).x) - O, pcbnew.ToMM(hr.CPoint(k).y) - O) for k in range(hr.PointCount())])
        out.append([pts, holes])
    return out


def item_poly(it, lay, clr=0):
    s = pcbnew.SHAPE_POLY_SET()
    it.TransformShapeToPolygon(s, lay, clr, ERR, pcbnew.ERROR_INSIDE)
    return polys(s)


out = {"cu": [], "holes": [], "mask": [], "silk": [], "crt": {}, "edge": []}
for t in b.GetTracks():
    for ln, lay in CU.items():
        if t.IsOnLayer(lay):
            out["cu"].append(dict(kind=t.GetClass(), net=t.GetNetname(), nc=t.GetNetClassName(), layer=ln, poly=item_poly(t, lay)))
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        out["holes"].append([pcbnew.ToMM(p.x) - O, pcbnew.ToMM(p.y) - O, pcbnew.ToMM(t.GetDrillValue()) / 2, "via " + t.GetNetname()])
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        for ln, lay in CU.items():
            if p.IsOnLayer(lay) and p.FlashLayer(lay):
                out["cu"].append(dict(kind="pad", ref=ref, num=p.GetNumber(), net=p.GetNetname(), nc=p.GetNetClassName(),
                                      layer=ln, poly=item_poly(p, lay)))
        if p.HasHole():
            q = p.GetPosition()
            out["holes"].append([pcbnew.ToMM(q.x) - O, pcbnew.ToMM(q.y) - O, pcbnew.ToMM(p.GetDrillSize().x) / 2, "pad %s.%s" % (ref, p.GetNumber())])
        for ln, lay in (("F.Mask", pcbnew.F_Mask), ("B.Mask", pcbnew.B_Mask)):
            if p.IsOnLayer(lay):
                out["mask"].append(dict(ref=ref, num=p.GetNumber(), layer=ln, poly=item_poly(p, lay, p.GetSolderMaskExpansion(lay))))
    for it in fp.GraphicalItems():                 # mask openings drawn in the footprint (J5's back opening)
        for ln, lay in (("F.Mask", pcbnew.F_Mask), ("B.Mask", pcbnew.B_Mask)):
            if it.GetLayer() == lay:
                s = pcbnew.SHAPE_POLY_SET()
                it.TransformShapeToPolygon(s, lay, 0, ERR, pcbnew.ERROR_INSIDE)
                out["mask"].append(dict(ref=ref, num="gfx", layer=ln, poly=polys(s)))
    for ln, lay in (("F.CrtYd", pcbnew.F_CrtYd), ("B.CrtYd", pcbnew.B_CrtYd)):
        c = fp.GetCourtyard(lay)
        if c.OutlineCount():
            out["crt"].setdefault(ref, {})[ln] = polys(c)
    for it in list(fp.GraphicalItems()) + [fp.Reference(), fp.Value()]:
        for ln, lay in (("F.SilkS", pcbnew.F_SilkS), ("B.SilkS", pcbnew.B_SilkS)):
            if it.GetLayer() == lay and (not hasattr(it, "IsVisible") or it.IsVisible()):
                s = pcbnew.SHAPE_POLY_SET()
                it.TransformShapeToPolygon(s, lay, 0, ERR, pcbnew.ERROR_INSIDE)
                out["silk"].append(dict(ref=ref, what=it.GetClass() + (":" + it.GetText() if hasattr(it, "GetText") else ""), layer=ln, poly=polys(s)))
for it in b.GetDrawings():
    for ln, lay in (("F.SilkS", pcbnew.F_SilkS), ("B.SilkS", pcbnew.B_SilkS)):
        if it.GetLayer() == lay:
            s = pcbnew.SHAPE_POLY_SET()
            it.TransformShapeToPolygon(s, lay, 0, ERR, pcbnew.ERROR_INSIDE)
            out["silk"].append(dict(ref="", what=it.GetClass() + (":" + it.GetText() if hasattr(it, "GetText") else ""), layer=ln, poly=polys(s)))
    if it.GetLayer() == pcbnew.Edge_Cuts:
        s = pcbnew.SHAPE_POLY_SET()
        it.TransformShapeToPolygon(s, pcbnew.Edge_Cuts, 0, ERR, pcbnew.ERROR_INSIDE)
        out["edge"] += polys(s)
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for ln, lay in CU.items():
        if z.IsOnLayer(lay) and z.HasFilledPolysForLayer(lay):
            out["cu"].append(dict(kind="zone", name=z.GetZoneName(), net=z.GetNetname(), nc=z.GetNetClassName(), layer=ln,
                                  teardrop=z.IsTeardropArea(), poly=polys(z.GetFilledPolysList(lay))))
j5 = b.FindFootprintByReference("J5")
if j5:
    p = j5.Pads()[0]
    out["j5"] = dict(pos=[pcbnew.ToMM(j5.GetPosition().x) - O, pcbnew.ToMM(j5.GetPosition().y) - O],
                     layer=b.GetLayerName(j5.GetLayer()), net=p.GetNetname(), zone_connect=int(p.GetLocalZoneConnection()),
                     size=pcbnew.ToMM(p.GetSize(pcbnew.F_Cu).x), drill=pcbnew.ToMM(p.GetDrillSize().x),
                     mask_exp_F=pcbnew.ToMM(p.GetSolderMaskExpansion(pcbnew.F_Mask)),
                     ref_pos=[pcbnew.ToMM(j5.Reference().GetPosition().x) - O, pcbnew.ToMM(j5.Reference().GetPosition().y) - O],
                     attrs=j5.GetAttributes(), fpid=j5.GetFPIDAsString(), value=j5.GetValue())
json.dump(out, open(sys.argv[2], "w"))
print("cu items", len(out["cu"]), "holes", len(out["holes"]), "silk", len(out["silk"]), "J5", out.get("j5"))
