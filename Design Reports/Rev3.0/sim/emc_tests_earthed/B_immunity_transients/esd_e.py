"""ESD with an earthed chassis -- EN 55014-2 5.1 Table 1 (PDF p.16): 4 kV contact to the earthed metal (probe ring
bolted to the chassis, steel front sheet), 8 kV air (painted sheet; upper bound with the contact network), criterion B.
Gun: fitted network of the committed scope-B folder (NOT READ from the standard).  The discharge lands on the chassis
(CH), which is on PE: PE cord 2 uH + 1 Ohm to the reference (ASM), chassis 150 pF to the plane (ASM), chassis-to-mains
coupling 300 pF (heater, fan, wiring; ASM).  Mains L/N reach the plane through the cord (2 uH) and the supply (25 Ohm).
SELV: C_bar to mains, C_sp to chassis; thermocouple grounded (1 uH wires from CH to J20) or insulated (100 pF);
optional SELV-PE bond (fix F2).
Run: python -X utf8 esd_e.py
"""
import itertools, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common_e as ce

cm = ce.cm
_TVS = json.load(open(os.path.join(ce.OLD, 'tvs_model.json')))['pts']
TVSPWL = ', '.join(f'{x:.4g},{y:.4g}' for x, y in zip(
    [-p[0] for p in _TVS[::-1] if p[0] > 0] + [0.0] + [p[0] for p in _TVS if p[0] > 0],
    [-p[1] for p in _TVS[::-1] if p[0] > 0] + [0.0] + [p[1] for p in _TVS if p[0] > 0]))
GP = cm.ESD_PARS


def netlist(V, tc, bond, Cbar, Csp, Cch=150e-12):
    gun = f"""
.subckt GUNE tip ret
Cm m1 ret {GP['Cm']:.4g} IC={V}
Rm m1 m2 {GP['Rm']:.4g}
Lm m2 tip {GP['Lm']:.4g}
Cs s1 ret {GP['Cs']:.4g} IC={V}
Rs s1 s2 {GP['Rs']:.4g}
Ls s2 tip {GP['Ls']:.4g}
.ends
"""
    tcw = ('Ltp CH TJ1 1u\nLtn CH TJ2 1u\nKtc Ltp Ltn 0.95' if tc == 'grounded'
           else 'Ltp TCW TJ1 1u\nLtn TCW TJ2 1u\nKtc Ltp Ltn 0.95\nCts TCW CH 100p')
    bd = 'Lbd SG BBD 0.5u\nRbd BBD CH 0.05' if bond else ''
    return f"""esd earthed
{gun}
X1 CH 0 GUNE
Cch CH 0 {Cch}
Lpe CH PEX 2u
Rpe PEX 0 1
Ccm CH MN 300p
Lmc MN MC 2u
Rmc MC 0 25
V33 V33 SG DC 3.3
Cbar SG MN {Cbar}
Csp SG CH {Csp}
Cenv SG 0 10p
{bd}
{tcw}
Rwp TJ1 J20P 0.5
Rwn TJ2 J20N 0.5
Ltv1 J20P TV1 2n
Btv1 TV1 SG I = pwl(V(TV1,SG), {TVSPWL})
Ctv1 TV1 SG 35p
Ltv2 J20N TV2 2n
Btv2 TV2 SG I = pwl(V(TV2,SG), {TVSPWL})
Ctv2 TV2 SG 35p
R220 J20P TCFP 1k
R221 J20N TCFN 1k
C221 TCFP SG 10n
C222 TCFN SG 10n
C220 TCFP TCFN 100n
Lp1 TCFP AIN0 3n
Lp2 TCFN AIN1 3n
Dh0 AIN0 V33 dclamp
Dl0 SG AIN0 dclamp
Dh1 AIN1 V33 dclamp
Dl1 SG AIN1 dclamp
Cin0 AIN0 SG 5p
Cin1 AIN1 SG 5p
.model dclamp D(Is=1e-14 N=1 Rs=5)
.options reltol=1e-3 method=gear rshunt=1e12
.tran 20p 1u 0 50p uic
.end
"""


