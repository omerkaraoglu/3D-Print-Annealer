"""Post-layout EMC estimates for the Rev3.0 controller (EN 55014-1 / IEC 61000-3-2 context).
Outputs estimates.json and plots. System Python (numpy, matplotlib)."""
import json, math, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT = os.path.dirname(os.path.abspath(__file__))
dB = lambda x: 20 * math.log10(max(x, 1e-30))
res = {}

# ---------------------------------------------------------------- limits (EN 55014-1:2017 Table 5, Table 9) ----
def lim_mains_qp(f):      # dBuV, mains port, quasi-peak
    if f < 0.5e6: return 66 + (56 - 66) * math.log10(f / 0.15e6) / math.log10(0.5 / 0.15)
    if f < 5e6: return 56
    return 60
def lim_mains_av(f):
    if f < 0.5e6: return 56 + (46 - 56) * math.log10(f / 0.15e6) / math.log10(0.5 / 0.15)
    if f < 5e6: return 46
    return 50
def lim_rad_far3m(f):     # dBuV/m, FAR 3 m, Table 9
    if f < 230e6: return 42 + (35 - 42) * math.log10(f / 30e6) / math.log10(230 / 30)
    return 42
def lim_rad_oats10m(f): return 30 if f < 230e6 else 37

# ---------------------------------------------------------------- 1. conducted: triac turn-on step at the LISN ----
# Heater branch: J3 -> F3 -> Q1 -> R1 (52.9 ohm) -> NEUT. Triac fired t_d after the zero crossing: v = Vpk*sin(w t_d).
# Current step dI = v/R, rise limited by the series inductance (LISN 2x50 uH + cable + heater element) over R.
# LISN per line: 50 ohm receiver (via 0.25 uF) in parallel with 50 uH to the supply. DM current flows through both lines.
# QP reading for a 100 Hz pulse train (Band B): CISPR 16-1-1 pulse response: impulse area 0.316 uVs emf at 100 Hz PRF reads
# like a 2 mV emf sine -> at the 50 ohm input: 0.158 uVs <-> 1 mV rms (60 dBuV).  Reading = 60 dB + 20log(A/0.158 uVs).
Vrms, R = 230.0, 52.9
L_lisn, L_cable, L_heater = 50e-6, 3e-6, 20e-6         # per line LISN 50 uH (two in series for DM), 2 m cable, coiled element
def lisn_line(f):
    w = 2 * math.pi * f
    zrec = 50 + 1 / (1j * w * 0.25e-6); zsup = 1j * w * L_lisn
    return zrec * zsup / (zrec + zsup), zrec, zsup       # impedance seen per line, and the branches
def step_spectrum(f, dI, tau):
    return dI / (2 * math.pi * f) / math.sqrt(1 + (2 * math.pi * f * tau) ** 2)   # |I(f)| of one step, A*s
def heater_reading(f, V_on, cx=0.0, Ls=0.0, Rdamp=0.0):
    """QP reading (dBuV) at frequency f for a turn-on voltage V_on, with an optional X2 capacitor cx across the heater
    branch and a series inductor Ls between the capacitor and the mains (plus the LISN)."""
    w = 2 * math.pi * f
    dI = V_on / R
    tau = (2 * L_lisn + L_cable + L_heater + Ls) / R if cx == 0 else (L_cable + L_heater) / R   # with a local cap the step is sourced locally
    zl, zrec, zsup = lisn_line(f)
    z_dm = 2 * zl                                        # both lines
    I_step = step_spectrum(f, dI, tau)
    if cx > 0:
        zc = 1 / (1j * w * cx) + Rdamp
        frac = abs(zc / (zc + z_dm + 1j * w * Ls))      # current divider: local capacitor vs mains path
    else:
        frac = 1.0
    I_lisn = I_step * frac
    V_rec = abs(I_lisn * zl)                             # voltage per line at the port node (receiver sees it through 0.25 uF)
    # the receiver sees the port node voltage through the 0.25 uF (negligible above 150 kHz)
    A = V_rec                                            # V*s impulse-area equivalent at the receiver input
    return 60 + dB(A / 0.158e-6)
