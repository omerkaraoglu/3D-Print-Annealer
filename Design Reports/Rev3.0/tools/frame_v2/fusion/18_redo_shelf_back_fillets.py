"""18 - FIX: the 16e fillet 'Root fillets R0.5 - shelf back' rolled off the two wall/shelf-back edges that end at
the tail-pocket side faces and continued across the whole shelf end (x 29..176): a wedge up to 0.04 mm tall on the
free shelf strip, plus 0.26 mm strips in front of the six tail-pocket support ribs. 16h ('tail pocket shelf end')
sat on that corner too (its face reached Z +3.8).
Deletes both, re-fillets the shelf-back roots WITHOUT the two segments that run into the tail pocket (they stay
sharp, reported), then redoes the tail-pocket shelf-end corner fillet.
Expects: 16b..16i done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 18 start")
    for nm in ("Root fillets R0.5 - tail pocket shelf end", "Root fillets R0.5 - shelf back"):
        f = L.feature(nm)
        if f is not None:
            f.deleteMe()
            L.log("18 deleted " + nm)
    f1, n1 = L.fillet_set("shelf back (not into the tail pocket)")
    f2, n2 = L.fillet_set("tail pocket shelf end")
    nt, bad = L.timeline_health()
    L.log("18 %s; timeline %d unhealthy %s" % (L.body_stats(), nt, bad))
    L.show_iso()
    print(n1, n2, L.body_stats(), nt, bad)
