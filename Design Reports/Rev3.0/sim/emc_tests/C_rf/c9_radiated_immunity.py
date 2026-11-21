"""C_rf step 9 - radiated RF immunity (EN 55014-2:2015 5.5 Table 11: 80-1000 MHz, 3 V/m rms unmodulated, 1 kHz 80 % AM,
IEC 61000-4-3 or -4-22, criterion A for category IV 7.2.4 - PDF p.20/23).

Model: the same thin-wire MoM EUT as c5 (PCB ground grid, panel metal, FPC return, mains band + HLK barrier, mains cable,
heater, fan and thermocouple leads) illuminated by a plane wave of 3 V/m from 10 directions/polarisations (front, back,
sides, top; both polarisations) -> induced CM currents. The thermocouple lead's CM current at J20 is converted to RF at the
ADS1115 pins with the per-ampere transfer of c8 (input network incl. tolerance corner), then to a temperature shift with
the c8 rectification bound (EMIRR 20 dB, CM weight 1) and a realistic estimate (EMIRR 50 dB above 80 MHz, CM weight 0.1).
The FPC return current gives the CM disturbance at the panel's RGB inputs: V = w * L'_ret * l * I (c3: 0.24 nH/mm worst line).
Field-to-trace coupling on the board (0.2 mm microstrip over In1): bound V <= w*mu0*(2E/eta0)*l*h per trace.
Limits: the IEC 61000-4-3 uniform-field set-up (1.5 x 1.5 m UFA, cable 1 m exposed) is NOT read from the standard; free
space, no RGP, no oven steel.
Outputs: results.json["radiated_immunity"], plots/radimm_*.png
"""
import json, math, time
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *
import c5_cm_structure as c5

