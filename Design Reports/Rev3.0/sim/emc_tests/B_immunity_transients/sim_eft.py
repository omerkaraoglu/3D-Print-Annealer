"""EFT/burst 1 kV common mode on the a.c. mains port -- EN 55014-2 5.2 Table 4 (PDF p.16-17), criterion B.

Generator (NRS, validated in validate_generators.py): 1 kV open-circuit 5/50 ns pulse, 50 Ohm source, 10 nF
blocking capacitor, CDN 33 nF to L and to N together (common mode), burst 15 ms at 5 kHz every 300 ms.
The EUT stands on an insulating support over the reference ground plane (RGP).  All stray / barrier
capacitances are ASSUMED and swept (see PARS); the circuit is linear except the TVS diodes.

One pulse is simulated (pulses are 200 us apart, every node of interest settles within a few us, so the
burst response is the single-pulse response repeated; slow nodes are integrated over the burst analytically).
Run: python -X utf8 sim_eft.py
"""
import itertools, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as cm

EFT = json.load(open(os.path.join(cm.HERE, 'eft_fit.json')))
TVS = json.load(open(os.path.join(cm.HERE, 'tvs_model.json')))['pts']


def tvs_pwl():
    xs = [-p[0] for p in TVS[::-1] if p[0] > 0] + [0.0] + [p[0] for p in TVS if p[0] > 0]
    ys = [-p[1] for p in TVS[::-1] if p[0] > 0] + [0.0] + [p[1] for p in TVS if p[0] > 0]
    return ', '.join(f'{x:.4g},{y:.4g}' for x, y in zip(xs, ys))


def pulse_pwl(V=1000.0, pol=+1, t0=5e-9, tend=600e-9, n=300):
    t = np.linspace(0, tend, n)
    v = (1 - np.exp(-t / EFT['a'])) ** 4 * np.exp(-t / EFT['b'])
    v = v / v.max() * V * pol
    return ' '.join(f'{ti + t0:.4g} {vi:.4g}' for ti, vi in zip(t, v))


