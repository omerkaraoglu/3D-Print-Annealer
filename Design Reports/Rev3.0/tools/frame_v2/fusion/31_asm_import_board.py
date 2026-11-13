"""31 - import the KiCad board STEP (every 3D model incl. the panel DS1 with its folded tails; exported with
--user-origin 0x0mm so X = board x, Y = -board y) into a new component 'Rev3.0 PCB full (KiCad STEP)'.
May run longer than the MCP timeout; progress goes to the log.
Expects: 30 done, active doc = the fit assembly."""
import importlib
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

STEP = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
        r"\scratchpad\cad\Rev3.0_PCB_full.step")


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    t0 = time.time()
    L.log("=== 31 start import")
    root = L.root()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = "Rev3.0 PCB full (KiCad STEP)"
    im = adsk.core.Application.get().importManager
    opt = im.createSTEPImportOptions(STEP)
    ok = im.importToTarget(opt, occ.component)
    c = occ.component
    L.log("31 import %s in %.0f s: %d occurrences, %d bodies (all levels)" % (
        ok, time.time() - t0, c.allOccurrences.count, c.bRepBodies.count))
    print(ok, time.time() - t0, c.allOccurrences.count)
