"""Collect the verdict table of report_section.md from results.json (every number in the table comes from here).
Run after validate_generators.py, sim_surge.py, sim_surge.py --proposal, sim_eft.py, firmware_zcd_model.py,
sim_dips.py, sim_esd.py.   python -X utf8 make_summary.py
"""
import json
import numpy as np
import common as cm

R = cm.load_results()
rows = []


def row(test, clause, part, worst, limit, unit, kind='max', note='', verdict=None):
    if verdict is None:
        v, m = cm.verdict(worst, limit, kind)
    else:
        v, m = verdict, ((limit - worst) / limit if kind == 'max' else (worst - limit) / limit) if limit else None
    rows.append({'test': test, 'clause': clause, 'part': part, 'worst': worst, 'limit': limit, 'unit': unit,
                 'margin_pct': None if m is None else round(100 * m, 1), 'verdict': v, 'note': note})


S = 'EN 55014-2 5.6 Table 12, PDF p.20-21 (crit. B 7.2.4 p.23)'
sv = R['surge']['verdicts']
row('Surge 1 kV L-N', S, 'BTA24 Q1 off-state (VDRM 800 V)', sv['BTA24 off-state voltage']['value'], 800, 'V', note='vs VDSM 900 V (10 ms, non-repetitive): ' + f"{(900 - sv['BTA24 off-state voltage']['value']) / 9:.1f} %")
row('Surge 1 kV L-N', S, 'MOC3052 U5 (VDRM 600 V)', sv['MOC3052 off-state voltage']['value'], 600, 'V')
row('Surge 1 kV L-N', S, 'K1 open contacts (750 Vac 1 min = 1061 Vpk)', sv['K1 open-contact voltage']['value'], 750 * np.sqrt(2), 'V', note='no impulse rating published')
row('Surge 1 kV L-N', S, 'BTA24 dV/dt (500 V/us)', sv['BTA24 dV/dt']['value'], 500, 'V/us')
row('Surge 1 kV L-N', S, 'RV1 TVR14431 current (4500 A; ~1.2 kA for 10 pulses @20 us, DS p.18)', sv['RV1 peak current']['value'], 1200, 'A')
row('Surge 1 kV L-N', S, 'RV1 energy (115 J)', sv['RV1 energy']['value'], 115, 'J')
row('Surge 1 kV L-N', S, 'F3 8 A I2t (pre-arc >= 10.2 A2s)', sv['F3 I2t']['value'], 10.2, 'A2s', note='fuse does not open')
row('Surge 1 kV L-N', S, 'F1 1 A T I2t (3.5 A2s)', sv['F1 I2t']['value'], 3.5, 'A2s', note='fuse does not open')
row('Surge 1 kV L-N', S, 'H11AA1 LED current (40 mA)', sv['H11AA1 LED current']['value'], 40, 'mA')
row('Surge 1 kV L-N', S, 'R6/R7 33k 1 W (500 V)', sv['R6/R7 voltage']['value'], 500, 'V')
vend = R['surge_proposals']['HLK vendor reference circuit (10D561K, no L40/C40)']
ours = R['surge']['psu_sweep']
ratio = max(o['V_bulk_pk'] / v['V_bulk_pk'] for o, v in zip(ours, vend))
row('Surge 1 kV L-N', S, 'HLK-10M05 bulk (black box): ours / vendor reference circuit', ratio, 1.0, 'ratio',
    note=f"ours {min(o['V_bulk_pk'] for o in ours):.0f}-{max(o['V_bulk_pk'] for o in ours):.0f} V, vendor ref {min(v['V_bulk_pk'] for v in vend):.0f}-{max(v['V_bulk_pk'] for v in vend):.0f} V",
    verdict='NOT SIMULABLE (abs.); lower than vendor ref.')
SP = R['surge_proposals']
def prop(name, key):
    return [v for k, v in SP.items() if k.startswith(name)][0]
