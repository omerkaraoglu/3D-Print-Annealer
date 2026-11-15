"""07b - (one-off fix of the first build, not part of a clean rebuild) the first 'Tube ribs F1-F4' ran to Z_TUBE_TOP
and stood 0.5 above the step-wall back over its 0.4 buried end (two 0.40 mm root edges and a 1.43 x 0.5 end face on
the plate: census 09). Re-run 02 first (adds trib_h_min, Z_TRIB_TOP); this script deletes the rib feature and its
sketch (last items in the timeline) and re-makes them with 07.make_ribs (rib top Z_TRIB_TOP).
Expects: 07 done, 02 re-run."""
import importlib
import sys

import adsk.core
import adsk.fusion

D = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion"
sys.path.insert(0, D)
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 07b start")
    tl = L.des().timeline
    last = tl.item(tl.count - 1)
    if last.name != "Tube ribs F1-F4":
        raise RuntimeError("last timeline item is %r, expected 'Tube ribs F1-F4'" % last.name)
    last.entity.deleteMe()
    sk = L.comp().sketches.itemByName("Tube ribs F1-F4 sketch")
    sk.deleteMe()
    ns = {"__name__": "gf_07"}
    P = D + r"\07_tubes_tube_ribs.py"
    exec(compile(open(P, encoding="utf-8").read(), P, "exec"), ns)
    uc = ns["make_ribs"](L.body())
    n, bad = L.timeline_health()
    L.log("07b Z_TRIB_TOP %.3f; %s; %s; timeline %d unhealthy %s" % (L.P("Z_TRIB_TOP"), L.body_stats(), uc, n, bad))
    print(L.P("Z_TRIB_TOP"), L.body_stats(), uc, n, bad)
