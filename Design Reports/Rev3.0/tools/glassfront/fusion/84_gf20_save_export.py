"""84 - stage 4 (GF-2.0) FINAL: save + exports to Mechanical/Rev3.0_GlassFront/ under the existing names (the GF-1.1
copies are in archive/GF-1.1/):
  Rev3.0_GlassFront_Frame.step / .stl   component 'Frame GF' (one body) as 25 (STL binary, high refinement)
  Rev3.0_GlassFront_Glass.step          component 'Glass' (glass + 0.02 print layer)
  Rev3.0_GlassFront_Assembly.step       root, variant S4 as visible (hidden R4 bodies, socket check cylinders and the
                                        GF-1.1 reference tails are omitted by Fusion's STEP export; listed from the file)
  Rev3.0_GlassFront.f3d                 Fusion archive of the whole document
Refuses unless the flex parameters are at their defaults, the timeline is healthy, no section analysis exists, no
position change is pending, the R4 / check components are hidden and the GF-1.1 tails are hidden.
Writes gf20/export.json (paths, sizes, version). After this script the frame is not changed again."""
import importlib
import json
import os
import re
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

DEFAULTS = globals().get("DEFAULTS") or {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0, "border": 18.5, "g_bend": 3.0}
SAVE_MSG = globals().get("SAVE_MSG") or (
    "GF-2.0 FINAL (scripts 66-84): equal border 18.5, tails bent back behind the bridge (g_bend 3.0, nose R1.5, break "
    "0.3), floors over the flange plate, divider rib, S4 / R4 only (S8 + F5-F8 removed); assembly with the GF-2.0 tail "
    "solids; flex 10/10; frame STEP / STL, glass STEP, assembly STEP, .f3d exported from this version")


def step_products(path):
    names = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = re.search(r"PRODUCT\('([^']*)'", line)
            if m:
                names.add(m.group(1))
    return names


def run(_context: str):
    d = L.check_doc()
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
    for cn in ("Rivets R4 F1-F4 (hidden)", L.CHECK_COMP):
        if L.occ_by_comp(cn).isLightBulbOn:
            raise RuntimeError(cn + " visible")
    if L.body_in(L.occ_by_comp("Oven sheet").component, "Oven sheet R4 (rivet holes)").isLightBulbOn:
        raise RuntimeError("R4 sheet body visible")
    old = [b for p, b in A.board() if A.is_ds1(p) and A.ds1_part(p) in ("tft_tail_5", "tft_fingers_6", "ctp_tail_7",
                                                                       "ctp_fingers_8")]
    if any(b.isVisible for b in old):
        raise RuntimeError("GF-1.1 reference tails visible")
    frame = L.body_dict()
    ok, ver = L.save_version(SAVE_MSG)
    em = d.exportManager
    out = {}
    base = os.path.join(L.MECH, "Rev3.0_GlassFront_Frame")
    out["frame_step"] = em.execute(em.createSTEPExportOptions(base + ".step", L.comp()))
    o = em.createSTLExportOptions(L.body(), base + ".stl")
    o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    o.isBinaryFormat = True
    out["frame_stl"] = em.execute(o)
    pa = os.path.join(L.MECH, "Rev3.0_GlassFront_Assembly.step")
    out["assembly_step"] = em.execute(em.createSTEPExportOptions(pa, L.root()))
    pg = os.path.join(L.MECH, "Rev3.0_GlassFront_Glass.step")
    out["glass_step"] = em.execute(em.createSTEPExportOptions(pg, L.occ_by_comp("Glass").component))
    pf = os.path.join(L.MECH, "Rev3.0_GlassFront.f3d")
    out["f3d"] = em.execute(em.createFusionArchiveExportOptions(pf))
    prods = step_products(pa)
    txt = open(pa, encoding="latin-1").read()
    solids = len(re.findall(r"MANIFOLD_SOLID_BREP\('", txt))
    ref_names = sorted(set(re.findall(r"'(GF-1\.1 reference[^']*)'", txt)))
    new_tails = sorted(set(re.findall(r"'((?:TFT|CTP) tail GF-2\.0[^']*)'", txt)))
    files = {}
    for p in (base + ".step", base + ".stl", pa, pg, pf):
        if os.path.exists(p):
            st = os.stat(p)
            files[os.path.basename(p)] = {"bytes": st.st_size, "mtime": time.strftime("%Y-%m-%d %H:%M:%S %z",
                                                                                   time.localtime(st.st_mtime))}
    res = {"saved": ok, "dataFile_version_at_save_call": ver, "save_comment": SAVE_MSG, "exports": out, "files": files,
           "frame": frame, "timeline_count": n, "assembly_step_products": len(prods),
           "hidden_or_reference_in_assembly_step": sorted(x for x in prods if "hidden" in x.lower() or "Check" in x
                                                          or "GF-1.1" in x),
           "tails_in_assembly_step": sorted(x for x in prods if "tail" in x.lower()),
           "assembly_step_solids": solids, "gf11_reference_bodies_in_assembly_step": ref_names,
           "gf20_tail_bodies_in_assembly_step": new_tails}
    L.dump(res, DUMP + "/export.json")
    L.log("84 %s" % res)
    print(res)
