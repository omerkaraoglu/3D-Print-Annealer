# Scope A — mains-port emissions and low-frequency phenomena (simulation, 2026-11-18)

*Saved by the main session on 2026-11-18 at the owner's request, from the scope-A agent's hand-back texts (the harness blocks subagents from writing .md files). The cross-check in §9 was added after review. Every number is in `results.json`; the scripts regenerate them (`python -X utf8 <script>`).*

**This is a simulation, not an accredited measurement.** MARGINAL means less than 6 dB (or less than 20 %) of margin. Citations are to the owner's PDFs (PDF page numbers); **NOT READ** means the value is not in the owner's files and comes from the public source named.

## Verdicts (decided firmware)

| Test | Clause (PDF page) | Worst result | Limit | Margin | Verdict |
|---|---|---|---|---|---|
| A1 conducted, quasi-peak (QP) | EN 55014-1 4.3.3.2, Table 5 col. 2 (p. 34, 36) | 54.9 dBµV on N at 150 kHz nominal. Monte Carlo (120 runs, V_on 10–40 V): 5th percentile 2.8 dB, worst 0.0 dB | 66 dBµV | 11.2 dB nominal | **MARGINAL** |
| A1 conducted, average (AV) | Table 5 col. 3 | Monte Carlo worst margin 23.1 dB | 59→46 dBµV | 23 dB | PASS |
| A1, heater off (mode M3) | Table 5 | HLK-10M05 is a black box | — | — | NOT SIMULABLE (bound given) |
| A2 load-terminal | 4.3.3.3 b/d (p. 34) | internal port, not applicable | — | — | N/A |
| A3 clicks, triac | 4.4.2.2 (p. 39) | no clicks registered; continuous limits apply (= A1) | Table 5 | as A1 | PASS via A1 |
| A3 clicks, relay K1 | 4.4.2.3, 5.4.3.2 / 5.4.3.4 (p. 39, 50–51) | 0.24–3.3 ms, N = 0.017 per minute | exempt | — | PASS by exemption |
| A4 harmonics | IEC 61000-3-2 Table 1 / 6.2 + Table 3 (p. 137, 146–147) | 19.9 % of limit (h17, V_on 40 V) | 100 % | 80 % | PASS |
| A4 control method | 6.2 (p. 137) | zero-cross timing can drop half-cycles → half-wave (asymmetrical) control | prohibited above 100 W | — | RISK |
| A5 flicker | IEC 61000-3-3 clause 5 (NOT READ) | P_lt 0.532 | 0.65 | 18 % | **MARGINAL** |
| A5 d_c / d_max / T_max | same | 0.75 % / 0.79 % / 0 | 3.3 % / 4 % / 0.5 s | ≥ 76 % | PASS |

The current (sigma-delta) firmware fails A5 (P_st 1.687 at duty 0.80) and is MARGINAL on the 6.2 / Table 3 rule at duty 0.02 (96–97 % of limit; driven by the assumed HLK rectifier and the low measured power).

## Proposed changes (re-simulated, not applied)

- **F1 (firmware):** timestamp both /ZCD edges and fire at the window centre, with a gate pulse of at least 300 µs straddling the zero.
  - The triac then always turns on at its gate threshold, 8.7–17.7 V.
  - A1 Monte Carlo with V_on 8–18 V: worst margin 6.3 dB, 5th percentile 9.8 dB → A1 **PASS**.
  - At the all-worst corner the margin goes from −2.6 dB to +5.9 dB.
  - It also removes the half-cycle-loss risk.
- **F2 (firmware):** 1500-cycle burst frame instead of 1000. P_lt 0.532 → 0.467 (28 % margin) → A5 **PASS**.
- **Rejected:** extra X2 capacitance at the triac (100 nF or 220 nF from Q1.A2 to R1.2). It makes 0.7–1 MHz 7–11 dB worse, because the limit there is set by common mode.

## 0. Inputs

