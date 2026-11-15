"""61 - stage 3 (GF-1.1): documentation-only fix. The comment of user parameter cb_floor still said 'F5-F8 0.6 into the
flange front' from before cb_floor_mid (2.0) took over F5-F8 (51b). Only the comment is changed (no expression, so no
geometry); the frame volume / face count are checked unchanged, the document is saved as a new version and the
Fusion archive Rev3.0_GlassFront.f3d is re-exported (the STEP / STL exports of 59 carry no parameter comments and
stay valid: same geometry)."""
import importlib
import os
import sys

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

NEW = ("GF-1.1: counterbore floor above Z_SHEET_BACK at F1-F4, in the pad face (1.4 flange + 0.2; Z -11.82 at glass "
       "3.0); F5-F8 use cb_floor_mid")
MSG = "GF-1.1: parameter comment cb_floor corrected (documentation only, geometry unchanged)"


def run(_context: str):
    d = L.check_doc()
    b = L.body()
    v0, f0 = b.volume, b.faces.count
    p = d.userParameters.itemByName("cb_floor")
    old = p.comment
    p.comment = NEW
    d.computeAll()
    b = L.body()
    if abs(b.volume - v0) > 1e-9 or b.faces.count != f0:
        raise RuntimeError("geometry changed?! %r %r" % (b.volume, b.faces.count))
    n, bad = L.timeline_health()
    if bad or d.analyses.sectionAnalyses.count or d.snapshots.hasPendingSnapshot:
        raise RuntimeError("not clean: %s" % bad)
    ok, ver = L.save_version(MSG)
    em = d.exportManager
    pf = os.path.join(L.MECH, "Rev3.0_GlassFront.f3d")
    f3d = em.execute(em.createFusionArchiveExportOptions(pf))
    L.log("61 comment %r -> %r; saved %s (log version %s); f3d %s %d bytes" % (old, NEW, ok, ver, f3d,
                                                                              os.path.getsize(pf)))
    print("saved", ok, ver, "f3d", f3d, os.path.getsize(pf))
