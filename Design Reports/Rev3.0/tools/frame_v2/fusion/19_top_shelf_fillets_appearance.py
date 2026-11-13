"""19 - (a) the two TOP shelf-back/wall root segments (y 18.75, x ~29..48 and ~157..176) that 18's tail-pocket
filter wrongly skipped (its x test had no y condition; fixed in fv2lib._runs_into_tail) get their R0.5 fillet
'Root fillets R0.5 - shelf back (top, completed)'; (b) body appearance 'Plastic - Matte (Black)' (black nylon).
Expects: 18 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 19 start")
    es = [e for g, e, m, z, o in L.root_edges2(0.9) if g == "shelf back" and not L._runs_into_tail(e)]
    if len(es) != 2:
        raise RuntimeError("expected the 2 top shelf-back segments, found %d" % len(es))
    coll = adsk.core.ObjectCollection.create()
    for e in es:
        coll.add(e)
    ff = L.root().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll, L.VI("fillet_root"), False)
    fi.isRollingBallCorner = True
    f = ff.add(fi)
    f.name = "Root fillets R0.5 - shelf back (top, completed)"
    L.set_appearance(L.body(), "Plastic - Matte (Black)")
    nt, bad = L.timeline_health()
    L.log("19 %s; timeline %d unhealthy %s" % (L.body_stats(), nt, bad))
    L.show_iso()
    print(L.body_stats(), nt, bad)
