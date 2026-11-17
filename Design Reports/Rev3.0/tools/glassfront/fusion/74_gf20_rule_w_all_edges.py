"""74 - stage 4 (GF-2.0): flex test 71 (frame_v2) left one failure, at glass 1.1 (level snap):
'Root fillets R0.5 - outer wall to the flange plate (rule)' finds no edge there, because at the snap the flange back
and the land-plate back are one face (attributed to 'Land plate + step wall (back)') and the rule W before it has
already rounded the outer wall on it. The three root pairs - step wall / flange back (not at the snap), outer wall /
land-plate back (always), outer wall / flange back (below the board edge, not at the snap) - cannot be split into
two BETWEEN sets, and every rule must find at least one edge in every state. So both rules are replaced by ONE rule
at W's timeline position, same name 'Root fillets R0.5 - wall + step wall to plates (rule)':
    ALL concave edges of the faces of ['Land plate + step wall (back)', 'Outer wall block']
(never empty: the outer wall always stands on the land plate). R1 is deleted. Expected at glass 3.0: same volume and
the same unfilleted-root census as after 73."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

N_W = "Root fillets R0.5 - wall + step wall to plates (rule)"
N_R1 = "Root fillets R0.5 - outer wall to the flange plate (rule)"


def run(_context: str):
    d = L.check_doc()
    L.log("=== 74 start")
    tl = d.timeline
    if L.feature(N_R1) is None:
        raise RuntimeError("74 already applied (no R1)")
    v0, f0 = L.body().volume, L.body().faces.count
    L.feature(N_R1).deleteMe()
    w = L.feature(N_W)
    nxt = tl.item(w.timelineObject.index + 1)
    w.deleteMe()
    nxt.rollTo(True)
    f = L.rule_fillet(N_W, "all", ["Land plate + step wall (back)", "Outer wall block"])
    nf = f.faces.count
    tl.moveToEnd()
    d.computeAll()
    n, bad = L.timeline_health()
    roots = {}
    for g, e, m, z, o in L.root_edges(0.9):
        roots[g] = roots.get(g, 0) + 1
    res = {"W_faces": nf, "timeline": n, "unhealthy": bad, "volume_before": round(v0, 5),
           "volume_after": round(L.body().volume, 5), "faces_before": f0, "faces_after": L.body().faces.count,
           "roots": roots}
    L.dump(res, "gf20/74_rule_w.json")
    L.log("74 %s" % res)
    if bad:
        raise RuntimeError(bad)
    print(res)
