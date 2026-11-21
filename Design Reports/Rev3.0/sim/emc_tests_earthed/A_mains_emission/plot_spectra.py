"""Earthed case: QP/AV spectra on line N, nominal parameters - unearthed reference, earthed (today, F1), earthed + fix
(today, F1). Writes plots/E_spectra_N.png and results.json section 'spectra_N_nominal'."""
import os
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import earthed_model as em
import emission_core as ec
import fixes
from ecommon import save, PLOTS

CASES = {
    "unearthed reference, today V_on 20 V": dict(earthed=False, C_ch=50e-12, selv="floating", C_RV2=120e-12, RV3=False, C_fanframe=1e-15, V_on=20.0),
    "earthed, today V_on 20 V": dict(V_on=20.0),
    "earthed, F1 V_on 15 V": dict(V_on=15.0),
    "earthed + 200 uH A1-lead, today V_on 20 V": dict(fixes.ALL[fixes.CHOSEN], V_on=20.0),
    "earthed + 200 uH A1-lead, F1 V_on 15 V": dict(fixes.ALL[fixes.CHOSEN], V_on=15.0),
}


def job(lab):
    P = dict(em.EARTHED); P.update(CASES[lab])
    m, sc = em.evalP(P, ec.F_SCAN, want_scan=True)
    return lab, {"f": sc["f"], "QP_N": sc["N"]["QP"], "AV_N": sc["N"]["AV"], "QP_L": sc["L"]["QP"], "margins": m}


def main():
    with ProcessPoolExecutor(max_workers=len(CASES)) as ex:
        res = dict(ex.map(job, list(CASES)))
    save("spectra_N_nominal", res)
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for (lab, r), c in zip(res.items(), ("0.5", "C3", "C1", "C0", "C2")):
        ax.semilogx(np.array(r["f"]) / 1e6, r["QP_N"], color=c, lw=1.4, label=f"QP N: {lab}")
        ax.semilogx(np.array(r["f"]) / 1e6, r["AV_N"], color=c, lw=0.9, ls=":")
    ff = np.logspace(np.log10(0.15), np.log10(30), 300)
    ax.semilogx(ff, [em.lim_qp(x * 1e6) for x in ff], "k-", lw=2, label="EN 55014-1 Table 5 QP limit")
    ax.semilogx(ff, [em.lim_av(x * 1e6) for x in ff], "k--", lw=2, label="Table 5 AV limit (dotted curves = AV)")
    ax.set_xlim(0.15, 30); ax.set_ylim(-20, 90); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("AMN receiver port, line N (dBµV)")
    ax.set_title("Earthed chassis (class I): N-line conducted emission, nominal parameters, C_hc 300 pF", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "E_spectra_N.png"), dpi=140); plt.close(fig)
    for lab, r in res.items():
        print(lab, r["margins"])


if __name__ == "__main__":
    main()
