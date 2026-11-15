"""44 - stage 2, Part D: batched visibility switch of the board's first-level occurrences EXCEPT the panel DS1
(TFT7_SAT070AT40D21), at most 40 per call (v2 36b rule: never toggle hundreds of occurrences in one script).
SHOW = False hides the PCB and every component model (for 'back_no_PCB'), True restores. Re-run until DONE."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

SHOW = False


def run(_context: str):
    L.check_doc()
    board = L.occ_by_comp(L.BOARD_COMP)
    ch = board.childOccurrences.item(0).childOccurrences
    n = left = 0
    for i in range(ch.count):
        o = ch.item(i)
        if o.name.startswith("TFT7"):
            continue
        if o.isLightBulbOn != SHOW:
            if n < 40:
                o.isLightBulbOn = SHOW
                n += 1
            else:
                left += 1
    # the PCB body itself sits in the 'board_full' component
    top = board.childOccurrences.item(0)
    for k in range(top.bRepBodies.count):
        top.bRepBodies.item(k).isLightBulbOn = SHOW
    L.log("44 SHOW=%s switched %d, left %d" % (SHOW, n, left))
    print("DONE" if left == 0 else "MORE", n, left, "top bodies", top.bRepBodies.count)
