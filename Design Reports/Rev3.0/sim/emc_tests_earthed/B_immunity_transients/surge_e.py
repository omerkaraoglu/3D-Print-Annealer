"""Surge with an earthed chassis -- EN 55014-2 5.6 Table 12 (PDF p.20-21): 2 kV line-to-earth and neutral-to-earth
with 12 Ohm (now applicable: the product has provision for connection to earth), 1 kV L-N with 2 Ohm; positive at
90 deg, negative at 270 deg.  Coupling (NOT READ from the standard: TI SLVA711 p.8-9): L-E/N-E 9 uF + 10 Ohm,
L-N 18 uF; generator 2 Ohm (fitted CWG of the committed scope-B folder).

Network: committed scope-B surge model + earth: cord L/N/PE 1 uH each (k 0.9), chassis node CH on PE, supply N earthed
at the source behind 1.5 mH; heater-to-chassis, fan-to-frame, wiring-to-chassis, heatsink and SELV-to-chassis
capacitances (ASM, swept); thermocouple ring on the chassis with the junction grounded (wires tied to CH) or insulated
(wires to CH through the probe's wire-to-sheath capacitance, ASM 100 pF).  Design state: see common_e.py.
Run (each block a few minutes):  python -X utf8 surge_e.py main | sweep | ln | fix
"""
import itertools, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common_e as ce

cm = ce.cm; P = ce.P
VPK = 230 * np.sqrt(2)
U1K = json.load(open(os.path.join(ce.OLD, 'cwg_fit.json')))      # fitted CWG
U_SCALE = json.load(open(os.path.join(ce.OLD, 'results.json'), encoding='utf-8'))['validation']['cwg']['U_for_1kV_open_circuit']


def cwg(U):
    p = U1K
    return f"""
.subckt CWGE out ret PARAMS: ts=0
Cc c1 ret {p['Cc']:.5g} IC={U}
Sw c1 c2 ctl 0 swm
Vctl ctl 0 PWL(0 0 {{ts}} 0 {{ts+1n}} 1)
Rs1 c2 ret {p['Rs1']:.5g}
Rm c2 c3 {p['Rm']:.5g}
Lr c3 out {p['Lr']:.5g}
Rs2 out ret {p['Rs2']:.5g}
.model swm sw(vt=0.5 vh=0.01 ron=1m roff=1e12)
.ends
"""


