"""Part additions / removal of the EMC-fix round (2026-11-21).

New symbol instances are cloned from an existing instance of the same kind (same lib symbol, same footprint family),
get a deterministic UUID (uuid5 of the reference), their own pin UUIDs and the instance path of their sheet.
The target connectivity (baseline netlist) is extended by the new pins on existing nets; no new net is created.
  root   : C9   1 nF C0G 0402   ZCD node (U6.2 / R8.2 / U1.5) - GND       (EFT P-E1)          template C5
           D6   1.5KE440CA-TKS  LINE_FILT - Q1.A1 (replaces RV2 MOV)       (surge P-S4)        template D112 (Device:D_TVS)
           RV3  TVR14431KSU15Y  LINE_FUSED - NEUT                          (surge P-S2b)       template RV1
           RV2  removed
  Display: C134, C135 100 nF X7R 0402  +5V - GND at the J10 via field      (radiated, C 6.1)   template C123
"""
import copy
import uuid

from core import S, N, find, first, prop_node, getprop

NS = uuid.uuid5(uuid.NAMESPACE_URL, "readark/rev3.0/emc-fix-round/2026-11-21")

NEW = [
    # sheet, ref, template (sheet, ref), lib_id, footprint, {pin: net-of-pin or net name}
    ("root", "C9", ("root", "C5"), "Device:C", "Capacitor_SMD:C_0402_1005Metric", {"1": ("pin", "U6", "2"), "2": ("net", "GND")}),
    ("root", "D6", ("Display", "D112"), "Device:D_TVS", "Diode_THT:D_DO-201AD_P15.24mm_Horizontal",
     {"1": ("pin", "Q1", "2"), "2": ("pin", "Q1", "1")}),
    ("root", "RV3", ("root", "RV1"), "Device:Varistor", "Varistor:RV_Disc_D15.5mm_W5mm_P7.5mm",
     {"1": ("pin", "F3", "1"), "2": ("net", "NEUT")}),
    ("Display", "C134", ("Display", "C123"), "Device:C", "Capacitor_SMD:C_0402_1005Metric", {"1": ("net", "+5V"), "2": ("net", "GND")}),
    ("Display", "C135", ("Display", "C123"), "Device:C", "Capacitor_SMD:C_0402_1005Metric", {"1": ("net", "+5V"), "2": ("net", "GND")}),
]
REMOVE = [("root", "RV2")]
# round 2 (owner decision 2026-11-21): U5 symbol -> Relay_SolidState:MOC3083M (pins, pin types and body identical to MOC3052M,
# checked with LibSym), footprint unchanged; R4 footprint 0402 -> 0603
import os as _os
MODIFY = {"U5": dict(lib=("Relay_SolidState", "MOC3083M")), "R4": dict(footprint="Resistor_SMD:R_0603_1608Metric")}
if _os.environ.get("EMC_ROUND", "2") != "2":
    MODIFY = {}


def uid(ref, what="sym"):
    return str(uuid.uuid5(NS, "%s/%s" % (ref, what)))


def clone(builders, sheet, ref, tpl, lid, fp):
    b = builders[sheet]
    tsheet, tref = tpl
    src = builders[tsheet].doc.symbols[tref]
    b.ensure_lib(lid)
    node = copy.deepcopy(src)
    assert first(node, "lib_id")[1] == lid, (ref, first(node, "lib_id")[1], lid)
    for m in find(node, "mirror"):
        node.remove(m)
    first(node, "uuid")[1] = uid(ref)
    prop_node(node, "Reference")[2] = ref
    prop_node(node, "Footprint")[2] = fp
    for i, p in enumerate(find(node, "pin")):
        first(p, "uuid")[1] = uid(ref, "pin%s" % p[1])
    inst = first(first(node, "instances"), "project")
    path = first(inst, "path")
    path[1] = b.doc.inst_path
    first(path, "reference")[1] = ref
    b.doc.symbols[ref] = node
    return node


def modify(builders, log):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from kicad_lib import get_symbol
    from core import LibSym
    b = builders["root"]
    for ref, m in MODIFY.items():
        node = b.doc.symbols[ref]
        if "lib" in m:
            lib, name = m["lib"]
            new = get_symbol(lib, name)
            old_lid = first(node, "lib_id")[1]
            old = b.doc.libs[old_lid]
            nl = LibSym(new)
            assert [(p["num"], p["type"], p["x"], p["y"], p["ang"]) for p in nl.pins] ==                    [(p["num"], p["type"], p["x"], p["y"], p["ang"]) for p in old.pins] and nl.body(1) == old.body(1), ref
            ls = first(b.doc.tree, "lib_symbols")
            users = [r for r, s in b.doc.symbols.items() if first(s, "lib_id")[1] == old_lid]
            if users == [ref]:
                ls.remove(old.node); del b.doc.libs[old_lid]
            if new[1] not in b.doc.libs:
                ls.append(new); b.doc.libs[new[1]] = nl
            first(node, "lib_id")[1] = new[1]
            log.append("root: %s lib_id %s -> %s (pins/body identical)" % (ref, old_lid, new[1]))
        if "footprint" in m:
            p = prop_node(node, "Footprint"); old = p[2]; p[2] = m["footprint"]
            log.append("root: %s footprint %s -> %s" % (ref, old, m["footprint"]))


def apply(builders, target):
    log = []
    modify(builders, log)
    for sheet, ref in REMOVE:
        b = builders[sheet]
        node = b.doc.symbols.pop(ref)
        for (r, n), net in list(target.pin_net.items()):
            if r == ref:
                del target.pin_net[(r, n)]
                target.net_pins[net].discard((r, n))
        log.append("%s: %s removed (%s)" % (sheet, ref, getprop(node, "Value")))
    for sheet, ref, tpl, lid, fp, pins in NEW:
        clone(builders, sheet, ref, tpl, lid, fp)
        for num, spec in pins.items():
            net = target.pin_net[(spec[1], spec[2])] if spec[0] == "pin" else spec[1]
            target.pin_net[(ref, num)] = net
            target.net_pins.setdefault(net, set()).add((ref, num))
        log.append("%s: %s added (%s, %s) pins %s" % (sheet, ref, lid, fp,
                   ", ".join("%s=%s" % (n, target.pin_net[(ref, n)]) for n in pins)))
    return log
