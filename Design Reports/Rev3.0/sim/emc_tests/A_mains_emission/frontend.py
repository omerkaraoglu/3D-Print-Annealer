"""Mains front-end circuit model (ngspice netlists) for scope A.

Every value is tagged with its source in PARAMS_DOC. Routed lengths come from design_inputs.json (current PCB).
Two netlists are produced from the same element list:
  - 'ac'  : the triac replaced by a 1 V AC source between Q1.A2 (LINE_FILT side) and Q1.A1 (source-substitution:
            the triac voltage waveform is the only HF source; linear network) -> transfer to both LISN ports;
            or a 1 A AC current source at the HLK input pins (PS1 bound) in DM or CM.
  - 'tran': the full circuit with the 230 V source and the triac as a behavioural switch driven by a
            time-defined conduction control (turn-on when |v_line| reaches V_on after each zero crossing,
            voltage collapse over t_f, turn-off when the load current falls to I_H).
"""
import json, math, os
import numpy as np
from common import HERE

DI = json.load(open(os.path.join(HERE, "design_inputs.json"), encoding="utf8"))


def trace_L(l_mm, w_mm, t_mm=0.035):
    if not l_mm:
        return 1e-12
    return 1e-9 * 0.2 * l_mm * (math.log(2 * l_mm / (w_mm + t_mm)) + 0.5 + 0.2235 * (w_mm + t_mm) / l_mm)


def br(key):
    return DI["branches_mm"][key]["length_mm"]


NOMINAL = {
    # mains supply behind the AMN (assumed; split like the 61000-3-3 reference impedance, not read)
    "Vrms": 230.0, "f": 50.0, "Rm": 0.40, "Lm": 0.8e-3,
    # AMN 50 ohm || (50 uH + 5 ohm) (CISPR 16-1-2, NOT READ; Schwarzbeck NSLK 8117 listing, Politecnico di Milano AC-LISN paper)
    "L_lisn": 50e-6, "R_lisn": 5.0, "C_sup": 4e-6, "C_coup": 0.25e-6, "R_rec": 50.0,
    # 1 m two-wire mains cord 0.4 m over the RGP (EN 55014-1 5.2.1.1 / 5.2.2.1, PDF p. 41-42); per-conductor L from
    # mu0/2pi ln(2h/r), mutual from ln(2h/s): assumed geometry r 0.8 mm, s 4 mm
    "L_cord": 1.38e-6, "k_cord": 0.77, "C_cord": 50e-12, "C_cord_g": 15e-12,
    # board copper (design_inputs.json branch lengths, flat-conductor partial inductance; mutuals neglected)
    "trace_scale": 1.0,
    "L_F3": 20e-9, "R_F3": 0.012,                      # fuse body + clips (assumed)
    "L40": 100e-6, "R40": 0.10, "Cp40": 10e-12, "Rp40": 30e3,   # RC1415U-101K: 100 uH +-10 %, 0.1 ohm (spec 12.5 / BOM); Cp, Rp assumed
    "C40": 1.0e-6, "ESR40": 0.010, "ESL40": 20e-9,     # C42P2105KBSC400 1 uF X2 (netlist); ESR/ESL assumed (27.5 mm pitch box)
    "C1": 100e-9, "ESR1": 0.030, "ESL1": 12e-9,        # C42P2104M6SC361 100 nF X2; ESR/ESL assumed
    "C_RV1": 370e-12,                                  # TVR14431: 370 pF @ 1 kHz (TVR10391KSY.pdf p. 7)
    "C_RV2": 120e-12,                                  # TVR10561: 120 pF (TVR10391KSY.pdf p. 6)
    "R5": 47.0, "C4": 10e-9,                           # snubber R5 47 R 2 W, C4 10 nF X2 (netlist)
    "R_heater": 230.0 ** 2 / 1000.0,                   # 1 kW at 230 V
    "L_heater": 5e-6,                                  # leads + element, assumed (swept 1-20 uH)
    "C_hc": 300e-12, "C_ch": 50e-12,                   # heater-to-oven-chassis and chassis-to-RGP, assumed (class II, floating chassis)
    "R_fan": 790.0, "L_fan": 3.8, "C_fan": 200e-12,    # 230 V fan ~20 W, PF 0.55 (assumed; no fan data in the project)
    "R_F1": 0.15, "L_F1": 20e-9,                       # 1 A slow-blow STC1A250V (resistance assumed)
    "L_cmc": 10e-3, "k_cmc": 0.995, "Cw_cmc": 5e-12,   # LFU09V-103: 10 mH (part number); leakage/winding C assumed
    "Rp_cmc": 15e3,                                    # ferrite core loss as a parallel R per winding (Q ~ 1 at 0.2-1 MHz), assumed 5-50 k
    "R_zcd": 66e3,                                     # R6 + R7 33 k each (netlist)
    "C_ps_in": 22e-12, "C_ps_y": 50e-12, "C_gnd_rgp": 40e-12,  # HLK input (bridge off) / primary-secondary / board+display to RGP: assumed
    # oven chassis <-> SELV ground (thermocouple probe + lead inside the oven), assumed 20 pF (5-100 pF; 'bonded' = 10 nF)
    "C_cs": 20e-12,
    # triac switching (BTA24-800CW; MOC3052 gate drive)
    "V_on": 20.0, "t_f": 0.5e-6, "I_H": 0.05, "t_off": 0.5e-6,
}

