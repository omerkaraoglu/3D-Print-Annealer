"""When does the triac actually turn on? Zero-cross detector -> ISR -> MOC3052 -> BTA24 timing.

Circuit (current schematic): PS1-AC/L,N -> R6, R7 33 k -> H11AA1 (U1) LEDs; U1 collector -> R8 10 k to 3V3 and
U6 (74xx1G14 Schmitt inverter) -> R9 -> /ZCD (IO34). Firmware: attachInterrupt(ZCD_PIN, zcd_isr, FALLING)
(AnnealerFirmware.ino.ino line 1737), ISR: delayMicroseconds(230), TRIG high 150 us (lines 790-793).
Near the zero crossing the LED current falls, the phototransistor turns OFF, the collector rises, the inverter
output FALLS -> the ISR runs at the START of the zero-cross window, i.e. BEFORE the zero crossing, by the
half-window width Delta (not at the zero crossing as the 2026-11-12 report assumed).

Data: H11AA1 CTR >= 20 % at IF 10 mA (Vishay 83608 p. 2), normalised CTR vs IF Fig. 2 and vs temperature Fig. 3
(p. 3; digitised here, extrapolated below 1 mA with the 1-2 mA slope), VF Fig. 1. LVC1G14 VT+ 1.5-1.87 V at 3 V
(sn74lvc1g14.pdf p. 6; the BOM part is SN74AHC1G14, assumed similar, 1.5-2.2 V used). MOC3052: VTM 2.5 V max at
100 mA, IH 540 uA (onsemi p. 3). BTA24-800CW: IGT <= 35 mA, VGT <= 1.3 V (BTA12-CW row, ST p. 3; BTA24 via spec 7.1).
Phototransistor turn-off delay with 10 k and ISR latency: assumed.
"""
import math, json
import numpy as np
from common import save_results

VPK = 325.27; W = 2 * math.pi * 50
R_LED = 66e3
NCTR = [(0.25, 0.27), (0.5, 0.37), (1.0, 0.50), (2.0, 0.68), (5.0, 0.90), (10.0, 1.0)]   # (mA, normalised), Fig. 2 (<1 mA extrapolated)


def nctr(if_ma):
    x = np.log([p[0] for p in NCTR]); y = np.log([p[1] for p in NCTR])
    return float(np.exp(np.interp(np.log(max(if_ma, 0.05)), x, y, left=y[0] + (np.log(max(if_ma, 0.05)) - x[0]) * (y[1] - y[0]) / (x[1] - x[0]))))


def threshold_voltage(ctr10, vt_plus=1.75, temp_factor=1.0, vf=1.05):
    """|v_line| at which the phototransistor can no longer hold the collector below VT+ (window edge)."""
    ic_need = (3.3 - vt_plus) / 10e3 * 1e3      # mA
    lo, hi = 0.01, 5.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if m * ctr10 * nctr(m) * temp_factor >= ic_need:
            hi = m
        else:
            lo = m
    return vf + hi * 1e-3 * R_LED, hi


def gate_threshold(igt=0.035, vgt=1.3, vtm=2.5, r3=360.0, r2=360.0):
    return r3 * (igt + vgt / r2) + vtm + vgt


def case(ctr10, vt_plus, temp_factor, t_photo, t_isr, igt):
    vth, ifth = threshold_voltage(ctr10, vt_plus, temp_factor)
    delta = math.asin(min(vth / VPK, 1)) / W
    t_f = -delta + t_photo + t_isr + 230e-6          # gate pulse start relative to the zero crossing
    t_e = t_f + 150e-6
    vg = gate_threshold(igt)
    t_latch = math.asin(3.5 / VPK) / W               # MOC conducts > IH once |v| > ~3.5 V
    if t_e < 0:
        outcome = "MISSED: pulse ends before the zero crossing (fires the previous half-cycle tail, new half-cycle lost)"
        von = abs(VPK * math.sin(W * t_f))
    elif t_e < t_latch:
        outcome = "UNCERTAIN: pulse ends before the MOC can latch"
        von = float("nan")
    else:
        v_start = VPK * math.sin(W * max(t_f, 0))
        von = max(vg, v_start)
        outcome = "fires at gate threshold" if v_start < vg else "fires late (pulse starts after threshold)"
    return {"ctr10_pct": 100 * ctr10, "VT+": vt_plus, "T_factor": temp_factor, "window_threshold_V": round(vth, 1),
            "half_window_us": round(delta * 1e6, 0), "pulse_start_us_rel_zero": round(t_f * 1e6, 0),
            "pulse_end_us": round(t_e * 1e6, 0), "gate_threshold_V": round(vg, 1), "V_on_V": round(von, 1) if von == von else None,
            "outcome": outcome}


