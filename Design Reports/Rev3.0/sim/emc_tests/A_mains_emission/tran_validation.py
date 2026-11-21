"""Validation of the source-substitution (LTI) conducted-emission method against a full transient ngspice run of
the nonlinear front end (230 V source, behavioural triac with V_on / t_f / I_H, everything else as in frontend.py).
Runs 0-41.5 ms at a 5 ns maximum step (~3 min), takes the 21.5-41.5 ms window as one period, and compares the receiver
readings with the LTI result at the same parameters. Writes tran_validation.json and plots/A1_validation_transient.png."""
import json, os, time
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import common  # noqa: F401  (sets sys.path)
import ngspice_helper as ng
import frontend as fe
import emission_core as ec
import receiver as rx
from common import HERE, PLOTS, dBuV


def main():
    P = dict(fe.NOMINAL)
    t0 = time.time()
    net, ons, offs = fe.netlist_tran(P, 0.0415, 5e-9)
    r = ng.run_netlist(net)
    t = np.real(r["time"]); vl = np.real(r["v(rx_l)"]); vn = np.real(r["v(rx_n)"])
    n = 2 ** 22
    tu = 21.5e-3 + np.arange(n) * 0.02 / n   # second period: start-up transients (3.6 kHz supply LC) decayed
    out = {"tran_runtime_s": round(time.time() - t0, 1), "n_timepoints": int(t.size), "turn_on_times_s": ons}
    H = ec.ac_transfer(P)
    fL, XLl, XNl = ec.lisn_lines(P, H)
    fsc = np.array([150e3, 200e3, 300e3, 500e3, 700e3, 1e6, 1.4e6, 2e6, 3e6, 5e6])
    rows = []
    specs = {}
    for side, v, Xl in (("L", vl, XLl), ("N", vn, XNl)):
        vu = np.interp(tu, t, v)
        out[f"window_wrap_jump_{side}_mV"] = round(1e3 * float(np.interp(tu[0] + 0.02, t, v) - vu[0]), 3)
        f, X = ec.line_spectrum(tu, vu)
        sel = (f >= 100e3) & (f <= 40e6); f, X = f[sel], X[sel]
        specs[side] = (f, X)
        for f0 in fsc:
            tt, e = rx.envelope_periodic(f, X, f0, 0.02)
            a = rx.readings_periodic(tt, e)
            tt, e2 = rx.envelope_periodic(fL, Xl, f0, 0.02)
            b = rx.readings_periodic(tt, e2)
            rows.append({"line": side, "f_MHz": f0 / 1e6, "QP_tran": round(float(dBuV(a["QP"])), 2), "QP_LTI": round(float(dBuV(b["QP"])), 2),
                         "AV_tran": round(float(dBuV(a["AV"])), 2), "AV_LTI": round(float(dBuV(b["AV"])), 2)})
    d = np.array([r_["QP_tran"] - r_["QP_LTI"] for r_ in rows])
    out["rows"] = rows
    out["QP_tran_minus_LTI_dB"] = {"max": round(float(d.max()), 2), "min": round(float(d.min()), 2)}
    json.dump(out, open(os.path.join(HERE, "tran_validation.json"), "w"), indent=1)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for side, c in (("L", "C0"), ("N", "C1")):
        rr = [x for x in rows if x["line"] == side]
        ax.semilogx([x["f_MHz"] for x in rr], [x["QP_tran"] for x in rr], c + "o-", label=f"QP {side}, full transient")
        ax.semilogx([x["f_MHz"] for x in rr], [x["QP_LTI"] for x in rr], c + "x--", label=f"QP {side}, source substitution (LTI)")
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("dBµV"); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8)
    ax.set_title("Validation: nonlinear transient vs source-substitution model (nominal)", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A1_validation_transient.png"), dpi=140); plt.close(fig)
    print(json.dumps(out["QP_tran_minus_LTI_dB"]), [ (x["line"], x["f_MHz"], x["QP_tran"], x["QP_LTI"]) for x in rows])


if __name__ == "__main__":
    main()
