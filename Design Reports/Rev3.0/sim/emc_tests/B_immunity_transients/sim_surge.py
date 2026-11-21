"""Surge 1 kV line-to-neutral, 2 Ohm, 1.2/50 (8/20) us -- EN 55014-2 5.6 Table 12 (PDF p.20-21).

Positive pulses at 90 deg, negative at 270 deg of the mains (STD p.21).  L-E / N-E surges are not applied
(no provision for earth, STD p.21).  Generator: fitted CWG (validate_generators.py) through an 18 uF
coupling capacitor (NRS, TI SLVA711 p.8) between L and N, mains 230 V behind 1.5 mH decoupling chokes (ASM).

EUT model (topology from the current schematic, netlist_extract.json):
  J3.L -> F3 -> LINE_FUSED -> L40 (saturable, swept) -> LINE_FILT ; C40 1 uF, C1 100 nF, RV1 TVR14431 at LINE_FILT-NEUT
  K1 COM on LINE_FUSED -> fan (NO contact), open or closed
  Q1 BTA24 A2 = LINE_FILT, A1 -> heater 52.9 Ohm -> NEUT ; RV2 TVR10561 and R5 47 Ohm + C4 10 nF across A2-A1;
    MOC3052 (R3 360 Ohm from A2, R2 360 Ohm gate-A1) sees ~V(A2-A1)
  F1 -> L1 (CMC, differential leakage swept) -> HLK-10M05 (black box: 11 Ohm inrush resistor from the 34 A
    inrush spec, bridge, bulk C swept, 7 W load) ; ZCD R6/R7 33k + H11AA1 LEDs across the HLK AC pins.
Run:  python -X utf8 sim_surge.py [--proposal]
"""
import itertools, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as cm

P = cm.P
VPK = 230 * np.sqrt(2)


# ---- breakover model: bistable state nodes sm (driver) and sq (Q1) with a cubic latch term; set when
# |V_driver| > VBO (resp. |I_gate| > IGT), reset when the main current < IH.
# ---- (argument made quantitative; thresholds ASM: MOC breakover at its VDRM 600 V -- the real
# VBO is not specified and is >= 600 V; MOC hold current 540 uA (onsemi p.3 IH typ); Q1 latches when the gate current
# exceeds IGT max 35 mA and drops out below IH 50 mA (ST p.2); gate modelled as antiparallel diodes ~1 V at 35 mA)
BREAKOVER_MOC = '''Bmoc moc6 QG I = V(moc6,QG)*(1n + 0.2*max(V(sm),0))
Bsm 0 sm I = 1m*( -10*V(sm)*(V(sm)-0.5)*(V(sm)-1) + 1.5*(1+tanh((abs(V(moc6,QG))-VBO)/2)) - 0.5*(1+tanh((540u-abs(V(moc6,QG))*(1n+0.2*max(V(sm),0)))/100u)) )
Csm sm 0 1n
Dsm1 sm smh dlim
Vsmh smh 0 1
Dsm0 0 sm dlim
.model dlim D(Is=1e-12 N=0.3)'''
GATE_BO = '''R2 QG A1 360.0
Vgs QG gx 0
Dg1 gx A1 dgt
Dg2 A1 gx dgt
.model dgt D(Is=1e-12 N=1.5 Rs=2)'''
BREAKOVER_Q1 = '''Bq LFI A1 I = V(LFI,A1)*(1e-7 + 20*max(V(sq),0))
Cq LFI A1 100p
Bsq 0 sq I = 1m*( -10*V(sq)*(V(sq)-0.5)*(V(sq)-1) + 1.5*(1+tanh((abs(i(Vgs))-35m)/2m)) - 0.5*(1+tanh((50m-abs(V(LFI,A1))*(1e-7+20*max(V(sq),0)))/10m)) )
Csq sq 0 1n
Dsq1 sq sqh dlim
Vsqh sqh 0 1
Dsq0 0 sq dlim'''


