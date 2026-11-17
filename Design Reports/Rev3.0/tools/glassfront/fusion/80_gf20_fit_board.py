"""80 - stage 4 (GF-2.0), READ-ONLY, resumable (40 adapted): every VISIBLE body of the imported board against
  * the frame: bbox gap; if within 6 mm the min distance + intersection volume when touching
  * every part body (S4, R4 hidden bodies, socket check cylinders, GF-2.0 tails) whose bbox comes within 6 mm
The hidden GF-1.1 reference tail bodies (70) are skipped. Progress in %TEMP%\\rev3_glassfront\\gf20\\fit_board.json;
~45 s per call; call again until it prints DONE (delete the file to start over)."""
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
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

OUT = os.path.join(L.SCR, DUMP, "fit_board.json")
NEAR = 6.0
BUDGET = 45.0


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    st = json.load(open(OUT)) if os.path.exists(OUT) else {"results": [], "skipped_hidden": []}
    done = {r["i"] for r in st["results"]} | {r["i"] for r in st["skipped_hidden"]}
    fr = A.frame()
    P = A.parts() + [(A.TAIL_COMP, n, b, "S4") for n, b in A.tails()]
    bl = A.board()
    n = 0
    for i, (path, b) in enumerate(bl):
        if i in done:
            continue
        if not b.isVisible:
            st["skipped_hidden"].append({"i": i, "path": path, "body": b.name})
            continue
        r = {"i": i, "path": path, "body": b.name, "bbox": L.bbox_mm(b), "ds1": A.ds1_part(path)}
        g = A.bbox_gap(fr, b)
        r["frame_bbox_gap"] = round(g, 3)
        if g <= NEAR:
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
    left = len(bl) - len(st["results"]) - len(st["skipped_hidden"])
    L.log("80 measured %d this call, %d left" % (n, left))
    print("DONE" if left == 0 else "MORE", n, left, round(time.time() - t0, 1))
