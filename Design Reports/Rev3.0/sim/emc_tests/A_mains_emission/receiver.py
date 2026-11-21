"""CISPR 16-1-1 Band B measuring-receiver model (9 kHz IF, peak / quasi-peak / CISPR-average detectors).

EN 55014-1 5.1.2 (PDF p. 39) requires QP receivers per CISPR 16-1-1 clause 4 and AV per clause 6; CISPR 16-1-1
itself is NOT READ FROM THE STANDARD (not in the owner's folder). Constants used, from the public source
Schwarzbeck Mess-Elektronik, "The EMI-Receiver according to CISPR 16-1-1" (D. Schwarzbeck), table p. 15:
  Band B: 6 dB bandwidth 9 kHz, QP charge 1 ms, QP discharge 160 ms, meter time constant 160 ms,
  calibration impulse 0.158 uVs across 50 ohm at 100 Hz PRF = 60 dBuV sine; theoretical ratios for that pulse
  train QP-PK -6.1 dB, QP-AV 32.9 dB, QP-RMS 14.3 dB (used here as validation targets).
IF filter: Gaussian with 6 dB bandwidth 9 kHz (assumption: the real CISPR filter is a tolerance mask).
Mechanical meter: critically damped 2nd order, each pole tau_m = 160 ms (assumption about the definition).
Readings are in rms-of-sine equivalent (a sine of peak A reads A/sqrt(2)).
"""
import numpy as np

B6 = 9e3
A_GAUSS = np.log(2.0) / (B6 / 2) ** 2          # |G(df)| = exp(-a df^2); 0.5 at +-4.5 kHz
TAU_C, TAU_D, TAU_M = 1e-3, 160e-3, 160e-3
TAU_AV_M = 160e-3


def G(df):
    return np.exp(-A_GAUSS * np.asarray(df, dtype=float) ** 2)


def envelope_periodic(spec_f, spec_X, f0, T, n_t=4096, span=25e3):
    """IF envelope over one period T of a periodic signal given by its one-sided complex line spectrum
    x(t) = Re sum X_k exp(j 2 pi f_k t) (X_k = peak complex amplitude, f_k = k/T).
    Returns (t, e(t)) with e in volts (peak of the IF carrier)."""
    df0 = 1.0 / T
    sel = np.nonzero(np.abs(spec_f - f0) <= span)[0]
    k = np.rint((spec_f[sel] - f0) / df0).astype(int)    # offset in lines (f0 snapped to the line grid)
    Z = np.zeros(n_t, dtype=complex)
    np.add.at(Z, k % n_t, spec_X[sel] * G(spec_f[sel] - f0))
    z = np.fft.ifft(Z) * n_t                               # complex baseband over one period
    t = np.arange(n_t) * T / n_t
    return t, np.abs(z)


def qp_detector(e, dt, v0=0.0):
    """Charge/discharge diode detector: dV/dt = (e-V)/tau_c [e>V] - V/tau_d. Exact per-step update."""
    v = np.empty_like(e)
    vc = v0
    ac, ad = np.exp(-dt / TAU_C), np.exp(-dt / TAU_D)
    for i, x in enumerate(e):
        if x > vc:
            # parallel charge + discharge: steady value x*tau_d/(tau_c+tau_d), combined tau
            tau = 1.0 / (1.0 / TAU_C + 1.0 / TAU_D)
            vinf = x * TAU_D / (TAU_C + TAU_D)
            vc = vinf + (vc - vinf) * np.exp(-dt / tau)
        else:
            vc = vc * ad
        v[i] = vc
    return v


def meter(v, dt, tau=TAU_M):
    """Critically damped 2nd-order meter (two equal real poles at 1/tau)."""
    a = np.exp(-dt / tau)
    y1 = np.empty_like(v); y2 = np.empty_like(v)
    s1 = s2 = 0.0
    for i, x in enumerate(v):
        s1 = a * s1 + (1 - a) * x
        s2 = a * s2 + (1 - a) * s1
        y2[i] = s2
    return y2


QP_CAL = (TAU_C + TAU_D) / TAU_D    # sine calibration of the diode detector (a sine must read its rms value)


