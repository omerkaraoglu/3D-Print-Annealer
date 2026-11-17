"""diag_gf20_views - read-mostly diagnostic renders of the frame (stage 4): every other occurrence hidden, the frame
body temporarily shown in a light grey appearance, views from VIEWS (or the module global VIEWS set by the runner),
everything restored afterwards (visibility, appearance). PNGs to %TEMP%\\rev3_glassfront\\gf20\\diag_*.png."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

OUT = os.path.join(L.SCR, "gf20")
# name: (eye direction, target model mm (X, Y=-y_abs, Z), extent mm)
VIEWS = globals().get("VIEWS") or {
    "bl_corner_back": ((-0.5, -0.6, 1.0), (25.0, -140.0, -6.0), 45),
    "bridge_back": ((0.25, -0.7, 1.0), (80.0, -128.0, -6.0), 40),
    "bridge_front": ((0.2, -0.6, -1.0), (80.0, -124.0, -9.0), 40),
}


def run(_context: str):
    L.check_doc()
    r = L.root()
    vis = {}
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        vis[o.component.name] = o.isLightBulbOn
        o.isLightBulbOn = (o.component.name == L.COMP_NAME)
    b = L.body()
    ap0 = b.appearance
    b.appearance = L.appearance("Plastic - Matte (Gray)")
    out = []
    try:
        for nm, (eye, tgt, ext) in VIEWS.items():
            p = os.path.join(OUT, "diag_%s.png" % nm)
            L.shot(p, eye, target_mm=tgt, up=(0, 0, 1) if abs(eye[2]) < 0.2 else (0, 1, 0), w=1400, h=1000,
                   fit=False, extent_mm=ext)
            out.append(p)
    finally:
        b.appearance = ap0
        for i in range(r.occurrences.count):
            o = r.occurrences.item(i)
            o.isLightBulbOn = vis[o.component.name]
    print(out)
