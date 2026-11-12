"""Electrical model of the filament-dryer heater on the IEC 61000-3-3 reference impedance,
heater switching patterns (current firmware and alternatives), and a cached, parallel
evaluation driver (P_st, d-parameters, modulation spectrum, thermal ripple)."""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flickermeter as fl  # noqa: E402

# ---------------- electrical model ----------------
U = 230.0
F0 = 50.0
W = 2 * np.pi * F0
R_REF = 0.40
L_REF = 0.25 / W
R_H = U ** 2 / 1000.0          # 52.9 ohm
T_FIRE = 230e-6                # gate delay after the zero crossing
FS = 4000.0                    # flickermeter input sample rate
PRE_S = 30.0                   # pre-roll (discarded)
OBS_S = 600.0                  # 10-min observation
N_PRE = int(PRE_S * F0)
N_OBS = int(OBS_S * F0)
N_CYC = N_PRE + N_OBS
SD_FULL = 65536


def half_cycle_shapes(tau):
    """Terminal voltage over one positive half cycle (local time tau in [0, T/2)) for the
    off case (no current) and the on case (triac fired at T_FIRE, conducts to the end of the
    half cycle). Series R-L source impedance, resistive load, exact transient solution."""
    vs = np.sqrt(2) * U * np.sin(W * tau)
    R = R_H + R_REF
    Z = complex(R, W * L_REF)
    phi = np.angle(Z)
    tc = L_REF / R
    i = np.sqrt(2) * U / abs(Z) * (np.sin(W * tau - phi) - np.sin(W * T_FIRE - phi) * np.exp(-(tau - T_FIRE) / tc))
    v_on = np.where(tau >= T_FIRE, R_H * i, vs)
    return vs, v_on


def templates(fs=FS):
    n = int(round(fs / (2 * F0)))
    tau = np.arange(n) / fs
    off, on = half_cycle_shapes(tau)
    # exact half-cycle rms from a 1 MHz grid
    tf = (np.arange(10000) + 0.5) / 1e6
    off_f, on_f = half_cycle_shapes(tf)
    return off, on, float(np.sqrt(np.mean(off_f ** 2))), float(np.sqrt(np.mean(on_f ** 2)))


TPL_OFF, TPL_ON, U_OFF, U_ON = templates()
DU_REL = (U_OFF - U_ON) / U_OFF


def waveform(cycles_on, fs=FS):
    """Terminal voltage for a per-full-cycle on/off sequence (starts at a + zero crossing)."""
    on_hc = np.repeat(np.asarray(cycles_on, dtype=bool), 2)
    sign = np.where(np.arange(on_hc.size) % 2 == 0, 1.0, -1.0)
    off, on = (TPL_OFF, TPL_ON) if fs == FS else templates(fs)[:2]
    return (np.where(on_hc[:, None], on[None, :], off[None, :]) * sign[:, None]).reshape(-1)


# ---------------- switching patterns (per full mains cycle) ----------------
def sd_increment(duty):
    return int(round(duty * SD_FULL))


