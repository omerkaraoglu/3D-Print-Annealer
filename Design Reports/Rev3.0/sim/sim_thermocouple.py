"""(c) Thermocouple front end: 2 x 1 k series, 100 nF differential, 2 x 10 nF common-mode caps,
10 M open-thermocouple bias (to 3.3 V on + lead, to GND on - lead, placed on the TERMINAL side of the
series resistors), ADS1115 input modelled as 710 kohm differential || 100 Mohm per input to GND
(datasheet values for FSR = +-256 mV).

Stimulus: 12.3 mV DC (300 C K-type), 1 V / 50 Hz common mode on both leads (ideal source,
worst case), 50 mVpp / 100 kHz differential burst between 20 ms and 30 ms.
Engine: ngspice 46 shared lib (KiCad 10) via PySpice 1.5
"""
import json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from ngspice_helper import run_netlist

HERE = Path(__file__).resolve().parent
PLOTS = HERE / "plots"
S_K = 41e-6; LSB = 0.256 / 32768

def tran_netlist(ccm_mismatch=0.0, stop="250m", step="1u", burst=True, cm_amp=1.0, emf_step=False, open_tc=False):
    c2 = 10 * (1 + ccm_mismatch)
    b = "V = 25m*sin(2*pi*100k*time)*(u(time-20m)-u(time-30m))" if burst else "V = 0"
    emf = "PULSE(0 12.3m 1m 1n 1n 10 20)" if emf_step else "DC 12.3m"
    lead = "1T" if open_tc else "5"       # open thermocouple: leads disconnected
    return f"""TC front end mismatch={ccm_mismatch}
Vdd vdd 0 3.3
* common-mode pickup (ideal, worst case) referenced to the 1.65 V bias point
Vcm cmn 0 SIN(1.65 {cm_amp} 50)
* thermocouple EMF + 100 kHz differential burst, lead resistance 5 ohm per leg
Vtc tc1 cmn {emf}
Bburst tc2 tc1 {b}
Rlead1 tc2 t1 {lead}
Rlead2 cmn t2 {lead}
* open-thermocouple bias network at the terminal
Rb1 vdd t1 10Meg
Rb2 t2 0 10Meg
* differential / common-mode RC filter
R1 t1 ainp 1k
R2 t2 ainn 1k
Cd ainp ainn 100n
Ccm1 ainp 0 10n
Ccm2 ainn 0 {c2}n
* ADS1115 input model (FSR 256 mV)
Rin ainp ainn 710k
Rcm1 ainp 0 100Meg
Rcm2 ainn 0 100Meg
.tran {step} {stop} 0 {step}
.end
"""

AC_DM = """TC filter AC, differential drive
Vdd vdd 0 3.3
Vd tc1 0 DC 0 AC 1
Rlead1 tc1 t1 5
Rlead2 0 t2 5
Rb1 vdd t1 10Meg
Rb2 t2 0 10Meg
R1 t1 ainp 1k
R2 t2 ainn 1k
Cd ainp ainn 100n
Ccm1 ainp 0 10n
Ccm2 ainn 0 10n
Rin ainp ainn 710k
Rcm1 ainp 0 100Meg
Rcm2 ainn 0 100Meg
.ac dec 40 1 10Meg
.end
"""

def ac_cm(mismatch):
    return f"""TC filter AC, common-mode drive, Ccm mismatch {mismatch}
Vdd vdd 0 3.3
Vc cmn 0 DC 0 AC 1
Rlead1 cmn t1 5
Rlead2 cmn t2 5
Rb1 vdd t1 10Meg
Rb2 t2 0 10Meg
R1 t1 ainp 1k
R2 t2 ainn 1k
Cd ainp ainn 100n
Ccm1 ainp 0 10n
Ccm2 ainn 0 {10*(1+mismatch)}n
Rin ainp ainn 710k
Rcm1 ainp 0 100Meg
Rcm2 ainn 0 100Meg
.ac dec 40 1 10Meg
.end
"""

