"""77 - stage 4 (GF-2.0): the scan (76) found the 8 coring-groove walls at F1-F4 UNDRAFTED. Cause: 66 re-set the
profile of the two-sided cut 'Fastener tube coring F1-F4' and Fusion reset its side-two taper to 0 deg (side one
kept 'draft'). Restored exactly as 55: side one +Z 1 mm, taper grow (draft); side two core_depth, taper shrink
(-draft). Then health and the coring floor fillet edge count. (Pitfall noted in the README: after setting
ExtrudeFeature.profile on a two-sided extrude, re-apply setTwoSidesExtent.)"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    d = L.check_doc()
    L.log("=== 77 start")
    tl = d.timeline
    f = L.feature("Fastener tube coring F1-F4")
    v0 = L.body().volume
    f.timelineObject.rollTo(True)
    ok = f.setTwoSidesExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("1 mm")),
                             adsk.fusion.DistanceExtentDefinition.create(L.VI("core_depth")),
                             L.VI(L.grow()), L.VI(L.shrink()))
    tl.moveToEnd()
    d.computeAll()
    if not ok:
        raise RuntimeError("setTwoSidesExtent failed")
    f = L.feature("Fastener tube coring F1-F4")
    n, bad = L.timeline_health()
    fl = L.feature("Coring groove floor edges R core_floor_r")
    res = {"taper1": f.taperAngleOne.expression, "taper2": f.taperAngleTwo.expression, "timeline": n, "unhealthy": bad,
           "volume_before": round(v0, 5), "volume_after": round(L.body().volume, 5), "faces": L.body().faces.count,
           "core_fillet_faces": fl.faces.count}
    L.log("77 %s" % res)
    if bad:
        raise RuntimeError(bad)
    print(res)
