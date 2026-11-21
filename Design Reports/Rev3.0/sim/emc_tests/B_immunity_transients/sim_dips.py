"""Voltage dips -- EN 55014-2 5.7 Table 13 (PDF p.21), criterion C; interruptions are not performed (5.7).

Rows: 0 % residual for 0.5 cycle, 40 % for 10 cycles, 70 % for 25 cycles, change at zero crossing (STD).
Generator (NRS, IS 14700-4-11 = IEC 61000-4-11:2004 Table 4): rise/fall 1-5 us (treated as a step), output impedance
< 0.4 + j0.25 Ohm.

Black-box HLK-10M05 model (time-domain, numpy):
  mains -> F1/L1 (neglected) -> 11 Ohm inrush resistor (34 A inrush at 264 Vac, DS p.2) -> bridge (2 x 1 V)
  -> bulk capacitor Cb -> flyback drawing P_in = P_5V / eta while V_bulk > V_off, regulated 5.0 V output.
  Cb is derived from the datasheet envelope (DS 10M series V1.5 Fig.6 p.9: 85 Vac -> ~85 % load, and the DC curve
  70 Vdc -> 70 % load): holding 85 % of 12.5 W input for one half cycle at 85 Vac with the bulk staying >= 70 V
  needs Cb >= 22 uF.  Swept 10 (pessimistic) / 22 / 33 uF;  V_off swept 50 / 70 / 90 V.
5 V rail: C2 220 uF + 2 x 10 uF ceramics at the buck input (SCH), load 5.5 W peak (spec sec.7) as constant power.
3V3: TPS562201 output = min(3.32 V, Dmax * V5 - I*R), Dmax = t_on/(t_on + t_off,min 310 ns) (DS p.5), shut down below
UVLO 3.3 V, restart above 3.8-4.3 V with 1 ms soft start; output caps 2 x 22 uF + ~20 uF distributed; 3V3 load 0.9 A.
ESP32 brown-out reset at 2.43 V (ESP-IDF default level, not a datasheet value).
ZCD: H11AA1 LED current through 66 kOhm, CTR 20 % min (Vishay DS p.2), R8 10k pull-up -> edge timing vs residual.
Run: python -X utf8 sim_dips.py
"""
import itertools, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as cm

F = 50.0; VPK = 230 * np.sqrt(2)


def simulate(residual, cycles, Cb=22e-6, Voff=70.0, P5=5.5, eta=0.80, t_dip=0.1, tend=0.9, Von=None, dt=5e-6):
    Von = Von or 100.0
    t = np.arange(0, tend, dt)
    dur = cycles / F
    amp = np.where((t >= t_dip) & (t < t_dip + dur), residual, 1.0)
    vac = VPK * amp * np.sin(2 * np.pi * F * t)       # t_dip is a multiple of 10 ms -> zero crossing
    vb = np.empty_like(t); v5 = np.empty_like(t); v3 = np.empty_like(t)
    vb_ = VPK - 5; v5_ = 5.0; v3_ = 3.32; run_ = True; buck_on = True; ss = 1.0
    C5 = 220e-6 + 20e-6; C3 = 64e-6
    I3 = 0.9; reset_t = None; bod = False
    for k, tk in enumerate(t):
        va = abs(vac[k]) - 2.0
        i_in = max(0.0, (va - vb_) / 11.0)
        if run_:
            p_in = P5 / eta
            if vb_ < Voff: run_ = False
        else:
            p_in = 0.0
            if vb_ > Von: run_ = True
        vb_ += dt * (i_in - p_in / max(vb_, 1.0)) / Cb
        # 5 V rail: regulated while the flyback runs, else discharged by the constant-power load
        if run_:
            v5_ = min(5.0, v5_ + dt * 2.0 / C5)        # current-limited recovery (~2.2 A short-time, DS p.4)
        else:
            v5_ = max(0.0, v5_ - dt * (P5 / max(v5_, 0.5)) / C5)
        # buck
        if buck_on and v5_ < 3.35: buck_on = False
        if not buck_on and v5_ > 4.05: buck_on = True; ss = 0.0
        if buck_on:
            ss = min(1.0, ss + dt / 1e-3)
            ton = 3.32 / (max(v5_, 0.1) * 580e3)
            dmax = ton / (ton + 310e-9)
            target = min(3.32, dmax * v5_ - I3 * 0.15) * ss
            v3_ = target if target > v3_ else max(target, v3_ - dt * I3 / C3)
        else:
            v3_ = max(0.0, v3_ - dt * I3 / C3)
        if v3_ < 2.43 and not bod:
            bod = True; reset_t = tk
        vb[k] = vb_; v5[k] = v5_; v3[k] = v3_
    w = t >= t_dip - 0.02
    return {'t': t, 'vac': vac, 'vb': vb, 'v5': v5, 'v3': v3,
            'min_vbulk': float(vb[w].min()), 'min_5V': float(v5[w].min()), 'min_3V3': float(v3[w].min()),
            'brownout_reset': bod, 'reset_at_ms': (reset_t - t_dip) * 1e3 if reset_t else None}