results = {}
# ---------------- transient, matched and 10 % mismatched Ccm
fig, axes = plt.subplots(3, 1, figsize=(10, 9))
for mm, lbl in ((0.0, "Ccm matched"), (0.10, "Ccm 10 % mismatch")):
    d = run_netlist(tran_netlist(mm))
    t = d["time"]; vd = d["v(ainp)"] - d["v(ainn)"]; vp = d["v(ainp)"]
    final = vd[(t > 200e-3)].mean()
    # 50 Hz residual outside the burst, after settling (40..250 ms, excluding burst? burst is 20..30 ms)
    m = (t > 40e-3)
    ripple_pp = vd[m].max() - vd[m].min()
    # 100 kHz residual during burst (22..28 ms) minus the 50 Hz component (remove with 1 ms moving mean)
    mb = (t > 22e-3) & (t < 28e-3)
    vb = vd[mb]; k = int(1e-3 / np.median(np.diff(t)))
    base = np.convolve(vb, np.ones(k) / k, mode="same")
    burst_resid_pp = (vb - base)[k:-k].max() - (vb - base)[k:-k].min()
    # ADS1115 at 16 SPS: approximate the digital filter by a 62.5 ms box average (sinc1 notch at n*16 Hz)
    Ts = 1 / 16
    samples = []
    t0 = 50e-3
    while t0 + Ts <= t[-1]:
        samples.append(vd[(t >= t0) & (t < t0 + Ts)].mean()); t0 += Ts
    samples = np.array(samples)
    # 32 SPS version
    Ts2 = 1 / 32; samples32 = []; t0 = 50e-3
    while t0 + Ts2 <= t[-1]:
        samples32.append(vd[(t >= t0) & (t < t0 + Ts2)].mean()); t0 += Ts2
    samples32 = np.array(samples32)
    results[lbl] = dict(final_diff_mV=round(final * 1e3, 4),
                        gain_error_pct=round((final / 12.3e-3 - 1) * 100, 3),
                        residual_50Hz_pp_uV=round(ripple_pp * 1e6, 1),
                        residual_50Hz_pp_degC=round(ripple_pp / S_K, 2),
                        burst_100kHz_residual_pp_uV=round(burst_resid_pp * 1e6, 1),
                        burst_100kHz_residual_pp_degC=round(burst_resid_pp / S_K, 3),
                        adc16sps_sample_spread_pp_uV=round((samples.max() - samples.min()) * 1e6, 2),
                        adc16sps_sample_spread_pp_degC=round((samples.max() - samples.min()) / S_K, 3),
                        adc32sps_sample_spread_pp_uV=round((samples32.max() - samples32.min()) * 1e6, 2),
                        cm_at_ainp_pp_V=round(float(vp[m].max() - vp[m].min()), 3))
    print(lbl, results[lbl])
    axes[0].plot(t * 1e3, vd * 1e3, lw=0.7, label=lbl)
    axes[1].plot(t * 1e3, (vd - final) * 1e6, lw=0.7, label=lbl)
    axes[2].plot(t * 1e3, (vd - final) * 1e6, lw=0.7, label=lbl)
axes[0].set_ylabel("V(AIN0-AIN1) (mV)"); axes[0].set_title("Thermocouple filter output: 12.3 mV DC + 1 V/50 Hz CM + 50 mVpp/100 kHz burst (20-30 ms)")
axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8); axes[0].set_xlim(0, 250)
axes[1].set_ylabel("residual (uV)"); axes[1].set_xlim(40, 250); axes[1].set_ylim(-400, 400); axes[1].grid(alpha=0.3)
axes[1].set_title("Residual vs settled value (50 Hz CM->DM conversion)"); axes[1].legend(fontsize=8)
axes[2].set_xlim(19.5, 30.5); axes[2].set_ylim(-600, 600); axes[2].grid(alpha=0.3); axes[2].set_xlabel("time (ms)")
axes[2].set_ylabel("residual (uV)"); axes[2].set_title("100 kHz burst window"); axes[2].legend(fontsize=8)
plt.tight_layout(); plt.savefig(PLOTS / "tc_transient.png", dpi=130); plt.close()

