"""U5 = Isocom MOC3083X with R4 = 120 R 0603 (Royalohm 0603SAJ0121T5E, 5 %, 100 ppm/K, 1/10 W): LED drive and firing analysis.
Sources: Isocom DE93284 (20/08/2026) p.1 abs max, p.2 recommended IF 7.5/10/30 mA, p.3 VF 1.2/1.4 V @ 20 mA, IFT 5 mA, IH 200 uA,
VTM 3.0 V @ 100 mA, IDRM 500 nA, dv/dt 1000 V/us; p.4 VINH 5 typ / 20 max V, IDRM2 500 uA; p.5 Fig.1 IF derating (29 mA at 85 C),
Fig.3 IFT x1.45 at -20 C / x0.97 at 85 C, Fig.4 IH x1.6 at -20 C; p.6 Fig.9 VF(T).
ESP32 DS v5.3 p.52 VOH >= 0.8 VDD; TPS562201 p.5 VFB 749/768/787 mV; ST BTA24 DS2112 Rev12 p.2 IGT 35 mA, VGT 1.3 V, VGD 0.2 V,
IL 70/80 mA, Fig.8 p.5 IGT x1.75 / IL x1.4 at -20 C."""
import math
VDD = dict(min=0.749 * (1 + 33.2 * 0.99 / 10.1), typ=0.768 * 4.32, max=0.787 * (1 + 33.2 * 1.01 / 9.9))
R = 120.0; tolp = 0.05 + 100e-6 * 60; Rmax, Rmin = R * (1 + tolp), R * (1 - tolp)
IFT, kc, kh = 5.0, 1.45, 0.97
VF_hi = 1.40 + 45 * 1.7e-3          # max VF (20 mA, 25 C) moved to -20 C with Fig.9's -1.7 mV/K
VF_lo = 1.10                        # 85 C, ~20 mA: Fig.9 typical 1.18 V minus 0.08 V (no VF min published)
VF_ty = 1.20
ROUT = 25.0                          # typical GPIO source resistance (ASSUMED; ESP gives only the 0.8 VDD bound)
ifmin_g = (0.8 * VDD["min"] - VF_hi) / Rmax * 1e3
ifmin_r = (VDD["min"] - VF_hi) / (Rmax + ROUT) * 1e3
iftyp = (VDD["typ"] - VF_ty) / (R + ROUT) * 1e3
ifmax = (VDD["max"] - VF_lo) / Rmin * 1e3
need_aged = IFT * kc * 1.2
print("VDD %.3f/%.3f/%.3f V" % (VDD["min"], VDD["typ"], VDD["max"]))
print("IF min guaranteed %.1f mA, realistic min %.1f, typ %.1f, max %.1f mA" % (ifmin_g, ifmin_r, iftyp, ifmax))
print("ratio to IFT max (25 C): %.2f / %.2f; to IFT cold (-20 C, x1.45 = %.2f mA): %.2f / %.2f; cold + 20 %% ageing (%.2f mA): %.2f / %.2f"
      % (ifmin_g / IFT, ifmin_r / IFT, IFT * kc, ifmin_g / (IFT * kc), ifmin_r / (IFT * kc), need_aged, ifmin_g / need_aged, ifmin_r / need_aged))
print("Isocom recommended IF 7.5 min / 10 typ / 30 max mA; IF allowed at 85 C (Fig.1) ~29 mA")
p_r = (ifmax / 1e3) ** 2 * Rmin * 1e3
print("R4 power max %.0f mW continuous (0603 1/10 W, derated to ~82 mW at 85 C: %.0f %%); LED power max %.0f mW"
      % (p_r, p_r / 82 * 100, ifmax * (VF_lo + 0.15)))
# firing analysis
R3, R2, RH = 360.0, 360.0, 52.9
VTM, VGT = 3.0, 1.3
for T, kg in (("25 C", 1.0), ("-20 C", 1.75), ("85 C", 0.6)):
    ig = 35e-3 * kg
    i3 = ig + VGT / R2
    v = i3 * (R3 + RH) + VTM + VGT
    for vpk, lab in ((230 * math.sqrt(2), "230 V"), (207 * math.sqrt(2), "207 V")):
        t = math.asin(v / vpk) / (2 * math.pi * 50) * 1e6
        print("Q1 fires (%s, IGT max x%.2f): I(R3) %.1f mA at |v| = %.1f V -> %.0f us after the zero crossing at %s" % (T, kg, i3 * 1e3, v, t, lab))
ih_cold = 200e-6 * 1.6
v_hold = 1.0 + ih_cold * (R3 + RH)
print("driver held from |v| = %.2f V (VTM onset ~1.0 V, Fig.6, + IH %.0f uA x %.0f Ohm) = %.0f us after the zero crossing"
      % (v_hold, ih_cold * 1e6, R3 + RH, math.asin(v_hold / 325.3) / (2 * math.pi * 50) * 1e6))
for lab, idrm2 in (("Isocom MOC3083X IDRM2 500 uA", 500e-6), ("onsemi MOC3083M IDRM2 2 mA", 2e-3)):
    print("%s x R2 360 = %.2f V against VGD 0.2 V; R2 for VGD/2: %.0f Ohm" % (lab, idrm2 * R2, 0.1 / idrm2))
