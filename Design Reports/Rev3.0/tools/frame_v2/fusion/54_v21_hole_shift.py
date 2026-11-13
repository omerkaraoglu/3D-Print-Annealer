"""54 - v2.1 final hole shift (coordinator 2026-11-13): FH1 x 43.5, FH2 x 103.5, FH4/FH10 y 40.5, FH5/FH9 y 98.5
(fv2lib.STUDS), so the dia-12 M4 socket keeps >= 1.5 mm from the PCB screw bosses outside the wall. Only the
fhN_x / fhN_y parameters change; tubes, ribs, slots and their fillets follow parametrically. Checks timeline
health, re-runs the stud-area census (no new / lost root edges) and saves the frame as a new version.
Expects: frame v4 active."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 54 start")
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        for k, e in (("_x", xe), ("_y", ye)):
            p = L.des().userParameters.itemByName(n + k)
            if p.expression.replace(" ", "") != e.replace(" ", ""):
                p.expression = e
    nt, bad = L.timeline_health()
    left = [(g, e.length * 10) for g, e, m, z, o in L.root_edges2(0.9) if g == "stud tubes + ribs"]
    pos = [(nm, round(L.P(nm.lower() + "_x"), 3), round(L.P(nm.lower() + "_y"), 3)) for nm, _, _, _ in L.STUDS]
    L.log("54 %s; timeline %d unhealthy %s; unfilleted stud roots %d; holes %s" % (L.body_stats(), nt, bad,
                                                                                   len(left), pos))
    if bad:
        raise RuntimeError("unhealthy timeline after the shift: %s" % bad)
    ok, v = L.save_version("v2.1 final: FH1 43.5, FH2 103.5, side holes y 40.5 / 98.5 (socket >= 1.5 mm from the "
                           "PCB bosses)")
    L.show_iso()
    print(L.body_stats(), nt, bad, len(left), ok, pos)
