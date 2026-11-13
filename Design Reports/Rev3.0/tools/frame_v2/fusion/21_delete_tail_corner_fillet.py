"""21 - FIX: delete 'Root fillets R0.5 - tail pocket shelf end' (re-made in 18). The concave corner between the
tail-pocket side face and the shelf end face is only 2.5 tall (Z_SEAT..Z_SHELF_BACK) and its top opens onto the
tail-pocket side face, which continues up as the tail wall; the R0.5 cannot cap there and Fusion rolled it 6 mm
up the tail-wall corner as a flap (material 0.016 inside the tail pocket at Z -1.5, face 2.58 mm2 with 2A/P 0.28).
The two corners stay SHARP (reported as unfilleted roots).
Expects: 19 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    f = L.feature("Root fillets R0.5 - tail pocket shelf end")
    if f is None:
        raise RuntimeError("feature not found")
    f.deleteMe()
    nt, bad = L.timeline_health()
    L.log("21 deleted tail pocket shelf end fillet; %s; timeline %d unhealthy %s" % (L.body_stats(), nt, bad))
    L.show_iso()
    print(L.body_stats(), nt, bad)