Values come from the current schematic (kicad-cli netlist export of a copy) and from `3dFilamentDryer.kicad_pcb`, parsed read-only (`design_inputs.json`). The committed `Rev3.0_netlist.net` is stale (discrepancy 1).

- **Topology:** J3.1 → F3 → LINE_FUSED → L40 100 µH → LINE_FILT, with C40 1 µF, C1 100 nF and RV1 across. LINE_FILT feeds Q1 A2 → A1 → heater R1 → NEUT. Snubber 47 Ω + 10 nF. K1 COM is on LINE_FUSED. PSU path: F1 → L1 CMC → HLK.
- **Routed branches:** F3→L40 11.9 mm; L40→K1 33.3 mm; L40.1→C40 15.4 mm; L40.1→Q1 47.6 mm; Q1.A1→R1 32.0 mm; C40.2→J3.2 72.5 mm; R1.2→J3.2 5.4 mm.

## 1. Test matrix

**Not applicable**
- EN 55014-1 4.3.2 / Tables 2–4 (p. 32–34): induction cooking only.
- 4.3.3.3 associated ports (p. 34): heater and fan are internal, non-extendable wiring.
- Table 6 (p. 35–36): tools only.

**Applicable**
- 4.3.3.2 + Table 5 col. 2/3 (p. 34, 36), mains L/N, QP 66→56 / 56 / 60 and AV 59→46 / 46 / 50 dBµV, in modes M1, M2, M3.
- 4.4 / 5.4 / Annex B–C clicks (p. 39, 49–52, 100–105).
- Operating conditions per clause 6 and A.4.1 / A.4.7 (p. 52–53, 80–81).
- Table 10 general margin for series production (p. 55): 3.8 / 2.5 / 1.5 / 0.7 dB for n = 3–6.
- 4.3.4 / Tables 7–9 (30–1000 MHz): scope C.
- IEC 61000-3-2: Class A (5.1, p. 135), 6.2 (p. 137–138), 6.3 (p. 138–141), Tables 1, 3, 4 (p. 146–147).
- IEC 61000-3-3: scope (p. 10), definitions 3.2–3.5 (p. 11); limits NOT READ.

**Found outside every scope:** the 6.2 asymmetrical-control prohibition (from A0).

## A0. Triac turn-on (zero-cross timing)

- **Why the ISR runs early:** the ISR triggers on the falling edge of /ZCD, which is the *start* of the zero-cross window (U6 inverts the opto signal), half a window before the zero.
- **Data used:** H11AA1 CTR ≥ 20 % (Vishay p. 2) with the Fig. 2/3 curves (p. 3); Schmitt threshold VT+ 1.5–2.2 V (sn74lvc1g14 p. 6); MOC3052 V_TM 2.5 V (onsemi p. 3); triac I_GT 10–35 mA and V_GT 1.3 V (BTA12-CW row, ST p. 3).
- **Results:** 22 of 40 parameter cases miss the zero (CTR at 10 mA ≤ 50 % at 25 °C, or ≤ 100 % at about 60 °C): the 150 µs pulse ends before the zero and the half-cycle is lost (DC 1.96 A, h2 at 86 % of the Class A limit). Otherwise the triac fires at 8.7–17.7 V.
- **Fix:** F1.

## A1. Conducted emission

- **Set-up**
  - LISN: 50 Ω ∥ (50 µH + 5 Ω). CISPR 16-1-2 is NOT READ; topology from the Schwarzbeck NSLK 8117 listing.
  - Mains cord: 1 m, coupled-inductor model.
  - Receiver: 9 kHz IF, QP 1 / 160 ms, meter 160 ms. CISPR 16-1-1 is NOT READ; constants from the Schwarzbeck note, p. 15.
- **Model**
  - Source substitution: the triac is replaced by its own voltage waveform.
  - A full parasitic AC network (both lines, differential and common mode) gives the transfer function.
  - Parameter table (value and source) is in `frontend.py` (NOMINAL / PARAMS_DOC).
