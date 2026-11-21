"""Test A5: IEC 61000-3-3 voltage changes and flicker (P_st, P_lt, d_c, d_max, T_max).

Flickermeter: sim/emc/flickermeter.py (IEC 61000-4-15 model of 2026-11-12), IMPORTED, not edited; re-validated
here (results in results.json 'A5_flicker.revalidation'; the test points are NOT READ FROM THE STANDARD -
IEC 61000-4-15 is not in the owner's folder; they are the values the 2026-11-12 brief used).
Limits and Z_ref: NOT READ FROM THE STANDARD (IEC 61000-3-3 clause 5 and 6.4 are not in the 21-page preview).
Read from the preview: scope (<= 16 A, 220-250 V, 50 Hz; PDF p. 10/20), definitions of d(t), d_c, d_max, T_max
(3.2-3.5, PDF p. 11), assessment methods list (4.1-4.3, TOC p. 5), corrigendum note "P_lt shall not be evaluated"
for A.16 equipment only (PDF p. 19).
Electrical model: ideal 230 V source + Z_ref (0.40 + j0.25 ohm at 50 Hz) + heater 52.9 ohm, triac turn-on at
V_on after each zero crossing of a fired half cycle (exact R-L transient per half cycle).
"""
import math, os, sys, json, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import PLOTS, save_results, FLICKER_LIMITS, ZREF, STD_3_3
import flickermeter as fl
import patterns as pt

U, F0 = 230.0, 50.0
W = 2 * np.pi * F0
R_REF, L_REF = ZREF["R_ohm"], ZREF["X_ohm"] / W
R_H = U ** 2 / 1000.0
FS = 4000.0
PRE_S, OBS_S = 30.0, 600.0
V_ON = 15.0


def half_cycle_shapes(tau, v_on=V_ON, r_load=R_H):
    vs = np.sqrt(2) * U * np.sin(W * tau)
    t_on = math.asin(v_on / (np.sqrt(2) * U)) / W
    R = r_load + R_REF
    Z = complex(R, W * L_REF); phi = np.angle(Z); tc = L_REF / R
    i = np.sqrt(2) * U / abs(Z) * (np.sin(W * tau - phi) - np.sin(W * t_on - phi) * np.exp(-(tau - t_on) / tc))
    v_on_shape = np.where(tau >= t_on, r_load * i, vs)
    return vs, v_on_shape


def templates(fs=FS):
    n = int(round(fs / (2 * F0)))
    tau = np.arange(n) / fs
    off, on = half_cycle_shapes(tau)
    tf = (np.arange(10000) + 0.5) / 1e6
    a, b = half_cycle_shapes(tf)
    return off, on, float(np.sqrt(np.mean(a ** 2))), float(np.sqrt(np.mean(b ** 2)))


TPL_OFF, TPL_ON, U_OFF, U_ON = templates()


def waveform(cycles_on):
    on_hc = np.repeat(np.asarray(cycles_on, bool), 2)
    sign = np.where(np.arange(on_hc.size) % 2 == 0, 1.0, -1.0)
    return (np.where(on_hc[:, None], TPL_ON[None, :], TPL_OFF[None, :]) * sign[:, None]).reshape(-1)


_FM = None


def _init():
    global _FM
    _FM = fl.Flickermeter(fs=FS, hp_order=1)


def eval_case(args):
    fam, duty = args
    if _FM is None:
        _init()
    n = int((PRE_S + OBS_S) * F0)
    if ":" in fam:                      # proposal: decided pattern with a longer frame, e.g. 'decided:1500'
        seq = pt.decided_fw(duty, n, frame=int(fam.split(":")[1]))
    else:
        seq = pt.PATTERNS[fam](duty, n)
    p = _FM.pinst(waveform(seq))[int(PRE_S * _FM.fsd):]
    on = seq[int(PRE_S * F0):]
    hc = np.concatenate([np.full(200, U_OFF), np.where(np.repeat(seq, 2), U_ON, U_OFF)])
    dp = fl.d_parameters(hc, Un=U)
    return {"family": fam, "duty": duty, "duty_real": float(on.mean()), "Pst": fl.pst(p, "cpf"),
            "Pinst_max": float(p.max()), "d_max_pct": 100 * dp["d_max"], "d_c_pct": 100 * dp["d_c"], "T_max_s": dp["T_max_s"],
            "changes_per_min": float(np.count_nonzero(np.diff(on.astype(np.int8))) / (OBS_S / 60))}


