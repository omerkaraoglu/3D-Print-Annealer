"""Fit and validate the generator and device models used by the scope-B simulations.

1. Combination-wave generator (CWG): topology of TI SLVA711 Fig.6 (Cc, Rs1, Rm, Lr, Rs2) fitted to the
   1.2/50 us open-circuit voltage, 8/20 us short-circuit current and the 2 Ohm effective impedance
   (NOT read from the standard; see common.NRS['cwg']); then re-checked in ngspice.
2. ESD generator: 150 pF / 330 Ohm main branch + fast tip branch, fitted to the contact-discharge current
   into a 2 Ohm target (first peak 3.75 A/kV, rise 0.7-1 ns, 2 A/kV at 30 ns, 1 A/kV at 60 ns; NRS).
3. EFT pulse: 5/50 ns into 50 Ohm, 50 Ohm source, 1 kV open circuit (NRS); checked into 50 and 1000 Ohm.
4. MOV models (RV1 TVR14431, RV2 TVR10561) against the datasheet table points; TVS model (PESD5V0S1BA)
   against its two 8/20 clamping points; L40 saturation curves (assumed, plotted).
Outputs: cwg_fit.json, esd_gun_fit.json, results.json['validation'], plots/val_*.png
"""
import json, os
import numpy as np
from scipy.linalg import expm
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as cm

OUT = {}


def lin_sim(A, x0, C, t):
    dt = t[1] - t[0]
    Ad = expm(A * dt)
    x = np.array(x0, float); y = np.empty(len(t))
    for k in range(len(t)):
        y[k] = C @ x
        x = Ad @ x
    return y


# ---------------------------------------------------------------- CWG
def cwg_wave(p, mode, t, U=1.0):
    Cc, Rs1, Rm, Lr, Rs2 = p
    # states: vc, iL ; open: vout = Rs2*iL ; short: vout = 0
    Rl = Rs2 if mode == 'open' else 0.0
    A = np.array([[-1 / (Rs1 * Cc), -1 / Cc], [1 / Lr, -(Rm + Rl) / Lr]])
    C = np.array([0, Rs2]) if mode == 'open' else np.array([0, 1.0])
    return lin_sim(A, [U, 0], C, t)


t_us = np.linspace(0, 200e-6, 40001)


def cwg_metrics(p):
    v = cwg_wave(p, 'open', t_us); i = cwg_wave(p, 'short', t_us)
    T1v, T2v, Vp = cm.front_time_V(t_us, v)
    T1i, T2i, Ip = cm.front_time_I(t_us, i)
    return T1v, T2v, Vp, T1i, T2i, Ip


def cwg_res(lp):
    p = np.exp(lp)
    T1v, T2v, Vp, T1i, T2i, Ip = cwg_metrics(p)
    return [(T1v - 1.2e-6) / 1.2e-6, (T2v - 50e-6) / 50e-6, (T1i - 8e-6) / 8e-6, (T2i - 20e-6) / 20e-6,
            (Vp / Ip - 2.0) / 2.0]


p0 = np.log([10e-6, 20.0, 0.8, 9e-6, 26.0])
sol = least_squares(cwg_res, p0, x_scale=1.0, diff_step=1e-3, max_nfev=400)
pc = np.exp(sol.x)
cwg_fit = dict(zip(['Cc', 'Rs1', 'Rm', 'Lr', 'Rs2'], [float(x) for x in pc]))
json.dump(cwg_fit, open(os.path.join(cm.HERE, 'cwg_fit.json'), 'w'), indent=1)
cm.CWG_PARS.update(cwg_fit)
T1v, T2v, Vp, T1i, T2i, Ip = cwg_metrics(pc)

# ngspice re-check (the circuit actually used by the surge simulation), U scaled so Voc peak = 1 kV
U1k = 1000.0 / Vp
res = {}
for mode in ('open', 'short'):
    load = 'Rload out 0 1e9' if mode == 'open' else 'Rload out 0 1m'
    net = f"cwg check\n{cm.cwg_subckt('CWG', U1k)}\nX1 out 0 CWG PARAMS: ts=1n\n{load}\n.tran 20n 200u uic\n.end\n"
    r = cm.run_netlist(net)
    t = r['time']; y = r['v(out)'] if mode == 'open' else r['v(out)'] / 1e-3
    tu = np.linspace(0, t[-1], 100001); yu = np.interp(tu, t, y)
    res[mode] = (tu, yu)