def netlist(pol=+1, heater=False, relay_closed=False, mov='max', Lsat=10e-6, Isat=10.0, Lleak=100e-6, Cbulk=10e-6,
            U=1000.0, rv1_node='LFI', rv2='RV2', extra='', tmax=200e-9, breakover=False, t_after=250e-6, vbo=600):
    ts = 45e-3 if pol > 0 else 35e-3              # 90 deg (3rd cycle) / 270 deg (2nd cycle)
    Ug = pol * U * cm.load_results()['validation']['cwg']['U_for_1kV_open_circuit'] / 1000.0
    L0 = P['L40_L0'][0]; phs = L0 * Isat
    k = (1 / Lsat - 1 / L0)
    # NOTE (2026-11-18 fix): the gate node was called 'G', which SPICE (case-insensitive) merged with the CWG
    # output node 'g' -> the surge drove A1 through R2 (1.3 A, A1 ~70 V up).  The gate node is now 'QG'.
    if heater:
        triac = 'Rq LFI A1 0.05'
    elif breakover:
        triac = BREAKOVER_Q1
    else:
        triac = 'Rq LFI A1 10Meg\nCq LFI A1 100p'
    moc = BREAKOVER_MOC.replace('VBO', str(vbo)) if (breakover and not heater) else 'Rmoc moc6 QG 1G\nCmoc moc6 QG 1p'
    gate = GATE_BO if (breakover and not heater) else 'R2 QG A1 360.0'
    if relay_closed:
        k1 = 'Rk1 LF FANH 10m'
    else:
        k1 = 'Ck1 LF FANH 1.5p\nRk1 LF FANH 1G'
    rv2_line = (f"Brv2 LFI A1x I = pwl(V(LFI,A1x), {cm.mov_pwl(rv2, mov)})\nLrv2 A1x A1 15n\nCrv2 LFI A1 {P[rv2]['C_pF']}p"
                if rv2 else '')
    return f"""surge
{cm.cwg_subckt('CWG', Ug)}
.model dled D(Is=1e-19 N=1.5 Rs=3)
.model dbr D(Is=1e-9 N=1.8 Rs=0.05 Cjo=50p TT=1u)
* ---- mains + CDN (decoupling ASM 1.5 mH per line, source 0.4 Ohm + 0.8 mH)
Bm mL mN V = {VPK:.2f}*sin(2*pi*50*time)*(1-exp(-time/4m))
Rsrc mL m1 0.4
Lsrc m1 m2 0.8m
Ldl m2 LT 1.5m
Ldn mN 0 1.5m
X1 g 0 CWG PARAMS: ts={ts}
Ccp g LT 18u
* ---- cord (ASM 1 uH per conductor) and EUT
Lcl LT J3L {P['Lcord'][0]}
Lcn 0 NEUT {P['Lcord'][0]}
Rf3 J3L LF 10m
{k1}
Cfan FANH NEUT 200p
Rfan FANH fx 600
Lfan fx NEUT 3
* L40 saturable (flux-linkage integrator)
Gphi 0 phi LF LX 1
Cphi phi 0 1
Rphi phi 0 1e9
BL40 LF LX I = V(phi)/{Lsat:.4g} - {k:.6g}*{phs:.6g}*tanh(V(phi)/{phs:.6g})
RL40 LX LFI {P['L40_R'][0]}
CL40 LF LFI 10p
* X capacitors (ESL/ESR ASM)
C40 LFI c40a {P['C40'][0]}
Lc40 c40a c40b 20n
Rc40 c40b NEUT 10m
C1 LFI c1a {P['C1'][0]}
Lc1 c1a NEUT 15n
* RV1
Brv1 {rv1_node} rv1x I = pwl(V({rv1_node},rv1x), {cm.mov_pwl('RV1', mov)})
Lrv1 rv1x NEUT 15n
Crv1 {rv1_node} NEUT {P['RV1']['C_pF']}p
* triac branch
{triac}
{rv2_line}
R5 LFI sn {P['R5'][0]}
C4 sn A1 {P['C4'][0]}
R3 LFI moc6 {P['R3'][0]}
{moc}
{gate}
Lh A1 hx {P['Lheater'][0]}
Rh hx NEUT {P['Rheater'][0]:.3f}
* PSU branch: F1, L1 differential leakage (ASM), HLK black box
Rf1 LFI PL 0.15
Ll1a PL AL {Lleak/2:.4g}
Rl1ap PL AL 2k
Rl1a AL ALx 0.5
Ll1b NEUT AN {Lleak/2:.4g}
Rl1bp NEUT AN 2k
Cx_hlk ALx ANx 1n
Rl1b AN ANx 0.5
Rin ALx hin 11
D1 hin bp dbr
D2 ANx bp dbr
D3 bn hin dbr
D4 bn ANx dbr
Cb bp bn {Cbulk:.4g}
Rld bp bn 13.7k
* ZCD: R6/R7 on the HLK AC pins (after L1), H11AA1 antiparallel LEDs
R6 ALx zl 33k
Dz1 zl zn dled
Dz2 zn zl dled
R7 zn ANx 33k
{extra}
.options reltol=1e-3 abstol=1e-9 vntol=1e-4 itl4=200 method=gear
.tran {tmax:.3g} {ts + t_after:.6g} {ts - 30e-6:.6g} {tmax:.3g} uic
.end
""", ts


