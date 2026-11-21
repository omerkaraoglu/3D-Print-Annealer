"""ESD -- EN 55014-2 5.1 Table 1 (PDF p.16): 8 kV air, 4 kV contact, 10 + and 10 - per point, criterion B.

Gun: fitted IEC 61000-4-2 network (validate_generators.py; NRS).  Discharge points (accessible in normal use,
NRS IS 14700-4-2 8.3.1 p.17) are argued in report_section.md; this script simulates:
 E1  contact 4 kV to the thermocouple probe ring (grounded-junction probe, wires 1 m) -> J20 -> PESD5V0S1BA ->
     1 kOhm -> ADS1115 AIN0/1; class-II board floating: SELV ground couples to the reference plane (C_env) and through
     the isolation barrier (C_bar: HLK interwinding + opto + relay + heatsink) to the mains conductors, which reach the
     reference plane through the mains cord (2 uH) and the supply (25 Ohm).  Swept C_env, C_bar.
 E2  contact 4 kV / air 8 kV to the steel oven front sheet around the glass (floating metal, ASM C_sheet 100-300 pF
     to the plane, 5-20 pF to the SELV board): SELV potential and barrier voltage.
 E3  air 8 kV onto the 3 mm front glass over the touch sensor: displacement charge through the glass into an ITO
     electrode -> GT911 pin clamp -> TP_VDD (C126 100 nF + C133 1 nF) -> FPC -> board.  The charge transferred is
     bounded by C_spot * V; C_spot swept 0.5-3 pF.
Run: python -X utf8 sim_esd.py
"""
import itertools, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as cm

TVS = json.load(open(os.path.join(cm.HERE, 'tvs_model.json')))['pts']


def tvs_pwl():
    xs = [-p[0] for p in TVS[::-1] if p[0] > 0] + [0.0] + [p[0] for p in TVS if p[0] > 0]
    ys = [-p[1] for p in TVS[::-1] if p[0] > 0] + [0.0] + [p[1] for p in TVS if p[0] > 0]
    return ', '.join(f'{x:.4g},{y:.4g}' for x, y in zip(xs, ys))


BOARD = """
* SELV board: ground SG, 3V3 rail stiff (bulk decoupling), coupling to the reference plane and across the barrier
V33 V33 SG DC 3.3
Cenv SG 0 {Cenv}
Cbar SG MN {Cbar}
Lmc MN mc 2u
Rmc mc 0 25
"""


def net_tc(V, Cenv, Cbar):
    return f"""esd tc
{cm.esd_gun_subckt('GUN', V)}
X1 PROBE 0 GUN
Ltp PROBE j1 1u
Ltn PROBE j2 1u
Ktc Ltp Ltn 0.95
Rwp j1 J20P 0.5
Rwn j2 J20N 0.5
Ltv1 J20P tv1 2n
Btv1 tv1 SG I = pwl(V(tv1,SG), {tvs_pwl()})
Ctv1 tv1 SG 35p
Ltv2 J20N tv2 2n
Btv2 tv2 SG I = pwl(V(tv2,SG), {tvs_pwl()})
Ctv2 tv2 SG 35p
R220 J20P TCFP 1k
R221 J20N TCFN 1k
C221 TCFP SG 10n
C222 TCFN SG 10n
C220 TCFP TCFN 100n
Lp1 TCFP ain0 3n
Lp2 TCFN ain1 3n
Dh0 ain0 V33 dclamp
Dl0 SG ain0 dclamp
Dh1 ain1 V33 dclamp
Dl1 SG ain1 dclamp
Cin0 ain0 SG 5p
Cin1 ain1 SG 5p
.model dclamp D(Is=1e-14 N=1 Rs=5)
{BOARD.format(Cenv=Cenv, Cbar=Cbar)}
.options reltol=1e-3 method=gear rshunt=1e12
.tran 20p 600n 0 50p uic
.end
"""


