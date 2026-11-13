"""42 - v2.1 support ribs (coordinator item 4): the 26 ribs are rebuilt with their free ends running 0.5 past
the shelf edge (and, for the six ribs over the tail pocket, past the shelf end) and are INSERTED IN THE TIMELINE
BEFORE THE 'Window' CUT (marker rolled back), so the Window and Tail-pocket cuts trim them flush on their drafted
faces: no land, no free-end root. Position, width, wall burial unchanged (v1 rib list). Ribs that
rib_pad_check.py had to keep at v1 length (pad < 1.0 mm) would stay v1 - none did (min 1.147, J4.1, rib 3).
Expects: 41 done (Window cut reaches Z_PCB + 1)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 42 start")
    tl = L.des().timeline
    win = L.feature("Window")
    win.timelineObject.rollTo(True)
    b = L.body()
    rects = L.rib_rects_v21()
    sk = L.new_sketch("PCB support ribs (26)", "Z_SHELF_BACK plane")
    for (k, side, ext, x0, x1, y0, y1) in rects:
        L.rrect(sk, x0, x1, y0, y1, None, dims=False)
    L.fix_all(sk)
    sk.isComputeDeferred = False
    prof = L.pick_profiles(sk, lambda a, bb: True)
    if prof.count != 26:
        tl.moveToEnd()
        raise RuntimeError("rib profiles %d" % prof.count)
    L.extrude(prof, "join", "Z_PCB - Z_SHELF_BACK", +1, L.shrink(), "PCB support ribs (26)", b)
    tl.moveToEnd()
    n, bad = L.timeline_health()
    L.log("42 ribs %s; timeline %d unhealthy %s; extended %d" % (L.body_stats(), n, bad,
                                                                  sum(1 for r in rects if r[2])))
    L.show_iso()
    print(L.body_stats(), n, bad)