def run(**kw):
    r = ce.run(netlist(**kw)); t = r['time']
    d = lambda a, b: r[f'v({a.lower()})'] - r[f'v({b.lower()})']
    pk = lambda x: float(np.max(np.abs(x)))
    vain = d('AIN0', 'SG')
    return {'V_chassis_pk': pk(r['v(ch)']), 'V_barrier_pk': pk(d('SG', 'MN')), 'V_barrier_end': float(d('SG', 'MN')[-1]),
            'V_SELV_chassis_pk': pk(d('SG', 'CH')), 'I_TVS_pk': max(pk(r['ltv1#branch']), pk(r['ltv2#branch'])),
            'V_J20_pk': pk(d('J20P', 'SG')), 'V_AIN_min': float(vain.min()), 'V_AIN_max': float(vain.max()),
            'I_AIN_pk_mA': max(pk(r['lp1#branch']), pk(r['lp2#branch'])) * 1e3,
            'E_R220_uJ': float(np.trapezoid(d('J20P', 'TCFP') ** 2 / 1e3, t) * 1e6),
            'V_probe_ins_pk': pk(d('TCW', 'CH')) if 'v(tcw)' in r else 0.0}, t, r


def main():
    rows = []
    for V, tc, bond, Cbar, Csp in itertools.product((4000.0, -4000.0, 8000.0), ('grounded', 'insulated'), (False, True),
                                                    (20e-12, 100e-12, 1e-9, 2.2e-9), (10e-12, 50e-12, 200e-12)):
        o, *_ = run(V=V, tc=tc, bond=bond, Cbar=Cbar, Csp=Csp)
        rows.append({'V': V, 'tc': tc, 'bond': bond, 'Cbar_pF': Cbar * 1e12, 'Csp_pF': Csp * 1e12, **o})
    summ = {}
    for tc, bond in itertools.product(('grounded', 'insulated'), (False, True)):
        for lvl in ('4 kV contact', '8 kV air (bound)'):
            rr = [r for r in rows if r['tc'] == tc and r['bond'] == bond and ((abs(r['V']) == 4000) == (lvl.startswith('4')))]
            summ[f'{tc}|bond={bond}|{lvl}'] = {k: (max(abs(r[k]) for r in rr)) for k in
                                               ('V_chassis_pk', 'V_barrier_pk', 'V_SELV_chassis_pk', 'I_TVS_pk', 'V_J20_pk', 'I_AIN_pk_mA', 'E_R220_uJ', 'V_probe_ins_pk')}
            summ[f'{tc}|bond={bond}|{lvl}']['V_AIN_min'] = min(r['V_AIN_min'] for r in rr)
            summ[f'{tc}|bond={bond}|{lvl}']['V_AIN_max'] = max(r['V_AIN_max'] for r in rr)
    ce.save('esd_earthed', {'rows': rows, 'summary': summ})
    for k, v in summ.items():
        print(k, {kk: round(vv, 3) for kk, vv in v.items()})
    # waveform plot
    fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    for tc in ('grounded', 'insulated'):
        o, t, r = run(V=4000.0, tc=tc, bond=False, Cbar=100e-12, Csp=50e-12)
        ax[0].plot(t * 1e9, r['v(sg)'] - r['v(mn)'], label=f'barrier SELV–mains, TC {tc}')
        ax[1].plot(t * 1e9, r['v(ain0)'] - r['v(sg)'], label=f'ADS1115 AIN0, TC {tc}')
    ax[0].plot(t * 1e9, r['v(ch)'], 'k--', lw=0.8, label='chassis vs reference')
    ax[0].axhline(1500 * np.sqrt(2), c='r', ls=':', label='K1 coil–contact 2121 Vpk')
    ax[1].axhline(-0.3, c='r', ls=':'); ax[1].axhline(3.6, c='r', ls=':', label='AIN GND−0.3 / VDD+0.3')
    for a in ax: a.grid(alpha=.3); a.legend(fontsize=7)
    ax[0].set_ylabel('V'); ax[1].set_ylabel('V'); ax[1].set_xlabel('t (ns)')
    ax[0].set_title('ESD 4 kV contact to the earthed chassis / probe ring, C_bar 100 pF, C_SELV-PE 50 pF (ASM)', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(ce.PLOTS, 'esd_earthed.png'), dpi=120); plt.close(fig)


if __name__ == '__main__':
    main()
