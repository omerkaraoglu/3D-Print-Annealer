"""Test A1: EN 55014-1 mains-terminal disturbance voltage 150 kHz-30 MHz (QP, AV), plus A2 load-terminal check.

Run:  python -X utf8 conducted.py            (nominal, modes, validation, HLK bound, proposals)
      python -X utf8 conducted.py --mc 150   (adds the Monte-Carlo / corner sweep)
Writes results.json sections 'A1_conducted', 'A2_load_terminal' and plots/A1_*.png.
"""
import math, os, sys, time, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import (PLOTS, HERE, save_results, lim_qp, lim_av, lim_assoc_qp, lim_assoc_av, dBuV, LIMIT_SRC)
import frontend as fe
import emission_core as ec
import receiver as rx
import patterns as pt

RNG = np.random.default_rng(20261118)
OUT = {"limit_source": LIMIT_SRC, "receiver": "receiver.py (CISPR 16-1-1 Band B model, constants NOT READ FROM THE STANDARD, Schwarzbeck note)",
       "lisn": "50 ohm || (50 uH + 5 ohm) V-network, CISPR 16-1-2 NOT READ FROM THE STANDARD (Schwarzbeck NSLK 8117 listing)",
       "params_nominal": {k: v for k, v in fe.NOMINAL.items()}, "params_doc": fe.PARAMS_DOC}


def full_scan(P, H=None, f_scan=ec.F_SCAN):
    f, XL, XN = ec.lisn_lines(P, H)
    sc = ec.scan(f, XL, XN, f_scan=f_scan)
    return sc, (f, XL, XN)


def plot_scan(sc, title, fn, extra=None):
    f = np.array(sc["f"]) / 1e6
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.semilogx(f, sc["L"]["QP"], "C0-", lw=1.4, label="QP, line L")
    ax.semilogx(f, sc["N"]["QP"], "C1-", lw=1.4, label="QP, line N")
    ax.semilogx(f, sc["L"]["AV"], "C0:", lw=1.2, label="AV, line L")
    ax.semilogx(f, sc["N"]["AV"], "C1:", lw=1.2, label="AV, line N")
    ax.semilogx(f, sc["N"]["PK"], color="0.6", lw=0.8, label="peak, line N (information)")
    ff = np.logspace(np.log10(0.15), np.log10(30), 400)
    ax.semilogx(ff, [lim_qp(x * 1e6) for x in ff], "k-", lw=2, label="EN 55014-1 Table 5 col. 2 QP limit")
    ax.semilogx(ff, [lim_av(x * 1e6) for x in ff], "k--", lw=2, label="EN 55014-1 Table 5 col. 3 AV limit")
    if extra:
        for lab, (xf, yv, sty) in extra.items():
            ax.semilogx(np.array(xf) / 1e6, yv, sty, lw=1.2, label=lab)
    ax.set_xlim(0.15, 30); ax.set_ylim(-20, 100)
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("Disturbance voltage at the AMN receiver port (dBµV)")
    ax.set_title(title, fontsize=10); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, fn), dpi=140); plt.close(fig)


def summarise(sc):
    m = ec.margins(sc)
    f = np.array(sc["f"])
    pick = {}
    for f0 in (150e3, 500e3, 1.4e6, 30e6):
        i = int(np.argmin(abs(f - f0)))
        pick[f"{f0/1e6:g}MHz"] = {s: {d: round(sc[s][d][i], 1) for d in ("QP", "AV", "PK")} for s in ("L", "N")}
    return {"worst": m, "at_click_freqs": pick}


