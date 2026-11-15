"""40 - stage 2, Part C (READ-ONLY, resumable): every body of the imported board (292, DS1 shifted) against
  * the frame: min distance (measureMinimumDistance) + intersection volume when touching (temporary BReps)
  * every part body (all variants + socket cylinders) whose bounding box comes within 6 mm (else not measured)
Progress in scratchpad fit_board.json; ~45 s per call; call again until it prints DONE."""
import importlib
import json
import os
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)

OUT = os.path.join(L.SCR, "fit_board.json")
NEAR = 6.0
BUDGET = 45.0


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    st = json.load(open(OUT)) if os.path.exists(OUT) else {"results": []}
    done = {r["i"] for r in st["results"]}
    fr = A.frame()
    P = A.parts()
    bl = A.board()
    n = 0
    for i, (path, b) in enumerate(bl):
        if i in done:
            continue
        r = {"i": i, "path": path, "body": b.name, "bbox": L.bbox_mm(b), "ds1": A.ds1_part(path)}
        r["frame"] = A.pair(fr, b)
        near = []
        for cn, bn, pb, v in P:
            if A.bbox_gap(pb, b) > NEAR:
                continue
            q = A.pair(pb, b)
            q.update({"part": "%s / %s" % (cn, bn), "variant": v})
            near.append(q)
        r["parts"] = near
        st["results"].append(r)
        n += 1
        if time.time() - t0 > BUDGET:
            break
    json.dump(st, open(OUT, "w"), indent=1)
    left = len(bl) - len(st["results"])
    L.log("40 measured %d this call, %d left" % (n, left))
    print("DONE" if left == 0 else "MORE", n, left, round(time.time() - t0, 1))
