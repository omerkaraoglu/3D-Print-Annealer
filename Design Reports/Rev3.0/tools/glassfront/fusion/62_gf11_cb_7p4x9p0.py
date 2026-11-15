"""62 - stage 3 follow-up (GF-1.1, lead round 2): counterbore enlarged to slot + 1.0 per side,
cb_w 7.2 -> 7.4 and cb_l 8.8 -> 9.0 (both user parameters only; depths, cb_r, draft unchanged). Checks the timeline
health and logs the body; the flex test (90, TAG gf11c) and the scratch scan (53, TAG_SUFFIX cb74) are run after it
with their module globals set by the runner."""
import importlib
import sys

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

NEW = {"cb_w": ("7.4 mm", "GF-1.1 (lead round 2): counterbore width at its opening = slot_w + 2 x 1.0 (was 7.2)"),
       "cb_l": ("9.0 mm", "GF-1.1 (lead round 2): counterbore length at its opening = slot_l + 2 x 1.0 (was 8.8)")}


def run(_context: str):
    d = L.check_doc()
    L.log("=== 62 start")
    ups = d.userParameters
    old = {}
    for n, (expr, cm) in NEW.items():
        p = ups.itemByName(n)
        old[n] = p.expression
        p.expression = expr
        p.comment = cm
    d.computeAll()
    n, bad = L.timeline_health()
    L.log("62 %s -> %s; timeline %d unhealthy %s; %s" % (old, {k: v[0] for k, v in NEW.items()}, n, bad,
                                                           L.body_stats()))
    print(old, n, bad, L.body_stats())
