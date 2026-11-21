"""Earthed-oven study (2026-11-21), scope C - common paths. Re-uses the committed scope-C modules READ-ONLY
(../../emc_tests/C_rf: mom.py, c5_cm_structure.py geometry helpers, c0_common limits/citations) and their results.json
(read-only, as the 'unearthed' reference and for the SPICE chain / 2D inductance data). Writes only into this folder."""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.abspath(os.path.join(HERE, "..", "..", "emc_tests", "C_rf"))
sys.path.insert(0, OLD)
import c0_common as C0M                      # noqa: E402  (limits, citations, constants; its RESULTS path is NOT used here)
from c0_common import dB, rnd, lim_far3m, lim_sac10m, lim_power_qp, CITE, C0, MU0, EPS0, ETA0, WORK, GEOM, spice   # noqa: F401

PLOTS = os.path.join(HERE, "plots")
RESULTS = os.path.join(HERE, "results.json")
OLD_RESULTS = os.path.join(OLD, "results.json")
EWORK = os.path.join(WORK, "earthed")
os.makedirs(PLOTS, exist_ok=True)
os.makedirs(EWORK, exist_ok=True)


def old():
    return json.load(open(OLD_RESULTS, encoding="utf-8"))


def load_results():
    return json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else {}


def save_section(key, data):
    r = load_results()
    r[key] = data
    json.dump(r, open(RESULTS, "w", encoding="utf-8"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


# design state decided by the owner 2026-11-21 (coordinator message): RN1-RN7 150 ohm, 2 x 100 nF at the J10 via field,
# 1 nF C0G on the ZCD node, NO Y1. No panel-bonding pads on the PCB in this round (bonding concepts are simulated only).
DESIGN = {"RN_ohm": 150, "J10_caps": "2 x 100 nF", "ZCD_cap": "1 nF C0G", "Y1": None, "panel_bonding_on_pcb": False}