- **Nominal results**
  - M1: QP 54.85 dBµV on N at 150 kHz, 11.2 dB margin; AV margin 36.4 dB.
  - M2: current firmware 38.5–54.7 dBµV; decided firmware 54.7 dBµV, never above M1.
  - Common mode sets the N line at 0.4–2 MHz (about 42 dBµV).
- **V_on sweep:** 10 / 20 / 30 / 40 V gives 17.3 / 11.2 / 7.6 / 5.1 dB margin.
- **Single-parameter corners:** chassis-to-plane capacitance C_ch = 150 pF gives 6.6 dB; all bad corners together give −2.6 dB.
- **Monte Carlo (V_on 10–40 V):** minimum 0.0 dB, 5th percentile 2.8, median 8.2; 38 of 120 runs below 6 dB → MARGINAL.
- **Monte Carlo with F1 (V_on 8–18 V):** minimum 6.3 dB, 5th percentile 9.8 → PASS.
- **HLK bound**
  - Board adds DM insertion loss vs the HLK reference circuit of +29.1 / +45.9 / −4.8 / +8.4 dB at 0.15 / 0.5 / 5 / 30 MHz; minimum −6.5 dB (1.2–15 MHz).
  - Common-mode extra insertion loss −6.4 to +33.5 dB.
  - HLK noise current that would just reach the QP limit, DM: 79.8 / 62.5 / 59.7 / 36.2 dBµA at 0.15 / 0.3 / 1 / 5 MHz; CM: 42.2 / 22.1 / 41.1 / 41.0 dBµA.
  - Mode M3 therefore needs the HLK to have at least 6.5 dB of its own margin, which only a measurement can show.
- **What the model cannot see:** the HLK itself; the real IF filter and meter; turn-on physics; mutual inductances; L40 self-resonance; the oven's capacitances.

Plots: `plots/A1_M1_nominal.png`, `A1_M1_all_worst_corners.png`, `A1_proposals.png`, `A1_monte_carlo.png`, `A1_validation_transient.png`, `A1_hlk_insertion_loss.png`.

## A2. Load terminals

Not applicable (4.3.3.3 b/d). For information only: the heater terminal reads 103.1 / 92.2 / 79.4 dBµV QP at 0.15 / 0.5 / 1.4 MHz against 80 / 74 dBµV. It would fail only if the controller were sold separately (A.10.2.2, p. 94).

## A3. Clicks

- **Triac:** at V_on 20 V the IF envelope stays 5.1 / 7.9 / 10.6 dB below the IF reference at 0.15 / 0.5 / 1.4 MHz. At 40 V it exceeds by 0.9 dB for 37 µs, but bursts are 10 ms apart, so they are "other than clicks" and the continuous limits (A1) apply.
- **K1 relay**
  - Single break event: 49.9–66.7 dBµV QP at 150 kHz, up to 110 dBµV at 1.4 MHz.
  - Duration 0.24–3.3 ms; click rate N = 0.017 per minute, so the click limit is L + 44 dB.
  - The 3 ms case would exceed that limit at 0.5–1.4 MHz, but this is not relied on: exemptions 5.4.3.2 and 5.4.3.4 apply → PASS.
  - Real arc statistics are not modelled; the arc model is a deterministic sawtooth. Fan and relay data are assumed.

Plot: `plots/A3_relay_click.png`.

## A4. Harmonics

- **Method:** IEC 61000-4-7 is NOT READ; harmonic groups and 1.5 s smoothing from IS 14700-4-7, 5.5.1, p. 19. T_obs 200 s.
- **Results**
  - 100 %: 3.6 % of limit (V_on 20 V), 20.5 % (V_on 40 V).
  - Current firmware: h2 group 74.9 %; Table 3 at duty 0.02 is 96–97 % (MARGINAL).
  - Decided firmware: ≤ 19.9 % (PASS).
  - Half-wave fault: h2 85.7 %, DC 1.96 A, prohibited by 6.2.

