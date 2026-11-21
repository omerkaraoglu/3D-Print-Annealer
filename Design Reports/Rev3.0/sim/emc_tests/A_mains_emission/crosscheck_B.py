"""Cross-check of scope-B hardware proposals against test A1 (EN 55014-1 Table 5 conducted emission).

P-D1 : Y1 capacitor SELV GND -> NEUT next to PS1 (470 pF / 1 nF / 2.2 nF, 5 nH ESL assumed), node gndb -> l1_1 (L1.1 on NEUT)
P-S2b: second TVR14431 (370 pF, TVR10391KSY.pdf p. 7) LINE_FUSED -> NEUT in front of L40 (node l40_2 -> c40_2, 15 nH assumed)
P-E1 : 1 nF on the ZCD collector node -> zcd_timing.py with +8.4 us edge delay (section A0_zcd_timing_E1)
Model change for this cross-check: oven chassis <-> SELV ground coupling C_cs (thermocouple probe/lead inside the oven),
assumed 20 pF nominal, MC 5-100 pF, plus a 'probe bonded to chassis' case (10 nF). The baseline is re-run with it.
CMC L1 core loss: 15 kohm parallel per winding (5-50 k in the MC); a lossless 10 mH CMC resonates with the
HLK primary-secondary capacitance near 265 kHz and gives a spurious, very sharp N-line peak (first run, not kept).
Monte Carlo: 120 paired draws (identical random parameters for every variant), with V_on 10-40 V (as designed) and
8-18 V (F1 firmware), 4 variants each, run in parallel processes.
Writes results.json sections 'A1_crosscheck_scopeB' and 'A1_F1_construction_grid'.
"""
import os, sys, time, json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import PLOTS, save_results, lim_qp, lim_av
import frontend as fe
import emission_core as ec
import conducted as cd

Y1 = lambda C: ("gndb", "l1_1", C, 5e-9)
S2B = ("l40_2", "c40_2", 370e-12, 15e-9)
VARIANTS = {"baseline": [], "P-D1 Y1 1nF": [Y1(1e-9)], "P-S2b MOV 370pF": [S2B], "P-D1 + P-S2b": [Y1(1e-9), S2B]}
F = np.unique(np.concatenate([cd.MC_FSCAN, np.logspace(np.log10(0.2e6), np.log10(1.2e6), 30)]))   # dense where CM resonates


def margins_per_line(sc):
    f = np.array(sc["f"]); out = {}
    for side in ("L", "N"):
        for det, lim in (("QP", lim_qp), ("AV", lim_av)):
            m = np.array([lim(x) for x in f]) - np.array(sc[side][det])
            i = int(np.argmin(m))
            out[f"{det}_{side}"] = {"margin_dB": round(float(m[i]), 2), "f_MHz": round(float(f[i] / 1e6), 3)}
    return out


def evalP(P, fscan=F):
    sc, _ = cd.full_scan(P, f_scan=fscan)
    return margins_per_line(sc)


def draws(n, seed=20261119):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        d = {"u_von": rng.uniform(), "t_f": 10 ** rng.uniform(np.log10(0.2e-6), np.log10(2e-6)),
             "L_heater": 10 ** rng.uniform(-6, np.log10(20e-6)), "ESL40": rng.uniform(10e-9, 30e-9), "Cp40": rng.uniform(3e-12, 20e-12),
             "L40": 100e-6 * rng.uniform(0.9, 1.1), "C40": 1e-6 * rng.uniform(0.9, 1.1), "C1": 100e-9 * rng.uniform(0.8, 1.2),
             "trace_scale": rng.uniform(0.5, 1.5), "C_hc": 10 ** rng.uniform(-10, -9), "C_ch": rng.uniform(20e-12, 150e-12),
             "Rm": rng.uniform(0.1, 1.0), "Lm": rng.uniform(0, 1.5e-3), "k_cord": rng.uniform(0.6, 0.85),
             "Rp40": 10 ** rng.uniform(np.log10(5e3), np.log10(100e3)), "C_cs": 10 ** rng.uniform(np.log10(5e-12), np.log10(100e-12)),
             "Rp_cmc": 10 ** rng.uniform(np.log10(5e3), np.log10(50e3))}
        out.append(d)
    return out


def mc_job(args):
    d, von, caps = args
    P = dict(fe.NOMINAL); P.update({k: v for k, v in d.items() if k != "u_von"})
    P["V_on"] = von[0] + d["u_von"] * (von[1] - von[0])
    P["extra_caps"] = caps
    return evalP(P)