def netlist(mode='LPE', pol=+1, heater=False, relay_closed=False, tc='grounded', Cbar=100e-12, Csp=50e-12, Chc=200e-12,
            Cts=100e-12, mov='max', Lsat=10e-6, Isat=10.0, entry=None, bond=False, k1mov=False, tmax=200e-9, t_after=250e-6):
    ts = 25e-3 if pol > 0 else 35e-3          # 90 deg / 270 deg
    kV = 1.0 if mode == 'LN' else 2.0
    Ug = pol * kV * 1000 * U_SCALE / 1000.0
    if mode == 'LPE':
        coup = 'X1 GO 0 CWGE PARAMS: ts={}\nRcp GO GC 10\nCcp GC LT 9u'.format(ts)
    elif mode == 'NPE':
        coup = 'X1 GO 0 CWGE PARAMS: ts={}\nRcp GO GC 10\nCcp GC NT 9u'.format(ts)
    else:
        # L-N: generator return on the N terminal, held at the earth reference (a floating return does not converge
        # in ngspice here); this bounds the CM part of the L-N surge by 1 kV L-PE, below the 2 kV L-PE test
        coup = 'X1 GO NT CWGE PARAMS: ts={}\nCcp GO LT 18u\nRntg NT 0 1m'.format(ts)
    L0 = P['L40_L0'][0]; phs = L0 * Isat; k = (1 / Lsat - 1 / L0)
    triac = 'Rq LFI A1 0.05' if heater else 'Rq LFI A1 10Meg\nCq LFI A1 100p'
    k1 = 'Rk1 LF FANH 10m' if relay_closed else 'Ck1 LF FANH 1.5p\nRk1 LF FANH 1G'
    if tc == 'grounded':
        tcw = 'Ltp CH TJ1 1u\nLtn CH TJ2 1u\nKtc Ltp Ltn 0.95'
    else:
        tcw = f'Ltp TCW TJ1 1u\nLtn TCW TJ2 1u\nKtc Ltp Ltn 0.95\nCts TCW CH {Cts}\nRts TCW CH 1G'
    ent = ''
    if bond:                       # fix F2: deliberate single-point SELV GND -> PE bond (wire + lug to the chassis)
        ent += 'Lbond SG BB 0.5u\nRbond BB CH 0.05\n'
    if k1mov:                      # fix F3: TVR14431 (275 Vac) across the K1 COM-NO contact
        ent += f"Bk1m LF K1MX I = pwl(V(LF,K1MX), {cm.mov_pwl('RV1', 'max')})\nLk1m K1MX FANH 15n\n"
    if entry == 'mov_pe':          # fix F1: TVR14431 L-PE and N-PE at the mains inlet (off-board, on the chassis)
        ent += (f"Bpl J3L PLX I = pwl(V(J3L,PLX), {cm.mov_pwl('RV1', 'max')})\nLpl PLX CH 15n\n"
               f"Bpn NEUT PNX I = pwl(V(NEUT,PNX), {cm.mov_pwl('RV1', 'max')})\nLpn PNX CH 15n")
    elif entry == 'mov_gdt_pe':    # F1b: MOV L/N -> X, GDT X -> PE; GDT held at an ASSUMED 800 V dynamic sparkover
        gdt = '-1e4,-1e3, -900,-50, -800,-1e-3, -700,-1e-9, 0,0, 700,1e-9, 800,1e-3, 900,50, 1e4,1e3'
        ent += (f"Bpl J3L PLX I = pwl(V(J3L,PLX), {cm.mov_pwl('RV1', 'max')})\nLpl PLX GX 15n\n"
               f"Bpn NEUT PNX I = pwl(V(NEUT,PNX), {cm.mov_pwl('RV1', 'max')})\nLpn PNX GX 15n\n"
               f"Bgdt GX CH I = pwl(V(GX,CH), {gdt})\nCgdt GX CH 1p")
    return f"""surge earthed
{cwg(Ug)}
.model dled D(Is=1e-19 N=1.5 Rs=3)
.model dbr D(Is=1e-9 N=1.8 Rs=0.05 Cjo=50p TT=1u)
.model dclamp D(Is=1e-14 N=1 Rs=5)
Bm ML MN V = {VPK:.2f}*sin(2*pi*50*time)*(1-exp(-time/4m))
Rne MN 0 0.1
Rsrc ML M1 0.4
Lsrc M1 M2 0.8m
Ldl M2 LT 1.5m
Ldn MN NT 1.5m
{coup}
* cord L/N/PE 1 uH each; L-N coupling k 0.9 (PE coupling omitted: ngspice fails at the surge edge with a 3-way K)
Lcl LT J3L 1u
Lcn NT NEUT 1u
Lcp 0 CH 1u
Kc1 Lcl Lcn 0.9
Cwl J3L CH 30p
Cwn NEUT CH 30p
{ent}
Rf3 J3L LF 10m
{k1}
Cfan FANH NEUT 200p
Rfan FANH FX 600
Lfan FX NEUT 3
Cfch FANH CH 100p
Gphi 0 PHI LF LX 1
Cphi PHI 0 1
Rphi PHI 0 1e9
BL40 LF LX I = V(PHI)/{Lsat:.4g} - {k:.6g}*{phs:.6g}*tanh(V(PHI)/{phs:.6g})
RL40 LX LFI 0.1
CL40 LF LFI 10p
C40 LFI C40A 1u
Lc40 C40A C40B 20n
Rc40 C40B NEUT 10m
C1 LFI C1A 100n
Lc1 C1A NEUT 15n
Brv1 LFI RV1X I = pwl(V(LFI,RV1X), {cm.mov_pwl('RV1', mov)})
Lrv1 RV1X NEUT 15n
Crv1 LFI NEUT 370p
Brv3 LF RV3X I = pwl(V(LF,RV3X), {cm.mov_pwl('RV1', mov)})
Lrv3 RV3X NEUT 15n
Crv3 LF NEUT 370p
{triac}
Btvs LFI TVX I = pwl(V(LFI,TVX), {cm.mov_pwl('TVS440', 'max')})
Ltvs TVX A1 15n
Ctvs LFI A1 180p
R5 LFI SN 47
C4 SN A1 10n
R3 LFI MOC6 360
Rmoc MOC6 QG 1G
Cmoc MOC6 QG 1p
R2 QG A1 360
Lh A1 HX 2u
Rh HX NEUT 52.9
Chc1 A1 CH {Chc/2:.4g}
Chc2 NEUT CH {Chc/2:.4g}
Chs1 LFI HS 15p
Chs2 HS CH 5p
Chs3 HS SG 1p
Rhs HS CH 1G
Rf1 LFI PL 0.15
Ll1a PL AL 50u
Rl1ap PL AL 2k
Rl1a AL ALX 0.5
Ll1b NEUT AN 50u
Rl1bp NEUT AN 2k
Rl1b AN ANX 0.5
Cxh ALX ANX 1n
Rin ALX HIN 11
D1 HIN BP dbr
D2 ANX BP dbr
D3 BN HIN dbr
D4 BN ANX dbr
Cb BP BN 10u
Rld BP BN 13.7k
Cpa BP HP 10n
Cpb BN HP 10n
Cbar HP SG {Cbar}
Rbar HP SG 1G
R6 ALX ZL 33k
Dz1 ZL ZN dled
Dz2 ZN ZL dled
R7 ZN ANX 33k
Cio ZL SG 0.5p
Cdio MOC6 SG 1p
Ckc LF SG 2p
V33 V33 SG DC 3.3
Csp SG CH {Csp}
Rsp SG CH 1G
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
.options reltol=1e-3 abstol=1e-9 vntol=1e-4 itl4=200 method=gear rshunt=1e12
.tran {tmax:.3g} {ts + t_after:.6g} {ts - 20e-6:.6g} {tmax:.3g} uic
.end
""", ts


