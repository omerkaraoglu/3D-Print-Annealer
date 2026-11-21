"""Earthed (class I) variant of the scope-A conducted-emission model.

Imports the committed scope-A modules READ-ONLY from ../../emc_tests/A_mains_emission (frontend, emission_core,
receiver); their netlist is post-processed here. Nothing in that folder is written (sys.dont_write_bytecode, own
results.json in this folder).

Changes against the unearthed model (owner statement 2026-11-21: oven chassis and sheet metal earthed; details assumed):
  * chassis node 'chs' bonded to PE: internal bond wire L_bond (0.3 uH nominal, 0.1-3 uH) -> PE conductor of a 3-core
    1 m cord (self 1.38 uH, k 0.77 to L and N, 50 pF to each), plug end on the AMN reference ground
    (EN 55014-1 5.2.2.1, PDF p. 42). C_ch (chassis to RGP) is kept as a 30 pF stray in parallel.
  * fan motor frame on the earthed chassis: winding -> frame 150 pF (50-300 pF, assumed).
  * design state 2026-11-21: RV2 -> 1.5KE440CA TVS across the triac (25 pF assumed, replaces 120 pF);
    RV3 = TVR14431 370 pF LINE_FUSED-NEUT (L40.2 -> C40.2 neutral copper, 15 nH); no Y1; 1 nF ZCD node and 150 ohm RN
    arrays do not enter the mains model; U5 800 V driver assumed to have the MOC3052 gate threshold.
  * SELV ground vs chassis (thermocouple WRNT-02 ring probe bolted to the chassis):
      'insulated' : junction capacitance C_jn (50 pF, 20-200 pF assumed) in series with the board input network
      'grounded'  : junction on the ring -> lead 0.5 uH -> board input network
      board input network (netlist): per lead TVS PESD5V0S1BA to GND (35 pF typ, assumed) || 1 k (R220/221) + 10 nF
                   (C221/222) to GND; both leads in parallel -> 70 pF || (500 ohm + 20 nF)
      'bonded'    : deliberate SELV-to-chassis wire at the board, 0.15 uH + 10 mohm
Fix options (all parameterised): input CMC at J3 + Y caps to a PCB PE terminal, Y caps only, heater-lead CMC,
single-lead inductor in the heater A1 lead.
"""
import os, sys, math, re
HERE = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.abspath(os.path.join(HERE, "..", "..", "emc_tests", "A_mains_emission"))
sys.path.insert(0, OLD)
import common as oc            # noqa: E402  (sets sys.path for ngspice_helper; its save_results is NOT used)
import numpy as np             # noqa: E402
import ngspice_helper as ng    # noqa: E402
import frontend as fe          # noqa: E402
import emission_core as ec     # noqa: E402
import receiver as rx          # noqa: E402
from common import lim_qp, lim_av   # noqa: E402

EARTHED = dict(fe.NOMINAL)
EARTHED.update({
    "earthed": True, "L_bond": 0.3e-6, "R_bond": 0.005, "k_pe": 0.77, "C_cord_pe": 50e-12, "C_ch": 30e-12,
    "C_fanframe": 150e-12, "C_RV2": 25e-12, "RV3": True,
    "selv": "insulated", "C_jn": 50e-12, "L_probe": 0.5e-6, "C_tvs_in": 70e-12, "R_in_tc": 500.0, "C_in_tc": 20e-9,
    "L_selvbond": 0.15e-6,
    "Rp_cmc": 15e3,
    # fixes (off by default)
    "fix_in_cmc": None,      # dict(L, k, Cw, Rp, Rdc)
    "fix_y": None,           # dict(C, esl, L_pe_wire)
    "fix_heater_cmc": None,  # dict(L, k, Cw, Rp, Rdc)
    "fix_lead_L": None,      # dict(L, Rp, Cw)
})

CMC_6A = {"L": 1.8e-3, "k": 0.99, "Cw": 15e-12, "Rp": 5e3, "Rdc": 0.02}   # 6 A 1.8 mH class (Schaffner RN x42-6-02 table row); k, Cw, Rp assumed


def _sub_nodes(line, mapping):
    toks = line.split()
    for i in (1, 2):
        if i < len(toks) and toks[i] in mapping:
            toks[i] = mapping[toks[i]]
    return " ".join(toks)


