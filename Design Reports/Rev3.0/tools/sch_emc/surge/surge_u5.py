"""Run from a copy of sim/emc_tests/B_immunity_transients/ with this common.py (adds the Thinking TVS models).
agentHW 2026-11-21: surge 1 kV / 2 Ohm re-run for the stocked TVS (Thinking 1.5KE440CA-TKS) + RV3, and the U5 options.
Copy of scope B's sim_surge.py / common.py (campaign folder untouched); results -> results_u5.json here.
  part 1: D6 = 1.5KE440CA-TKS across Q1 (two curve corners, see common.py), RV3 = TVR14431 at LINE_FUSED-NEUT
  part 2: option 3 (600 V driver kept, breakover): VBO 600 / 650 / 700 V with D6 + RV3, Q1 loop inductance 100/300 nH (ASM)
"""
import itertools, json, os, sys
import numpy as np
import common as cm
import sim_surge as ss

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_u5.json')


def part1():
    sat_sets = [(20e-6, 20.0), (10e-6, 10.0), (5e-6, 6.0)]
    res = {}
    for label, tvs in (('D6 Thinking, ST-shape slope (18.2 Ohm)', 'TVSTK'), ('D6 Thinking, linear 56 Ohm bound', 'TVSTKL'),
                       ('reference: ST 1.5KE440CA as in the campaign', 'TVS440')):
        rows = []
        for pol, heater, mov, (Lsat, Isat) in itertools.product((+1, -1), (False, True), ('max', 'min'), sat_sets):
            m, *_ = ss.run_case(pol=pol, heater=heater, relay_closed=False, mov=mov, Lsat=Lsat, Isat=Isat, rv2=tvs,
                                extra=ss.RV3(mov))
            rows.append({'case': f"{'+' if pol > 0 else '-'}|heater {'on' if heater else 'off'}|MOV/TVS {mov}|L40 {Lsat*1e6:.0f}uH/{Isat:.0f}A", **m})
        w = lambda k, f='': max((r.get(k, 0), r['case']) for r in rows if f in r['case'])
        res[label] = {k: w(k, 'heater off' if k == 'V_triac_pk' else '') for k in
                      ('V_triac_pk', 'V_K1_open_contacts_pk', 'V_LINE_FILT_pk', 'V_LINE_FUSED_pk', 'I_RV2_pk', 'E_RV2_J',
                       'I_RV3_pk', 'E_RV3_J', 'I_RV1_pk', 'E_RV1_J', 'dVdt_triac_max_V_per_us', 'I2t_F3_A2s', 'V_bulk_pk')}
        res[label]['rows'] = rows
        print(label, {k: (round(v[0], 3), v[1]) for k, v in res[label].items() if k != 'rows'}, flush=True)
    return res


def part2():
    out = {}
    for vbo, Lq, pol in itertools.product((600, 650, 700), (100e-9, 300e-9), (+1, -1)):
        net, ts = ss.netlist(pol=pol, heater=False, mov='max', Lsat=5e-6, Isat=6.0, breakover=True, vbo=vbo, rv2='TVSTK',
                             extra=ss.RV3('max'), t_after=6e-3, tmax=50e-9)
        net = net.replace('Bq LFI A1 I = V(LFI,A1)', 'Bq qa A1 I = V(qa,A1)').replace('abs(V(LFI,A1))*(1e-7', 'abs(V(qa,A1))*(1e-7')
        net = net.replace('Cq LFI A1 100p', f'Cq LFI A1 100p\nLq LFI qa {Lq:.3g}\nRqd LFI qa 1k')
        r = cm.run_netlist(net)
        t = r['time']; w = t >= ts - 5e-6; tw = t[w] - ts
        v = lambda a, b: (r[f'v({a.lower()})'] - r[f'v({b.lower()})'])[w]
        iq = r['lq#branch'][w]
        ih = r['lh#branch'][w]
        imoc = v('LFI', 'moc6') / 360.0
        on = np.abs(ih) > 0.2
        dt = np.diff(tw)
        res = {'driver_fired': bool(np.max(r['v(sm)'][w]) > 0.5), 'Q1_latched': bool(np.max(r['v(sq)'][w]) > 0.5),
               'V_triac_pk': float(np.max(np.abs(v('LFI', 'A1')))), 'I_driver_pk_A': float(np.max(np.abs(imoc))),
               'I2t_driver_A2s': float(np.trapezoid(imoc ** 2, tw)),
               'I_Q1_pk_A': float(np.max(np.abs(iq))), 'Q1_dIdt_max_A_per_us': float(np.max(np.abs(np.gradient(iq, tw))) / 1e6),
               'heater_on_ms': float(np.sum(dt[on[:-1]]) * 1e3), 'I_heater_pk_A': float(np.max(np.abs(ih))),
               'heater_energy_J': float(np.trapezoid(ih ** 2 * cm.P['Rheater'][0], tw))}
        key = f"VBO {vbo} V | Lq {Lq*1e9:.0f} nH | {'+90' if pol > 0 else '-270'}"
        out[key] = res
        print(key, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in res.items()}, flush=True)
    return out


if __name__ == '__main__':
    for part in ('part1', 'part2'):
        if part in sys.argv:
            r = globals()[part]()
            json.dump(r, open(OUT.replace('.json', '_%s.json' % part), 'w', encoding='utf-8'), indent=1, default=float)