def summarise_mc(rows):
    s = {}
    for k in rows[0]:
        m = np.array([r[k]["margin_dB"] for r in rows])
        s[k] = {"min": round(float(m.min()), 1), "p5": round(float(np.percentile(m, 5)), 1), "median": round(float(np.median(m)), 1),
                "f_MHz_at_min": rows[int(np.argmin(m))][k]["f_MHz"], "n_below_6dB": int((m < 6).sum())}
    return s


def selv_bound():
    """SELV-ground noise EMF (relative to the reference plane) that reaches the Table 5 limit on the worse AMN line,
    narrowband (continuous) noise: QP and AV read the rms of a sine -> V_max = limit - 20 lg|H|."""
    fq = [150e3, 300e3, 580e3, 1.2e6, 2.4e6, 3.6e6, 5e6, 10e6, 20e6, 30e6]
    res = {}
    for lab, caps in (("no Y1 (HLK primary-secondary 50 pF only)", []), ("Y1 470 pF", [Y1(470e-12)]), ("Y1 1 nF", [Y1(1e-9)]), ("Y1 2.2 nF", [Y1(2.2e-9)])):
        P = dict(fe.NOMINAL); P["extra_caps"] = caps
        f, HL, HN = ec.ac_transfer(P, source="selv", ppd=100)
        H = np.maximum(np.abs(HL), np.abs(HN))
        row = {}
        for x in fq:
            h = float(np.interp(x, f, H))
            row[f"{x/1e6:g}MHz"] = {"transfer_dB": round(20 * np.log10(h), 1),
                                    "Vn_max_QP_dBuV": round(lim_qp(x) - 20 * np.log10(h), 1),
                                    "Vn_max_AV_dBuV": round(lim_av(x) - 20 * np.log10(h), 1)}
        res[lab] = row
    res["note"] = ("ideal Thevenin EMF between SELV GND (gndb) and the reference plane, i.e. the open-circuit ground-noise "
                   "voltage scope C reports; narrowband noise is limited by the AV column (QP = AV for a steady sine). "
                   "Impulsive noise would be read lower by AV. Harmonic lines of the 580 kHz buck and 1.2 MHz boost: compare each line.")
    return res


