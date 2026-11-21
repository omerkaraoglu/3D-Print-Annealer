"""Item 3 (review 2026-11-21): F2 single-point SELV-PE bond together with the decided panel bond.

Panel model (ASSUMED): LCM metal frame PF bonded to PCB ground through the bare landing pads on the PCB back
(10 nH + 5 mOhm), and also tied to PCB ground through the FPC ground conductors: J10 TFT tail (3 GND pins, ~68 mm:
15 nH + 50 mOhm in parallel) and J11 CTP tail (1 GND pin, ~40 mm: 30 nH + 0.1 Ohm).  Frame-to-earthed-sheet
capacitance C_fs 50 / 200 pF.  Bond wire SELV GND -> chassis stud 50 / 150 / 500 nH.
Blocks:  python -X utf8 panel_e.py static | surge | esd
"""
import itertools, sys
import numpy as np
import common_e as ce
import surge_e as s
import esd_e as e

PANEL = ('Cfs PF CH {Cfs}\nLpad PF PFA 10n\nRpad PFA SG 5m\nLfpc PF PFB 15n\nRfpc PFB SG 50m\n'
         'Lctp PF PFC 30n\nRctp PFC SG 0.1\n')
TC_BIAS = 'R222 V33 J20P 10Meg\nR223 J20N SG 10Meg\n'


def with_tc_emf(net):
    # K-type at ~420 C over a 25 C cold junction: ~16.4 mV; split ~ +8.6 mV (chromel leg) / -7.8 mV (alumel leg) ASSUMED
    net = net.replace('Rwp TJ1 J20P 0.5', 'Rwp TJ1 TE1 0.5\nVep J20P TE1 DC 0.0086')
    net = net.replace('Rwn TJ2 J20N 0.5', 'Rwn TJ2 TE2 0.5\nVen J20N TE2 DC -0.0078')
    return net


def static():
    out = {}
    for tc, bond in itertools.product(('grounded', 'insulated'), (None, 150e-9)):
        net, ts = s.netlist(mode='LPE', pol=1, tc=tc, t_after=20e-3, Cbar=1e-9, bond=bond is not None)
        net = net.replace(f"{ts - 20e-6:.6g} 2e-07 uic", "0.005 2e-07 uic")
        net = net.replace("Vctl ctl 0 PWL(0 0 {ts} 0 {ts+1n} 1)", "Vctl ctl 0 DC 0")
        net = net.replace('Lbond SG BB 0.5u', f'Lbond SG BB {bond}')
        net = with_tc_emf(net).replace('.options', TC_BIAS + PANEL.format(Cfs='100p') + '.options', 1)
        r = ce.run(net); t = r['time']; w = t > 0.02
        a0 = (r['v(ain0)'] - r['v(sg)'])[w]; a1 = (r['v(ain1)'] - r['v(sg)'])[w]
        d = a0 - a1
        key = f"{tc}|bond={'none' if bond is None else '150nH'}"
        out[key] = {'AIN0_min': float(a0.min()), 'AIN0_max': float(a0.max()), 'AIN0_mean': float(a0.mean()),
                    'AIN1_min': float(a1.min()), 'AIN1_max': float(a1.max()), 'AIN1_mean': float(a1.mean()),
                    'diff_mean_mV': float(d.mean() * 1e3), 'diff_pp_uV': float((d.max() - d.min()) * 1e6),
                    'SELV_chassis_pk_V': float(np.max(np.abs((r['v(sg)'] - r['v(ch)'])[w])))}
        print(key, {k: round(v, 4) for k, v in out[key].items()}, flush=True)
    ce.save('panel_static_50Hz_tc', out)


def surge():
    rows = []
    for Lb, Cfs, mode in itertools.product((50e-9, 150e-9, 500e-9), (50e-12, 200e-12), ('LPE', 'NPE')):
        net, ts = s.netlist(mode=mode, pol=1, heater=False, relay_closed=False, tc='grounded', Cbar=1e-9, bond=True, tmax=200e-9)
        net = net.replace('Lbond SG BB 0.5u', f'Lbond SG BB {Lb}')
        net = net.replace('.options', 'Cfan2 FANH NEUT 47n\n' + PANEL.format(Cfs=Cfs) + '.options', 1)
        try:
            r = ce.run(net)
        except Exception:
            try:
                r = ce.run(net.replace('method=gear', 'method=trap'))
            except Exception:
                rows.append({'Lb_nH': Lb * 1e9, 'Cfs_pF': Cfs * 1e12, 'mode': mode, 'failed': True}); continue
        w = r['time'] >= ts - 5e-6
        pk = lambda n: float(np.max(np.abs(r[f'{n}#branch'][w])))
        o = {'Lb_nH': Lb * 1e9, 'Cfs_pF': Cfs * 1e12, 'mode': mode, 'I_bond_pk': pk('lbond'), 'I_pads_pk': pk('lpad'),
             'I_fpc_tft_pk': pk('lfpc'), 'I_fpc_ctp_pk': pk('lctp'),
             'V_frame_vs_SELV_pk': float(np.max(np.abs((r['v(pf)'] - r['v(sg)'])[w]))),
             'V_SELV_vs_chassis_pk': float(np.max(np.abs((r['v(sg)'] - r['v(ch)'])[w]))),
             'V_K1_coil_contact': float(np.max(np.abs((r['v(lf)'] - r['v(sg)'])[w]))),
             'V_HLK_barrier': float(np.max(np.abs((r['v(hp)'] - r['v(sg)'])[w])))}
        rows.append(o); print({k: round(v, 3) if isinstance(v, float) else v for k, v in o.items()}, flush=True)
    ce.save('panel_surge', rows)


def esd():
    rows = []
    for V, Lb, Cfs, tc in itertools.product((4000.0, 8000.0), (50e-9, 150e-9, 500e-9), (50e-12, 200e-12), ('grounded', 'insulated')):
        net = e.netlist(V=V, tc=tc, bond=True, Cbar=1e-9, Csp=50e-12)
        net = net.replace('Lbd SG BBD 0.5u', f'Lbd SG BBD {Lb}')
        net = net.replace('.options', PANEL.format(Cfs=Cfs) + '.options', 1)
        r = ce.run(net); t = r['time']
        pk = lambda n: float(np.max(np.abs(r[f'{n}#branch'])))
        q = lambda n: float(np.trapezoid(np.abs(r[f'{n}#branch']), t) * 1e9)
        o = {'V': V, 'Lb_nH': Lb * 1e9, 'Cfs_pF': Cfs * 1e12, 'tc': tc,
             'I_bond_pk': pk('lbd'), 'I_pads_pk': pk('lpad'), 'I_fpc_tft_pk': pk('lfpc'), 'I_fpc_ctp_pk': pk('lctp'),
             'Q_fpc_tft_nC': q('lfpc'), 'Q_fpc_ctp_nC': q('lctp'),
             'V_frame_vs_SELV_pk': float(np.max(np.abs(r['v(pf)'] - r['v(sg)']))),
             'V_SELV_vs_chassis_pk': float(np.max(np.abs(r['v(sg)'] - r['v(ch)']))),
             'V_barrier_pk': float(np.max(np.abs(r['v(sg)'] - r['v(mn)']))),
             'V_AIN_min': float((r['v(ain0)'] - r['v(sg)']).min()), 'I_TVS_pk': pk('ltv1')}
        rows.append(o); print({k: round(v, 3) if isinstance(v, float) else v for k, v in o.items()}, flush=True)
    ce.save('panel_esd', rows)


if __name__ == '__main__':
    {'static': static, 'surge': surge, 'esd': esd}[sys.argv[1]]()