# ------------------------------------------------------------------ validation -------------------------------
def validation():
    v = {}
    # (a) ideal L-C filter: SPICE vs analytic (no parasitics, no CM, no cord, fan off, PSU branch open)
    P = dict(fe.NOMINAL)
    P.update(Cp40=1e-15, Rp40=1e12, ESL40=1e-15, ESR40=1e-6, C1=1e-15, ESL1=1e-15, C_RV1=1e-15, C_RV2=1e-15, C4=1e-15,
             trace_scale=1e-6, L_F3=1e-15, R_F3=1e-6, L_heater=1e-15, C_hc=1e-15, C_ch=1e-15, L_cord=1e-15, k_cord=0.0,
             C_cord=1e-15, C_cord_g=1e-15, fan_on=False, C_fan=1e-15, R_F1=1e9, R40=1e-6, Cw_cmc=1e-15, C_ps_in=1e-15, R_zcd=1e12,
             C_ps_y=1e-15)
    f, HL, HN = ec.ac_transfer(P, fstart=1e5, fstop=3e7, ppd=20)
    w = 2 * np.pi * f
    Zl = 1 / (1 / (P["R_lisn"] + 1j * w * P["L_lisn"]) + 1 / (P["R_rec"] + 1 / (1j * w * P["C_coup"])))
    Zrx = P["R_rec"] / (P["R_rec"] + 1 / (1j * w * P["C_coup"]))      # receiver share of the port voltage
    Zmain = 2 * Zl + 1j * w * P["L40"]
    Zc = 1 / (1j * w * P["C40"])
    Zsh = 1 / (1 / Zc + 1 / Zmain)
    I_tot = 1.0 / (P["R_heater"] + Zsh)                  # 1 V triac source in series with the heater
    V_f = I_tot * Zsh
    V_rx = V_f / Zmain * Zl * Zrx
    err = 20 * np.log10(np.abs(HL) / np.abs(V_rx))
    v["ideal_LC_spice_vs_analytic_dB"] = {"max_abs_dev": round(float(np.max(np.abs(err))), 3),
                                          "at_150k_spice_dB": round(float(20 * np.log10(abs(HL[np.argmin(abs(f - 150e3))]))), 2),
                                          "at_150k_analytic_dB": round(float(20 * np.log10(abs(V_rx[np.argmin(abs(f - 150e3))]))), 2)}
    # (b) pass-1/2 topology (no filter in the heater path) vs the 2026-11-12 one-pulse estimate (93 dBuV QP at 150 kHz, V_on 23 V)
    P = dict(fe.NOMINAL); P.update(no_filter=True, V_on=23.0)
    sc, _ = full_scan(P, f_scan=np.array([150e3, 500e3, 1e6, 5e6]))
    v["no_filter_Von23_QP_dBuV"] = {"this_model_L": [round(x, 1) for x in sc["L"]["QP"]], "this_model_N": [round(x, 1) for x in sc["N"]["QP"]],
                                    "freqs_MHz": [0.15, 0.5, 1, 5], "old_estimate": [93, 75, 63, 36],
                                    "note": "old model: tau=L/R exponential step through 2x50 uH LISN; here source substitution with 0.5 us collapse"}
    # (c) transient (full nonlinear circuit) vs source-substitution, from tran_validation.npz if present
    tv = os.path.join(HERE, "tran_validation.json")
    if os.path.exists(tv):
        v["transient_vs_LTI"] = json.load(open(tv))
    return v


# ------------------------------------------------------------------ modes ------------------------------------
def regulating_readings(P, H, duty_list=(0.05, 0.2, 0.5, 0.8, 0.99), f_list=(150e3, 500e3, 1.4e6, 30e6), T_obs=15.0):
    """M2: readings for the actual firing sequence (event-based detector, 15 s observation per EN 55014-1 5.4.1.1).
    The IF envelope of one half-cycle event is cut from the 100 % periodic envelope."""
    f, XL, XN = ec.lisn_lines(P, H)
    res = {}
    vpk = math.sqrt(2) * P["Vrms"]; w = 2 * math.pi * P["f"]
    ton = math.asin(P["V_on"] / vpk) / w
    for fam in ("current", "decided"):
        res[fam] = {}
        for d in duty_list:
            n = int(T_obs * 50) + 2000
            acc0 = 0
            seq = pt.PATTERNS[fam](d, n)
            # observe a 15 s window that contains the start of an on-burst (worst case for the burst frame)
            k0 = 0
            if fam == "decided":
                k0 = 1000 - 1 if d > 0 else 0
            seq = seq[k0:k0 + int(T_obs * 50)]
            cyc = np.nonzero(seq)[0]
            ev = np.sort(np.concatenate([cyc * 0.02, cyc * 0.02 + 0.01])) + 0.0    # zero-crossing times of fired half cycles
            row = {}
            for f0 in f_list:
                best = {}
                for side, X in (("L", XL), ("N", XN)):
                    t, e = rx.envelope_periodic(f, X, f0, 0.02, n_t=8192)
                    dt = t[1] - t[0]
                    # one event = window from -0.6 ms to +2.4 ms around the first zero crossing (turn-off + turn-on)
                    i0 = int(round((0.02 - 0.6e-3) / dt)) % len(e)
                    pulse = np.roll(e, -i0)[: int(3.0e-3 / dt)]
                    r = rx.readings_events(pulse, dt, ev, T_obs) if len(ev) else {"QP": 1e-12, "AV": 1e-12, "PK": 1e-12}
                    best[side] = {k: round(float(dBuV(r[k])), 1) for k in ("QP", "AV")}
                row[f"{f0/1e6:g}MHz"] = best
            res[fam][f"{d:g}"] = row
    return res