freqs = np.logspace(math.log10(150e3), math.log10(30e6), 200)
cases = {
    "as designed (no filter in heater path), V_on 23 V": dict(V_on=23.0),
    "as designed, V_on 40 V (late ZCD)": dict(V_on=40.0),
    "as designed, V_on 10 V": dict(V_on=10.0),
    "X2 0.22 uF across heater branch": dict(V_on=23.0, cx=0.22e-6),
    "X2 0.47 uF across heater branch": dict(V_on=23.0, cx=0.47e-6),
    "X2 1 uF across heater branch": dict(V_on=23.0, cx=1.0e-6),
    "X2 0.47 uF + 47 uH series (heater branch)": dict(V_on=23.0, cx=0.47e-6, Ls=47e-6),
    "heater behind existing L40 120 uH + C40 1 uF + C1": dict(V_on=23.0, cx=1.1e-6, Ls=120e-6),
    "heater behind L40/C40, V_on 40 V": dict(V_on=40.0, cx=1.1e-6, Ls=120e-6),
}
cond = {}
for name, kw in cases.items():
    r = [heater_reading(f, **kw) for f in freqs]
    marg = [lim_mains_qp(f) - v for f, v in zip(freqs, r)]
    i = int(np.argmin(marg))
    cond[name] = dict(at_150k=round(r[0], 1), at_500k=round(float(np.interp(500e3, freqs, r)), 1), at_1M=round(float(np.interp(1e6, freqs, r)), 1),
                      at_5M=round(float(np.interp(5e6, freqs, r)), 1), worst_margin_dB=round(marg[i], 1), worst_at_MHz=round(freqs[i] / 1e6, 3))
res["conducted_heater_turn_on"] = dict(model="current step dI=V_on/R at 100 Hz, exponential rise tau=L/R, LISN 50 ohm||50 uH per line, CISPR 16-1-1 Band B pulse weighting (0.158 uVs <-> 60 dBuV at 100 Hz PRF)",
                                       limit="EN 55014-1 Table 5 col 2 (QP): 66->56 dBuV 0.15-0.5 MHz, 56 dBuV 0.5-5 MHz, 60 dBuV 5-30 MHz",
                                       cases=cond)
plt.figure(figsize=(8, 5))
for name, kw in list(cases.items())[:1] + list(cases.items())[3:8]:
    plt.semilogx(freqs / 1e6, [heater_reading(f, **kw) for f in freqs], label=name)
plt.semilogx(freqs / 1e6, [lim_mains_qp(f) for f in freqs], "k--", label="EN 55014-1 QP limit")
plt.semilogx(freqs / 1e6, [lim_mains_av(f) for f in freqs], "k:", label="EN 55014-1 AV limit")
plt.xlabel("MHz"); plt.ylabel("dBµV at the LISN"); plt.title("Heater triac turn-on (full-cycle firing, 230 µs after zero cross)")
plt.grid(True, which="both", alpha=.3); plt.legend(fontsize=7); plt.tight_layout(); plt.savefig(os.path.join(OUT, "conducted_heater.png"), dpi=150)

# ---------------------------------------------------------------- 2. harmonics of the notched heater current (61000-3-2) ----
def harmonics(t_d, n_cycles_on=1, n_cycles_off=0):
    fs = 200e3; T = 0.02; N = int(fs * T)
    t = np.arange(N) / fs
    v = math.sqrt(2) * Vrms * np.sin(2 * math.pi * 50 * t)
    g = np.ones(N); half = N // 2
    nd = int(t_d * fs)
    g[:nd] = 0; g[half:half + nd] = 0                     # triac off for t_d after each zero crossing
    i = v / R * g
    spec = np.fft.rfft(i) / N * 2
    return {h: float(abs(spec[h])) for h in range(2, 41)}, float(np.sqrt(np.mean(i ** 2)))
classA = {3: 2.30, 5: 1.14, 7: 0.77, 9: 0.40, 11: 0.33, 13: 0.21, 2: 1.08, 4: 0.43, 6: 0.30}
for h in range(15, 40, 2): classA[h] = 0.15 * 15 / h
for h in range(8, 41, 2): classA[h] = 0.23 * 8 / h
harm = {}
for td in (230e-6, 500e-6, 1000e-6):
    hs, irms = harmonics(td)
    worst = max(((hs[h] / classA[h]), h) for h in classA)
    harm[f"t_d={td*1e6:.0f}us"] = dict(I_rms=round(irms, 3), I3=round(hs[3], 4), I5=round(hs[5], 4), I7=round(hs[7], 4),
                                       worst_ratio_to_classA=round(worst[0], 4), worst_order=worst[1])
