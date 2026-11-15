"""08 - milestone save: body complete (no root fillets, no slots yet). Expects: 07 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version("GF-1.0 frame: body complete (plates, step wall, lip, pads, v2 structure, pips, tubes, "
                           "tube ribs); no fillets / slots yet")
    print(ok, v, L.body_stats())
