"""15 - FIX: 0.153 mm ledge at Z_PCB in front of the two tail walls.
The 'Tail wall block' end line (y = pocket_y1 at Z_FRONT, 1 deg draft) and the 'Above-shelf space' face
(y = pocket_y1 at Z_SHELF_BACK, 1 deg draft) are parallel planes 0.153 apart at Z_PCB, leaving a 0.15 wide
strip of wall top in front of each tail wall (found when its R0.5 root fillet failed: ASM_BL_CAP_COMPLEX).
Fix: the block's end line becomes pocket_y1 - (Z_SHELF_BACK - Z_FRONT) * tan(draft) at Z_FRONT, i.e. the block's
end face lies IN the pocket face plane; the panel pocket / above-shelf cuts (later in the timeline) trim the
block where it enters the pocket, above Z_SHELF_BACK the tail walls continue the pocket face with no step.
Expects: 14a done (stud fillets). Edits the sketch dimension driven by 'pocket_y1' in 'Tail wall block sketch'.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

NEW = "pocket_y1 - ( Z_SHELF_BACK - Z_FRONT ) * tan(draft)"


def run(_context: str):
    L.check_doc()
    L.log("=== 15 start")
    sk = L.root().sketches.itemByName("Tail wall block sketch")
    hit = 0
    for i in range(sk.sketchDimensions.count):
        d = sk.sketchDimensions.item(i)
        if d.parameter is not None and d.parameter.expression.strip() == "pocket_y1":
            d.parameter.expression = NEW
            hit += 1
    if hit != 1:
        raise RuntimeError("expected one 'pocket_y1' dimension, found %d" % hit)
    L.set_param("tail_wall_y0", NEW, "mm",
                "v2: tail-wall block end line at Z_FRONT, so its drafted end face lies in the pocket face plane")
    n, bad = L.timeline_health()
    L.log("15 %s; timeline %d unhealthy %s" % (L.body_stats(), n, bad))
    L.show_iso()
    print(L.body_stats(), n, bad)
