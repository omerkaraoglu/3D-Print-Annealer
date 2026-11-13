"""36a - assembly screenshots, everything visible (socket-cylinder check component stays hidden):
Fusion_Assembly_iso_front.png, Fusion_Assembly_iso_back.png (1600 x 1200). Expects: 35 done."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

R = os.path.join(L.MECH, "renders_v2")
TGT = (102.0, -85.0, -3.0)


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    out = [L.shot(os.path.join(R, "Fusion_Assembly_iso_front.png"), (0.55, 0.45, -1.0), target_mm=TGT),
           L.shot(os.path.join(R, "Fusion_Assembly_iso_back.png"), (0.5, 0.45, 1.0), target_mm=TGT)]
    L.log("36a %s" % out)
    print(out)