def run_tc(V, Cenv, Cbar):
    r = cm.run_netlist(net_tc(V, Cenv, Cbar))
    t = r['time']
    d = lambda a, b: r[f'v({a})'] - r[f'v({b})']
    itv = r['ltv1#branch']; igun = r['ltp#branch'] + r['ltn#branch']
    vain = d('ain0', 'sg')
    # ADS pin current = current through the clamp diodes ~ current in Lp1
    iain = r['lp1#branch']
    p220 = (d('j20p', 'tcfp')) ** 2 / 1e3
    out = {'I_gun_pk_A': float(np.max(np.abs(igun))), 'I_TVS_pk_A': float(np.max(np.abs(itv))),
           'V_J20_pk': float(np.max(np.abs(d('j20p', 'sg')))),
           'V_AIN0_max': float(vain.max()), 'V_AIN0_min': float(vain.min()),
           'I_AIN0_pk_mA': float(np.max(np.abs(iain)) * 1e3),
           'E_R220_uJ': float(np.trapezoid(p220, t) * 1e6), 'P_R220_pk_W': float(p220.max()),
           'V_SG_vs_RGP_pk': float(np.max(np.abs(r['v(sg)']))), 'V_barrier_pk': float(np.max(np.abs(d('sg', 'mn')))),
           'V_barrier_end': float(d('sg', 'mn')[-1]), 'V_SG_end': float(r['v(sg)'][-1])}
    return out, t, {'itv': itv, 'vain': vain, 'vbar': d('sg', 'mn'), 'igun': igun}


def net_sheet(V, Csheet, Cc, Cenv, Cbar):
    return f"""esd sheet
{cm.esd_gun_subckt('GUN', V)}
X1 SHEET 0 GUN
Csh SHEET 0 {Csheet}
Ccp SHEET SG {Cc}
{BOARD.format(Cenv=Cenv, Cbar=Cbar)}
.options reltol=1e-3 method=gear rshunt=1e12
.tran 50p 1u 0 0.1n uic
.end
"""


def net_glass(V, Cspot):
    # ITO electrode -> GT911 clamp to TP_VDD (C126 100 nF + C133 1 nF at J11 via the 40 mm CTP tail, ~25 nH)
    return f"""esd glass
{cm.esd_gun_subckt('GUN', V)}
X1 SPOT 0 GUN
Cspot SPOT ITO {Cspot}
Dto ITO TPV dclamp
Dtg SG ITO dclamp
Cito ITO SG 10p
Ltail TPV tpv2 25n
C133 tpv2 SG 1n IC=3.3
C126 tpv2 SG 100n IC=3.3
Rtpv tpv2 V33 1
.model dclamp D(Is=1e-14 N=1 Rs=5)
{BOARD.format(Cenv='30p', Cbar='100p')}
.options reltol=1e-3 method=gear rshunt=1e12
.tran 20p 200n 0 50p uic
.end
"""


