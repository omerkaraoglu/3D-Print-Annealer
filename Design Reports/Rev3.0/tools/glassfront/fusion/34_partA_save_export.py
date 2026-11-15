"""34 - stage 2, Part A: save the fixed frame (version comment) and re-export the frame STEP / STL by running
25_export_frame.py verbatim (overwrites stage 1's Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step / .stl,
intended). Refuses unless every flex parameter is at its default and the timeline is healthy. Writes scratchpad
docinfo_partA.json (document id / version, timeline, user parameters, body)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": 3.0, "t_sheet": 1.0, "t_opt": 0.3, "t_bond": 1.0, "t_gap": 1.0}


def docinfo(name):
    d = L.des()
    doc = L.app().activeDocument
    df = doc.dataFile
    tl = d.timeline
    items = [{"i": i, "name": tl.item(i).name, "health": str(tl.item(i).healthState)} for i in range(tl.count)]
    ups = d.userParameters
    params = []
    for i in range(ups.count):
        p = ups.item(i)
        val = p.value * 10.0 if p.unit == "mm" else (p.value * 57.29577951308232 if p.unit == "deg" else p.value)
        params.append({"name": p.name, "expression": p.expression, "value": round(val, 6), "unit": p.unit,
                       "comment": p.comment})
    info = {"document": doc.name, "dataFile_id": df.id if df else None, "version": df.versionNumber if df else None,
            "isModified": doc.isModified, "timeline_count": tl.count, "timeline": items, "user_parameters": params,
            "body_props": L.body_dict()}
    return L.dump(info, name), info


def run(_context: str):
    L.check_doc()
    for k, v in DEFAULTS.items():
        if abs(L.P(k) - v) > 1e-9:
            raise RuntimeError("%s not at its default" % k)
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("timeline unhealthy %s" % bad)
    ok, ver = L.save_version("Stage 2 Part A: H7 cell corner R1.0 (cell_r_h7) and H6 cell corner arc blended into "
                             "the boss (h6_fill_y); cell root fillets re-created; scans + flex test clean")
    p = os.path.join(L.GF_DIR, "25_export_frame.py")
    ns = {"__name__": "gf_script", "__file__": p}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    ns["run"](_context)
    path, info = docinfo("docinfo_partA.json")
    print("saved", ok, "version", ver, "doc", info["dataFile_id"], "params", len(info["user_parameters"]))
