"""Verdict table, earthed chassis (this folder) next to the unearthed campaign (committed folder, read-only).
python -X utf8 summary_e.py
"""
import json, os
import numpy as np
import common_e as ce

R = ce.load()
OLDR = json.load(open(os.path.join(ce.OLD, 'results.json'), encoding='utf-8'))
rows = []
VPK = lambda vac: vac * np.sqrt(2)


def add(test, part, worst, limit, unit, unearthed='', note='', kind='max', verdict=None):
    v, m = ce.verdict(worst, limit, kind) if verdict is None else (verdict, None)
    if verdict is None:
        m = round(100 * m, 1)
    rows.append({'test': test, 'part': part, 'worst': round(float(worst), 3), 'limit': round(float(limit), 3), 'unit': unit,
                 'margin_pct': m, 'verdict': v, 'unearthed': unearthed, 'note': note})


def mx(rows_, key, filt=lambda r: True):
    rr = [r for r in rows_ if not r.get('failed') and filt(r)]
    return max(r[key] for r in rr) if rr else float('nan')


M = R['surge_LE_NE_main']
nf = sum(1 for r in M if r.get('failed'))
for tc in ('grounded', 'insulated'):
    f = lambda r, tc=tc: f'tc={tc}' in r['case']
    T = f'Surge 2 kV L/N-PE, TC {tc}'
    add(T, 'K1 coil-contact (1500 Vac = 2121 Vpk)', mx(M, 'V_K1_coil_contact', f), VPK(1500), 'V', 'n/a (L-E not applied)')
    add(T, 'HLK-10M05 barrier (2500 Vac = 3536 Vpk)', mx(M, 'V_HLK_barrier', f), VPK(2500), 'V')
    add(T, '800 V driver isolation (FOD4218 class 5000 Vrms)', mx(M, 'V_driver_iso', f), VPK(5000), 'V')
    add(T, 'H11AA1 isolation (5000 Vrms)', mx(M, 'V_H11AA1_iso', f), VPK(5000), 'V')
    add(T, 'K1.1-coil pads 3.52 mm (~4 kV impulse, IEC 60664-1 F.2 NRS)', mx(M, 'V_K1_coil_contact', f), 4000, 'V')
    add(T, 'mains-SELV 6.4 mm creepage (~7 kV impulse NRS)', mx(M, 'V_mains_SELV_max', f), 7000, 'V')
    add(T, 'ADS1115 AIN current (10 mA)', mx(M, 'I_ADS_AIN_mA', f), 10, 'mA')
    add(T, 'ADS1115 AIN voltage (VDD+0.3 = 3.6 V)', mx(M, 'V_AIN_max', f), 3.6, 'V')
    add(T, 'D220/D221 (IPPM 12 A)', max(mx(M, 'I_TVS_D220', f), mx(M, 'I_TVS_D221', f)), 12, 'A')
    if tc == 'insulated':
        add(T, 'TC probe insulation wire-sheath (rating unknown: 1.5 kV impulse ASM)', mx(M, 'V_probe_insulation', f), 1500, 'V')
f = lambda r: True
T = 'Surge 2 kV L/N-PE (off-board)'
add(T, 'heater element to chassis (needs >= 2.5 kV impulse, cat. II NRS)', mx(M, 'V_heater_to_chassis'), 2500, 'V')
add(T, 'wiring to chassis', mx(M, 'V_wiring_to_chassis'), 2500, 'V')
add(T, 'fan winding to frame', mx(M, 'V_fan_to_frame'), 2500, 'V')
add(T, 'HS1 insulated tab (2.5 kVrms = 3536 Vpk)', mx(M, 'V_HS_tab'), VPK(2500), 'V')
add(T, 'HS1 pins to SELV, 6.4 mm', mx(M, 'V_HS_to_SELV'), 7000, 'V')
add(T, 'HS1 pins to mains, 2.5 mm (~3.5 kV NRS)', mx(M, 'V_HS_to_mains_A1'), 3500, 'V')
add(T, 'Q1 / 800 V driver off-state', mx(M, 'V_triac'), 800, 'V', unearthed='L-N: 606 V')
add(T, 'K1 open contact (1061 Vpk)', mx(M, 'V_K1_open'), VPK(750), 'V', unearthed='L-N: 773 V')

S = R.get('static_50Hz_tc_bias', {})
for k, v in S.items():
    add('Normal operation 50 Hz (no surge)', f'TC input common mode vs SELV, {k}', v['AIN0_max'], 3.6, 'V', note=f"min {v['AIN0_min']:.2f} V (GND-0.3 = -0.3 V); clamp current {v.get('I_AIN_pk_uA', 0):.1f} uA; bond current {v.get('I_bond_pk_uA', 0):.0f} uA",
        verdict=('FAIL' if (v['AIN0_min'] < -0.3 or v['AIN0_max'] > 3.6) else 'PASS'))

LN = R.get('surge_LN_earthed', [])
if LN:
    T = 'Surge 1 kV L-N, earthed'
    add(T, 'Q1 / 800 V driver off-state', mx(LN, 'V_triac'), 800, 'V', unearthed='606 V (P-S1+P-S4)')
    add(T, 'K1 open contact', mx(LN, 'V_K1_open'), VPK(750), 'V', unearthed='1162 V (773 with RV3)')
    add(T, 'K1 coil-contact', mx(LN, 'V_K1_coil_contact'), VPK(1500), 'V')
    add(T, 'ADS1115 AIN current', mx(LN, 'I_ADS_AIN_mA'), 10, 'mA')

