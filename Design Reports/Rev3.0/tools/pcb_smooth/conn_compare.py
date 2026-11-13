"""Compare net -> pad connectivity of two boards (pad nets, and copper connectivity: the pads each net's copper joins,
from pcbnew's connectivity, plus the unconnected count).  Usage: conn_compare.py before.kicad_pcb after.kicad_pcb"""
import sys, pcbnew
def sig(path):
    b = pcbnew.LoadBoard(path); b.BuildConnectivity(); c = b.GetConnectivity()
    nets = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            nets.setdefault(p.GetNetname(), set()).add("%s.%s" % (fp.GetReference(), p.GetNumber()))
    return nets, c.GetUnconnectedCount(True), len(b.GetNetInfo().NetsByName())
a, ua, na = sig(sys.argv[1]); b, ub, nb = sig(sys.argv[2])
print("nets with pads: before %d after %d | board nets %d / %d | unconnected before %d after %d" % (len(a), len(b), na, nb, ua, ub))
diff = 0
for n in sorted(set(a) | set(b)):
    if a.get(n, set()) != b.get(n, set()):
        diff += 1
        print("  %-24s removed %s added %s" % (n, sorted(a.get(n, set()) - b.get(n, set())), sorted(b.get(n, set()) - a.get(n, set()))))
print("nets that differ:", diff)
