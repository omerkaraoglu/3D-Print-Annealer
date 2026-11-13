"""68 - (copy of 66, final) save the fit assembly after v2.2 (linked frame v6, patch with side-peg holes P1 round / P2 slot, socket check
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
    ok, v = L.save_version("v2.2 final fit: both peg holes X-slots"
)
    print(ok, v)
