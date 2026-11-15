"""21 - READ-ONLY plan sections of body 'Frame GF' for the thin-wall probe (and the above-Z0 / carry-over checks):
TemporaryBRepManager.planeIntersection at each Z -> wire body -> createFaceFromPlanarWires -> every face's loops
(outer / inner) sampled every <= 0.05 mm, abs KiCad coordinates (x, y down). Written to scratchpad
sections_<TAG>.json; ../gf_offline_checks.py turns them into polygons (shapely) and runs the inscribed-disc probe
(walls and gaps < 1.0 mm), as the v2 CadQuery cadcheck did.
Z levels (default stack, glass 3.0): through the lip, the seat ring, the flange, the land / pips, the land plate,
the tube tops, the walls, the shelf, the support ribs and the tail walls."""
import importlib
import json
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

TAG = "gf"
ZS = [-14.0, -13.0, -12.0, -10.7, -10.2, -9.0, -7.7, -6.0, -4.0, -3.35, -1.0, -0.6, 2.0]   # -0.6: below the relief floor (-0.5 is coplanar with it)


def sample_edge(e, tol=0.0005):
    """polyline of the edge (getStrokes, chord tolerance tol cm = 0.005 mm), abs x / y-down mm"""
    ev = e.evaluator
    ok, p0, p1 = ev.getParameterExtents()
    ok, strokes = ev.getStrokes(p0, p1, tol)
    if not ok or len(strokes) < 2:
        strokes = [e.startVertex.geometry, e.endVertex.geometry]
    return [[round(p.x * 10, 4), round(-p.y * 10, 4)] for p in strokes]


def section(body, z_mm):
    tb = adsk.fusion.TemporaryBRepManager.get()
    pl = adsk.core.Plane.create(adsk.core.Point3D.create(0, 0, z_mm / 10.0), adsk.core.Vector3D.create(0, 0, 1))
    wire = tb.planeIntersection(body, pl)
    if wire is None or wire.edges.count == 0:
        return []
    sheet = tb.createFaceFromPlanarWires([wire])
    faces = []
    for i in range(sheet.faces.count):
        f = sheet.faces.item(i)
        loops = []
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            segs = [sample_edge(lp.edges.item(k)) for k in range(lp.edges.count)]
            loops.append({"outer": lp.isOuter, "edges": segs})
        faces.append({"area_mm2": round(f.area * 100, 4), "loops": loops})
    return faces


def run(_context: str):
    L.check_doc()
    b = L.body()
    out = {"tag": TAG, "levels": {}}
    for z in ZS:
        out["levels"]["%.3f" % z] = section(b, z)
    p = L.dump(out, "sections_%s.json" % TAG)
    print(p, {k: len(v) for k, v in out["levels"].items()})
