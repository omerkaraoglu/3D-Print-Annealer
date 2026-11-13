"""55 - (v2.1 final copy of 48: stud close-up re-targeted to FH2 at x 103.5) frame-alone screenshots (1600 x 1200, orthographic, camera set by script) to
Mechanical/Rev3.0_Frame/renders_v2/Fusion_<name>.png. Model Y up = top of the board; front = -Z (sealing face).
Expects: 22 done (fillets, black appearance)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

R = os.path.join(L.MECH, "renders_v2")
VIEWS = [
    ("Frame_front", dict(eye_dir=(0, 0, -1))),
    ("Frame_back", dict(eye_dir=(0, 0, 1))),
    ("Frame_iso_front", dict(eye_dir=(0.55, 0.45, -1.0))),
    ("Frame_iso_back", dict(eye_dir=(0.5, 0.45, 1.0))),
    ("Frame_closeup_stud_boss_FH2", dict(eye_dir=(0.55, 0.6, 1.0), target_mm=(103.5, -11.0, -7.0), fit=False,
                                         extent_mm=26)),
    ("Frame_closeup_tail_pocket", dict(eye_dir=(0.25, -0.55, 1.0), target_mm=(103.0, -136.0, -3.0), fit=False,
                                       extent_mm=150)),
]


def run(_context: str):
    L.check_doc()
    os.makedirs(R, exist_ok=True)
    out = []
    for name, kw in VIEWS:
        out.append((name, L.shot(os.path.join(R, "Fusion_%s.png" % name), **kw)))
    L.show_iso()
    L.log("24 renders %s" % out)
    print(out)
