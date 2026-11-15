"""23 - READ-ONLY (v2 script 46 adapted): body 'Frame GF' intersected with a box Z_PCB .. +50 (temporary BRep);
writes its volume, lumps and a dense point cloud of its boundary (vertices + edge strokes, abs KiCad x / y-down / Z)
to scratchpad above_z0.json. ../gf_offline_checks.py measures the 2D distance of that material to the KiCad board
outline (board_geom.json, ears included): if every point is > 1.0 mm outside the outline, the frame volume inside
'outline + 1 mm' above Z 0 is exactly 0 (the material above Z 0 consists of prisms whose boundary is sampled)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    tb = adsk.fusion.TemporaryBRepManager.get()
    a = tb.copy(L.body())
    obb = adsk.core.OrientedBoundingBox3D.create(adsk.core.Point3D.create(10.0, -8.0, 2.5),
                                                 adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                 30.0, 25.0, 5.0)          # cm: X -5..25, Y -20.5..4.5, Z 0..5
    box = tb.createBox(obb)
    tb.booleanOperation(a, box, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    pts = []
    for i in range(a.edges.count):
        e = a.edges.item(i)
        ev = e.evaluator
        ok, p0, p1 = ev.getParameterExtents()
        ok, st = ev.getStrokes(p0, p1, 0.0005)
        for p in (st if ok else [e.startVertex.geometry, e.endVertex.geometry]):
            pts.append([round(p.x * 10, 4), round(-p.y * 10, 4), round(p.z * 10, 4)])
    bb = a.boundingBox
    res = {"volume_mm3": round(a.volume * 1000, 4), "lumps": a.lumps.count, "faces": a.faces.count,
           "bbox_abs": [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3), round(-bb.maxPoint.y * 10, 3),
                        round(-bb.minPoint.y * 10, 3), round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)],
           "points": pts}
    p = L.dump(res, "above_z0.json")
    print(p, res["volume_mm3"], res["lumps"], res["faces"], res["bbox_abs"], len(pts))
