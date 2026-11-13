"""44d - retry of 44c with a TIGHT climb test: 44c judged by the fillet faces' bounding boxes (zmax -1.919,
0.18 above the shelf back) and deleted the R0.3; face bounding boxes of curved faces can be loose. Here the
max Z is taken from the fillet faces' edges and vertices and from evaluator points that lie ON the faces
(isParameterOnFace grid). Kept only if that max Z <= Z_SHELF_BACK + 0.01 and the tail-pocket probe stays empty.
Expects: 44c done (feature deleted)."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def face_zmax(f):
    z = -1e9
    for k in range(f.edges.count):
        e = f.edges.item(k)
        z = max(z, e.startVertex.geometry.z * 10, e.endVertex.geometry.z * 10)
        ev = e.evaluator
        ok, p0, p1 = ev.getParameterExtents()
        for t in range(1, 20):                      # interior parameters only (end values can be out of range)
            ok, p = ev.getPointAtParameter(p0 + (p1 - p0) * t / 20.0)
            if ok:
                z = max(z, p.z * 10)
    ev = f.evaluator
    rng = ev.parametricRange()
    for i in range(31):
        for j in range(31):
            uv = adsk.core.Point2D.create(rng.minPoint.x + (rng.maxPoint.x - rng.minPoint.x) * i / 30,
                                          rng.minPoint.y + (rng.maxPoint.y - rng.minPoint.y) * j / 30)
            if ev.isParameterOnFace(uv):
                ok, p = ev.getPointAtParameter(uv)
                z = max(z, p.z * 10)
    return z


def run(_context: str):
    L.check_doc()
    L.log("=== 44d start")
    f, n = L.fillet_set("tail pocket shelf end", radius="0.3 mm")
    zsb = L.P("Z_SHELF_BACK")
    zmax = max(face_zmax(f.faces.item(i)) for i in range(f.faces.count))
    nf = f.faces.count
    ok = zmax <= zsb + 0.01
    if not ok:
        f.deleteMe()
    L.log("44d R0.3 tail corners: %d edges, %d faces, tight zmax %.4f (shelf back %.3f) -> %s" % (
        n, nf, zmax, zsb, "KEPT" if ok else "DELETED (climbs)"))
    nt, bad = L.timeline_health()
    L.show_iso()
    print(n, nf, round(zmax, 4), "KEPT" if ok else "DELETED", L.body_stats(), nt, bad)