Plot: `plots/A4_harmonics.png`.

## A5. Flicker

- **Flickermeter re-validation:** rectangular test points within +2.84 %; sine mean 1.0002.
- **Heater step:** ΔU 0.752 %.
- **Current firmware:** P_st 1.687 → FAIL.
- **Decided, 1000 cycles:** 0.532 → MARGINAL on P_lt. **1500 cycles:** 0.467 → PASS. **2000 cycles:** 0.422.
- **Single events:** cold heater 0.789 %; HLK inrush 0.642 % (21.6 A peak); fan 0.074 %; T_max 0 → PASS.
- **Not in the preview file:** limits and Z_ref, NOT READ; source is the Keysight note 5964-1917E and the 2026-11-12 assessment.

Plot: `plots/A5_flicker_pst_vs_duty.png`.

## 6. Discrepancies with the old assessment and the spec

1. **Stale netlist.** `Rev3.0_netlist.net` (2026-11-12) still has K1 on LINE_FILT, MOC3053, R4 = 200 Ω and L12 = 2.2 µH.
2. **Fan relay is now unfiltered.** K1 is on LINE_FUSED, so its arcs reach the LISN with no filter. The old F6 and spec 12.5 still say it sits behind the filter.
3. **Firing time.** The old report assumed the triac fires 230 µs after the zero crossing (23 V). In fact /ZCD falls at the start of the zero-cross window, so V_on is the gate threshold — or the half-cycle is lost (A0).
4. **AV limit.** The old report used 56→46 dBµV; Table 5 says 59→46 (the old report was conservative).
5. **Harmonics method.** With IEC 61000-4-7 grouping the sigma-delta pattern's interharmonics put h2 at 75 % of the Class A limit, and 6.2 requires the Table 3 check for the heater. The old F5 said neither applied.
6. **Flicker margin.** The old report called the decided frame a pass with 17 % margin; under this campaign's 20 % rule it is MARGINAL.
7. **Associated-port threshold.** The old report used 3 m; the standard uses 2 m non-extendable, and internal ports are exempt.
8. **Common mode missing.** The old one-pulse model had no common mode, but common mode sets the N line from 0.4 to 2 MHz.
9. **X-capacitor return path.** C40 and C1 return over 72.5 mm of NEUT, while the heater returns to J3.2 in 5.4 mm.

## 7. Assumptions that drive the verdicts

- **Triac turn-on voltage V_on.** Spearman correlation with the A1 margin −0.87; each 10 V costs about 3 dB.
- **Heater→chassis and chassis→reference-plane capacitances (C_hc, C_ch).** Assumed 300 pF and 50 pF; they depend on how the oven is built.
- **HLK-10M05 input stage.** Assumed 10 Ω and 10 µF; sets the Table 3 result for the current firmware.
- **Fan and relay data.** All assumed.
- **Flicker limits and Z_ref.** Not readable from the 61000-3-3 preview.

## 8. Validation

- LC filter: SPICE against the analytic case, within 0.27 dB.
- Receiver: the 0.158 µVs / 100 Hz calibration pulse reads 60.55 dBµV QP; QP−PK and QP−AV within 0.7 dB of the reference values.
- Method check: the full nonlinear transient matches the source-substitution result within 0.35–0.6 dB up to 2 MHz.
- Unfiltered (pass-1/2) topology: 93.6 dBµV, against 93 in the old report.
- Flickermeter: rectangular test points within 2.8 %.

## 9. Cross-check of the scope-B proposals (added after review)

None of scope B's parts costs measurable conducted-emission margin (≤ 0.3 dB), apart from Y1, which gains up to 2.6 dB on N. Results in `results.json` sections `A1_crosscheck_scopeB`, `A1_F1_construction_grid`, `A0_zcd_timing_E1`; script `crosscheck_B.py`.