res["harmonics_61000_3_2"] = dict(note="whole-cycle on/off control adds no integer harmonics (the gate is constant over each cycle); only the turn-on notch t_d after each zero crossing does; full-on case shown, Class A Table 1 limits", cases=harm)

# ---------------------------------------------------------------- 3. radiated: switching loops and the RGB bus (DM) ----
def trapezoid_harm(I, f0, d, tr, f):
    """peak amplitude of the trapezoid current harmonic at frequency f (envelope), Ott: 2 I d |sinc(pi f d T)| |sinc(pi f tr)|"""
    T = 1 / f0                                             # envelope (not the exact sinc nulls)
    s1 = min(1.0, 1 / (math.pi * f * d * T))
    s2 = min(1.0, 1 / (math.pi * f * tr))
    return 2 * I * d * s1 * s2
def E_loop(I, A, f, r=3.0): return 1.316e-14 * f ** 2 * A * I / r     # V/m (Ott), free space, add +6 dB for ground reflection
loops = {
    "buck hot loop (C330/C331-U30-GND, 1 A, 580 kHz, 20 ns)": dict(I=1.0, f0=580e3, d=0.66, tr=20e-9, A=10e-6),
    "boost loop (L11-U11-D111-C125, 0.5 A, 1.2 MHz, 15 ns)": dict(I=0.5, f0=1.2e6, d=0.5, tr=15e-9, A=20e-6),
    "RGB bus, 28 lines in phase, 33 MHz PCLK, 2 ns edges, 110 mm over 0.2 mm": dict(I=28 * 16.5e-3, f0=33.3e6, d=0.5, tr=2e-9, A=110e-3 * 0.2e-3),
}
rad = {}
for name, p in loops.items():
    rows = {}
    for f in (30e6, 50e6, 100e6, 200e6, 300e6, 500e6, 1000e6):
        if name.startswith("RGB"):
            n = max(1, round(f / p["f0"])); fh = n * p["f0"]
            Ih = trapezoid_harm(p["I"], p["f0"], p["d"], p["tr"], fh) if n % 2 == 1 else 0.0   # 50 % duty: odd harmonics only
            if Ih == 0: Ih = trapezoid_harm(p["I"], p["f0"], p["d"], p["tr"], (n + 1) * p["f0"]); fh = (n + 1) * p["f0"]
        else:
            Ih = trapezoid_harm(p["I"], p["f0"], p["d"], p["tr"], f); fh = f
        E = E_loop(Ih, p["A"], fh, 3.0) * 2         # +6 dB ground reflection
        rows[f"{f/1e6:.0f}MHz"] = dict(I_harm_mA=round(Ih * 1e3, 3), E_3m_dBuVm=round(dB(E) + 120, 1), limit_far3m=round(lim_rad_far3m(f), 1))
    rad[name] = rows
res["radiated_dm_loops"] = dict(model="Ott small-loop DM: E = 1.316e-14 f^2 A I / r, +6 dB ground reflection, 3 m; harmonic envelope of a trapezoid", cases=rad)

# ---------------------------------------------------------------- 4. common-mode current budget per cable ----
def I_cm_max(f, L, r=3.0):
    E = 10 ** ((lim_rad_far3m(f) - 120) / 20)
    if L >= 3e8 / f / 4:                                # resonant: bound E = 60 I / r
        return E * r / 60
    return E * r / (1.257e-6 * f * L)
cm = {}
for cable, L in (("mains cable 2 m", 2.0), ("heater cable 1 m", 1.0), ("thermocouple cable 1 m", 1.0), ("fan cable 0.5 m", 0.5), ("TFT FPC 50 mm", 0.05), ("CTP FPC 50 mm", 0.05)):
    cm[cable] = {f"{f/1e6:.0f}MHz": round(I_cm_max(f, L) * 1e6, 2) for f in (30e6, 50e6, 100e6, 200e6, 300e6, 500e6, 1000e6)}
res["common_mode_current_budget_uA"] = dict(model="E = 1.257e-6 f L I / r (short wire) or 60 I / r (resonant, L >= lambda/4), FAR 3 m limit, no ground-reflection margin", budget=cm)

json.dump(res, open(os.path.join(OUT, "estimates.json"), "w"), indent=1)
for k, v in res.items():
    print("==", k)
    print(json.dumps(v, indent=1)[:3000])
