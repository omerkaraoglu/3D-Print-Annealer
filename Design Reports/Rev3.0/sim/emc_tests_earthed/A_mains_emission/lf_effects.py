"""Earthed case: which scope-A results change besides conducted emission (no simulation re-run needed), plus the
fix's power loss and the earth-leakage budget. Writes results.json section 'lf_clicks_leakage'."""
import math
from ecommon import save

I_rms = 1000.0 / 230.0
out = {
    "A3_clicks_K1": "Unchanged verdict. Earthing adds the fan-frame capacitance (50-300 pF) as a CM path for the contact-arc "
                    "transients, so click amplitudes can rise; the verdict rests on 5.4.3.2 / 5.4.3.4 (EN 55014-1 PDF p. 50-51), "
                    "which do not depend on amplitude (N 0.017/min, clicks <= 3.3 ms). Not re-run.",
    "A3_clicks_triac": "Changes only through A1: without a fix the earthed CM level exceeds the IF reference level, so each "
                       "firing burst is a 'disturbance other than clicks' (4.4.2.2) and the continuous limit applies - i.e. the A1 FAIL. "
                       "With the fix + F1 the envelope is below the limit (A1 margin >= 8.7 dB), no clicks registered.",
    "A4_harmonics": "Unchanged: 50 Hz-2 kHz currents are set by the heater, HLK and fan; the chassis earth carries only "
                    "capacitive leakage (< 0.1 mA). The proposed 200 uH A1-lead inductor shifts the heater current by "
                    f"{math.degrees(math.atan(2*math.pi*50*200e-6/52.9)):.3f} deg at 50 Hz and lengthens the turn-on rise "
                    f"(L/R = {200e-6/52.9*1e6:.1f} us) - negligible against the 20.5 % worst harmonic. Not re-run.",
    "A5_flicker": f"Unchanged: earthing does not change the L-N current steps. The fix adds 2 x 0.1 ohm in series "
                  f"(dU change {100*0.2*I_rms/230:.3f} % of U) - negligible. Not re-run.",
    "fix_power_loss_W": round(2 * 0.10 * I_rms ** 2, 2),
    "fix_power_note": "2 x RC1415U-101K (0.10 ohm each, spec 12.5 / BOM) at 4.35 A rms -> ~1.9 W each, the same as L40; place them away from HS1 and C40",
    "leakage_current": {
        "limit": "class I portable appliance 0.75 mA - IEC 60335-1 clause 13/16 NOT READ FROM THE STANDARD; public source: Bel Fuse / CUI blog 'IEC 60335-1 explained' (0.75 mA portable, 3.5 mA stationary)",
        "heater_C_hc_1nF_uA": round(1e6 * 2 * math.pi * 50 * 1e-9 * 230 / 2, 1),
        "fan_frame_300pF_uA": round(1e6 * 2 * math.pi * 50 * 300e-12 * 230 / 2, 1),
        "Y_cap_budget_note": "Y capacitors are NOT part of the chosen fix. Had they been used: 2.2 nF L-PE at 1.06 x 230 V -> "
                             f"{1e3*2*math.pi*50*2.2e-9*244:.2f} mA, 4.7 nF -> {1e3*2*math.pi*50*4.7e-9*244:.2f} mA (budget 0.75 mA minus heater insulation leakage)",
    },
}
save("lf_clicks_leakage", out)
print(out)
