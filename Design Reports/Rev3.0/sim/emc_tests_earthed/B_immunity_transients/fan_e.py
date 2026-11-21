"""Item 1 (review 2026-11-21): K1 open-contact stress and the fan-side part.

Fan data ASSUMED (no fan specified): small 230 V 50 Hz shaded-pole / AC axial fan, run current ~0.1 A, start ~0.15 A,
winding R 500 Ohm + L 6 H (|Z| 1.95 kOhm), spread R 250 Ohm / L 3 H (0.24 A) to R 1 kOhm / L 12 H (0.06 A);
200 pF across the winding; winding-to-frame (earthed chassis) capacitance C_wf 20 / 100 / 500 pF.
Options across the fan output (K1 NO -> NEUT): none; X2 10 / 47 / 100 nF; series RC 47R+10nF, 100R+47nF, 220R+100nF;
F3 = TVR14431 across the K1 contact (COM-NO).
Board state: committed earthed model (surge_e.py) with F2 bond (150 nH), no inlet device, heater off, K1 open.
Run in pieces:  python -X utf8 fan_e.py surge <option-index 0..7> | turnoff
"""
import itertools, json, sys
import numpy as np
import common_e as ce
import surge_e as s

cm = ce.cm
FANS = {'nominal': (500.0, 6.0), 'high-current': (250.0, 3.0), 'low-current': (1000.0, 12.0)}
OPTS = [('none', ''), ('X2 10nF', 'Cfp FANH NEUT 10n'), ('X2 47nF', 'Cfp FANH NEUT 47n'), ('X2 100nF', 'Cfp FANH NEUT 100n'),
        ('RC 47R+10nF', 'Rfp FANH RCX 47\nCfp RCX NEUT 10n'), ('RC 100R+47nF', 'Rfp FANH RCX 100\nCfp RCX NEUT 47n'),
        ('RC 220R+100nF', 'Rfp FANH RCX 220\nCfp RCX NEUT 100n'), ('F3 MOV across K1', 'K1MOV')]


def build(mode, opt, R, L, Cwf, tmax):
    k1mov = opt == 'K1MOV'
    net, ts = s.netlist(mode=mode, pol=+1, heater=False, relay_closed=False, tc='grounded', Cbar=1e-9, bond=True,
                        k1mov=k1mov, tmax=tmax)
    net = net.replace('Lbond SG BB 0.5u', 'Lbond SG BB 150n')
    net = net.replace('Rfan FANH FX 600', f'Rfan FANH FX {R}').replace('Lfan FX NEUT 3', f'Lfan FX NEUT {L}')
    net = net.replace('Cfch FANH CH 100p', f'Cfch FANH CH {Cwf}')
    if opt and not k1mov:
        net = net.replace('.options', opt + '\n.options', 1)
    return net, ts


def run(mode, opt, R, L, Cwf):
    for tm, meth in ((200e-9, 'gear'), (100e-9, 'gear'), (200e-9, 'trap'), (50e-9, 'trap')):
        net, ts = build(mode, opt, R, L, Cwf, tm)
        try:
            r = ce.run(net.replace('method=gear', f'method={meth}')); break
        except ValueError:
            raise
        except Exception:
            continue
    else:
        return None
    o, tw, wv = s.measure(r, ts)
    w = r['time'] >= ts - 5e-6
    if 'v(rcx)' in r:
        i = (r['v(fanh)'] - r['v(rcx)'])[w] / float(opt.split('\n')[0].split()[-1])
        o['I_part_pk'] = float(np.max(np.abs(i)))
        o['E_part_R_mJ'] = float(np.trapezoid(i ** 2 * float(opt.split('\n')[0].split()[-1]), r['time'][w]) * 1e3)
    o['V_fan_side_pk'] = float(np.max(np.abs((r['v(fanh)'] - r['v(neut)'])[w])))
    if 'lk1m#branch' in r:
        o['I_part_pk'] = float(np.max(np.abs(r['lk1m#branch'][w])))
    return o


def surge(idx):
    name, opt = OPTS[idx]
    rows = []
    cases = [(m, 'nominal', c) for m in ('LPE', 'NPE', 'LN') for c in (20e-12, 100e-12, 500e-12)] + \
            [(m, f, 500e-12) for m in ('LPE', 'NPE', 'LN') for f in ('high-current', 'low-current')]
    for mode, fan, Cwf in cases:
        R, L = FANS[fan]
        o = run(mode, opt, R, L, Cwf)
        if o is None:
            rows.append({'mode': mode, 'fan': fan, 'Cwf_pF': Cwf * 1e12, 'failed': True}); print(name, mode, fan, Cwf, 'FAILED', flush=True); continue
        rows.append({'mode': mode, 'fan': fan, 'Cwf_pF': Cwf * 1e12, **o})
        print(name, mode, fan, Cwf, round(o['V_K1_open']), round(o['V_K1_coil_contact']), round(o.get('I_part_pk', 0), 2), round(o['V_fan_side_pk']), flush=True)
    R0 = ce.load().get('fan_option_surge', {}); R0[name] = rows; ce.save('fan_option_surge', R0)


