"""EFT/burst 1 kV with an earthed chassis -- EN 55014-2 5.2 Table 4 (PDF p.16-17), criterion B.
Coupling NOT READ from the standard: IS 14700-4-4:2008 (= IEC 61000-4-4:2004) 3.4 p.8 "common mode: simultaneous
coupling to all lines versus the ground reference plane", Table 1 p.10 "on power port, PE"; 33 nF per line (6.2.1 p.13).
Model: committed sim_eft.py netlist (imported read-only) + PE line pulsed through 33 nF together with L and N, PE cord
1 uH to the chassis, PE decoupled 1.5 mH to the supply earth; design state of common_e.py (1 nF on the ZCD node, TVS
1.5KE440CA 180 pF across Q1, RV3 370 pF at LINE_FUSED, 800 V driver ~1 pF I/O); thermocouple grounded (wires on the
chassis) or insulated (100 pF wire-to-sheath), optional SELV-PE bond (fix F2).
Run: python -X utf8 eft_e.py
"""
import itertools, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common_e as ce
import sim_eft as se          # committed scope-B EFT model (read-only)


def netlist(pol, Chlk, Csc, Ccg, q_on, tc, bond, Cio=0.5e-12):
    n = se.netlist(pol=pol, Chlk=Chlk, Csc=Csc, Ccg=Ccg, q_on=q_on, tc_on_chassis=(tc == 'grounded'), Cio_zcd=Cio, Czc=1e-9)
    n = n.replace('Crv2 LFI A1 120p', 'Crv2 LFI A1 180p')
    n = n.replace('Ctcx CHSX CHS 10p', 'Ctcx CHSX CHS 100p')
    add = ['Crv3 LF NEUT 370p',
           'Ccpe g2 PEC 33n', 'Lcpe PEC CHS 1u', 'Ccpeg PEC 0 30p', 'Rdpe PEC 0 1k']   # PE decoupling: 1.5 mH is open at ns; 1 kOhm (convergence)
    if bond:
        add += ['Lbd SG BBD 0.5u', 'Rbd BBD CHS 0.05']
    return n.replace('.options', '\n'.join(add) + '\n.options', 1)


def run(**kw):
    net = netlist(**kw)
    for variant in (net, net.replace('method=gear', 'method=trap'), net.replace('.tran 0.1n 3u 0 0.1n', '.tran 0.05n 3u 0 0.02n')):
        try:
            r = ce.run(variant); break
        except ValueError:
            raise
        except Exception:
            continue
    else:
        raise RuntimeError('ngspice failed')
    t = r['time']
    d = lambda a, b: r[f'v({a})'] - r[f'v({b})']
    vzc = d('zc', 'sg'); vT = d('lfi', 'a1')
    i_led = (r['v(sg)'] - r['v(led)']) / 120.0
    vtc = d('tcfp', 'tcfn')
    o = {'V_ZC_min': float(vzc.min()), 'V_ZC_max': float(vzc.max()), 'V_ZC_idle': float(vzc[0]),
         'V_triac_pk': float(np.max(np.abs(vT - vT[0]))), 'V_GA1_pk': float(np.max(np.abs(d('g', 'a1')))),
         'V_EN_dev_mV': float(np.max(np.abs(d('en', 'sg') - 3.3)) * 1e3),
         'V_TCFP_min': float(d('tcfp', 'sg').min()), 'V_TCFP_max': float(d('tcfp', 'sg').max()),
         'V_J20_pk': float(np.max(np.abs(d('j20p', 'sg')))),
         'TC_diff_area_uVs': float(np.trapezoid(vtc, t) * 1e6), 'V_TC_diff_pk_uV': float(np.max(np.abs(vtc)) * 1e6),
         'I_LED_pk_mA': float(np.max(np.abs(i_led)) * 1e3),
         'V_SELV_vs_RGP': float(np.max(np.abs(r['v(sg)']))), 'V_SELV_vs_chassis': float(np.max(np.abs(d('sg', 'chs')))),
         'V_K1_coil_contact': float(np.max(np.abs(d('lf', 'sg')))), 'V_HLK_barrier': float(np.max(np.abs(d('hp', 'sg'))))}
    return o


def main():
    rows = []
    for tc, bond, Chlk, (Csc, Ccg), q_on, pol in itertools.product(('grounded', 'insulated'), (False, True), (20e-12, 100e-12, 1e-9),
                                                                  ((20e-12, 50e-12), (50e-12, 150e-12)), (False, True), (+1, -1)):
        o = run(pol=pol, Chlk=Chlk, Csc=Csc, Ccg=Ccg, q_on=q_on, tc=tc, bond=bond)
        rows.append({'tc': tc, 'bond': bond, 'Chlk_pF': Chlk * 1e12, 'Csc_pF': Csc * 1e12, 'Ccg_pF': Ccg * 1e12,
                     'transistor': 'on' if q_on else 'off', 'pol': pol, **o})
    VTp, VTm = 1.5, 1.14
    def worst(filt):
        rr = [r for r in rows if filt(r)]
        return {'n': len(rr),
                'ZC_off_min': min(r['V_ZC_min'] for r in rr if r['transistor'] == 'off'),
                'ZC_on_max': max(r['V_ZC_max'] for r in rr if r['transistor'] == 'on'),
                'ZC_abs_max': max(r['V_ZC_max'] for r in rr),
                'false_edges': sum(1 for r in rr if (r['transistor'] == 'off' and r['V_ZC_min'] < VTm) or (r['transistor'] == 'on' and r['V_ZC_max'] > VTp)),
                'GA1_max': max(r['V_GA1_pk'] for r in rr), 'triac_max': max(r['V_triac_pk'] for r in rr),
                'EN_max_mV': max(r['V_EN_dev_mV'] for r in rr),
                'TCFP_min': min(r['V_TCFP_min'] for r in rr), 'TCFP_max': max(r['V_TCFP_max'] for r in rr),
                'J20_max': max(r['V_J20_pk'] for r in rr),
                'TC_err_degC_worst_conversion': max(abs(r['TC_diff_area_uVs']) for r in rr) * 75 / 62.5e-3 / 41.0,
                'K1_coil_contact_max': max(r['V_K1_coil_contact'] for r in rr), 'HLK_barrier_max': max(r['V_HLK_barrier'] for r in rr),
                'LED_max_mA': max(r['I_LED_pk_mA'] for r in rr)}
    summ = {f'{tc}|bond={b}': worst(lambda r, tc=tc, b=b: r['tc'] == tc and r['bond'] == b) for tc in ('grounded', 'insulated') for b in (False, True)}
    ce.save('eft_earthed', {'rows': rows, 'summary': summ, 'thresholds': {'VT+min': VTp, 'VT-max': VTm}})
    for k, v in summ.items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})


if __name__ == '__main__':
    main()