def netlist(pol=+1, Chlk=100e-12, Csc=20e-12, Ccg=50e-12, Csg=10e-12, Cj=100e-12, q_on=False, tc_on_chassis=True,
            Vinst=0.0, Cio_zcd=0.5e-12, Cio_moc=1e-12, triac_driver_C=1e-12, Czc=8e-12):
    rq = '200' if q_on else '1G'
    tc = ("Ltp CHS J20P 1u\nLtn CHS J20N 1u\nKtc Ltp Ltn 0.95" if tc_on_chassis
          else "Ltp CHSX J20P 1u\nLtn CHSX J20N 1u\nKtc Ltp Ltn 0.95\nCtcx CHSX CHS 10p\nRtcx CHSX CHS 1G")
    return f"""eft
Vg g0 0 PWL(0 0 {pulse_pwl(pol=pol)})
Rg g0 g1 50
Cbk g1 g2 10n
Ccl g2 LT 33n
Ccn g2 NT 33n
* decoupling side of the CDN (ASM: 1.5 mH + 1 uF to RGP per line) and the instantaneous mains voltage
Ldl LT mL 1.5m
Ldn NT mN 1.5m
Vm mL mN DC {Vinst}
Cdl mL 0 1u
Cdn mN 0 1u
* 1 m mains cord (ASM): 1 uH per conductor, k = 0.9, 30 pF per conductor to RGP
Lcl LT J3L 1u
Lcn NT NEUT 1u
Kc Lcl Lcn 0.9
Ccgl J3L 0 30p
Ccgn NEUT 0 30p
* mains side of the EUT (MOVs non-conducting at these levels -> capacitances)
Rf3 J3L LF 10m
Ck1 LF FANH 1.5p
Cfan FANH NEUT 200p
Rfan FANH NEUT 2k
Cfanc FANH CHS 50p
L40 LF LX 100u
RL40 LX LFI 0.1
CL40 LF LFI 10p
RL40p LF LFI 5k
C40 LFI c40a 1u
Lc40 c40a NEUT 20n
C1 LFI c1a 100n
Lc1 c1a NEUT 15n
Crv1 LFI NEUT 370p
Cq LFI A1 {Cj}
Rq LFI A1 10Meg
Crv2 LFI A1 120p
R5 LFI sn 47
C4 sn A1 10n
R3 LFI moc6 360
Cmoc moc6 G {triac_driver_C}
R2 G A1 360
Cga1 G A1 200p
Lh A1 hx 2u
Rh hx NEUT 52.9
Chc1 A1 CHS 50p
Chc2 NEUT CHS 50p
* heatsink HS1 (floating): 15 pF to the A2 tab, 3 pF to RGP, 1 pF to SELV
Chs1 LFI HS 15p
Chs2 HS 0 3p
Chs3 HS SG 1p
* PSU branch: F1, CMC L1 (10 mH CM, k 0.99, 15 pF winding capacitance, 2 kOhm loss), HLK primary
Rf1 LFI PL 0.15
Lca PL ALx 10m
Lcb NEUT ANx 10m
Kcm Lca Lcb 0.99
Ccwa PL ALx 15p
Ccwb NEUT ANx 15p
Rcwa PL ALx 2k
Rcwb NEUT ANx 2k
Cxh ALx ANx 1n
Cpa ALx HP 10n
Cpb ANx HP 10n
Chlk HP SG {Chlk}
Chg HP 0 2p
* ZCD: R6/R7 33k, H11AA1 LEDs (20 pF), opto I/O capacitance split collector / emitter
R6 ALx zl 33k
Cr6 ALx zl 0.3p
R7 zn ANx 33k
Cr7 zn ANx 0.3p
Czled zl zn 20p
Cio1 zl ZC {Cio_zcd/2}
Cio2 zn SG {Cio_zcd/2}
R8 V33 ZC 10k
Czc ZC SG {Czc}
Rq1 ZC SG {rq}
* MOC3052 LED side: IO33 driven low (0 V) through R4 120R, LED to SG; opto I/O capacitance to the triac side
R4 SG led 120
Dled led SG dled
Cled led SG 20p
Cmio moc6 led {Cio_moc}
.model dled D(Is=1e-19 N=1.6 Rs=2 Cjo=20p)
* K1 coil-contact capacitance (COM on LINE_FUSED, coil on +5V) ASM 2 pF
Ckc LF SG 2p
* SELV supply (ideal 3V3 referred to the SELV ground)
V33 V33 SG DC 3.3
* SELV board and appliance chassis strays (ASM, swept)
Csg SG 0 {Csg}
Csc SG CHS {Csc}
Ccg CHS 0 {Ccg}
* thermocouple: probe in the chamber, lead 1 m (1 uH per wire), J20 TVS, 1k/10n/100n filter
{tc}
Btvsp J20P SG I = pwl(V(J20P,SG), {tvs_pwl()})
Btvsn J20N SG I = pwl(V(J20N,SG), {tvs_pwl()})
Ctvp J20P SG 35p
Ctvn J20N SG 35p
R220 J20P TCFP 1k
R221 J20N TCFN 1.001k
C221 TCFP SG 10n
C222 TCFN SG 11n
C220 TCFP TCFN 100n
* EN pin: R11 10k to 3V3, C6 1 uF to SG
R11 V33 EN 10k
C6 EN SG 1u
.options reltol=1e-3 method=gear rshunt=1e10
.tran 0.1n 3u 0 0.1n
.end
"""