**Model changes for this run**
- Chassis-to-SELV capacitance C_cs (thermocouple probe and lead): 20 pF nominal, 5–100 pF in the Monte Carlo, plus a "probe bonded to the chassis" case at 10 nF.
- Core loss in L1 (10 mH common-mode choke): 15 kΩ in parallel per winding (5–50 kΩ in the Monte Carlo). A first run with a lossless L1 resonated with the HLK barrier capacitance at about 265 kHz and was discarded.
- Baseline unchanged: 11.14 dB QP on N at 150 kHz (11.15 dB before).
- P-D1 (Y1) sits from SELV GND to the L1.1 neutral node (5 nH ESL); P-S2b (second varistor) from L40.2 to the C40.2 neutral node (15 nH).

**Nominal (worst QP margin, dB)**

| | As designed, V_on 20 V | F1, V_on 15 V |
|---|---|---|
| Baseline | L 11.69; N 11.14 (0.15 MHz) | L 14.18; N 13.64 |
| P-D1 Y1 1 nF | L 11.67; N 11.16 | L 14.16; N 13.66 |
| P-D1 470 pF / 2.2 nF | N 11.16 / 11.16 | N 13.65 / 13.66 |
| P-S2b | L 11.54; N 11.01 | L 14.03; N 13.51 |
| P-D1 + P-S2b | L 11.52; N 11.03 | L 14.01; N 13.52 |
| Probe bonded, no Y1 | N 10.08 (0.65 MHz) | N 12.57 (0.67 MHz) |
| Probe bonded + Y1 1 nF | N 11.32 | N 13.81 |

**All-worst corner (QP on N)**

| | As designed, V_on 40 V | F1, V_on 18 V |
|---|---|---|
| Baseline | −3.10 (0.997 MHz) | 3.84 |
| P-D1 | −2.53 | 4.40 |
| P-S2b | −3.11 (0.793 MHz) | 3.83 |
| P-D1 + P-S2b | −2.56 | 4.37 |

**Monte Carlo (120 paired draws; QP minimum / 5th percentile / median, dB)**

| Variant | V_on 10–40 V, N line | F1, N line |
|---|---|---|
| Baseline | −0.2 / 2.7 / 8.6 (33 runs below 6 dB) | 6.3 / 8.9 / 13.9 (0 below 6 dB) |
| P-D1 | 0.2 / 2.9 / 8.8 (23 below) | 7.1 / 9.6 / 14.4 |
| P-S2b | −0.4 / 2.5 / 8.4 (33 below) | 6.4 / 8.8 / 13.7 |
| Both | 0.1 / 2.8 / 8.7 (25 below) | 7.0 / 9.5 / 14.3 |

AV minimum ≥ 22.6 dB in every as-designed case and ≥ 28.7 dB in every F1 case.

**SELV ground noise that just reaches the mains limit through Y1** (open-circuit SELV-GND-to-reference-plane voltage, dBµV, AV / QP; ideal source = pessimistic)

| f (MHz) | No Y1 (HLK 50 pF only) | Y1 470 pF | Y1 1 nF | Y1 2.2 nF |
|---|---|---|---|---|
| 0.15 | 113.4 / 120.4 | 96.0 / 103.0 | 90.0 / 97.0 | 83.2 / 90.2 |
| 0.3 | 98.5 / 107.2 | 79.6 / 88.3 | 73.3 / 82.0 | 66.3 / 75.0 |
| 0.58 (buck) | 89.1 / 99.1 | 67.1 / 77.1 | 60.6 / 70.6 | 53.7 / 63.7 |
| 1.2 (boost) | 85.1 / 95.1 | 60.3 / 70.3 | 54.0 / 64.0 | 48.7 / 58.7 |
| 2.4 | 80.0 / 90.0 | 54.4 / 64.4 | 49.2 / 59.2 | 46.6 / 56.6 |
| 3.6 | 78.0 / 88.0 | 51.2 / 61.2 | 47.3 / 57.3 | 46.3 / 56.3 |
| 5 | 74.8 / 84.8 | 48.7 / 58.7 | 46.7 / 56.7 | 46.9 / 56.9 |
| 10 | 70.3 / 80.3 | 56.3 / 66.3 | 57.2 / 67.2 | 57.7 / 67.7 |
| 20 | 77.3 / 87.3 | 64.0 / 74.0 | 64.9 / 74.9 | 65.6 / 75.6 |
| 30 | 86.0 / 96.0 | 69.2 / 79.2 | 69.3 / 79.3 | 69.4 / 79.4 |

