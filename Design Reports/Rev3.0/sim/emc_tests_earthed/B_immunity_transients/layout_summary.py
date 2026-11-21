"""Summarise layout_rv3 runs per option -> results.json['layout_rv3_summary'].  python -X utf8 layout_summary.py"""
import numpy as np
import common_e as ce
R = ce.load()['layout_rv3']
rows = [r for blk in R.values() for r in blk if not r.get('failed')]
nf = sum(1 for blk in R.values() for r in blk if r.get('failed'))
LIM = {'V_K1_open': 1000 * np.sqrt(2), 'V_K1_coil_contact': 5000 * np.sqrt(2), 'V_LF_N': 3500, 'V_triac': 800}
out = {}
for opt in ('a', 'b', 'c', 'b471'):
    rr = [r for r in rows if r['opt'] == opt]
    d = {'n': len(rr)}
    for k in ('V_K1_open', 'V_K1_coil_contact', 'V_LF_N', 'V_across_L40', 'V_fan_winding', 'V_fan_to_chassis', 'V_triac', 'I_TVS_triac', 'E_TVS_D6_J', 'I_RV1', 'E_RV1_J', 'I_varistor_pk', 'E_varistor_J', 'I2t_F3'):
        m = max(rr, key=lambda r: r[k])
        d[k] = {'max': m[k], 'case': m['case']}
        if k in LIM:
            d[k]['margin_pct'] = (LIM[k] - m[k]) / LIM[k] * 100
    for c in (20e-12, 100e-12, 500e-12):
        q = [r['V_K1_open'] for r in rr if abs(r.get('Cwf', 1e-10) - c) < 1e-15]
        if q: d[f'K1_open_max_Cwf_{c*1e12:.0f}pF'] = max(q)
    out[opt] = d
    print(opt, d['n'], {k: (round(v['max'], 3), round(v.get('margin_pct', 0), 1)) for k, v in d.items() if isinstance(v, dict)}, {k: round(v) for k, v in d.items() if k.startswith('K1_open_max')})
out['failed_runs'] = nf
ce.save('layout_rv3_summary', out)
print('failed', nf)