sv = cm.front_time_V(*res['open']); si = cm.front_time_I(*res['short'])
OUT['cwg'] = {'params': cwg_fit, 'U_for_1kV_open_circuit': U1k,
              'python': {'T1v_us': T1v * 1e6, 'T2v_us': T2v * 1e6, 'T1i_us': T1i * 1e6, 'T2i_us': T2i * 1e6, 'Zeff': Vp / Ip},
              'ngspice': {'T1v_us': sv[0] * 1e6, 'T2v_us': sv[1] * 1e6, 'Voc_pk_V': sv[2], 'T1i_us': si[0] * 1e6,
                          'T2i_us': si[1] * 1e6, 'Isc_pk_A': si[2], 'Zeff_ohm': sv[2] / si[2]},
              'targets': '1.2/50 us (+-30 %/+-20 %), 8/20 us (+-20 %), 2 Ohm (NRS)', 'src': cm.NRS['cwg']['src']}
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(res['open'][0] * 1e6, res['open'][1], label='model, open circuit')
ax[0].axhline(500, ls=':', c='gray'); ax[0].set_xlabel('t (µs)'); ax[0].set_ylabel('V (V)')
ax[0].set_title(f'CWG open circuit: T1 = {sv[0]*1e6:.2f} µs (1.2), T2 = {sv[1]*1e6:.1f} µs (50)'); ax[0].set_xlim(0, 150); ax[0].grid(alpha=.3)
ax[1].plot(res['short'][0] * 1e6, res['short'][1], c='C1', label='model, short circuit')
ax[1].set_xlabel('t (µs)'); ax[1].set_ylabel('I (A)'); ax[1].set_xlim(0, 80); ax[1].grid(alpha=.3)
ax[1].set_title(f'CWG short circuit: T1 = {si[0]*1e6:.2f} µs (8), T2 = {si[1]*1e6:.1f} µs (20), Z = {sv[2]/si[2]:.2f} Ω')
fig.suptitle('Combination-wave generator model at 1 kV (calibration targets NOT read from the standard: TI SLVA711)')
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_cwg.png'), dpi=120); plt.close(fig)


# ---------------------------------------------------------------- ESD gun
def esd_wave(p, t, Rload=2.0, V=1000.0):
    Cm, Rm = 150e-12, 330.0
    Lm, Cs, Rs, Ls = p
    # states: vCm, iLm, vCs, iLs
    A = np.array([[0, -1 / Cm, 0, 0],
                  [1 / Lm, -(Rm + Rload) / Lm, 0, -Rload / Lm],
                  [0, 0, 0, -1 / Cs],
                  [0, -Rload / Ls, 1 / Ls, -(Rs + Rload) / Ls]])
    C = np.array([0, 1, 0, 1.0])
    return lin_sim(A, [V, 0, V, 0], C, t)


t_ns = np.linspace(0, 120e-9, 24001)


def esd_metrics(p):
    i = esd_wave(p, t_ns)
    ip = np.argmax(i[: int(len(t_ns) * 5 / 120)]); Ip = i[ip]
    t10 = np.interp(0.1 * Ip, i[:ip + 1], t_ns[:ip + 1]); t90 = np.interp(0.9 * Ip, i[:ip + 1], t_ns[:ip + 1])
    I30 = np.interp(30e-9, t_ns, i); I60 = np.interp(60e-9, t_ns, i)
    return Ip, t90 - t10, I30, I60, i


def esd_res(lp):
    Ip, tr, I30, I60, _ = esd_metrics(np.exp(lp))
    return [(Ip - 3.75) / 3.75, (tr - 0.8e-9) / 0.8e-9, 0.5 * (I30 - 2.0) / 2.0, 0.5 * (I60 - 1.0) / 1.0]


q0 = np.log([1.0e-6, 6e-12, 150.0, 50e-9])
sol = least_squares(esd_res, q0, diff_step=1e-3, max_nfev=400,
                    bounds=(np.log([0.2e-6, 1e-12, 20.0, 5e-9]), np.log([5e-6, 20e-12, 600.0, 300e-9])))
