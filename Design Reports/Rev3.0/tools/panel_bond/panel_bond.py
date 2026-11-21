"""Panel bond, step 3: stack-ups, finger evaluation, contact sets, Formex openings, insulation check,
forces.  Reads out/board_pads.json (board_extract.py) and out/finger_model.json (finger_model.py),
writes results.json next to this script.  Every number in the proposal traces to a key in results.json;
every input carries its source in the 'inputs' block.

Run: python -X utf8 panel_bond.py
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
OFF = 20.0  # local = abs - 20

# ----------------------------------------------------------------------------------------------
# inputs (value, source)
# ----------------------------------------------------------------------------------------------
IN = {
    # frame v2 stack
    'v2_shelf_front_Z': (4.60, 'Rev3.0_Frame_Design.md s1 Z table; Frame_v2_params standoff/sheet_t'),
    'v2_formex_t_modelled': (0.40, 'Frame_v2_params sheet_t; Frame_Design s2'),
    'formex_GK10_t': (0.25, 'Frame_Design s8 q2 (GK-10 is 0.25)'),
    'formex_GK17_t': (0.43, 'Frame_Design s8 q2 (GK-17 is 0.43)'),
    'formex_t_tol': (0.03, 'assumed (sheet thickness tolerance; no source)'),
    'shelf_Z_tol': (0.10, 'assumed = GF-D50 boss-top tolerance +-0.1 [P]; v2 doc gives only ISO 20457 TG5'),
    'v2_gasket_gap_wc': (0.25, 'derived from Frame_Design s6: gasket 1.0 at 30 % = 0.30 compression; WC of LCM 0.3 + CTP 0.1 + seat 0.1 + sheet 0.05 = 0.55 -> up to 0.25 mm gap'),
    'v2_gasket_force_nom_N': (165.0, 'Frame_Design s5.4 (0.07 MPa at 30 %)'),
    'v2_gasket_force_max_N': (591.0, 'Frame_Design s5.4'),
    'v2_gasket_comp_nom_mm': (0.30, 'Frame_Design s1.1 (30 % of 1.0)'),
    # glass front stack
    'gf_boss_to_datumA': (13.42, 'GlassFront_Design s7.2 / GF-D50 (boss tops 13.42 behind A)'),
    'gf_lip_height': (1.00, 'GlassFront_Design s7.2 / s8.1 (lip 1.00 +-0.03)'),
    'gf_glass_t': (3.00, 'GlassFront params glass_t (default 3.0 +-0.2)'),
    'gf_loca_t': (0.30, 'GlassFront params t_opt (0.30 +-0.03)'),
    'panel_t': (5.32, 'GlassFront params panel_t; Frame_Design s2 (LCM 3.34 +-0.3 + CTP 1.98)'),
    'gf_panel_back_Z_nom': (5.80, 'GlassFront_Design s7.2 (panel back -5.80, floats -5.08 .. -6.52)'),
    'gf_backstop_gap_wc': ([0.08, 1.52], 'GlassFront params checks.backstop_gap_wc (3.0 glass)'),
    'tol_boss': (0.10, 'GF-D50 boss tops +-0.1 [P] (GlassFront_Design s8.1)'),
    'tol_lip': (0.03, 'GlassFront_Design s8.1 lip 1.00 +-0.03'),
    'tol_flush_wc': (0.11, 'GlassFront_Design s7.5 glass front vs lip top WC'),
    'tol_flush_rss': (0.06, 'GlassFront_Design s7.5 RSS'),
    'tol_glass': (0.20, 'GlassFront_Design s8.2 (3.0 +-0.2)'),
    'tol_loca': (0.03, 'GlassFront_Design s8.3 (0.30 +-0.03)'),
    'tol_lcm': (0.30, 'SAT070 datasheet p.16 side view 3.34 +-0.3'),
    'tol_ctp': (0.10, 'Frame_Design s6 tolerance notes (CTP stack +-0.1)'),
    'tol_panel_flat': (0.05, 'assumed (panel back flatness at a finger; datasheet silent)'),
    'tol_pcb_bow': (0.10, 'assumed (local bow of the screwed 1.6 mm board at a pad)'),
    'solder_offset': (0.03, 'assumed: hand-solder joint 0.05 under the base minus 0.02 mask recess of the bare pad'),
    'tol_solder': (0.05, 'assumed'),
    # finger (Laird LT17BH0731, Datasheets/Laird LT17BH0731 SMD contact finger (rev A).pdf)
    'finger_free_h': (7.5, 'Laird LT17BH0731 drawing rev A: 7.5 +-0.2 (detail A; rev A "new height 7.5")'),
    'finger_free_h_tol': (0.2, 'Laird drawing note G / detail A'),
    'finger_nom_comp_h': (6.25, 'Laird drawing: "contact spring in built-in nom. compression" 6.25'),
    'finger_base': ([5.0, 5.0], 'Laird drawing 5 +-0.2 x 5 +-0.2'),
    'finger_len': (6.0, 'Laird drawing 6 +-0.45'),
    'finger_len_tol': (0.45, 'Laird drawing'),
    'finger_w_tol': (0.2, 'Laird drawing'),
    'finger_pad_rec': ([5.25, 5.25], 'Laird drawing: recommended layout pad (5.25) x (5.25)'),
    'finger_clear_zone': ([6.6, 6.5], 'Laird drawing: clearance zone min (6.6) x (6.5)'),
    'finger_t': (0.127, 'Laird drawing title block 0.127 +-0.02'),
    'finger_mass_g': (0.0856, 'Laird drawing'),
    'finger_plating': ('Au 0.0254 um (1 u") over Ni 0.508-1.016 um, selective one side (contact + solder surfaces)', 'Laird drawing notes I'),
    'finger_material': ('BeCu C17200 1/2H, heat treated HV 343 min', 'Laird drawing notes F, H'),
    # bare pad (spec 12.12.3)
    'pad_bare': ([6.0, 5.0], 'spec 12.12.3 bare ENIG 6.0 x 5.0'),
    'pad_cu': ([8.0, 7.0], 'spec 12.12.3 copper 8.0 x 7.0'),
    # opening tolerances
    'tol_pcb_frame': (0.30, 'Frame_Design s1.2: PCB located by 9 PT screws in the 3.2 ear holes (+-0.3)'),
    'tol_sheet_v2': (0.75, 'Frame_Design s1.1: sheet located by the pocket walls, 0.75 per side'),
    'tol_sheet_gf': (0.50, 'assumed: GF sheet PSA-bonded with a placing template (GlassFront_Design s8.8 is silent; the pocket alone allows +-1.3)'),
    'tol_place_refined': (0.15, 'proposed mask-defined 5.25 opening vs 5.0 base: +-0.125'),
    'tol_place_current': (0.50, 'current 6.0 bare length vs 5.0 base'),
    'gap_free': (0.30, 'assumed running clearance finger-to-sheet edge'),
    'opening_R': (1.0, 'proposal'),
    # geometry
    'formex_sheet_abs': ([20.52, 184.42, 19.5, 118.5], 'GlassFront params plan_rectangles.formex; Frame_Design s1.1 (163.90 x 99.00)'),
    'shelf_window_local': ([2.62, 162.32, 1.6, 96.4], 'spec 12.12.3'),
    'panel_label_local': ([6.6, 21.8, 23.7, 74.3], 'SAT070 datasheet p.16 back view, barcode label box (undimensioned, scaled from the vector drawing; +-3 assumed)'),
    'label_tol': (3.0, 'assumed'),
    # mains lead protrusions below the PCB back (4.6 - gap to the Formex, Frame_Design s6 table)
    'protrusion': ({'PS1': 3.265, 'HS1': 2.865, 'Q1': 2.50, 'L40': 1.865, 'L1': 1.865, 'F1': 1.865, 'F3': 1.865,
                    'C40': 1.865, 'U1': 1.665, 'U5': 1.665}, 'Frame_Design s6 lead tips to the Formex at Z -4.6'),
    'protrusion_default': (2.50, 'assumed for parts not in the frame table (K1 RZ03, D6, RV3 are new since; C1, C4, J3, J4, R1-R7, RV1): 2.5 mm max (Q1 trim rule)'),
    'barrier': (6.4, 'spec 12.1-12.2: reinforced, 6.4 mm clearance and creepage'),
    # loads
    'panel_mass_g': (200.0, 'Frame_Design s2 weights (panel 200 g)'),
    'loca_area_mm2': (16490.0, 'GlassFront_Design s7.7'),
    'bead_area_mm2': (2402.6, 'GlassFront_Design s7.7'),
    'bead_dead_kPa': (1.54, 'GlassFront_Design s7.7'),
    'bead_250N_MPa': (0.104, 'GlassFront_Design s7.7 (250 N push or pull)'),
    'silicone_sustained_allow_MPa': (0.014, 'external reference, not in the project documents: ETAG 002 / EAD 090062 structural-silicone design stress for permanent load (0.014 MPa)'),
    'push_50N_centre_mm': (0.124, 'GlassFront_Design s7.8 (3.0 glass, 50 N window centre)'),
    'push_50N_lipline_mm': (0.040, 'GlassFront_Design s7.8'),
    'pcb_screw_preload_N': ([345.0, 690.0], 'Frame_Design s5.2'),
    'pcb_E_MPa': (20000.0, 'Frame_Design s5.4 (FR4 E ~ 20 GPa)'),
    'pcb_t': (1.6, 'spec 12.1'),
    'L_budget_nH': (15.0, 'brief; sim/emc_tests_earthed/C_rf/results.json contact_inductance "E_i19 +ferrite" 14.6 nH for 6 dB'),
    'dB_per_nH': (-0.48, 'sim/emc_tests_earthed/C_rf/results.json contact_inductance "E_i19 +ferrite"'),
    'esd_total_A': (4.0, 'brief (8 kV discharge, about 4 A in total through the bond)'),
}
V = {k: v[0] for k, v in IN.items()}

# Ozdisan search 2026-11-21 (leaf categories rf-aksesuarlari-657 'PCB Spring Contacts', pil-yaylari-351,
# yayli-baskili-konnektorler-353, yay-yuklu-konnektorler-309, pil-yuvalari-484; site search for WE-SECF,
# WE-SCFA, S17xx, Harwin, Kitagawa, fingerstock, EMI contact, grounding contact, shield finger, spring contact,
# C-Clip, gasket).  Datasheets: cdn.ozdisan.com/public/product/assets/<file>.  Price = qty 1, excl. VAT.
CANDIDATES = [
    dict(mpn='LT17BH0731', maker='Laird (Laird Signal)', type='SMD contact finger, BeCu zig-zag', stock=602220, usd_1=0.17, usd_700=0.11338,
         heights='free 7.5 +-0.2; built-in nominal compression 6.25; working range NOT stated', ds='Laird drawing rev A (Datasheets/)',
         verdict='CHOSEN - the only stocked SMD finger tall enough; force, range, current, temperature not stated (model + bench test)'),
    dict(mpn='3SST-NN55NN-NNNNG', maker='AMTEK', type='EMI spring with stopper, TiCu 0.12', stock=0, lead='10-11 weeks',
         heights='working 3.60-5.20; 3 A; -20..+85 C', ds='AMTEK GW271-AB331', verdict='would suit frame v2; NOT stocked'),
    dict(mpn='3SS8-NN67NN-NNQ1G', maker='AMTEK', type='EMI spring, TiCu 0.15', stock=0, lead='10-11 weeks',
         heights='working 5.0-6.2; 3 A; -20..+85 C', ds='AMTEK GW271-AB336', verdict='would suit GF-2.1 (RSS range); NOT stocked'),
    dict(mpn='3SQQ-NN51NN-K1Q1G', maker='AMTEK', type='EMI spring, PhBz 0.15', stock=0, lead='10-11 weeks',
         heights='application 3.65-4.3', ds='AMTEK GW271-BN264', verdict='too low; not stocked'),
    dict(mpn='331061603010', maker='Wurth (WE-SECF)', type='SMT EMI contact finger, CuBe Au', stock=0, lead='4-5 weeks',
         heights='10.0 free; working 8.3-9.7; -40..+100 C', ds='Wurth 331061603010 rev 002.002', verdict='too tall; not stocked'),
    dict(mpn='1437259-6', maker='TE', type='C-clip', stock=0, heights='4.0 free; working 2.6-3.5', ds='TE 1437259-6', verdict='too low; not stocked'),
    dict(mpn='1447009-8', maker='TE', type='C-clip', stock=0, heights='3.5 free', ds='Ozdisan card', verdict='too low; not stocked'),
    dict(mpn='1871059-1', maker='TE', type='RFI shield finger', stock=0, heights='unknown (Ozdisan links a wrong datasheet)', ds='-', verdict='not stocked'),
    dict(mpn='S7121-42R', maker='Harwin', type='SMT spring contact', stock=0, heights='1.7', ds='Ozdisan card', verdict='too low; not stocked'),
    dict(mpn='303A-753018-000', maker='ATTEND', type='SMT pogo pin (other concept)', stock=1135, usd_1=0.79,
         heights='7.5 free, working 6.8, min 6.2; 0.85 N; 2 A; -40..+85 C', ds='ATTEND 303A-753018-000_B_1',
         verdict='not a spring finger; 6.2 min misses frame v2 and the GF low end; 85 C rating = ambient, no margin'),
    dict(mpn='303A-441615-000', maker='ATTEND', type='R/A SMT pogo pin', stock=3103, usd_1=0.95,
         heights='acts parallel to the board (body 1.5 high)', ds='ATTEND 303A-441615-000_B_1', verdict='wrong direction'),
    dict(mpn='303A-C4418-000', maker='ATTEND', type='SMT machine pin, rigid', stock=1849, heights='4.4 rigid', ds='ATTEND', verdict='no spring'),
    dict(mpn='L-KLS5-1100-G-R', maker='KLS', type='coin-cell side contact SMT, SS 0.15', stock=1806, heights='2.5, side acting', ds='KLS drawing', verdict='too low, side acting'),
    dict(mpn='FLAT SPRING CLIP', maker='OEM', type='leaf clip 23.5 x 3.4, not SMD', stock=1098, heights='23.5', ds='image only', verdict='not SMD, unspecified'),
]


def wc_rss(nominal, tols):
    wc = sum(tols)
    rss = math.sqrt(sum(t * t for t in tols))
    return dict(nom=round(nominal, 3), wc=[round(nominal - wc, 3), round(nominal + wc, 3)],
                rss=[round(nominal - rss, 3), round(nominal + rss, 3)], wc_tol=round(wc, 3), rss_tol=round(rss, 3))


def stacks():
    s = {}
    common = [V['tol_panel_flat'], V['tol_pcb_bow'], V['tol_solder']]
    for name, tf in (('v2_formex_0.40', V['v2_formex_t_modelled']), ('v2_GK-10_0.25', V['formex_GK10_t']),
                     ('v2_GK-17_0.43', V['formex_GK17_t'])):
        nom = V['v2_shelf_front_Z'] + tf - V['solder_offset']
        r = wc_rss(nom, [V['shelf_Z_tol'], V['formex_t_tol']] + common)
        r['wc'][1] = round(r['wc'][1] + V['v2_gasket_gap_wc'], 3)          # panel can float forward
        r['note'] = 'upper WC includes the panel floating forward by the gasket gap (0.25)'
        s[name] = r
    nom = V['gf_boss_to_datumA'] + V['gf_lip_height'] - V['gf_glass_t'] - V['gf_loca_t'] - V['panel_t'] - V['solder_offset']
    tol = [V['tol_boss'], V['tol_lip'], V['tol_flush_wc'], V['tol_glass'], V['tol_loca'], V['tol_lcm'], V['tol_ctp']] + common
    r = wc_rss(nom, tol)
    tol_r = [V['tol_boss'], V['tol_lip'], V['tol_flush_rss'], V['tol_glass'], V['tol_loca'], V['tol_lcm'], V['tol_ctp']] + common
    rss = math.sqrt(sum(t * t for t in tol_r))
    r['rss'] = [round(nom - rss, 3), round(nom + rss, 3)]
    r['rss_tol'] = round(rss, 3)
    r['check_vs_doc'] = 'GlassFront s7.2 panel back -5.80, floats -5.08 .. -6.52 (gap to the Formex 0.08-1.52); this stack is measured from the boss tops and adds board bow, panel flatness and the solder joint'
    s['GF-2.1'] = r
    return s


def finger(stk):
    fm = json.load(open(os.path.join(OUT, 'finger_model.json')))
    cases = fm['cases']
    summ = fm['summary']

    def F(case, h, shift=0.0):
        hist = cases[case]['hist']
        hs = np.array([r['h'] for r in hist]); fs = np.array([r['F'] for r in hist]); ss = np.array([r['sigma_max'] for r in hist])
        o = np.argsort(hs)
        hh = h - shift                      # free height +shift behaves like the nominal spring at h - shift
        return float(np.interp(hh, hs[o], fs[o])), float(np.interp(hh, hs[o], ss[o]))

    res = {}
    tolH = V['finger_free_h_tol']
    for name, st in stk.items():
        hmin, hmax = st['wc']
        rmin, rmax = st['rss']
        Fn, Sn = F('t_nom_0.127', st['nom'])
        Fmin, _ = F('t_min_0.107', hmax, shift=-tolH)        # thin strip, low spring, largest gap
        Fmax, Smax = F('t_max_0.147', hmin, shift=+tolH)     # thick strip, tall spring, smallest gap
        _, S_nom_hmin = F('t_nom_0.127', hmin, shift=+tolH)
        Frs_lo, _ = F('t_nom_0.127', rmax)
        Frs_hi, _ = F('t_nom_0.127', rmin)
        res[name] = dict(h_nom=st['nom'], h_wc=st['wc'], h_rss=st['rss'],
                         deflection_nom=round(V['finger_free_h'] - st['nom'], 3),
                         deflection_wc=[round(V['finger_free_h'] - tolH - hmax, 3), round(V['finger_free_h'] + tolH - hmin, 3)],
                         compression_pct_wc_max=round(100 * (V['finger_free_h'] + tolH - hmin) / (V['finger_free_h'] + tolH), 1),
                         F_nom=round(Fn, 3), F_min_wc=round(Fmin, 3), F_max_wc=round(Fmax, 3), F_rss=[round(Frs_lo, 3), round(Frs_hi, 3)],
                         sigma_nom=round(Sn), sigma_max_wc_tmax=round(Smax), sigma_wc_tnom=round(S_nom_hmin))
    return dict(model_summary=summ, per_design=res, yield_assumed_MPa=fm['yield_MPa_assumed'])


def rect_dist(px, py, x0, x1, y0, y1):
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)


def seg_rect_dist(a, b, rect, n=40):
    return min(rect_dist(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, *rect) for i in range(n + 1))


def rr_overlap_gap(r1, r2):
    """plan gap between two axis-aligned rectangles (x0,x1,y0,y1); negative = overlap"""
    dx = max(r2[0] - r1[1], r1[0] - r2[1])
    dy = max(r2[2] - r1[3], r1[2] - r2[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def main():
    board = json.load(open(os.path.join(OUT, 'board_pads.json'), encoding='utf8'))
    stk = stacks()
    fin = finger(stk)
    fm = json.load(open(os.path.join(OUT, 'finger_model.json')))
    # plan envelope of the finger relative to the base centre (+x = bend side), union over 4.4..7.5 mm
    hist = fm['cases']['t_nom_0.127']['hist']
    xmin = min(r['x_min'] for r in hist if r['h'] >= 4.4)
    xmax = max(r['x_max'] for r in hist if r['h'] >= 4.4)
    base_c = 2.5            # base runs x 0..5 in the model
    env = dict(x_free_side=round(xmin - base_c, 3), x_bend_side=round(xmax - base_c, 3), half_w=2.5,
               note='model centre line + t/2, nominal drawing dimensions, union over the working range')
    pads = {b['ref']: b for b in board['landing_pads']}
    mains = []
    for p in board['tht_pads']:
        is_m = bool(p['mains_net']) or p['ref'] == 'HS1'
        if not is_m:
            continue
        prot = V['protrusion'].get(p['ref'], V['protrusion_default'])
        lead_r = max((p['drill'][0] if p['drill'] else 1.0) - 0.2, 0.5) / 2
        mains.append(dict(ref=p['ref'], num=p['num'], net=p['net'], x=p['x'], y=p['y'], pad_r=max(p['sx'], p['sy']) / 2,
                          lead_r=round(lead_r, 3), protrusion=prot,
                          prot_src='frame table' if p['ref'] in V['protrusion'] else 'assumed 2.5'))
    tracks = board['mains_tracks_bcu']

    # pad attributes
    lab = V['panel_label_local']
    lt = V['label_tol']
    pad_info = {}
    for ref, b in pads.items():
        cx, cy = b['x'], b['y']
        cu = (cx - 4.0, cx + 4.0, cy - 3.5, cy + 3.5)
        dm = min(min(rect_dist(m['x'], m['y'], *cu) - m['pad_r'] for m in mains),
                 min(seg_rect_dist(t['pts'][0], t['pts'][-1], cu) - t['w'] / 2 for t in tracks))
        lab_gap = rr_overlap_gap((cx - 3.5, cx + 3.5, cy - 2.6, cy + 2.6), (lab[0], lab[1], lab[2], lab[3]))
        # nearest mains item direction -> bend side away from it
        near = min(mains, key=lambda m: math.hypot(m['x'] - cx, m['y'] - cy))
        bend_dir = -1 if near['x'] > cx else +1
        pad_info[ref] = dict(x=cx, y=cy, mains_copper_mm=round(dm, 2), label_gap_mm=round(lab_gap, 2),
                             label_conflict=lab_gap < lt, bend_dir=bend_dir, nearest_mains=f"{near['ref']}.{near['num']} {near['net']}",
                             to_board_bottom_edge=round(99.0 - (cy + 2.6), 2))
    # contact sets
    sets = {
        'minimum_6': ['BP1', 'BP6', 'BP10', 'BP11', 'BP13', 'BP15'],
        'recommended_8': ['BP1', 'BP6', 'BP8', 'BP10', 'BP11', 'BP13', 'BP15', 'BP16'],
    }
    unused = {
        'BP2': 'top-left column already has BP1; 9.5 mm to mains copper (lowest of all); 3.2 mm from the label box (inside its +-3 assumed scatter)',
        'BP3': 'on the panel barcode label (datasheet p.16 back view)',
        'BP4': 'interior, 13.2 mm to mains; openings of BP4/BP5 (9 mm pitch) would merge',
        'BP5': 'as BP4',
        'BP7': 'right edge covered by BP6 and BP8; spare',
        'BP9': 'right edge covered by BP8 and BP10; spare',
        'BP12': 'interior next to BP11/BP13; spare for J10 if a third FPC-end contact is wanted',
        'BP14': 'bottom edge already covered by BP13 and BP15 (29.5 mm and 32.5 mm away); spare',
        'BP17': 'on the panel barcode label (datasheet p.16 back view)',
        'BP18': 'interior, 15.5 mm to mains; spare',
    }
    # openings
    designs = {'v2': V['tol_sheet_v2'], 'GF': V['tol_sheet_gf']}
    fx = V['formex_sheet_abs']
    sheet_local = (fx[0] - OFF, fx[1] - OFF, fx[2] - OFF, fx[3] - OFF)
    win = V['shelf_window_local']
    openings = {}
    for dname, tsheet in designs.items():
        add = V['finger_len_tol'] / 2 + V['tol_place_refined'] + V['tol_pcb_frame'] + tsheet + V['gap_free']
        add_y = V['finger_w_tol'] + V['tol_place_refined'] + V['tol_pcb_frame'] + tsheet + V['gap_free']
        rows = []
        for ref in sets['recommended_8']:
            pi = pad_info[ref]
            d = pi['bend_dir']
            # finger plan envelope in local coords
            xa = pi['x'] + d * env['x_bend_side']
            xb = pi['x'] + d * env['x_free_side']
            fx0, fx1 = min(xa, xb), max(xa, xb)
            fy0, fy1 = pi['y'] - 2.5, pi['y'] + 2.5
            o = (round(fx0 - add, 2), round(fx1 + add, 2), round(fy0 - add_y, 2), round(fy1 + add_y, 2))
            rows.append(dict(ref=ref, finger_env=[round(fx0, 3), round(fx1, 3), fy0, fy1], opening_local=o,
                             opening_abs=[round(o[0] + OFF, 2), round(o[1] + OFF, 2), round(o[2] + OFF, 2), round(o[3] + OFF, 2)],
                             size=[round(o[1] - o[0], 2), round(o[3] - o[2], 2)],
                             centre_abs=[round((o[0] + o[1]) / 2 + OFF, 2), round((o[2] + o[3]) / 2 + OFF, 2)],
                             web_to_sheet_edge=round(min(o[0] - sheet_local[0], sheet_local[1] - o[1], o[2] - sheet_local[2], sheet_local[3] - o[3]), 2),
                             inside_shelf_window=bool(o[0] >= win[0] and o[1] <= win[1] and o[2] >= win[2] and o[3] <= win[3]),
                             window_margin=round(min(o[0] - win[0], win[1] - o[1], o[2] - win[2], win[3] - o[3]), 2)))
        # webs between openings
        webs = []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                webs.append((round(rr_overlap_gap(rows[i]['opening_local'], rows[j]['opening_local']), 2), rows[i]['ref'], rows[j]['ref']))
        webs.sort()
        openings[dname] = dict(added_per_side_x=round(add, 3), added_per_side_y=round(add_y, 3), rows=rows,
                               min_web_between=webs[0], webs_below_10=[w for w in webs if w[0] < 10])
    # insulation check per opening
    ins = {}
    for dname in designs:
        panelZ_min = {'v2': V['v2_shelf_front_Z'] + V['formex_GK10_t'], 'GF': V['v2_shelf_front_Z'] + V['v2_formex_t_modelled'] + V['gf_backstop_gap_wc'][0]}[dname]
        out = []
        for row in openings[dname]['rows']:
            o = row['opening_local']
            fe = row['finger_env']
            fe_t = (fe[0] - V['tol_place_refined'] - V['finger_len_tol'] / 2, fe[1] + V['tol_place_refined'] + V['finger_len_tol'] / 2,
                    fe[2] - V['finger_w_tol'] - V['tol_place_refined'], fe[3] + V['finger_w_tol'] + V['tol_place_refined'])
            best = dict(clear_finger=(1e9, ''), clear_panel=(1e9, ''), creep_formex=(1e9, ''))
            for m in mains:
                tag = f"{m['ref']}.{m['num']} {m['net']} (prot {m['protrusion']})"
                dplan_f = rect_dist(m['x'], m['y'], *fe_t) - max(m['pad_r'], m['lead_r'])
                if dplan_f < best['clear_finger'][0]:
                    best['clear_finger'] = (dplan_f, tag)
                # pin tip (Z -prot) to the opening area in the Formex back plane (Z -4.6): conservative for the panel
                dpl = rect_dist(m['x'], m['y'], *o)
                dz = V['v2_shelf_front_Z'] - m['protrusion']
                dpan = math.hypot(max(dpl - m['lead_r'], 0), dz)
                # pad / fillet ring at Z 0 to the panel plane at its closest
                dpan2 = math.hypot(max(dpl - m['pad_r'], 0), panelZ_min)
                d = min(dpan, dpan2)
                if d < best['clear_panel'][0]:
                    best['clear_panel'] = (d, tag)
                # creepage over the Formex: pin tip assumed touching the sheet, along the sheet to the opening edge, down its cut edge
                cr = max(dpl - m['lead_r'], 0) + V['formex_GK10_t']
                if cr < best['creep_formex'][0]:
                    best['creep_formex'] = (cr, tag)
            for t in tracks:
                tag = f"B.Cu track {t['net']} w{t['w']}"
                dpf = seg_rect_dist(t['pts'][0], t['pts'][-1], fe_t) - t['w'] / 2
                if dpf < best['clear_finger'][0]:
                    best['clear_finger'] = (dpf, tag)
                dpl = seg_rect_dist(t['pts'][0], t['pts'][-1], o) - t['w'] / 2
                d = math.hypot(max(dpl, 0), panelZ_min)
                if d < best['clear_panel'][0]:
                    best['clear_panel'] = (d, tag)
            r = {k: dict(mm=round(v[0], 2), item=v[1], margin=round(v[0] - V['barrier'], 2), ok=v[0] >= V['barrier']) for k, v in best.items()}
            out.append(dict(ref=row['ref'], **r))
        ins[dname] = out
    # insulation for every pad (info, v2 tolerances)
    all_pad = {}
    for ref, pi in pad_info.items():
        o = (pi['x'] - 3.5 - openings['v2']['added_per_side_x'], pi['x'] + 3.5 + openings['v2']['added_per_side_x'],
             pi['y'] - 2.5 - openings['v2']['added_per_side_y'], pi['y'] + 2.5 + openings['v2']['added_per_side_y'])
        dmin = min(rect_dist(m['x'], m['y'], *o) - m['lead_r'] for m in mains)
        all_pad[ref] = dict(min_plan_pin_to_opening=round(dmin, 2))
    # forces
    forces = {}
    for dname, key in (('v2', 'v2_formex_0.40'), ('GF', 'GF-2.1')):
        f = fin['per_design'][key]
        for sname, refs in sets.items():
            n = len(refs)
            forces[f'{dname}_{sname}'] = dict(n=n, total_nom=round(n * f['F_nom'], 2), total_min=round(n * f['F_min_wc'], 2),
                                             total_max=round(n * f['F_max_wc'], 2))
    w_panel = V['panel_mass_g'] * 9.81e-3
    gf = forces['GF_recommended_8']
    gf_checks = dict(
        panel_weight_N=round(w_panel, 2),
        loca_pressure_kPa_nom=round(gf['total_nom'] / V['loca_area_mm2'] * 1e3, 3),
        loca_pressure_kPa_max=round(gf['total_max'] / V['loca_area_mm2'] * 1e3, 3),
        loca_dead_kPa_doc=0.12,
        loca_direction='compression (fingers push the panel onto the glass); the document states only the dead load 0.12 kPa',
        bead_tension_kPa_nom=round(gf['total_nom'] / V['bead_area_mm2'] * 1e3, 2),
        bead_tension_kPa_max=round(gf['total_max'] / V['bead_area_mm2'] * 1e3, 2),
        bead_dead_kPa_doc=V['bead_dead_kPa'],
        bead_sustained_allow_kPa_ext=V['silicone_sustained_allow_MPa'] * 1e3,
        bead_ratio_to_allow_max=round(gf['total_max'] / V['bead_area_mm2'] / V['silicone_sustained_allow_MPa'], 2),
        glass_dish_mm_max=round(V['push_50N_centre_mm'] * gf['total_max'] / 50.0, 4),
        lipline_mm_max=round(V['push_50N_lipline_mm'] * gf['total_max'] / 50.0, 4),
    )
    v2 = forces['v2_recommended_8']
    k_gasket = V['v2_gasket_force_nom_N'] / V['v2_gasket_comp_nom_mm']
    v2_checks = dict(gasket_force_nom_N=V['v2_gasket_force_nom_N'], gasket_force_max_N=V['v2_gasket_force_max_N'],
                     finger_total_max_N=v2['total_max'], ratio_nom=round(v2['total_max'] / V['v2_gasket_force_nom_N'], 3),
                     gasket_secant_N_per_mm=round(k_gasket, 0),
                     extra_gasket_squeeze_mm=round(v2['total_max'] / k_gasket, 3),
                     before_mounting='nothing holds the panel against the fingers once the subassembly leaves the fixture (Frame_Design s7: "held only by the PCB/sheet stack")')
    # PCB: plate deflection under the interior pads, simply supported 164 x 99 (Timoshenko central load alpha 0.0159 at b/a 1.66)
    D = V['pcb_E_MPa'] * V['pcb_t'] ** 3 / (12 * (1 - 0.15 ** 2))
    fmax1 = max(f['F_max_wc'] for f in fin['per_design'].values())
    fnom1 = max(f['F_nom'] for f in fin['per_design'].values())
    pcb = dict(plate_D_Nmm=round(D, 0), alpha=0.0159,
               defl_one_finger_at_board_centre_nom_mm=round(0.0159 * fnom1 * 99.0 ** 2 / D, 4),
               note='upper bound: plate simply supported on its edges only, load at the centre; the chosen pads lie 7-18 mm from supported edges, so the real deflection is smaller; it reduces compression (safe side for stress, unsafe for the minimum force)',
               total_on_9_screws_nom_N=round(8 * fnom1, 2), total_on_9_screws_wc_N=round(8 * fmax1, 2),
               per_screw_wc_N=round(8 * fmax1 / 9, 2),
               vs_preload_pct_wc=round(100 * 8 * fmax1 / 9 / V['pcb_screw_preload_N'][0], 2))
    # inductance (partial self-inductance of a flat strip, Rosa/Grover: L = 0.2 l [ln(2l/(w+t)) + 0.5 + 0.2235 (w+t)/l] nH, l,w in mm)
    def Lstrip(l, w, t):
        return 0.2 * l * (math.log(2 * l / (w + t)) + 0.5 + 0.2235 * (w + t) / l)
    cm = fm['cases']['t_nom_0.127']
    # current path: from the soldered base's bend end, both right bends, both inclines, the left bend, and the
    # top leg from its bend to the contact patch (model contact at x ~3.3 -> about 1.7 mm of top leg)
    path = cm['Ls'] * 2 + 2 * math.radians(166.8) * (0.87 + 0.0635) + math.radians(153.6) * (0.65 + 0.0635) + 1.7
    Lnd = dict(path_length_mm=round(path, 2),
               L_upper_unfolded_nH=round(Lstrip(path, 5.0, 0.127), 2),
               L_lower_straight_post_nH={str(h): round(Lstrip(h, 5.0, 0.127), 2) for h in (5.0, 5.8)},
               note='true value lies between: the two inclined legs carry opposite horizontal currents (partial cancellation); contact spot adds < 0.5 nH (assumed)',
               budget_nH=V['L_budget_nH'],
               dB_cost_upper_vs_2nH=round((Lstrip(path, 5.0, 0.127) - 2.0) * V['dB_per_nH'], 2))
    esd = dict(total_A=V['esd_total_A'], per_finger_worst_A=V['esd_total_A'],
               strip_section_mm2=round(5.0 * 0.127, 3),
               current_density_A_mm2_worst=round(V['esd_total_A'] / (5.0 * 0.127), 2),
               note='ns pulse, I2t ~ 1e-7 A2s: negligible heating; the drawing states no current rating')
    # elastic verdict per design (stress vs assumed yield)
    sy = fin['yield_assumed_MPa']
    fsum = fin['model_summary']['t_nom_0.127']
    verdict = {}
    fmc = fm['cases']['t_nom_0.127']['hist']
    def sig_at(h):
        hs = np.array([r['h'] for r in fmc]); ss = np.array([r['sigma_max'] for r in fmc]); o = np.argsort(hs)
        return float(np.interp(h, hs[o], ss[o]))
    def h_at_sigma(s):
        for r in fmc:
            if r['sigma_max'] >= s:
                return r['h']
        return None
    for key, f in fin['per_design'].items():
        verdict[key] = dict(sigma_nom=round(sig_at(f['h_nom'])), sigma_rss_low=round(sig_at(f['h_rss'][0])),
                            sigma_wc_low_tall_spring=round(sig_at(f['h_wc'][0] - V['finger_free_h_tol'])),
                            ratio_nom=round(sig_at(f['h_nom']) / sy, 2), ratio_rss=round(sig_at(f['h_rss'][0]) / sy, 2),
                            ratio_wc=round(sig_at(f['h_wc'][0] - V['finger_free_h_tol']) / sy, 2))
    elastic_limit = dict(h_at_yield_nominal_strip=h_at_sigma(sy), h_at_80pct_yield=h_at_sigma(0.8 * sy),
                         note='nominal strip 0.127, nominal free height; the tall spring (+0.2) reaches the same stress 0.2 mm higher')
    res = dict(inputs={k: dict(value=v[0], source=v[1]) for k, v in IN.items()},
               candidates=CANDIDATES, elastic_verdict=verdict, elastic_limit=elastic_limit,
               stackups=stk, finger=fin, finger_plan_envelope=env, pads=pad_info, contact_sets=sets, unused_pads=unused,
               openings=openings, insulation=ins, insulation_all_pads_info=all_pad, forces=forces,
               gf_checks=gf_checks, v2_checks=v2_checks, pcb=pcb, inductance=Lnd, esd=esd,
               mains_conductors_considered=dict(pins=len(mains), bcu_tracks=len(tracks)))
    json.dump(res, open(os.path.join(HERE, 'results.json'), 'w', encoding='utf8'), indent=1)
    print(json.dumps(dict(stackups=stk, finger=fin['per_design'], env=env), indent=0))
    print(json.dumps(dict(openings={k: [(r['ref'], r['size'], r['web_to_sheet_edge'], r['window_margin']) for r in v['rows']] for k, v in openings.items()},
                          webs={k: v['min_web_between'] for k, v in openings.items()}), indent=0))
    for d, rows in ins.items():
        for r in rows:
            print(d, r['ref'], r['clear_finger']['mm'], r['clear_panel']['mm'], r['creep_formex']['mm'], r['clear_panel']['item'])
    print(json.dumps(dict(forces=forces, gf=gf_checks, v2=v2_checks, pcb=pcb, L=Lnd, verdict=verdict, elastic_limit=elastic_limit), indent=0))
    print(json.dumps({k: (v['mains_copper_mm'], v['label_gap_mm'], v['nearest_mains'], v['bend_dir']) for k, v in pad_info.items()}))


if __name__ == '__main__':
    main()
