"""Internal connectivity check of a set of five sheet files against the baseline netlist (no KiCad needed).
Usage: python -I model_check.py <dir with the five .kicad_sch>   (default: the baseline copy)
Used first to validate the transform/connection model on the baseline drawings themselves."""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, NETPREFIX, BASELINE, Doc, Target, sheet_clusters, interior_hits, getprop, first, find, Conn  # noqa


def drawn_items(doc):
    wires = []
    for w in find(doc.tree, "wire"):
        pts = find(first(w, "pts"), "xy")
        wires.append(((float(pts[0][1]), float(pts[0][2])), (float(pts[1][1]), float(pts[1][2]))))
    points = []
    for ref, node in doc.symbols.items():
        for num, p, o, pd in doc.pins_of(node):
            points.append((p, ("pin", ref, num)))
    for i, node in enumerate(doc.power_syms):
        val = getprop(node, "Value")
        for num, p, o, pd in doc.pins_of(node):
            points.append((p, ("pwr", val, i)))
    for k in ("label", "global_label"):
        for i, l in enumerate(find(doc.tree, k)):
            at = first(l, "at")
            points.append(((float(at[1]), float(at[2])), (k, l[1], i)))
    return wires, points


def check(dirpath, target, verbose=True):
    gc = Conn()
    pin_cluster = {}
    problems = []
    for sheet, fn in FILES.items():
        doc = Doc(os.path.join(dirpath, fn), sheet)
        wires, points = drawn_items(doc)
        juncs = [(float(first(j, "at")[1]), float(first(j, "at")[2])) for j in find(doc.tree, "junction")]
        cl, _ = sheet_clusters(wires, points, juncs)
        for tag, cid in cl.items():
            node = (sheet, cid)
            gc.f(node)
            if tag[0] == "pin":
                pin_cluster[(tag[1], tag[2])] = node
            elif tag[0] == "pwr":
                if tag[1] != "PWR_FLAG":
                    gc.u(node, ("NAME", tag[1]))
            elif tag[0] == "global_label":
                gc.u(node, ("NAME", tag[1]))
            elif tag[0] == "label":
                gc.u(node, ("NAME", NETPREFIX[sheet] + tag[1]))
        hits = interior_hits(wires, [p for p, t in points])
        for p, a, b in hits:
            problems.append("%s: T-join without wire split at %s on wire %s-%s" % (sheet, p, a, b))
    # group pins by global cluster
    groups = defaultdict(set)
    for pin, node in pin_cluster.items():
        groups[gc.f(node)].add(pin)
    # compare
    bad = 0
    for net, pins in target.net_pins.items():
        roots = {gc.f(pin_cluster[p]) for p in pins if p in pin_cluster}
        missing = [p for p in pins if p not in pin_cluster]
        if missing:
            problems.append("net %s: pins not drawn %s" % (net, missing)); bad += 1; continue
        if len(roots) != 1:
            parts = [sorted(groups[r] & pins) for r in roots]
            problems.append("net %s split into %d: %s" % (net, len(roots), parts)); bad += 1; continue
        extra = groups[next(iter(roots))] - pins
        if extra:
            problems.append("net %s shorted with %s" % (net, sorted(extra))); bad += 1
    if verbose:
        for p in problems:
            print("  ", p)
        print("model check: %d nets, %d bad, %d problems" % (len(target.net_pins), bad, len(problems)))
    return problems


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else BASELINE
    t = Target(os.path.join(BASELINE, "baseline.xml"), BASELINE)
    check(d, t)