E_RMS = 3.0
PK = math.sqrt(2) * 1.8
TOL_C = 0.5
SEEBECK = 41e-6
tr = json.load(open(os.path.join(WORK, "tc_transfer.json")))
I2D = load_results()["inductance2d"]
Lret_line = I2D["fpc_tft"]["G3 (pin 16) alone, returns GND + VDD"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
FPC_L = 0.0877

EXC = []
for kd, pols in (((0, 0, -1), ((1, 0, 0), (0, 1, 0))), ((0, 0, 1), ((1, 0, 0), (0, 1, 0))), ((1, 0, 0), ((0, 1, 0), (0, 0, 1))),
                 ((-1, 0, 0), ((0, 1, 0), (0, 0, 1))), ((0, -1, 0), ((1, 0, 0), (0, 0, 1)))):
    for p in pols:
        EXC.append((np.array(kd, float), np.array(p, float)))


def interp_tr(corner, key, f):
    t = tr[corner]
    return np.interp(f / 1e6, t["f_MHz"], t[key])


def run(cfg, freqs, label):
    w = c5.build(cfg)
    src, loads = c5.setup_loads(w, cfg)
    tags = np.array(w.tags)
    out = {k: [] for k in ("tc_root", "fpc_max", "hlk", "mains_root", "pcb_max")}
    t0 = time.time()
    for f in freqs:
        if f > cfg.get("fmax", 2e9):
            for k in out:
                out[k].append(float("nan"))
            continue
        Z = w.Z(f)
        for b, zf in loads.items():
            Z[b, b] += zf(f)
        V = np.stack([w.plane_wave_V(f, E_RMS, p, k) for k, p in EXC], axis=1)
        I = np.linalg.solve(Z, V)
        res = {k: 0.0 for k in out}
        for j in range(I.shape[1]):
            c = w.seg_currents(I[:, j])
            for key, tag, fn in (("tc_root", "tc", "root"), ("fpc_max", "fpc", "max"), ("hlk", "hlk", "max"), ("mains_root", "mains_cable", "root"), ("pcb_max", "pcb", "max")):
                segs = np.where(tags == tag)[0]
                if len(segs) == 0:
                    continue
                val = np.abs(c[segs[0], 0]) if fn == "root" else np.abs(c[segs]).max()
                res[key] = max(res[key], float(val))
        for k in out:
            out[k].append(res[k])
    print(label, "%.0fs" % (time.time() - t0), flush=True)
    return {k: np.array(v) for k, v in out.items()}


if __name__ == "__main__":
    freqs = np.geomspace(80e6, 1000e6, 30)
    cfgs = {"nominal (TC 1.0 m)": {}, "TC 0.5 m": {"tc": 0.5}, "TC 2.0 m": {"tc": 2.0}, "no mains cable": {"mains_cable": False},
            "Y1 1 nF (scope B), barrier 50 pF": {"Ciso": 50e-12, "Y1": 1e-9},
            "oven body + probe bonded (<=400 MHz)": {"oven": True, "tc_chassis": "bonded", "fmax": 400e6},
            "oven body + probe 20 pF (<=400 MHz)": {"oven": True, "tc_chassis": "20pF", "fmax": 400e6},
            "oven body + probe bonded + Y1 1 nF (<=400 MHz)": {"oven": True, "tc_chassis": "bonded", "Ciso": 50e-12, "Y1": 1e-9, "fmax": 400e6},
            "proposal: panel frame bonded to PCB GND (6 points)": c5.CONFIGS["bond_6pt"]}
    # v2 (review): the lossless structure over-states the 170-180 MHz resonance; add the series loss of the Q band and the
    # driver loading reflected into the CM loop (w^2 M^2 Y, from the SPICE chain), both from results.json["emission"]
    EM = load_results()["emission"]
    SCd = load_results()["spice_chain"]
    ELL = 0.08765
    def _y(d):
        a = np.array(d["fpc_moment_Am"]); v = np.array(d["V_oc_V"])
        I0 = a[:, 0] * np.exp(1j * a[:, 1]) / ELL; V = v[:, 0] * np.exp(1j * v[:, 1]); f_ = np.array(d["f_MHz"]) * 1e6
        ok = np.abs(V) > 1e-4
        return f_[ok], I0[ok] / V[ok]
    def _yd(key, mult=1.0):              # passive distributed-EMF admittance (c4c), Re clipped >= 0
        d = SCd["Ydist"][key]
        return np.array(d["f_MHz"]) * 1e6, (np.maximum(np.array(d["re"]), 0) + 1j * np.array(d["im"])) * mult
    fyd, yd = _yd("data_in_phase_Rs33", 24); fyp, yp = _yd("pclk_Rs33")
    Md, Mp = EM["M_nH"]["data_in_phase"] * 1e-9, EM["M_nH"]["pclk"] * 1e-9
    def zref(f):
        w_ = 2 * np.pi * f
        return w_ ** 2 * (Md ** 2 * (np.interp(f, fyd, yd.real) + 1j * np.interp(f, fyd, yd.imag)) + Mp ** 2 * (np.interp(f, fyp, yp.real) + 1j * np.interp(f, fyp, yp.imag)))
    for Q in ("30.0", "10.0", "3.0"):
        RL = EM["mode"]["R_loss_added_ohm"][Q]
        cfgs[f"lossy Q {float(Q):g} (nominal cables)"] = {"gap_load": (lambda f, RL=RL: RL + zref(f))}
    RL10 = EM["mode"]["R_loss_added_ohm"]["10.0"]
    cfgs["lossy Q 10 + panel bonded 19 contacts"] = dict(c5.CONFIGS["bond_perimeter"], gap_load=lambda f: RL10 + zref(f))
    cfgs["lossy Q 10 + panel bonded 6 contacts"] = dict(c5.CONFIGS["bond_6pt"], gap_load=lambda f: RL10 + zref(f))
    import sys
    if len(sys.argv) > 1:                       # run a subset and merge into the existing section
        cfgs = {k: v for k, v in cfgs.items() if k in sys.argv[1:]}
    resd = dict(load_results().get("radiated_immunity", {})) if len(sys.argv) > 1 else {}
    resd.update({"model": __doc__.split("\n")[0], "freqs_MHz": (freqs / 1e6).round(2).tolist(), "criterion_A_proposed_degC": TOL_C})
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    for name, cfg in cfgs.items():
        r = run(cfg, freqs, name)
        Itc = r["tc_root"] * PK
        out = {"I_tc_root_mA_rms_max": float(np.nanmax(r["tc_root"]) * 1e3), "I_fpc_mA_rms_max": float(np.nanmax(r["fpc_max"]) * 1e3),
               "I_mains_root_mA_rms_max": float(np.nanmax(r["mains_root"]) * 1e3), "I_hlk_mA_rms_max": float(np.nanmax(r["hlk"]) * 1e3)}
        for corner in ("corner0", "corner1"):
            vdm = interp_tr(corner, "Vdm_per_A", freqs) * Itc
            vcm = interp_tr(corner, "Vcm_per_A", freqs) * Itc
            vj = interp_tr(corner, "VJ_per_A", freqs) * Itc
            dTw = (vdm ** 2 + vcm ** 2) / (0.1 * 10) * 1.32 / SEEBECK
            dTr = (vdm ** 2 + 0.1 * vcm ** 2) / (0.1 * 10 ** 2.5) * 1.32 / SEEBECK
            out[corner] = {"Vdm_ADC_mVpk_max": float(np.nanmax(vdm) * 1e3), "Vcm_ADC_mVpk_max": float(np.nanmax(vcm) * 1e3), "VJ20_Vpk_max": float(np.nanmax(vj)),
                           "dT_worst_bound_degC": float(np.nanmax(dTw)), "at_MHz": float(freqs[int(np.nanargmax(dTw))] / 1e6), "dT_realistic_degC": float(np.nanmax(dTr))}
            if corner == "corner1":
                ax[0].semilogy(freqs / 1e6, dTw, label=name + " (bound)")
                ax[0].semilogy(freqs / 1e6, np.maximum(dTr, 1e-9), ":", label=name + " (realistic)")
        vpan = 2 * np.pi * freqs * Lret_line * FPC_L * r["fpc_max"] * PK
        out["panel_input_noise_Vpk_max"] = float(np.nanmax(vpan))
        out["panel_noise_at_MHz"] = float(freqs[int(np.nanargmax(vpan))] / 1e6)
        ax[1].semilogy(freqs / 1e6, r["tc_root"] * 1e3, label=name + " TC lead at J20")
        ax[1].semilogy(freqs / 1e6, r["fpc_max"] * 1e3, "--", label=name + " FPC return")
        ax[2].semilogy(freqs / 1e6, vpan, label=name)
        resd[name] = out
    # board traces: bound
    hb = 0.2e-3
    vtr = {}
    for nm, L in (("TC_P/TC_N (33 mm)", 33.4e-3), ("I2C (95 mm)", 95e-3), ("ZCD (120 mm)", 120e-3), ("RGB (108 mm)", 108e-3)):
        f = 1e9
        vtr[nm] = 2 * math.pi * f * MU0 * (2 * E_RMS / ETA0) * L * hb * PK
    resd["field_to_trace_bound_Vpk_at_1GHz"] = rnd(vtr, 6)
    resd["touch_panel"] = "GT911 + ITO sensor: false touches / missed touches under 3 V/m depend on the GT911 firmware filtering - NOT SIMULABLE; check in pre-compliance with the panel in place"
    ax[0].axhline(TOL_C, color="r", ls="--", label="proposed criterion A 0.5 degC"); ax[0].set_xlabel("MHz"); ax[0].set_ylabel("degC")
    ax[0].set_title("Thermocouple shift under 3 V/m, 80 % AM (worst tolerance corner)"); ax[0].legend(fontsize=6); ax[0].grid(True, which="both", alpha=.3)
    ax[1].set_xlabel("MHz"); ax[1].set_ylabel("mA rms (3 V/m)"); ax[1].set_title("Induced CM currents (max over 10 incidences)"); ax[1].legend(fontsize=6); ax[1].grid(True, which="both", alpha=.3)
    ax[2].axhline(0.99, color="r", ls="--", label="panel VIL 0.3 VDD (logic margin)"); ax[2].set_xlabel("MHz"); ax[2].set_ylabel("V pk")
    ax[2].set_title("CM disturbance at the panel RGB inputs"); ax[2].legend(fontsize=6); ax[2].grid(True, which="both", alpha=.3)
    if len(sys.argv) == 1:
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "radimm_currents_tc.png"), dpi=150)
    save_section("radiated_immunity", rnd(resd, 5))
    print(json.dumps(rnd(resd, 4), indent=1)[:4000])