PARAMS_DOC = {
    "V_on": "turn-on voltage: gate threshold of MOC3052 (VTM 2.2/2.5 V @100 mA, onsemi p. 3) + R3 360 R + BTA24 IGT <= 35 mA, VGT <= 1.3 V (BTA12-CW table, ST p. 3; BTA24 values second-source per spec 7.1) -> 8.5-18 V; or later if the ZCD-referenced gate pulse starts later (see zcd_timing). Swept 10-40 V as specified.",
    "t_f": "triac voltage-collapse time, assumed 0.5 us (swept 0.2-2 us)",
    "I_H": "BTA24-800CW holding current 50 mA (spec 7.1, second-source); commutation step I_H at each half-cycle end",
}


def element_list(P, mode):
    """Return the netlist body lines shared by all analyses."""
    s = P["trace_scale"]
    Lt = lambda key, w: trace_L(br(key), w) * s
    e = []
    a = e.append
    if mode == "tran":
        vpk = math.sqrt(2) * P["Vrms"]
        a(f"Vml ms_l 0 SIN(0 {vpk:.4f} {P['f']})")
    else:
        a("Vml ms_l 0 dc 0 ac 0")
    a("Vmn ms_n 0 dc 0")
    a(f"Rml ms_l msl2 {P['Rm'] * 0.6:.6g}"); a(f"Lml msl2 sl {P['Lm'] * 0.6:.6g}")
    a(f"Rmn ms_n msn2 {P['Rm'] * 0.4:.6g}"); a(f"Lmn msn2 sn {P['Lm'] * 0.4:.6g}")
    for side in ("l", "n"):
        a(f"Csup_{side} s{side} 0 {P['C_sup']:.6g}")
        a(f"R5_{side} s{side} l5{side} {P['R_lisn']:.6g}")
        a(f"L50_{side} l5{side} lisn_{side} {P['L_lisn']:.6g}")
        a(f"Cc_{side} lisn_{side} rx_{side} {P['C_coup']:.6g}")
        a(f"Rrx_{side} rx_{side} 0 {P['R_rec']:.6g}")
    # mains cord (coupled lumped model)
    a(f"Lcd1 lisn_l j3_1 {P['L_cord']:.6g}"); a(f"Lcd2 lisn_n j3_2 {P['L_cord']:.6g}"); a(f"Kcd Lcd1 Lcd2 {P['k_cord']}")
    a(f"Ccd j3_1 j3_2 {P['C_cord']:.6g}"); a(f"Ccg1 j3_1 0 {P['C_cord_g']:.6g}"); a(f"Ccg2 j3_2 0 {P['C_cord_g']:.6g}")
    # LINE -> F3 -> LINE_FUSED
    a(f"Rf3 j3_1 f3a {P['R_F3']}"); a(f"Lf3 f3a lfused {P['L_F3'] + Lt('LINE:J3.1->F3.2', 2.5):.6g}")
    a(f"Llf1 lfused l40_2 {Lt('LINE_FUSED:F3.1->L40.2', 2.5):.6g}")
    # K1 fan branch on LINE_FUSED (contact closed, fan running)
    a(f"Llf2 l40_2 k1c {Lt('LINE_FUSED:L40.2->K1.1', 2.5):.6g}")
    if P.get("fan_on", True):
        a("Rk1 k1c k1no 0.03")
    else:
        a("Rk1 k1c k1no 1e9")
    a(f"Lj4 k1no j4_1 {Lt('Net-(J4-Pin_1):K1.3->J4.1', 1.0):.6g}")
    a(f"Rfan j4_1 fanm {P['R_fan']}"); a(f"Lfan fanm j4_2 {P['L_fan']}"); a(f"Cfan j4_1 j4_2 {P['C_fan']:.6g}")
    a(f"Lj4n j4_2 j3_2 {Lt('NEUT:J3.2->J4.2', 1.0):.6g}")
    # L40 with parasitics
    # no_filter: pass-1/2 topology check (heater straight on the mains: L40 shorted, X caps removed)
    a(f"L40 l40_2 x40 {1e-12 if P.get('no_filter') else P['L40']:.6g}"); a(f"R40 x40 l40_1 {P['R40']}")
    a(f"C40p l40_2 l40_1 {P['Cp40']:.6g}"); a(f"R40p l40_2 l40_1 {P['Rp40']:.6g}")
    # LINE_FILT shunt branch: C40, C1, RV1 (returning on the 72 mm NEUT run to J3.2)
    a(f"Lc40s l40_1 c40_1 {Lt('LINE_FILT:L40.1->C40.1', 1.0):.6g}")
    if not P.get("no_filter"):
        a(f"C40 c40_1 c40m {P['C40']:.6g}"); a(f"Rc40 c40m c40e {P['ESR40']}"); a(f"Lc40 c40e c40_2 {P['ESL40']:.6g}")
        a(f"Lc1s c40_1 c1_1 {Lt('LINE_FILT:C40.1->C1.1', 1.0):.6g}")
        a(f"Cx1 c1_1 c1m {P['C1']:.6g}"); a(f"Rcx1 c1m c1e {P['ESR1']}"); a(f"Lcx1 c1e c1_2 {P['ESL1']:.6g}")
        a(f"Lc1n c1_2 c40_2 {Lt('NEUT:C40.2->C1.2', 1.0):.6g}")
        a(f"Lrv1 c40_1 rv_1 {Lt('LINE_FILT:C40.1->RV1.1', 1.0):.6g}"); a(f"Crv1 rv_1 c40_2 {P['C_RV1']:.6g}")
    a(f"Ln1 c40_2 j3_2 {Lt('NEUT:J3.2->C40.2', 1.0):.6g}")
    # proposal hooks: extra X2 capacitor between two nodes with its own ESL
    for i, (n1, n2, C, esl) in enumerate(P.get("extra_caps", [])):
        a(f"Cxp{i} {n1} cxp{i}m {C:.6g}"); a(f"Lxp{i} cxp{i}m {n2} {esl:.6g}"); a(f"Rxp{i} {n1} {n2} 1e9")
    # heater trunk and triac
    a(f"Ltr l40_1 q1_2 {Lt('LINE_FILT:L40.1->Q1.2', 2.5):.6g}")
    a(f"R5s q1_2 snb {P['R5']}"); a(f"C4s snb q1_1 {P['C4']:.6g}"); a(f"Crv2 q1_2 q1_1 {P['C_RV2']:.6g}")
    a(f"La1 q1_1 r1_1 {Lt('Net-(Q1-A1):Q1.1->R1.1', 2.5):.6g}")
    Rh, Lh = P["R_heater"], P["L_heater"]
    a(f"Rh1 r1_1 hm1 {Rh / 2:.6g}"); a(f"Lh1 hm1 hmid {Lh / 2:.6g}")
    a(f"Rh2 hmid hm2 {Rh / 2:.6g}"); a(f"Lh2 hm2 r1_2 {Lh / 2:.6g}")
    a(f"Chc hmid chs {P['C_hc']:.6g}"); a(f"Cch chs 0 {P['C_ch']:.6g}"); a("Rchs chs 0 1e9")
    a(f"Lr1n r1_2 j3_2 {Lt('NEUT:J3.2->R1.2', 2.5):.6g}")
    # PSU branch: F1 -> PSU_L -> L1 (CMC) -> HLK-10M05
    a(f"Lf1t l40_1 f1_1 {Lt('LINE_FILT:L40.1->F1.1', 2.5):.6g}"); a(f"Rf1 f1_1 f1x {P['R_F1']}"); a(f"Lf1 f1x psu_l {P['L_F1']:.6g}")
    a(f"Lpl psu_l l1_4 {Lt('PSU_L:F1.2->L1.4', 1.0):.6g}")
    a(f"Lnl j3_2 l1_1 {Lt('NEUT:J3.2->L1.1', 1.0):.6g}")
    a(f"Lca l1_4 ps_l {P['L_cmc']:.6g}"); a(f"Lcb l1_1 ps_n {P['L_cmc']:.6g}"); a(f"Kcmc Lca Lcb {P['k_cmc']}")
    a(f"Cwa l1_4 ps_l {P['Cw_cmc']:.6g}"); a(f"Cwb l1_1 ps_n {P['Cw_cmc']:.6g}")
    a(f"Rpa l1_4 ps_l {P.get('Rp_cmc', 1e12):.6g}"); a(f"Rpb l1_1 ps_n {P.get('Rp_cmc', 1e12):.6g}")
    a(f"Rzcd ps_l ps_n {P['R_zcd']:.6g}"); a(f"Cpsin ps_l ps_n {P['C_ps_in']:.6g}"); a("Rpsin ps_l ps_n 1e6")
    a(f"Cpsy ps_n gndb {P['C_ps_y']:.6g}"); a(f"Cgnd gndb 0 {P['C_gnd_rgp']:.6g}"); a("Rgndb gndb 0 1e9")
    a(f"Ccs chs gndb {P.get('C_cs', 1e-15):.6g}")
    return e


