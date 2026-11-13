"""Geometry export for the refdes placement (KiCad 10 python).

python refdes_geom.py <board.kicad_pcb> <geom.json>

Writes, in absolute board mm:
  edge      board outline polygons (Edge.Cuts) and NPTH / PTH holes (centre, radius)
  (every polygon is [outline, hole, ...]: a library silk rectangle is a ring, not a filled area)
  fps       per footprint: reference, footprint id, position, orientation, courtyard outlines + bbox, pads as the
            F.Mask aperture polygons (pad shape grown by its solder-mask expansion), library F.SilkS items as ink
            polygons, F.Fab bbox, the current Reference field state
  silk      board-level F.SilkS items (texts and shapes) as ink polygons
  ink       ink bbox (stroke outline, relative to the text position, centre/centre justified) of every reference
            for every text style at 0 and 90 degrees
Footprint Reference fields are NOT obstacles (they are what gets placed); every other visible F.SilkS item is.
"""
import json
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labels_def  # noqa: E402

MAXERR = 1000          # 1 um polygon approximation error
STYLES = {             # name: (height, width, thickness) mm
    "S": (0.8, 0.7, 0.10),
    "C": (0.8, 0.6, 0.10),
    "L": (1.0, 1.0, 0.15),
}


def mm(v):
    return round(v / 1e6, 5)


def ring(ol):
    return [[mm(ol.CPoint(j).x), mm(ol.CPoint(j).y)] for j in range(ol.PointCount())]


def polys(ps):
    """[[outline, hole, hole, ...], ...] (closed rings, absolute mm)"""
    out = []
    for i in range(ps.OutlineCount()):
        out.append([ring(ps.Outline(i))] + [ring(ps.Hole(i, k)) for k in range(ps.HoleCount(i))])
    return out


def bbox(ps):
    b = ps.BBox()
    return [mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())]


def vbbox(rl):
    xs = [p[0] for rings in rl for p in rings[0]]
    ys = [p[1] for rings in rl for p in rings[0]]
    return [min(xs), min(ys), max(xs), max(ys)]


def item_poly(it, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    it.TransformShapeToPolygon(ps, layer, 0, MAXERR, pcbnew.ERROR_OUTSIDE)
    ps.Simplify()
    return ps


def text_ink(board, txt, style, ang):
    h, w, t = STYLES[style] if isinstance(style, str) else style
    x = pcbnew.PCB_TEXT(board)
    x.SetText(txt)
    x.SetLayer(pcbnew.F_SilkS)
    x.SetTextSize(pcbnew.VECTOR2I(int(round(w * 1e6)), int(round(h * 1e6))))
    x.SetTextThickness(int(round(t * 1e6)))
    x.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    x.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    x.SetPosition(pcbnew.VECTOR2I(0, 0))
    x.SetTextAngleDegrees(ang)
    return bbox(item_poly(x, pcbnew.F_SilkS))


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    out = {"edge": {}, "fps": [], "silk": [], "ink": {}}
    ps = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps, True)
    out["edge"]["outline"] = polys(ps)
    holes = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                d = p.GetDrillSize()
                holes.append([mm(p.GetPosition().x), mm(p.GetPosition().y), mm(max(d.x, d.y)) / 2, fp.GetReference()])
    out["edge"]["holes"] = holes
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if fp.IsFlipped():                      # DS1, the display on B.Cu: nothing on the front
            continue
        cy = pcbnew.SHAPE_POLY_SET(fp.GetCourtyard(pcbnew.F_CrtYd))
        rec = {"ref": ref, "fpid": fp.GetFPIDAsString(), "pos": [mm(fp.GetPosition().x), mm(fp.GetPosition().y)],
               "ang": round(fp.GetOrientationDegrees(), 3), "flipped": fp.IsFlipped()}
        rec["cy"] = polys(cy) if cy.OutlineCount() else []
        # bbox of the courtyard outline itself (SHAPE_POLY_SET.BBox() is 0.05 mm larger on every side)
        rec["cybb"] = vbbox(rec["cy"]) if cy.OutlineCount() else None
        pads = []
        for p in fp.Pads():
            if not p.IsOnLayer(pcbnew.F_Mask):
                continue
            pp = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(pp, pcbnew.F_Cu, p.GetSolderMaskExpansion(pcbnew.F_Mask), MAXERR,
                                      pcbnew.ERROR_OUTSIDE)
            pp.Simplify()
            pads.append({"num": p.GetNumber(), "poly": polys(pp), "bb": bbox(pp)})
        rec["pads"] = pads
        silk = []
        fab = None
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                if g.GetClass() in ("PCB_TEXT", "PCB_TEXTBOX") and not g.IsVisible():
                    continue
                silk.append(polys(item_poly(g, pcbnew.F_SilkS)))
            elif g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE":
                bb = g.GetBoundingBox()
                r = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
                fab = r if fab is None else [min(fab[0], r[0]), min(fab[1], r[1]), max(fab[2], r[2]), max(fab[3], r[3])]
        for f in fp.GetFields():                      # visible non-reference fields on the silk stay obstacles
            if f.GetName() != "Reference" and f.IsVisible() and f.GetLayer() == pcbnew.F_SilkS:
                silk.append(polys(item_poly(f, pcbnew.F_SilkS)))
        rec["silk"] = silk
        rec["fabbb"] = fab
        r = fp.Reference()
        rec["refnow"] = {"layer": b.GetLayerName(r.GetLayer()), "pos": [mm(r.GetPosition().x), mm(r.GetPosition().y)],
                         "ang": r.GetTextAngleDegrees(), "h": mm(r.GetTextHeight()), "w": mm(r.GetTextWidth()),
                         "t": mm(r.GetTextThickness()), "visible": r.IsVisible()}
        out["fps"].append(rec)
        out["ink"][ref] = {s: {str(a): text_ink(b, ref, s, a) for a in (0, 90)} for s in STYLES}
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS:
            out["silk"].append({"cls": d.GetClass(), "text": d.GetText() if d.GetClass() == "PCB_TEXT" else "",
                                "uuid": d.m_Uuid.AsString(), "poly": polys(item_poly(d, pcbnew.F_SilkS))})
    # F.Cu tracks (legibility only: the title / warning blocks stay off them; tented vias are not obstacles)
    trk = []
    for tr in b.GetTracks():
        if tr.GetClass() != "PCB_VIA" and tr.IsOnLayer(pcbnew.F_Cu):
            trk.extend(polys(item_poly(tr, pcbnew.F_Cu)))
    out["tracks"] = trk
    # Cmts.User mains-area outline (segments)
    out["mains_outline"] = [[[mm(d.GetStart().x), mm(d.GetStart().y)], [mm(d.GetEnd().x), mm(d.GetEnd().y)]]
                            for d in b.GetDrawings() if d.GetLayer() == pcbnew.Cmts_User and d.GetClass() == "PCB_SHAPE"]
    # ink boxes of the board legend
    li = {}
    for L in labels_def.LABELS:
        li[L["name"]] = text_ink(b, L["text"], L["size"], L["ang"])
    for B in labels_def.BLOCKS:
        for k, (txt, sz) in enumerate(B["lines"]):
            li["%s.%d" % (B["name"], k)] = text_ink(b, txt, sz, 0)
    out["label_ink"] = li
    out["styles"] = STYLES
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=None)
    print("footprints %d, board silk items %d, holes %d" % (len(out["fps"]), len(out["silk"]), len(holes)))


if __name__ == "__main__":
    main()