# ---------------- step response: EMF steps 0 -> 12.3 mV at t = 1 ms (no CM, no burst)
d = run_netlist(tran_netlist(0.0, stop="10m", step="2u", burst=False, cm_amp=0.0, emf_step=True))
t = d["time"]; vd = d["v(ainp)"] - d["v(ainn)"]
plt.figure(figsize=(7, 3.8))
plt.plot(t * 1e3, vd * 1e3); plt.axhline(12.3, color="k", ls=":", lw=0.6)
plt.xlabel("time (ms)"); plt.ylabel("V(AIN0-AIN1) (mV)"); plt.title("Filter step response, 0 -> 12.3 mV step at 1 ms")
plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig(PLOTS / "tc_step_response.png", dpi=130); plt.close()
m = t > 1e-3
results["step_settle_1LSB_ms"] = round(float(t[m][np.argmax(np.abs(vd[m] - vd[-1]) < LSB)] * 1e3 - 1.0), 2)
results["step_tau_ms_analytic"] = round(2 * 1e3 * (100e-9 + 5e-9) * 1e3, 3)

# ---------------- open thermocouple: operating point of the bias network
d = run_netlist(tran_netlist(0.0, stop="3", step="1m", burst=False, cm_amp=0.0, open_tc=True))
t = d["time"]; vd = d["v(ainp)"] - d["v(ainn)"]
results["open_tc"] = dict(V_ainp_V=round(float(d["v(ainp)"][-1]), 3), V_ainn_V=round(float(d["v(ainn)"][-1]), 3),
                          V_diff_mV=round(float(vd[-1]) * 1e3, 1), V_diff_LSB=round(float(vd[-1]) / LSB, 0),
                          t_to_half_final_s=round(float(t[np.argmax(vd >= vd[-1] / 2)]), 3))
print("open TC:", results["open_tc"])

# ---------------- AC analysis
dd = run_netlist(AC_DM)
f = np.real(dd["frequency"]); hd = dd["v(ainp)"] - dd["v(ainn)"]
plt.figure(figsize=(8, 4.6))
plt.semilogx(f, 20 * np.log10(np.abs(hd)), label="differential: V(AIN0-AIN1)/Vd")
for mm, ls in ((0.0, "--"), (0.10, "-."), (0.01, ":")):
    dc = run_netlist(ac_cm(mm))
    hcm_d = dc["v(ainp)"] - dc["v(ainn)"]; hcm = dc["v(ainp)"]
    if mm == 0.0:
        plt.semilogx(f, 20 * np.log10(np.abs(hcm)), ls=ls, label="common-mode gain at AIN0: V(AIN0)/Vcm")
    plt.semilogx(f, 20 * np.log10(np.maximum(np.abs(hcm_d), 1e-12)), ls=ls,
                 label=f"CM->DM conversion, Ccm mismatch {mm*100:.0f} %")
    results[f"ac_cm_to_dm_mismatch_{mm}"] = {
        "50Hz_dB": round(float(20 * np.log10(np.abs(np.interp(50, f, np.abs(hcm_d))))), 1),
        "100kHz_dB": round(float(20 * np.log10(np.abs(np.interp(100e3, f, np.abs(hcm_d))))), 1)}
results["ac_dm"] = {f"{fx}Hz_dB": round(float(20 * np.log10(np.interp(fx, f, np.abs(hd)))), 2)
                    for fx in (10, 50, 100, 758, 1000, 10000, 100000, 1000000)}
results["ac_cm_gain_at_ain0"] = {f"{fx}Hz_dB": round(float(20 * np.log10(np.interp(fx, f, np.abs(hcm)))), 2)
                                 for fx in (50, 15900, 100000, 1000000)}
f3 = f[np.argmax(np.abs(hd) < np.abs(hd[0]) / math.sqrt(2))]
results["ac_dm"]["f_3dB_Hz"] = round(float(f3), 1)
plt.axvline(50, color="grey", ls=":", lw=0.6); plt.axvline(100e3, color="grey", ls=":", lw=0.6)
plt.xlabel("frequency (Hz)"); plt.ylabel("gain (dB)"); plt.ylim(-130, 5); plt.grid(True, which="both", alpha=0.3)
plt.title("Thermocouple input filter: 2x1 k, Cd = 100 nF, Ccm = 2x10 nF, ADS1115 load")
plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(PLOTS / "tc_filter_bode.png", dpi=130); plt.close()
print(json.dumps({k: v for k, v in results.items() if k.startswith("ac")}, indent=1))

with open(HERE / "results_thermocouple.json", "w") as fh:
    json.dump(results, fh, indent=1)
print("written results_thermocouple.json")