pe = np.exp(sol.x)
esd_fit = {'Cm': 150e-12, 'Rm': 330.0, 'Lm': float(pe[0]), 'Cs': float(pe[1]), 'Rs': float(pe[2]), 'Ls': float(pe[3])}
json.dump(esd_fit, open(os.path.join(cm.HERE, 'esd_gun_fit.json'), 'w'), indent=1)
cm.ESD_PARS.update(esd_fit)
Ip, tr, I30, I60, iw = esd_metrics(pe)
# ngspice check at 4 kV into 2 Ohm
net = f"esd check\n{cm.esd_gun_subckt('G', 4000.0)}\nX1 tip 0 G\nRt tip 0 2\n.tran 5p 120n uic\n.end\n"
r = cm.run_netlist(net)
ts = r['time']; isp = r['v(tip)'] / 2.0
k5 = ts < 5e-9
Ip_s = isp[k5].max(); ipk = np.argmax(isp[k5])
t10 = np.interp(0.1 * Ip_s, isp[:ipk + 1], ts[:ipk + 1]); t90 = np.interp(0.9 * Ip_s, isp[:ipk + 1], ts[:ipk + 1])
OUT['esd_gun'] = {'params': esd_fit,
                  'per_kV_python': {'Ip': Ip, 'tr_ns': tr * 1e9, 'I30': I30, 'I60': I60},
                  'ngspice_4kV': {'Ip_A': Ip_s, 'tr_ns': (t90 - t10) * 1e9, 'I30_A': float(np.interp(30e-9, ts, isp)),
                                  'I60_A': float(np.interp(60e-9, ts, isp))},
                  'targets_per_kV': '3.75 A (+-15 %), tr 0.8 ns (+-25 %), 2 A @30 ns, 1 A @60 ns (+-30 %) (NRS)',
                  'src': cm.NRS['esd']['src']}
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(ts * 1e9, isp, label='model, 4 kV contact into 2 Ω (ngspice)')
for tt, val, tol in ((None, 15.0, .15), (30, 8.0, .3), (60, 4.0, .3)):
    x = 1.0 if tt is None else tt
    ax.errorbar([x], [val], yerr=[[val * tol], [val * tol]], fmt='rs', capsize=4)
ax.set_xlabel('t (ns)'); ax.set_ylabel('I (A)'); ax.grid(alpha=.3); ax.set_xlim(0, 100)
ax.set_title(f'ESD generator 4 kV: Ip {Ip_s:.1f} A (15 ±15 %), tr {(t90-t10)*1e9:.2f} ns, I30 {np.interp(30e-9, ts, isp):.1f} A (8), I60 {np.interp(60e-9, ts, isp):.1f} A (4)', fontsize=9)
ax.legend(['model', 'targets ±tol (NOT read from the standard)'])
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_esd_gun.png'), dpi=120); plt.close(fig)


# ---------------------------------------------------------------- EFT pulse
def eft_shape(t, a, b):
    return (1 - np.exp(-t / a)) ** 4 * np.exp(-t / b)


tt = np.linspace(0, 400e-9, 40001)


def eft_metrics(a, b):
    v = eft_shape(tt, a, b); v = v / v.max(); ip = np.argmax(v)
    tr = np.interp(.9, v[:ip + 1], tt[:ip + 1]) - np.interp(.1, v[:ip + 1], tt[:ip + 1])
    td = tt[ip + np.where(v[ip:] < .5)[0][0]] - np.interp(.5, v[:ip + 1], tt[:ip + 1])
    return tr, td


sol = least_squares(lambda lp: [(eft_metrics(*np.exp(lp))[0] - 5e-9) / 5e-9, (eft_metrics(*np.exp(lp))[1] - 50e-9) / 50e-9],
                    np.log([2e-9, 60e-9]), diff_step=1e-3)