def measure(r, ts, heater, rv1_node='LFI'):
    t = r['time']; w = (t >= ts - 20e-6) & (t <= ts + 250e-6)
    tw = t[w]
    def v(a, b=None):
        x = r[f'v({a.lower()})'][w]
        return x - r[f'v({b.lower()})'][w] if b else x
    out = {}
    vLF = v('LF', 'NEUT'); vLFI = v('LFI', 'NEUT'); vT = v('LFI', 'A1')
    out['V_LINE_FUSED_pk'] = float(np.max(np.abs(vLF)))
    out['V_K1_open_contacts_pk'] = float(np.max(np.abs(v('LF', 'FANH'))))
    out['V_LINE_FILT_pk'] = float(np.max(np.abs(vLFI)))
    out['V_triac_pk'] = float(np.max(np.abs(vT)))
    dv = np.gradient(vT, tw)
    out['dVdt_triac_max_V_per_us'] = float(np.max(np.abs(dv)) / 1e6)
    # currents via voltage drops / B-source branches
    def br(name):
        k = f'{name}#branch'
        return r[k][w] if k in r else None
    irv1 = br('lrv1'); irv2 = br('lrv2')
    iL40 = v('LX', 'LFI') / P['L40_R'][0]
    iF1 = v('LFI', 'PL') / 0.15
    iF3 = v('J3L', 'LF') / 10e-3
    ih = v('hx', 'NEUT') / P['Rheater'][0]
    iled = v('ALx', 'zl') / 33e3
    out['I_L40_pk'] = float(np.max(np.abs(iL40)))
    out['I_F3_pk'] = float(np.max(np.abs(iF3)))
    out['I2t_F3_A2s'] = float(np.trapezoid(iF3 ** 2, tw))
    out['I_F1_pk'] = float(np.max(np.abs(iF1)))
    out['I2t_F1_A2s'] = float(np.trapezoid(iF1 ** 2, tw))
    if irv1 is not None:
        vr1 = v(rv1_node, 'rv1x')
        out['I_RV1_pk'] = float(np.max(np.abs(irv1)))
        out['E_RV1_J'] = float(np.trapezoid(np.abs(irv1 * vr1), tw))
    irv3 = br('lrv3')
    if irv3 is not None:
        out['I_RV3_pk'] = float(np.max(np.abs(irv3)))
        out['E_RV3_J'] = float(np.trapezoid(np.abs(irv3 * v('LF', 'rv3x')), tw))
    if irv2 is not None:
        vr2 = v('LFI', 'A1x')
        out['I_RV2_pk'] = float(np.max(np.abs(irv2)))
        out['E_RV2_J'] = float(np.trapezoid(np.abs(irv2 * vr2), tw))
    out['V_bulk_pk'] = float(np.max(v('bp', 'bn')))
    out['V_bulk_pre'] = float(v('bp', 'bn')[0])
    out['I_LED_pk_mA'] = float(np.max(np.abs(iled)) * 1e3)
    out['V_R6_pk'] = float(np.max(np.abs(v('ALx', 'zl'))))
    out['V_HLK_in_pk'] = float(np.max(np.abs(v('ALx', 'ANx'))))
    out['I_heater_pk'] = float(np.max(np.abs(ih)))
    out['V_heater_pk'] = float(np.max(np.abs(v('A1', 'NEUT'))))
    return out, tw, {'vLF': vLF, 'vLFI': vLFI, 'vT': vT, 'irv1': irv1, 'iL40': iL40,
                     'vbulk': v('bp', 'bn'), 'iled': iled}


