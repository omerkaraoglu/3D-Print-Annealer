"""Analytic calculations for the Rev3.0 EMI / SI report.
Run:  python analytic.py   -> prints results, writes results_analytic.json and plots/*.png
"""
import json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLOTS = HERE / "plots"
PLOTS.mkdir(exist_ok=True)
R = {}
c0 = 299_792_458.0
kB = 1.380649e-23

# --------------------------------------------------------------------------
# 1. Microstrip impedance (Hammerstad-Jensen with thickness correction) + IPC-2141
# --------------------------------------------------------------------------
def microstrip(w, h, t, er):
    """w,h,t in mm. Returns Z0 [ohm], eps_eff, tpd [ps/mm]."""
    w_eff = w + (t / math.pi) * (1 + math.log(2 * h / t))     # Hammerstad thickness correction
    u = w_eff / h
    eeff = (er + 1) / 2 + (er - 1) / 2 * (1 / math.sqrt(1 + 12 / u))
    if u <= 1:
        eeff += (er - 1) / 2 * 0.04 * (1 - u) ** 2
        z0 = 60 / math.sqrt(eeff) * math.log(8 / u + 0.25 * u)
    else:
        z0 = 120 * math.pi / (math.sqrt(eeff) * (u + 1.393 + 0.667 * math.log(u + 1.444)))
    tpd = math.sqrt(eeff) / c0 * 1e9          # ps/mm
    return z0, eeff, tpd

def microstrip_ipc2141(w, h, t, er):
    """IPC-2141: Z0 = 87/sqrt(er+1.41) * ln(5.98h/(0.8w+t)); valid 0.1<w/h<2."""
    return 87 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * w + t))

stackups = {
    "2-layer 1.6 mm, w=0.25 mm (h=1.5 mm core)": dict(w=0.25, h=1.50, t=0.035, er=4.3),
    "2-layer 1.6 mm, w=0.60 mm":                 dict(w=0.60, h=1.50, t=0.035, er=4.3),
    "4-layer, w=0.25 mm (h=0.20 mm prepreg)":    dict(w=0.25, h=0.20, t=0.035, er=4.4),
    "4-layer, w=0.30 mm":                        dict(w=0.30, h=0.20, t=0.035, er=4.4),
}
R["microstrip"] = {}
print("=== Microstrip impedance ===")
for name, p in stackups.items():
    z0, eeff, tpd = microstrip(**p)
    zipc = microstrip_ipc2141(**p)
    R["microstrip"][name] = dict(**p, Z0_hammerstad=round(z0, 1), Z0_ipc2141=round(zipc, 1),
                                 eps_eff=round(eeff, 3), tpd_ps_per_mm=round(tpd, 2),
                                 C_per_mm_pF=round(tpd / z0, 4),      # ps/mm / ohm = pF/mm
                                 L_per_mm_nH=round(tpd * z0 * 1e-3, 4))
    print(f"{name:44s} Z0(HJ)={z0:6.1f}  Z0(IPC)={zipc:6.1f}  eeff={eeff:.3f}  tpd={tpd:.2f} ps/mm")

# --------------------------------------------------------------------------
# 2. Critical length vs edge rate
# --------------------------------------------------------------------------
tpd_used = 6.5   # ps/mm, conservative value used for the simulations; HJ gives 5.6-6.0
R["critical_length"] = {"tpd_ps_per_mm": tpd_used, "rows": []}
print("\n=== Critical length (tpd = %.1f ps/mm) ===" % tpd_used)
for tr in (1.0, 2.0, 4.0):
    l_tr6 = tr * 1e3 / (6 * tpd_used)   # mm; line is 'long' when td > tr/6
    l_tr4 = tr * 1e3 / (4 * tpd_used)
    l_rt = tr * 1e3 / (2 * tpd_used)    # round-trip 2*td < tr
    f_knee = 0.5 / tr * 1e3             # MHz
    R["critical_length"]["rows"].append(dict(tr_ns=tr, l_tr6_mm=round(l_tr6, 1), l_tr4_mm=round(l_tr4, 1),
                                             l_roundtrip_mm=round(l_rt, 1), f_knee_MHz=round(f_knee, 0)))
    print(f"tr={tr} ns: l(td=tr/6)={l_tr6:5.1f} mm  l(td=tr/4)={l_tr4:5.1f} mm  l(2td=tr)={l_rt:5.1f} mm  f_knee={f_knee:.0f} MHz")
