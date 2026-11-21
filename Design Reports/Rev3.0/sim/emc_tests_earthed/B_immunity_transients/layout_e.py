"""Layout question 2026-11-21: where (if anywhere) the second TVR14431 goes, now that it cannot sit across LINE_FUSED-NEUT.
  a) no RV3;  b) TVR14431 across K1 COM-NO only;  c) reference: RV3 across LINE_FUSED-NEUT (no fan-side part);
  b471) as (b) with a 471-class disc (TVR14471 curve as proxy for TVR10471: lower leakage).
Design state: K1 = TE RZ03-1A4-D005 (coil-contact 5000 Vrms / 10 mm reinforced; open contact 1000 Vrms = 1414 Vpk),
U5 MOC3083X (800 V), D6 1.5KE440CA across Q1, no fan-side capacitor, no Y1, chassis earthed, no inlet device.
Fan ASSUMED as in fan_e.py.  Insulated-junction probe (recommended); SELV-PE bond (F2, 150 nH) present or absent.
Blocks (each a few minutes): python -X utf8 layout_e.py main a|b|c | spread | closed | heater | neg | b471
"""
import itertools, sys
import numpy as np
import common_e as ce
import surge_e as s

cm = ce.cm
# TVR14471 (DS TVR p.7 row: V1mA 470 (423-517), 300 Vac, Vc 775 V @ 50 A; curve p.24 digitised, top curve) -- in memory only
cm.P['RV14471'] = {'part': 'TVR14471', 'V1mA': (423, 470, 517), 'C_pF': 320}
cm.MOV_CURVE_MAX['RV14471'] = [(1.2e-6, 225), (1e-5, 289), (1e-4, 357), (5e-4, 405), (1e-2, 580), (0.1, 638), (1, 688), (10, 740),
                               (50, 781), (100, 817), (300, 886), (1000, 1009), (2000, 1213), (4500, 1618)]
FANS = {'nominal': (500.0, 6.0), 'high-current': (250.0, 3.0), 'low-current': (1000.0, 12.0)}


def build(opt, mode, pol, heater, relay_closed, Cwf, fan, bond, tmax):
    R, L = FANS[fan]
    net, ts = s.netlist(mode=mode, pol=pol, heater=heater, relay_closed=relay_closed, tc='insulated', Cbar=1e-9,
                        bond=bond, tmax=tmax)
    keep = []
    for ln in net.splitlines():
        if opt in ('a', 'b', 'b471') and (ln.startswith('Brv3') or ln.startswith('Lrv3') or ln.startswith('Crv3')):
            continue
        keep.append(ln)
    net = '\n'.join(keep)
    net = net.replace('Lbond SG BB 0.5u', 'Lbond SG BB 150n')
    net = net.replace('Ck1 LF FANH 1.5p', 'Ck1 LF FANH 1p').replace('Ckc LF SG 2p', 'Ckc LF SG 2p')
    net = net.replace('Rfan FANH FX 600', f'Rfan FANH FX {R}').replace('Lfan FX NEUT 3', f'Lfan FX NEUT {L}')
    net = net.replace('Cfch FANH CH 100p', f'Cfch FANH CH {Cwf}')
    if opt in ('b', 'b471'):
        curve = 'RV1' if opt == 'b' else 'RV14471'
        part = (f"Bk1m LF K1MX I = pwl(V(LF,K1MX), {cm.mov_pwl(curve, 'max')})\nLk1m K1MX FANH 15n\n"
                f"Ck1m LF FANH {cm.P[curve]['C_pF']}p\n")
        net = net.replace('.options', part + '.options', 1)
    return net, ts


