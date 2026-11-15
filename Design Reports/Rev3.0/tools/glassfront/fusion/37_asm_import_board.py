"""37 - stage 2, Part B: import the KiCad board STEP (every footprint model incl. the panel DS1 with its folded tails)
into a new component 'Rev3.0 PCB full (KiCad STEP)' (as frame_v2 script 31).
The STEP was exported OUTSIDE Fusion from a COPY of the board (the KiCad project is never touched):
    copy KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb + .kicad_pro -> %TEMP%\\rev3_glassfront\\board\\
    kicad-cli pcb export step --subst-models --user-origin 0x0mm -D KIPRJMOD=<real project folder> -f
              -o board_full.step 3dFilamentDryer.kicad_pcb
  (KiCad 10.0; board file md5 82cfd2615aa8e4511e89f13eb2a7eb6c = commit a9d56fc). X = KiCad x, Y = -KiCad y,
  Z 0 = the exported core back (0.08 above the physical PCB back: no copper / mask; 38 moves it +board_dz).
May take minutes; progress in the log."""
import importlib
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

STEP = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\board\board_full.step"


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    L.log("=== 37 start import")
    o = L.new_comp(L.BOARD_COMP)
    im = L.app().importManager
    opt = im.createSTEPImportOptions(STEP)
    ok = im.importToTarget(opt, o.component)
    c = o.component
    L.log("37 import %s in %.0f s: %d occurrences (all levels), %d bodies at the top" % (
        ok, time.time() - t0, c.allOccurrences.count, c.bRepBodies.count))
    print(ok, round(time.time() - t0), c.allOccurrences.count, c.bRepBodies.count)