With Y1 1 nF, SELV ground noise above about 47 dBµV (220 µV) at 2.5–5 MHz, or 54 dBµV at 1.2 MHz, fails the AV limit; without Y1 the thresholds are 25–35 dB higher.

**P-E1 (1 nF on the zero-cross collector):** the window-start edge comes 6.1–11.0 µs later; the zcd_timing conclusions and F1 are unchanged (window centre moves ≤ 11 µs ≙ ≤ 1.1 V).

**F1 timing versus oven construction** — QP margin (dB) at V_on 18 V, worst of L and N. C_hc = heater to chassis, C_ch = chassis to reference plane. Plot: `plots/A1_F1_construction_grid.png`.

| C_hc \ C_ch | 20 pF | 50 pF | 100 pF | 150 pF | 220 pF | 300 pF |
|---|---|---|---|---|---|---|
| **Other parameters nominal** | | | | | | |
| 100 pF | 12.3 | 12.2 | 12.0 | 11.8 | 10.7 | 10.0 |
| 220 pF | 12.2 | 12.1 | 10.3 | 8.3 | 6.6 | 5.4 |
| 470 pF | 12.2 | 12.0 | 8.6 | 6.0 | 3.8 | 2.1 |
| 1000 pF | 12.2 | 12.0 | 7.6 | 4.8 | 2.1 | 0.0 |
| **Other parameters at their bad ends** | | | | | | |
| 100 pF | 11.0 | 10.9 | 10.7 | 10.7 | 9.8 | 9.1 |
| 220 pF | 11.0 | 10.8 | 9.3 | 7.4 | 5.7 | 4.5 |
| 470 pF | 11.0 | 10.8 | 7.6 | 5.1 | 2.9 | 1.2 |
| 1000 pF | 11.0 | 10.7 | 6.7 | 3.8 | 1.2 | −0.9 |

F1 alone keeps ≥ 6 dB for: any heater capacitance up to 1 nF with the chassis ≤ 50 pF to the plane; heater ≤ 220 pF with the chassis ≤ 150 pF; heater ≤ 100 pF at any chassis capacitance up to 300 pF. Outside that range the oven needs a mechanical or common-mode measure (Y1 gains at most 2.6 dB).

## 10. What could not be done

- HLK and converter emission (black box; bound given in A1).
- CISPR 16-1-1/-1-2, IEC 61000-4-7, IEC 61000-4-15 and IEC 61000-3-3 clause 5 / 6.4 are not in the owner's folder (NOT READ; public sources: Schwarzbeck receiver note, Schwarzbeck LISN listing, IS 14700-4-7, Keysight 5964-1917E).
- L40: no self-resonance figure found; swept instead.
- Relay arcs: real arc statistics are not modelled.

## 11. Files

`Design Reports/Rev3.0/sim/emc_tests/A_mains_emission/`
- Scripts: `design_inputs.py`, `common.py`, `receiver.py`, `frontend.py`, `emission_core.py`, `conducted.py` (`--mc 120`), `tran_validation.py`, `zcd_timing.py`, `clicks.py`, `harmonics.py`, `flicker.py`, `patterns.py`, `crosscheck_B.py`
- Data: `design_inputs.json`, `results.json` (A0_zcd_timing, A1_conducted with A2 inside, A3_clicks, A4_harmonics, A5_flicker, A1_crosscheck_scopeB, A1_F1_construction_grid, A0_zcd_timing_E1), `tran_validation.json`
- Plots: `plots/*.png`