for name, label in (('P-S1 alone', 'P-S1 alone (800 V driver, RV2 unchanged)'), ('P-S3 alone', 'P-S3 alone (RV2 -> TVR14431)'),
                    ('P-S2b + P-S3', 'P-S1+P-S2b+P-S3'), ('P-S4', 'P-S1+P-S4 (RV2 -> 1.5KE440CA)'), ('P-S2b + P-S4', 'P-S1+P-S2b+P-S4'),
                    ('info: RV2 -> TVR14391', 'P-S1 + RV2 -> TVR14391 (250 Vac, info)')):
    p = prop(name, None)
    vt = p['V_triac_pk_heater_off'][0]
    row('Surge, ' + label, S, 'Q1 BTA24 off-state (VDRM 800 V)', vt, 800, 'V', note=f"vs VDSM 900 V: {(900 - vt) / 9:.1f} %; case {p['V_triac_pk_heater_off'][1]}")
    if name == 'P-S1 alone':
        row('Surge, ' + label, S, 'U5 MOC3052 as is (VDRM 600 V)', vt, 600, 'V')
    row('Surge, ' + label, S, '800 V driver off-state (VDRM 800 V)', vt, 800, 'V')
    if p['I_RV2_pk'][0] > 0.05:
        row('Surge, ' + label, S, 'triac clamp current / energy', p['I_RV2_pk'][0], 13 if 'S4' in name else 1200, 'A',
            note=f"E {p['E_RV2_J'][0]:.3f} J; limit {'13 A 8/20 (1.5KE440CA)' if 'S4' in name else '~1.2 kA, 10 pulses'}")
p = prop('P-S2b:', None)
row('Surge, P-S2b', S, 'K1 open contacts', p['V_K1_open_pk'][0], 750 * np.sqrt(2), 'V', note=f"RV3 {p['I_RV3_pk'][0]:.0f} A / {p['E_RV3_J'][0]:.2f} J")
# continuous-voltage checks of the triac clamp candidates at 230 V + 10 % = 253 Vac (358 Vpk)
row('Continuous check 253 Vac', 'mains tolerance (ASM 230 V +10 %)', '1.5KE440CA VRM 376 V (IRM 1 uA)', 253 * np.sqrt(2), 376, 'Vpk')
row('Continuous check 253 Vac', 'mains tolerance (ASM 230 V +10 %)', 'TVR14391 max 250 Vac', 253, 250, 'Vac')
row('Continuous check 253 Vac', 'mains tolerance (ASM 230 V +10 %)', 'TVR14431 max 275 Vac', 253, 275, 'Vac')
BO = R.get('surge_breakover', {})
for k, v in BO.items():
    row('Surge breakover: behavioural model, NOT a validated result', S, k, v['V_triac_pk'], 0, 'V triac pk', verdict='ARGUMENT (model inconclusive)',
        note=f"driver latched {v['moc_fired']}, Q1 latched {v['q1_latched']}, I_driver {v['I_driver_pk_A']:.3f} A, heater pk {v['I_heater_pk_A']:.1f} A for {v['heater_on_ms']:.3f} ms, {v['heater_energy_J']:.3f} J")

E = 'EN 55014-2 5.2 Table 4, PDF p.16-17 (crit. B)'
eft = R['eft']; w = eft['worst']
n_false = len(eft['zcd_false_edge_cases']); n_tot = len(eft['cases'])
row('EFT 1 kV CM mains', E, 'ZCD node false edges (U6 VT- 1.14 / VT+ 1.5 V)', n_false, 0, f'of {n_tot} corners', verdict='MARGINAL (functional)',
    note=f"pulse width <= {w['ZC_false_pulse_width_ns']:.0f} ns; firmware: +{max(v['burst']['error_pct_of_full'] for v in R['eft_firmware']['current_firmware'].values()):.1f} % of full power, no firing at duty 0")