FX = R.get('surge_fix', [])
for name, filt in (('F2 SELV-PE bond only', lambda r: 'entry=None' in r['case'] and 'bond=True' in r['case']),
                   ('F1 MOV L/N-PE at inlet (no bond)', lambda r: 'entry=mov_pe' in r['case'] and 'bond=False' in r['case']),
                   ('F1 MOV L/N-PE + F2 bond', lambda r: 'entry=mov_pe' in r['case'] and 'bond=True' in r['case']),
                   ('F1b MOV+GDT(800 V held) L/N-PE + F2 bond', lambda r: 'entry=mov_gdt_pe' in r['case'] and 'bond=True' in r['case']),
                   ('F1b MOV+GDT(800 V held), no bond', lambda r: 'entry=mov_gdt_pe' in r['case'] and 'bond=False' in r['case'])):
    T = f'Surge 2 kV L/N-PE + {name}'
    add(T, 'K1 coil-contact (2121 Vpk)', mx(FX, 'V_K1_coil_contact', filt), VPK(1500), 'V')
    add(T, 'HLK barrier (3536 Vpk)', mx(FX, 'V_HLK_barrier', filt), VPK(2500), 'V')
    add(T, 'heater/wiring to chassis (2.5 kV)', max(mx(FX, 'V_heater_to_chassis', filt), mx(FX, 'V_wiring_to_chassis', filt)), 2500, 'V')
    add(T, 'ADS1115 AIN current (10 mA)', mx(FX, 'I_ADS_AIN_mA', filt), 10, 'mA')
    add(T, 'ADS1115 AIN voltage (3.6 V)', mx(FX, 'V_AIN_max', filt), 3.6, 'V')
    add(T, 'TC probe insulation (insulated junction)', mx(FX, 'V_probe_insulation', filt), 1500, 'V')
    if 'MOV' in name:
        add(T, 'inlet MOV current (TVR14431, ~1.2 kA/10 pulses)', mx(FX, 'I_entry_LPE', filt), 1200, 'A', note=f"energy {mx(FX, 'E_entry_J', filt):.2f} J of 115 J")

FS = R.get('surge_fixset_F1b_F2_F3', [])
if FS:
    T = 'Surge 2 kV L/N-PE, recommended set F1b+F2+F3 (all states)'
    add(T, 'K1 open contact (1061 Vpk)', mx(FS, 'V_K1_open'), VPK(750), 'V', unearthed='773 V (L-N)')
    add(T, 'K1 coil-contact (2121 Vpk)', mx(FS, 'V_K1_coil_contact'), VPK(1500), 'V')
    add(T, 'HLK barrier (3536 Vpk)', mx(FS, 'V_HLK_barrier'), VPK(2500), 'V')
    add(T, 'heater/wiring/fan to chassis (2.5 kV)', max(mx(FS, 'V_heater_to_chassis'), mx(FS, 'V_wiring_to_chassis'), mx(FS, 'V_fan_to_frame')), 2500, 'V')
    add(T, 'Q1 / 800 V driver', mx(FS, 'V_triac'), 800, 'V')
    add(T, 'ADS1115 AIN current (10 mA)', mx(FS, 'I_ADS_AIN_mA'), 10, 'mA')
    add(T, 'ADS1115 AIN voltage (3.6 V)', mx(FS, 'V_AIN_max'), 3.6, 'V')
    add(T, 'TC probe insulation', mx(FS, 'V_probe_insulation'), 1500, 'V')
    add(T, 'inlet MOV (TVR14431)', mx(FS, 'I_entry_LPE'), 1200, 'A')
E = R.get('eft_earthed', {}).get('summary', {})
for k, v in E.items():
    T = f'EFT 1 kV L+N+PE, {k}'
    add(T, 'ZCD false edges (1 nF fitted)', v['false_edges'], 0, f"of {v['n']}", verdict='PASS' if v['false_edges'] == 0 else 'FAIL', unearthed='0 with 1 nF')
    add(T, 'U6 input (6.5 V)', v['ZC_abs_max'], 6.5, 'V')
    add(T, 'Q1 gate-A1 (VGD 0.2 V)', v['GA1_max'], 0.2, 'V', unearthed='0.153 V')
    add(T, 'TC input vs SELV (VDD+0.3 / GND-0.3)', max(v['TCFP_max'], -v['TCFP_min']), 0.3, 'V', note='limit shown for the negative excursion')
    add(T, 'TC reading error (0.5 degC)', v['TC_err_degC_worst_conversion'], 0.5, 'degC', unearthed='0.18 degC')
    add(T, 'ESP32 EN (mV)', v['EN_max_mV'], 2700, 'mV')
    add(T, 'K1 coil-contact transient', v['K1_coil_contact_max'], VPK(1500), 'V', unearthed='549 V')

Z = R.get('esd_earthed', {}).get('summary', {})
for k, v in Z.items():
    T = f'ESD to earthed chassis/ring/sheet, {k}'
    add(T, 'barrier SELV-mains (2121 Vpk)', v['V_barrier_pk'], VPK(1500), 'V', unearthed='E1 3.98 kV (C_bar 20 pF)')
    add(T, 'ADS1115 AIN (GND-0.3 V)', -v['V_AIN_min'], 0.3, 'V', unearthed='-0.296 V')
    add(T, 'D220 (12 A)', v['I_TVS_pk'], 12, 'A', unearthed='4.6 A')
    if 'insulated' in k:
        add(T, 'probe insulation', v['V_probe_ins_pk'], 1500, 'V')

ce.save('verdict_table_earthed', rows)
for r in rows:
    print(f"{r['test'][:46]:46s} | {r['part'][:56]:56s} | {r['worst']:.4g}/{r['limit']:.4g} {r['unit']} | {r['margin_pct']} | {r['verdict']} | {r['unearthed']}")
print('failed ngspice runs in main block:', nf)
