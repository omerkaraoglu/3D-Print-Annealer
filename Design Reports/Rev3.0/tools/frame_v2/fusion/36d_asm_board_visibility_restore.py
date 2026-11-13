"""36d - (copy of 36b with SHOW = True) batched visibility switch for the board's first-level occurrences EXCEPT the panel (TFT7_SAT070AT40D21),
at most 40 per call (memory note: never toggle hundreds of occurrences in one script). SHOW = False hides
(PCB + all components), True restores. Re-run until it prints DONE.
Expects: 36a done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

SHOW = True


def run(_context: str):
    L.check_doc("Rev3.0 Frame v2 fit assembly")
    board, bl = L.asm_bodies()
    ch = board.childOccurrences.item(0).childOccurrences
    n = 0
    left = 0
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
    L.log("36b SHOW=%s switched %d, left %d" % (SHOW, n, left))
    print("DONE" if left == 0 else "MORE", n, left)
