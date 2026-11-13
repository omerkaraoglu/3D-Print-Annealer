"""Round 3: footprint position / orientation differences between two boards and item counts.
Usage: r3_diff.py before.kicad_pcb after.kicad_pcb"""
import sys, pcbnew
from collections import Counter
from common import *


def load(p):
    b = pcbnew.LoadBoard(p)
    fps = {f.GetReference(): (L(f.GetPosition()), f.GetOrientationDegrees()) for f in b.GetFootprints()}
    c = Counter(t.GetClass() for t in b.Tracks())
    c['GND vias'] = sum(1 for t in b.Tracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND')
    c['free GND vias'] = sum(1 for t in b.Tracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and t.GetIsFree())
    c['teardrop zones'] = sum(1 for z in b.Zones() if z.IsTeardropArea())
    c['rule areas'] = sum(1 for z in b.Zones() if z.GetIsRuleArea())
    c['washer keep-outs'] = sum(1 for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() == 'M3 washer keep-out')
    c['copper pours'] = sum(1 for z in b.Zones() if not z.GetIsRuleArea() and not z.IsTeardropArea())
    c['footprints'] = len(fps)
    c['Edge.Cuts items'] = sum(1 for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    return fps, c


a, ca = load(sys.argv[1]); b, cb = load(sys.argv[2])
for r in sorted(set(a) | set(b)):
    if a.get(r) is None or b.get(r) is None:
        print("  %-5s %s" % (r, 'added at %s' % (b[r],) if r in b else 'removed'))
    elif not close(a[r][0], b[r][0], 0.001) or abs(a[r][1] - b[r][1]) > 0.01:
        print("  %-5s (%.3f, %.3f) %.0f deg -> (%.3f, %.3f) %.0f deg" % (r, a[r][0][0], a[r][0][1], a[r][1], b[r][0][0], b[r][0][1], b[r][1]))
for k in sorted(set(ca) | set(cb)):
    print("  %-16s %6d -> %6d" % (k, ca[k], cb[k]))