def run(opt, mode='LPE', pol=+1, heater=False, relay_closed=False, Cwf=100e-12, fan='nominal', bond=True):
    for tm, meth in ((200e-9, 'gear'), (100e-9, 'gear'), (200e-9, 'trap'), (50e-9, 'trap')):
        net, ts = build(opt, mode, pol, heater, relay_closed, Cwf, fan, bond, tm)
        try:
            r = ce.run(net.replace('method=gear', f'method={meth}')); break
        except ValueError:
            raise
        except Exception:
            continue
    else:
        return None
    o, tw, wv = s.measure(r, ts)
    w = r['time'] >= ts - 5e-6; t = r['time'][w]
    v = lambda a, b: (r[f'v({a.lower()})'] - r[f'v({b.lower()})'])[w]
    pk = lambda x: float(np.max(np.abs(x)))
    o['V_LF_N'] = pk(v('LF', 'NEUT')); o['V_LF_CH'] = pk(v('LF', 'CH'))
    o['V_across_L40'] = pk(v('LF', 'LFI')); o['V_fan_winding'] = pk(v('FANH', 'NEUT')); o['V_fan_to_chassis'] = pk(v('FANH', 'CH'))
    o['V_D6'] = o['V_triac']
    o['E_RV1_J'] = float(np.trapezoid(np.abs(r['lrv1#branch'][w] * v('LFI', 'RV1X')), t))
    o['E_TVS_D6_J'] = float(np.trapezoid(np.abs(r['ltvs#branch'][w] * v('LFI', 'TVX')), t))
    o['I_F3_pk'] = pk(v('J3L', 'LF') / 10e-3); o['I2t_F3'] = float(np.trapezoid((v('J3L', 'LF') / 10e-3) ** 2, t))
    if 'lrv3#branch' in r:
        o['I_varistor_pk'] = pk(r['lrv3#branch'][w]); o['E_varistor_J'] = float(np.trapezoid(np.abs(r['lrv3#branch'][w] * v('LF', 'RV3X')), t))
    elif 'lk1m#branch' in r:
        o['I_varistor_pk'] = pk(r['lk1m#branch'][w]); o['E_varistor_J'] = float(np.trapezoid(np.abs(r['lk1m#branch'][w] * v('LF', 'K1MX')), t))
    else:
        o['I_varistor_pk'] = 0.0; o['E_varistor_J'] = 0.0
    return o


KEYS = ('V_K1_open', 'V_K1_coil_contact', 'V_LF_N', 'V_across_L40', 'V_fan_winding', 'V_fan_to_chassis', 'V_triac',
        'I_TVS_triac', 'E_TVS_D6_J', 'I_RV1', 'E_RV1_J', 'I_varistor_pk', 'E_varistor_J', 'I2t_F3')


def go(block, cases):
    R0 = ce.load().get('layout_rv3', {})
    rows = R0.get(block, [])
    for kw in cases:
        o = run(**kw)
        tag = '|'.join(f'{k}={v}' for k, v in kw.items())
        if o is None:
            rows.append({'case': tag, 'failed': True, **kw}); print(tag, 'FAILED', flush=True); continue
        rows.append({'case': tag, **kw, **{k: o[k] for k in KEYS}})
        print(tag, ' '.join(f'{k[2:]}={o[k]:.0f}' for k in ('V_K1_open', 'V_K1_coil_contact', 'V_LF_N', 'V_fan_winding', 'V_fan_to_chassis', 'V_triac')),
              f"Ivar={o['I_varistor_pk']:.1f} Evar={o['E_varistor_J']:.3f}", flush=True)
    R0[block] = rows
    ce.save('layout_rv3', R0)


if __name__ == '__main__':
    b = sys.argv[1]
    if b == 'main':
        opt = sys.argv[2]
        go(f'main_{opt}', [dict(opt=opt, mode=m, Cwf=c, bond=bd) for m, c, bd in itertools.product(('LN', 'LPE', 'NPE'), (20e-12, 100e-12, 500e-12), (True, False))])
    elif b == 'spread':
        go('spread', [dict(opt=o, mode=m, Cwf=500e-12, fan=f) for o, m, f in itertools.product(('a', 'b', 'c'), ('LN', 'LPE', 'NPE'), ('high-current', 'low-current'))])
    elif b == 'closed':
        go('closed', [dict(opt=o, mode=m, Cwf=c, relay_closed=True) for o, m, c in itertools.product(('a', 'b', 'c'), ('LN', 'LPE', 'NPE'), (20e-12, 500e-12))])
    elif b == 'heater':
        go('heater', [dict(opt=o, mode=m, Cwf=500e-12, heater=True) for o, m in itertools.product(('a', 'b', 'c'), ('LN', 'LPE', 'NPE'))])
    elif b == 'neg':
        go('neg', [dict(opt=o, mode=m, Cwf=500e-12, pol=-1) for o, m in itertools.product(('a', 'b', 'c'), ('LN', 'LPE', 'NPE'))])
    elif b == 'b471':
        go('b471', [dict(opt='b471', mode=m, Cwf=c) for m, c in itertools.product(('LN', 'LPE', 'NPE'), (20e-12, 500e-12))])
