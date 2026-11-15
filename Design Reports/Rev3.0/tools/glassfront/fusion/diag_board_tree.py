"""diag (stage 2) - READ-ONLY: structure of the imported board: top-level children, the DS1 (TFT7 / SAT070) subtree
with every body's bbox (abs x / y-down / Z), body count; occurrence transforms of the board and DS1."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    o = L.occ_by_comp(L.BOARD_COMP)
    print("board occ", o.name, "z", round(o.transform2.translation.z * 10, 4), "children", o.childOccurrences.count,
          "all", o.component.allOccurrences.count)
    lvl1 = o.childOccurrences
    names = [lvl1.item(i).name for i in range(lvl1.count)]
    print("level1:", names[:10])
    if lvl1.count == 1:
        lvl2 = lvl1.item(0).childOccurrences
        names2 = [lvl2.item(i).name for i in range(lvl2.count)]
        print("level2 count", lvl2.count, names2[:40])
    allb = L.bodies_under(o)
    print("bodies", len(allb))
    for path, b in allb:
        if "TFT7" in path or "SAT070" in path:
            print(" DS1", path, b.name, L.bbox_mm(b))
    for path, b in allb[:6]:
        print(" first", path, b.name, L.bbox_mm(b))
