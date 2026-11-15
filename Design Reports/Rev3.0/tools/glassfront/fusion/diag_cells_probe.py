"""diag (stage 2, Part A) - READ-ONLY: the 'Corner cells sketch' arcs / radial dimensions and the faces of body
'Frame GF' near the H6 / H7 boss-side cell corners (type, area, 2A/P, owner feature)."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    c = L.comp()
    sk = c.sketches.itemByName("Corner cells sketch")
    print("sketch", sk.name, "curves", sk.sketchCurves.count, "dims", sk.sketchDimensions.count)
    for i in range(sk.sketchCurves.sketchArcs.count):
        a = sk.sketchCurves.sketchArcs.item(i)
        g = a.geometry
        print(" arc %d centre abs (%.3f, %.3f) r %.3f" % (i, g.center.x * 10, -g.center.y * 10, g.radius * 10))
    for i in range(sk.sketchDimensions.count):
        d = sk.sketchDimensions.item(i)
        if d.objectType.endswith("SketchRadialDimension"):
            a = d.entity
            g = a.geometry
            print(" radial dim %d -> arc centre (%.3f, %.3f) expr %s" % (i, g.center.x * 10, -g.center.y * 10,
                                                                     d.parameter.expression))
    b = L.body()
    owners = L.face_owners()
    for i in range(b.faces.count):
        f = b.faces.item(i)
        cc = f.centroid
        x, y = cc.x * 10, -cc.y * 10
        for h in ("h6", "h7"):
            if math.hypot(x - L.P(h + "_x"), y - L.P(h + "_y")) < 7.5 and cc.z * 10 < 0.01:
                A = f.area * 100
                Pm = sum(f.edges.item(k).length for k in range(f.edges.count)) * 10
                bb = f.boundingBox
                print("%s face %d type %d area %.3f 2A/P %.3f cen (%.3f, %.3f, %.3f) z %.3f..%.3f owner %s" % (
                    h, i, f.geometry.surfaceType, A, 2 * A / Pm, x, y, cc.z * 10, bb.minPoint.z * 10,
                    bb.maxPoint.z * 10, owners.get(f.tempId)))
    tl = L.des().timeline
    for i in range(tl.count):
        it = tl.item(i)
        print(i, it.name, it.healthState, "rolledBack" if it.isRolledBack else "")
