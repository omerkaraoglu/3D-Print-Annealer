"""Test A3: EN 55014-1 discontinuous disturbance (clicks), 4.4 / 5.4 / Annexes A.4, B, C.

(1) Triac heater switching, both firmware patterns: is any discontinuous disturbance registered at all (IF envelope
    above the IF reference level, 3.3.4) and, if so, is it a click (3.3.3: <= 200 ms, >= 200 ms separation)?
(2) Fan relay K1 (LINE_FUSED, ahead of L40, so no filter between the contact and the AMN): showering-arc model
    at contact break of the inductive fan current -> gap voltage -> AC transfer (SPICE, 'relay' source) -> AMN ->
    receiver: click amplitude (QP, single event), duration on the IF envelope, click rate N, applicable limit.
Arc model (assumed, no relay data in the project): breakdown voltage 300 V rising 0.9 V/us with the opening gap
(0.3 m/s contact speed x 3 kV/mm), arc-voltage floor 15 V, fan winding + wiring capacitance 200 pF charged by the
fan current (worst at its peak 0.23 A), showering lasting 1 ms (swept 0.1-3 ms).
"""
import math, os, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import PLOTS, save_results, lim_qp, dBuV, click_relaxation_dB, STD_55014_1
import frontend as fe
import emission_core as ec
import receiver as rx
import patterns as pt

F_CLICK = (150e3, 500e3, 1.4e6, 30e6)        # 5.4.2.3, PDF p. 49


def if_reference_level(L_dBuV):
    """IF envelope amplitude (carrier peak, V) of an unmodulated sine whose QP reading equals L (3.3.4)."""
    return math.sqrt(2) * 1e-6 * 10 ** (L_dBuV / 20)


def triac_part():
    P = dict(fe.NOMINAL)
    out = {}
    for von in (20.0, 40.0):
        P["V_on"] = von
        H = ec.ac_transfer(P)
        f, XL, XN = ec.lisn_lines(P, H)
        row = {}
        for f0 in F_CLICK:
            worst = None
            for side, X in (("L", XL), ("N", XN)):
                t, e = rx.envelope_periodic(f, X, f0, 0.02, n_t=8192)
                ref = if_reference_level(lim_qp(f0))
                over = e > ref
                dt = t[1] - t[0]
                r = {"peak_env_over_IF_ref_dB": round(float(20 * np.log10(e.max() / ref)), 1),
                     "time_above_ref_per_event_us": round(float(over.sum() * dt / 2 * 1e6), 1)}
                if worst is None or r["peak_env_over_IF_ref_dB"] > worst["peak_env_over_IF_ref_dB"]:
                    worst = dict(r, line=side)
            row[f"{f0/1e6:g}MHz"] = worst
        out[f"V_on={von:g}V"] = row
    out["interpretation"] = ("If the IF envelope never exceeds the IF reference level no discontinuous disturbance is registered. "
                             "If it does, the events of one firing burst are 10 ms apart (< 200 ms) -> 'disturbances other than clicks' "
                             "(3.3.3, Figure 3) -> Table 5 limits apply without relaxation (4.4.2.2, PDF p. 39), which is test A1.")
    # burst structure of both patterns (duration of the shortest burst, separation)
    st = {}
    for fam in ("current", "decided"):
        rows = {}
        for d in (0.005, 0.01, 0.05, 0.5, 0.95):
            seq = pt.PATTERNS[fam](d, 3000 * 4)
            x = np.concatenate([[0], seq.astype(int), [0]])
            starts = np.nonzero(np.diff(x) == 1)[0]; ends = np.nonzero(np.diff(x) == -1)[0]
            lens = (ends - starts) * 20e-3
            gaps = (starts[1:] - ends[:-1]) * 20e-3 if len(starts) > 1 else np.array([np.inf])
            rows[f"{d:g}"] = {"bursts_per_min": round(len(starts) / (len(seq) / 3000), 1),
                              "burst_len_s_min": round(float(lens.min()), 3) if lens.size else None,
                              "gap_s_min": round(float(gaps.min()), 3) if gaps.size else None}
        st[fam] = rows
    out["burst_structure"] = st
    return out


def arc_waveform(i0=0.23, C=200e-12, vb0=300.0, dvb=0.9e6, v_arc=15.0, t_show=1e-3, fs=100e6, T=0.04, t0=0.005):
    n = int(T * fs)
    v = np.zeros(n)
    t = t0; vb = vb0; k_list = []
    while t < t0 + t_show:
        vb = vb0 + dvb * (t - t0)
        dtc = C * (vb - v_arc) / i0
        i1, i2 = int(t * fs), int((t + dtc) * fs)
        if i2 >= n:
            break
        v[i1:i2] = np.linspace(v_arc, vb, max(i2 - i1, 1), endpoint=False)
        k_list.append(t)
        t += dtc
    i_end = int(t * fs)
    # after the showering the gap holds: voltage settles to the line voltage across the open contact (slow, < 9 kHz) -> keep v_arc
    return np.arange(n) / fs, v, len(k_list)


