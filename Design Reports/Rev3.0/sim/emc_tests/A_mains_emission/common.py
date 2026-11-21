"""Shared constants, limits (each with its source) and the results.json merge helper for scope A."""
import json, math, os, sys
sys.dont_write_bytecode = True           # never leave __pycache__ in sim/ or sim/emc/ (read-only folders)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLOTS = os.path.join(HERE, "plots")
os.makedirs(PLOTS, exist_ok=True)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SIM = os.path.join(ROOT, "Design Reports", "Rev3.0", "sim")
sys.path.insert(0, SIM)                      # ngspice_helper.py
sys.path.insert(0, os.path.join(SIM, "emc"))  # flickermeter.py (imported, never written)
RESULTS = os.path.join(HERE, "results.json")

STD_55014_1 = "BS EN 55014-1:2017+A11:2020"
STD_3_2 = "IEC 61000-3-2:2018+AMD1:2020+AMD2:2024 CSV (ed. 5.2), FINAL VERSION part"
STD_3_3 = "IEC 61000-3-3 ed. 3.2 (21-page webstore preview)"
NOT_READ = "NOT READ FROM THE STANDARD"


def save_results(section, data):
    res = {}
    if os.path.exists(RESULTS):
        with open(RESULTS, encoding="utf8") as f:
            res = json.load(f)
    res[section] = data
    with open(RESULTS, "w", encoding="utf8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=_np)


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def dB(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-30))


def dBuV(v_rms):
    return 20 * np.log10(np.maximum(v_rms, 1e-30) / 1e-6)


# ---------------------------------------------------------------- EN 55014-1 limits -----------------------------
# Table 5 "General limits", mains ports, columns 2 (QP) and 3 (AV); associated ports columns 4/5.
# BS EN 55014-1:2017+A11:2020, 4.3.3.2 + Table 5, PDF page 36 (read from the rendered table; the text extraction
# of this table is scrambled). Note: the AV limit is 59 -> 46 dBuV in 0.15-0.5 MHz (the 2026-11-12 assessment used
# 56 -> 46, i.e. the CISPR 32 value). "The lower limit applies at the transition frequencies."
LIMIT_SRC = f"{STD_55014_1}, 4.3.3.2 and Table 5 col. 2/3, PDF p. 36"


def _loglin(f, f1, f2, a, b):
    return a + (b - a) * math.log10(f / f1) / math.log10(f2 / f1)


def lim_qp(f):
    f = float(f)
    if f < 0.5e6:
        return _loglin(f, 0.15e6, 0.5e6, 66.0, 56.0)
    if f <= 5e6:          # lower limit at the 5 MHz transition
        return 56.0
    return 60.0


def lim_av(f):
    f = float(f)
    if f < 0.5e6:
        return _loglin(f, 0.15e6, 0.5e6, 59.0, 46.0)
    if f <= 5e6:
        return 46.0
    return 50.0


def lim_assoc_qp(f):   # Table 5 col. 4 (associated port, disturbance voltage), PDF p. 36
    return 80.0 if f < 0.5e6 else 74.0


def lim_assoc_av(f):   # Table 5 col. 5
    return 70.0 if f < 0.5e6 else 64.0


def click_relaxation_dB(N):
    """EN 55014-1 4.4.2.3 (PDF p. 39): Lq = L + 44 dB for N < 0.2, + 20 lg(30/N) for 0.2 <= N < 30, none for N >= 30."""
    if N < 0.2:
        return 44.0
    if N < 30:
        return 20 * math.log10(30.0 / N)
    return 0.0


# ---------------------------------------------------------------- IEC 61000-3-2 limits --------------------------
# Table 1 Class A, FINAL VERSION PDF p. 146; Table 3 (Class D style, used by 6.2 for symmetrical control of
# heating elements), PDF p. 147; 6.2 text PDF p. 137-138.
def classA(h):
    odd = {3: 2.30, 5: 1.14, 7: 0.77, 9: 0.40, 11: 0.33, 13: 0.21}
    even = {2: 1.08, 4: 0.43, 6: 0.30}
    if h % 2:
        return odd.get(h, 0.15 * 15 / h)
    return even.get(h, 0.23 * 8 / h)


def table3(h, P):
    """Table 3: min(mA/W * P, absolute A); odd orders only (3..39). For 13 <= h <= 39: 3.85/h mA/W, absolute 'see Table 1'."""
    if h % 2 == 0:
        return None
    per_w = {3: 3.4, 5: 1.9, 7: 1.0, 9: 0.5, 11: 0.35}.get(h, 3.85 / h) * 1e-3
    return min(per_w * P, classA(h))


# ---------------------------------------------------------------- IEC 61000-3-3 limits (NOT READ) --------------
# The preview file stops before clause 5 (limits) and 6.4 (Zref); these values are NOT READ FROM THE STANDARD.
# Public source used: Keysight (HP) application note 5964-1917E "IEC 61000-3-3" (docs.ampnuts.ru mirror) and the
# 2026-11-12 assessment (which also took them "as known"). Confirm against a full copy (open item 6).
FLICKER_LIMITS = {"Pst": 1.0, "Plt": 0.65, "dc_pct": 3.3, "dmax_pct": 4.0, "Tmax_s": 0.5,
                  "source": NOT_READ + " - IEC 61000-3-3 clause 5 is not in the preview file"}
ZREF = {"R_ohm": 0.40, "X_ohm": 0.25, "split": "phase 0.24 + j0.15, neutral 0.16 + j0.10",
        "source": NOT_READ + " - IEC 61000-3-3 6.4 is not in the preview file"}
