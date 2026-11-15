"""25 - exports of the frame only (component 'Frame GF', default parameters) to Mechanical/Rev3.0_GlassFront/:
  Rev3.0_GlassFront_Frame.step  (component 'Frame GF' = the one body 'Frame GF'; model frame Z 0 = PCB back,
                                 X = KiCad x, Y = -KiCad y, mm)
  Rev3.0_GlassFront_Frame.stl   (body, high refinement, binary)
Refuses unless every flex parameter is at its default. Expects: final model, flex test done (defaults restored)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0}


def run(_context: str):
    L.check_doc()
    for k, v in DEFAULTS.items():
        if abs(L.P(k) - v) > 1e-9:
            raise RuntimeError("%s = %r is not the default %r" % (k, L.P(k), v))
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("timeline unhealthy: %s" % bad)
    em = L.des().exportManager
    base = os.path.join(L.MECH, "Rev3.0_GlassFront_Frame")
    r = []
    o = em.createSTEPExportOptions(base + ".step", L.comp())
    r.append(("step", em.execute(o)))
    o = em.createSTLExportOptions(L.body(), base + ".stl")
    o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    o.isBinaryFormat = True
    r.append(("stl", em.execute(o)))
    sizes = [(ext, os.path.getsize(base + "." + ext) if os.path.exists(base + "." + ext) else None)
             for ext in ("step", "stl")]
    L.log("25 exports %s sizes %s; %s" % (r, sizes, L.body_stats()))
    print(r, sizes, L.body_stats())
