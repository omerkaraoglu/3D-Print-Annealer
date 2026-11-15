"""53 - stage 3 (GF-1.1) iteration helper (READ-ONLY on the design): exports the frame component to a SCRATCH STEP
(%TEMP%\\rev3_glassfront\\gf11\\frame_iter.step, not the deliverable) for the thickness check, and runs 20_scan
verbatim (TAG gf11) -> scan_gf11.json. Module global TAG_SUFFIX names the STEP / scan."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

TAG_SUFFIX = "iter"


def run(_context: str):
    L.check_doc()
    out = os.path.join(L.SCR, "gf11")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, "frame_%s.step" % TAG_SUFFIX)
    em = L.des().exportManager
    ok = em.execute(em.createSTEPExportOptions(p, L.comp()))
    p20 = os.path.join(L.GF_DIR, "20_scan.py")
    ns = {"__name__": "gf_20", "__file__": p20}
    exec(compile(open(p20, encoding="utf-8").read(), p20, "exec"), ns)
    ns["TAG"] = "gf11_" + TAG_SUFFIX
    ns["run"](_context)
    print("step", ok, p, os.path.getsize(p) if os.path.exists(p) else None)
