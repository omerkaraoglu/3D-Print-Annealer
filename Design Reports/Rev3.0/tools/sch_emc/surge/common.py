"""Shared data, device models and generator models for scope B (transient immunity).

Every number carries its source:
  STD   = read from BS EN 55014-2:2015 on disk (clause/table, PDF page)
  NRS   = NOT read from the standard (basic standard not on disk); public source cited
  DS    = component datasheet (file / document, page)
  SCH   = current schematic (netlist exported from the KiCad files by netlist_extract.py)
  PCB   = layout (Rev3.0_Design_Specification.md section / board file)
  ASM   = assumed, swept range given
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = r'C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/sim'
sys.path.insert(0, SIM)
from ngspice_helper import run_netlist  # noqa: E402,F401

PLOTS = os.path.join(HERE, 'plots')
os.makedirs(PLOTS, exist_ok=True)
RESULTS = os.path.join(HERE, 'results.json')


def save_results(section, data):
    """Merge one section into results.json (each script owns its sections)."""
    allr = {}
    if os.path.exists(RESULTS):
        with open(RESULTS, encoding='utf-8') as f:
            allr = json.load(f)
    allr[section] = data
    with open(RESULTS, 'w', encoding='utf-8') as f:
        json.dump(allr, f, indent=1, ensure_ascii=False, default=float)


def load_results():
    with open(RESULTS, encoding='utf-8') as f:
        return json.load(f)


# ----------------------------------------------------------------------------------------------
# Standard requirements (STD) -- BS EN 55014-2:2015 (identical to CISPR 14-2:2015)
# ----------------------------------------------------------------------------------------------
STD = {
    'category': {'value': 'IV', 'src': 'STD 4.3 (cat. II needs no clock > 15 MHz), 4.5, PDF p.15-16; ESP32 40 MHz crystal, SSD1963 PCLK 33 MHz'},
    'esd': {'air_kV': 8, 'contact_kV': 4, 'n': '10 + / 10 - per point', 'criterion': 'B',
            'src': 'STD 5.1 Table 1 PDF p.16; criterion 7.2.4 PDF p.23'},
    'eft_ac': {'kV': 1.0, 'tr_td_ns': '5/50', 'rep_kHz': 5, 'duration': '2 min each polarity', 'criterion': 'B',
               'src': 'STD 5.2 + Table 4 PDF p.16-17; 7.2.4 PDF p.23'},
    'eft_signal': {'kV': 0.5, 'cond': 'only ports with cables that can exceed 3 m', 'src': 'STD Table 2 PDF p.16'},
    'surge': {'LN_kV': 1.0, 'LN_ohm': 2, 'LE_kV': 2.0, 'LE_ohm': 12, 'LE_applicable': False,
              'pulses': '5 + at 90 deg, 5 - at 270 deg', 'criterion': 'B',
              'src': 'STD 5.6 Table 12 PDF p.20-21 (no L-E for products without provision for earth); 7.2.4 PDF p.23'},
    'dips': {'rows': [{'residual_pct': 0, 'dip_pct': 100, 'cycles_50Hz': 0.5},
                      {'residual_pct': 40, 'dip_pct': 60, 'cycles_50Hz': 10},
                      {'residual_pct': 70, 'dip_pct': 30, 'cycles_50Hz': 25}],
             'interruptions': 'not performed (5.7)', 'change_at': 'zero crossing', 'criterion': 'C',
             'src': 'STD 5.7 Table 13 PDF p.21; 7.2.4 PDF p.23'},
}

# ----------------------------------------------------------------------------------------------
# Component data (DS / SCH / ASM)
# ----------------------------------------------------------------------------------------------
P = {
    # mains input chain (SCH: J3 LINE -> F3 -> LINE_FUSED -> L40 -> LINE_FILT; C40, C1, RV1 LINE_FILT-NEUT)
    'F3_I2t_min': (10.2, 'DS Datasheets/Normal FUSE.pdf p.2: fast-acting 400 % -> 10 ms min: (4*8 A)^2*10 ms = 10.2 A2s pre-arc lower bound (no I2t published)'),
    'F1_I2t': (3.5, 'Reomax TBC 1 A time-lag 5x20, Datasheets/Slow Blow Fuse Series.pdf p.3 (BOM part STC1A250V: same maker; TBC table used, ASM)'),
    'L40_L0': (100e-6, 'DS RC1415U-101K 100 uH +-10 % (spec sec.2)'),
    'L40_R': (0.1, 'DS 100 mOhm (spec sec.2)'),
    'L40_Lsat': ((5e-6, 10e-6, 20e-6), 'ASM: drum core, fully saturated inductance (air-core) 5-20 uH, swept'),
    'L40_Isat': ((6.0, 10.0, 20.0), 'ASM: saturation knee 6-20 A swept (5 A is the thermal rating; no Isat published)'),
    'C40': (1.0e-6, 'SCH C40 C42P2105KBSC400 1 uF X2'),
    'C1': (0.1e-6, 'SCH C1 C42P2104M6SC361 100 nF X2'),
    'C4': (10e-9, 'SCH C4 10 nF X2 (snubber)'), 'R5': (47.0, 'SCH R5 47 Ohm 2 W'),
    'R2': (360.0, 'SCH R2 360 Ohm gate-A1'), 'R3': (360.0, 'SCH R3 360 Ohm A2-MOC'),
    'Rheater': (230.0**2/1000.0, 'SCH R1 heater 1 kW at 230 V'),
    'Lheater': (2e-6, 'ASM heater element + leads 2 uH'),
    'Lcord': (1.0e-6, 'ASM 1 m of mains cord between CDN and J3 (~1 uH)'),
    # MOVs (DS Datasheets/TVR10391KSY.pdf, Thinking TVR series 2014.05)
    'RV1': {'part': 'TVR14431KSU15Y', 'V1mA': (387, 430, 473), 'Vac': 275, 'Vc': 710, 'Ip': 50, 'Imax_8_20': 4500,
            'Wmax_J_10_1000': 115, 'P_W': 0.6, 'C_pF': 370,
            'src': 'DS TVR p.7 (printed 14) 14 mm table row TVR14431; V-I curve p.24 (printed 31), digitised'},
    'RV2': {'part': 'TVR10561KFARY', 'V1mA': (504, 560, 616), 'Vac': 350, 'Vc': 930, 'Ip': 25, 'Imax_8_20': 2500,
            'Wmax_J_10_1000': 70, 'P_W': 0.4, 'C_pF': 120,
            'src': 'DS TVR p.6 (printed 13) 10 mm table row TVR10561; V-I curve p.23 (printed 30), digitised'},
    # semiconductors
    'BTA24': {'VDRM': 800, 'VDSM': 900, 'dVdt_min_Vus': 500, 'IGT_max_mA': 35, 'VGT_max': 1.3, 'VGD_min': 0.2,
              'ITSM_50Hz': 250, 'I2t': 340, 'dIdt': 50, 'Rd_mOhm': 16, 'Viso_kV_rms': 2.5,
              'src': 'DS ST DS2112 Rev 12 (Sept 2021) Table 1-2 p.2, Table 4-5 p.3'},
    'MOC3052': {'VDRM': 600, 'ITSM_A': 1.0, 'dVdt_Vus': 1000, 'IFT_max_mA': 10, 'IF_max_mA': 60, 'VIOTM_Vpk': 6000,
                'src': 'DS onsemi MOC3052M/D Rev 3 (2019) p.2-3 (BOM part is Isocom MOC3052X, same JEDEC type: ASM equal ratings)'},
    'H11AA1': {'IF_max_mA': 40, 'VF_typ': 1.2, 'VF_max_10mA': 1.5, 'CTR_min': 0.20, 'Viso_Vrms': 5000,
               'src': 'DS Vishay H11AA1 doc 83608 Rev 2.0 (2026) p.1-2 (BOM part Isocom H11AA1X; Isocom copies list +-50 mA, the lower Vishay value is used)'},
    'PESD5V0S1BA': {'VRWM': 5, 'VBR': (5.5, 9.5), 'VCL_1A': 10, 'VCL_12A': 14, 'IPPM': 12, 'Cd_pF': 35,
                    'ESD_contact_kV': 30, 'src': 'DS Nexperia PESD5V0S1BA product data sheet 26 Apr 2024, Table 5 p.3, Table 6 p.4'},
    'ESP32': {'VDD_max': 3.6, 'VIL_frac': 0.25, 'VIH_frac': 0.75, 'latchup_mA': 200, 'HBM_V': 2000,
              'gpio33_reset': 'oe=0, ie=0 (no pull) at and after reset', 'EN_VIL_nRST': 0.6, 'tRST_us': 50,
              'BOD_V': 2.43,
              'src': 'DS Espressif ESP32 datasheet v5.3 Table 5-1 p.51, DC table p.52, reliability p.53 (latch-up +-200 mA JESD78), '
                     'IO_MUX At Reset p.69-70, Table 2-4 p.19; WROOM-32E datasheet v2.1 p.28 (VDD33 3.6 V), p.39 (EN RC 10k/1uF), p.46 (HBM 2 kV); '
                     'BOD 2.43 V = ESP-IDF Kconfig ESP_BROWNOUT_DET_LVL_SEL_0 (default), not a datasheet value'},
    'GT911': {'VIO_max': 3.47, 'HBM_kV': 2, 'src': 'DS Goodix GT911 Rev.10 (2015) 10.1 p.22'},
    'CTP_module': {'air_kV': 8, 'contact_kV': 4, 'src': 'DS SAT070AT40D21 (Datasheets/) p.23 CTP spec item 13'},
    'LCM': {'esd': '+-2 kV, 150 pF/330 Ohm', 'src': 'DS SAT070AT40D21 p.15 reliability table'},
    'ADS1115': {'AIN_max': 'VDD+0.3', 'I_in_max_mA': 10, 'SDA_max': 5.5,
                'src': 'DS TI ADS1115 Datasheets/ADS1115.pdf 5.1 Absolute Maximum Ratings p.4'},
    'HLK10M05': {'Vin_ac': (85, 264), 'Vin_dc': (70, 350), 'inrush_A': 34, 'eff_min': 0.80, 'iso_Vac': (3000, 2500),
                 'load_vs_vdc': '70 Vdc -> 70 % load, 110 Vdc -> 100 % load', 'ext_MOV_recommended': '10D561K',
                 'ext_fuse': '1 A slow', 'esd_claim': 'IEC 61000-4-2 level 4 8/15 kV', 'surge_claim': 'none published',
                 'src': 'DS Hi-Link 10M series V1.5 (2020-05-22): 5.1 p.2, 5.3 p.4, Fig.6 p.9, 8 p.10, 9.2 p.11 (isolation 3000 Vac p.1 vs 2500 Vac p.11)'},
    'TPS562201': {'UVLO_off': (3.3, 3.4), 'UVLO_on': (3.8, 4.3), 'toff_min_ns': (220, 310), 'fsw': 580e3, 'tss_ms': 1.0,
                  'src': 'DS TI SLVSD91D p.5 (Electrical characteristics)'},
    'K1': {'open_contacts_Vac': 750, 'coil_contact_Vac': 1500, 'src': 'DS Tianbo HJR-3FF p.2 characteristics data'},
    'R6R7': {'R': 33e3, 'P_W': 1.0, 'Vmax': 500, 'src': 'SCH/BOM value field "33k 1W 500V" (CFR01SJ0333A10); pulse rating not published: ASM'},
    'MOC_LED_R4': (120.0, 'SCH R4'),
}

# Digitised V-I curves (max clamping voltage curves; DS TVR p.23/24, printed pages 30/31) (I in A, V in V)
MOV_CURVE_MAX = {
    # <= 0.5 mA: 'max leakage current' branch; >= 2 mA: 'max clamping voltage' branch (both digitised, digit.py)
    'RV1': [(1.2e-6, 199), (1e-5, 261), (1e-4, 322), (5e-4, 367), (2e-3, 491), (1e-2, 530), (0.1, 580), (1, 638),
            (10, 676), (50, 710), (100, 757), (300, 817), (1000, 918), (2000, 1109), (4500, 1492)],
    'RV2': [(1.2e-6, 266), (1e-5, 335), (1e-4, 421), (5e-4, 479), (2e-3, 643), (1e-2, 708), (0.1, 770), (1, 821),
            (10, 900), (25, 938), (50, 964), (100, 1014), (300, 1180), (1000, 1431), (2500, 1760)],
}


# Candidate clamps across the triac (review round 2026-11-18)
P['RV14391'] = {'part': 'TVR14391K', 'V1mA': (351, 390, 429), 'Vac': 250, 'Vc': 650, 'Ip': 50, 'Imax_8_20': 4500,
                'C_pF': 390, 'src': 'DS TVR p.7 row TVR14391; curve p.24 digitised (rank 3 from top)'}
MOV_CURVE_MAX['RV14391'] = [(1.2e-6, 184), (1e-5, 240), (1e-4, 297), (5e-4, 332), (2e-3, 443), (1e-2, 478), (0.1, 530),
                            (1, 575), (10, 618), (50, 646), (100, 682), (300, 737), (1000, 839), (2000, 1014), (4500, 1340)]
P['TVS440'] = {'part': '1.5KE440CA', 'V1mA': (418, 440, 462), 'VRM': 376, 'IRM_uA': 1, 'C_pF': 180,
               'src': 'DS SGS-Thomson 1.5KExx Transil p.3 (datasheets/ST_SGS_1.5KExx_Transil.pdf): IRM 1 uA @ VRM 376 V, VBR 418/440/462 V @ 1 mA, '
                      'VCL 603 V @ 3.5 A (10/1000 us), 776 V @ 13 A (8/20 us), C 360 pF/2 (bidirectional)'}
# max corner: VBR max at 1 mA; the 10/1000 us point (603 V @ 3.5 A) is used below 13 A (conservative: higher than the 8/20 line)
MOV_CURVE_MAX['TVS440'] = [(1e-6, 376), (1e-3, 462), (3.5, 603), (13, 776), (100, 2360)]   # last point: 8/20 slope extrapolated (not reached)


def mov_curve(name, corner='max'):
    """Return (V, I) arrays of the MOV curve for the tolerance corner.
    max = datasheet 'max clamping voltage' curve (V1mA at +10 %); nom/min scale the voltage axis by
    V1mA_nom/V1mA_max and V1mA_min/V1mA_max (ASM: shape preserved inside the tolerance band)."""
    pts = np.array(MOV_CURVE_MAX[name])
    I, V = pts[:, 0], pts[:, 1].astype(float)
    vmin, vnom, vmax = P[name]['V1mA']
    k = {'max': 1.0, 'nom': vnom / vmax, 'min': vmin / vmax}[corner]
    return V * k, I


def mov_pwl(name, corner='max', npts=40):
    """ngspice pwl() argument list for a symmetric MOV (current vs voltage), log-interpolated."""
    V, I = mov_curve(name, corner)
    lgI = np.linspace(np.log10(I[0]), np.log10(I[-1] * 3), npts)
    # extrapolate the last segment slope for currents above the curve end
    Vi = np.interp(lgI, np.log10(I), V)
    s = (V[-1] - V[-2]) / (np.log10(I[-1]) - np.log10(I[-2]))
    Vi = np.where(lgI > np.log10(I[-1]), V[-1] + s * (lgI - np.log10(I[-1])), Vi)
    Ii = 10 ** lgI
    xs = list(-Vi[::-1]) + [0.0] + list(Vi)
    ys = list(-Ii[::-1]) + [0.0] + list(Ii)
    return ', '.join(f'{x:.4g},{y:.4g}' for x, y in zip(xs, ys))


def mov_current(name, v, corner='max'):
    V, I = mov_curve(name, corner)
    av = np.abs(v)
    return np.sign(v) * 10 ** np.interp(av, V, np.log10(I), left=-12, right=np.log10(I[-1]))


# ----------------------------------------------------------------------------------------------
# Generators (NRS)
# ----------------------------------------------------------------------------------------------
NRS = {
    'cwg': {'Voc_front_us': 1.2, 'Voc_dur_us': 50, 'Isc_front_us': 8, 'Isc_dur_us': 20, 'Zeff_ohm': 2,
            'tol': 'front V +-30 %, duration V +-20 %, front I +-20 %, duration I +-20 % (commonly quoted, NOT verified against a primary source)',
            'coupling_LL': '18 uF',
            'src': 'NOT read from the standard. TI SLVA711 (June 2015) p.7-9: 1.2/50 us open-circuit, 8/20 us short-circuit, 2 Ohm, 18 uF L-L coupling capacitor; definitions T1=1.67(T90-T30) (V), 1.25(T90-T10) (I) as in IEC 61000-4-5 (from memory, NRS)'},
    'eft': {'tr_ns': 5, 'td_ns': 50, 'tol': '+-30 % into 50 Ohm', 'Zs_ohm': 50, 'Cblock_nF': 10, 'burst_ms': 15,
            'period_ms': 300, 'f_kHz': 5, 'Ccoupling_nF': 33, 'level_1kV_Isc_A': 20,
            'src': 'NOT read from the standard. IS 14700-4-4:2008 (= IEC 61000-4-4:2004; EN 55014-2 cites the 2012 edition) clause 6.1.1 p.11 and 6.2.1 p.13; TI SLVA711 Table 2 p.4 (1 kV -> 20 A short-circuit, i.e. 50 Ohm, 1 kV open circuit)'},
    'esd': {'C_pF': 150, 'R_ohm': 330, 'Ip_A_per_kV': 3.75, 'I30_A_per_kV': 2.0, 'I60_A_per_kV': 1.0, 'tr_ns': (0.7, 1.0),
            'tol': 'Ip +-15 % (2008: +-15 %), I30/I60 +-30 %, tr 0.8 ns +-25 % (2008)',
            'src': 'NOT read from the standard. IS 14700-4-2:2008 (= IEC 61000-4-2:2001) Table 2 p.11 (7.5 A / 0.7-1 ns / 4 A / 2 A at 2 kV); TI SLVA711 p.2 (150 pF, 330 Ohm); '
                   '2008-edition tolerances from In Compliance Magazine / ESDA "A look into generator waveforms" (web)'},
    'dips': {'tr_us': (1, 5), 'Zout': '< 0.4 + j0.25 Ohm', 'sequence': '3 dips, >= 10 s apart',
             'src': 'NOT read from the standard. IS 14700-4-11:2008 (= IEC 61000-4-11:2004, the edition EN 55014-2 cites) Table 4 p.13, 8.2.1 p.16'},
    'esd_points': 'only points accessible in normal use (maintenance-only points excluded); contact to conductive, air to insulating surfaces; charge removal on ungrounded EUT (470 kOhm bleeder) -- '
                  'IS 14700-4-2:2008 (= IEC 61000-4-2:2001) 8.3.1 p.17, 5 p.12, 7.2.2 p.14 (NRS)',
}


# ESD gun network (fitted in validate_generators.py; parameters stored there, imported here)
def esd_gun_subckt(name='ESDGUN', V=4000.0, pars=None):
    """Two-branch ESD generator network: main 150 pF/330 Ohm + fast tip branch.
    Nodes: tip gnd.  Capacitors start charged (use .tran ... uic)."""
    p = pars or ESD_PARS
    return f"""
