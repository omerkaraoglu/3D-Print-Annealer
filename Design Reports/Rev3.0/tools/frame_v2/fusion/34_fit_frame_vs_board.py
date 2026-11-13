"""34 - READ-ONLY, resumable: minimum distance from the frame (linked occurrence proxy) to every body of the
imported board (proxies, board shifted +0.08), via measureManager.measureMinimumDistance. Bodies at distance
< 0.001 mm also get the intersection volume (TemporaryBRepManager boolean). Works ~40 s per call, keeps
progress in scratchpad/cad/fit_frame_board.json; call again until it prints DONE.
Expects: 33 census (same body order)."""
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

OUT = os.path.join(L.SCR, "fit_frame_board.json")


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    t0 = time.time()
    st = json.load(open(OUT)) if os.path.exists(OUT) else {"results": []}
    done = {r["i"] for r in st["results"]}
    board, bl = L.asm_bodies()
    focc, fb = L.frame_proxy()
    n = 0
    for i, (path, top, b) in enumerate(bl):
        if i in done:
            continue
        d, p1, p2 = L.min_dist_mm(fb, b)
        r = {"i": i, "path": path, "d_mm": round(d, 4),
             "p_frame": [round(p1.x * 10, 3), round(-p1.y * 10, 3), round(p1.z * 10, 3)],
             "p_body": [round(p2.x * 10, 3), round(-p2.y * 10, 3), round(p2.z * 10, 3)],
             "bbox": L.bbox_mm(b)}
        if d < 0.001:
            r["overlap_mm3"] = round(L.overlap_volume_mm3(fb, b), 5)
        st["results"].append(r)
        n += 1
        if time.time() - t0 > 40:
            break
    json.dump(st, open(OUT, "w"), indent=1)
    left = len(bl) - len(st["results"])
    L.log("34 measured %d this call, %d left" % (n, left))
    print("DONE" if left == 0 else "MORE", n, left)