ea, eb = np.exp(sol.x)
eft_fit = {'a': float(ea), 'b': float(eb)}
json.dump(eft_fit, open(os.path.join(cm.HERE, 'eft_fit.json'), 'w'), indent=1)
tr_e, td_e = eft_metrics(ea, eb)
vv = eft_shape(tt, ea, eb); vv /= vv.max()
OUT['eft'] = {'shape': 'v(t) = Voc (1-exp(-t/a))^4 exp(-t/b), normalised, 50 Ohm source', 'a_s': ea, 'b_s': eb,
              'tr_ns_50ohm': tr_e * 1e9, 'td_ns_50ohm': td_e * 1e9, 'V_50ohm_at_1kV': 500.0, 'V_1000ohm_at_1kV': 1000 * 1000 / 1050,
              'targets': '5 ns +-30 %, 50 ns +-30 % (NRS)', 'src': cm.NRS['eft']['src']}
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.plot(tt * 1e9, 500 * vv, label='into 50 Ω (500 V)'); ax.plot(tt * 1e9, 1000 * 1000 / 1050 * vv, label='into 1000 Ω (952 V)')
ax.set_xlabel('t (ns)'); ax.set_ylabel('V (V)'); ax.grid(alpha=.3); ax.legend()
ax.set_title(f'EFT pulse model, 1 kV level: tr {tr_e*1e9:.2f} ns (5 ± 30 %), td {td_e*1e9:.1f} ns (50 ± 30 %) — NRS', fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_eft.png'), dpi=120); plt.close(fig)

# ---------------------------------------------------------------- MOVs and TVS
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
mv = {}
for k, (name, a) in enumerate((('RV1', ax[0]), ('RV2', ax[1]))):
    Vd, Id = cm.mov_curve(name, 'max')
    for corner, ls in (('max', '-'), ('nom', '--'), ('min', ':')):
        I = np.logspace(-5, np.log10(P_Imax := cm.P[name]['Imax_8_20']), 300)
        V = np.interp(np.log10(I), np.log10(cm.mov_curve(name, corner)[1]), cm.mov_curve(name, corner)[0])
        a.semilogx(I, V, ls, c='C0', label=f'model {corner}')
    a.semilogx(Id, Vd, 'kx', label='digitised datasheet curve (max)')
    a.plot([cm.P[name]['Ip']], [cm.P[name]['Vc']], 'rs', ms=8, label=f"table: Vc {cm.P[name]['Vc']} V @ {cm.P[name]['Ip']} A")
    a.plot([1e-3, 1e-3, 1e-3], cm.P[name]['V1mA'], 'g^', label='V1mA min/nom/max')
    a.set_xlabel('I (A)'); a.set_ylabel('V (V)'); a.grid(alpha=.3, which='both'); a.legend(fontsize=7)
    a.set_title(f"{name} {cm.P[name]['part']} (Thinking TVR, DS p.{23 if name=='RV2' else 24})")
    vc_model = np.interp(np.log10(cm.P[name]['Ip']), np.log10(Id), Vd)
    mv[name] = {'Vc_table': cm.P[name]['Vc'], 'Vc_model_max_curve': float(vc_model),
                'error_pct': float((vc_model - cm.P[name]['Vc']) / cm.P[name]['Vc'] * 100)}
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_mov.png'), dpi=120); plt.close(fig)
OUT['mov'] = mv

# TVS
TVS_PTS = [(0.0, 0.0), (5.0, 1e-7), (7.5, 1e-3), (9.0, 0.2), (10.0, 1.0), (14.0, 12.0), (30.0, 12.0 + 16 / 0.3636)]
json.dump({'pts': TVS_PTS, 'src': cm.P['PESD5V0S1BA']['src'] + '; knee 1 mA at VBR mid-range 7.5 V (ASM), Rd = (14-10)/11 = 0.364 Ohm'},
          open(os.path.join(cm.HERE, 'tvs_model.json'), 'w'), indent=1)
fig, ax = plt.subplots(figsize=(6, 4))
v = np.array([p[0] for p in TVS_PTS]); i = np.array([p[1] for p in TVS_PTS])
ax.plot(i[1:], v[1:], 'o-', label='model (pwl)'); ax.plot([1, 12], [10, 14], 'rs', ms=9, label='datasheet VCL max (8/20 µs)')
ax.axhspan(5.5, 9.5, color='g', alpha=.15, label='VBR 5.5–9.5 V @ 1 mA')
ax.set_xscale('log'); ax.set_xlabel('I (A)'); ax.set_ylabel('V (V)'); ax.grid(alpha=.3, which='both'); ax.legend(fontsize=8)
ax.set_title('PESD5V0S1BA model vs Nexperia data (26 Apr 2024, p.4)', fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_tvs.png'), dpi=120); plt.close(fig)
OUT['tvs'] = {'pts': TVS_PTS, 'Rd_ohm': 0.364, 'check': 'passes through both datasheet points by construction'}

# L40 saturation (assumed)
fig, ax = plt.subplots(figsize=(6, 4))
for Lsat in cm.P['L40_Lsat'][0]:
    for Isat in cm.P['L40_Isat'][0]:
        L0 = cm.P['L40_L0'][0]; ph_s = L0 * Isat
        phi = np.linspace(0, 6 * ph_s, 400)
        I = phi / Lsat - (1 / Lsat - 1 / L0) * ph_s * np.tanh(phi / ph_s)
        ax.plot(I, phi * 1e3, lw=1, label=f'Lsat {Lsat*1e6:.0f} µH, knee {Isat:.0f} A')
ax.set_xlim(0, 150); ax.set_xlabel('I (A)'); ax.set_ylabel('flux linkage (mWb)'); ax.grid(alpha=.3)
ax.set_title('L40 RC1415U-101K saturation models (ASSUMED, swept)', fontsize=9); ax.legend(fontsize=6)
fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'val_L40_sat.png'), dpi=120); plt.close(fig)

cm.save_results('validation', OUT)
print(json.dumps(OUT, indent=1, default=float))
