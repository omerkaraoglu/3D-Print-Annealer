"""
IEC 61000-4-15 flickermeter model (230 V / 50 Hz lamp, 60 W reference) and
IEC 61000-3-3 relative-voltage-change parameters d(t), d_c, d_max, T_max.

Signal chain
  Block 1  input voltage adaptor: x / sqrt(<x^2>_27.3s)  (first-order LP, tau 27.3 s, on x^2)
  Block 2  squaring demodulator
  Block 3  6th-order Butterworth LP 35 Hz (at fs), decimation to fs/dec,
           Butterworth HP 0.05 Hz (order selectable: 1 = IEC 61000-4-15 text, 6 = brief),
           lamp-eye-brain weighting filter (230 V coefficients, bilinear transform)
  Block 4  squaring + first-order LP tau = 300 ms, scaled so that an 8.8 Hz
           sinusoidal modulation of dV/V = 0.250 % (peak-to-peak) gives P_inst = 1
           (calibrated numerically on the steady-state mean of P_inst)
  Block 5  CPF with log-spaced classes, smoothed percentiles, P_st.
"""
import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d

# Lamp-eye-brain weighting filter, 230 V / 60 W incandescent lamp
K_W = 1.74802
LAM = 2 * np.pi * 4.05981
W1 = 2 * np.pi * 9.15494
W2 = 2 * np.pi * 2.27979
W3 = 2 * np.pi * 1.22535
W4 = 2 * np.pi * 21.9


def weighting_zpk_s():
    """H(s) = k w1 s/(s^2+2 lam s+w1^2) * (1+s/w2)/((1+s/w3)(1+s/w4)) as analog zpk."""
    z = np.array([0.0, -W2])
    p = np.concatenate([np.roots([1.0, 2 * LAM, W1 ** 2]), [-W3, -W4]])
    k = K_W * W1 * W3 * W4 / W2
    return z, p, k


def weighting_mag(f):
    """|H(j 2 pi f)| of the analog weighting filter."""
    s = 1j * 2 * np.pi * np.asarray(f, dtype=float)
    h = K_W * W1 * s / (s ** 2 + 2 * LAM * s + W1 ** 2) * (1 + s / W2) / ((1 + s / W3) * (1 + s / W4))
    return np.abs(h)


PST_PCT = [0.1, 0.7, 1, 1.5, 2.2, 3, 4, 6, 8, 10, 13, 17, 30, 50, 80]


def _first_order_lp(tau, fs):
    return signal.bilinear([1.0], [tau, 1.0], fs)


class Flickermeter:
    def __init__(self, fs=4000.0, f0=50.0, dec=4, hp_order=1, calibrate=True):
        self.fs = float(fs)
        self.f0 = float(f0)
        self.dec = int(dec)
        self.fsd = self.fs / self.dec
        self.hp_order = hp_order
        self.ba_adapt = _first_order_lp(27.3, self.fs)
        self.sos_lp35 = signal.butter(6, 35.0, 'low', fs=self.fs, output='sos')
        self.sos_hp = signal.butter(hp_order, 0.05, 'high', fs=self.fsd, output='sos')
        z, p, k = weighting_zpk_s()
        zd, pd, kd = signal.bilinear_zpk(z, p, k, self.fsd)
        self.sos_w = signal.zpk2sos(zd, pd, kd)
        self.ba_300 = _first_order_lp(0.3, self.fsd)
        self.gain = 1.0
        if calibrate:
            self.gain = self.calibrate()

    # ---------------- blocks 1-4 ----------------
    def pinst(self, v):
        """Return instantaneous flicker sensation P_inst sampled at fs/dec."""
        x = np.asarray(v, dtype=float)
        ncyc = int(round(self.fs / self.f0))
        # Block 1: adaptor, 27.3 s mean-square tracker initialised at the first cycle
        ms0 = np.mean(x[:ncyc] ** 2)
        b, a = self.ba_adapt
        ms, _ = signal.lfilter(b, a, x * x, zi=signal.lfilter_zi(b, a) * ms0)
        # Block 2: squaring demodulator (normalised so that the carrier gives mean 1)
        y = (x * x) / ms
        # Block 3: LP 35 Hz (6th-order Butterworth), decimate, HP 0.05 Hz, weighting
        y0 = np.mean(y[:ncyc])
        y, _ = signal.sosfilt(self.sos_lp35, y, zi=signal.sosfilt_zi(self.sos_lp35) * y0)
        y = y[::self.dec]
        y, _ = signal.sosfilt(self.sos_hp, y, zi=signal.sosfilt_zi(self.sos_hp) * y0)
        y = signal.sosfilt(self.sos_w, y)
        # Block 4: squaring + 300 ms first-order sliding mean
        y = y * y
        b, a = self.ba_300
        y = signal.lfilter(b, a, y)
        return y * self.gain

    def calibrate(self, T=40.0, settle=20.0):
        """Gain so that 8.8 Hz sinusoidal modulation, dV/V = 0.25 % p-p, gives mean P_inst = 1."""
        v = sine_modulated(self.fs, T, 0.0025, 8.8, f0=self.f0)
        self.gain = 1.0
        p = self.pinst(v)
        n0 = int(settle * self.fsd)
        return 1.0 / np.mean(p[n0:])


