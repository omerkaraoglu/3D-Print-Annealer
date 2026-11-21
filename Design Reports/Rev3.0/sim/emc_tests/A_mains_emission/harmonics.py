"""Test A4: IEC 61000-3-2 harmonic currents (Class A Table 1 and, via 6.2, Table 3) for the whole appliance.

Input current = heater (whole-cycle firing with the real turn-on notch V_on and the I_H turn-off notch)
              + HLK-10M05 capacitive-input rectifier (10 ohm input resistance derived from its <= 34 A inrush,
                bulk capacitor assumed 10 uF, 6 W input) + fan (assumed 20 W, PF 0.55, 8 % 3rd harmonic)
              + X-capacitor current (C40 + C1, 1.1 uF).
Measurement (IEC 61000-4-7:2002 - NOT READ FROM THE STANDARD; source: IS 14700 (Part 4/Sec 7):2006, the identical
Indian adoption, 5.5.1, PDF p. 19 via law.resource.org): 10-cycle rectangular DFT windows (5 Hz bins), harmonic
group G_n^2 = C_{k-5}^2/2 + sum_{i=-4..4} C_{k+i}^2 + C_{k+5}^2/2, first-order 1.5 s smoothing of G_n and of P.
Assessment per IEC 61000-3-2 6.3.2-6.3.4 / 6.3.3.4 (FINAL VERSION PDF p. 138-141): average over T_obs <= limit,
every smoothed value <= 150 % (Class A: <= 200 % for < 10 % of T_obs if the average < 90 %), harmonics < 0.6 % of the
input current or < 5 mA disregarded. T_obs per Table 4 (PDF p. 147): 200 s (>= 10 frames of the 20 s burst cycle).
"""
import math, os, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import PLOTS, save_results, classA, table3, STD_3_2
import patterns as pt

F0, U = 50.0, 230.0
VPK = math.sqrt(2) * U
R_H = U ** 2 / 1000.0
NS = 20000                        # samples per mains cycle for the templates (1 MHz)
tc = (np.arange(NS) + 0.5) / NS / F0
vcyc = VPK * np.sin(2 * np.pi * F0 * tc)
NB = 430                          # 5 Hz bins up to 2150 Hz


def heater_cycle(V_on=20.0, I_H=0.05, half="both"):
    w = 2 * np.pi * F0
    ton = math.asin(V_on / VPK) / w
    toff = math.asin(min(I_H * R_H / VPK, 1)) / w
    th = tc % (0.5 / F0)
    on = (th >= ton) & (th <= 0.5 / F0 - toff)
    if half == "pos":
        on &= tc < 0.5 / F0
    return np.where(on, vcyc / R_H, 0.0)


def hlk_cycle(P_in=6.0, R_in=10.0, C=10e-6, Vd=0.9):
    """steady-state input current of a bridge + R_in + bulk C with a constant-power load."""
    dt = 1 / F0 / NS
    vc = VPK * 0.9
    i = np.zeros(NS)
    for rep in range(60):
        for k in range(NS):
            vin = abs(vcyc[k]) - 2 * Vd
            ich = (vin - vc) / R_in if vin > vc else 0.0
            vc += (ich - P_in / vc) * dt / C
            i[k] = ich * np.sign(vcyc[k])
    return i


def fan_cycle(P=20.0, pf=0.55, h3=0.08):
    I1 = P / (U * pf)
    ph = math.acos(pf)
    w = 2 * np.pi * F0
    return math.sqrt(2) * I1 * (np.sin(w * tc - ph) + h3 * np.sin(3 * (w * tc - ph)))


def xcap_cycle(C=1.1e-6):
    return 2 * np.pi * F0 * C * VPK * np.cos(2 * np.pi * F0 * tc)


def window_template(i_cycle):
    """complex DFT coefficient (peak amplitude) on the 5 Hz bin grid of a 10-cycle window that contains this
    cycle at position 0 and zeros elsewhere."""
    b = np.arange(NB)
    E = np.exp(-2j * np.pi * np.outer(b * 5.0, tc))           # NB x NS
    return 2 * (E @ i_cycle) / (10 * NS)


