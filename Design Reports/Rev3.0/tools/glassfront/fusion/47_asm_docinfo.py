"""47 - stage 2 (READ-ONLY): final document info -> scratchpad docinfo_asm.json: document id / version / modified,
component tree (occurrence, light bulb, bodies with appearance / volume / bbox), timeline count + health, every user
parameter, plus two plan measurements for the report:
  * the print window as built: inner loop of the 'Glass print' body section at Z_GLASS_BACK - print_t / 2
  * the chin span: the opening of the frame section just behind the land face (Z_LAND + 0.01) around (gc_x, 135)."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)


def loops_bbox(body, z):
    tb = adsk.fusion.TemporaryBRepManager.get()
    pl = adsk.core.Plane.create(adsk.core.Point3D.create(0, 0, z / 10.0), adsk.core.Vector3D.create(0, 0, 1))
    w = tb.planeIntersection(tb.copy(body), pl)
    sh = tb.createFaceFromPlanarWires([w])
    out = []
    for i in range(sh.faces.count):
        f = sh.faces.item(i)
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            bb = None
            for k in range(lp.edges.count):
                b = lp.edges.item(k).boundingBox
                bb = b if bb is None else bb
                if bb is not b:
                    bb.combine(b)
            out.append({"outer": lp.isOuter, "bbox_abs": [round(bb.minPoint.x * 10, 4), round(bb.maxPoint.x * 10, 4),
                                                         round(-bb.maxPoint.y * 10, 4), round(-bb.minPoint.y * 10, 4)]})
    return out


def run(_context: str):
    d = L.check_doc()
    doc = L.app().activeDocument
    df = doc.dataFile
    r = L.root()
    tree = []
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        e = {"occurrence": o.name, "component": o.component.name, "visible": o.isLightBulbOn, "bodies": []}
        if o.component.name != L.BOARD_COMP:
            for k in range(o.bRepBodies.count):
                b = o.bRepBodies.item(k)
                e["bodies"].append({"name": b.name, "visible": b.isLightBulbOn,
                                    "appearance": b.appearance.name if b.appearance else None,
                                    "volume_mm3": round(b.volume * 1000, 3), "bbox_abs": L.bbox_mm(b)})
        else:
            e["occurrences_all_levels"] = o.component.allOccurrences.count
            e["bodies_all_levels"] = len(L.bodies_under(o))
            e["z_offset_mm"] = round(o.transform2.translation.z * 10, 4)
        tree.append(e)
    n, bad = L.timeline_health()
    ups = d.userParameters
    params = []
    for i in range(ups.count):
        p = ups.item(i)
        val = p.value * 10.0 if p.unit == "mm" else (p.value * 57.29577951308232 if p.unit == "deg" else p.value)
        params.append({"name": p.name, "expression": p.expression, "value": round(val, 6), "unit": p.unit,
                       "comment": p.comment})
    prt = A.part("Glass", "Glass print (black, 0.02)")
    pw = loops_bbox(prt, L.P("Z_GLASS_BACK") - L.P("print_t") / 2)
    land = loops_bbox(A.frame(), L.P("Z_LAND") + 0.01)
    chin = [lp for lp in land if not lp["outer"] and lp["bbox_abs"][0] < L.P("gc_x") < lp["bbox_abs"][1]
            and lp["bbox_abs"][2] < 135 < lp["bbox_abs"][3]]
    info = {"document": doc.name, "dataFile_id": df.id if df else None, "version": df.versionNumber if df else None,
            "isModified": doc.isModified, "timeline_count": n, "timeline_unhealthy": bad, "tree": tree,
            "user_parameters": params, "print_loops": pw, "land_plane_openings_around_chin": chin,
            "section_analyses": d.analyses.sectionAnalyses.count, "pending_snapshot": d.snapshots.hasPendingSnapshot}
    p = L.dump(info, "docinfo_asm.json")
    print(p, info["version"], info["isModified"], n, bad, len(params), pw, chin)