def hlk_bound(P):
    """Insertion loss of the board's input network for noise injected at the HLK-10M05 AC pins, relative to the
    vendor's reference circuit (1 A fuse + 0.1 uF X2 + 10 mH CMC directly at the mains cord; HLK datasheet p. 12)."""
    f, HL, HN = ec.ac_transfer(P, source="psu_dm", ppd=40)
    Pr = dict(P)
    # reference: remove L40/C40/RV1/heater/fan; C1 + CMC directly at J3 (approximate: no_filter + no heater + fan off)
    Pr.update(no_filter=True, R_heater=1e9, L_heater=1e-9, fan_on=False, C_hc=1e-15)
    Pr["extra_caps"] = [("lfused", "j3_2", 100e-9, 12e-9)]
    fr, HLr, HNr = ec.ac_transfer(Pr, source="psu_dm", ppd=40)
    il_dm = 20 * np.log10(np.maximum(np.abs(HLr), np.abs(HNr)) / np.maximum(np.abs(HL), np.abs(HN)))
    fc, CL, CN = ec.ac_transfer(P, source="psu_cm", ppd=40)
    fcr, CLr, CNr = ec.ac_transfer(Pr, source="psu_cm", ppd=40)
    il_cm = 20 * np.log10(np.maximum(np.abs(CLr), np.abs(CNr)) / np.maximum(np.abs(CL), np.abs(CN)))
    sel = (f >= 150e3) & (f <= 30e6)
    out = {"model": "IL_extra = |V_AMN(reference circuit)| / |V_AMN(this board)| for a 1 A source at the HLK AC pins",
           "DM_IL_extra_dB": {"min": round(float(il_dm[sel].min()), 1), "at_150k": round(float(np.interp(150e3, f, il_dm)), 1),
                              "at_500k": round(float(np.interp(500e3, f, il_dm)), 1), "at_5M": round(float(np.interp(5e6, f, il_dm)), 1),
                              "at_30M": round(float(np.interp(30e6, f, il_dm)), 1)},
           "CM_IL_extra_dB": {"min": round(float(il_cm[sel].min()), 1), "max": round(float(il_cm[sel].max()), 1)},
           "transimpedance_DM_dBohm_150k": round(float(20 * np.log10(max(abs(np.interp(150e3, f, np.abs(HL))), abs(np.interp(150e3, f, np.abs(HN)))))), 1),
           "max_HLK_DM_current_for_QP_limit_150k_dBuA": None}
    zt = np.maximum(np.abs(HL), np.abs(HN))
    # DM noise current at the HLK pins that would just reach the QP limit (narrowband, continuous): I = V_lim / Z_t
    out["max_HLK_DM_current_for_QP_limit_dBuA"] = {f"{fx/1e6:g}MHz": round(float(lim_qp(fx) - 20 * np.log10(np.interp(fx, f, zt))), 1)
                                                   for fx in (150e3, 300e3, 500e3, 1e6, 5e6, 30e6)}
    zc = np.maximum(np.abs(CL), np.abs(CN))
    out["max_HLK_CM_current_for_QP_limit_dBuA"] = {f"{fx/1e6:g}MHz": round(float(lim_qp(fx) - 20 * np.log10(np.interp(fx, fc, zc))), 1)
                                                   for fx in (150e3, 300e3, 500e3, 1e6, 5e6, 30e6)}
    out["max_HLK_DM_current_for_AV_limit_dBuA"] = {f"{fx/1e6:g}MHz": round(float(lim_av(fx) - 20 * np.log10(np.interp(fx, f, zt))), 1)
                                                   for fx in (150e3, 300e3, 500e3, 1e6, 5e6, 30e6)}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogx(f / 1e6, il_dm, label="DM: extra insertion loss vs HLK reference circuit")
    ax.semilogx(fc / 1e6, il_cm, label="CM: extra insertion loss vs HLK reference circuit")
    ax.set_xlim(0.15, 30); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8)
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("dB"); ax.set_title("HLK-10M05 black box: what the board adds in front of the module")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A1_hlk_insertion_loss.png"), dpi=140); plt.close(fig)
    return out


