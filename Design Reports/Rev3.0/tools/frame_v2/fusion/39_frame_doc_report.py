"""39 - READ-ONLY report on the FRAME document while the assembly is active (no activation: the frame design is
read through app.documents -> products): timeline names + health, user parameters, body stats, data-file
version, faces at Z_PCB. Writes scratchpad/cad/frame_doc_report.json. Expects: both documents open."""
import importlib
import json
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    app = adsk.core.Application.get()
    fd = None
    for i in range(app.documents.count):
        d = app.documents.item(i)
        if d.name.startswith("Rev3.0 Frame v2") and "assembly" not in d.name:
            fd = d
    des = adsk.fusion.Design.cast(fd.products.itemByProductType("DesignProductType"))
    tl = des.timeline
    items, bad = [], []
    for i in range(tl.count):
        it = tl.item(i)
        items.append(it.name)
        if it.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            bad.append((i, it.name, it.errorOrWarningMessage))
    ups = des.userParameters
    params = []
    for i in range(ups.count):
        p = ups.item(i)
        val = p.value * 10.0 if p.unit == "mm" else (math.degrees(p.value) if p.unit == "deg" else p.value)
        params.append({"name": p.name, "expression": p.expression, "value": round(val, 6), "unit": p.unit or "",
                       "comment": p.comment})
    b = des.rootComponent.bRepBodies.item(0)
    bb = b.boundingBox
    z0 = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        fb = f.boundingBox
        if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType and abs(fb.minPoint.z) < 1e-6 \
                and abs(fb.maxPoint.z) < 1e-6:
            z0.append({"area_mm2": round(f.area * 100, 3), "bbox_abs": [round(fb.minPoint.x * 10, 3),
                       round(fb.maxPoint.x * 10, 3), round(-fb.maxPoint.y * 10, 3), round(-fb.minPoint.y * 10, 3)],
                       "loops": f.loops.count})
    df = fd.dataFile
    res = {"doc": fd.name, "is_modified": fd.isModified, "data_file_id": df.id if df else None,
           "version": df.versionNumber if df else None, "timeline_count": tl.count, "timeline_unhealthy": bad,
           "timeline": items, "params": params, "body": b.name, "volume_cm3": round(b.physicalProperties.volume, 4),
           "faces": b.faces.count, "bbox_model_mm": [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3),
                                                      round(bb.minPoint.y * 10, 3), round(bb.maxPoint.y * 10, 3),
                                                      round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)],
           "faces_at_Z_PCB": z0}
    json.dump(res, open(os.path.join(L.SCR, "frame_doc_report.json"), "w"), indent=1)
    print(res["doc"], res["version"], res["timeline_count"], bad, res["volume_cm3"], res["faces"], len(z0),
          fd.isModified)
