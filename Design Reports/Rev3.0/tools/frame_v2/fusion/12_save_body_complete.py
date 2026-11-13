"""12 - milestone save: 'body complete (flange, 10 studs, cells, ribs, pegs), before root fillets'.
Expects: 11 done, active doc = Rev3.0 Frame v2 (saved before)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version("v2 body complete: flange, 10 M4 stud bosses + ribs, cells, 26 ribs, pegs; before root fillets")
    print(ok, v, L.body_stats())
