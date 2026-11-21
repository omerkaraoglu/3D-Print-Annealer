"""Extra earthed-case checks: (1) the recommended fix set F1b (MOV+GDT L/N-PE at the inlet) + F2 (SELV-PE bond)
+ F3 (MOV across the K1 contact) under L-PE and N-PE surge, both polarities, heater/K1 states; (2) 50 Hz thermocouple
input common mode in normal operation with the SELV-PE bond.   python -X utf8 extra_e.py fixset | static
"""
import itertools, sys
import numpy as np
import common_e as ce
import surge_e as s


def fixset():
    rows = []
    for mode, pol, heater, relay, tc in itertools.product(('LPE', 'NPE'), (+1, -1), (False, True), (False, True), ('grounded', 'insulated')):
        if relay and heater:
            continue
        kw = dict(mode=mode, pol=pol, heater=heater, relay_closed=relay, tc=tc, Cbar=1e-9, entry='mov_gdt_pe', bond=True, k1mov=True)
        res = s.run_case(**kw)
        if res is None:
            rows.append({'case': s.key(kw), 'failed': True}); print(s.key(kw), 'FAILED', flush=True); continue
        o = res[0]; rows.append({'case': s.key(kw), **o})
        print(s.key(kw), round(o['V_K1_open']), round(o['V_K1_coil_contact']), round(o['V_HLK_barrier']), round(o['V_heater_to_chassis']), round(o['I_ADS_AIN_mA'], 3), round(o['V_triac']), flush=True)
    ce.save('surge_fixset_F1b_F2_F3', rows)


def static():
    out = {}
    for tc in ('grounded', 'insulated'):
        net, ts = s.netlist(mode='LPE', pol=1, tc=tc, t_after=20e-3, Cbar=1e-9, bond=True)
        net = net.replace(f"{ts - 20e-6:.6g} 2e-07 uic", "0.005 2e-07 uic")
        net = net.replace("Vctl ctl 0 PWL(0 0 {ts} 0 {ts+1n} 1)", "Vctl ctl 0 DC 0")
        r = ce.run(net); t = r['time']; w = t > 0.02
        a0 = r['v(ain0)'] - r['v(sg)']
        out[f'{tc}|Cbar 1000p|bond'] = {'AIN0_min': float(a0[w].min()), 'AIN0_max': float(a0[w].max()),
                                         'I_bond_pk_uA': float(np.max(np.abs(r['lbond#branch'][w])) * 1e6),
                                         'SELV_chassis_pk': float(np.max(np.abs((r['v(sg)'] - r['v(ch)'])[w])))}
        print(tc, out[f'{tc}|Cbar 1000p|bond'], flush=True)
    R = ce.load().get('static_50Hz_tc_bias', {}); R.update(out); ce.save('static_50Hz_tc_bias', R)


def routeb():
    """Route B: no inlet device; F2 bond + F3 MOV across K1 (K1 coil-contact handled by a reinforced relay, rating only)."""
    rows = []
    for mode, pol, heater, tc in itertools.product(('LPE', 'NPE'), (+1, -1), (False, True), ('grounded',)):
        kw = dict(mode=mode, pol=pol, heater=heater, relay_closed=False, tc=tc, Cbar=1e-9, bond=True, k1mov=True)
        res = s.run_case(**kw)
        if res is None:
            rows.append({'case': s.key(kw), 'failed': True}); continue
        o = res[0]; rows.append({'case': s.key(kw), **o})
        print(s.key(kw), round(o['V_K1_open']), round(o['V_K1_coil_contact']), round(o['V_HLK_barrier']), round(o['V_heater_to_chassis']), round(o['V_wiring_to_chassis']), round(o['V_fan_to_frame']), round(o['I_ADS_AIN_mA'], 3), flush=True)
    ce.save('surge_routeB_F2_F3', rows)


if __name__ == '__main__':
    {'fixset': fixset, 'static': static, 'routeb': routeb}[sys.argv[1]]()