R["critical_length"]["td_60mm_ps"] = 60 * tpd_used
R["critical_length"]["td_90mm_ps"] = 90 * tpd_used

# --------------------------------------------------------------------------
# 3. Harmonic envelope of a 20 MHz trapezoid, 0..3.3 V
# --------------------------------------------------------------------------
A = 3.3; f0 = 20e6; T = 1 / f0; duty = 0.5
f = np.logspace(6, 9, 1500)
plt.figure(figsize=(8, 5))
R["harmonics"] = {"f1_MHz": round(1 / (math.pi * duty * T) / 1e6, 1), "corners": {}, "levels_dBuV": {}}
for tr in (1e-9, 2e-9, 4e-9):
    env = 2 * A * duty * np.minimum(1, 1 / (np.pi * f * duty * T)) * np.minimum(1, 1 / (np.pi * f * tr))
    plt.semilogx(f / 1e6, 20 * np.log10(env / 1e-6), label=f"envelope, tr = {tr*1e9:.0f} ns")
    R["harmonics"]["corners"][f"tr_{tr*1e9:.0f}ns"] = round(1 / (math.pi * tr) / 1e6, 1)
    lv = {}
    for fh in (20e6, 60e6, 100e6, 200e6, 300e6, 500e6, 1e9):
        v = 2 * A * duty * min(1, 1 / (math.pi * fh * duty * T)) * min(1, 1 / (math.pi * fh * tr))
        lv[f"{fh/1e6:.0f}MHz"] = round(20 * math.log10(v / 1e-6), 1)
    R["harmonics"]["levels_dBuV"][f"tr_{tr*1e9:.0f}ns"] = lv
n = np.arange(1, 51)
fh = n * f0
an = 2 * A * duty * np.abs(np.sinc(fh * duty * T)) * np.abs(np.sinc(fh * 1.5e-9))
plt.stem(fh / 1e6, 20 * np.log10(np.maximum(an, 1e-9) / 1e-6), linefmt="C3-", markerfmt="C3.", basefmt=" ",
         label="actual harmonics, tr = 1.5 ns, 50 % duty")
plt.axvline(R["harmonics"]["f1_MHz"], color="k", ls=":", lw=0.8)
plt.text(R["harmonics"]["f1_MHz"] * 1.05, 128, "f1 = 1/(pi*tau)\n-20 dB/dec", fontsize=8)
for tr in (1e-9, 2e-9, 4e-9):
    fc = 1 / (math.pi * tr) / 1e6
    plt.axvline(fc, color="grey", ls="--", lw=0.6)
    plt.text(fc * 1.03, 60, f"f2={fc:.0f} MHz\n-40 dB/dec", fontsize=7)
plt.xlabel("Frequency (MHz)"); plt.ylabel("Harmonic amplitude (dBuV, peak)")
plt.title("Envelope of 20 MHz 3.3 V trapezoid (50 % duty) vs edge rate")
plt.grid(True, which="both", alpha=0.3); plt.legend(fontsize=8); plt.ylim(40, 135)
plt.tight_layout(); plt.savefig(PLOTS / "harmonic_envelope.png", dpi=130); plt.close()
print("\n=== Harmonic envelope ===", R["harmonics"])