_TVS = json.load(open(os.path.join(ce.OLD, 'tvs_model.json')))['pts']
TVSPWL = ', '.join(f'{x:.4g},{y:.4g}' for x, y in zip(
    [-p[0] for p in _TVS[::-1] if p[0] > 0] + [0.0] + [p[0] for p in _TVS if p[0] > 0],
    [-p[1] for p in _TVS[::-1] if p[0] > 0] + [0.0] + [p[1] for p in _TVS if p[0] > 0]))


def measure(r, ts):
    t = r['time']; w = (t >= ts - 5e-6)
    tw = t[w]
    def v(a, b='0'):
        x = r[f'v({a.lower()})'][w]
        return x - (r[f'v({b.lower()})'][w] if b != '0' else 0)
    pk = lambda x: float(np.max(np.abs(x)))
    br = lambda n: r[f'{n}#branch'][w] if f'{n}#branch' in r else np.zeros_like(tw)
    o = {}
    o['V_HLK_barrier'] = pk(v('HP', 'SG'))
    o['V_K1_coil_contact'] = pk(v('LF', 'SG'))
    o['V_driver_iso'] = pk(v('MOC6', 'SG'))
    o['V_H11AA1_iso'] = pk(v('ZL', 'SG'))
    o['V_mains_SELV_max'] = max(pk(v(n, 'SG')) for n in ('LF', 'LFI', 'NEUT', 'ALX', 'ANX', 'A1', 'J3L'))
    o['V_heater_to_chassis'] = max(pk(v('A1', 'CH')), pk(v('NEUT', 'CH')), pk(v('HX', 'CH')))
    o['V_fan_to_frame'] = pk(v('FANH', 'CH'))
    o['V_wiring_to_chassis'] = max(pk(v('J3L', 'CH')), pk(v('NEUT', 'CH')), pk(v('LF', 'CH')))
    o['V_HS_tab'] = pk(v('LFI', 'HS'))
    o['V_HS_to_SELV'] = pk(v('HS', 'SG'))
    o['V_HS_to_mains_A1'] = pk(v('HS', 'A1'))
    o['V_SELV_to_chassis'] = pk(v('SG', 'CH'))
    o['V_triac'] = pk(v('LFI', 'A1'))
    o['V_K1_open'] = pk(v('LF', 'FANH'))
    o['V_LINE_FILT_N'] = pk(v('LFI', 'NEUT'))
    o['I_TVS_D220'] = pk(br('ltv1')); o['I_TVS_D221'] = pk(br('ltv2'))
    o['V_J20_SELV'] = max(pk(v('J20P', 'SG')), pk(v('J20N', 'SG')))
    o['I_ADS_AIN_mA'] = max(pk(br('lp1')), pk(br('lp2'))) * 1e3
    o['V_AIN_min'] = float(min(v('AIN0', 'SG').min(), v('AIN1', 'SG').min()))
    o['V_AIN_max'] = float(max(v('AIN0', 'SG').max(), v('AIN1', 'SG').max()))
    o['E_R220_mJ'] = float(np.trapezoid((v('J20P', 'TCFP')) ** 2 / 1e3, tw) * 1e3)
    o['P_R220_pk_W'] = float(np.max(v('J20P', 'TCFP') ** 2 / 1e3))
    o['V_probe_insulation'] = pk(v('TCW', 'CH')) if 'v(tcw)' in r else 0.0
    o['I_RV1'] = pk(br('lrv1')); o['I_RV3'] = pk(br('lrv3')); o['I_TVS_triac'] = pk(br('ltvs'))
    o['I_PE_cord'] = pk(br('lcp'))
    o['I_entry_LPE'] = pk(br('lpl')); o['I_entry_NPE'] = pk(br('lpn'))
    o['E_entry_J'] = float(np.trapezoid(np.abs(br('lpl') * v('J3L', 'PLX')), tw) + np.trapezoid(np.abs(br('lpn') * v('NEUT', 'PNX')), tw)) if 'v(plx)' in r else 0.0
    return o, tw, {'HLK': v('HP', 'SG'), 'K1c': v('LF', 'SG'), 'heater': v('A1', 'CH'), 'SG_CH': v('SG', 'CH'),
                   'ITVS': br('ltv1'), 'IADS': br('lp1')}