def _qp_period(e, dt, vc0, active):
    """One period of the diode detector; only 'active' samples (e > small) are stepped, the rest decay analytically.
    Returns (vc at period end, time-integral of vc over the period)."""
    tau = 1.0 / (1.0 / TAU_C + 1.0 / TAU_D)
    ech = np.exp(-dt / tau)
    n = len(e)
    vc = vc0; integ = 0.0; last = 0
    for i in active:
        gap = (i - last) * dt
        if gap > 0:
            integ += vc * TAU_D * (1 - np.exp(-gap / TAU_D)); vc *= np.exp(-gap / TAU_D)
        x = e[i]
        if x > vc:
            vinf = x * TAU_D / (TAU_C + TAU_D)
            vn = vinf + (vc - vinf) * ech
        else:
            vn = vc * np.exp(-dt / TAU_D)
        integ += 0.5 * (vc + vn) * dt; vc = vn; last = i + 1
    gap = (n - last) * dt
    integ += vc * TAU_D * (1 - np.exp(-gap / TAU_D)); vc *= np.exp(-gap / TAU_D)
    return vc, integ


def readings_periodic(t, e, settle=None):
    """Peak, QP and AV readings (V rms-equivalent) for a periodic envelope e over one period (steady state)."""
    dt = t[1] - t[0]
    T = dt * len(e)
    emax = float(np.max(e))
    active = np.nonzero(e > 1e-4 * emax)[0] if emax > 0 else np.array([], int)
    if active.size > 0.5 * len(e):     # dense signal (e.g. a sine): step every sample
        active = np.arange(len(e))
    vc = 0.0
    for _ in range(2000):
        vn, integ = _qp_period(e, dt, vc, active)
        if abs(vn - vc) <= 1e-7 * max(vn, 1e-18):
            vc = vn; break
        vc = vn
    vc_end, integ = _qp_period(e, dt, vc, active)
    qp = integ / T * QP_CAL          # meter of a periodic input -> mean of the detector voltage
    s = np.sqrt(2.0)
    return {"PK": emax / s, "QP": qp / s, "AV": float(np.mean(e)) / s}


def readings_sequence(e, dt):
    """Peak, QP and AV readings for an arbitrary (non-periodic) envelope sequence e sampled at dt.
    QP: diode detector + critically damped meter, maximum of the meter. AV: linear average with the
    160 ms meter (critically damped), maximum of the meter (CISPR AV 'peak reading of the meter')."""
    s = np.sqrt(2.0)
    vqp = qp_detector(e, dt) * QP_CAL
    q = meter(vqp, dt)
    a = meter(e, dt, TAU_AV_M)
    return {"PK": float(np.max(e)) / s, "QP": float(np.max(q)) / s, "AV": float(np.max(a)) / s,
            "qp_trace": q / s, "av_trace": a / s}


def readings_events(pulse, dt, t_events, T_total, dt_c=2e-4, return_traces=False):
    """QP / AV / PK readings for a sequence of identical, non-overlapping envelope pulses (one per switching
    event) placed at t_events (s). pulse: IF envelope of one event sampled at dt (V, carrier peak).
    Diode detector stepped exactly through each pulse, analytic decay between pulses; meter (critically damped,
    160 ms) and the AV meter run on a dt_c grid. Returns the maximum meter readings (V rms-equivalent)."""
    from scipy.signal import lfilter
    tau = 1.0 / (1.0 / TAU_C + 1.0 / TAU_D)
    ech, edd = np.exp(-dt / tau), np.exp(-dt / TAU_D)
    n_c = int(np.ceil(T_total / dt_c)) + 1
    vgrid = np.zeros(n_c)
    vc, t_last = 0.0, 0.0
    after = []                      # (time after pulse, vc after pulse)
    for te in t_events:
        vc *= np.exp(-(te - t_last) / TAU_D)
        for x in pulse:
            if x > vc:
                vinf = x * TAU_D / (TAU_C + TAU_D); vc = vinf + (vc - vinf) * ech
            else:
                vc *= edd
        t_last = te + len(pulse) * dt
        after.append((t_last, vc))
    # vc on the coarse grid: piecewise decay from the last pulse end
    tg = np.arange(n_c) * dt_c
    if after:
        ta = np.array([a[0] for a in after]); va = np.array([a[1] for a in after])
        idx = np.searchsorted(ta, tg, side="right") - 1
        ok = idx >= 0
        vgrid[ok] = va[idx[ok]] * np.exp(-(tg[ok] - ta[idx[ok]]) / TAU_D)
    a = np.exp(-dt_c / TAU_M)
    b, aa = [(1 - a) ** 2], [1, -2 * a, a * a]
    q = lfilter(b, aa, vgrid * QP_CAL)
    # AV: envelope area per event deposited on the coarse grid, then the 160 ms meter
    area = float(np.sum(pulse) * dt)
    eg = np.zeros(n_c)
    ib = np.clip((np.asarray(t_events) / dt_c).astype(int), 0, n_c - 1)
    np.add.at(eg, ib, area / dt_c)
    a2 = np.exp(-dt_c / TAU_AV_M)
    av = lfilter([(1 - a2) ** 2], [1, -2 * a2, a2 * a2], eg)
    s = np.sqrt(2.0)
    out = {"PK": float(np.max(pulse)) / s if len(t_events) else 0.0, "QP": float(np.max(q)) / s, "AV": float(np.max(av)) / s}
    if return_traces:
        out.update({"t": tg, "qp_trace": q / s, "av_trace": av / s})
    return out


