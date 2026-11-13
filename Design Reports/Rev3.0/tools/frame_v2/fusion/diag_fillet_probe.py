"""DIAGNOSTIC (not a build step): try R fillet_root on edge sub-groups, record success/failure, delete the test
fillet again. Catches the fillet compute error ON PURPOSE (to keep probing); prints the Fusion message."""
import importlib
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

PROBES = []   # set by the caller text below


def probe(sel):
    es = [e for g, e, m, z, o in L.root_edges2(0.9) if sel(g, m, z, o)]
    coll = adsk.core.ObjectCollection.create()
    for e in es:
        coll.add(e)
    ff = L.root().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll, L.VI("fillet_root"), False)
    fi.isRollingBallCorner = True
    t0 = time.time()
    try:
        f = ff.add(fi)
        f.deleteMe()
        return len(es), "OK %.1fs" % (time.time() - t0)
    except RuntimeError as ex:
        return len(es), "FAIL " + str(ex).split("//")[-1][:90]


def run(_context: str):
    L.check_doc()
    for name, sel in PROBES:
        n, r = probe(sel)
        L.log("probe %s: %d edges %s" % (name, n, r))
        print(name, n, r)


def probe2(sel_a, r_a, sel_b, r_b):
    """two edge sets with different radii in ONE fillet feature"""
    es = L.root_edges2(0.9)
    A = [e for g, e, m, z, o in es if sel_a(g, e, m, z, o)]
    B = [e for g, e, m, z, o in es if sel_b(g, e, m, z, o)]
    ff = L.root().features.filletFeatures
    fi = ff.createInput()
    for lst, r in ((A, r_a), (B, r_b)):
        if lst:
            c = adsk.core.ObjectCollection.create()
            for e in lst:
                c.add(e)
            fi.edgeSetInputs.addConstantRadiusEdgeSet(c, L.VI(r), False)
    fi.isRollingBallCorner = True
    try:
        f = ff.add(fi)
        f.deleteMe()
        return len(A), len(B), "OK"
    except RuntimeError as ex:
        return len(A), len(B), "FAIL " + str(ex).split("//")[-1][:90]
