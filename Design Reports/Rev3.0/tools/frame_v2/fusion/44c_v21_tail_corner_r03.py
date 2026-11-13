"""44c - v2.1 item 5: the two tail-pocket corners (shelf end <-> tail-pocket side face, Z_SEAT..Z_SHELF_BACK) at
R 0.3 ('Root fillets R0.3 - tail pocket shelf end'). Accept only if no face of the fillet reaches above
Z_SHELF_BACK + 0.01 (in v2.0 the R0.5 climbed 6 mm up the tail wall as a flap) and no material appears inside
the tail pocket above the shelf (probe grid); otherwise the feature is deleted again and the corners stay sharp.
Expects: 44b done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 44c start")
    f, n = L.fillet_set("tail pocket shelf end", radius="0.3 mm")
    zsb = L.P("Z_SHELF_BACK")
    zmax = max(f.faces.item(i).boundingBox.maxPoint.z * 10 for i in range(f.faces.count))
    # probe: inside the tail pocket, just off the side faces, above the shelf back
    b = L.body()
    IN = adsk.fusion.PointContainment.PointInsidePointContainment
    k = __import__("math").tan(__import__("math").radians(L.P("draft")))
    hits = 0
    for side, x0 in ((+1, L.P("tr_x0")), (-1, L.P("tr_x1"))):
        for z in (zsb + 0.2, zsb + 1.0, -0.5, 1.0, 3.0):
            xf = x0 - side * (z - L.P("Z_FRONT")) * k          # tail-pocket side face at height z
            for dx in (0.05, 0.15, 0.3):
                for y in (118.9, 119.1, 119.3, 119.6):
                    if b.pointContainment(adsk.core.Point3D.create((xf + side * dx) / 10, -y / 10, z / 10)) == IN:
                        hits += 1
    ok = zmax <= zsb + 0.01 and hits == 0
    if not ok:
        f.deleteMe()
    L.log("44c R0.3 tail corners: %d edges, fillet zmax %.3f (shelf back %.3f), pocket probe hits %d -> %s" % (
        n, zmax, zsb, hits, "KEPT" if ok else "DELETED (climbs)"))
    nt, bad = L.timeline_health()
    L.show_iso()
    print(n, round(zmax, 3), hits, "KEPT" if ok else "DELETED", L.body_stats(), nt, bad)