.subckt {name} tip gnd
Cm m1 gnd {p['Cm']:.4g} IC={V}
Rm m1 m2 {p['Rm']:.4g}
Lm m2 tip {p['Lm']:.4g}
Cs s1 gnd {p['Cs']:.4g} IC={V}
Rs s1 s2 {p['Rs']:.4g}
Ls s2 tip {p['Ls']:.4g}
.ends
"""


ESD_PARS = {'Cm': 150e-12, 'Rm': 330.0, 'Lm': 1.0e-6, 'Cs': 4e-12, 'Rs': 20.0, 'Ls': 20e-9}   # overwritten by fit
_esd_fit = os.path.join(HERE, 'esd_gun_fit.json')
if os.path.exists(_esd_fit):
    ESD_PARS.update(json.load(open(_esd_fit)))

CWG_PARS = {'Cc': 10e-6, 'Rs1': 20.0, 'Rm': 0.8, 'Lr': 9e-6, 'Rs2': 26.0}   # overwritten by fit
_cwg_fit = os.path.join(HERE, 'cwg_fit.json')
if os.path.exists(_cwg_fit):
    CWG_PARS.update(json.load(open(_cwg_fit)))


def cwg_subckt(name='CWG', U=1000.0, pars=None):
    """Combination-wave generator (TI SLVA711 Fig.6 topology): Cc charged to U, Rs1 across Cc,
    Rm + Lr in series, Rs2 across the output.  Output nodes: out gnd.  Switch closes at t = ts (param)."""
    p = pars or CWG_PARS
    return f"""