# ---------------- block 5 ----------------
def percentiles_cpf(p, pct=PST_PCT, n_classes=4096):
    """Levels exceeded pct % of the time, from a CPF with n_classes log-spaced classes
    (linear interpolation inside a class)."""
    p = np.asarray(p, dtype=float)
    pmax = float(p.max())
    lo = max(pmax * 1e-6, 1e-12)
    edges = np.logspace(np.log10(lo), np.log10(pmax * (1 + 1e-9)), n_classes + 1)
    counts, _ = np.histogram(np.clip(p, lo, None), bins=edges)
    ex = np.concatenate([[1.0], 1.0 - np.cumsum(counts) / p.size])  # fraction >= edges[j]
    ex = np.clip(ex, 0.0, 1.0)
    out = {}
    for x in pct:
        q = x / 100.0
        j = int(np.nonzero(ex >= q)[0][-1])
        if j >= n_classes:
            out[x] = edges[-1]
            continue
        den = ex[j] - ex[j + 1]
        frac = 0.0 if den <= 0 else (ex[j] - q) / den
        out[x] = edges[j] + frac * (edges[j + 1] - edges[j])
    return out


def percentiles_exact(p, pct=PST_PCT):
    return {x: float(np.percentile(p, 100.0 - x)) for x in pct}


def pst_from_percentiles(P):
    p1s = (P[0.7] + P[1] + P[1.5]) / 3
    p3s = (P[2.2] + P[3] + P[4]) / 3
    p10s = (P[6] + P[8] + P[10] + P[13] + P[17]) / 5
    p50s = (P[30] + P[50] + P[80]) / 3
    return float(np.sqrt(0.0314 * P[0.1] + 0.0525 * p1s + 0.0657 * p3s + 0.28 * p10s + 0.08 * p50s))


def pst(pinst, method='cpf', n_classes=4096):
    P = percentiles_cpf(pinst, n_classes=n_classes) if method == 'cpf' else percentiles_exact(pinst)
    return pst_from_percentiles(P)


def plt_from_pst(psts):
    psts = np.asarray(psts, dtype=float)
    return float(np.cbrt(np.mean(psts ** 3)))


