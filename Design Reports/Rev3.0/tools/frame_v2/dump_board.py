"""Dump the Rev3.0 board geometry the carrier frame needs (KiCad 10 Python, READ-ONLY).

It loads a temporary COPY of the .kicad_pcb, never the live file, and writes
out/board_geom.json with:
  * the Edge.Cuts outline (polygon, absolute mm, KiCad y-down) and the M3 holes H1..H9
  * every pad (position, size, shape polygon, layers, THT/SMD, net, mains flag)
  * mains copper on B.Cu (tracks/arcs/zone fills as polygons) - for the creepage check
  * DS1's Dwgs.User drawing (panel outline, view area, loops, finger zones)
  * per footprint: side, position, rotation, courtyard bbox

  "C:\Program Files\KiCad\10.0\bin\python.exe" dump_board.py [board.kicad_pcb] [out.json]
"""
import json, os, shutil, sys, tempfile
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.normpath(os.path.join(HERE, r"..\..\..\..\KiCad\3dFilamentDryer\3dFilamentDryer.kicad_pcb"))
src = sys.argv[1] if len(sys.argv) > 1 else BOARD
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out", "board_geom.json")
tmpd = tempfile.mkdtemp()
tmp = os.path.join(tmpd, "board_copy.kicad_pcb")
shutil.copyfile(src, tmp)
if os.path.exists(src[:-10] + ".kicad_pro"):
    shutil.copyfile(src[:-10] + ".kicad_pro", tmp[:-10] + ".kicad_pro")  # net classes live in the project file
b = pcbnew.LoadBoard(tmp)
M = pcbnew.ToMM


def poly_set_to_lists(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        out.append([[M(ol.CPoint(k).x), M(ol.CPoint(k).y)] for k in range(ol.PointCount())])
    return out


# Net classes come from the project file's netclass_patterns (pcbnew on a board copy does not
# resolve them reliably). Mains = class Mains / MainsHeater, plus the zero-cross pair.
import fnmatch
_PRO = src[:-10] + ".kicad_pro"
_PATTERNS = []
if os.path.exists(_PRO):
    _PATTERNS = [(p["pattern"], p["netclass"]) for p in
                 json.load(open(_PRO, encoding="utf8"))["net_settings"].get("netclass_patterns", [])]


def netclass_of(name):
    for pat, nc in _PATTERNS:
        if pat == name or fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(name.lstrip("/"), pat):
            return nc
    return ""


def netclass(item):
    return netclass_of(item.GetNetname())


def is_mains(item):
    n = item.GetNetname()
    return netclass_of(n).startswith("Mains") or "ZCD_L" in n or "ZCD_N" in n


# outline
ol = pcbnew.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(ol, False)
outline = []
for i in range(ol.OutlineCount()):
    o = ol.Outline(i)
    outline.append([[M(o.CPoint(k).x), M(o.CPoint(k).y)] for k in range(o.PointCount())])
    for h in range(ol.HoleCount(i)):
        hh = ol.Hole(i, h)
        outline.append([[M(hh.CPoint(k).x), M(hh.CPoint(k).y)] for k in range(hh.PointCount())])

pads, fps, ds1 = [], [], []
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    cbb = None
    if cy.OutlineCount():
        bb = cy.BBox()
        cbb = [M(bb.GetX()), M(bb.GetY()), M(bb.GetRight()), M(bb.GetBottom())]
    fps.append({"ref": fp.GetReference(), "fpid": fp.GetFPIDAsString(), "side": "B" if fp.IsFlipped() else "F",
                "x": M(fp.GetPosition().x), "y": M(fp.GetPosition().y), "rot": fp.GetOrientationDegrees(),
                "crtyd": cbb})
    for p in fp.Pads():
        sh = pcbnew.SHAPE_POLY_SET()
        lay = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
        p.TransformShapeToPolygon(sh, lay, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
        pads.append({"ref": fp.GetReference(), "num": p.GetNumber(), "x": M(p.GetPosition().x),
                     "y": M(p.GetPosition().y), "attr": {pcbnew.PAD_ATTRIB_PTH: "PTH", pcbnew.PAD_ATTRIB_NPTH: "NPTH",
                                                          pcbnew.PAD_ATTRIB_SMD: "SMD"}.get(p.GetAttribute(), "OTHER"),
                     "drill": M(p.GetDrillSize().x), "on_bcu": p.IsOnLayer(pcbnew.B_Cu),
                     "on_fcu": p.IsOnLayer(pcbnew.F_Cu), "net": p.GetNetname(), "netclass": netclass(p),
                     "mains": is_mains(p), "poly": poly_set_to_lists(sh)})
    if fp.GetReference() == "DS1":
        for g in fp.GraphicalItems():
            if g.GetLayer() not in (pcbnew.Dwgs_User, pcbnew.Cmts_User):
                continue
            try:
                sh = pcbnew.SHAPE_POLY_SET()
                g.TransformShapeToPolygon(sh, g.GetLayer(), 0, pcbnew.FromMM(0.01), pcbnew.ERROR_INSIDE)
                bb = g.GetBoundingBox()
                ds1.append({"layer": b.GetLayerName(g.GetLayer()), "cls": g.GetClass(),
                            "text": g.GetText() if hasattr(g, "GetText") else "",
                            "bbox": [M(bb.GetX()), M(bb.GetY()), M(bb.GetRight()), M(bb.GetBottom())]})
            except Exception as e:
                ds1.append({"err": str(e), "cls": g.GetClass()})

mains_b = []
for t in b.GetTracks():
    if t.GetLayer() != pcbnew.B_Cu and t.GetClass() != "PCB_VIA":
        continue
    if not is_mains(t):
        continue
    sh = pcbnew.SHAPE_POLY_SET()
    t.TransformShapeToPolygon(sh, pcbnew.B_Cu, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
    mains_b.append({"kind": t.GetClass(), "net": t.GetNetname(), "poly": poly_set_to_lists(sh)})
for z in b.Zones():
    if not z.IsOnLayer(pcbnew.B_Cu) or z.GetIsRuleArea():
        continue
    if not is_mains(z):
        continue
    fill = z.GetFilledPolysList(pcbnew.B_Cu)
    mains_b.append({"kind": "ZONE", "net": z.GetNetname(), "poly": poly_set_to_lists(fill)})

# all B.Cu copper extents near the edge (any net) for the rim contact check: tracks + zones bbox polys
bcu_zones = []
for z in b.Zones():
    if z.IsOnLayer(pcbnew.B_Cu) and not z.GetIsRuleArea():
        bcu_zones.append({"net": z.GetNetname(), "poly": poly_set_to_lists(z.GetFilledPolysList(pcbnew.B_Cu))})

ebb = b.GetBoardEdgesBoundingBox()
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump({"board": src, "edge_bbox": [M(ebb.GetX()), M(ebb.GetY()), M(ebb.GetRight()), M(ebb.GetBottom())],
           "thickness": M(b.GetDesignSettings().GetBoardThickness()), "outline": outline, "fps": fps,
           "pads": pads, "ds1_drawing": ds1, "mains_bcu": mains_b, "bcu_zones": bcu_zones}, open(dst, "w"))
shutil.rmtree(tmpd, ignore_errors=True)
print("wrote", dst, "fps", len(fps), "pads", len(pads), "mains B.Cu items", len(mains_b), "ds1 items", len(ds1))