def run_case(**kw):
    """Try gear/trap and finer steps; return None if ngspice fails every time (recorded, not hidden)."""
    for tm, meth in ((200e-9, 'gear'), (100e-9, 'gear'), (200e-9, 'trap'), (50e-9, 'trap')):
        net, ts = netlist(tmax=tm, **kw)
        net = net.replace('method=gear', f'method={meth}')
        try:
            r = ce.run(net); break
        except ValueError:
            raise
        except Exception:
            continue
    else:
        return None
    return measure(r, ts) + (ts,)


def key(kw):
    return '|'.join(f'{k}={v}' for k, v in kw.items())


def block_main():
    rows = []
    for mode, pol, heater, relay, tc in itertools.product(('LPE', 'NPE'), (+1, -1), (False, True), (False, True), ('grounded', 'insulated')):
        kw = dict(mode=mode, pol=pol, heater=heater, relay_closed=relay, tc=tc)
        res = run_case(**kw)
        if res is None:
            rows.append({'case': key(kw), 'failed': True}); print(key(kw), 'NGSPICE FAILED'); continue
        o = res[0]
        rows.append({'case': key(kw), **o})
        print(key(kw), {k: round(o[k], 1) for k in ('V_HLK_barrier', 'V_K1_coil_contact', 'V_heater_to_chassis', 'I_TVS_D220', 'I_ADS_AIN_mA', 'V_SELV_to_chassis', 'V_probe_insulation', 'V_triac', 'V_K1_open')})
    ce.save('surge_LE_NE_main', rows)


def block_sweep():
    rows = []
    for tc, Cbar, Csp in itertools.product(('grounded', 'insulated'), (20e-12, 100e-12, 1e-9, 2.2e-9), (10e-12, 50e-12, 200e-12)):
        kw = dict(mode='LPE', pol=+1, heater=False, relay_closed=False, tc=tc, Cbar=Cbar, Csp=Csp)
        res = run_case(**kw)
        if res is None:
            rows.append({'case': key(kw), 'failed': True}); continue
        o = res[0]
        rows.append({'case': key(kw), 'tc': tc, 'Cbar_pF': Cbar * 1e12, 'Csp_pF': Csp * 1e12, **o})
        print(tc, Cbar, Csp, round(o['V_HLK_barrier']), round(o['V_K1_coil_contact']), round(o['I_ADS_AIN_mA'], 1), round(o['V_probe_insulation']), round(o['V_SELV_to_chassis']))
    for Chc in (100e-12, 1e-9):
        kw = dict(mode='LPE', pol=+1, heater=False, relay_closed=False, tc='grounded', Chc=Chc)
        res = run_case(**kw)
        if res is None:
            rows.append({'case': key(kw), 'failed': True}); continue
        o = res[0]
        rows.append({'case': key(kw), 'tc': 'grounded', 'Chc_pF': Chc * 1e12, **o})
    ce.save('surge_LE_sweep', rows)


