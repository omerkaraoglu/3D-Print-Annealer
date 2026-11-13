"""59 - v2.2 radial stud slots + stud fillets:
  * deletes 'Root fillets R0.5 - stud tubes + ribs' (30 edge references lost when the tubes/ribs grew in 58)
  * 'Stud FHn slot (radial)': stadium stud_hole x (stud_hole + stud_slot), axis = unit vector from the datum
    (datum_x, datum_y) to the hole centre, centred on (fhN_x, fhN_y), cut from Z_FRONT up through Z_STUD_TOP + 1
    with draft_loc widening to the back. FIXED sketch geometry computed from the parameters (two end circles +
    the rotated centre rectangle): re-run this script if a hole position, the datum, stud_hole or stud_slot changes.
  * re-fillets the stud set R0.5 (fv2lib.FILLET_SETS 'stud tubes + ribs', edges re-collected).
Expects: 58 done."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 59 start")
    f = L.feature("Root fillets R0.5 - stud tubes + ribs")
    if f is not None:
        f.deleteMe()
    b = L.body()
    dx0, dy0 = L.P("datum_x"), L.P("datum_y")
    h, s = L.P("stud_hole"), L.P("stud_slot")
    axes = []
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        x, y = L.P(n + "_x"), L.P(n + "_y")
        r = math.hypot(x - dx0, y - dy0)
        ux, uy = (x - dx0) / r, (y - dy0) / r
        nx, ny = -uy, ux
        cm = (x - s / 2 * ux, y - s / 2 * uy)
        cp = (x + s / 2 * ux, y + s / 2 * uy)
        pts = [(cm[0] + h / 2 * nx, cm[1] + h / 2 * ny), (cp[0] + h / 2 * nx, cp[1] + h / 2 * ny),
               (cp[0] - h / 2 * nx, cp[1] - h / 2 * ny), (cm[0] - h / 2 * nx, cm[1] - h / 2 * ny)]
        sk = L.new_sketch("Stud %s slot (radial)" % name, "Z_FRONT plane")
        lines = sk.sketchCurves.sketchLines
        first = prev = None
        for k in range(4):
            a = prev.endSketchPoint if prev is not None else L.P3(*pts[0])
            bpt = first.startSketchPoint if k == 3 else L.P3(*pts[k + 1])
            ln = lines.addByTwoPoints(a, bpt)
            first = first or ln
            prev = ln
        L.circle(sk, cm[0], cm[1], h, dims=False)
        L.circle(sk, cp[0], cp[1], h, dims=False)
        L.fix_all(sk)
        sk.isComputeDeferred = False
        prof = L.pick_profiles(sk, lambda a_, bb: True)
        L.extrude(prof, "cut", "Z_STUD_TOP - Z_FRONT + 1 mm", +1, L.grow("draft_loc"), "Stud %s slot (radial)" % name, b)
        axes.append((name, round(math.degrees(math.atan2(uy, ux)), 3)))
    ff, nf = L.fillet_set("stud tubes + ribs")
    nt, bad = L.timeline_health()
    L.log("59 slots %s; stud fillet %d edges; %s; timeline %d unhealthy %s" % (axes, nf, L.body_stats(), nt, bad))
    L.show_iso()
    print(axes, nf, L.body_stats(), nt, bad)