def relay_part():
    P = dict(fe.NOMINAL)
    f, HL, HN = ec.ac_transfer(P, source="relay", ppd=100)
    out = {"model": __doc__.split("Arc model")[1].strip()}
    res = {}
    for t_show in (0.1e-3, 1e-3, 3e-3):
        t, v, ndis = arc_waveform(t_show=t_show)
        fl, X = ec.line_spectrum(t, v)
        sel = (fl >= 100e3) & (fl <= f[-1]); fl, X = fl[sel], X[sel]
        row = {"n_discharges": ndis}
        for f0 in F_CLICK[:3] + (30e6,):
            best = None
            for side, H in (("L", HL), ("N", HN)):
                Y = X * ec.interp_c(fl, f, H)
                tt, e = rx.envelope_periodic(fl, Y, f0, 0.04, n_t=16384)
                dt = tt[1] - tt[0]
                r = rx.readings_events(e, dt, [0.0], 2.0)    # single event (the 40 ms record as one pulse)
                ref = if_reference_level(lim_qp(f0))
                dur = float((e > ref).sum() * dt)
                q = float(dBuV(r["QP"]))
                if best is None or q > best["QP_dBuV"]:
                    best = {"line": side, "QP_dBuV": round(q, 1), "PK_dBuV": round(float(dBuV(r["PK"])), 1),
                            "duration_above_IF_ref_ms": round(dur * 1e3, 3), "L_dBuV": round(lim_qp(f0), 1)}
            row[f"{f0/1e6:g}MHz"] = best
        res[f"showering_{t_show*1e3:g}ms"] = row
    out["results"] = res
    # click rate: the fan relay is switched once per power-up (firmware sets FAN_PIN HIGH at boot, line 1730, never off)
    N = 2 / 120.0      # assume (pessimistically) one on + one off in the 120 min minimum observation time (5.4.2.1 a)
    out["click_rate_N_per_min"] = round(N, 4)
    out["Lq_relaxation_dB"] = click_relaxation_dB(N)
    out["exemptions"] = {"5.4.3.2 individual switching operations (PDF p. 50-51)": "fan relay operated at power-up / programme start only -> disregarded",
                         "5.4.3.4 instantaneous switching (PDF p. 51)": "N <= 5, every click <= 20 ms, 90 % <= 10 ms -> deemed to comply regardless of amplitude"}
    worst_q = max(v["150MHz" if False else "0.15MHz"]["QP_dBuV"] for v in res.values())
    out["worst_QP_at_150k_dBuV"] = worst_q
    out["Lq_at_150k_dBuV"] = round(lim_qp(150e3) + click_relaxation_dB(N), 1)
    return out


def main():
    out = {"standard": STD_55014_1, "clauses": "4.4.1, 4.4.2.1-4.4.2.3 (PDF p. 39); 5.4.2-5.4.3 (PDF p. 49-52); A.4.1 (PDF p. 80-81); Table B.1 (PDF p. 100); Annex C (PDF p. 101-105); definitions 3.3.1-3.3.8 (PDF p. 25-26)"}
    out["triac"] = triac_part()
    out["relay_K1"] = relay_part()
    save_results("A3_clicks", out)
    # plot: arc gap voltage and LISN IF envelope at 150 kHz for 1 ms showering
    t, v, nd = arc_waveform()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    m = (t > 0.0049) & (t < 0.0062)
    ax[0].plot((t[m] - 0.005) * 1e3, v[m], lw=0.5)
    ax[0].set_xlabel("time after contact separation (ms)"); ax[0].set_ylabel("contact gap voltage (V)"); ax[0].set_title("K1 break, showering-arc model (assumed)", fontsize=9)
    P = dict(fe.NOMINAL)
    f, HL, HN = ec.ac_transfer(P, source="relay", ppd=100)
    fl, X = ec.line_spectrum(t, v); sel = (fl >= 100e3) & (fl <= f[-1]); fl, X = fl[sel], X[sel]
    for f0, c in ((150e3, "C0"), (500e3, "C1"), (1.4e6, "C2")):
        Y = X * ec.interp_c(fl, f, HN)
        tt, e = rx.envelope_periodic(fl, Y, f0, 0.04, n_t=16384)
        ax[1].semilogy((tt - 0.005) * 1e3, e / math.sqrt(2) / 1e-6, c, lw=1, label=f"IF envelope {f0/1e6:g} MHz (line N)")
        ax[1].axhline(10 ** (lim_qp(f0) / 20), color=c, ls="--", lw=1)
    ax[1].set_xlim(-0.5, 3); ax[1].set_xlabel("time (ms)"); ax[1].set_ylabel("IF envelope, rms-equivalent (µV); dashed: IF reference level = Table 5 QP limit")
    ax[1].legend(fontsize=7); ax[1].grid(alpha=0.3, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A3_relay_click.png"), dpi=140); plt.close(fig)
    print(json.dumps(out, indent=1, default=str)[:5000])


if __name__ == "__main__":
    main()
