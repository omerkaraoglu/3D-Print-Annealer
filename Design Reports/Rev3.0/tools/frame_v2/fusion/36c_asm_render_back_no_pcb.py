"""36c - back views with the PCB and all components hidden (36b SHOW=False), showing frame + Formex sheet on the
panel back (gasket in front of the glass, behind the panel): Fusion_Assembly_back_no_PCB.png and
Fusion_Assembly_iso_back_no_PCB.png. Expects: 36b hide DONE."""
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
    out = [L.shot(os.path.join(R, "Fusion_Assembly_back_no_PCB.png"), (0, 0, 1), target_mm=TGT),
           L.shot(os.path.join(R, "Fusion_Assembly_iso_back_no_PCB.png"), (0.45, 0.4, 1.0), target_mm=TGT)]
    L.log("36c %s" % out)
    print(out)