def load_terminal(P):
    """A2: disturbance voltage at the heater terminal R1.1 and the fan terminal J4.1 to the reference ground
    (information only - see report: not an associated port)."""
    f, HL, HN, Hr1, Hj4 = ec.ac_transfer(P, extra=("r1_1", "j4_1"))
    t, v = fe.triac_voltage_waveform(P)
    fl, X = ec.line_spectrum(t, v)
    sel = (fl >= 100e3) & (fl <= f[-1]); fl, X = fl[sel], X[sel]
    out = {}
    for name, H in (("heater_R1.1", Hr1), ("fan_J4.1", Hj4)):
        Y = X * ec.interp_c(fl, f, H)
        res = []
        for f0 in (150e3, 500e3, 1.4e6, 5e6, 30e6):
            tt, e = rx.envelope_periodic(fl, Y, f0, 0.02)
            r = rx.readings_periodic(tt, e)
            res.append({"f_MHz": f0 / 1e6, "QP_dBuV": round(float(dBuV(r["QP"])), 1), "AV_dBuV": round(float(dBuV(r["AV"])), 1),
                        "Table5_col4_QP": lim_assoc_qp(f0), "Table5_col5_AV": lim_assoc_av(f0)})
        out[name] = res
    out["note"] = "node voltage to the RGP with ideal (infinite-impedance) probe; a 1500 ohm probe (CISPR 16-1-2) would read the same within <1 dB at these source impedances"
    return out


# ------------------------------------------------------------------ Monte Carlo ------------------------------
MC_FSCAN = np.unique(np.concatenate([np.logspace(np.log10(150e3), np.log10(30e6), 36), [150e3, 500e3]]))


def mc_draw(von=(10.0, 40.0)):
    P = dict(fe.NOMINAL)
    P["V_on"] = RNG.uniform(*von)
    P["t_f"] = 10 ** RNG.uniform(np.log10(0.2e-6), np.log10(2e-6))
    P["L_heater"] = 10 ** RNG.uniform(np.log10(1e-6), np.log10(20e-6))
    P["ESL40"] = RNG.uniform(10e-9, 30e-9)
    P["Cp40"] = RNG.uniform(3e-12, 20e-12)
    P["L40"] *= RNG.uniform(0.9, 1.1)
    P["C40"] *= RNG.uniform(0.9, 1.1)
    P["C1"] *= RNG.uniform(0.8, 1.2)
    P["trace_scale"] = RNG.uniform(0.5, 1.5)
    P["C_hc"] = 10 ** RNG.uniform(np.log10(100e-12), np.log10(1e-9))
    P["C_ch"] = RNG.uniform(20e-12, 150e-12)
    P["Rm"] = RNG.uniform(0.1, 1.0); P["Lm"] = RNG.uniform(0.0, 1.5e-3)
    P["k_cord"] = RNG.uniform(0.6, 0.85)
    P["Rp40"] = 10 ** RNG.uniform(np.log10(5e3), np.log10(100e3))
    return P


MC_KEYS = ["V_on", "t_f", "L_heater", "ESL40", "Cp40", "L40", "C40", "C1", "trace_scale", "C_hc", "C_ch", "Rm", "Lm", "k_cord", "Rp40"]


