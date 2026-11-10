"""Thin wrapper around PySpice's NgSpiceShared for the KiCad-bundled ngspice.dll.

Engine: ngspice 46 shared library shipped with KiCad 10
(KiCad/10.0/bin/ngspice.dll), driven through PySpice 1.5.
No ngspice.exe exists on this machine, so every netlist is run in-process.
"""
import os
import numpy as np

NGSPICE_DLL = r"C:\Program Files\KiCad\10.0\bin\ngspice.dll"
NGSPICE_ROOT = r"C:\Program Files\KiCad\10.0"
NGSPICE_LIB = r"C:\Program Files\KiCad\10.0\lib\ngspice"   # *.cm code models

os.environ.setdefault("SPICE_LIB_DIR", NGSPICE_LIB)
os.add_dll_directory(os.path.join(NGSPICE_ROOT, "bin"))

from PySpice.Spice.NgSpice.Shared import NgSpiceShared  # noqa: E402

NgSpiceShared.LIBRARY_PATH = NGSPICE_DLL
NgSpiceShared.NGSPICE_PATH = NGSPICE_ROOT

_instance = None


def engine():
    global _instance
    if _instance is None:
        _instance = NgSpiceShared.new_instance()
    return _instance


def run_netlist(netlist: str, plot_name: str | None = None) -> dict:
    """Load a complete netlist (title line .. .end), run it and return
    {vector_name(lower): np.ndarray}. Complex vectors (AC) are returned as complex."""
    ng = engine()
    ng.destroy()          # clear previous circuits/plots
    ng.load_circuit(netlist)
    ng.run()
    name = plot_name or ng.last_plot
    plot = ng.plot(None, name)
    out = {}
    for k, vec in plot.items():
        key = k.lower()
        arr = np.asarray(vec._data)
        out[key] = arr
        # ngspice returns node voltages under the bare node name; add a v(node) alias
        if key not in ("time", "frequency") and "#" not in key and not key.startswith("v("):
            out[f"v({key})"] = arr
    return out


def to_uniform(t, y, dt):
    """Resample a variable-step transient result onto a uniform grid."""
    tu = np.arange(t[0], t[-1], dt)
    return tu, np.interp(tu, t, y)


def spectrum(t, y, dt, window="hann"):
    """One-sided amplitude spectrum (peak amplitude per bin) of y(t)."""
    tu, yu = to_uniform(t, y, dt)
    n = len(yu)
    w = np.hanning(n) if window == "hann" else np.ones(n)
    cg = w.sum() / n                       # coherent gain
    Y = np.fft.rfft(yu * w) / (n * cg)
    f = np.fft.rfftfreq(n, dt)
    amp = 2 * np.abs(Y)
    amp[0] /= 2
    return f, amp
