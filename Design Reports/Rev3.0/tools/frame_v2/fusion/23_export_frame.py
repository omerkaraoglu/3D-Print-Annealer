"""23 - exports of the frame document to Mechanical/Rev3.0_Frame/:
  Rev3.0_Frame_v2.step  (root component = the one body 'Frame v2', model frame: Z 0 = PCB back)
  Rev3.0_Frame_v2.stl   (body, high refinement)
  Rev3.0_Frame_v2.f3d   (Fusion archive of the whole parametric document)
Expects: 22 done."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    em = L.des().exportManager
    base = os.path.join(L.MECH, "Rev3.0_Frame_v2")
    r = []
    o = em.createSTEPExportOptions(base + ".step", L.root())
    r.append(("step", em.execute(o)))
    o = em.createSTLExportOptions(L.body(), base + ".stl")
    o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    o.isBinaryFormat = True
    r.append(("stl", em.execute(o)))
    o = em.createFusionArchiveExportOptions(base + ".f3d")
    r.append(("f3d", em.execute(o)))
    sizes = [(ext, os.path.getsize(base + "." + ext) if os.path.exists(base + "." + ext) else None)
             for ext in ("step", "stl", "f3d")]
    L.log("23 exports %s sizes %s" % (r, sizes))
    print(r, sizes)
