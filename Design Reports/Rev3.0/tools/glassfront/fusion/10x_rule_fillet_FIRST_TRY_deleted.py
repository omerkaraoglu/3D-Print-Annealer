"""10x - (FIRST TRY, deleted again: with the land-plate feature in BOTH sets the rule filleted the wrong edges and missed the tube roots; see diag_rule_fillet_probe.py) root fillet R0.5 round the fastener tubes, the tube ribs and the step wall's back part, as a RULE FILLET
"between features" (fillets only = concave edges):
    set one: 'Fastener tubes F1-F8', 'Tube ribs F1-F4', 'Land plate + step wall (back)'
    set two: 'Flange plate', 'Land plate + step wall (back)', 'Fastener tubes F1-F8'
Why a rule and not an edge set: these are the only roots whose TOPOLOGY changes with glass_t (tube top above /
below the step-wall back at glass 3.5; the step-wall face behind the flange vanishes at the level snap, glass 1.1).
A rule fillet re-collects its edges on every recompute, so the flex test keeps a healthy timeline; an edge-set
fillet would lose its references.
Expects: 07 (07b) done; no other fillet yet (this is the first fillet in the timeline, as v2's stud fillet)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

ONE = ["Fastener tubes F1-F8", "Tube ribs F1-F4", "Land plate + step wall (back)"]
TWO = ["Flange plate", "Land plate + step wall (back)", "Fastener tubes F1-F8"]
NAME = "Root fillets R0.5 - tubes, tube ribs, step wall to flange back (rule)"


def run(_context: str):
    L.check_doc()
    L.log("=== 10 start")
    ff = L.comp().features.filletFeatures
    ri = ff.createRuleFilletInput()
    ok = ri.setByBetweenFacesOrFeatures([L.feature(n) for n in ONE], [L.feature(n) for n in TWO])
    if not ok:
        raise RuntimeError("setByBetweenFacesOrFeatures failed")
    ri.radius = L.VI("fillet_root")
    ri.topologyType = adsk.fusion.RuleFilletTopologyTypes.FilletsOnlyRuleFilletTopologyType
    ri.isRollingBallCorner = True
    f = ff.addRuleFillet(ri)
    f.name = NAME
    n, bad = L.timeline_health()
    L.log("10 rule fillet: %d faces; %s; timeline %d unhealthy %s" % (f.faces.count, L.body_stats(), n, bad))
    print(f.faces.count, L.body_stats(), n, bad)