# --------------------------------------------------------------------------
# 4. Radiated E-field estimates at 3 m
# --------------------------------------------------------------------------
# Differential-mode (small loop):  E = 263e-16 * f^2 * A * I / r   [V/m]  (Ott, free space)
# Common-mode (short wire):        E = 12.6e-7 * f * I_cm * L / r   [V/m]  (Ott)
# Class B limits at 3 m: 40 dBuV/m (30-230 MHz), 47 dBuV/m (230-1000 MHz), QP
r = 3.0
def e_dm(f, I, A_loop):  return 263e-16 * f**2 * A_loop * I / r
def e_cm(f, I, L):       return 12.6e-7 * f * I * L / r
def dbuv(e): return 20 * np.log10(max(e, 1e-12) / 1e-6)
ASSUME = {"loop_area_2layer_m2": 60e-3 * 1.5e-3, "loop_area_4layer_m2": 60e-3 * 0.2e-3,
          "cm_antenna_length_m": 0.15, "ground_return_inductance_nH": {"solid_plane": 0.5, "split_or_2layer_gap": 10},
          "cm_path_impedance_ohm": 150, "n_lines_switching": 9}
R["efield"] = {"limits_dBuV_m_at_3m": {"30-230MHz": 40, "230-1000MHz": 47}, "assumptions": ASSUME, "rows": []}
for Rs in (0, 33):
    for fh, tr in ((100e6, 1.5e-9), (200e6, 1.5e-9), (300e6, 1.5e-9)):
        z_src = 35 + Rs
        c_tot = 8e-12 + 60 * 0.06e-12
        tr_eff = math.sqrt(tr**2 + (2.2 * z_src * c_tot) ** 2)
        v_eff = 2 * A * duty * min(1, 1 / (math.pi * fh * duty * T)) * min(1, 1 / (math.pi * fh * tr_eff))
        i_h = v_eff / (z_src + 105)
        i_tot = i_h * ASSUME["n_lines_switching"]
        e1 = e_dm(fh, i_tot, ASSUME["loop_area_2layer_m2"])
        e2 = e_dm(fh, i_tot, ASSUME["loop_area_4layer_m2"])
        rows = {}
        for lbl, Lg in ASSUME["ground_return_inductance_nH"].items():
            v_gb = i_tot * 2 * math.pi * fh * Lg * 1e-9
            i_cm = v_gb / ASSUME["cm_path_impedance_ohm"]
            rows[lbl] = dict(v_gb_mV=round(v_gb * 1e3, 2), i_cm_uA=round(i_cm * 1e6, 1),
                             E_cm_dBuV_m=round(dbuv(e_cm(fh, i_cm, ASSUME["cm_antenna_length_m"])), 1))
        R["efield"]["rows"].append(dict(Rs=Rs, f_MHz=fh / 1e6, tr_eff_ns=round(tr_eff * 1e9, 2),
                                        I_harm_mA_total=round(i_tot * 1e3, 2),
                                        E_dm_2layer_dBuV_m=round(dbuv(e1), 1), E_dm_4layer_dBuV_m=round(dbuv(e2), 1),
                                        cm=rows))
print("\n=== E-field estimates ===")
for row in R["efield"]["rows"]:
    print(row)

# --------------------------------------------------------------------------
# 5. Series termination (ideal value and RC edge slowing)
# --------------------------------------------------------------------------
R["termination"] = {}
for z0 in (55, 105, 130):
    R["termination"][f"ideal_Rs_Z0_{z0}"] = z0 - 35
for Rs in (0, 22, 33, 47):
    for z0, ctr in ((55, 7.1), (105, 3.7)):
        tau = (35 + Rs) * (8 + ctr) * 1e-12
        R["termination"][f"t10_90_Rs{Rs}_Z0{z0}_ns"] = round(2.2 * tau * 1e9, 2)
print("\n=== termination ===", R["termination"])

# --------------------------------------------------------------------------
# 6. I2C pull-up sizing
# --------------------------------------------------------------------------
VDD = 3.3; VOL = 0.4; IOL = 3e-3; tr_max = 300e-9
R["i2c"] = {"Rp_min_ohm": round((VDD - VOL) / IOL, 0),
            "Rp_max_ohm": {f"Cb_{cb}pF": round(tr_max / (0.8473 * cb * 1e-12), 0) for cb in (50, 100)},
            "rise_ns": {}, "sink_mA": {}}