def netlist_ac(P, source="triac", fstart=1e5, fstop=40e6, ppd=200):
    e = element_list(P, "ac")
    if source == "triac":
        e.append("Vtri q1_2 q1_1 dc 0 ac 1")
    elif source == "psu_dm":
        e.append("Ips ps_l ps_n dc 0 ac 1")
    elif source == "psu_cm":           # CM noise current from the HLK primary into the secondary/board ground
        e.append("Ipsc gndb ps_n dc 0 ac 1")
    elif source == "selv":             # SELV-ground noise EMF relative to the reference plane (Thevenin, ideal)
        e = [x for x in e if not x.startswith(("Cgnd ", "Rgndb "))]
        e.append("Vsel gndb 0 dc 0 ac 1")
    elif source == "relay":            # arc voltage source in series with the K1 contact
        e = [x for x in e if not x.startswith("Rk1 ")]
        e.append("Vrly k1c k1no dc 0 ac 1")
    body = "\n".join(e)
    return f"* scope A front end AC\n{body}\n.ac dec {ppd} {fstart:g} {fstop:g}\n.end\n"


def conduction_control(P, t_end, pre=0.0):
    """PWL control c(t) in [0,1] for the triac (1 = conducting) for every half cycle in [0, t_end].
    Returns list of (t, c) breakpoints and the list of turn-on / turn-off times."""
    vpk = math.sqrt(2) * P["Vrms"]; w = 2 * math.pi * P["f"]
    ton = math.asin(min(P["V_on"] / vpk, 1.0)) / w
    toff = math.asin(min(P["I_H"] * P["R_heater"] / vpk, 1.0)) / w
    half = 0.5 / P["f"]
    pts = [(0.0, 0.0)]
    ons, offs = [], []
    k = 0
    while k * half < t_end:
        t1 = k * half + ton
        t2 = (k + 1) * half - toff
        fire = P.get("pattern") is None or P["pattern"][k % len(P["pattern"])]
        if fire and t1 < t_end:
            n = 8   # raised-cosine collapse sampled in 8 steps
            for i in range(n + 1):
                tt = t1 + P["t_f"] * i / n
                pts.append((tt, 0.5 - 0.5 * math.cos(math.pi * i / n)))
            pts.append((t2, 1.0)); pts.append((t2 + P["t_off"], 0.0))
            ons.append(t1); offs.append(t2)
        k += 1
    return pts, ons, offs


