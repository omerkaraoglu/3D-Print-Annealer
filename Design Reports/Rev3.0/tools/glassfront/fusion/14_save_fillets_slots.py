"""14 - milestone save after the fillets and the slots (run inline through the MCP with exactly this body).
Expects: 13 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    ok, v = L.save_version('GF-1.0 frame: root fillets (edge sets + rule fillets), lip R0.3 / R0.2, radial slots F1-F8, '
                           'black nylon')
    print(ok, v, L.body_stats(), L.timeline_health())