def turnoff():
    """K1 opening on the running fan: (a) current interrupted at its zero, (b) current chopped at its peak (low-current
    contacts often fail to hold an arc at 0.1 A).  No contact breakdown modelled: the result is the voltage the gap must
    withstand, or restrike at."""
    out = {}
    for (name, opt), fan in itertools.product(OPTS, FANS):
        R, L = FANS[fan]
        part = '' if opt in ('', 'K1MOV') else opt
        mov = (f"Bk1m LF K1MX I = pwl(V(LF,K1MX), {cm.mov_pwl('RV1', 'max')})\nLk1m K1MX FANH 15n") if opt == 'K1MOV' else ''
        res = {}
        # probe the steady-state current phase with K1 closed
        def net(topen):
            ctl = f'PWL(0 1 {topen} 1 {topen + 10e-9} 0)' if topen else 'DC 1'
            return f"""fan turnoff
Vm ML 0 SIN(0 {230*np.sqrt(2):.1f} 50)
Rsrc ML M1 0.4
Lsrc M1 LF 0.8m
Vk KC 0 {ctl}
Sk LF FANH KC 0 swk
.model swk sw(vt=0.5 vh=0.01 ron=10m roff=1e12)
Ck LF FANH 1.5p
Cfan FANH NEUT 200p
Rfan FANH FX {R}
Lfan FX NEUT {L}
Cwf FANH 0 100p
Rn NEUT 0 1m
{part}
{mov}
.options reltol=1e-4 method=gear
.tran {'1u' if topen else '10u'} {topen + 4e-3 if topen else 0.1} {topen - 1e-3 if topen else 0.06} {'0.2u' if topen else '2u'}
.end
"""
        r = ce.run(net(None)); t = r['time']; i = r['lfan#branch']
        w = t > 0.06
        tz = t[w][np.where(np.diff(np.sign(i[w])) != 0)[0][0]]
        tp = t[w][np.argmax(np.abs(i[w]))]
        res['I_run_pk_mA'] = float(np.max(np.abs(i[w])) * 1e3)
        for tag, topen in (('at current zero', tz), ('chopped at peak current', tp)):
            rr = ce.run(net(topen)); tt = rr['time']; ww = tt > topen
            vk = (rr['v(lf)'] - rr['v(fanh)'])[ww]
            vf = (rr['v(fanh)'] - rr['v(neut)'])[ww]
            # ring frequency from zero crossings of the fan-side voltage in the first 2 ms
            tt2 = tt[ww]; zc = tt2[np.where(np.diff(np.sign(vf)) != 0)[0]]
            f_ring = float(1 / (2 * np.median(np.diff(zc[:6])))) if len(zc) > 3 else None
            dv = np.gradient(vk, tt2)
            res[tag] = {'V_contact_pk': float(np.max(np.abs(vk))), 'f_ring_Hz': f_ring,
                        'dVdt_contact_max_V_per_us': float(np.max(np.abs(dv[:2000])) / 1e6)}
        out[f'{name}|{fan}'] = res
        print(name, fan, {k: (v if not isinstance(v, dict) else {kk: round(vv, 1) if vv else vv for kk, vv in v.items()}) for k, v in res.items()}, flush=True)
    # K1-open 50 Hz leakage through each option: only F3 conducts across the open contact (MOV leakage);
    # the X2/RC parts sit across the fan and see no source when K1 is open (contact capacitance 1.5 pF only)
    V = 230 * np.sqrt(2) * 1.1
    out['leak_K1_open'] = {'contact capacitance 1.5 pF (all options)': 2 * np.pi * 50 * 1.5e-12 * 253 * 1e6,
                           'F3 TVR14431 max-leakage curve at 358 Vpk (uA peak)': float(cm.mov_current('RV1', np.array([V]), 'max')[0] * 1e6),
                           'unit': 'uA'}
    out['reactive_K1_closed_mA'] = {n: 2 * np.pi * 50 * c * 230 * 1e3 for n, c in (('X2 10nF', 10e-9), ('X2 47nF', 47e-9), ('X2 100nF', 100e-9))}
    ce.save('fan_turnoff', out)
    print(out['leak_K1_open'], out['reactive_K1_closed_mA'])


if __name__ == '__main__':
    if sys.argv[1] == 'surge':
        surge(int(sys.argv[2]))
    else:
        turnoff()
