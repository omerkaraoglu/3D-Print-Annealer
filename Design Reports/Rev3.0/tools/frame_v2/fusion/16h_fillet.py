"""16h - root fillet set 'tail pocket shelf end' (fv2lib.FILLET_SETS; edges = concave 25..155 deg edges between ORIGINAL
plane/cone faces, grouped by the features that created the two faces; pilots, reliefs, stud holes, peg roots
and the support-rib FREE ENDS excluded). One FilletFeature 'Root fillets R0.5 - tail pocket shelf end', R fillet_root,
rolling-ball corners. Groups were probed first with diag_fillet_probe.py.
Expects: 15 done and the previous 16x sets applied (edges are re-collected each time)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    f, n = L.fillet_set("tail pocket shelf end")
    nt, bad = L.timeline_health()
    L.show_iso()
    print(n, "edges", L.body_stats(), nt, bad)
