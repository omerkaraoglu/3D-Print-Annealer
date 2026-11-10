"""(d) Power rails.

1. TPS562201 buck 5 V -> 3.3 V output ripple: inductor-current triangle (analytic dIL) injected into the
   output capacitor model (2 x 22 uF X5R, ESR 5 mohm, ESL 0.6 nH each; DC-bias-derated 2 x 14 uF).
2. MIC2288 boost 5 V -> 9.6 V / 140 mA input current (continuous triangle 0.2 App at 1.2 MHz around 0.32 A)
   plus the PWM backlight dimming envelope (1 kHz, 50 %), injected into the 5 V rail:
   a) no filter: 10 uF at the boost input directly on the 5 V rail (20 nH trace)
   b) pi filter: 10 uF | 2.2 uH | 10 uF
   c) pi filter + damping: as (b) plus 47 uF electrolytic (ESR 0.5 ohm) across the boost-side cap
   d) as (c) plus 100 uF polymer bulk (ESR 30 mohm) on the 5 V rail
   5 V rail source model: HLK-10M05 output (470 uF electrolytic, ESR 0.15 ohm) through 30 mohm + 100 nH wiring,
   plus a 22 uF ceramic at the buck input.
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
results = {}

# ---------------------------------------------------------------- buck output ripple
Vin, Vout, fsw, L = 5.0, 3.3, 580e3, 4.7e-6
D = Vout / Vin; T = 1 / fsw
dIL = (Vin - Vout) * D / (fsw * L)
def buck_netlist(C_each_uF):
    # inductor current = DC load + triangle; only the AC triangle flows into the caps (DC goes to the load)
    return f"""buck output ripple
Iac out 0 PULSE({-dIL/2} {dIL/2} 0 {D*T} {(1-D)*T} 1p {T})
* two output ceramics in parallel, each C + ESR 5 mohm + ESL 0.6 nH
C1 out n1 {C_each_uF}u
R1 n1 n2 5m
L1 n2 0 0.6n
C2 out n3 {C_each_uF}u
R2 n3 n4 5m
L2 n4 0 0.6n
* load 1 A equivalent (3.3 ohm) - keeps the DC path defined
Rl out 0 3.3
.tran 2n 1m 990u 2n
.end
"""
plt.figure(figsize=(8, 3.8))
for C_each, lbl in ((22, "2 x 22 uF nominal"), (14, "2 x 14 uF (DC-bias derated)")):
    d = run_netlist(buck_netlist(C_each))
    t = d["time"]; v = d["v(out)"]
    m = t > 995e-6
    vpp = v[m].max() - v[m].min()
    results[f"buck_{lbl}"] = dict(dIL_App=round(dIL, 3), Vripple_pp_mV=round(float(vpp) * 1e3, 2),
                                  analytic_cap_mV=round(dIL / (8 * fsw * 2 * C_each * 1e-6) * 1e3, 2),
                                  analytic_esr_mV=round(dIL * 2.5e-3 * 1e3, 2))
    print(lbl, results[f"buck_{lbl}"])
    plt.plot((t[m] - 995e-6) * 1e6, (v[m] - v[m].mean()) * 1e3, label=f"{lbl}: {vpp*1e3:.1f} mVpp")
plt.xlabel("time (us)"); plt.ylabel("ripple (mV)"); plt.title("TPS562201 3.3 V output ripple, 580 kHz, 4.7 uH, 1 A load")
plt.grid(alpha=0.3); plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(PLOTS / "buck_output_ripple.png", dpi=130); plt.close()

# ---------------------------------------------------------------- boost input / pi filter
Vin_b, Vo_b, Io_b, fsw_b, Lb, eta = 5.0, 9.6, 0.14, 1.2e6, 10e-6, 0.85
Db = 1 - Vin_b / Vo_b; Tb = 1 / fsw_b
dILb = Vin_b * Db / (fsw_b * Lb)
ILavg = Io_b * Vo_b / (Vin_b * eta)
results["boost_input"] = dict(D=round(Db, 3), dIL_App=round(dILb, 3), IL_avg_A=round(ILavg, 3))

RAIL = f"""* ---- 5 V rail source: HLK-10M05 + wiring + buck input ceramic
V5 hlk 0 5
Rhlk hlk hlk2 0.03
Chlk hlk2 hlk3 470u
Resr hlk3 0 0.15
Rw hlk2 rw 0.03
Lw rw rail 100n
Cbk rail bk1 22u
Rbk bk1 0 5m
"""
LOAD = f"""* ---- boost input current: triangle (continuous conduction) x PWM dimming envelope (1 kHz, 50 %)
* PULSE: rise = D*T, fall = (1-D)*T - 1 ns, pw 0.5 ns, so that TR+PW+TF < PER (otherwise ngspice flattens it)
Vtri tri 0 PULSE({ILavg-dILb/2} {ILavg+dILb/2} 0 {Db*Tb} {(1-Db)*Tb-1e-9} 0.5n {Tb})
Vpwm pwm 0 PULSE(0 1 0 200n 200n 499.6u 1m)
Bload bin 0 I = V(tri)*V(pwm)
"""
def filt_netlist(variant):
    if variant == "none":
        net = """* no filter: 20 nH trace to the boost input cap
