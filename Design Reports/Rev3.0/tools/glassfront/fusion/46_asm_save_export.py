"""46 - stage 2, Part D: final assembly save + exports to Mechanical/Rev3.0_GlassFront/:
  Rev3.0_GlassFront_Assembly.step   root component, variant S4 as visible (see EXCLUDE_HIDDEN below)
  Rev3.0_GlassFront_Glass.step      component 'Glass' (glass body with the 0.5 arris + the 0.02 print layer body)
  Rev3.0_GlassFront.f3d             Fusion archive of the whole document
Refuses unless the flex parameters are at their defaults, the timeline is healthy, no section analysis exists and no
position change is pending. The hidden variant / check components (R4, S8, socket cylinders) and the hidden R4 sheet
body stay hidden; the script then lists the PRODUCT names in the written STEP to prove what went in. Result
(2026-11-15): Fusion omits hidden occurrences and bodies from the STEP - none of the hidden products is in the file
(191 solids = the S4 assembly as shown)."""
import importlib
import os
import re
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0}
SAVE_MSG = ("Stage 2 FINAL: GlassFront fit assembly (Glass, Optical bond, Formex, Bead, VHB strips, Oven sheet S4 + "
            "hidden R4 / S8 sets, board STEP with DS1 at Z_PANEL_BACK), checks 39-42, renders 43-45")


def step_products(path):
    names = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = re.search(r"PRODUCT\('([^']*)'", line)
            if m:
                names.add(m.group(1))
    return names


def run(_context: str):
    L.check_doc()
    d = L.des()
    for k, v in DEFAULTS.items():
        if abs(L.P(k) - v) > 1e-9:
            raise RuntimeError("%s not at its default" % k)
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("timeline unhealthy %s" % bad)
    if d.analyses.sectionAnalyses.count:
        raise RuntimeError("section analysis present")
    if d.snapshots.hasPendingSnapshot:
        raise RuntimeError("pending position change")
    ok, ver = L.save_version(SAVE_MSG)
    em = d.exportManager
    out = {}
    p = os.path.join(L.MECH, "Rev3.0_GlassFront_Assembly.step")
    out["assembly_step"] = em.execute(em.createSTEPExportOptions(p, L.root()))
    p2 = os.path.join(L.MECH, "Rev3.0_GlassFront_Glass.step")
    out["glass_step"] = em.execute(em.createSTEPExportOptions(p2, L.occ_by_comp("Glass").component))
    p3 = os.path.join(L.MECH, "Rev3.0_GlassFront.f3d")
    out["f3d"] = em.execute(em.createFusionArchiveExportOptions(p3))
    prods = step_products(p)
    hidden_in = sorted(x for x in prods if "hidden" in x or "Check" in x)
    sizes = {os.path.basename(x): os.path.getsize(x) for x in (p, p2, p3) if os.path.exists(x)}
    L.log("46 saved %s v%s; exports %s %s; hidden products in the assembly STEP %s" % (ok, ver, out, sizes, hidden_in))
    print("saved", ok, ver, out, sizes, "products", len(prods), "hidden in STEP:", hidden_in)