def netlist_tran(P, t_end, tmax, save=("rx_l", "rx_n")):
    e = element_list(P, "tran")
    pts, ons, offs = conduction_control(P, t_end)
    pwl = " ".join(f"{t:.9e} {c:.6f}" for t, c in pts)
    e.append(f"Vctl ctl 0 PWL({pwl})")
    Rl = P["R_heater"]
    # c -> conductance giving an approximately linear triac-voltage collapse into the resistive load
    e.append(f"Btri q1_2 q1_1 I = V(q1_2,q1_1) * max(V(ctl),1e-9) / ({Rl}*(1-min(V(ctl),1)) + 0.02*min(V(ctl),1) + 1e-6)")
    body = "\n".join(e)
    sv = " ".join(f"v({n})" for n in save)
    return (f"* scope A front end transient\n{body}\n.options reltol=1e-4 abstol=1e-9 vntol=1e-7 method=gear\n"
            f".save {sv}\n.tran {tmax:g} {t_end:g} 0 {tmax:g} uic\n.end\n"), ons, offs


def triac_voltage_waveform(P, n=2 ** 21, pattern_halfcycles=None):
    """One mains period (20 ms) of the triac voltage for the source-substitution model, sampled at n points.
    v_tri = v_line * (1 - c(t)); the triac is assumed to see the full line voltage while off."""
    T = 1.0 / P["f"]
    t = np.arange(n) * T / n
    vpk = math.sqrt(2) * P["Vrms"]; w = 2 * math.pi * P["f"]
    v = vpk * np.sin(w * t)
    ton = math.asin(min(P["V_on"] / vpk, 1.0)) / w
    toff = math.asin(min(P["I_H"] * P["R_heater"] / vpk, 1.0)) / w
    c = np.zeros(n)
    for k in range(2):
        t1 = k * T / 2 + ton; t2 = (k + 1) * T / 2 - toff
        x = np.clip((t - t1) / P["t_f"], 0, 1)
        on = 0.5 - 0.5 * np.cos(np.pi * x)
        off = np.clip(1 - (t - t2) / P["t_off"], 0, 1)
        m = (t >= t1)
        c = np.where(m, np.minimum(on, off), c) if k == 0 else np.where(m & (t < T), np.maximum(c, np.minimum(on, off)), c)
    return t, v * (1 - c)
