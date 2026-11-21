"""C_rf common: paths, results.json store, limit lines read from the owner's standards (with citations), helpers."""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLOTS = os.path.join(HERE, "plots")
REV3 = os.path.abspath(os.path.join(HERE, "..", "..", ".."))            # Design Reports/Rev3.0
PROJ = os.path.abspath(os.path.join(REV3, "..", ".."))
WORK = r"C:\Users\lenovo\AppData\Local\Temp\claude\6a344b3f0e20185f\953b9f31-5e7b-46a1-b4f4-a743202145e7\scratchpad\agentC"
GEOM = os.path.join(WORK, "geom.json")                                    # written by c1_export_geom.py (KiCad python, board copy)
RESULTS = os.path.join(HERE, "results.json")
sys.path.insert(0, os.path.join(REV3, "sim"))
os.makedirs(PLOTS, exist_ok=True)

C0 = 299792458.0
MU0 = 4e-7 * math.pi
EPS0 = 1.0 / (MU0 * C0 ** 2)
ETA0 = MU0 * C0


def dB(x):
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-30))


def load_results():
    if os.path.exists(RESULTS):
        return json.load(open(RESULTS, encoding="utf-8"))
    return {}


def save_section(key, data):
    """Merge one section into results.json (each script owns its keys)."""
    r = load_results()
    r[key] = data
    json.dump(r, open(RESULTS, "w", encoding="utf-8"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def rnd(x, n=2):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, n) for v in x]
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


# ------------------------------------------------------------------------------------------------------------
# Limits and levels, READ FROM THE OWNER'S FILES (scratchpad/standards_zip/*.txt, PDF page = "=====PAGE n=====")
# ------------------------------------------------------------------------------------------------------------
STD = {
    "E1": "BS EN 55014-1:2017+A11:2020",
    "E2": "BS EN 55014-2:2015",
}
CITE = {
    "table9": "EN 55014-1:2017+A11:2020, 4.3.4.5 Table 9, PDF p.38 (QP; FAR 3 m 42->35 dBuV/m 30-230 MHz decreasing with log f, 42 above; OATS/SAC 10 m 30 / 37 dBuV/m; 'lower limit applies at the transition frequency')",
    "432": "EN 55014-1, 4.3.4.2 method a)/b), PDF p.37 (clock < 30 MHz condition for the 300-1000 MHz exemption)",
    "table7": "EN 55014-1, 4.3.4.4 Table 7, PDF p.37 (disturbance power 30-300 MHz, general: QP 45->55 dBpW, AV 35->45 dBpW, increasing linearly with frequency)",
    "table8": "EN 55014-1, Table 8, PDF p.38 (reduction 0->10 dB QP over 200-300 MHz, only for method a))",
    "5343": "EN 55014-1, 5.3.4.3 test set-up (table-top 0.8 m; cables: mains vertically to the floor, CMAD, >= 0.8 m visible in a FAR), PDF p.47-48",
    "ZZ": "EN 55014-1:2017+A11:2020 Annex ZZ, PDF p.8-9: clause 7 (80/80 statistics) shall not be applied for presumption of conformity",
    "scope_radio": "EN 55014-1, clause 1 Scope, PDF p.23: radiated requirements not applicable to intentional transmissions of a radio transmitter nor to spurious emissions related to them",
    "cat": "EN 55014-2:2015, 4.3/4.5, PDF p.15-16 (category II only if no clock > 15 MHz; otherwise category IV); 3.1.18 clock frequency definition PDF p.15",
    "721": "EN 55014-2, 7.2.4 category IV: injected currents up to 80 MHz criterion A (5.4), RF fields criterion A (5.5), PDF p.23",
    "t8": "EN 55014-2, 5.4 Table 8 (signal/control ports) 0.15-80 MHz, 1 V rms unmodulated, 1 kHz 80 % AM, 150 ohm, only if cable can exceed 3 m; PDF p.19",
    "t10": "EN 55014-2, 5.4 Table 10 (a.c. power ports) 0.15-80 MHz, 3 V rms unmodulated, 1 kHz 80 % AM, 150 ohm, CDN; PDF p.20",
    "t11": "EN 55014-2, 5.5 Table 11 (enclosure) 80-1000 MHz, 3 V/m rms unmodulated, 1 kHz 80 % AM, IEC 61000-4-3 or -4-22; PDF p.20",
    "critA": "EN 55014-2, clause 6 performance criterion A, PDF p.21-22; Annex A Table A.1 (heating 10 %, sensor functions 'f'), PDF p.26",
    "81": "EN 55014-2, 8.1 most susceptible mode, setting ~50 % for adjustable levels; 8.4 modes at random during the scan, PDF p.23-24",
}


def lim_far3m(f):
    """Table 9, FAR 3 m, QP dBuV/m. 30-230 MHz: 42 -> 35 decreasing linearly with log f; 230-1000: 42.
    'The lower limit applies at the transition frequency' -> 35 at exactly 230 MHz."""
    f = np.asarray(f, float)
    lo = 42.0 + (35.0 - 42.0) * np.log10(f / 30e6) / np.log10(230.0 / 30.0)
    return np.where(f <= 230e6, lo, 42.0)


def lim_sac10m(f):
    f = np.asarray(f, float)
    return np.where(f <= 230e6, 30.0, 37.0)


def lim_power_qp(f):
    """Table 7 col. 2 (general, QP) 45 -> 55 dBpW increasing linearly with frequency 30-300 MHz."""
    f = np.asarray(f, float)
    return 45.0 + 10.0 * (f - 30e6) / 270e6


def table8_reduction(f):
    f = np.asarray(f, float)
    return np.where(f < 200e6, 0.0, 10.0 * (f - 200e6) / 100e6)


# SPICE helper of the project (KiCad 10 ngspice.dll)
def spice():
    import ngspice_helper
    return ngspice_helper