# ---------------- IEC 61000-3-3 d-parameters ----------------
def half_cycle_rms(v, fs, f0=50.0):
    """rms of each half cycle; v must start at a positive-going zero crossing and
    fs/(2 f0) must be an integer."""
    n = fs / (2 * f0)
    assert abs(n - round(n)) < 1e-9, 'fs/(2 f0) must be an integer'
    n = int(round(n))
    m = (len(v) // n) * n
    return np.sqrt(np.mean(np.asarray(v[:m], dtype=float).reshape(-1, n) ** 2, axis=1))


def _longest_run(mask):
    if not mask.any():
        return 0
    m = np.concatenate([[0], mask.astype(np.int8), [0]])
    dm = np.diff(m)
    starts = np.nonzero(dm == 1)[0]
    ends = np.nonzero(dm == -1)[0]
    return int(np.max(ends - starts))


def d_parameters(urms, Un=230.0, f0=50.0, tol=0.002, t_ss=1.0, d_lim=0.033):
    """Simplified IEC 61000-3-3 evaluation on a half-cycle rms sequence.
    Steady state: every half cycle covered by a window of >= t_ss seconds in which
    max-min <= 2*tol*Un (voltage inside a +/-tol band for >= t_ss).
    Voltage change characteristic: from the end of one steady state to the start of the
    next (or to the end of the record); d(t) relative to the preceding steady-state level.
    d_c: max |difference| of adjacent steady-state levels; d_max: max |d(t)| during a change;
    T_max: longest contiguous time with |d(t)| > d_lim during one change."""
    u = np.asarray(urms, dtype=float)
    n = len(u)
    w = int(round(t_ss * 2 * f0))
    segs = []
    if n >= w:
        # window starting at i covers [i, i+w); a run of consecutive valid window starts
        # [s0, s1] is one steady state covering [s0, s1 + w). Separate runs are separate
        # steady states even if their coverage touches (e.g. a step between two levels).
        mx = maximum_filter1d(u, w, origin=-(w // 2))[: n - w + 1]
        mn = minimum_filter1d(u, w, origin=-(w // 2))[: n - w + 1]
        ok = (mx - mn) <= 2 * tol * Un
        m = np.concatenate([[0], ok.astype(np.int8), [0]])
        dm = np.diff(m)
        rs = np.nonzero(dm == 1)[0]
        re = np.nonzero(dm == -1)[0]   # last valid start = re - 1
        prev_end = 0
        for s0, s1 in zip(rs, re):
            a, b = max(int(s0), prev_end), int(s1 - 1 + w)
            if b > a:
                segs.append((a, b, float(np.mean(u[a:b]))))
                prev_end = b
    d = np.zeros(n)
    d_max = d_c = t_max = 0.0
    if not segs:
        changes = [(0, n, Un, None)]
    else:
        changes = []
        for k, (a, b, lev) in enumerate(segs):
            d[a:b] = (lev - u[a:b]) / Un
            nxt = segs[k + 1] if k + 1 < len(segs) else None
            changes.append((b, nxt[0] if nxt else n, lev, nxt[2] if nxt else None))
    for (a, b, lev, lev_next) in changes:
        if lev_next is not None:
            d_c = max(d_c, abs(lev - lev_next) / Un)
        if b <= a:
            continue
        dd = (lev - u[a:b]) / Un
        d[a:b] = dd
        d_max = max(d_max, float(np.max(np.abs(dd))))
        t_max = max(t_max, _longest_run(np.abs(dd) > d_lim) / (2 * f0))
    return {'d_max': d_max, 'd_c': d_c, 'T_max_s': t_max, 'n_steady_states': len(segs), 'd': d}


# ---------------- test signals ----------------
def sine_modulated(fs, T, dvv, fm, f0=50.0, U=230.0, phase=0.0):
    t = np.arange(int(round(T * fs))) / fs
    return np.sqrt(2) * U * (1 + 0.5 * dvv * np.sin(2 * np.pi * fm * t + phase)) * np.sin(2 * np.pi * f0 * t)


def rect_modulated(fs, T, dvv, cpm, f0=50.0, U=230.0, t_offset=0.0):
    """Rectangular (50 % duty) modulation, dvv = relative change between the two levels,
    cpm = changes per minute (2 changes per modulation period). First change at t_offset."""
    t = np.arange(int(round(T * fs))) / fs
    rate = cpm / 60.0  # changes per second
    k = np.floor((t - t_offset) * rate)
    sq = np.where(k % 2 == 0, -1.0, 1.0)
    sq[t < t_offset] = 1.0
    return np.sqrt(2) * U * (1 + 0.5 * dvv * sq) * np.sin(2 * np.pi * f0 * t)


if __name__ == '__main__':
    fm = Flickermeter()
    print('gain', fm.gain)
    f = np.arange(0.5, 40, 0.01)
    print('|H_w(8.8 Hz)|', weighting_mag(8.8), ' peak f', f[np.argmax(weighting_mag(f))])
    v = sine_modulated(4000, 60, 0.0025, 8.8)
    p = fm.pinst(v)[int(20 * fm.fsd):]
    print('8.8 Hz 0.25 %: mean', p.mean(), 'max', p.max())