def run_case(**kw):
    # max time step 200 ns (converged to 0.1 V against 20 ns, see review note); retry finer if ngspice fails
    for tm in (200e-9, 100e-9, 50e-9, 20e-9):
        net, ts = netlist(tmax=tm, **{k: v for k, v in kw.items() if k != 'tmax'})
        try:
            r = cm.run_netlist(net)
            break
        except Exception:
            continue
    else:
        raise RuntimeError('ngspice failed at every step size')
    m, tw, wv = measure(r, ts, kw.get('heater', False), kw.get('rv1_node', 'LFI'))
    return m, tw, wv, ts


def main(proposal=False):
    cases = []
    sat_sets = [(20e-6, 20.0), (10e-6, 10.0), (5e-6, 6.0)]     # soft / mid / hard saturation (ASM)
    worst = {}
    waves = {}
    for pol, heater, relay, mov, (Lsat, Isat) in itertools.product((+1, -1), (False, True), (False, True), ('max', 'min'), sat_sets):
        m, tw, wv, ts = run_case(pol=pol, heater=heater, relay_closed=relay, mov=mov, Lsat=Lsat, Isat=Isat)
        key = f"{'+' if pol > 0 else '-'}|heater {'on' if heater else 'off'}|K1 {'closed' if relay else 'open'}|MOV {mov}|L40 sat {Lsat*1e6:.0f}uH/{Isat:.0f}A"
        cases.append({'case': key, **m})
        print(key, 'Vtriac', round(m['V_triac_pk']), 'VK1', round(m['V_K1_open_contacts_pk']), 'IRV1', round(m['I_RV1_pk']))
        if pol > 0 and not heater and not relay and mov == 'max' and Isat == 10.0:
            waves['ref'] = (tw - ts, wv)
    # PSU-branch sweep (worst MOV corner max, heater off, + polarity): CMC leakage and bulk C
    psu = []
    for Lleak, Cb in itertools.product((20e-6, 100e-6, 200e-6), (4.7e-6, 10e-6, 22e-6)):
        m, *_ = run_case(pol=+1, heater=False, relay_closed=False, mov='max', Lsat=10e-6, Isat=10.0, Lleak=Lleak, Cbulk=Cb)
        psu.append({'Lleak_uH': Lleak * 1e6, 'Cbulk_uF': Cb * 1e6, **{k: m[k] for k in ('V_bulk_pk', 'V_bulk_pre', 'I_F1_pk', 'I2t_F1_A2s', 'I_LED_pk_mA', 'V_R6_pk', 'V_HLK_in_pk')}})
        print('PSU', Lleak, Cb, round(psu[-1]['V_bulk_pk']))
    def wmax(key):
        c = max(cases, key=lambda c: c.get(key, 0)); return c[key], c['case']
    summary = {k: {'max': wmax(k)[0], 'case': wmax(k)[1]} for k in cases[0] if k != 'case'}
    summary['V_triac_pk_heater_off'] = max(((c['V_triac_pk'], c['case']) for c in cases if 'heater off' in c['case']))
    summary['V_K1_open_pk'] = max(((c['V_K1_open_contacts_pk'], c['case']) for c in cases if 'K1 open' in c['case']))
    summary['E_RV1_min_corner'] = max(((c['E_RV1_J'], c['case']) for c in cases if 'MOV min' in c['case']))
    ratings = {
        'V_triac_pk_heater_off': (P['BTA24']['VDRM'], 'BTA24 VDRM 800 V (VDSM 900 V, 10 ms)'),
        'V_MOC3052': (P['MOC3052']['VDRM'], 'MOC3052 VDRM 600 V'),
        'V_K1_open_pk': (750 * np.sqrt(2), 'HJR-3FF 750 Vac open-contact dielectric (1 min) = 1061 Vpk; no impulse rating published'),
        'dVdt': (P['BTA24']['dVdt_min_Vus'], 'BTA24-800CW static dV/dt 500 V/us min (125 C, 67 % VDRM)'),
        'I_RV1': (P['RV1']['Imax_8_20'], 'TVR14431 Imax 4500 A 8/20 single pulse'),
        'E_RV1': (P['RV1']['Wmax_J_10_1000'], 'TVR14431 115 J 10/1000 us'),
        'I_RV2': (P['RV2']['Imax_8_20'], 'TVR10561 Imax 2500 A'),
        'I2t_F3': (P['F3_I2t_min'][0], 'F3 8 A fast pre-arc I2t lower bound 10.2 A2s'),
        'I2t_F1': (P['F1_I2t'][0], 'F1 1 A time-lag I2t 3.5 A2s'),
        'I_LED': (P['H11AA1']['IF_max_mA'], 'H11AA1 IF +-40 mA continuous (no pulse rating; conservative)'),
        'V_R6': (P['R6R7']['Vmax'], 'R6/R7 500 V (BOM value field)'),
        'V_bulk': (400.0, 'HLK bulk capacitor: assumed 400 V e-cap (internals unpublished)'),
    }
    ver = {}
    def add(name, val, rk, case):
        lim, txt = ratings[rk]
        v, mg = cm.verdict(val, lim)
        ver[name] = {'value': val, 'limit': lim, 'rating': txt, 'margin_pct': mg * 100, 'verdict': v, 'case': case}
    add('BTA24 off-state voltage', summary['V_triac_pk_heater_off'][0], 'V_triac_pk_heater_off', summary['V_triac_pk_heater_off'][1])
    add('MOC3052 off-state voltage', summary['V_triac_pk_heater_off'][0], 'V_MOC3052', summary['V_triac_pk_heater_off'][1])
    add('K1 open-contact voltage', summary['V_K1_open_pk'][0], 'V_K1_open_pk', summary['V_K1_open_pk'][1])
    add('BTA24 dV/dt', summary['dVdt_triac_max_V_per_us']['max'], 'dVdt', summary['dVdt_triac_max_V_per_us']['case'])
    add('RV1 peak current', summary['I_RV1_pk']['max'], 'I_RV1', summary['I_RV1_pk']['case'])
    add('RV1 energy', summary['E_RV1_min_corner'][0], 'E_RV1', summary['E_RV1_min_corner'][1])
    add('RV2 peak current', summary['I_RV2_pk']['max'], 'I_RV2', summary['I_RV2_pk']['case'])
    add('F3 I2t', summary['I2t_F3_A2s']['max'], 'I2t_F3', summary['I2t_F3_A2s']['case'])
    pw = max(psu, key=lambda d: d['I2t_F1_A2s'])
    add('F1 I2t', pw['I2t_F1_A2s'], 'I2t_F1', f"Lleak {pw['Lleak_uH']} uH, Cbulk {pw['Cbulk_uF']} uF")
    pl = max(psu, key=lambda d: d['I_LED_pk_mA'])
    add('H11AA1 LED current', pl['I_LED_pk_mA'], 'I_LED', f"Lleak {pl['Lleak_uH']} uH")
    add('R6/R7 voltage', max(d['V_R6_pk'] for d in psu), 'V_R6', 'PSU sweep max')
    pb = max(psu, key=lambda d: d['V_bulk_pk'])
    add('HLK bulk capacitor', pb['V_bulk_pk'], 'V_bulk', f"Lleak {pb['Lleak_uH']} uH, Cbulk {pb['Cbulk_uF']} uF")
    # MOV life: 10 pulses at the simulated peak current vs the 8/20 single-pulse rating -> fraction
    res = {'cases': cases, 'psu_sweep': psu, 'summary': summary, 'verdicts': ver,
           'mov_life_note': 'RV1 peak current vs the 4500 A single-pulse rating; 10 pulses of the test (5+/5-) are read against the derating curve family p.17-18 in the report'}
    cm.save_results('surge' + ('_proposal' if proposal else ''), res)
    # plot reference case
    if 'ref' in waves:
        tw, wv = waves['ref']
        fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
        ax[0].plot(tw * 1e6, wv['vLF'], label='LINE_FUSED–NEUT (K1 COM, fan branch)')
        ax[0].plot(tw * 1e6, wv['vLFI'], label='LINE_FILT–NEUT (RV1, HLK input)')
        ax[0].plot(tw * 1e6, wv['vT'], '--', label='triac A2–A1 (heater off)')
        ax[0].axhline(800, c='r', ls=':', label='BTA24 VDRM 800 V'); ax[0].axhline(600, c='m', ls=':', label='MOC3052 VDRM 600 V')
        ax[0].axhline(1061, c='k', ls=':', label='K1 open contacts 750 Vac = 1061 Vpk')
        ax[0].set_ylabel('V (V)'); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
        ax[0].set_title('Surge +1 kV / 2 Ω at 90°, heater off, K1 open, RV1/RV2 max-voltage corner, L40 knee 10 A (ASM)', fontsize=9)
        ax[1].plot(tw * 1e6, wv['irv1'], label='I RV1'); ax[1].plot(tw * 1e6, wv['iL40'], label='I L40')
        ax[1].set_xlabel('t after surge trigger (µs)'); ax[1].set_ylabel('I (A)'); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
        fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'surge_waveforms.png'), dpi=120); plt.close(fig)
    # bar plot of margins
    fig, ax = plt.subplots(figsize=(9, 4.5))
    names = list(ver); vals = [ver[n]['value'] / ver[n]['limit'] * 100 for n in names]
    cols = ['tab:red' if ver[n]['verdict'] == 'FAIL' else 'tab:orange' if ver[n]['verdict'] == 'MARGINAL' else 'tab:green' for n in names]
    ax.barh(names, vals, color=cols); ax.axvline(100, c='k'); ax.axvline(80, c='k', ls=':')
    ax.set_xlabel('worst stress / rating (%)'); ax.set_xscale('log'); ax.grid(alpha=.3, axis='x')
    ax.set_title('Surge 1 kV L–N: worst case over polarity, heater, K1, MOV tolerance, L40 saturation', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(cm.PLOTS, 'surge_margins.png'), dpi=120); plt.close(fig)
    print(json.dumps(ver, indent=1, default=float))


