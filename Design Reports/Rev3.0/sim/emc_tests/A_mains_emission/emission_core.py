"""Core of the conducted-emission computation: AC transfer (SPICE) x triac-voltage line spectrum -> LISN line
spectrum -> CISPR receiver (envelope per tuned frequency, QP / AV / PK)."""
import math
import numpy as np
import common  # noqa: F401  (sets sys.path)
import ngspice_helper as ng
import frontend as fe
import receiver as rx
from common import lim_qp, lim_av, dBuV

F_SCAN = np.unique(np.concatenate([np.logspace(np.log10(150e3), np.log10(30e6), 160), [150e3, 500e3, 1.4e6, 30e6]]))


def ac_transfer(P, source="triac", fstart=1e5, fstop=40e6, ppd=200, extra=()):
    r = ng.run_netlist(fe.netlist_ac(P, source, fstart, fstop, ppd))
    f = np.real(r["frequency"])
    if extra:
        return (f, r["v(rx_l)"], r["v(rx_n)"]) + tuple(r[f"v({n})"] for n in extra)
    return f, r["v(rx_l)"], r["v(rx_n)"]


def interp_c(fq, f, H):
    """complex interpolation in log-f (magnitude in dB, unwrapped phase)."""
    lf = np.log(f)
    mag = np.interp(np.log(fq), lf, np.log(np.abs(H) + 1e-300))
    ph = np.interp(np.log(fq), lf, np.unwrap(np.angle(H)))
    return np.exp(mag) * np.exp(1j * ph)


def line_spectrum(t, v):
    """one-sided complex peak-amplitude line spectrum of one period."""
    n = len(v)
    X = np.fft.rfft(v) / n * 2
    T = (t[1] - t[0]) * n
    f = np.arange(X.size) / T
    return f[1:], X[1:]


def lisn_lines(P, H=None, n=2 ** 21):
    if H is None:
        H = ac_transfer(P)
    fH, HL, HN = H
    t, v = fe.triac_voltage_waveform(P, n)
    f, X = line_spectrum(t, v)
    sel = (f >= 100e3) & (f <= fH[-1])
    f, X = f[sel], X[sel]
    return f, X * interp_c(f, fH, HL), X * interp_c(f, fH, HN)


def scan(f, XL, XN, T=0.02, f_scan=F_SCAN, n_t=4096):
    out = {"f": [], "L": {"QP": [], "AV": [], "PK": []}, "N": {"QP": [], "AV": [], "PK": []}}
    for f0 in f_scan:
        out["f"].append(float(f0))
        for side, X in (("L", XL), ("N", XN)):
            t, e = rx.envelope_periodic(f, X, f0, T, n_t=n_t)
            r = rx.readings_periodic(t, e)
            for k in ("QP", "AV", "PK"):
                out[side][k].append(float(dBuV(r[k])))
    return out


def margins(sc):
    f = np.array(sc["f"])
    res = {}
    for det, lim in (("QP", lim_qp), ("AV", lim_av)):
        L = np.array([lim(x) for x in f])
        worst = None
        for side in ("L", "N"):
            v = np.array(sc[side][det])
            m = L - v
            i = int(np.argmin(m))
            if worst is None or m[i] < worst["margin_dB"]:
                worst = {"margin_dB": round(float(m[i]), 2), "f_MHz": round(float(f[i] / 1e6), 4), "line": side,
                         "level_dBuV": round(float(v[i]), 2), "limit_dBuV": round(float(L[i]), 2)}
        res[det] = worst
    return res


def event_pulses(f, X, f0, T=0.02, n_t=8192):
    """IF envelope over one period at f0 -> the two per-half-cycle event pulses (turn-on + preceding turn-off are
    within the same 0.2 ms window around each zero crossing)."""
    t, e = rx.envelope_periodic(f, X, f0, T, n_t=n_t)
    return t, e
