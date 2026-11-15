"""27 - final save (all flex parameters at their defaults, checked) and document info -> scratchpad docinfo.json:
document name / id / version, folder, component / body names, timeline (name, type, health) and the user-parameter
dump (name, expression, value, unit, comment). Expects: 25 / 26 done (exports, renders; no temporary objects)."""
import importlib
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
            raise RuntimeError("%s not at its default" % k)
    d = L.des()
    if d.analyses.sectionAnalyses.count:
        raise RuntimeError("a section analysis is still present")
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("timeline unhealthy %s" % bad)
    ok, v = L.save_version("GF-1.0 frame FINAL: flex-tested (glass 1.1/2.0/3.0/4.0, t_sheet 0.8/1.5, t_opt 1.0), "
                           "scanned, exported; all parameters at their defaults (glass_t 3.0)")
    doc = L.app().activeDocument
    df = doc.dataFile
    tl = d.timeline
    items = []
    for i in range(tl.count):
        it = tl.item(i)
        items.append({"i": i, "name": it.name, "type": it.entity.objectType.split("::")[-1] if it.entity else None,
                      "health": str(it.healthState)})
    ups = d.userParameters
    params = []
    for i in range(ups.count):
        p = ups.item(i)
        val = p.value * 10.0 if p.unit == "mm" else (p.value * 57.29577951308232 if p.unit == "deg" else p.value)
        params.append({"name": p.name, "expression": p.expression, "value": round(val, 6), "unit": p.unit,
                       "comment": p.comment})
    info = {"document": doc.name, "saved": ok, "dataFile_id": df.id if df else None,
            "version": df.versionNumber if df else None, "project": df.parentProject.name if df else None,
            "folder": df.parentFolder.name if df else None, "component": L.COMP_NAME, "body": L.BODY_NAME,
            "attribute_guard": "%s/%s = %s" % (L.TAG_GROUP, L.TAG_NAME, L.DOC_NAME),
            "timeline_count": tl.count, "timeline": items, "user_parameters": params,
            "body_props": L.body_dict()}
    p = L.dump(info, "docinfo.json")
    print(p, ok, info["dataFile_id"], info["version"], tl.count, len(params))
