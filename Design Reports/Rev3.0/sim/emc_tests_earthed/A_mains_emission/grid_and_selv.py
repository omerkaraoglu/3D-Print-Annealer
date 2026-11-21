"""Earthed case: (1) oven-construction table - worst QP margin with F1 (V_on 18 V) vs C_hc and PE-bond inductance,
without and with the chosen fix, other parameters nominal and at their bad ends;
(2) SELV paths - HLK primary->secondary CM noise and SELV-ground noise EMF to the AMN for the three SELV cases.
Writes results.json sections 'construction_grid' and 'selv_paths', plot plots/E_construction_grid.png."""
import os
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import earthed_model as em
import fixes
from ecommon import save, PLOTS

CHC = [100e-12, 220e-12, 470e-12, 1e-9]
LB = [0.1e-6, 0.3e-6, 1e-6, 3e-6]
BAD = {k: em.WORST[k] for k in ("t_f", "L_heater", "ESL40", "Cp40", "L40", "C40", "C1", "trace_scale", "Rp40")}


def job(args):
    fixlab, others, a, b = args
    P = dict(em.EARTHED); P.update(fixes.ALL[fixlab] if fixlab != "none" else {}); P.update(others); P.update(V_on=18.0, C_hc=a, L_bond=b)
    m = em.evalP(P)
    w = min((m["QP_L"], m["QP_N"]), key=lambda r: r["margin_dB"]); wa = min((m["AV_L"], m["AV_N"]), key=lambda r: r["margin_dB"])
    return (fixlab, "bad" if others else "nominal", a, b), {"QP_margin_dB": w["margin_dB"], "QP_f_MHz": w["f_MHz"], "AV_margin_dB": wa["margin_dB"]}


def selv_paths():
    out = {}
    fq = [150e3, 300e3, 580e3, 1.2e6, 2.4e6, 5e6, 10e6, 30e6]
    for s in ("insulated", "grounded", "bonded"):
        P = dict(em.EARTHED); P["selv"] = s
        row = {}
        for src in ("psu_cm", "selv"):
            f, HL, HN = em.ac_transfer(P, src, ppd=60)
            H = np.maximum(np.abs(HL), np.abs(HN))
            row[src] = {f"{x/1e6:g}MHz": {"transfer_dB": round(float(20 * np.log10(np.interp(x, f, H))), 1),
                                          "max_for_AV_limit": round(float(em.lim_av(x) - 20 * np.log10(np.interp(x, f, H))), 1),
                                          "max_for_QP_limit": round(float(em.lim_qp(x) - 20 * np.log10(np.interp(x, f, H))), 1)} for x in fq}
        out[s] = row
    out["note"] = ("psu_cm: 1 A noise current HLK primary -> secondary (transfer in dB-ohm; max values are dBuA); "
                   "selv: ideal EMF SELV GND -> reference plane (dB; max values are dBuV). Unearthed reference values are in "
                   "emc_tests/A_mains_emission results.json A1_crosscheck_scopeB.selv_noise_bound / M3_heater_off_HLK_bound.")
    return out


def main():
    jobs = [(fx, o, a, b) for fx in ("none", fixes.CHOSEN) for o in ({}, BAD) for a in CHC for b in LB]
    with ProcessPoolExecutor(max_workers=min(len(jobs), (os.cpu_count() or 4) - 2)) as ex:
        res = dict(ex.map(job, jobs))
    tables = {}
    for (fx, o, a, b), v in res.items():
        tables.setdefault(f"{fx} | others {o}", {})[f"C_hc={a*1e12:g}pF|L_bond={b*1e6:g}uH"] = v
    save("construction_grid", {"V_on_V": 18.0, "C_hc_pF": [x * 1e12 for x in CHC], "L_bond_uH": [x * 1e6 for x in LB], "tables": tables,
                               "note": "F1 timing, worst of L/N; SELV insulated junction; bad ends = t_f 0.2 us, L_heater 1 uH, ESL40 30 nH, Cp40 20 pF, L40 90 uH, C40 0.9 uF, C1 80 nF, traces x1.5"})
    fig, axs = plt.subplots(1, 4, figsize=(18, 4))
    for ax, (lab, tab) in zip(axs, tables.items()):
        M = np.array([[tab[f"C_hc={a*1e12:g}pF|L_bond={b*1e6:g}uH"]["QP_margin_dB"] for b in LB] for a in CHC])
        ax.imshow(M, origin="lower", cmap="RdYlGn", vmin=-10, vmax=20, aspect="auto")
        for i in range(len(CHC)):
            for j in range(len(LB)):
                ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8)
        ax.set_xticks(range(len(LB))); ax.set_xticklabels([f"{b*1e6:g}" for b in LB]); ax.set_yticks(range(len(CHC))); ax.set_yticklabels([f"{a*1e12:g}" for a in CHC])
        ax.set_xlabel("PE bond inductance chassis -> inlet (µH)"); ax.set_ylabel("C_hc heater -> earthed chassis (pF)"); ax.set_title(lab[:60], fontsize=8)
    fig.suptitle("Earthed chassis, F1 (V_on 18 V): worst QP margin to EN 55014-1 Table 5 (dB)", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "E_construction_grid.png"), dpi=130); plt.close(fig)
    save("selv_paths", selv_paths())
    for k, t in tables.items():
        print("==", k)
        for a in CHC:
            print("  C_hc", round(a * 1e12), [t[f"C_hc={a*1e12:g}pF|L_bond={b*1e6:g}uH"]["QP_margin_dB"] for b in LB])


if __name__ == "__main__":
    main()