def RV3(mov):
    return (f"Brv3 LF rv3x I = pwl(V(LF,rv3x), {cm.mov_pwl('RV1', mov)})\n"
            "Lrv3 rv3x NEUT 15n\nCrv3 LF NEUT 370p")


def proposals():
    sat_sets = [(20e-6, 20.0), (10e-6, 10.0), (5e-6, 6.0)]
    variants = {
        'P-S1 alone (800 V driver, RV2 unchanged): same circuit as the current design': dict(),
        'P-S3 alone: RV2 TVR10561 -> TVR14431': dict(rv2='RV1'),
        'P-S2b: add RV3 = TVR14431KSU15Y at LINE_FUSED-NEUT, keep RV1 at LINE_FILT': dict(extra_fn=RV3),
        'P-S2b + P-S3': dict(extra_fn=RV3, rv2='RV1'),
        'P-S4: RV2 -> 1.5KE440CA bidirectional TVS across the triac': dict(rv2='TVS440'),
        'P-S2b + P-S4': dict(extra_fn=RV3, rv2='TVS440'),
        'info: RV2 -> TVR14391 (250 Vac class)': dict(rv2='RV14391'),
        'P-S2a (rejected): RV1 moved from LINE_FILT to LINE_FUSED (in front of L40)': dict(rv1_node='LF'),
    }
    out = {}
    for name, var in variants.items():
        rows = []
        for heater, mov, (Lsat, Isat) in itertools.product((False, True), ('max', 'min'), sat_sets):
            kw = dict(pol=+1, heater=heater, relay_closed=False, mov=mov, Lsat=Lsat, Isat=Isat)
            if 'rv1_node' in var: kw['rv1_node'] = var['rv1_node']
            if 'extra_fn' in var: kw['extra'] = var['extra_fn'](mov)
            if 'rv2' in var: kw['rv2'] = var['rv2']
            m, *_ = run_case(**kw)
            rows.append({'case': f"heater {'on' if heater else 'off'}|MOV {mov}|L40 {Lsat*1e6:.0f}uH/{Isat:.0f}A", **m})
        w = lambda k, filt='': max((r.get(k, 0), r['case']) for r in rows if filt in r['case'])
        out[name] = {'rows': rows,
                     'V_triac_pk_heater_off': w('V_triac_pk', 'heater off'),
                     'V_K1_open_pk': w('V_K1_open_contacts_pk'),
                     'V_LINE_FILT_pk': w('V_LINE_FILT_pk'),
                     'I_RV1_pk': w('I_RV1_pk'), 'E_RV1_J': w('E_RV1_J'),
                     'I_RV3_pk': w('I_RV3_pk'), 'E_RV3_J': w('E_RV3_J'),
                     'V_bulk_pk': w('V_bulk_pk'), 'I2t_F3_A2s': w('I2t_F3_A2s'), 'dVdt': w('dVdt_triac_max_V_per_us'),
                     'I_RV2_pk': w('I_RV2_pk'), 'E_RV2_J': w('E_RV2_J'), 'V_heater_pk': w('V_heater_pk', 'heater off')}
        print(name, 'Vtriac', out[name]['V_triac_pk_heater_off'], 'K1', out[name]['V_K1_open_pk'][0], 'Irv2', out[name]['I_RV2_pk'][0], 'Erv2', out[name]['E_RV2_J'][0])
    # Hi-Link reference input circuit (DS 10M series V1.5 sec.8 p.9-10): fuse + 10D561K + 0.1 uF X + 10 mH CMC,
    # no L40/C40 -- the HLK bulk stress it produces is the vendor's own design case for the module
    vend = []
    for Lleak, Cb in itertools.product((20e-6, 100e-6, 200e-6), (4.7e-6, 10e-6, 22e-6)):
        net, ts = netlist(pol=+1, heater=False, relay_closed=False, mov='max', Lleak=Lleak, Cbulk=Cb, rv2=None)
        lines = []
        for ln in net.splitlines():
            if ln.startswith('BL40'): ln = 'VL40 LF LX 0'
            if ln.startswith('C40 '): ln = 'C40 LFI c40a 1p'
            if ln.startswith('Brv1'): ln = ln.replace(cm.mov_pwl('RV1', 'max'), cm.mov_pwl('RV2', 'max'))
            lines.append(ln)
        try:
            r = cm.run_netlist(chr(10).join(lines))
        except Exception:
            r = cm.run_netlist(chr(10).join(lines).replace('.tran 2e-07', '.tran 5e-08'))
        m, *_ = measure(r, ts, False)
        vend.append({'Lleak_uH': Lleak * 1e6, 'Cbulk_uF': Cb * 1e6, 'V_HLK_in_pk': m['V_HLK_in_pk'], 'V_bulk_pk': m['V_bulk_pk']})
        print('vendor ref', vend[-1])
    out['HLK vendor reference circuit (10D561K, no L40/C40)'] = vend
    cm.save_results('surge_proposals', out)


