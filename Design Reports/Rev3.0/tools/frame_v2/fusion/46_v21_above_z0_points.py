"""46 - READ-ONLY (item 3 verification, part 1): the frame body intersected with a box Z_PCB .. +50 (temporary
BRep); writes its volume, solids and a dense point cloud of its boundary (vertices + edge samples, abs KiCad
x / y-down / Z) to scratchpad/cad/above_z0.json. above_z0_check.py then measures the 2D distance of that material
to the PCB outline polygon: if every point is > 1.0 mm outside the outline, the volume inside 'outline + 1 mm'
above Z 0 is exactly 0. Expects: 44b-d done."""
import importlib
import json
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    tb = adsk.fusion.TemporaryBRepManager.get()
    a = tb.copy(L.body())
    obb = adsk.core.OrientedBoundingBox3D.create(adsk.core.Point3D.create(10.0, -8.5, 2.5),
                                                 adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                 30.0, 25.0, 5.0)        # cm: X 0..30, Y -21..4, Z 0..5 (= 0..50 mm)
    box = tb.createBox(obb)
    tb.booleanOperation(a, box, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    pts = []
    for i in range(a.edges.count):
        e = a.edges.item(i)
        ev = e.evaluator
        ok, p0, p1 = ev.getParameterExtents()
        pts.append([e.startVertex.geometry.x * 10, -e.startVertex.geometry.y * 10, e.startVertex.geometry.z * 10])
        for t in range(1, 40):
            ok, p = ev.getPointAtParameter(p0 + (p1 - p0) * t / 40.0)
            if ok:
                pts.append([p.x * 10, -p.y * 10, p.z * 10])
    bb = a.boundingBox
    res = {"volume_mm3": round(a.volume * 1000, 4), "lumps": a.lumps.count, "faces": a.faces.count,
           "bbox_abs": [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3), round(-bb.maxPoint.y * 10, 3),
                        round(-bb.minPoint.y * 10, 3), round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)],
           "points": [[round(v, 4) for v in p] for p in pts]}
    json.dump(res, open(os.path.join(L.SCR, "above_z0.json"), "w"))
    print(res["volume_mm3"], res["lumps"], res["faces"], res["bbox_abs"], len(pts))