def run(**kw):
    r = cm.run_netlist(netlist(**kw))
    t = r['time']
    g = r['v(sg)']
    d = lambda a, b: r[f'v({a})'] - r[f'v({b})']
    vzc = d('zc', 'sg'); vT = d('lfi', 'a1'); vmoc = d('moc6', 'g'); vtc = d('tcfp', 'tcfn')
    i_led = (r['v(sg)'] - r['v(led)']) / 120.0
    dvdt = np.gradient(vT, t)
    out = {'V_GND_vs_RGP_pk': float(np.max(np.abs(g))),
           'V_ZC_min': float(vzc.min()), 'V_ZC_max': float(vzc.max()), 'V_ZC_idle': float(vzc[0]),
           'V_triac_pk': float(np.max(np.abs(vT - vT[0]))), 'dVdt_triac_V_per_us': float(np.max(np.abs(dvdt)) / 1e6),
           'V_moc_pk': float(np.max(np.abs(vmoc - vmoc[0]))),
           'I_LED_pk_mA': float(np.max(np.abs(i_led)) * 1e3), 'Q_LED_nC': float(np.trapezoid(np.abs(i_led), t) * 1e9),
           'V_TC_diff_pk_uV': float(np.max(np.abs(vtc)) * 1e6), 'V_TC_diff_end_uV': float(vtc[-1] * 1e6),
           'TC_diff_area_uVs': float(np.trapezoid(vtc, t) * 1e6),
           'V_TCFP_vs_GND_pk': float(np.max(np.abs(d('tcfp', 'sg')))), 'V_J20_pk': float(np.max(np.abs(d('j20p', 'sg')))),
           'V_EN_dev_mV': float(np.max(np.abs(d('en', 'sg') - 3.3)) * 1e3),
           'V_HLK_barrier_pk': float(np.max(np.abs(d('hp', 'sg')))),
           'V_K1_coil_contact_pk': float(np.max(np.abs(d('lf', 'sg')))),
           'V_GA1_pk': float(np.max(np.abs(d('g', 'a1')))),
           'ZC_false_pulse_width_ns': float(np.sum(np.diff(t)[(vzc[:-1] < 1.14) if vzc[0] > 2 else (vzc[:-1] > 1.5)]) * 1e9),
           'V_TCFP_vs_GND_min': float(np.min(d('tcfp', 'sg'))), 'V_TCFP_vs_GND_max': float(np.max(d('tcfp', 'sg')))}
    # displacement charge through the triac junction capacitance (gate-charge argument)
    out['Q_Cj_nC'] = float(kw.get('Cj', 100e-12) * out['V_triac_pk'] * 1e9)
    return out, t, {'vzc': vzc, 'vT': vT, 'g': g, 'vtc': vtc}