def main():
    t0 = time.time()
    out = {"doc": __doc__}
    # ---- deterministic nominal + Y1 size + probe-bonded cases
    det = {}
    for von_lab, von in (("as designed V_on 20 V", 20.0), ("F1 V_on 15 V", 15.0)):
        rows = {}
        for lab, caps in list(VARIANTS.items()) + [("P-D1 Y1 470pF", [Y1(470e-12)]), ("P-D1 Y1 2.2nF", [Y1(2.2e-9)])]:
            for cs_lab, cs in (("C_cs 20pF", 20e-12), ("probe bonded to chassis (C_cs 10 nF)", 10e-9)):
                P = dict(fe.NOMINAL); P.update(V_on=von, extra_caps=caps, C_cs=cs)
                rows[f"{lab} | {cs_lab}"] = evalP(P, ec.F_SCAN)
        det[von_lab] = rows
        print(von_lab, "done", time.time() - t0, flush=True)
    out["nominal"] = det
    out["selv_noise_bound"] = selv_bound()
    # ---- all-worst corner (as in conducted.corners) with each variant
    worstP = {"V_on": 40.0, "t_f": 0.2e-6, "L_heater": 1e-6, "ESL40": 30e-9, "Cp40": 20e-12, "L40": 90e-6, "C40": 0.9e-6, "C1": 80e-9,
              "trace_scale": 1.5, "C_hc": 1e-9, "C_ch": 150e-12, "Rp40": 100e3}
    aw = {}
    for von_lab, von in (("as designed (V_on 40 V)", 40.0), ("F1 (V_on 18 V)", 18.0)):
        for lab, caps in VARIANTS.items():
            P = dict(fe.NOMINAL); P.update(worstP); P.update(V_on=von, extra_caps=caps)
            aw[f"{von_lab} | {lab}"] = evalP(P)
    out["all_worst_corner"] = aw
    print("corners done", time.time() - t0, flush=True)
    # ---- paired Monte Carlo
    n = int(sys.argv[sys.argv.index("--mc") + 1]) if "--mc" in sys.argv else 120
    D = draws(n)
    jobs, keys = [], []
    for von_lab, von in (("V_on 10-40 V (as designed)", (10.0, 40.0)), ("V_on 8-18 V (F1)", (8.0, 18.0))):
        for lab, caps in VARIANTS.items():
            for d in D:
                jobs.append((d, von, caps)); keys.append((von_lab, lab))
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        res = list(ex.map(mc_job, jobs, chunksize=4))
    mc = {}
    for (vl, lab), r in zip(keys, res):
        mc.setdefault(vl, {}).setdefault(lab, []).append(r)
    out["monte_carlo"] = {vl: {lab: summarise_mc(rows) for lab, rows in v.items()} for vl, v in mc.items()}
    out["monte_carlo"]["n"] = n
    # paired change vs baseline (per draw), worst-line QP
    delta = {}
    for vl, v in mc.items():
        base = np.array([min(r["QP_L"]["margin_dB"], r["QP_N"]["margin_dB"]) for r in v["baseline"]])
        for lab, rows in v.items():
            if lab == "baseline":
                continue
            x = np.array([min(r["QP_L"]["margin_dB"], r["QP_N"]["margin_dB"]) for r in rows]) - base
            delta[f"{vl} | {lab}"] = {"min_dB": round(float(x.min()), 2), "median_dB": round(float(np.median(x)), 2), "max_dB": round(float(x.max()), 2)}
    out["monte_carlo_paired_delta_worst_QP"] = delta
    out["runtime_s"] = round(time.time() - t0, 1)
    save_results("A1_crosscheck_scopeB", out)
    print("MC done", time.time() - t0, flush=True)
    # ---- F1 construction grid: C_hc x C_ch at V_on 18 V (F1 upper end); nominal others, and others at their bad ends
    chc = [100e-12, 220e-12, 470e-12, 1e-9]
    cch = [20e-12, 50e-12, 100e-12, 150e-12, 220e-12, 300e-12]
    grid = {}
    for lab, extra in (("F1 V_on 18 V, other parameters nominal", {}),
                       ("F1 V_on 18 V, other parameters at their bad ends (t_f 0.2 us, L_heater 1 uH, ESL40 30 nH, Cp40 20 pF, L40 90 uH, C40 0.9 uF, C1 80 nF, traces x1.5)",
                        {k: worstP[k] for k in ("t_f", "L_heater", "ESL40", "Cp40", "L40", "C40", "C1", "trace_scale", "Rp40")})):
        tab = {}
        for a in chc:
            for b in cch:
                P = dict(fe.NOMINAL); P.update(extra); P.update(V_on=18.0, C_hc=a, C_ch=b)
                m = evalP(P)
                w = min((m["QP_L"], m["QP_N"]), key=lambda r: r["margin_dB"])
                wa = min((m["AV_L"], m["AV_N"]), key=lambda r: r["margin_dB"])
                tab[f"C_hc={a*1e12:g}pF|C_ch={b*1e12:g}pF"] = {"QP_margin_dB": w["margin_dB"], "QP_f_MHz": w["f_MHz"], "AV_margin_dB": wa["margin_dB"]}
        grid[lab] = tab
    save_results("A1_F1_construction_grid", {"C_hc_pF": [x * 1e12 for x in chc], "C_ch_pF": [x * 1e12 for x in cch], "tables": grid,
                                             "note": "worst of lines L/N; V_on 18 V = upper end of the F1 gate-threshold range (8.7-17.7 V); C_cs 20 pF, no scope-B parts"})
    # plot the grid
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for a_, (lab, tab) in zip(ax, grid.items()):
        M = np.array([[tab[f"C_hc={x*1e12:g}pF|C_ch={y*1e12:g}pF"]["QP_margin_dB"] for y in cch] for x in chc])
        im = a_.imshow(M, origin="lower", cmap="RdYlGn", vmin=0, vmax=15, aspect="auto")
        for i in range(len(chc)):
            for j in range(len(cch)):
                a_.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8)
        a_.set_xticks(range(len(cch))); a_.set_xticklabels([f"{y*1e12:g}" for y in cch]); a_.set_yticks(range(len(chc))); a_.set_yticklabels([f"{x*1e12:g}" for x in chc])
        a_.set_xlabel("C_ch oven chassis -> reference plane (pF)"); a_.set_ylabel("C_hc heater -> chassis (pF)")
        a_.set_title(("nominal others" if "nominal" in lab else "other parameters at bad ends") + ", F1, V_on 18 V", fontsize=9)
    fig.colorbar(im, ax=ax, label="worst QP margin to EN 55014-1 Table 5 (dB)")
    fig.savefig(os.path.join(PLOTS, "A1_F1_construction_grid.png"), dpi=140, bbox_inches="tight"); plt.close(fig)
    print("grid done", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