def run_mc(n, von=(10.0, 40.0)):
    rows = []
    t0 = time.time()
    for i in range(n):
        P = mc_draw(von)
        sc, _ = full_scan(P, f_scan=MC_FSCAN)
        m = ec.margins(sc)
        rows.append({"params": {k: P[k] for k in MC_KEYS}, "QP_margin": m["QP"]["margin_dB"], "QP_f_MHz": m["QP"]["f_MHz"],
                     "AV_margin": m["AV"]["margin_dB"], "AV_f_MHz": m["AV"]["f_MHz"], "line": m["QP"]["line"]})
        if (i + 1) % 10 == 0:
            print(f"  MC {i+1}/{n}  {time.time()-t0:.0f} s  worst QP so far {min(r['QP_margin'] for r in rows):.1f} dB", flush=True)
    qp = np.array([r["QP_margin"] for r in rows]); av = np.array([r["AV_margin"] for r in rows])
    # sensitivity: rank correlation of each parameter with the QP margin
    from scipy.stats import spearmanr
    sens = {}
    for k in MC_KEYS:
        x = np.array([r["params"][k] for r in rows])
        rho = spearmanr(x, qp).correlation
        sens[k] = round(float(rho), 2)
    worst = rows[int(np.argmin(qp))]
    return {"n": n, "V_on_range": von, "QP_margin_dB": {"min": round(float(qp.min()), 1), "p5": round(float(np.percentile(qp, 5)), 1), "median": round(float(np.median(qp)), 1)},
            "AV_margin_dB": {"min": round(float(av.min()), 1), "p5": round(float(np.percentile(av, 5)), 1), "median": round(float(np.median(av)), 1)},
            "spearman_rho_vs_QP_margin": sens, "worst_case_params": worst, "rows": rows}


def corners():
    """Deterministic corners: each single parameter at its unfavourable end, then all at once."""
    base = dict(fe.NOMINAL)
    worst = {"V_on": 40.0, "t_f": 0.2e-6, "L_heater": 1e-6, "ESL40": 30e-9, "Cp40": 20e-12, "L40": 90e-6, "C40": 0.9e-6,
             "C1": 80e-9, "trace_scale": 1.5, "C_hc": 1e-9, "C_ch": 150e-12, "Rp40": 100e3}
    res = {}
    sc, _ = full_scan(base, f_scan=MC_FSCAN)
    res["nominal"] = ec.margins(sc)
    for k, v in worst.items():
        P = dict(base); P[k] = v
        sc, _ = full_scan(P, f_scan=MC_FSCAN)
        res[f"{k}={v:g}"] = ec.margins(sc)
    P = dict(base); P.update(worst)
    sc, lines = full_scan(P)
    res["all_worst"] = ec.margins(sc)
    return res, sc, P


# ------------------------------------------------------------------ proposals --------------------------------
def proposal_scan(label, mods):
    P = dict(fe.NOMINAL); P.update(mods)
    sc, _ = full_scan(P)
    return label, sc, ec.margins(sc)