row('EFT 1 kV CM mains', E, 'U6 input (VI max 6.5 V)', w['V_ZC_max'], 6.5, 'V', note='< 60 ns, < 1 nC')
pe = eft['proposal_P_E1_1nF_on_ZCD_node']
row('EFT, proposal P-E1 (1 nF on ZCD node)', E, 'ZCD node, transistor off: min vs VT- 1.14 V', pe['worst_off_min'], 1.14, 'V', kind='min')
row('EFT, proposal P-E1', E, 'ZCD node, transistor on: max vs VT+ 1.5 V', pe['worst_on_max'], 1.5, 'V')
row('EFT 1 kV CM mains', E, 'BTA24 gate-A1 (VGD min 0.2 V)', w['V_GA1_pk'], 0.2, 'V', note=f"triac {w['V_triac_pk']:.0f} V / {w['dVdt_triac_V_per_us']:.0f} V/us for ns; Q(Cj) ~ {eft['triac_worst']['Q_Cj_nC']:.1f}-4 nC")
row('EFT 1 kV CM mains', E, 'ESP32 EN (VIL_nRST 0.6 V)', w.get('V_EN_dev_mV', eft['EN_worst_mV']) / 1e3, 3.3 - 0.6, 'V')
row('EFT 1 kV CM mains', E, 'Barrier / K1 coil-contact (2121 Vpk)', eft['K1_coil_contact_worst'], 1500 * np.sqrt(2), 'V')
row('EFT TC lead (info, Table 2 n/a)', E, 'TC reading error (1 conversion per burst)', eft['tc_error']['avg_error_degC_worst_conversion'], 0.5, 'degC')

D = 'EN 55014-2 5.7 Table 13, PDF p.21 (crit. C)'
for k, v in R['dips']['summary'].items():
    row(f'Dip {k}', D, 'ESP32 3V3 (BOD 2.43 V), Cb >= 22 uF', v['min_3V3_Cb22_Voff70_5.5W'], 2.43, 'V', kind='min',
        note=f"resets in {v['resets_in_cases']}/{v['n_cases']} swept corners (Cb 10 uF only); reset -> TRIG floats, heater off, program restarts cold")

Z = 'EN 55014-2 5.1 Table 1, PDF p.16 (crit. B)'
e1 = R['esd']['E1_worst']
row('ESD 4 kV contact, TC probe', Z, 'D220 TVS current (IPPM 12 A 8/20; 30 kV IEC)', e1['I_TVS_pk_A'], 12, 'A')
row('ESD 4 kV contact, TC probe', Z, 'ADS1115 AIN (GND-0.3 V)', -e1['V_AIN0_min'], 0.3, 'V', note='pin current 7 uA vs 10 mA')
row('ESD 4 kV contact, TC probe', Z, 'Barrier SELV-mains (relay coil-contact 2121 Vpk)', e1['V_barrier_pk'], 1500 * np.sqrt(2), 'V', note='C_bar 20 pF/C_env 10 pF; 2.3 kV at 100 pF/30 pF')
E1 = R['esd']['E1_tc_probe_contact_4kV']
yb = max(d['V_barrier_pk'] for d in E1 if d['Cbar_pF'] >= 999)
CB = R.get('esd_barrier_vs_Cbar')
if CB:
    for k, v in CB['crossing_Cbar_pF'].items():
        if 'relay' in k:
            row('ESD E1: C_bar threshold', Z, k, v if v is not None else float('nan'), 0, 'pF (C_bar above this passes)', verdict='threshold')
row('ESD, proposal P-D1 (Y1 1 nF SELV GND-N)', Z, 'Barrier SELV-mains', yb, 1500 * np.sqrt(2), 'V')
row('ESD 8 kV air / 4 kV contact, steel sheet', Z, 'Barrier SELV-mains', R['esd']['E2_worst']['V_barrier_pk'], 1500 * np.sqrt(2), 'V')
row('ESD 8 kV air, glass over touch', Z, 'GT911 / CTP (maker: +-8 kV air on 0.7 mm cover)', R['esd']['E3_stack_ratio']['C_per_area_ratio_ours_over_ctp'], 1.0, 'coupling ratio',
    verdict='NOT SIMULABLE (bounded by comparison)')

cm.save_results('verdict_table', rows)
for r in rows:
    print(f"{r['test'][:34]:34s} | {r['part'][:52]:52s} | {r['worst']:.4g} / {r['limit']:.4g} {r['unit']} | {r['margin_pct']} % | {r['verdict']}")
