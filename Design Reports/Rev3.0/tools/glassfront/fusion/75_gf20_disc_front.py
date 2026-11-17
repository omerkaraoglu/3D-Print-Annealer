"""75 - stage 4 (GF-2.0), follow-up of 74: the all-edges rule W also rounded the 4 pad roots and the 8 seat-ring
root edges (sharp ON PURPOSE: tape margin). Reason: 'Land plate + step wall (back)' starts on the Z_FLANGE_FRONT
plane, its front face merges with the flange front (parting plane) and Fusion attributes that face to it.
FIX (no geometry change): the land plate + step wall solid starts 0.5 behind the flange front, at
Z_DISC_FRONT = Z_FLANGE_FRONT + 0.5 mm, with its outline offset to s_disc_front = s_ring_b - 0.5 tan(draft) there so
the step face stays the same plane; the 0.5 it no longer covers lies inside the (full) flange plate at every glass_t
(flange_t 2.5 / 2.6). New hidden plane 'Z_DISC_FRONT plane'; sketch 'Land plate + step wall (back) sketch' redefined,
dims s_ring_b -> s_disc_front, extent Z_STEPWALL_BACK - Z_DISC_FRONT. Expected: glass 3.0 volume 83.4496 cm3 and the
GF-1.1 census (pips 8, shelf back 2, pilots 18, pads 4, seat ring 8)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    d = L.check_doc()
    L.log("=== 75 start")
    ups = d.userParameters
    if ups.itemByName("Z_DISC_FRONT") is not None:
        raise RuntimeError("75 already applied")
    tl = d.timeline
    v0 = L.body().volume
    L.set_param("Z_DISC_FRONT", "Z_FLANGE_FRONT + 0.5 mm", "mm",
                "GF-2.0: front of the 'Land plate + step wall (back)' solid, 0.5 inside the full flange plate (so the "
                "parting-plane face belongs to the flange plate; no geometry change)")
    L.set_param("s_disc_front", "s_ring_b - ( Z_DISC_FRONT - Z_FLANGE_FRONT ) * tan(draft)", "mm",
                "GF-2.0: step-wall back outline (s) drawn on the Z_DISC_FRONT plane = the same 1 deg face as s_ring_b on "
                "the flange front")
    sk = L.comp().sketches.itemByName("Land plate + step wall (back) sketch")
    sk.timelineObject.rollTo(True)
    pl = L.offset_plane("Z_DISC_FRONT plane", "Z_DISC_FRONT")
    pl.isLightBulbOn = False
    if not sk.redefine(pl):
        raise RuntimeError("redefine")
    k = 0
    for j in range(sk.sketchDimensions.count):
        dm = sk.sketchDimensions.item(j)
        e = dm.parameter.expression
        if "s_ring_b" in e:
            dm.parameter.expression = e.replace("s_ring_b", "s_disc_front")
            k += 1
    if k != 8:
        raise RuntimeError("disc dims %d" % k)
    tl.moveToEnd()
    f = L.feature("Land plate + step wall (back)")
    f.timelineObject.rollTo(True)
    ok = f.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("Z_STEPWALL_BACK - Z_DISC_FRONT")),
                            adsk.fusion.ExtentDirections.PositiveExtentDirection, L.VI(L.shrink()))
    tl.moveToEnd()
    if not ok:
        raise RuntimeError("extent")
    d.computeAll()
    n, bad = L.timeline_health()
    roots = {}
    for g, e, m, z, o in L.root_edges(0.9):
        roots[g] = roots.get(g, 0) + 1
    res = {"dims": k, "timeline": n, "unhealthy": bad, "volume_before": round(v0, 5),
           "volume_after": round(L.body().volume, 5), "faces": L.body().faces.count, "roots": roots}
    L.dump(res, "gf20/75_disc_front.json")
    L.log("75 %s" % res)
    if bad:
        raise RuntimeError(bad)
    print(res)
