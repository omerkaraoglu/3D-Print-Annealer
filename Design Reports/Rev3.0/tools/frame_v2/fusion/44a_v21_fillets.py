"""44a - v2.1 root fillets R0.5 (rebuilt after 40): one FilletFeature per fv2lib.FILLET_SETS entry, edges
re-collected before each (concave 25..155 deg edges between original plane/cone faces, grouped by creating
features; pilots, reliefs, stud slots, peg roots and the two shelf-back segments that run into the tail pocket
excluded). Sets: "stud tubes + ribs", "PCB bosses on the walls", "corner cells + cell ribs + cell bosses", "PCB support rib sides".
Expects: 43b done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

SETS = ["stud tubes + ribs", "PCB bosses on the walls", "corner cells + cell ribs + cell bosses", "PCB support rib sides"]


def run(_context: str):
    L.check_doc()
    L.log("=== 44a start")
    out = []
    for s in SETS:
        f, n = L.fillet_set(s)
        out.append((s, n))
    nt, bad = L.timeline_health()
    L.log("44a %s; %s; timeline %d unhealthy %s" % (out, L.body_stats(), nt, bad))
    L.show_iso()
    print(out, L.body_stats(), nt, bad)
