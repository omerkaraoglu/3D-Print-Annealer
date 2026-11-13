"""53 - save the fit assembly v2.1 (linked frame updated to v2.1, patch holes at the new pattern, socket check
cylinders rebuilt, checks 33/34/51/52 + renders done). Expects: all visible (36d DONE)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    L.show_iso()
    ok, v = L.save_version("v2.1 fit: frame v2.1 linked, oven-sheet holes at the new 10-stud pattern, socket checks "
                           "incl. DS1 and frame wall")
    print(ok, v)
