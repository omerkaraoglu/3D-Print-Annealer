"""35 - fit checks of the assembly parts + tool access:
  * Formex sheet / gasket / oven-sheet patch vs frame: min distance + intersection volume
  * Formex sheet vs every board body (lead tips through the PCB): min distance (filtered later by ref)
  * tool access: component 'Check - socket cylinders (hidden)' with ten dia-12 cylinders from Z -6.5 to +45 at
    FH1..FH10 (the M4 nut socket); min distance of each to the PCB solid and every component body whose XY bbox
    comes within 25 mm (all others are farther by construction); the component is hidden afterwards.
Writes scratchpad/cad/fit_parts.json. Expects: 34 done."""
import importlib
import json
import math
import os
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

OUT = os.path.join(L.SCR, "fit_parts.json")
CYL = "Check - socket cylinders (hidden)"


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    t0 = time.time()
    root = L.root()
    focc, fb = L.frame_proxy()
    res = {}
    parts = {n: L.part_body(n) for n in ("Formex sheet", "Gasket (compressed)", "Oven sheet patch")}
    for n, b in parts.items():
        d, p1, p2 = L.min_dist_mm(fb, b)
        res[n + " vs frame"] = {"d_mm": round(d, 4), "overlap_mm3": round(L.overlap_volume_mm3(fb, b), 5),
                                "p_frame": [round(p1.x * 10, 3), round(-p1.y * 10, 3), round(p1.z * 10, 3)]}
    board, bl = L.asm_bodies()
    sheet = parts["Formex sheet"]
    sv = []
    for i, (path, top, b) in enumerate(bl):
        bb = L.bbox_mm(b)
        if bb[4] > -1.0:                       # nothing below Z -1 cannot come near the sheet (Z -5..-4.6)
            continue
        d, p1, p2 = L.min_dist_mm(sheet, b)
        r = {"i": i, "path": path, "d_mm": round(d, 4), "bbox": bb}
        if d < 0.001:
            r["overlap_mm3"] = round(L.overlap_volume_mm3(sheet, b), 4)
        sv.append(r)
    res["sheet_vs_board"] = sv
    # tool access cylinders
    cyl_occ = None
    for i in range(root.occurrences.count):
        if root.occurrences.item(i).component.name == CYL:
            cyl_occ = root.occurrences.item(i)
    if cyl_occ is None:
        cyl_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        cyl_occ.component.name = CYL
        tb = adsk.fusion.TemporaryBRepManager.get()
        xy = [(L.P("fh%d_x" % k), L.P("fh%d_y" % k)) for k in range(1, 11)]   # read BEFORE the base-feature edit
        bf = cyl_occ.component.features.baseFeatures.add()
        bf.startEdit()
        for k in range(1, 11):
            x, y = xy[k - 1]
            c = tb.createCylinderOrCone(adsk.core.Point3D.create(x / 10, -y / 10, -0.65), 0.6,
                                        adsk.core.Point3D.create(x / 10, -y / 10, 4.5), 0.6)
            nb = cyl_occ.component.bRepBodies.add(c, bf)
            nb.name = "socket FH%d" % k
        bf.finishEdit()
    acc = []
    for k in range(cyl_occ.bRepBodies.count):
        cb = cyl_occ.bRepBodies.item(k)
        cbb = L.bbox_mm(cb)
        best = None
        for i, (path, top, b) in enumerate(bl):
            bb = L.bbox_mm(b)
            if "TFT7" in path:
                continue
            gx = max(bb[0] - cbb[1], cbb[0] - bb[1], 0)
            gy = max(bb[2] - cbb[3], cbb[2] - bb[3], 0)
            if math.hypot(gx, gy) > 25:
                continue
            d, p1, p2 = L.min_dist_mm(cb, b)
            if best is None or d < best["d_mm"]:
                best = {"d_mm": round(d, 4), "path": path, "bbox": bb,
                        "p_body": [round(p2.x * 10, 3), round(-p2.y * 10, 3), round(p2.z * 10, 3)]}
        acc.append({"hole": cb.name.replace("socket ", ""), "nearest": best})
    cyl_occ.isLightBulbOn = False
    res["tool_access"] = acc
    json.dump(res, open(OUT, "w"), indent=1)
    L.log("35 parts/tool access done in %.0f s" % (time.time() - t0))
    print({k: v for k, v in res.items() if k.endswith("frame")}, [(a["hole"], a["nearest"]["d_mm"] if a["nearest"] else None) for a in acc])
