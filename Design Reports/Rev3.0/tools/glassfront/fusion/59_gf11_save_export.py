"""59 - stage 3 (GF-1.1): save (version comment) and every export to Mechanical/Rev3.0_GlassFront/:
Rev3.0_GlassFront_Frame.step / .stl (25 verbatim), Rev3.0_GlassFront_Assembly.step (root, S4 as shown; Fusion omits
hidden occurrences / bodies - checked again in the file), Rev3.0_GlassFront_Glass.step, Rev3.0_GlassFront.f3d.
Refuses unless the flex parameters are at their defaults, the timeline is healthy, no section analysis and no pending
position change exist, and the weld flange is back at the nominal 5.5 x 0.7."""
import importlib
import os
import re
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0, "stud_fl_d": 5.5,
            "stud_fl_k": 0.7}
MSG = ("GF-1.1 (stage 3): counterbores 7.2 x 8.8, tube coring grooves, H6 cell jog (no fill), tail pocket +0.3/side, "
       "glass R6.25 / cut-out R7.55, F5-F8 tube blend R1.2, S8 DIN 988 spacer; flex 1.1/2.0/3.0/4.0 healthy")


def run(_context: str):
    L.check_doc()
    d = L.des()
    for k, v in DEFAULTS.items():
        if abs(L.P(k) - v) > 1e-9:
            raise RuntimeError("%s = %r not at its default %r" % (k, L.P(k), v))
    n, bad = L.timeline_health()
    if bad or d.analyses.sectionAnalyses.count or d.snapshots.hasPendingSnapshot:
        raise RuntimeError("not clean: %s / sections %d / pending %s" % (bad, d.analyses.sectionAnalyses.count,
                                                                          d.snapshots.hasPendingSnapshot))
    ok, ver = L.save_version(MSG)
    p25 = os.path.join(L.GF_DIR, "25_export_frame.py")
    ns = {"__name__": "gf_25", "__file__": p25}
    exec(compile(open(p25, encoding="utf-8").read(), p25, "exec"), ns)
    ns["run"](_context)
    em = d.exportManager
    out = {}
    pa = os.path.join(L.MECH, "Rev3.0_GlassFront_Assembly.step")
    out["assembly"] = em.execute(em.createSTEPExportOptions(pa, L.root()))
    pg = os.path.join(L.MECH, "Rev3.0_GlassFront_Glass.step")
    out["glass"] = em.execute(em.createSTEPExportOptions(pg, L.occ_by_comp("Glass").component))
    pf = os.path.join(L.MECH, "Rev3.0_GlassFront.f3d")
    out["f3d"] = em.execute(em.createFusionArchiveExportOptions(pf))
    prods = set()
    with open(pa, encoding="latin-1") as fh:
        for line in fh:
            m = re.search(r"PRODUCT\('([^']*)'", line)
            if m:
                prods.add(m.group(1))
    hidden = sorted(x for x in prods if "hidden" in x or "Check" in x or "R4 (rivet" in x)
    L.log("59 saved %s v%s; exports %s; hidden products in the assembly STEP %s; %s" % (ok, ver, out, hidden,
                                                                                         L.body_stats()))
    print("saved", ok, ver, out, "hidden in STEP", hidden, L.body_stats())
