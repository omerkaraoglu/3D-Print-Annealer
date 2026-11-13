"""52 - READ-ONLY socket-to-frame-wall clearance (coordinator item 1, 'expect >= 1.5 at 7.5 offset'): min
distance from each dia-12 socket cylinder 'socket FHn' (Z -6.5 .. +45) to the frame faces that rise above the
DIN 9021 washer top (bbox zmax > Z_STUD_TOP + 1.0 = -5.02: outer wall, PCB bosses, tail walls) within 12 mm of
the hole in plan. The stud tube top, the rib top and their fillets lie under the washer (zmax -6.02) and are
excluded (the washer, not the socket, sits there). Appends 'socket_vs_frame_wall' to scratchpad/cad/fit_parts.json.
Expects: 51 done."""
import importlib
import json
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

CYL = "Check - socket cylinders (hidden)"
WASHER_TOP = -6.02 + 1.0


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    root = L.root()
    focc, fb = L.frame_proxy()
    cyl = [root.occurrences.item(i) for i in range(root.occurrences.count)
           if root.occurrences.item(i).component.name == CYL][0]
    out = []
    for k in range(cyl.bRepBodies.count):
        cb = cyl.bRepBodies.item(k)
        if not cb.name.startswith("socket FH"):
            continue
        cbb = cb.boundingBox
        cx, cy = (cbb.minPoint.x + cbb.maxPoint.x) * 5, (cbb.minPoint.y + cbb.maxPoint.y) * 5
        best = None
        for i in range(fb.faces.count):
            f = fb.faces.item(i)
            bb = f.boundingBox
            if bb.maxPoint.z * 10 <= WASHER_TOP:
                continue
            gx = max(bb.minPoint.x * 10 - cx, cx - bb.maxPoint.x * 10, 0)
            gy = max(bb.minPoint.y * 10 - cy, cy - bb.maxPoint.y * 10, 0)
            if (gx * gx + gy * gy) ** 0.5 > 12:
                continue
            d, p1, p2 = L.min_dist_mm(cb, f)
            if best is None or d < best["d_mm"]:
                best = {"d_mm": round(d, 4), "p_frame": [round(p2.x * 10, 3), round(-p2.y * 10, 3), round(p2.z * 10, 3)],
                        "face_area_mm2": round(f.area * 100, 2)}
        out.append(dict(best or {}, hole=cb.name.replace("socket ", "")))
    p = os.path.join(L.SCR, "fit_parts.json")
    d = json.load(open(p))
    d["socket_vs_frame_wall"] = out
    json.dump(d, open(p, "w"), indent=1)
    print([(o["hole"], o.get("d_mm"), o.get("p_frame")) for o in out])