def main():
    t0 = time.time()
    OUT["validation"] = validation()
    print("validation done", time.time() - t0, json.dumps(OUT["validation"], indent=0)[:800])
    P = dict(fe.NOMINAL)
    H = ec.ac_transfer(P)
    sc1, lines = full_scan(P, H)
    OUT["M1_heater_100pct_fan_on"] = summarise(sc1); OUT["M1_heater_100pct_fan_on"]["scan"] = sc1
    plot_scan(sc1, "A1 conducted, mode M1: heater 100 %, fan on, nominal parameters (V_on 20 V, t_f 0.5 µs)", "A1_M1_nominal.png")
    # DM / CM split (information)
    f = H[0]
    OUT["transfer_dB_per_V_triac"] = {f"{x/1e6:g}MHz": {"L": round(float(20*np.log10(abs(np.interp(x, f, np.abs(H[1]))))), 1),
                                                        "N": round(float(20*np.log10(abs(np.interp(x, f, np.abs(H[2]))))), 1),
                                                        "DM": round(float(20*np.log10(abs(np.interp(x, f, np.abs(H[1]-H[2]))/2))), 1),
                                                        "CM": round(float(20*np.log10(abs(np.interp(x, f, np.abs(H[1]+H[2]))/2))), 1)}
                                      for x in (150e3, 500e3, 1e6, 5e6, 10e6, 30e6)}
    # V_on sweep at nominal parasitics
    OUT["V_on_sweep"] = {}
    for von in (10.0, 20.0, 30.0, 40.0):
        Pv = dict(P); Pv["V_on"] = von
        s, _ = full_scan(Pv, H, f_scan=MC_FSCAN)
        OUT["V_on_sweep"][f"{von:g}"] = ec.margins(s)
    # M1 with the fan off and with no CM path (heater-chassis C) to separate mechanisms
    for lab, mods in (("fan_off", {"fan_on": False}), ("no_heater_CM_path", {"C_hc": 1e-15})):
        Pm = dict(P); Pm.update(mods)
        s, _ = full_scan(Pm, f_scan=MC_FSCAN)
        OUT[f"M1_{lab}"] = ec.margins(s)
    # M2 regulating, both firmware patterns
    OUT["M2_regulating"] = regulating_readings(P, H)
    OUT["M2_regulating"]["note"] = "15 s observation (5.4.1.1); decided pattern observed across a frame start; readings <= M1 because each event is identical and fewer events per second"
    # M3 heater off: no triac events; HLK bound
    OUT["M3_heater_off_HLK_bound"] = hlk_bound(P)
    OUT["A2_load_terminal_information"] = load_terminal(P)
    # corners
    cr, scw, Pw = corners()
    OUT["corners"] = cr
    plot_scan(scw, "A1 conducted, all unfavourable corners at once (V_on 40 V, t_f 0.2 µs, L_heater 1 µH, ...)", "A1_M1_all_worst_corners.png")
    OUT["corners_all_worst_scan"] = scw
    # proposal candidates (evaluated at the all-worst corner, where margins are smallest)
    props = {}
    for lab, mods in (
        ("P1: C1 100 nF moved to Q1.A2/R1.2 (short return to J3.2)", {"extra_caps": [("q1_2", "r1_2", 100e-9, 12e-9)], "C1": 1e-15}),
        ("P2: add 220 nF X2 Q1.A2 -> R1.2", {"extra_caps": [("q1_2", "r1_2", 220e-9, 15e-9)]}),
        ("P3: firmware fires at the ZCD window centre (V_on <= 15 V)", {"V_on": 15.0}),
    ):
        Pp = dict(Pw); Pp.update(mods)
        if "C1" in mods and mods["C1"] < 1e-12:
            Pp["C1"] = 1e-15
        s, _ = full_scan(Pp)
        props[lab] = {"margins_all_worst": ec.margins(s), "scan": s}
    OUT["proposals_at_all_worst_corner"] = props
    extra = {k.split(":")[0] + " QP N": (v["scan"]["f"], v["scan"]["N"]["QP"], st) for (k, v), st in zip(props.items(), ("g-", "m-", "c-"))}
    plot_scan(scw, "A1 all-worst corner with proposals (QP, line N)", "A1_proposals.png", extra=extra)
    if "--mc" in sys.argv:
        n = int(sys.argv[sys.argv.index("--mc") + 1])
        OUT["monte_carlo"] = run_mc(n)
        OUT["monte_carlo_proposal_Von_8_18"] = run_mc(n, (8.0, 18.0))
        mc = OUT["monte_carlo"]
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        ax[0].hist([r["QP_margin"] for r in mc["rows"]], bins=25); ax[0].set_xlabel("worst QP margin to Table 5 col. 2 (dB)")
        ax[1].hist([r["AV_margin"] for r in mc["rows"]], bins=25, color="C1"); ax[1].set_xlabel("worst AV margin to Table 5 col. 3 (dB)")
        for a in ax: a.set_ylabel("runs"); a.grid(alpha=0.3); a.axvline(6, color="k", ls="--", lw=1); a.axvline(0, color="r", lw=1)
        mp = OUT["monte_carlo_proposal_Von_8_18"]
        ax[0].hist([r["QP_margin"] for r in mp["rows"]], bins=25, alpha=0.6, color="C2", label="V_on 8-18 V (proposal F1)")
        ax[0].legend(fontsize=7)
        fig.suptitle(f"A1 Monte Carlo, {mc['n']} runs each (blue/orange: V_on 10-40 V; green: V_on 8-18 V); t_f 0.2-2 µs, parasitics, mains Z", fontsize=9)
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A1_monte_carlo.png"), dpi=140); plt.close(fig)
    OUT["runtime_s"] = round(time.time() - t0, 1)
    save_results("A1_conducted", OUT)
    print(json.dumps({k: OUT[k] for k in ("M1_heater_100pct_fan_on",)}, default=str)[:1500])


if __name__ == "__main__":
    main()