def block_ln():
    rows = []
    for pol, heater, tc in itertools.product((+1, -1), (False, True), ('grounded', 'insulated')):
        kw = dict(mode='LN', pol=pol, heater=heater, relay_closed=False, tc=tc)
        res = run_case(**kw)
        if res is None:
            rows.append({'case': key(kw), 'failed': True}); print(key(kw), 'FAILED'); continue
        o = res[0]
        rows.append({'case': key(kw), **o})
        print(key(kw), round(o['V_triac']), round(o['V_K1_open']), round(o['V_HLK_barrier']), round(o['V_K1_coil_contact']), round(o['I_ADS_AIN_mA'], 2))
    ce.save('surge_LN_earthed', rows)


def block_fix():
    rows = []
    for entry, bond, tc, mode, Cbar in itertools.product((None, 'mov_pe', 'mov_gdt_pe'), (False, True), ('grounded', 'insulated'), ('LPE', 'NPE'), (20e-12, 1e-9)):
        if entry is None and not bond:
            continue                    # = main block
        kw = dict(mode=mode, pol=+1, heater=False, relay_closed=False, tc=tc, Cbar=Cbar, entry=entry, bond=bond)
        res = run_case(**kw)
        if res is None:
            rows.append({'case': key(kw), 'failed': True}); print(key(kw), 'FAILED'); continue
        o = res[0]
        rows.append({'case': key(kw), **o})
        print(key(kw), round(o['V_HLK_barrier']), round(o['V_K1_coil_contact']), round(o['V_heater_to_chassis']), round(o['I_ADS_AIN_mA'], 2), round(o['I_entry_LPE']), round(o['E_entry_J'], 2), round(o['V_probe_insulation']), flush=True)
    ce.save('surge_fix', rows)


def plot_ref():
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for tc in ('grounded', 'insulated'):
        o, tw, wv, ts = run_case(mode='LPE', pol=+1, heater=False, relay_closed=False, tc=tc)
        ax[0].plot((tw - ts) * 1e6, wv['HLK'], label=f'HLK barrier (primary–SELV), TC {tc}')
        ax[0].plot((tw - ts) * 1e6, wv['K1c'], '--', label=f'K1 COM–coil (SELV), TC {tc}')
        if tc == 'grounded':
            ax[1].plot((tw - ts) * 1e6, wv['ITVS'], label='D220 current (A)')
            ax[1].plot((tw - ts) * 1e6, wv['IADS'] * 1e3, label='ADS1115 AIN0 current (mA)')
    ax[0].axhline(1500 * np.sqrt(2), c='r', ls=':', label='K1 coil–contact 1500 Vac = 2121 Vpk')
    ax[0].axhline(2500 * np.sqrt(2), c='m', ls=':', label='HLK 2500 Vac = 3536 Vpk')
    ax[0].set_ylabel('V'); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
    ax[0].set_title('Surge +2 kV L–PE / 12 Ω at 90°, earthed chassis, C_bar 100 pF, C_SELV-PE 50 pF (ASM)', fontsize=9)
    ax[1].axhline(10, c='r', ls=':', label='ADS1115 10 mA'); ax[1].axhline(12, c='m', ls=':', label='PESD IPPM 12 A')
    ax[1].set_xlabel('t (µs)'); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(ce.PLOTS, 'surge_LPE_waveforms.png'), dpi=120); plt.close(fig)


if __name__ == '__main__':
    {'main': block_main, 'sweep': block_sweep, 'ln': block_ln, 'fix': block_fix, 'plot': plot_ref}[sys.argv[1]]()