def assess(seq_on, tmpl_h, tmpl_s, p_h, p_s, label):
    """seq_on: boolean per mains cycle; tmpl_h: heater on-cycle template; tmpl_s: steady (every cycle) template."""
    nwin = len(seq_on) // 10
    on = seq_on[: nwin * 10].reshape(nwin, 10).astype(float)
    b = np.arange(NB)
    W = np.exp(-2j * np.pi * np.outer(np.arange(10), b) / 10.0)   # position m -> phase of bin b (5 Hz * 20 ms * m)
    X = (on @ W) * tmpl_h[None, :] + (np.ones((1, 10)) @ W) * tmpl_s[None, :]
    C = np.abs(X) / math.sqrt(2)                                # rms per bin
    P_win = on.mean(axis=1) * p_h + p_s
    a = 1 - math.exp(-0.2 / 1.5)
    G = np.zeros((nwin, 41)); Gs = np.zeros_like(G); Ps = np.zeros(nwin)
    for n in range(1, 41):
        k = 10 * n
        g2 = 0.5 * C[:, k - 5] ** 2 + np.sum(C[:, k - 4:k + 5] ** 2, axis=1) + 0.5 * C[:, k + 5] ** 2
        G[:, n] = np.sqrt(g2)
    ys = G[0].copy(); ps = P_win[0]
    for j in range(nwin):
        ys = ys + a * (G[j] - ys); Gs[j] = ys
        ps = ps + a * (P_win[j] - ps); Ps[j] = ps
    # skip the first 10 s after a switching event as 6.3.3.3 allows (we start inside steady operation; drop 1.5 s settling)
    k0 = int(1.5 / 0.2)
    avg = Gs[k0:].mean(axis=0); mx = Gs[k0:].max(axis=0)
    I_tot = math.sqrt(np.mean(np.sum(C[k0:] ** 2, axis=1)))
    Pmax = float(Ps[k0:].max())
    disregard = max(0.006 * I_tot, 0.005)
    rows = []
    worstA = worst3 = (0, None)
    for n in range(2, 41):
        lA = classA(n); l3 = table3(n, Pmax)
        rA = avg[n] / lA; rAm = mx[n] / lA
        r3 = avg[n] / l3 if l3 else None
        ign = avg[n] < disregard
        rows.append({"h": n, "avg_A": round(float(avg[n]), 4), "max_smoothed_A": round(float(mx[n]), 4), "classA_limit_A": round(lA, 4),
                     "avg_pct_classA": round(100 * rA, 1), "max_pct_classA": round(100 * rAm, 1),
                     "table3_limit_A": round(l3, 4) if l3 else None, "avg_pct_table3": round(100 * r3, 1) if r3 is not None else None,
                     "disregarded_<0.6%_or_5mA": bool(ign)})
        if not ign:
            if rA > worstA[0]: worstA = (rA, n)
            if rAm / 1.5 > worstA[0]: worstA = (rAm / 1.5, n) if rAm / 1.5 > worstA[0] else worstA
            if r3 is not None and r3 > worst3[0]: worst3 = (r3, n)
    return {"label": label, "I_rms_A": round(I_tot, 3), "P_max_smoothed_W": round(Pmax, 1), "disregard_A": round(disregard, 4),
            "worst_classA_pct_(avg/limit or max/1.5limit)": round(100 * worstA[0], 1), "worst_classA_order": worstA[1],
            "worst_table3_pct": round(100 * worst3[0], 1), "worst_table3_order": worst3[1], "rows": rows}


