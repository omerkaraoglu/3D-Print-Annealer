"""33 - READ-ONLY census of the fit assembly: every body under the board occurrence (path, top-level ref,
body name, world bbox abs x / y-down / Z), plus the frame and the three parts. Writes scratchpad/cad/census.json.
Expects: 32 done."""
import importlib
import json
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    board, bl = L.asm_bodies()
    out = []
    for i, (path, top, b) in enumerate(bl):
        out.append({"i": i, "path": path, "top": top, "body": b.name, "bbox": L.bbox_mm(b)})
    focc, fb = L.frame_proxy()
    res = {"board_occ": board.name, "board_dz_mm": round(board.transform2.translation.z * 10, 4),
           "n_bodies": len(out), "frame_bbox": L.bbox_mm(fb), "bodies": out,
           "tops": sorted(set(o["top"] for o in out))}
    json.dump(res, open(os.path.join(L.SCR, "census.json"), "w"), indent=1)
    L.log("33 census: %d bodies, %d top refs, board dz %.3f" % (len(out), len(res["tops"]), res["board_dz_mm"]))
    print(len(out), len(res["tops"]), res["board_dz_mm"])