def main():
    res = {'E1_tc_probe_contact_4kV': [], 'E2_sheet': [], 'E3_glass_air_8kV': []}
    wav = None
    for V, Cenv, Cbar in itertools.product((4000.0, -4000.0), (10e-12, 30e-12, 100e-12), (20e-12, 100e-12, 1e-9, 2.2e-9)):
        o, t, w = run_tc(V, Cenv, Cbar)
        res['E1_tc_probe_contact_4kV'].append({'V': V, 'Cenv_pF': Cenv * 1e12, 'Cbar_pF': Cbar * 1e12, **o})
        if V > 0 and Cenv == 30e-12 and Cbar == 100e-12: wav = (t, w)
        print('E1', V, Cenv, Cbar, {k: round(v, 2) for k, v in o.items()})
    for V, Csheet, Cc, Cbar in itertools.product((4000.0, 8000.0), (100e-12, 300e-12), (5e-12, 20e-12), (20e-12, 100e-12, 1e-9)):
        r = cm.run_netlist(net_sheet(V, Csheet, Cc, 30e-12, Cbar))
        vb = r['v(sg)'] - r['v(mn)']
        res['E2_sheet'].append({'V': V, 'Csheet_pF': Csheet * 1e12, 'Cc_pF': Cc * 1e12, 'Cbar_pF': Cbar * 1e12,
                                'V_sheet_pk': float(np.max(np.abs(r['v(sheet)']))), 'V_barrier_pk': float(np.max(np.abs(vb))),
                                'V_SG_pk': float(np.max(np.abs(r['v(sg)'])))})
    for Cspot in (0.5e-12, 1e-12, 2e-12, 3e-12):
        r = cm.run_netlist(net_glass(8000.0, Cspot))
        t = r['time']; i = r['ltail#branch']
        q = float(np.trapezoid(np.abs(r['v(spot)'] - r['v(ito)']) * 0 + np.abs(np.gradient(r['v(spot)'] - r['v(ito)'], t)) * Cspot, t))
        res['E3_glass_air_8kV'].append({'Cspot_pF': Cspot * 1e12, 'I_clamp_pk_A': float(np.max(np.abs(i))),
                                        'V_ITO_vs_SG_pk': float(np.max(np.abs(r['v(ito)'] - r['v(sg)']))),
                                        'Q_transferred_nC': float(Cspot * 8000 * 1e9),
                                        'dV_TPVDD_mV': float(np.max(np.abs(r['v(tpv2)'] - r['v(sg)'] - 3.3)) * 1e3)})
    # stack comparison with the CTP maker's +-8 kV air rating on its own 0.7 mm cover lens (DS p.23):
    # coupling capacitance per area ~ 1/sum(d_i/eps_i): CTP alone 0.7 mm glass (eps 7); ours + 3 mm glass + 0.3 mm LOCA (eps 3)
    k_ctp = 1 / (0.7 / 7); k_ours = 1 / ((0.7 + 3.0) / 7 + 0.3 / 3)
    res['E3_stack_ratio'] = {'C_per_area_ratio_ours_over_ctp': k_ours / k_ctp,
                             'note': 'same surface charge density couples ~1/{:.1f} of the charge into the ITO compared with the module maker\'s own +-8 kV air test'.format(k_ctp / k_ours)}
    E1 = res['E1_tc_probe_contact_4kV']
    res['E1_worst'] = {k: max(E1, key=lambda d: abs(d[k]))[k] for k in ('I_TVS_pk_A', 'V_J20_pk', 'V_AIN0_max', 'I_AIN0_pk_mA', 'E_R220_uJ', 'P_R220_pk_W', 'V_barrier_pk', 'V_SG_vs_RGP_pk')}
    res['E1_worst']['V_AIN0_min'] = min(d['V_AIN0_min'] for d in E1)
    res['E1_worst']['V_barrier_end_max'] = max(abs(d['V_barrier_end']) for d in E1)
    res['E2_worst'] = max(res['E2_sheet'], key=lambda d: d['V_barrier_pk'])
    # barrier ratings (DS) and PCB clearance impulse withstand (IEC 60664-1 Table F.2 inhomogeneous field, NRS from memory)
    res['barrier_ratings_Vpk'] = {'HLK-10M05 2500 Vac (DS p.11, the lower of 2500/3000)': 2500 * np.sqrt(2),
                                  'H11AA1 5000 Vrms (Vishay p.1)': 5000 * np.sqrt(2), 'MOC3052 VIOTM 6000 Vpk (onsemi p.2)': 6000,
                                  'HJR-3FF coil-contact 1500 Vac (Tianbo p.2)': 1500 * np.sqrt(2),
                                  'K1.1 (LINE_FUSED) to coil pads 3.52 mm air (spec 12.8): ~4 kV impulse at 3 mm (IEC 60664-1 F.2, NRS)': 4000.0,
                                  'mains-SELV 6.4 mm (spec 12.2): ~7 kV impulse (NRS)': 7000.0}
    cm.save_results('esd', res)
    if wav:
        t, w = wav
        fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
        ax[0].plot(t * 1e9, w['igun'], label='probe current'); ax[0].plot(t * 1e9, w['itv'], label='D220 TVS current')
        ax[0].axhline(12, c='r', ls=':', label='IPPM 12 A (8/20 µs)'); ax[0].set_ylabel('A'); ax[0].legend(fontsize=7)
        ax[1].plot(t * 1e9, w['vain'], label='ADS1115 AIN0 vs GND'); ax[1].axhline(3.6, c='r', ls=':', label='VDD + 0.3 = 3.6 V')
        ax[1].axhline(-0.3, c='r', ls=':', label='GND − 0.3 V'); ax[1].set_ylabel('V'); ax[1].legend(fontsize=7)
        ax[2].plot(t * 1e9, w['vbar'], label='SELV GND vs mains conductors (barrier)'); ax[2].set_ylabel('V'); ax[2].legend(fontsize=7)
        ax[2].set_xlabel('t (ns)')
        for a in ax: a.grid(alpha=.3)
        ax[0].set_title('ESD +4 kV contact on the thermocouple probe, C_env 30 pF, C_bar 100 pF (ASM)', fontsize=9)
        fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'esd_tc_probe.png'), dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    for Cenv, mk in ((10e-12, 'o'), (30e-12, 's'), (100e-12, '^')):
        rr = [d for d in E1 if d['V'] > 0 and d['Cenv_pF'] == Cenv * 1e12]
        ax.semilogx([d['Cbar_pF'] for d in rr], [d['V_barrier_pk'] for d in rr], mk + '-', label=f'E1 probe 4 kV, C_env {Cenv*1e12:.0f} pF')
    rr = [d for d in res['E2_sheet'] if d['V'] == 8000 and d['Csheet_pF'] == 100 and d['Cc_pF'] == 20]
    ax.semilogx([d['Cbar_pF'] for d in rr], [d['V_barrier_pk'] for d in rr], 'kd--', label='E2 sheet 8 kV, C_c 20 pF')
    ax.axhline(1500 * np.sqrt(2), c='r', ls=':', label='relay coil–contact 1500 Vac = 2.1 kVpk')
    ax.axhline(2500 * np.sqrt(2), c='m', ls=':', label='HLK 2500 Vac = 3.5 kVpk')
    ax.set_xlabel('barrier capacitance SELV↔mains (pF, ASM)'); ax.set_ylabel('peak barrier voltage (V)'); ax.grid(alpha=.3, which='both'); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'esd_barrier.png'), dpi=120); plt.close(fig)
    print(json.dumps({k: v for k, v in res.items() if k.endswith('worst') or k == 'E3_glass_air_8kV' or k == 'E3_stack_ratio'}, indent=1, default=float))


