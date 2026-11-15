"""10 - root fillets R0.5 of everything except the fastener tubes / tube ribs, placed in the timeline BEFORE the
'Fastener tubes F1-F8 sketch' (the marker is rolled back there and moved to the end afterwards; in a clean rebuild
run 10 before 07, the roll-back is then a no-op).

Why before the tubes: at glass 2.0 / 3.0 the tube-rib top is flush with the step-wall / land-plate back, the faces
merge and the merged face counts as a face of the rib feature; any rule or ownership-based selection made AFTER the
ribs then changes with glass_t (diag_rule_fillet_probe2). Before the tubes the land-plate back is still its own face.

Order (v2 order: bosses, cells, rib sides, shelf back, wall to flange, shelf front, tail walls):
  edge sets (gflib.EDGE_SETS, topology independent of glass_t / t_sheet / t_opt):
    'PCB bosses on the walls'                  boss <-> land-plate back and boss <-> outer wall (H1-H5, H8, H9)
    'corner cells + cell ribs + cell bosses'   cells, cell ribs, H6 / H7
    'PCB support rib sides'                    26 ribs (free ends are trimmed flush: no free-end roots)
    'shelf back (not into the tail pocket)'    v2 rule; 2 bottom segments stay sharp (v2 corners 3 / 4)
  RULE fillet (fillets only) 'wall + step wall to plates (rule)': between ['Land plate + step wall (back)'] and
    ['Flange plate', 'Outer wall block', 'Tail wall block'] = step wall <-> flange back (vanishes at the level snap,
    glass 1.1) + outer wall / bottom beam <-> land-plate back (always there, so the rule never runs empty).
  edge sets: 'shelf front (pocket)', 'tail walls to wall top'.
Expects: 07 / 07b done (or not yet: then the fillets are simply appended), 06 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

SETS_A = ["PCB bosses on the walls", "corner cells + cell ribs + cell bosses", "PCB support rib sides",
          "shelf back (not into the tail pocket)"]
SETS_B = ["shelf front (pocket)", "tail walls to wall top"]
RULE_W = ("Root fillets R0.5 - wall + step wall to plates (rule)", ["Land plate + step wall (back)"],
          ["Flange plate", "Outer wall block", "Tail wall block"])


def check(tag):
    n, bad = L.timeline_health()
    if bad:
        raise RuntimeError("unhealthy after %s: %s" % (tag, bad))
    return n


def run(_context: str):
    L.check_doc()
    L.log("=== 10 start")
    tl = L.des().timeline
    sk = L.comp().sketches.itemByName("Fastener tubes F1-F8 sketch")
    if sk is not None:
        sk.timelineObject.rollTo(True)
    out = []
    for s in SETS_A:
        f, k = L.fillet_set(s)
        out.append((s, k))
        check(s)
    f = L.rule_fillet(RULE_W[0], "between", RULE_W[1], RULE_W[2])
    out.append(("wall + step wall (rule)", f.faces.count))
    check("rule W")
    for s in SETS_B:
        f, k = L.fillet_set(s)
        out.append((s, k))
        check(s)
    tl.moveToEnd()
    n = check("move to end")
    L.log("10 %s; %s; timeline %d" % (out, L.body_stats(), n))
    print(out, L.body_stats(), n)
