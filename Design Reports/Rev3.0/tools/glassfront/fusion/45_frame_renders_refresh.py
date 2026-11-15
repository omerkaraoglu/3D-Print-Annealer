"""45 - stage 2, Part A/D: regenerate stage 1's frame renders (Fusion_FrameGF_*.png, 26_renders.py verbatim) after
the Part A cell-corner fix. Every root occurrence except 'Frame GF:1' is hidden for the shots and its light bulb
restored afterwards (26 fits the camera to what is visible)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    r = L.root()
    old = {}
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        if o.component.name != L.COMP_NAME:
            old[o.name] = o.isLightBulbOn
            o.isLightBulbOn = False
    p = os.path.join(L.GF_DIR, "26_renders.py")
    ns = {"__name__": "gf_26", "__file__": p}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    try:
        ns["run"](_context)
    finally:
        for i in range(r.occurrences.count):
            o = r.occurrences.item(i)
            if o.name in old:
                o.isLightBulbOn = old[o.name]
    print("restored", old)