def impulse_train_spectrum(area, prf, fmax=1e6):
    """Line spectrum of a Dirac train of given area (V s) and PRF: X_k = 2*area*prf at k*prf."""
    f = np.arange(1, int(fmax / prf) + 1) * prf
    return f, np.full(f.size, 2 * area * prf, dtype=complex)


def validate():
    """Calibration checks against the Schwarzbeck table (CISPR 16-1-1 Band B, not read from the standard)."""
    out = {}
    area = 0.158e-6
    f, X = impulse_train_spectrum(area, 100.0, 2e6)
    t, e = envelope_periodic(f, X, 1.0e6, 0.01, n_t=8192)
    r = readings_periodic(t, e)
    dbu = {k: 20 * np.log10(v / 1e-6) for k, v in r.items()}
    out["pulse_100Hz_0.158uVs"] = {"QP_dBuV": round(dbu["QP"], 2), "PK_dBuV": round(dbu["PK"], 2), "AV_dBuV": round(dbu["AV"], 2),
                                   "target_QP_dBuV": 60.0, "tolerance_dB": 1.5,
                                   "QP_minus_PK_dB": round(dbu["QP"] - dbu["PK"], 2), "target_QP_minus_PK": -6.1,
                                   "QP_minus_AV_dB": round(dbu["QP"] - dbu["AV"], 2), "target_QP_minus_AV": 32.9}
    # sine: 1 mV rms at the tuned frequency -> 60 dBuV on all detectors
    T = 0.02
    fs = np.arange(1, 40001) * 50.0
    Xs = np.zeros(fs.size, complex); Xs[np.argmin(abs(fs - 1e6))] = 1e-3 * np.sqrt(2)
    t, e = envelope_periodic(fs, Xs, 1e6, T)
    rs = readings_periodic(t, e)
    out["sine_1mV"] = {k: round(20 * np.log10(v / 1e-6), 2) for k, v in rs.items()}
    # PRF dependence of QP (relative to 100 Hz) using the sequence detector (includes the meter)
    rel = {}
    for prf in (1000.0, 100.0, 20.0, 10.0, 2.0, 1.0):
        n_t = 4096 if prf >= 20 else 16384
        f, X = impulse_train_spectrum(area, prf, 0.6e6)
        t, e1 = envelope_periodic(f, X, 0.3e6, 1 / prf, n_t=n_t)
        if prf >= 20:
            rr = readings_periodic(t, e1)
        else:
            dt = t[1] - t[0]
            reps = int(np.ceil(3.0 * prf))
            rr = readings_sequence(np.tile(e1, reps), dt)
        rel[str(prf)] = round(20 * np.log10(rr["QP"] / 1e-6), 2)
    ref = rel["100.0"]
    out["QP_vs_PRF_relative_dB"] = {k: round(v - ref, 2) for k, v in rel.items()}
    # cross-check of the event-based detector against the periodic one (100 Hz train, 3 s)
    f, X = impulse_train_spectrum(area, 100.0, 2e6)
    t, e = envelope_periodic(f, X, 1.0e6, 0.01, n_t=8192)
    dt = t[1] - t[0]
    pulse = np.roll(e, 200)[:400]
    rr = readings_events(pulse, dt, np.arange(0, 3.0, 0.01), 3.0)
    out["event_detector_100Hz_QP_dBuV"] = round(20 * np.log10(rr["QP"] / 1e-6), 2)
    out["event_detector_100Hz_AV_dBuV"] = round(20 * np.log10(rr["AV"] / 1e-6), 2)
    out["note"] = ("targets from Schwarzbeck CISPR 16-1-1 receiver note p. 15 (100 Hz calibration, QP-PK, QP-AV); "
                   "PRF curve shown for information, not compared with CISPR 16-1-1 (not read)")
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(validate(), indent=1))
