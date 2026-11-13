"""61 - FIX: in 58, editing the 'Stud FHn tube' distance expression flipped the extrude direction (tubes grew from
Z_STUD_TOP UP to +3.98, beside the board; found by the above-Z0 check: 11 lumps, and by the scan). Each tube is
redefined with setOneSideExtent(stud_boss_h + flange_t, NEGATIVE direction, taper 'draft' = growing toward the
front) at its own timeline position; the stud fillet made on the wrong tubes in 59b is deleted and re-made before
the first other fillet (its v2.1 position); the marker goes back to the end (the radial slots stay last).
Expects: 59b done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 61 start")
    tl = L.des().timeline
    f = L.feature("Root fillets R0.5 - stud tubes + ribs")
    f.timelineObject.rollTo(True)
    f.deleteMe()
    for name, side, xe, ye in L.STUDS:
        t = adsk.fusion.ExtrudeFeature.cast(L.feature("Stud %s tube" % name))
        t.timelineObject.rollTo(True)
        t.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("stud_boss_h + flange_t")),
                           adsk.fusion.ExtentDirections.NegativeExtentDirection, L.VI(L.grow()))
    first = L.feature("Root fillets R0.5 - PCB bosses on the walls")
    first.timelineObject.rollTo(True)
    ff, nf = L.fillet_set("stud tubes + ribs")
    tl.moveToEnd()
    nt, bad = L.timeline_health()
    t = adsk.fusion.ExtrudeFeature.cast(L.feature("Stud FH10 tube"))
    zr = (min(fc.boundingBox.minPoint.z for fc in t.faces) * 10, max(fc.boundingBox.maxPoint.z for fc in t.faces) * 10)
    L.log("61 tubes z %.3f..%.3f; stud fillet %d edges; %s; timeline %d unhealthy %s" % (zr[0], zr[1], nf,
                                                                                        L.body_stats(), nt, bad))
    L.show_iso()
    print(zr, nf, L.body_stats(), nt, bad)