def cbar_sweep():
    """Barrier voltage vs C_bar (HLK primary-secondary + opto + relay + heatsink), so an LCR reading of the
    HLK +Vout <-> AC capacitance converts directly into a verdict.  4 kV contact on the TC probe, both polarities."""
    cb = np.logspace(np.log10(20e-12), np.log10(2.2e-9), 15)
    limits = {'relay coil-contact 1500 Vac = 2121 Vpk': 1500 * np.sqrt(2), 'HLK 2500 Vac = 3536 Vpk': 2500 * np.sqrt(2)}
    out = {'Cbar_pF': list(cb * 1e12), 'curves': {}, 'crossing_Cbar_pF': {}}
    for Cenv in (10e-12, 30e-12, 100e-12):
        vpk = []
        for c in cb:
            o, *_ = run_tc(4000.0, Cenv, c)
            o2, *_ = run_tc(-4000.0, Cenv, c)
            vpk.append(max(abs(o['V_barrier_pk']), abs(o2['V_barrier_pk'])))
        out['curves'][f'Cenv {Cenv*1e12:.0f} pF'] = vpk
        for name, lim in limits.items():
            v = np.array(vpk)
            if v[-1] > lim:
                x = None
            elif v[0] < lim:
                x = 0.0
            else:
                i = np.where(v < lim)[0][0]
                x = float(10 ** np.interp(np.log10(lim), np.log10(v[[i, i - 1]]), np.log10(cb[[i, i - 1]] * 1e12)))
            out['crossing_Cbar_pF'][f'Cenv {Cenv*1e12:.0f} pF | {name}'] = x
            # with the 20 % margin rule: C_bar for barrier <= 0.8 * limit
            v8 = 0.8 * lim
            if v[0] < v8:
                x8 = 0.0
            elif v[-1] > v8:
                x8 = None
            else:
                i = np.where(v < v8)[0][0]
                x8 = float(10 ** np.interp(np.log10(v8), np.log10(v[[i, i - 1]]), np.log10(cb[[i, i - 1]] * 1e12)))
            out['crossing_Cbar_pF'][f'Cenv {Cenv*1e12:.0f} pF | {name} | for PASS (>= 20 % margin)'] = x8
        print(Cenv, [round(x) for x in vpk])
    print(json.dumps(out['crossing_Cbar_pF'], indent=1))
    cm.save_results('esd_barrier_vs_Cbar', out)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for k, v in out['curves'].items():
        ax.loglog(cb * 1e12, v, 'o-', ms=3, label=f'E1 4 kV contact on TC probe, {k}')
    for name, lim in limits.items():
        ax.axhline(lim, ls=':', c='r' if 'relay' in name else 'm', label=name)
        ax.axhline(0.8 * lim, ls='--', lw=0.7, c='r' if 'relay' in name else 'm')
    ax.set_xlabel('C_bar, SELV GND <-> mains (pF): measure HLK +Vout <-> AC/L+N with an LCR meter, + ~5 pF for optos/relay/heatsink')
    ax.set_ylabel('peak barrier voltage (V)'); ax.grid(alpha=.3, which='both'); ax.legend(fontsize=7)
    ax.set_title('ESD E1: barrier voltage vs barrier capacitance (dashed = 80 % of rating)', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'esd_barrier_vs_Cbar.png'), dpi=120); plt.close(fig)


if __name__ == '__main__':
    import sys
    if '--cbar' in sys.argv:
        cbar_sweep()
    else:
        main()
