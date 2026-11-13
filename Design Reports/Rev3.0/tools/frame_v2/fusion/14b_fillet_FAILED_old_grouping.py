"""14b - root fillet group 'PCB bosses': one FilletFeature 'Root fillets R0.5 - PCB bosses' (R fillet_root, rolling-ball corners)
on every concave 60..120 deg edge between ORIGINAL plane/cone faces of that group (fv2lib.root_edges: pilots,
reliefs, stud holes and peg roots excluded). Edges are re-collected after each previous fillet group.
Expects: 13 scan clean; previous 14x groups done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    f, n = L.fillet_group("PCB bosses", "Root fillets R0.5 - PCB bosses")
    nt, bad = L.timeline_health()
    L.show_iso()
    print(n, "edges", L.body_stats(), nt, bad)
