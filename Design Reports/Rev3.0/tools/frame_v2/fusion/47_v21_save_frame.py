"""47 - save the frame document v2.1 (new version). Expects: 40-46 done, scans clean."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version("v2.1: symmetric 7.5/14, 10 studs (socket rule 6.5/11) as 4.5x5.3 slots, tail walls "
                           "stepped at y 129, ribs to the shelf edge, fillets redone")
    print(ok, v, L.body_stats())