def e1_delay(vt_plus, c=1e-9, r=10e3):
    """scope-B P-E1: 1 nF on the collector node; the rising (window-start) edge becomes an RC rise through R8."""
    return r * c * math.log(3.3 / (3.3 - vt_plus))


def run(e1=False):
    rows = []
    for ctr10 in (0.20, 0.35, 0.5, 1.0, 2.0):
        for vt in (1.5, 2.2):
            for tf in (1.0, 0.75):           # 25 C, ~60 C (Fig. 3, IF ~1 mA: 0.36/0.48)
                for igt in (0.010, 0.035):
                    rows.append(case(ctr10, vt, tf, 20e-6 + (e1_delay(vt) if e1 else 0.0), 3e-6, igt))
    return rows


def main():
    rows = run(False)
    rows_e1 = run(True)
    miss_e1 = [r for r in rows_e1 if r["outcome"].startswith("MISSED")]
    von_e1 = [r["V_on_V"] for r in rows_e1 if r["V_on_V"] is not None and not r["outcome"].startswith("MISSED")]
    changed = [(a["ctr10_pct"], a["VT+"], a["T_factor"], a["outcome"][:9], b["outcome"][:9]) for a, b in zip(rows, rows_e1) if a["outcome"][:9] != b["outcome"][:9]]
    save_results("A0_zcd_timing_E1", {
        "E1_edge_delay_us": {"VT+=1.5V": round(1e6 * e1_delay(1.5), 1), "VT+=2.2V": round(1e6 * e1_delay(2.2), 1)},
        "n_cases": len(rows_e1), "n_missed": len(miss_e1), "n_missed_without_E1": sum(r["outcome"].startswith("MISSED") for r in rows),
        "V_on_range_when_firing_V": [min(von_e1), max(von_e1)], "outcome_changes": changed, "rows": rows_e1,
        "F1_effect": ("F1 takes the zero as the centre of the measured window; E1 delays the start edge by 6-11 us and the end edge "
                      "by a similar RC/phototransistor-limited amount, so the centre estimate moves by <= 11 us: |v| at the zero "
                      "estimate <= 325 V * 2 pi 50 * 11 us = 1.1 V, far below the 8.7-17.7 V gate threshold -> F1 unchanged")})
    miss = [r for r in rows if r["outcome"].startswith("MISSED")]
    von = [r["V_on_V"] for r in rows if r["V_on_V"] is not None and not r["outcome"].startswith("MISSED")]
    out = {"rows": rows, "n_cases": len(rows), "n_missed": len(miss),
           "missed_if_ctr10_pct_le": max([r["ctr10_pct"] for r in miss], default=None),
           "V_on_range_when_firing_V": [min(von), max(von)],
           "assumptions": "phototransistor turn-off delay 20 us, ISR latency 3 us (Wi-Fi can add more), MOC latch at |v| > 3.5 V",
           "finding": "ISR runs at the START of the zero-cross window; with low-CTR H11AA1 parts (datasheet minimum 20 % at 10 mA) and/or high temperature the 150 us gate pulse ends before the zero crossing and the half-cycle is lost (DC / even harmonics, IEC 61000-3-2 6.2) - see report"}
    save_results("A0_zcd_timing", out)
    for r in rows:
        print(r)
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
