"""38 - milestone save of the fit assembly ('checks done'). Expects: 37, 35, 36a-d done (all visible)."""
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
    ok, v = L.save_version("fit checks done: board STEP +0.08 Z, Formex sheet, gasket, oven-sheet patch (rebuilt), "
                           "socket check cylinders (hidden)")
    print(ok, v)
