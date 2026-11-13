"""51 - v2.1 fit checks of the assembly parts + tool access (replaces 35):
  * frame volume check (linked occurrence = v2.1), Formex sheet / gasket / oven-sheet patch vs frame
    (min distance + intersection volume), Formex sheet vs every board body reaching below Z -1 (lead tips)
  * tool access (coordinator item 1): 'socket FHn' (dia 12, Z -6.5 .. +45) vs ALL board bodies INCLUDING DS1
    (nearest body per hole + every body within 3 mm, so the J3/J4/R1 wire stubs show up by name);
    'socket above tube FHn' (dia 12 from Z_STUD_TOP + 0.01 up) vs the frame itself (wall, bosses)
Writes scratchpad/cad/fit_parts.json. Expects: 50 done."""
import importlib
import json
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
    res = {"frame_volume_cm3": round(fb.physicalProperties.volume, 4)}
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
        if bb[4] > -1.0:
            continue
        d, p1, p2 = L.min_dist_mm(sheet, b)
        r = {"i": i, "path": path, "d_mm": round(d, 4), "bbox": bb}
        if d < 0.001:
            r["overlap_mm3"] = round(L.overlap_volume_mm3(sheet, b), 4)
        sv.append(r)
    res["sheet_vs_board"] = sv
    cyl = [root.occurrences.item(i) for i in range(root.occurrences.count)
           if root.occurrences.item(i).component.name == CYL][0]
    acc, wall = [], []
    for k in range(cyl.bRepBodies.count):
        cb = cyl.bRepBodies.item(k)
        if cb.name.startswith("socket above tube"):
            d, p1, p2 = L.min_dist_mm(cb, fb)
            wall.append({"hole": cb.name.replace("socket above tube ", ""), "d_mm": round(d, 4),
                         "p_frame": [round(p2.x * 10, 3), round(-p2.y * 10, 3), round(p2.z * 10, 3)]})
            continue
        cbb = L.bbox_mm(cb)
        near = []
        for i, (path, top, b) in enumerate(bl):
            bb = L.bbox_mm(b)
            gx = max(bb[0] - cbb[1], cbb[0] - bb[1], 0)
            gy = max(bb[2] - cbb[3], cbb[2] - bb[3], 0)
            if (gx * gx + gy * gy) ** 0.5 > 25:
                continue
            d, p1, p2 = L.min_dist_mm(cb, b)
            r = {"d_mm": round(d, 4), "path": path, "bbox": bb,
                 "p_body": [round(p2.x * 10, 3), round(-p2.y * 10, 3), round(p2.z * 10, 3)]}
            if d < 0.001:
                r["overlap_mm3"] = round(L.overlap_volume_mm3(cb, b), 4)
            near.append(r)
        near.sort(key=lambda r: r["d_mm"])
        acc.append({"hole": cb.name.replace("socket ", ""), "nearest": near[0] if near else None,
                    "within_3mm": [r for r in near if r["d_mm"] < 3.0], "n_checked": len(near)})
    res["tool_access"] = acc
    res["socket_vs_frame_wall"] = wall
    json.dump(res, open(OUT, "w"), indent=1)
    L.log("51 done in %.0f s" % (time.time() - t0))
    print(res["frame_volume_cm3"], {k: v for k, v in res.items() if k.endswith("frame")},
          [(a["hole"], a["nearest"]["d_mm"] if a["nearest"] else None) for a in acc],
          [(w["hole"], w["d_mm"]) for w in wall])
