"""69 - stage 4 (GF-2.0): 'Divider rib (bridge, low)' extrudes BOTH profiles of 'Divider rib (bridge) sketch'
(bridge face .. step-wall back + rib_bury) to Z_PCB; 'Divider rib (bridge, high)' keeps the back piece (tail-wall step
.. end) to Z_TROUGH_TOP. With the front piece only, the low and the high part met on a shared sketch edge whose two
tapered faces diverge upwards (a 2 x 1 deg V, 0.28 wide at Z 0); the model was solid there (68's rule fillet closed
it), but the overlap makes the step face = the high part's front face by construction (as the tail-wall block step)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    d = L.check_doc()
    L.log("=== 69 start")
    tl = d.timeline
    sk = L.comp().sketches.itemByName("Divider rib (bridge) sketch")
    f = L.feature("Divider rib (bridge, low)")
    v0 = L.body().volume
    if sk.profiles.count != 2:
        raise RuntimeError("profiles %d" % sk.profiles.count)
    f.timelineObject.rollTo(True)
    f.profile = L.pick_profiles(sk)
    tl.moveToEnd()
    d.computeAll()
    n, bad = L.timeline_health()
    out = {"volume_before": round(v0, 5), "volume_after": round(L.body().volume, 5), "timeline": n, "unhealthy": bad,
           "frame": L.body_dict()}
    L.log("69 %s" % out)
    if bad:
        raise RuntimeError(bad)
    print(out)
