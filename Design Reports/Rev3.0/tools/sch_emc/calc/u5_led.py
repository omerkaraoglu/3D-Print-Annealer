"""U5 LED drive worst case, -20...85 C, tolerances and life (agentHW 2026-11-21). Sources in comments (file, page)."""
import json
# 3V3 rail: TPS562201 VFB 749/768/787 mV (TI SLVSD91D p.5), R330 33.2k 1 % / R331 10k 1 % (schematic)
r_hi = 1 + 33.2 * 1.01 / (10 * 0.99); r_lo = 1 + 33.2 * 0.99 / (10 * 1.01); r_ty = 1 + 3.32
VDD = dict(min=0.749 * r_lo, typ=0.768 * r_ty, max=0.787 * r_hi)
# ESP32 GPIO: VOH >= 0.8 VDD (ESP32 DS v5.3 p.52, Table 5-3; IOH 40 mA at max drive strength) -> guaranteed bound.
# typical source resistance (not in the DS): (VDD - 0.8 VDD)/40 mA = 16.5 Ohm at max strength; 25 Ohm used for "typ" (ASM)
ROUT_TYP = 25.0
TC_R = 100e-6 * 60          # Royalohm 0402WGJ: 5 %, 100 ppm/K (Özdisan line text), 25 -> 85 C
OPT = {
    # name: IFT max (mA), T-factor at -20 C, at 85 C, VF max @25C (V), VF typ, VF temp coeff (V/K, from the typ curves), R4, IF abs max (mA), IF max @85C (mA)
    "0 MOC3053M + 200R (Rev1.2 design)": dict(ift=6, tf_cold=1.13, tf_hot=0.95, vfmax=1.50, vftyp=1.18, tcv=-1.4e-3, R=200, ifabs=60, if85=20.2 / 1.15,
        src="onsemi MOC3052M/D Rev4 p.3 (IFT 6 mA, VF 1.18/1.50 V @10 mA, IF 60 mA, emitter PD 100 mW -1.33 mW/K), p.5 Fig.1/3"),
    "1 MOC3052 (Isocom MOC3052X) + 120R (today)": dict(ift=10, tf_cold=1.13, tf_hot=0.95, vfmax=1.50, vftyp=1.20, tcv=-1.4e-3, R=120, ifabs=50, if85=27.6,
        src="Isocom DD93210 p.1 (IF 50 mA), p.2 (IFT 10 mA, VF 1.2/1.5 V @20 mA), p.3 Fig.1 (IF derating 50 mA to 50 C -> 18 mA at 100 C); "
            "no IFT-vs-T curve below 20 C -> onsemi MOC3052M Fig.3 used"),
    "1b MOC3052 + R4 for the 150 % rule": dict(ift=10, tf_cold=1.13, tf_hot=0.95, vfmax=1.50, vftyp=1.20, tcv=-1.4e-3, R=None, ifabs=50, if85=27.6, src="as 1"),
    "5 MOC3083M (onsemi) + 120R": dict(ift=5, tf_cold=1.26, tf_hot=0.93, vfmax=1.50, vftyp=1.30, tcv=-1.6e-3, R=120, ifabs=60, if85=35.4 / 1.15,
        src="onsemi MOC3083M/D p.3 (IF 60 mA, emitter PD 120 mW -1.41 mW/K), p.4 (IFT 5 mA, VF 1.3/1.5 V @30 mA), p.5 Fig.2/3"),
}

def run(o):
    vf_hi = o["vfmax"] + (-20 - 25) * o["tcv"]          # max VF at -20 C
    vf_lo = o["vftyp"] - 0.08 + (85 - 25) * o["tcv"]    # low VF at 85 C (typ curve - 0.08 V, ASM: no VF min published)
    need_onsemi = o["ift"] * o["tf_cold"] * 1.20        # onsemi MOC3052M p.6: IFT x T-factor x (1 + 20 % LED degradation)
    need_150 = o["ift"] * 1.5                           # onsemi MOC3052M p.4 note 2 / AN-3003 p.5: IF >= 1.5 x IFT max
    R = o["R"]
    if R is None:     # largest E24 that keeps IF_min (guaranteed GPIO bound) >= max(need_150, need_onsemi)
        need = max(need_150, need_onsemi) / 1e3
        R = (0.8 * VDD["min"] - vf_hi) / need / (1.05 + TC_R)
        E24 = [10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 43, 47, 51, 56, 62, 68, 75, 82, 91]
        R = max(e * 10 ** k for k in (0, 1, 2) for e in E24 if e * 10 ** k <= R)
    Rmax, Rmin = R * (1.05 + TC_R), R * (0.95 - TC_R)
    if_min_bound = (0.8 * VDD["min"] - vf_hi) / Rmax * 1e3             # guaranteed (DS bound)
    # typical-source estimate: VOH = VDD - I*Rout
    if_min_typ = (VDD["min"] - vf_hi) / (Rmax + ROUT_TYP) * 1e3
    if_typ = (VDD["typ"] - o["vftyp"]) / (R + ROUT_TYP) * 1e3
    if_max = (VDD["max"] - vf_lo) / Rmin * 1e3                          # GPIO at VDD (no drop)
    p_led_max = if_max * 1e-3 * (vf_lo + 0.15) * 1e3                    # mW, VF at that current ~ +0.15 V (ASM)
    p_r = (if_max * 1e-3) ** 2 * Rmin * 1e3
    return dict(R4=R, VDD=VDD, VF_max_m20=round(vf_hi, 3), VF_low_85=round(vf_lo, 3), need_150pct_mA=need_150, need_onsemi_method_mA=round(need_onsemi, 2),
                IF_min_guaranteed_mA=round(if_min_bound, 2), IF_min_typ_source_mA=round(if_min_typ, 2), IF_typ_mA=round(if_typ, 2), IF_max_mA=round(if_max, 2),
                ratio_min_guaranteed_to_IFTmax=round(if_min_bound / o["ift"], 2), ratio_min_typsource_to_IFTmax=round(if_min_typ / o["ift"], 2),
                IF_abs_max_mA=o["ifabs"], IF_max_at_85C_mA=round(o["if85"], 1), P_LED_max_mW=round(p_led_max, 1), P_R4_max_mW=round(p_r, 1), src=o["src"])

res = {k: run(o) for k, o in OPT.items()}
for k, v in res.items():
    print(k); print("   ", {a: b for a, b in v.items() if a not in ("src", "VDD")})
print("VDD", {k: round(v, 3) for k, v in VDD.items()})
json.dump(res, open("u5_led.json", "w"), indent=1)
