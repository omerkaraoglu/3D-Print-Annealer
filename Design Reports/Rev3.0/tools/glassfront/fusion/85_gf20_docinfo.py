"""85 - stage 4 (GF-2.0), READ-ONLY document info for the reports: document / data file / versions (number, comment),
timeline (count, health, the Frame GF features in order), user parameters (GF-2.0 ones with expressions), component
tree (occurrences, bodies, visibility). Writes gf20/docinfo.json."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

GF20_PARAMS = ["border", "glass_y1", "g_bend", "bend_y1", "bend_nose_R", "land_break", "tail_R_in_min", "tail_straight_l0",
               "tail_t", "Z_TAIL_LEG", "div_x", "div_t", "flange_y1_bottom", "fl_y1", "Z_FLOOR_LOW", "Z_WALL_FRONT",
               "Z_DISC_FRONT", "s_disc_front", "logo_h", "logo_cy", "gc_y", "f_y1"]


def run(_context: str):
    d = L.check_doc()
    app = L.app()
    doc = app.activeDocument
    df = doc.dataFile
    vers = []
    try:
        vs = df.versions
        for i in range(vs.count):
            v = vs.item(i)
            vers.append({"version": v.versionNumber, "comment": getattr(v, "description", None)})
    except Exception as ex:
        vers = [str(ex)]
    tl = d.timeline
    n, bad = L.timeline_health()
    items = []
    for i in range(tl.count):
        it = tl.item(i)
        items.append(it.name)
    r = L.root()
    tree = []
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        c = o.component
        tree.append({"occurrence": o.name, "visible": o.isLightBulbOn,
                     "bodies": [{"name": c.bRepBodies.item(k).name, "visible": c.bRepBodies.item(k).isLightBulbOn}
                                for k in range(c.bRepBodies.count)], "children": o.childOccurrences.count})
    ups = d.userParameters
    prm = {}
    for nm in GF20_PARAMS:
        p = ups.itemByName(nm)
        if p:
            prm[nm] = {"expression": p.expression, "value_mm": round(p.value * 10, 4), "comment": p.comment}
    res = {"document": doc.name, "dataFile_id": df.id, "version": df.versionNumber, "isModified": doc.isModified,
           "versions": vers, "timeline_count": n, "timeline_unhealthy": bad, "timeline_items": items,
           "user_parameters": ups.count, "gf20_parameters": prm, "component_tree": tree,
           "guard": d.attributes.itemByName("gf", "doc").value}
    L.dump(res, DUMP + "/docinfo.json")
    print({k: v for k, v in res.items() if k not in ("timeline_items", "component_tree", "gf20_parameters")})