RECT = [(1, 2.724), (2, 2.211), (7, 1.459), (39, 0.906), (110, 0.725), (1620, 0.402)]


def reval_case(args):
    kind, a, b = args
    if _FM is None:
        _init()
    if kind == "rect":
        v = fl.rect_modulated(FS, PRE_S + OBS_S, b / 100, a, t_offset=5.0)
        p = _FM.pinst(v)[int(PRE_S * _FM.fsd):]
        return {"cpm": a, "dvv_pct": b, "Pst": fl.pst(p, "cpf")}
    v = fl.sine_modulated(FS, 60.0, b / 100, a)
    p = _FM.pinst(v)[int(20 * _FM.fsd):]
    return {"f_Hz": a, "dvv_pct": b, "Pinst_mean": float(p.mean()), "Pinst_max": float(p.max())}


def switching_events():
    """d-parameters for single events: heater on (hot and cold), HLK power-on inrush, fan start (assumed)."""
    out = {}
    out["heater_step_hot"] = {"dU_pct": round(100 * (U_OFF - U_ON) / U_OFF, 3)}
    # cold heater: NiCr / FeCrAl element resistance ~5 % lower cold (assumption) -> 1050 W
    _, on_c = half_cycle_shapes((np.arange(10000) + 0.5) / 1e6, r_load=R_H / 1.05)
    uc = float(np.sqrt(np.mean(on_c ** 2)))
    out["heater_step_cold_5pct"] = {"dU_pct": round(100 * (U_OFF - uc) / U_OFF, 3)}
    # HLK power-on at the voltage peak: 10 ohm input + 10 uF bulk + X caps 1.1 uF charged from 0 (worst phase), Z_ref source
    dt = 1e-6
    t = np.arange(0, 0.2, dt)
    t = np.arange(0, 0.2, 0.2e-6)
    dt = t[1] - t[0]
    # switched on at the positive peak; source Z_ref (R + L), X caps 1.1 uF at the terminals, bridge + 10 ohm + 10 uF, 6 W
    vs = np.sqrt(2) * U * np.cos(W * t)
    i = 0.0; vx = 0.0; vb = 0.0; vt = np.zeros_like(t); ipk = 0.0
    for k in range(t.size):
        ib = (abs(vx) - 1.8 - vb) / 10.0 if abs(vx) - 1.8 > vb else 0.0
        i += (vs[k] - R_REF * i - vx) / L_REF * dt
        vx += (i - ib * np.sign(vx)) / 1.1e-6 * dt
        vb += (ib - 6.0 / max(vb, 50.0)) / 10e-6 * dt
        vt[k] = vx; ipk = max(ipk, abs(i))
    n = int(round(1 / (2 * F0) / dt))
    hc = np.sqrt(np.mean(vt[: (t.size // n) * n].reshape(-1, n) ** 2, axis=1))
    seq = np.concatenate([np.full(200, U), hc, np.full(200, hc[-1])])
    dp = fl.d_parameters(seq, Un=U)
    out["HLK_inrush_power_on"] = {"d_max_pct": round(100 * dp["d_max"], 3), "d_c_pct": round(100 * dp["d_c"], 3), "T_max_s": dp["T_max_s"],
                                  "peak_source_current_A": round(ipk, 1),
                                  "note": "half-cycle rms windows start at the switching instant; HLK datasheet inrush <= 34 A (p. 4)"}
    # fan start (assumed shaded-pole 20 W: 0.16 A run, 2.5x start current for 0.5 s, PF 0.55)
    I_run, I_st = 20 / (230 * 0.55), 2.5 * 20 / (230 * 0.55)
    zl = R_REF * 0.55 + (ZREF["X_ohm"]) * math.sin(math.acos(0.55))
    out["fan_start_assumed"] = {"d_max_pct": round(100 * I_st * zl / U, 3), "d_c_pct": round(100 * I_run * zl / U, 3), "T_max_s": 0.0}
    out["note"] = "power-on sequence: X caps + HLK inrush (sub-cycle), fan relay at boot (firmware line 1730), heater from the first PID output; events seconds apart"
    return out


def main():
    t0 = time.time()
    res = {"standard": STD_3_3, "limits": FLICKER_LIMITS, "Zref": ZREF, "V_on_V": V_ON,
           "U_off_V": U_OFF, "U_on_V": U_ON, "heater_step_dU_pct": 100 * (U_OFF - U_ON) / U_OFF}
    duties = [0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 1 / 3, 0.4, 0.45, 0.5, 0.55, 0.6, 2 / 3, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]
    cases = [(f, d) for f in ("current", "decided") for d in duties]
    cases += [(f, d) for f in ("decided:1500", "decided:2000") for d in (0.01, 0.1, 0.5, 0.9, 0.95, 0.99)]
    reval = [("rect", a, b) for a, b in RECT] + [("sine", 8.8, 0.25)]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2), initializer=_init) as ex:
        rv = list(ex.map(reval_case, reval))
        rr = list(ex.map(eval_case, cases))
    res["revalidation"] = {"rows": rv, "targets_source": "IEC 61000-4-15 rectangular P_st = 1 points and 8.8 Hz / 0.25 % sine P_inst = 1 - NOT READ FROM THE STANDARD (as used by the 2026-11-12 brief)",
                           "max_dev_pct": round(100 * max(abs(r["Pst"] - 1) for r in rv if "Pst" in r), 2),
                           "sine_mean": round(rv[-1]["Pinst_mean"], 4)}
    res["cases"] = rr
    for fam in ("current", "decided", "decided:1500", "decided:2000"):
        rows = [r for r in rr if r["family"] == fam]
        w = max(rows, key=lambda r: r["Pst"])
        res[f"worst_{fam}"] = {"Pst": round(w["Pst"], 3), "duty": round(w["duty"], 3), "Plt_const_duty": round(w["Pst"], 3),
                               "d_max_pct": round(max(r["d_max_pct"] for r in rows), 3), "d_c_pct": round(max(r["d_c_pct"] for r in rows), 3),
                               "T_max_s": max(r["T_max_s"] for r in rows),
                               "duties_Pst_gt_1": [round(r["duty"], 3) for r in rows if r["Pst"] > 1.0],
                               "duties_Plt_gt_0.65": [round(r["duty"], 3) for r in rows if r["Pst"] > 0.65]}
    res["single_events"] = switching_events()
    res["runtime_s"] = round(time.time() - t0, 1)
    save_results("A5_flicker", res)
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    for fam, c, lab in (("current", "C3", "current firmware (per-cycle sigma-delta)"), ("decided", "C0", "decided firmware (20 s burst frame, error carry)")):
        rows = sorted([r for r in rr if r["family"] == fam], key=lambda r: r["duty"])
        ax.plot([r["duty"] for r in rows], [r["Pst"] for r in rows], "o-", color=c, ms=3, label=lab)
    ax.axhline(1.0, color="k", lw=2, label="P_st limit 1.0 (NOT READ from the standard)")
    ax.axhline(0.65, color="k", ls="--", lw=1.5, label="P_lt limit 0.65 (= P_st at constant duty; NOT READ)")
    ax.set_xlabel("Heater duty (PID output)"); ax.set_ylabel("P_st (10 min) on Z_ref = 0.40 + j0.25 Ω")
    ax.set_title("A5 flicker: IEC 61000-4-15 model, 1 kW heater, V_on 15 V", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A5_flicker_pst_vs_duty.png"), dpi=140); plt.close(fig)
    print(json.dumps({k: v for k, v in res.items() if k not in ("cases",)}, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