Lt rail bin 20n
Cin bin c1 10u
Rc1 c1 0 5m
"""
    elif variant == "pi":
        net = """* pi filter 10 uF | 2.2 uH (DCR 60 mohm) | 10 uF
Ca rail a1 10u
Ra a1 0 5m
Lf rail lf1 2.2u
Rdcr lf1 bin 0.06
Cin bin c1 10u
Rc1 c1 0 5m
"""
    elif variant == "pi+damp":
        net = """* pi filter + damping: 47 uF electrolytic (ESR 0.5 ohm ~ sqrt(L/C)) across the boost-side 10 uF
Ca rail a1 10u
Ra a1 0 5m
Lf rail lf1 2.2u
Rdcr lf1 bin 0.06
Cin bin c1 10u
Rc1 c1 0 5m
Cdmp bin d1 47u
Rdmp d1 0 0.5
"""
    else:
        net = """* as pi+damp, plus 100 uF polymer bulk (ESR 30 mohm) on the 5 V rail
Ca rail a1 10u
Ra a1 0 5m
Lf rail lf1 2.2u
Rdcr lf1 bin 0.06
Cin bin c1 10u
Rc1 c1 0 5m
Cdmp bin d1 47u
Rdmp d1 0 0.5
Cblk rail b1 100u
Rblk b1 0 0.03
"""
    return "boost input filter " + variant + "\n" + RAIL + net + LOAD + ".tran 10n 2.0m 0 10n\n.end\n"

VARIANTS = ("none", "pi", "pi+damp", "pi+damp+bulk")

def ac_netlist(variant):
    """Transfer impedance |V(rail)/I(boost input)| : 1 A AC current drawn at the boost input."""
    body = filt_netlist(variant).split("* ---- boost input current")[0]
    body = body.replace("boost input filter " + variant, "boost input filter AC " + variant)
    return body + "Iac 0 bin DC 0 AC 1\n.ac dec 40 100 10Meg\n.end\n"

fig, axes = plt.subplots(2, 1, figsize=(10, 7))
colors = {"none": "C3", "pi": "C0", "pi+damp": "C2", "pi+damp+bulk": "C1"}
for variant in VARIANTS:
    d = run_netlist(filt_netlist(variant))
    t = d["time"]; v = d["v(rail)"]; vb = d["v(bin)"]
    m = (t > 1.0e-3)                      # steady state, second PWM period (PWM on 1.0-1.5 ms, off 1.5-2.0 ms)
    vac = v[m] - v[m].mean()
    # switching-frequency ripple: remove everything below ~200 kHz with a 2 us moving average (keeps 1.2 MHz)
    dt = 5e-9; k = int(2e-6 / dt)
    tu = np.arange(t[m][0], t[m][-1], dt); vu = np.interp(tu, t[m], vac); vbu = np.interp(tu, t[m], vb[m])
    slow = np.convolve(vu, np.ones(k) / k, mode="same")
    hf = (vu - slow)[k:-k]
    hfb = (vbu - np.convolve(vbu, np.ones(k) / k, mode="same"))[k:-k]
    tk = tu[k:-k]
    mon = (tk > 1.20e-3) & (tk < 1.48e-3)   # PWM 'on' window, after the step ringing
    # resistive DC shift of the rail from the 0.32 A step: I * (Rhlk + Rw) = 19 mV pp; what is left above that is ringing
    dc_shift = ILavg * 0.06
    results[f"filter_{variant}"] = dict(total_rail_pp_mV=round(float(vac.max() - vac.min()) * 1e3, 2),
                                       resistive_step_pp_mV=round(dc_shift * 1e3, 2),
                                       ringing_above_resistive_step_mV=round(float(vac.max() - vac.min() - dc_shift) * 1e3, 2),
                                       rail_1p2MHz_ripple_pp_mV=round(float(hf[mon].max() - hf[mon].min()) * 1e3, 3),
                                       boost_input_1p2MHz_ripple_pp_mV=round(float(hfb[mon].max() - hfb[mon].min()) * 1e3, 2))
    print(variant, results[f"filter_{variant}"])
    axes[0].plot((tu - 1.0e-3) * 1e6, vu * 1e3, lw=0.6, color=colors[variant], label=variant)
    z = (tu > 1.30e-3) & (tu < 1.305e-3)
    axes[1].plot((tu[z] - 1.30e-3) * 1e6, (vu[z] - vu[z].mean()) * 1e3, lw=0.8, color=colors[variant], label=variant)
axes[0].set_xlim(0, 1000); axes[0].set_xlabel("time (us)"); axes[0].set_ylabel("5 V rail deviation (mV)")
axes[0].set_title("5 V rail with backlight boost load: 0.32 A avg, 0.2 App @ 1.2 MHz, PWM dimming 1 kHz / 50 %")
axes[0].grid(alpha=0.3); axes[0].legend(fontsize=8)
axes[1].set_xlabel("time (us)"); axes[1].set_ylabel("1.2 MHz ripple (mV)"); axes[1].set_title("Switching ripple detail (PWM on)")
axes[1].grid(alpha=0.3); axes[1].legend(fontsize=8)
plt.tight_layout(); plt.savefig(PLOTS / "boost_input_filter_transient.png", dpi=130); plt.close()

plt.figure(figsize=(8, 4.4))
for variant in VARIANTS:
    d = run_netlist(ac_netlist(variant))
    f = np.real(d["frequency"]); z = np.abs(d["v(rail)"])
    plt.semilogx(f, 20 * np.log10(np.maximum(z, 1e-9)), color=colors[variant], label=variant)
    results[f"zt_{variant}"] = {f"{fx/1e3:g}kHz_dBohm": round(float(20 * np.log10(np.interp(fx, f, z))), 1)
                                for fx in (1e3, 10e3, 40e3, 100e3, 1.2e6, 3.6e6)}
    ipk = np.argmax(z[(f > 2e3) & (f < 300e3)]); fpk = f[(f > 2e3) & (f < 300e3)][ipk]
    results[f"zt_{variant}"]["peak_Hz"] = round(float(fpk), 0)
    results[f"zt_{variant}"]["peak_dBohm"] = round(float(20 * np.log10(z[(f > 2e3) & (f < 300e3)][ipk])), 1)
    print(variant, results[f"zt_{variant}"])
plt.axvline(1.2e6, color="grey", ls=":", lw=0.7); plt.text(1.25e6, -70, "fsw", fontsize=8)
plt.xlabel("frequency (Hz)"); plt.ylabel("|V(5V rail) / I(boost input)| (dB ohm)")
plt.title("Transfer impedance from boost input current to the 5 V rail"); plt.grid(True, which="both", alpha=0.3)
plt.legend(fontsize=8); plt.tight_layout(); plt.savefig(PLOTS / "boost_input_filter_bode.png", dpi=130); plt.close()

with open(HERE / "results_power.json", "w") as fh:
    json.dump(results, fh, indent=1)
print("written results_power.json")