for rp in (1500, 2200, 2700, 3300, 4700, 10000):
    for cb in (50, 100):
        R["i2c"]["rise_ns"][f"Rp_{rp}_Cb_{cb}pF"] = round(0.8473 * rp * cb * 1e-12 * 1e9, 0)
    R["i2c"]["sink_mA"][f"Rp_{rp}"] = round((VDD - VOL) / rp * 1e3, 2)
print("\n=== I2C ===", R["i2c"])

# --------------------------------------------------------------------------
# 7. Thermocouple front end
# --------------------------------------------------------------------------
Rf = 1e3; Cd = 100e-9; Ccm = 10e-9; T_amb = 273.15 + 85
f_dm = 1 / (2 * math.pi * 2 * Rf * (Cd + Ccm / 2))
f_cm = 1 / (2 * math.pi * Rf * Ccm)
def att_db(fx, fc): return -10 * math.log10(1 + (fx / fc) ** 2)
NB_dm = math.pi / 2 * f_dm
vn_filter = math.sqrt(4 * kB * T_amb * 2 * Rf * NB_dm)
vn_filter_adc_bw = math.sqrt(4 * kB * T_amb * 2 * Rf * 16)
LSB = 0.256 / 32768
S_K = 41e-6
adc_noise = LSB / math.sqrt(12) + 1.5e-6     # quantisation + ~1.5 uV internal (conservative)
R["thermocouple"] = dict(
    R_ohm=Rf, Cdiff_nF=Cd * 1e9, Ccm_nF=Ccm * 1e9,
    f_dm_Hz=round(f_dm, 1), f_cm_Hz=round(f_cm, 0),
    att_dm_50Hz_dB=round(att_db(50, f_dm), 3), att_dm_100kHz_dB=round(att_db(100e3, f_dm), 1),
    att_cm_50Hz_dB=round(att_db(50, f_cm), 3), att_cm_100kHz_dB=round(att_db(100e3, f_cm), 1),
    cm_to_dm_10pct_mismatch_50Hz_uV_per_V=round(2 * math.pi * 50 * Rf * 0.1 * Ccm * 1e6, 1),
    cm_to_dm_1pct_mismatch_50Hz_uV_per_V=round(2 * math.pi * 50 * Rf * 0.01 * Ccm * 1e6, 2),
    thermal_noise_filterBW_nVrms=round(vn_filter * 1e9, 1),
    thermal_noise_16Hz_nVrms=round(vn_filter_adc_bw * 1e9, 1),
    LSB_uV=round(LSB * 1e6, 4), LSB_degC=round(LSB / S_K, 3),
    fullscale_degC_equiv=round(0.256 / S_K, 0),
    adc_noise_rms_uV=round(adc_noise * 1e6, 2),
    adc_noise_rms_degC=round(adc_noise / S_K, 3),
    adc_noise_rms_degC_1s_avg_16SPS=round(adc_noise / S_K / math.sqrt(16), 3),
    adc_noise_rms_degC_1s_avg_32SPS=round(adc_noise / S_K / math.sqrt(32), 3),
    settle_time_to_1LSB_ms=round(2 * Rf * (Cd + Ccm / 2) * math.log(0.0123 / LSB) * 1e3, 1),
)
Rb = 10e6; R_tc = 10.0
I_bias = VDD / (2 * Rb)
R["thermocouple"].update(dict(
    bias_current_nA=round(I_bias * 1e9, 1),
    err_bias_at_terminal_uV=round(I_bias * R_tc * 1e6, 2),
    err_bias_at_terminal_degC=round(I_bias * R_tc / S_K, 3),
    err_bias_after_filterR_uV=round(I_bias * (R_tc + 2 * Rf) * 1e6, 1),
    err_bias_after_filterR_degC=round(I_bias * (R_tc + 2 * Rf) / S_K, 2),
    gain_err_from_Zin_pct=round((R_tc + 2 * Rf) / 710e3 * 100, 3),
    gain_err_from_Zin_degC_at_300C=round((R_tc + 2 * Rf) / 710e3 * 300, 2),
    open_tc_reading_mV=round(VDD * 710e3 / (2 * Rb + 710e3) * 1e3, 1),
    open_tc_reading_LSB=round(VDD * 710e3 / (2 * Rb + 710e3) / LSB, 0),
    open_tc_time_constant_s=round((Rb / 2) * (Cd + Ccm / 2), 3),
    cm_bias_V=VDD / 2,
    cmrr_residual_uV_per_V=round(1 / 10 ** (105 / 20) * 1e6, 2),
    adc_filter_50Hz_dB_16SPS=round(20 * math.log10(abs(math.sin(math.pi * 50 / 16) / (math.pi * 50 / 16))), 1),
    adc_filter_50Hz_dB_32SPS=round(20 * math.log10(abs(math.sin(math.pi * 50 / 32) / (math.pi * 50 / 32))), 1),
))
print("\n=== thermocouple ===")
for k, v in R["thermocouple"].items():
    print(f"  {k}: {v}")

