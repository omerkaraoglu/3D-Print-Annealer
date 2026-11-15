"""56 - stage 3 (GF-1.1): the two-sided redefinition of 'Fastener tube coring F1-F8' (55) renamed its faces, so the
edge-set 'Coring groove floor edges R core_floor_r' lost its 16 references. Deleted and re-created on the current
floor loops (8 annular floors at Z_TUBE_TOP - core_depth, both loops, R core_floor_r 0.4), then glass 2.0 / 1.1 /
4.0 / 3.0 health + root census + overhang probe (55's functions)."""
import importlib
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

NAME = "Coring groove floor edges R core_floor_r"


def floor_edges():
    b = L.body()
    zf = L.P("Z_TUBE_TOP") - L.P("core_depth")
    edges = adsk.core.ObjectCollection.create()
    nfl = 0
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType or abs(f.pointOnFace.z * 10 - zf) > 1e-4:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if n.z < 0.9999:
            continue
        c = f.centroid
        if min(math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) for k in range(1, 9)) > 2.0:
            continue
        nfl += 1
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            for e in range(lp.edges.count):
                edges.add(lp.edges.item(e))
    return nfl, edges


def run(_context: str):
    d = L.check_doc()
    L.log("=== 56 start")
    tl = d.timeline
    f = L.feature(NAME)
    if f is not None:
        f.timelineObject.rollTo(True)
        f.deleteMe()
    nfl, edges = floor_edges()
    if nfl != 8:
        raise RuntimeError("groove floors %d" % nfl)
    ff = L.comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, L.VI("core_floor_r"), True)
    fi.isRollingBallCorner = True
    fl = ff.add(fi)
    fl.name = NAME
    tl.moveToEnd()
    d.computeAll()
    p55 = os.path.join(L.GF_DIR, "55_gf11_cb_amend_groove_twoside.py")
    ns = {"__name__": "gf_55"}
    exec(compile(open(p55, encoding="utf-8").read(), p55, "exec"), ns)
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
                    "overhangs", ns["overhangs"]()))
    if abs(L.P("glass_t") - 3.0) > 1e-9:
        raise RuntimeError("glass_t not restored")
    L.log("56 edges %d; %s" % (edges.count, out))
    print("edges", edges.count)
    for r in out:
        print(r)
