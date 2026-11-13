"""62 - save the frame v2.2 (new version). Expects: 61 done, scan 60 clean."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version("v2.2: stud tubes 5 above the flange back (seat Z -3.52, full-height ribs, PEM FH-M4-18), "
                           "pegs on the side flanges, radial slots about the datum (102.47, 69.5)")
    print(ok, v, L.body_stats())
