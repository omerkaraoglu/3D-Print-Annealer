"""Earthed-chassis variant of scope B (2026-11-21).  Imports the committed scope-B models READ-ONLY from
../../emc_tests/B_immunity_transients (common.py: device data, MOV/TVS curves, generator fits) and writes only into
this folder (results.json, plots/).

Design state simulated (owner decision 2026-11-21, not re-exported from KiCad -- the schematic is being edited):
  topology = ../../emc_tests/B_immunity_transients/netlist_extract.json  plus
  U5 -> 800 V random-phase driver (FOD4218 class, VDRM 800 V), RV2 -> 1.5KE440CA TVS across Q1,
  RV3 = TVR14431KSU15Y across LINE_FUSED-NEUT, 1 nF on the ZCD collector node, NO Y1 capacitor.
Earthing (owner statement 2026-11-21, rest ASSUMED): oven chassis and sheet metal on PE via a 3-core cord bonded at
the inlet; the PCB has only L and N (no PE terminal); SELV ground not deliberately bonded to PE; heater element in/on
the earthed chassis; HS1 floats on the insulated tab; thermocouple WRNT-02 ring bolted to the chassis, junction either
grounded to the ring or insulated (both simulated); steel front sheet earthed.
"""
import json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.abspath(os.path.join(HERE, '..', '..', 'emc_tests', 'B_immunity_transients'))
sys.path.insert(0, OLD)
import common as cm          # noqa: E402  (read-only use: data, curves, generator subcircuits, run_netlist)

PLOTS = os.path.join(HERE, 'plots')
os.makedirs(PLOTS, exist_ok=True)
RESULTS = os.path.join(HERE, 'results.json')
P = cm.P


def save(section, data):
    allr = {}
    if os.path.exists(RESULTS):
        allr = json.load(open(RESULTS, encoding='utf-8'))
    allr[section] = data
    tmp = RESULTS + '.tmp'
    json.dump(allr, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False, default=float)
    os.replace(tmp, RESULTS)


def load():
    return json.load(open(RESULTS, encoding='utf-8'))


_ELEM = re.compile(r'^\s*([RCLDVIBGEFHKSX])(\S*)\s+(.*)$', re.I)


def check_nodes(netlist):
    """Fail if two node names differ only by letter case (SPICE is case-insensitive: the 2026-11-18 'G'/'g' bug).
    Scans the top level and every subcircuit separately."""
    scopes = {'top': {}}
    cur = 'top'
    for raw in netlist.splitlines():
        line = raw.strip()
        if not line or line.startswith('*') or line.startswith('+'):
            continue
        low = line.lower()
        if low.startswith('.subckt'):
            cur = line.split()[1]; scopes[cur] = {}
            for n in line.split()[2:]:
                if n.upper().startswith('PARAMS'): break
                scopes[cur].setdefault(n.lower(), set()).add(n)
            continue
        if low.startswith('.ends'):
            cur = 'top'; continue
        if line.startswith('.'):
            continue
        m = _ELEM.match(line)
        if not m: continue
        kind = m.group(1).upper(); rest = m.group(3).split()
        nn = {'R': 2, 'C': 2, 'L': 2, 'D': 2, 'V': 2, 'I': 2, 'B': 2, 'G': 4, 'E': 4, 'F': 2, 'H': 2, 'S': 4, 'K': 0}.get(kind, 0)
        if kind == 'X':
            nodes = [t for t in rest if '=' not in t and not t.upper().startswith('PARAMS')][:-1]
        else:
            nodes = rest[:nn]
        for n in nodes:
            scopes[cur].setdefault(n.lower(), set()).add(n)
    bad = {s: {k: sorted(v) for k, v in d.items() if len(v) > 1} for s, d in scopes.items()}
    bad = {s: d for s, d in bad.items() if d}
    if bad:
        raise ValueError(f'node names differing only by case: {bad}')
    gnd = [n for n in scopes['top'] if n == 'gnd']
    if gnd:
        raise ValueError("node 'gnd' is an alias of ground 0 in ngspice")
    return True


def run(netlist):
    check_nodes(netlist)
    return cm.run_netlist(netlist)


verdict = cm.verdict