.subckt {name} out gnd PARAMS: ts=0
Cc c1 gnd {p['Cc']:.5g} IC={U}
Sw c1 c2 ctl gnd swmod
Vctl ctl gnd PWL(0 0 {{ts}} 0 {{ts+1n}} 1)
Rs1 c2 gnd {p['Rs1']:.5g}
Rm c2 c3 {p['Rm']:.5g}
Lr c3 out {p['Lr']:.5g}
Rs2 out gnd {p['Rs2']:.5g}
.model swmod sw(vt=0.5 vh=0.01 ron=1m roff=1e12)
.ends
"""


def front_time_V(t, v):
    """IEC-style front time T1 = 1.67 (T90 - T30) and duration (virtual origin to 50 % on tail)."""
    pk = np.max(v); ip = np.argmax(v)
    t30 = np.interp(0.3 * pk, v[:ip + 1], t[:ip + 1]); t90 = np.interp(0.9 * pk, v[:ip + 1], t[:ip + 1])
    T1 = 1.67 * (t90 - t30); t0 = t30 - 0.3 * T1
    tail = np.where(v[ip:] < 0.5 * pk)[0]
    t50 = t[ip + tail[0]] if len(tail) else np.nan
    return T1, t50 - t0, pk


def front_time_I(t, i):
    pk = np.max(i); ip = np.argmax(i)
    t10 = np.interp(0.1 * pk, i[:ip + 1], t[:ip + 1]); t90 = np.interp(0.9 * pk, i[:ip + 1], t[:ip + 1])
    T1 = 1.25 * (t90 - t10); t0 = t10 - 0.1 * T1
    tail = np.where(i[ip:] < 0.5 * pk)[0]
    t50 = t[ip + tail[0]] if len(tail) else np.nan
    return T1, t50 - t0, pk


def verdict(value, limit, kind='max'):
    """PASS / MARGINAL (<20 % margin) / FAIL for a stress 'value' against a rating 'limit'."""
    if kind == 'max':
        margin = (limit - value) / limit
    else:  # value must exceed limit
        margin = (value - limit) / limit
    v = 'FAIL' if margin < 0 else ('MARGINAL' if margin < 0.2 else 'PASS')
    return v, margin


# ---- agentHW 2026-11-21: Thinking 1.5KE440CA-TKS (the stocked part), DS Thinking 1.5KE Series 2025.01 p.4:
# VRWM 376 V, IR 1 uA, VBR 418-462 V @ 1 mA, VC 602 V @ Ipp 2.5 A (10/1000 us). No 8/20 point published.
# Corner 'shape': ST's incremental slope above the 10/1000 point (776-603)/(13-3.5) = 18.2 Ohm (ST DS p.3) applied from 602 V @ 2.5 A
# Corner 'lin'  : straight line through (1 mA, 462 V) and (2.5 A, 602 V) -> 56 Ohm, continued (conservative bound)
P['TVSTK'] = dict(P['TVS440']); P['TVSTK']['part'] = '1.5KE440CA-TKS (Thinking)'; P['TVSTK']['src'] = 'DS Thinking 1.5KE Series 2025.01 p.4'
MOV_CURVE_MAX['TVSTK'] = [(1e-6, 376), (1e-3, 462), (2.5, 602), (13, 602 + 18.2 * 10.5), (100, 602 + 18.2 * 97.5)]
P['TVSTKL'] = dict(P['TVSTK'])
MOV_CURVE_MAX['TVSTKL'] = [(1e-6, 376), (1e-3, 462), (2.5, 602), (13, 602 + 56 * 10.5), (100, 602 + 56 * 97.5)]
