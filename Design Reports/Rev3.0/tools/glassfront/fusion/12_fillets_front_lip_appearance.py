"""12 - front-side (A half) fillets + appearance:
  'Root fillets R0.5 - land to recess wall'  concave corner land / glass-recess wall (s ~0.33, under the 0.4 gap;
                                             the bead starts at s -0.9, the glass back is 1.0 above the land)
  'Root fillets lip_root_r - lip root'       R0.2 lip outer face / seat-ring top (master JSON / concept 4.4)
  'Lip top edges R0.3'                       both convex top edges of the lip, R lip_top_r (flat 0.37 remains)
  appearance 'Plastic - Matte (Black)' on body 'Frame GF' (black nylon, as v2).
Left SHARP on purpose (listed in the report): pip roots (pips 1.5 x 0.5 would be consumed), corner-pad roots and
seat-ring roots on the flange front (tape_margin 1.0 = FLAT flange face beyond the tape edges), the v2 tail-pocket
corners. Expects: 11 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 12 start")
    out = []
    f, k = L.fillet_set("land to recess wall")
    out.append(("land to recess wall", k))
    f, k = L.fillet_set("lip root", radius="lip_root_r")
    out.append(("lip root", k))
    b = L.body()
    zt = L.P("Z_GLASS_FRONT")
    es = []
    for i in range(b.faces.count):
        fc = b.faces.item(i)
        if fc.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        bb = fc.boundingBox
        if abs(bb.minPoint.z * 10 - zt) < 1e-4 and abs(bb.maxPoint.z * 10 - zt) < 1e-4:
            es += [fc.edges.item(j) for j in range(fc.edges.count)]
    if len(es) != 16:
        raise RuntimeError("lip top: expected 16 edges (2 loops x 8), found %d" % len(es))
    L.fillet_edges(es, "lip_top_r", "Lip top edges R0.3")
    out.append(("lip top", len(es)))
    L.set_appearance(b, "Plastic - Matte (Black)")
    n, bad = L.timeline_health()
    L.log("12 %s; %s; timeline %d unhealthy %s" % (out, L.body_stats(), n, bad))
    print(out, L.body_stats(), n, bad)