def main():
    cases = []
    waves = {}
    for pol, Chlk, (Csc, Ccg), q_on in itertools.product((+1, -1), (20e-12, 100e-12, 1e-9), ((5e-12, 20e-12), (20e-12, 50e-12), (50e-12, 150e-12)), (False, True)):
        m, t, w = run(pol=pol, Chlk=Chlk, Csc=Csc, Ccg=Ccg, q_on=q_on)
        key = f"{'+' if pol > 0 else '-'}|C_hlk {Chlk*1e12:.0f}p|C_sc/C_cg {Csc*1e12:.0f}/{Ccg*1e12:.0f}p|ZCD transistor {'on' if q_on else 'off'}"
        cases.append({'case': key, **m})
        if pol > 0 and Chlk == 100e-12 and Csc == 20e-12:
            waves['on' if q_on else 'off'] = (t, w)

    # junction-capacitance sweep and mains phase (triac bias) for the triac
    triac = []
    for Cj, Vinst in itertools.product((50e-12, 100e-12, 200e-12), (0.0, 325.0)):
        for pol in (+1, -1):
            m, *_ = run(pol=pol, Cj=Cj, Vinst=Vinst)
            triac.append({'Cj_pF': Cj * 1e12, 'Vinst': Vinst, 'pol': pol, **{k: m[k] for k in ('V_triac_pk', 'dVdt_triac_V_per_us', 'V_moc_pk', 'Q_Cj_nC', 'V_GA1_pk')}})
    # opto coupling capacitance sweep for the ZCD node
    zcd = []
    for Cio, q_on, pol in itertools.product((0.3e-12, 0.5e-12, 1e-12, 2e-12), (False, True), (+1, -1)):
        m, *_ = run(pol=pol, Cio_zcd=Cio, q_on=q_on, Chlk=20e-12, Csc=5e-12, Ccg=20e-12)
        zcd.append({'Cio_pF': Cio * 1e12, 'transistor': 'on' if q_on else 'off', 'pol': pol, 'V_ZC_min': m['V_ZC_min'], 'V_ZC_max': m['V_ZC_max']})
    # thresholds: SN74LVC1G14 at VCC 3 V: VT+ 1.5-1.87 V, VT- 0.84-1.14 V (Datasheets/sn74lvc1g14.pdf p.6)
    VTp_min, VTm_max = 1.5, 1.14
    false_edges = [c['case'] for c in cases if ('off' in c['case'] and c['V_ZC_min'] < VTm_max) or ('on' in c['case'] and c['V_ZC_max'] > VTp_min)]
    fe_zcd = [z for z in zcd if (z['transistor'] == 'off' and z['V_ZC_min'] < VTm_max) or (z['transistor'] == 'on' and z['V_ZC_max'] > VTp_min)]
    # thermocouple: burst average error.  75 pulses per 15 ms, 1 burst / 300 ms; ADS1115 at 16 SPS integrates 62.5 ms
    worst_area = max(abs(c['TC_diff_area_uVs']) for c in cases)
    bursts_per_conv = 62.5 / 300.0
    err_uV = worst_area * 1e-6 * 75 * bursts_per_conv / 62.5e-3 * 1e6   # uV average over one conversion (upper bound: all pulses in one conversion)
    err_uV_worst_conv = worst_area * 1e-6 * 75 / 62.5e-3 * 1e6
    res = {'cases': cases, 'triac_sweep': triac, 'zcd_cio_sweep': zcd,
           'zcd_false_edge_cases': false_edges, 'zcd_false_edge_cio_cases': fe_zcd,
           'thresholds': {'VT+_min': VTp_min, 'VT-_max': VTm_max, 'src': 'TI SN74LVC1G14 (Datasheets/sn74lvc1g14.pdf) p.6, VCC 3 V; BOM MPN field says SN74AHC1G14DBVR'},
           'tc_error': {'worst_pulse_area_uVs': worst_area, 'avg_error_uV_one_burst_in_conversion': err_uV_worst_conv,
                        'avg_error_degC_worst_conversion': err_uV_worst_conv / 41.0, 'note': 'K-type 41 uV/K; a burst (15 ms) falls inside at most one 62.5 ms conversion'},
           'triac_worst': max(triac, key=lambda d: d['V_triac_pk']),
           'gnd_rgp_worst': max(c['V_GND_vs_RGP_pk'] for c in cases),
           'EN_worst_mV': max(c['V_EN_dev_mV'] for c in cases),
           'K1_coil_contact_worst': max(c['V_K1_coil_contact_pk'] for c in cases),
           'LED_worst': max(cases, key=lambda c: c['I_LED_pk_mA'])}
    res['worst'] = {k: max(cases, key=lambda c: abs(c[k]))[k] for k in ('ZC_false_pulse_width_ns', 'V_GA1_pk', 'V_TCFP_vs_GND_pk', 'V_J20_pk', 'I_LED_pk_mA', 'Q_LED_nC', 'V_moc_pk', 'V_ZC_max', 'V_triac_pk', 'dVdt_triac_V_per_us', 'V_HLK_barrier_pk')}
    res['worst']['V_TCFP_vs_GND_min'] = min(c['V_TCFP_vs_GND_min'] for c in cases)
    res['worst']['V_TCFP_vs_GND_max'] = max(c['V_TCFP_vs_GND_max'] for c in cases)
    res['worst']['V_GA1_pk_triac_sweep'] = None
    # proposal P-E1: 1 nF C0G from the ZCD collector node to GND (with R8 10k: tau 10 us)
    prop = []
    for pol, Chlk, (Csc, Ccg), q_on, Cio in itertools.product((+1, -1), (20e-12, 100e-12, 1e-9), ((5e-12, 20e-12), (20e-12, 50e-12), (50e-12, 150e-12)), (False, True), (0.5e-12, 2e-12)):
        m, *_ = run(pol=pol, Chlk=Chlk, Csc=Csc, Ccg=Ccg, q_on=q_on, Cio_zcd=Cio, Czc=1e-9)
        prop.append({'pol': pol, 'Chlk_pF': Chlk * 1e12, 'Csc_Ccg_pF': [Csc * 1e12, Ccg * 1e12], 'transistor': 'on' if q_on else 'off', 'Cio_pF': Cio * 1e12, 'V_ZC_min': m['V_ZC_min'], 'V_ZC_max': m['V_ZC_max']})
    res['proposal_P_E1_1nF_on_ZCD_node'] = {'rows': prop,
        'worst_off_min': min(p['V_ZC_min'] for p in prop if p['transistor'] == 'off'),
        'worst_on_max': max(p['V_ZC_max'] for p in prop if p['transistor'] == 'on'),
        'worst_abs_max': max(p['V_ZC_max'] for p in prop),
        'edge_delay_us': 10e3 * 1e-9 * np.log(3.3 / (3.3 - 1.87)) * 1e6}
    print('proposal', {k: v for k, v in res['proposal_P_E1_1nF_on_ZCD_node'].items() if k != 'rows'})
    print('worst', res['worst'])
    cm.save_results('eft', res)
    # plots
    fig, ax = plt.subplots(2, 1, figsize=(9, 7))
    for k, (t, w) in waves.items():
        ax[0].plot(t * 1e9, w['vzc'], label=f'ZCD collector node, transistor {k}')
    ax[0].axhline(VTp_min, c='r', ls=':', label='U6 VT+ min 1.5 V'); ax[0].axhline(VTm_max, c='m', ls=':', label='U6 VT− max 1.14 V')
    ax[0].set_ylabel('V vs SELV GND (V)'); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3); ax[0].set_xlim(0, 1000)
    ax[0].set_title('EFT +1 kV CM, C_hlk 100 pF, C_sc/C_cg 20/50 pF (ASM)', fontsize=9)
    t, w = waves['off']
    ax[1].plot(t * 1e9, w['vT'] - w['vT'][0], label='triac A2–A1 (Cj 100 pF)'); ax[1].plot(t * 1e9, w['g'], label='SELV GND vs RGP')
    ax[1].set_xlabel('t (ns)'); ax[1].set_ylabel('V (V)'); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3); ax[1].set_xlim(0, 1000)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'eft_waveforms.png'), dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4))
    for st, mk in (('off', 'o'), ('on', 's')):
        for pol, c in ((+1, 'C0'), (-1, 'C1')):
            zz = [z for z in zcd if z['transistor'] == st and z['pol'] == pol]
            y = [z['V_ZC_min'] if st == 'off' else z['V_ZC_max'] for z in zz]
            ax.plot([z['Cio_pF'] for z in zz], y, mk + '-', c=c, label=f"transistor {st}, {'+' if pol > 0 else '−'} pulse ({'min' if st == 'off' else 'max'})")
    ax.axhline(VTp_min, c='r', ls=':'); ax.axhline(VTm_max, c='m', ls=':')
    ax.set_xlabel('H11AA1 input–output capacitance (pF, ASM)'); ax.set_ylabel('ZCD node extreme (V)'); ax.grid(alpha=.3); ax.legend(fontsize=7)
    ax.set_title('False ZCD edge if: off → below 1.14 V, on → above 1.5 V', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'eft_zcd_sweep.png'), dpi=120); plt.close(fig)
    print('false edges:', len(false_edges), 'of', len(cases)); print('triac worst', res['triac_worst']); print('tc', res['tc_error'])
    print('gnd', res['gnd_rgp_worst'], 'EN', res['EN_worst_mV'], 'K1', res['K1_coil_contact_worst'])


if __name__ == '__main__':
    main()