def breakover_study():
    """Driver breakover -> gate -> Q1 latch -> heater on, simulated (thresholds ASM, see BREAKOVER_MOC)."""
    out = {}
    for label, vbo, rv2 in (('MOC3052 (VBO taken = VDRM 600 V), RV2 TVR10561', 600, 'RV2'),
                            ('P-S1 800 V driver (VBO 800 V), RV2 TVR10561', 800, 'RV2'),
                            ('P-S1 800 V driver, P-S3 RV2 TVR14431', 800, 'RV1')):
        for pol in (+1, -1):
            net, ts = netlist(pol=pol, heater=False, mov='max', Lsat=5e-6, Isat=6.0, breakover=True, vbo=vbo, rv2=rv2,
                              t_after=6e-3, tmax=100e-9)
            r = cm.run_netlist(net)
            t = r['time']; w = t >= ts - 5e-6; tw = t[w] - ts
            v = lambda a, b: (r[f'v({a.lower()})'] - r[f'v({b.lower()})'])[w]
            iq = v('LFI', 'A1') * (1e-7 + 20 * np.maximum(r['v(sq)'][w], 0))
            ih = r['lh#branch'][w]
            imoc = v('LFI', 'moc6') / 360.0
            on = np.abs(ih) > 0.2
            dur = float(np.sum(np.diff(tw)[on[:-1]]) * 1e3)
            didt = float(np.max(np.abs(np.gradient(iq, tw))) / 1e6)
            e = float(np.trapezoid(ih ** 2 * P['Rheater'][0], tw))
            res = {'moc_fired': bool(np.max(r['v(sm)'][w]) > 0.5), 'q1_latched': bool(np.max(r['v(sq)'][w]) > 0.5),
                   'V_triac_pk': float(np.max(np.abs(v('LFI', 'A1')))), 'I_driver_pk_A': float(np.max(np.abs(imoc))),
                   'heater_on_ms': dur, 'heater_energy_J': e, 'I_heater_pk_A': float(np.max(np.abs(ih))),
                   'Q1_dIdt_max_A_per_us': didt}
            out[f"{label} | {'+90' if pol > 0 else '-270'}"] = res
            print(label, pol, res)
    cm.save_results('surge_breakover', out)


if __name__ == '__main__':
    if '--breakover' in sys.argv:
        breakover_study()
    elif '--proposal' in sys.argv:
        proposals()
    else:
        main()