def pat_sd1(duty, n=N_CYC, K=1):
    """Current firmware for K=1: first-order sigma-delta, 16-bit accumulator, one decision
    per K full cycles, fire all K cycles when the accumulator overflows."""
    inc = sd_increment(duty)
    nd = -(-n // K)
    j = np.arange(nd + 1, dtype=np.int64)
    fire = np.diff((j * inc) // SD_FULL) > 0
    return np.repeat(fire, K)[:n]


def pat_burst(duty, n=N_CYC, N=50):
    """Fixed-period burst: round(duty*N) consecutive on cycles at the start of every N."""
    non = int(round(duty * N))
    return (np.arange(n) % N) < non


def pat_burst_dither(duty, n=N_CYC, N=500):
    """Fixed-period burst with error carry: each period the on-count is
    floor((acc + inc*N)/65536), remainder kept in acc (mean duty resolution 1/65536)."""
    inc = sd_increment(duty)
    npd = -(-n // N)
    p = np.arange(npd + 1, dtype=np.int64)
    non = np.diff((p * inc * N) // SD_FULL)
    idx = np.arange(n)
    return (idx % N) < non[idx // N]


def pat_sd2(duty, n=N_CYC, K=1):
    """Second-order error-feedback sigma-delta, NTF = (1 - z^-1)^2, 1-bit, decision per K cycles."""
    nd = -(-n // K)
    y = np.zeros(nd, dtype=bool)
    q1 = q2 = 0.0
    for k in range(nd):
        u = duty - 2 * q1 + q2
        yk = 1.0 if u >= 0.5 else 0.0
        q = yk - u
        q2, q1 = q1, q
        y[k] = yk > 0
    return np.repeat(y, K)[:n]


PATTERNS = {'sd1': pat_sd1, 'burst': pat_burst, 'burst_dither': pat_burst_dither, 'sd2': pat_sd2}


def make_pattern(family, param, duty):
    f = PATTERNS[family]
    if family in ('sd1', 'sd2'):
        return f(duty, K=int(param))
    return f(duty, N=int(param))


# ---------------- analysis helpers ----------------
def modulation_peaks(on_obs, top=3):
    """Peaks of the rms-envelope modulation spectrum (per-cycle sequence sampled at 50 Hz).
    Amplitude = peak of the sinusoidal component of the voltage envelope, % of U."""
    x = on_obs.astype(float)
    x = x - x.mean()
    X = np.abs(np.fft.rfft(x)) * 2 / x.size
    if x.size % 2 == 0:
        X[-1] /= 2  # Nyquist bin (25 Hz) is not doubled
    f = np.fft.rfftfreq(x.size, 1 / F0)
    amp = X * DU_REL * 100
    amp[0] = 0.0
    a = np.concatenate([amp, [0.0]])
    loc = np.nonzero((a[1:-1] >= a[:-2]) & (a[1:-1] >= a[2:]) & (a[1:-1] > 1e-6))[0] + 1
    if loc.size == 0:
        return [], []
    by_amp = loc[np.argsort(amp[loc])[::-1][:top]]
    wamp = amp * fl.weighting_mag(np.maximum(f, 1e-6))
    by_w = loc[np.argsort(wamp[loc])[::-1][:top]]
    return ([[round(float(f[i]), 4), round(float(amp[i]), 4)] for i in by_amp],
            [[round(float(f[i]), 4), round(float(amp[i]), 4), round(float(wamp[i]), 4)] for i in by_w])


def thermal_ripple(on_obs, duty_mean, taus=(60.0, 180.0, 300.0)):
    """Peak-to-peak ripple of a first-order thermal response to the heater power sequence,
    in % of the full-power steady-state temperature rise. Settles over the pre-roll first."""
    out = {}
    x = on_obs.astype(float)
    for tau in taus:
        a = np.exp(-1 / (F0 * tau))
        y = signal.lfilter([1 - a], [1, -a], x, zi=[a * duty_mean])[0]
        y = y[int(min(3 * tau, OBS_S / 2) * F0):]
        out[f'{int(tau)}'] = float((y.max() - y.min()) * 100)
    return out


def longest_on_spacing_s(on_obs):
    """Longest time between consecutive burst starts (rising edges) = slowest power-modulation period."""
    x = on_obs.astype(np.int8)
    rise = np.nonzero(np.diff(x) == 1)[0]
    if rise.size < 2:
        return None
    return float(np.max(np.diff(rise)) / F0)


# ---------------- evaluation ----------------
_FM = None


def _init():
    global _FM
    _FM = fl.Flickermeter(fs=FS, hp_order=1)


def evaluate(case):
    family, param, duty = case
    if _FM is None:
        _init()
    on = make_pattern(family, param, duty)
    v = waveform(on)
    p = _FM.pinst(v)[int(PRE_S * _FM.fsd):]
    on_obs = on[N_PRE:]
    # d-parameters: 2 s off (steady state), then the pattern from its start
    hc = np.concatenate([np.full(200, U_OFF), np.where(np.repeat(on, 2), U_ON, U_OFF)])
    dp = fl.d_parameters(hc, Un=U)
    peaks, wpeaks = modulation_peaks(on_obs)
    return {
        'family': family, 'param': param, 'duty_cmd': duty,
        'duty_real': float(on_obs.mean()),
        'pst': fl.pst(p, 'cpf'), 'pst_exact_pct': fl.pst(p, 'exact'),
        'pinst_max': float(p.max()), 'pinst_mean': float(p.mean()),
        'd_max_pct': 100 * dp['d_max'], 'd_c_pct': 100 * dp['d_c'], 'T_max_s': dp['T_max_s'],
        'n_steady_states': dp['n_steady_states'],
        'changes_per_min': float(np.count_nonzero(np.diff(on_obs.astype(np.int8))) / (OBS_S / 60)),
        'peaks_f_hz_amp_pct': peaks, 'weighted_peaks_f_hz_amp_pct_wamp': wpeaks,
        'thermal_ripple_pp_pct': thermal_ripple(on_obs, float(on_obs.mean())),
        'longest_on_spacing_s': longest_on_spacing_s(on_obs),
    }


def key(case):
    family, param, duty = case
    return f'{family}|{param}|{duty:.6f}'


def run_cases(cases, cache_path, workers=None):
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f).get('results', {})
    todo = [c for c in cases if key(c) not in cache]
    t0 = time.time()
    if todo:
        workers = workers or max(1, os.cpu_count() - 2)
        with ProcessPoolExecutor(max_workers=workers, initializer=_init) as ex:
            futs = {ex.submit(evaluate, c): c for c in todo}
            for k, fu in enumerate(as_completed(futs), 1):
                cache[key(futs[fu])] = fu.result()
                if k % 40 == 0 or k == len(todo):
                    _save(cache_path, cache)
                    print(f'  {k}/{len(todo)} done, {time.time() - t0:.0f} s', flush=True)
    return cache


def _save(path, cache):
    meta = {'U_V': U, 'Zref': '0.40 + j0.25 ohm', 'R_heater_ohm': R_H, 't_fire_us': T_FIRE * 1e6,
            'U_off_V': U_OFF, 'U_on_V': U_ON, 'dU_rel_pct': 100 * DU_REL, 'fs_hz': FS,
            'pre_roll_s': PRE_S, 'observation_s': OBS_S}
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump({'meta': meta, 'results': cache}, f, indent=0)
    os.replace(tmp, path)


if __name__ == '__main__':
    print('U_off', U_OFF, 'U_on', U_ON, 'dU %', 100 * DU_REL)
    for d in (0.5, 1 / 3, 0.1):
        print(d, pat_sd1(d, 12).astype(int))
    print(pat_burst_dither(0.3333, 30, N=10).astype(int))
    print(pat_sd2(0.3, 20).astype(int))
    t = time.time()
    r = evaluate(('sd1', 1, 0.1))
    print(time.time() - t, {k: r[k] for k in ('pst', 'pst_exact_pct', 'd_max_pct', 'd_c_pct', 'peaks_f_hz_amp_pct')})
