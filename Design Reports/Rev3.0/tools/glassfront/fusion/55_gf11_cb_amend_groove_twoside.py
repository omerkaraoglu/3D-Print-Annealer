"""55 - stage 3 (GF-1.1):
  (a) lead amendment to item 1: counterbore cb_w x cb_l = 7.2 x 8.8 (slot outline + 0.9 per side, so the dia-4 stud
      and not its 5.7 flange limits the travel); floor round cb_r 0.3 (with 7.2 the floor ring is 0.87 wide at F1-F4,
      so the upper end of the 0.2-0.3 range now leaves both the round strips (2A/P 0.36) and the floor (0.57) clear
      of the sliver rule); depths unchanged: F1-F4 cb_floor 1.6 (floor Z -11.82), F5-F8 cb_floor_mid 2.0
  (b) glass-4.0 fix: there the tube top lies 0.5 below the step-wall back and the F5-F8 blend (tube_sw_r 1.2) also
      rounds the tube-top / step-wall edge; the coring groove, cut only downwards from Z_TUBE_TOP, left that fillet
      material hanging over the groove (a -Z face = undercut). The groove cut is made TWO-SIDED: side one +Z by
      1.0 mm (1 deg widening upwards), side two -Z by core_depth (1 deg narrowing) - nothing can overhang it.
Then glass 2.0 / 1.1 / 4.0 / 3.0: health, root census, and -Z facing faces near the tube tops (overhang probe)."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def overhangs():
    """planar faces facing -Z within 9.5 of a fastener whose Z is above the counterbore floors (= over a groove)"""
    b = L.body()
    zmin = L.P("Z_SHEET_BACK") + L.P("cb_floor_mid") + 0.01
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if n.z > -0.9999:
            continue
        c = f.centroid
        if c.z * 10 < zmin:
            continue
        if min(math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) for k in range(1, 9)) < 9.5:
            out.append((round(c.x * 10, 2), round(-c.y * 10, 2), round(c.z * 10, 2), round(f.area * 100, 3)))
    return out


def run(_context: str):
    d = L.check_doc()
    L.log("=== 55 start")
    L.set_param("cb_w", "7.2 mm", "mm", "GF-1.1 (lead amendment): counterbore width at its opening = slot_w + 2 x 0.9")
    L.set_param("cb_l", "8.8 mm", "mm", "GF-1.1 (lead amendment): counterbore length at its opening = slot_l + 2 x 0.9")
    L.set_param("cb_r", "0.3 mm", "mm", "GF-1.1: counterbore floor edge round")
    tl = d.timeline
    f = L.feature("Fastener tube coring F1-F8")
    f.timelineObject.rollTo(True)
    ok = f.setTwoSidesExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("1 mm")),
                             adsk.fusion.DistanceExtentDefinition.create(L.VI("core_depth")),
                             L.VI(L.grow()), L.VI(L.shrink()))
    tl.moveToEnd()
    d.computeAll()
    if not ok:
        raise RuntimeError("setTwoSidesExtent failed")
    ups = d.userParameters
    out = []
    for g in ("2.0 mm", "1.1 mm", "4.0 mm", "3.0 mm"):
        ups.itemByName("glass_t").expression = g
        d.computeAll()
        n, bad = L.timeline_health()
        roots = {}
        for grp, e, m, z, o in L.root_edges(0.9):
            roots[grp] = roots.get(grp, 0) + 1
        out.append((g, "healthy" if not bad else bad, round(L.body().volume, 4), L.body().faces.count, roots,
                    "overhangs", overhangs()))
    if abs(L.P("glass_t") - 3.0) > 1e-9:
        raise RuntimeError("glass_t not restored")
    L.log("55 %s" % out)
    for r in out:
        print(r)