def main():
    out = {"standard": STD_3_2,
           "classification": "Class A (5.1, PDF p. 135 final: household appliance not in B, C or D); 7.1 exemptions (PDF p. 141): none (rated > 75 W, not professional)",
           "clause_6_2": "symmetrical control of heating elements producing integer harmonics up to 40: allowed only if full-sine heater power <= 200 W or Table 3 is not exceeded with the heater active (PDF p. 137); heater 1000 W -> Table 3 check required; asymmetrical control / half-wave only for <= 100 W etc. (PDF p. 137)",
           "measurement_method": "IEC 61000-4-7:2002 harmonic group + 1.5 s smoothing - NOT READ FROM THE STANDARD (IS 14700 Part 4/Sec 7:2006 5.5.1 p. 19)",
           "assumptions": {"HLK": "R_in 10 ohm (from inrush <= 34 A at 325 V, HLK datasheet p. 4), C_bulk 10 uF assumed, 6 W input", "fan": "20 W, PF 0.55, 8 % 3rd harmonic, assumed", "xcaps": "C40 + C1 = 1.1 uF"}}
    tm_s = window_template(hlk_cycle() + fan_cycle() + xcap_cycle())
    p_s = 6.0 + 20.0
    res = {}
    for von in (20.0, 40.0):
        tm_h = window_template(heater_cycle(V_on=von))
        p_h = float(np.mean(heater_cycle(V_on=von) * vcyc))
        key = f"V_on={von:g}V"
        res[key] = {}
        res[key]["100pct"] = assess(np.ones(1000, bool), tm_h, tm_s, p_h, p_s, "heater 100 %")
        for fam in ("current", "decided"):
            for d in (0.02, 0.05, 0.1, 0.2, 0.25, 0.3, 1 / 3, 0.4, 0.5, 0.6, 2 / 3, 0.7, 0.75, 0.8, 0.9, 0.95):
                seq = pt.PATTERNS[fam](d, 10000 + 10)   # 200 s
                r = assess(seq, tm_h, tm_s, p_h, p_s, f"{fam} duty {d:.3f}")
                r.pop("rows") if not (fam == "current" and abs(d - 0.5) < 1e-9) else None
                res[key][f"{fam}_{d:.3f}"] = r
    # risk scenario: ZCD reference too early -> the gate pulse misses one polarity (see report): half-wave heater
    tm_hw = window_template(heater_cycle(V_on=20.0, half="pos"))
    p_hw = float(np.mean(heater_cycle(half="pos") * vcyc))
    hw = assess(np.ones(1000, bool), tm_hw, tm_s, p_hw, p_s, "fault: positive half cycles only")
    i_hw = heater_cycle(half="pos")
    hw["dc_component_A"] = round(float(np.mean(i_hw)), 3)
    res["fault_half_wave"] = hw
    out["results"] = res
    # summary table
    summ = {}
    for key in ("V_on=20V", "V_on=40V"):
        for name, r in res[key].items():
            summ[f"{key}|{name}"] = (r["worst_classA_pct_(avg/limit or max/1.5limit)"], r["worst_classA_order"], r["worst_table3_pct"], r["worst_table3_order"])
    out["summary_pct_of_limit"] = summ
    save_results("A4_harmonics", out)
    # plot: % of Class A limit per order for 100 %, current fw at worst duty, decided at worst duty
    k = "V_on=40V"
    cur = max((v for n, v in res[k].items() if n.startswith("current")), key=lambda r: r["worst_classA_pct_(avg/limit or max/1.5limit)"])
    dec = max((v for n, v in res[k].items() if n.startswith("decided")), key=lambda r: r["worst_classA_pct_(avg/limit or max/1.5limit)"])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    h = np.arange(2, 41)
    for r, lab, c in ((res[k]["100pct"], "heater 100 % (V_on 40 V)", "C0"), (res[k]["current_0.500"], "current firmware, duty 0.5", "C1"), (res["fault_half_wave"], "fault: one polarity missed", "C3")):
        rows = r.get("rows")
        if rows:
            ax.semilogy(h, [max(x["avg_pct_classA"], 1e-3) for x in rows], "o-", color=c, ms=3, label=lab)
    ax.axhline(100, color="k", lw=2, label="IEC 61000-3-2 Table 1 Class A limit (100 %)")
    ax.set_xlabel("Harmonic order h"); ax.set_ylabel("Average harmonic group current, % of Class A limit")
    ax.set_title(f"A4 harmonics (worst duty current fw: {cur['label']}, {cur['worst_classA_pct_(avg/limit or max/1.5limit)']} %; decided: {dec['label']}, {dec['worst_classA_pct_(avg/limit or max/1.5limit)']} %)", fontsize=8)
    ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8); ax.set_ylim(1e-2, 300)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "A4_harmonics.png"), dpi=140); plt.close(fig)
    for kk, v in summ.items():
        print(kk, v)


if __name__ == "__main__":
    main()
