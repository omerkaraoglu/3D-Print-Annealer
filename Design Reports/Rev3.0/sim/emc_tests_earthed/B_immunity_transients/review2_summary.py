"""Collect the 2026-11-21 review answers (items 1-3) into results.json['review2'].  python -X utf8 review2_summary.py"""
import numpy as np
import common_e as ce

R = ce.load()
fo = R['fan_option_surge']; to = R['fan_turnoff']
item1 = {}
for k, rows in fo.items():
    ok = [r for r in rows if not r.get('failed')]
    by = lambda m: max(r['V_K1_open'] for r in ok if r['mode'] == m)
    t = {f: to[f'{k}|{f}'] for f in ('nominal', 'high-current', 'low-current')}
    item1[k] = {'K1_open_LPE': by('LPE'), 'K1_open_NPE': by('NPE'), 'K1_open_LN': by('LN'),
                'K1_open_max': max(r['V_K1_open'] for r in ok), 'margin_pct_vs_1061Vpk': (750 * np.sqrt(2) - max(r['V_K1_open'] for r in ok)) / (750 * np.sqrt(2)) * 100,
                'fan_winding_surge_pk': max(r['V_fan_side_pk'] for r in ok), 'K1_coil_contact_max': max(r['V_K1_coil_contact'] for r in ok),
                'part_current_pk_A': max(r.get('I_part_pk', 0) for r in ok), 'R_energy_mJ': max(r.get('E_part_R_mJ', 0) for r in ok),
                'turnoff_at_zero_Vpk': max(t[f]['at current zero']['V_contact_pk'] for f in t),
                'turnoff_chopped_Vpk_range': [min(t[f]['chopped at peak current']['V_contact_pk'] for f in t), max(t[f]['chopped at peak current']['V_contact_pk'] for f in t)],
                'n_cases': len(ok)}
item2 = {'stress_coil_contact_F2_no_inlet': {k: v['K1_coil_contact_max'] for k, v in item1.items()},
         'limits_Vpk': {'HJR-3FF 1500 Vac 1 min (only published figure)': 1500 * np.sqrt(2),
                        'reinforced relay 4 kVrms 1 min (public relay datasheets, NOT READ FROM THE STANDARD)': 4000 * np.sqrt(2),
                        'reinforced relay 6 kV 1.2/50 impulse (TE/Schrack 50.x public datasheet, NOT READ FROM THE STANDARD)': 6000,
                        'IEC 60664-1 reinforced for 2.5 kV OVC II = 4 kV impulse (from memory, NOT READ FROM THE STANDARD)': 4000}}
item2['margins_pct'] = {opt: {lim: (lv - st) / lv * 100 for lim, lv in item2['limits_Vpk'].items()} for opt, st in item2['stress_coil_contact_F2_no_inlet'].items() if opt in ('X2 47nF', 'none', 'F3 MOV across K1')}
item3 = {'esd_worst': {k: max(r[k] for r in R['panel_esd']) for k in ('I_bond_pk', 'I_pads_pk', 'I_fpc_tft_pk', 'I_fpc_ctp_pk', 'V_frame_vs_SELV_pk', 'V_barrier_pk')},
         'esd_Lb50': {k: max(r[k] for r in R['panel_esd'] if r['Lb_nH'] == 50) for k in ('I_fpc_tft_pk', 'I_fpc_ctp_pk', 'V_frame_vs_SELV_pk')},
         'surge_worst': {k: max(r[k] for r in R['panel_surge'] if not r.get('failed')) for k in ('I_bond_pk', 'I_pads_pk', 'I_fpc_tft_pk', 'I_fpc_ctp_pk', 'V_frame_vs_SELV_pk', 'V_SELV_vs_chassis_pk')},
         'static': R['panel_static_50Hz_tc']}
ce.save('review2', {'item1': item1, 'item2': item2, 'item3': item3})
import json; print(json.dumps({'item1': {k: {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in item1.items()}, 'item2': item2['margins_pct'], 'item3': {k: v for k, v in item3.items() if k != 'static'}}, indent=0, default=lambda x: round(float(x), 2)))
