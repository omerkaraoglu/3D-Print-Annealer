"""Print every symbol of a sheet with its lib pins (local coords, rot 0) and baseline nets: input for the layout design."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, BASELINE, Doc, Target, getprop, first  # noqa

t = Target(os.path.join(BASELINE, "baseline.xml"), BASELINE)
for sheet in sys.argv[1:]:
    doc = Doc(os.path.join(BASELINE, FILES[sheet]), sheet)
    print("=" * 20, sheet)
    for ref in sorted(doc.symbols, key=lambda r: (r.rstrip("0123456789"), int("0" + "".join(c for c in r if c.isdigit())))):
        node = doc.symbols[ref]
        lib = doc.lib_of(ref)
        x, y, rot, mir, unit = doc.placement(node)
        b = lib.body(unit)
        print("%s %s val=%r body=%s" % (ref, lib.name, getprop(node, "Value"), tuple(round(v, 2) for v in b) if b else None))
        for p in lib.unit_pins(unit):
            net = t.pin_net.get((ref, p["num"]), "?")
            print("    %4s %-12s %-14s (%6.2f,%6.2f) a%3d %s%s" % (p["num"], p["name"][:12], p["type"], p["x"], p["y"], p["ang"], net,
                                                           " HIDDEN" if p["hidden"] else ""))