def element_list(P, mode):
    Q = dict(P)
    caps = list(Q.get("extra_caps", []))
    if Q.get("RV3"):
        caps.append(("l40_2", "c40_2", 370e-12, 15e-9))
    Q["extra_caps"] = caps
    e = fe.element_list(Q, mode)
    out = []
    board_map = {}
    if Q.get("fix_in_cmc") or Q.get("fix_y"):
        board_map = {"j3_1": "jb_1", "j3_2": "jb_2"}
    for x in e:
        name = x.split()[0]
        if name in ("Cch", "Ccs"):
            continue
        if Q.get("fix_heater_cmc") or Q.get("fix_lead_L"):
            if name == "La1":
                x = _sub_nodes(x, {"r1_1": "ha"})
            if name == "Lr1n" and Q.get("fix_heater_cmc"):
                x = _sub_nodes(x, {"r1_2": "hb"})
        if board_map and name not in ("Lcd1", "Lcd2", "Ccd", "Ccg1", "Ccg2"):
            x = _sub_nodes(x, board_map)
        out.append(x)
    a = out.append
    a(f"Cch chs 0 {Q['C_ch']:.6g}")
    if Q.get("earthed", True):
        a(f"Lpeb chs peb {Q['L_bond']:.6g}"); a(f"Rpeb peb pe_in {Q['R_bond']:.6g}")
        a(f"Lcd3 pe_amn pe_in {Q['L_cord']:.6g}"); a(f"Kcd13 Lcd1 Lcd3 {Q['k_pe']}"); a(f"Kcd23 Lcd2 Lcd3 {Q['k_pe']}")
        a("Rpe0 pe_amn 0 0.001")
        a(f"Ccp1 j3_1 pe_in {Q['C_cord_pe']:.6g}"); a(f"Ccp2 j3_2 pe_in {Q['C_cord_pe']:.6g}")
    a(f"Cff fanm chs {Q['C_fanframe']:.6g}")
    # SELV ground <-> chassis
    s = Q["selv"]
    if s in ("insulated", "grounded"):
        a(f"Ctvs_tc tcn gndb {Q['C_tvs_in']:.6g}"); a(f"Rin_tc tcn tcm {Q['R_in_tc']:.6g}"); a(f"Cin_tc tcm gndb {Q['C_in_tc']:.6g}")
        a(f"Lpr tcj tcn {Q['L_probe']:.6g}")
        if s == "insulated":
            a(f"Cjn chs tcj {Q['C_jn']:.6g}"); a("Rjn chs tcj 1e9")
        else:
            a("Rjn chs tcj 0.01")
    elif s == "bonded":
        a(f"Lsb chs sbx {Q['L_selvbond']:.6g}"); a("Rsb sbx gndb 0.01")
    elif s == "floating":
        a("Rjn chs gndb 1e12")
    # fixes
    if Q.get("fix_in_cmc") or Q.get("fix_y"):
        c = Q.get("fix_in_cmc")
        if c:
            a(f"Lia j3_1 jb_1 {c['L']:.6g}"); a(f"Lib j3_2 jb_2 {c['L']:.6g}"); a(f"Kin Lia Lib {c['k']}")
            a(f"Cwia j3_1 jb_1 {c['Cw']:.6g}"); a(f"Cwib j3_2 jb_2 {c['Cw']:.6g}")
            a(f"Rpia j3_1 jb_1 {c['Rp']:.6g}"); a(f"Rpib j3_2 jb_2 {c['Rp']:.6g}")
        else:
            a("Rsh1 j3_1 jb_1 1e-4"); a("Rsh2 j3_2 jb_2 1e-4")
        y = Q.get("fix_y")
        if y:
            a(f"Lpebrd pe_brd chs {y['L_pe_wire']:.6g}")   # PCB PE terminal -> chassis star point
            a(f"Cy1 jb_1 cy1m {y['C']:.6g}"); a(f"Ly1 cy1m pe_brd {y['esl']:.6g}")
            a(f"Cy2 jb_2 cy2m {y['C']:.6g}"); a(f"Ly2 cy2m pe_brd {y['esl']:.6g}")
            a("Rpebrd pe_brd 0 1e9")
    c = Q.get("fix_heater_cmc")
    if c:
        a(f"Lha ha r1_1 {c['L']:.6g}"); a(f"Lhb hb r1_2 {c['L']:.6g}"); a(f"Kh Lha Lhb {c['k']}")
        a(f"Cwha ha r1_1 {c['Cw']:.6g}"); a(f"Cwhb hb r1_2 {c['Cw']:.6g}")
        a(f"Rpha ha r1_1 {c['Rp']:.6g}"); a(f"Rphb hb r1_2 {c['Rp']:.6g}")
    c = Q.get("fix_lead_L")
    if c:
        a(f"Lla ha r1_1 {c['L']:.6g}"); a(f"Cwla ha r1_1 {c['Cw']:.6g}"); a(f"Rpla ha r1_1 {c['Rp']:.6g}")
    return out


def netlist_ac(P, source="triac", fstart=1e5, fstop=40e6, ppd=200):
    e = element_list(P, "ac")
    if source == "triac":
        e.append("Vtri q1_2 q1_1 dc 0 ac 1")
    elif source == "psu_cm":
        e.append("Ipsc gndb ps_n dc 0 ac 1")
    elif source == "selv":
        e = [x for x in e if not x.startswith(("Cgnd ", "Rgndb "))]
        e.append("Vsel gndb 0 dc 0 ac 1")
    return "* earthed front end AC\n" + "\n".join(e) + f"\n.ac dec {ppd} {fstart:g} {fstop:g}\n.end\n"


def ac_transfer(P, source="triac", ppd=200):
    r = ng.run_netlist(netlist_ac(P, source, ppd=ppd))
    return np.real(r["frequency"]), r["v(rx_l)"], r["v(rx_n)"]


F_MC = np.unique(np.concatenate([np.logspace(np.log10(150e3), np.log10(30e6), 36), np.logspace(np.log10(0.2e6), np.log10(3e6), 30), [150e3, 500e3]]))


def margins_per_line(sc):
    f = np.array(sc["f"]); out = {}
    for side in ("L", "N"):
        for det, lim in (("QP", lim_qp), ("AV", lim_av)):
            m = np.array([lim(x) for x in f]) - np.array(sc[side][det])
            i = int(np.argmin(m))
            out[f"{det}_{side}"] = {"margin_dB": round(float(m[i]), 2), "f_MHz": round(float(f[i] / 1e6), 3)}
    return out


def evalP(P, fscan=F_MC, want_scan=False):
    H = ac_transfer(P)
    f, XL, XN = ec.lisn_lines(P, H)
    sc = ec.scan(f, XL, XN, f_scan=fscan)
    m = margins_per_line(sc)
    return (m, sc) if want_scan else m


WORST = {"V_on": 40.0, "t_f": 0.2e-6, "L_heater": 1e-6, "ESL40": 30e-9, "Cp40": 20e-12, "L40": 90e-6, "C40": 0.9e-6, "C1": 80e-9,
         "trace_scale": 1.5, "C_hc": 1e-9, "Rp40": 100e3}
