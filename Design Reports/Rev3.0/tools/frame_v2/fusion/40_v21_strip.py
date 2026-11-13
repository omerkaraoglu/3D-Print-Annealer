"""40 - v2.1 (coordinator review): remove the features that are rebuilt with the new stud pattern, stud slots
and extended support ribs: every 'Root fillets ...' feature, the 30 'Stud FHn tube/rib/hole' features and the
'PCB support ribs (26)' feature, each with its sketch (deleted last-to-first along the timeline).
Expects: frame document v3 active (110 timeline items)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def doomed(name):
    return (name.startswith("Root fillets") or name.startswith("Stud FH") or name.startswith("PCB support ribs (26)"))


def run(_context: str):
    L.check_doc()
    L.log("=== 40 start")
    tl = L.des().timeline
    names = []
    for i in range(tl.count - 1, -1, -1):
        it = tl.item(i)
        if doomed(it.name):
            names.append(it.name)
            it.entity.deleteMe()
    n, bad = L.timeline_health()
    L.log("40 deleted %d timeline items; timeline %d unhealthy %s; %s" % (len(names), n, bad, L.body_stats()))
    L.show_iso()
    print(len(names), n, bad, L.body_stats())
