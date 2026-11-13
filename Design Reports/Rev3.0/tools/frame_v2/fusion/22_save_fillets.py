"""22 - milestone save 'root fillets done'. Expects: 21 done, scans clean (17)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version("v2 root fillets R0.5 (341 roots in 10 features), tail-wall ledge fixed, black nylon appearance")
    print(ok, v, L.body_stats())