# --------------------------------------------------------------------------
# 8. Power ripple
# --------------------------------------------------------------------------
Vin, Vout, fsw, L = 5.0, 3.3, 580e3, 4.7e-6
D = Vout / Vin
dIL = (Vin - Vout) * D / (fsw * L)
R["buck"] = {}
for Cnom, lbl in ((44e-6, "nominal 2x22uF"), (28e-6, "derated 2x14uF (DC bias)")):
    vr_c = dIL / (8 * fsw * Cnom)
    vr_esr = dIL * 2.5e-3
    R["buck"][lbl] = dict(D=round(D, 3), dIL_App=round(dIL, 3), Vripple_cap_mV=round(vr_c * 1e3, 2),
                          Vripple_esr_mV=round(vr_esr * 1e3, 2),
                          Vripple_total_mV=round((vr_c + vr_esr) * 1e3, 2),
                          Vripple_esl_0p3nH_mV=round(0.3e-9 * dIL / ((1 - D) / fsw) * 1e3, 3))
Vin_b, Vo_b, Io_b, fsw_b, Lb, eta = 5.0, 9.6, 0.14, 1.2e6, 10e-6, 0.85
Db = 1 - Vin_b / Vo_b
dIL_b = Vin_b * Db / (fsw_b * Lb)
IL_avg = Io_b * Vo_b / (Vin_b * eta)
Cin_eff = 7e-6
vr_in = dIL_b / (8 * fsw_b * Cin_eff) + dIL_b * 5e-3
Lf = 2.2e-6; C1 = 7e-6
fc_lc = 1 / (2 * math.pi * math.sqrt(Lf * C1))
att_pi = 40 * math.log10(fsw_b / fc_lc)
R["boost"] = dict(D=round(Db, 3), dIL_App=round(dIL_b, 3), IL_avg_A=round(IL_avg, 3),
                  IL_peak_A=round(IL_avg + dIL_b / 2, 3),
                  Vin_ripple_single_10uF_mVpp=round(vr_in * 1e3, 2),
                  pi_filter=dict(L_uH=Lf * 1e6, C_each_uF_eff=C1 * 1e6, fc_Hz=round(fc_lc, 0),
                                 att_at_fsw_dB=round(att_pi, 1),
                                 ripple_on_5V_after_filter_uVpp=round(vr_in * 10 ** (-att_pi / 20) * 1e6, 1),
                                 Zo_ohm=round(math.sqrt(Lf / C1), 3),
                                 Q_undamped_ESR_5mohm=round(math.sqrt(Lf / C1) / 0.01, 1),
                                 pwm_dim_step_mA=round(IL_avg * 1e3, 0)))
print("\n=== buck ===", R["buck"]); print("=== boost ===", R["boost"])

with open(HERE / "results_analytic.json", "w") as fh:
    json.dump(R, fh, indent=1)
print("\nwritten results_analytic.json")