def zcd_edge_advance(residual, ctr=0.20, vf=1.2):
    """Time between the ZCD falling edge (node rising through VT+) and the true zero crossing.
    Transistor holds the node below VT- / VT+ while CTR*IF > (3.3 - Vth)/10k."""
    vpk = VPK * residual
    out = {}
    for name, vth in (('VT+ 1.87 V (max)', 1.87), ('VT+ 1.5 V (min)', 1.5)):
        i_need = (3.3 - vth) / 10e3 / ctr
        v_need = i_need * 66e3 + vf
        if v_need >= vpk:
            out[name] = None              # transistor never pulls low enough: no edges at all
        else:
            out[name] = float(np.arcsin(v_need / vpk) / (2 * np.pi * F) * 1e6)
    return out, float((VPK * residual - vf) / 66e3 * 1e3)


def main():
    rows = cm.STD['dips']['rows']
    res = {'rows': [], 'zcd': {}}
    worst_plot = {}
    for row in rows:
        resid = row['residual_pct'] / 100; cyc = row['cycles_50Hz']
        for Cb, Voff, P5 in itertools.product((10e-6, 22e-6, 33e-6), (50.0, 70.0, 90.0), (3.5, 5.5)):
            s = simulate(resid, cyc, Cb=Cb, Voff=Voff, P5=P5)
            res['rows'].append({'residual_pct': row['residual_pct'], 'cycles': cyc, 'Cbulk_uF': Cb * 1e6, 'Voff': Voff, 'P5_W': P5,
                                **{k: s[k] for k in ('min_vbulk', 'min_5V', 'min_3V3', 'brownout_reset', 'reset_at_ms')}})
            if Cb == 22e-6 and Voff == 70.0 and P5 == 5.5:
                worst_plot[row['residual_pct']] = s
        adv, ipk = zcd_edge_advance(resid)
        res['zcd'][f"{row['residual_pct']} %"] = {'edge_before_zero_us_min_CTR': adv, 'LED_peak_mA': ipk}
    adv, ipk = zcd_edge_advance(1.0)
    res['zcd']['100 % (nominal)'] = {'edge_before_zero_us_min_CTR': adv, 'LED_peak_mA': ipk}
    # summary per row
    summ = {}
    for row in rows:
        rr = [r for r in res['rows'] if r['residual_pct'] == row['residual_pct']]
        summ[f"{row['residual_pct']} % / {row['cycles_50Hz']} cyc"] = {
            'resets_in_cases': sum(r['brownout_reset'] for r in rr), 'n_cases': len(rr),
            'resets_with_Cb_ge_22uF': sum(r['brownout_reset'] for r in rr if r['Cbulk_uF'] >= 22),
            'min_5V_Cb22_Voff70_5.5W': [r['min_5V'] for r in rr if r['Cbulk_uF'] == 22 and r['Voff'] == 70 and r['P5_W'] == 5.5][0],
            'min_3V3_Cb22_Voff70_5.5W': [r['min_3V3'] for r in rr if r['Cbulk_uF'] == 22 and r['Voff'] == 70 and r['P5_W'] == 5.5][0],
            'worst_min_5V': min(r['min_5V'] for r in rr), 'worst_min_3V3': min(r['min_3V3'] for r in rr)}
    res['summary'] = summ
    # interruption (info only, not required): find the 0 % duration that first resets with Cb 22 uF, Voff 70 V, 5.5 W
    for cyc in np.arange(0.5, 20.5, 0.5):
        if simulate(0.0, cyc, tend=0.1 + cyc / F + 0.3)['brownout_reset']:
            res['info_first_reset_0pct_cycles'] = float(cyc); break
    cm.save_results('dips', res)
    fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    for pct, s in worst_plot.items():
        tt = (s['t'] - 0.1) * 1e3
        ax[0].plot(tt, s['vb'], label=f'{pct} % residual'); ax[1].plot(tt, s['v5']); ax[2].plot(tt, s['v3'])
    ax[0].axhline(70, c='r', ls=':', label='70 Vdc min input (DS)'); ax[0].set_ylabel('HLK bulk (V)'); ax[0].legend(fontsize=7)
    ax[1].set_ylabel('+5 V (V)'); ax[1].axhline(3.35, c='r', ls=':', label='buck UVLO off 3.3–3.4 V'); ax[1].legend(fontsize=7)
    ax[2].set_ylabel('+3V3 (V)'); ax[2].axhline(2.43, c='r', ls=':', label='ESP32 BOD 2.43 V (ESP-IDF default)'); ax[2].legend(fontsize=7)
    ax[2].set_xlabel('t from dip start (ms)'); ax[2].set_xlim(-20, 700)
    for a in ax: a.grid(alpha=.3)
    ax[0].set_title('Table 13 dips, HLK bulk 22 µF (derived), V_off 70 V, 5.5 W load', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'dips_rails.png'), dpi=120); plt.close(fig)
    print(json.dumps(summ, indent=1)); print(res['zcd']); print('first reset', res.get('info_first_reset_0pct_cycles'))


if __name__ == '__main__':
    main()
