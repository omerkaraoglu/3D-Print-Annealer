# Scope C — RF: radiated emission 30–1000 MHz, injected and radiated RF immunity, layout/PDN audit

*Saved by the main session on 2026-11-18 at the owner's request, from the scope-C agent's hand-back texts (the harness blocks subagents from writing .md files). The radiated-emission results are the agent's second issue: the first model (ideal sources on a lossless structure) radiated more power than the drivers can supply, failed the reviewer's energy check and was withdrawn. All fields below are rms.*

**This is a model, not a measurement.** Common-mode results carry about ±10 dB. Every number is in `results.json`.

## Verdict table (as designed; FAR 3 m method)

Emission values are nominal at Q 10, then [Q 3 … Q 30 with the cable/barrier envelope].

| Test | Clause / table (PDF p.) | Worst result | Limit | Margin (nominal / upper) | Verdict | Dominant mechanism |
|---|---|---|---|---|---|---|
| Radiated, PCLK (33.3 MHz harmonics, always present) | EN 55014-1 4.3.4.2 b), Table 9 (p.37–38) | 77.8 dBµV/m @233.1 MHz [75.3 … 78.5] | 42.0 | −35.8 / −36.5 | **FAIL** | FPC return → panel/PCB common mode |
| same, worst upper row | Table 9 | 76.5 @366.3 MHz [… 80.4] | 42.0 | −34.5 / −38.4 | **FAIL** | same |
| Radiated, typical UI data | Table 9 | 62.3 @383.0 MHz [59.7 … 62.8] | 42.0 | −20.3 / −20.8 | **FAIL** | same |
| Radiated, worst pattern (1-px stripes) | Table 9 | 89.4 @216.5 MHz [87.5 … 91.9] | 35.2 | −54.2 / −56.7 | **FAIL** | same |
| Radiated, SAC 10 m | Table 9 | PCLK −35.2 / −35.7; typical UI −18.9 / −19.3 | 30/37 | — | FAIL | same |
| Disturbance power (indicative only) | 4.3.4.4 Table 7 (p.37) | PCLK −7.7 dB @166.5 MHz; worst pattern −31.3 dB | — | — | FAIL | mains-cord CM current |
| 8080 bus / buck / boost / crystal (board DM) | Table 9 | — | — | about +30 / +50 / +46 / +66 dB (rms-corrected) | PASS | DM loops |
| Injected RF, mains port 3 V | EN 55014-2 5.4 Table 10 (p.20), 7.2.4 | TC shift ≤ 0.06 °C (bound), 0.0006 °C (realistic) | 0.5 °C (proposed) | ≥ 18 dB | PASS | CM via HLK barrier |
| Injected RF, TC lead 1 V | Table 8 (p.19) | bound 2.3–10 °C, realistic ≤ 0.1 °C | — | — | N/A (1 m internal lead), computed anyway | 150 kHz CM |
| Injected RF, ZCD node | Table 10 | 0.19 V pk at U6 input (0.9–1.8 mV with the 1 nF of P-E1) | ~1 V (assumed) | 14 dB | PASS | opto barrier capacitance |
| Radiated RF 3 V/m, thermocouple | 5.5 Table 11 (p.20) | ≤ 0.003 mV at ADC, ≈ 0 °C | 0.5 °C | ample | PASS | RC filter + TVS capacitance |
| Radiated RF 3 V/m, display inputs | Table 11 | 1.57 V pk CM @840 MHz at Q 10 [1.12 … 1.64] | ~0.99 V logic margin | −4 dB | **FAIL risk** | same panel/PCB structure |
| Touch (GT911) | Table 11 | — | — | — | NOT SIMULABLE | — |

The 0.5 °C criterion-A tolerance is proposed by the agent, **for the owner to confirm**.

## 1. Applicability (standards read from the owner's files; PDF pages)

- The appliance contains electronics, so radiated emission 30–1000 MHz applies (EN 55014-1 4.3.4.1, p.36).
- Clocks above 30 MHz (PCLK 33.3 MHz on the board) mean disturbance power alone is not enough. Method a) (Table 7, plus radiated 300–1000 MHz) or method b) (Table 9 only) may be chosen (4.3.4.2, p.37). Recommended: b).
- Table 9 (p.38): FAR 3 m, 42→35 dBµV/m QP (30–230 MHz), 42 dBµV/m above; SAC 10 m, 30/37 dBµV/m.
- The 80/80 rule does not apply (Annex ZZ, p.8–9).
- Wi-Fi intentional and related spurious emissions are excluded (Scope, p.23). Test with Wi-Fi off where possible (6.5, p.53).
- Set-up per 5.3.4.3 (p.47–48). Operating modes per clause 6 / Annex A.4.1 (p.52, 80): heater in steady state, UI active, plus a worst-content check.
- Immunity: category IV (EN 55014-2 4.5, p.16). Injected 0.15–80 MHz (5.4: Table 10 3 V mains; Table 8 1 V only for cables that can exceed 3 m, p.19–20). RF field 80–1000 MHz, 3 V/m, 80 % AM (Table 11, p.20). Criterion A (7.2.4, p.23; clause 6, p.21).
- **Not read from the standards:** CISPR 16 (detectors, clamp, CMAD), IEC 61000-4-3/-4-6 set-ups (public descriptions used). RED requirements for the radio (EN 300 328, EN 301 489-17, EN 62311) are in nobody's scope.

## 2. Models and validation

- Layout extracted by script from the current board (md5 82cfd261): In1/In2 fills rasterised at 0.05 mm, 578 vias.
- 2D partial-inductance solver: two-wire line within 0.5 %, microstrip within 6.8 % of Hammerstad.
- SPICE chains (per-line lengths, LC-ladder lines): trapezoid harmonics within 1e-4 dB; 12-period vs 40-period runs within 0.02 dB. Driver open-circuit harmonic voltages stored per line.
- Thin-wire MoM of PCB, panel, FPC and cables: half-wave dipole 84.7 + j44.7 Ω (converged); short-dipole field −0.66 dB vs Hertzian; image +6.02 dB. Energy check: radiated power from a far-field sphere integral equals delivered power minus resistive-load power to within 0.1 % (`mom_energy_check`).
- Two-way coupling between the display lines and the common-mode structure: the drivers, RN and lines load the structure through a passive admittance from a separate SPICE AC run (`c4c_ydist.py`).
- Cavity-model PDN; ngspice AC common-mode network for injection; plane-wave MoM for the field test.

**Structural assumptions**
- Panel metal frame connected to panel GND: **assumed**. The SAT070AT40D21 pin table (datasheet p.5) only lists GND pins 3, 29 and 36. The floating-frame case is computed below.
- PCB-to-panel spacing: 5 mm spacer (spec 12.8); the model uses 6.4 mm from In1 to the panel back.
- FPC tail 67.65 mm (spec 12.9) plus 20 mm of panel-internal routing (assumed).
- FPC return conductors: 3 GND pins (3, 29, 36) plus VDD (pin 4).
- SSD1963 output resistance 30 Ω and edge 1.5 ns (not in its datasheet); panel input 5 pF.
- Probe: TC1 = WRNT-02, M6 ring tip, 1 m lead; grounded and insulated (20 pF) junction both modelled.

## 3. Radiated emission

### Mechanism

The 7" panel's FPC carries the return current of 28 fast lines on 3 ground pins. The voltage across that return drives the panel metal against the PCB ground; the pair forms a resonant structure (mode at 182 MHz) and the attached cables radiate the common-mode current.

### Power balance (nominal cables, Q 10)

Available power = N·|V_oc|²/(8·(30 + 33) Ω). Every ratio of delivered to available power is ≤ 1 (worst −1.5 dB at Q 10, −1.15 dB lossless; the withdrawn model was +11.9 dB).

| Source | f (MHz) | Available (µW) | Delivered (µW) | Ratio (dB) |
|---|---|---|---|---|
| 24 data lines | 83.25 | 7984 | 135 | −17.7 |
| | 116.6 | 3875 | 177 | −13.4 |
| | 149.9 | 2191 | 101 | −13.4 |
| | 183.2 | 1346 | 125 | −10.3 |
| | 216.5 | 868 | 97 | −9.5 |
| | 249.8 | 575 | 257 | −3.5 |
| | 283.1 | 386 | 111 | −5.4 |
| | 316.4 | 260 | 73 | −5.5 |
| | 349.7 | 174 | 49 | −5.5 |
| | 383.0 | 115 | 82 | −1.5 |
| | 416.3 | 75 | 12.4 | −7.8 |
| | 815.9 | 2.5 | 1.16 | −3.3 |
| PCLK | 99.9 | 903 | 0.60 | −31.8 |
| | 166.5 | 284 | 0.66 | −26.4 |
| | 233.1 | 117 | 8.2 | −11.6 |
| | 299.7 | 53 | 3.3 | −12.1 |
| | 366.3 | 23.7 | 3.5 | −8.3 |
| | 432.9 | 9.9 | 0.60 | −12.2 |
| | 499.5 | 3.5 | 0.26 | −11.3 |
| | 832.5 | 0.45 | 0.13 | −5.4 |

The field at 3 m can exceed the 2.15 dBi ceiling line by up to 2.5 dB (383 MHz): the structure with its cables is directional (1.4 to 6.1 dBi by the same sphere integral), not over-powered.

### Mode and lumped cross-check

- Mode 182 MHz, structure resistance 2.69 Ω. Unloaded Q 13.2 (radiation, CMAD and barrier resistors); loss added for Q 10 (+0.85 Ω) and Q 3 (+9.1 Ω); Q 30 is not reachable.
- The drivers, RN and lines reflect 12.1 − j33.5 Ω into the mode: **loaded Q 2.4 / 2.3 / 1.5** for unloaded Q 13.2 / 10 / 3. That is why the loss band barely moves the results.
- Cable current at resonance: lumped estimate (Q × ωC_self, panel free-space capacitance 5.1 pF) 0.077 A/V against MoM 0.080 A/V (+0.4 dB).
- Mode frequency: plate capacitance (28.8 pF at 5 mm, 22.5 pF at 6.4 mm) with 44 nH gives 141–160 MHz against 182 MHz from the MoM (13–29 % apart; the wire grid probably under-counts the plate capacitance).

### Cable common-mode current budget (PCLK; allowed at the limit vs estimated rms at Q 10)

- Mains cord at 233 MHz: 1.6 µA allowed vs 101 µA [76 … 105].
- Thermocouple lead at 233 MHz: 4.8 µA allowed vs 293 µA.
- Fan lead at 166.5 MHz: 9.3 µA allowed vs 218 µA.
- The cables carry 25–36 dB too much.

### Proposals (worst row, margin nominal / upper, dB; FAR 3 m)

| Change | PCLK | Typical UI | Worst pattern |
|---|---|---|---|
| As designed | −35.8 / −36.5 | −20.3 / −20.8 | −54.2 / −56.7 |
| Panel frame bonded to PCB GND, 6 contacts | −13.4 / −15.1 | +1.6 / +1.2 | −32.3 / −33.1 |
| Panel frame bonded, 19 contacts (perimeter) | −7.8 / −10.6 | +5.5 / +4.9 | −23.8 / −24.7 |
| FPC ferrite (150 Ω) | −17.9 / −18.8 | −2.6 / −2.8 | −40.1 / −40.2 |
| 19 contacts + ferrite | +1.6 / −1.3 (5V-island cavity) | +25.5 / +24.6 | −5.1 / −9.8 |
| RN1–RN7 150 Ω alone | −33.6 / −34.2 | — | −50.8 / −51.0 |
| 2 × 1 nF (+5V–GND) at the J10 re-sort vias alone | −35.8 / −36.1 | — | — |
| 6 contacts + RN 150 + 2 × 1 nF | −12.5 / −13.3 | +1.6 / +1.2 | −24.7 / −25.3 |
| 19 contacts + RN 150 + 2 × 1 nF | −6.1 / −7.4 | +5.5 / +4.9 | −16.2 / −17.4 |
| **19 contacts + ferrite + RN 150 + 2 × 1 nF** | **+12.3 / +7.8** | **+25.5 / +24.6** | −2.2 / −5.7 |
| Floating panel frame, as designed | −22.0 / −22.6 | −14.8 / −15.2 | −39.4 / −39.5 |

SAC 10 m (nominal / upper): as designed PCLK −35.2 / −35.7, typical UI −18.9 / −19.3, worst pattern −53.5 / −53.8; 6 contacts −13.0 / −15.6, +2.2 / +1.6, −32.6 / −33.5; 19 contacts −8.0 / −11.7, +5.6 / +4.8, −23.4 / −24.7. Not computed for the full combination.

### What is needed for a PASS with ≥ 6 dB at the upper end of the band

- **PCLK (always present, the decisive row):** all four together — panel frame bonded to PCB ground at about 19 points around the perimeter, a 150 Ω flat ferrite on the TFT FPC, RN1–RN7 changed to 150 Ω (PCLK edge at the panel 3.3 ns, no overshoot; check the panel's setup/hold), and 2 × 1 nF C0G from +5V to GND at the J10 re-sort vias. Result +7.8 dB upper, +12.3 dB nominal. Any subset is short of 6 dB.
- **Typical UI:** 19 contacts plus ferrite is enough (+24.6 dB). 19 contacts alone +4.9 (MARGINAL); 6 contacts alone +1.2.
- **Worst pattern (1-pixel stripes):** still fails with everything applied, by 5.7 dB at the upper end. It is not a normal operating mode under EN 55014-1 clause 6, but the UI must not produce it (firmware/UI rule, or panel-side FPC grounding).
- Ask the panel maker about extra FPC ground pins.

Plots: `plots/emission_far3m.png` (with the available-power ceiling line), `emission_power_balance.png`, `emission_structure_transfer.png`, `spice_rgb_chain.png`.

## 4. Radiated RF immunity, display inputs (lossy structure)

- Peak common-mode voltage at the panel inputs under 3 V/m with 80 % AM: 1.57 V pk at Q 10 [1.12 … 1.64 V], at 840 MHz, against the ~0.99 V logic margin → FAIL risk (−4 dB).
- With 19 contacts: 0.29 V pk → PASS (+10.7 dB). With 6 contacts: 0.30 V pk → PASS.
- Thermocouple under the field: about 1 µV → PASS.

Plot: `plots/radimm_currents_tc.png`.

## 5. Cross-scope checks (Y1 capacitor, ZCD capacitor, probe)

- **Emission with Y1 1 nF:** PCLK −38.5 / −38.9, typical UI −20.0 / −20.3. Mains-cord current per FPC ampere: median 0 dB, at most +12.3 dB. No verdict changes.
- **Emission with the oven body and a bonded probe** (valid to 400 MHz only): PCLK −32.3 / −32.8, typical UI −14.0 / −14.3; mains-cord current median +6.1 dB, at most +26.7 dB. No verdict changes.
- **Thermocouple with Y1 (mains 3 V test)**
  - Grounded junction: the worst-case bound rises from 0.016 °C to 4.8 / 7.1 / 9.0 °C (470 pF / 1 nF / 2.2 nF); realistic estimate 0.05–0.09 °C.
  - J20 common mode reaches 3.8–4.2 V pk against the TVS's 5 V working voltage → MARGINAL (TVS conduction would rectify).
  - Insulated junction (20 pF): bound 0.05–0.07 °C.
- **Conducted 150 kHz–30 MHz through Y1 1 nF**, margin against scope A's AV thresholds (realistic / bound):
  - buck 0.58 MHz: −2.8 / −12.6 dB
  - boost 1.2 MHz: **−15.6** / −28.1 dB
  - FPC worst pattern 16.65 MHz: −25.6 dB
  - crystal +31.9 dB; 8080 bus +32.8 dB; backlight PWM +82.6 dB
  - Without Y1 add 25–35 dB: everything then passes except the worst pattern (−0.6 to +9 dB).
  - **Y1 is likely to create a conducted failure at the switching fundamentals** unless switch-node coupling is at least 16 dB below the estimate (area-ratio estimate, ±10 dB). Measure with and without Y1.
- **ZCD node with 1 nF C0G (P-E1):** 0.9–1.8 mV (0.4 mV with Y1) against 0.19 V without it → PASS.
- **Probe, immunity (mains test):** grounded junction 0.008–0.06 °C; insulated 20 pF about 0.001 °C.

Plot: `plots/y1_conducted.png`, `plots/inj_thermocouple.png`.

## 6. PDN

- 3V3: above the 0.33 Ω target from about 46 MHz; anti-resonance 332 MHz (2.7 Ω).
- 5V island: 254 Ω at 498.5 MHz at the J10 via field (a quarter-wave stub, right on PCLK's 15th harmonic at 499.5 MHz); 2 × 1 nF there bring it to 1.6 Ω. Alternative: GND on In2 under that via field.
- 1V2: below 1 Ω up to about 170 MHz.

Plot: `plots/pdn_impedance.png`.

### 6.1 Follow-up (2026-11-18): capacitor choice at the J10 via field — 2 × 100 nF replaces 2 × 1 nF

Raised in review of the results PDF: with 2 × 1 nF the +5V-island impedance shows a new peak near 63 MHz. Checked with `c7b_j10_caps.py` (capacitors at their own ports 2.5 mm either side of the vias, 0402 inductance 0.35 nH + 0.77 nH via mounting).

- **The peak is real:** 26.5 Ω at 64.6 MHz (25.3 Ω in the at-port model). The 1 nF parts resonate against the island's inductance back to the decoupling near the buck (C330/C331/C127) and the C2/PS1 lobe.
- **Emission cost is small:** 66.6 MHz is an even harmonic of both PCLK and the data rate; the island term stays ≥ 19 dB below the limit at every PCLK harmonic for every option. The proposal rows move slightly because the old rows used the at-port model: all four changes, PCLK **+12.0 / +7.2 dB** with 2 × 1 nF, **+12.0 / +7.1 dB with 2 × 100 nF** (was +12.3 / +7.8); 19 contacts + RN 150 Ω + J10 caps −6.1 / −7.5 dB. All four changes are still needed for ≥ 6 dB at the upper end.
- **Recommended: 2 × 100 nF X7R 0402 from +5V to GND, one on either side of the J10 re-sort vias, each with its own GND via.** 498.5 MHz: 253 Ω → 2.96 Ω; no peak below 300 MHz; 0.5 Ω met up to about 100 MHz (the island's spreading inductance sets the floor above that: 0.85 Ω at 166.5 MHz, 1.6 Ω at 300 MHz).
- Every undamped option leaves a mode near 824 MHz of about 42–45 Ω; 2 × (10 nF + 1 Ω) or 100 nF + (1 nF + 2.2 Ω) damp it to about 15 Ω but sit about 0.5 Ω higher below 300 MHz.
- Rejected: 100 nF + 1 nF (6.2 Ω peak at 100 MHz, next to the 99.9 MHz PCLK harmonic); 10 nF + 1 nF (4.0 Ω at 25.5 MHz, 5.2 Ω at 102 MHz); 2 × 10 nF (3.8 Ω at 20 MHz).

|Z| at the J10 via field, realistic placement (Ω):

| Option | 63 MHz | 66.6 MHz | 150 MHz | 498.5 MHz |
|---|---|---|---|---|
| No caps | 1.07 | 1.13 | 2.70 | 253 |
| 2 × 1 nF | 14.9 | 10.4 | 0.36 | 2.80 |
| **2 × 100 nF** | **0.31** | **0.33** | **0.76** | **2.96** |
| 2 × (10 nF + 1 Ω) | 0.50 | 0.51 | 0.86 | 2.99 |
| 100 nF + (1 nF + 2.2 Ω) | 0.50 | 0.53 | 1.02 | 3.06 |

Wherever this document says "2 × 1 nF at the J10 vias", read **2 × 100 nF**. Data: `results.json["pdn"]["5V"]["J10_cap_options"]`, new emission proposal rows per option; plot `plots/pdn_j10_cap_options.png`.

## 7. Layout audit (current board)

- RGB: all on F.Cu over solid In1, 0 mm over voids, at least 9.9 mm from the board edge.
- B2, B3, PCLK, HSYNC, VSYNC and DE have 2 vias each; their B.Cu sections reference the In2 +5V island, with the nearest +5V capacitor 31–47 mm away. B2 and B3 cross the 3V3/+5V split.
- 8080 D5–D7: 9–18 mm within 1 mm of the In1 edge at the mains-band boundary.
- Stitching: GND-via spacing median 3.0 mm; largest gap 8.4 mm at (102.9, 86.1) against λ/20 in FR4 at 1 GHz of 7.15 mm; edge fence ≤ 4.8 mm.
- Hot loops: buck 3.7 mm², boost 5.9 mm², crystal 11.7 mm².
- In1 voids: one merged void, the intentional L30 keep-out (50 mm², plus L11 32 mm²); BUCK_SW and BL_SW run over them.
- IPC: only tables of contents are available for IPC-2221C 9.1.4/9.1.4.1 and 6.1.2, so the layout checks are cited by clause title, not content.

Plot: `plots/layout_planes_fastnets.png`.

## 8. Discrepancies with the old assessment and the spec

- **Vias:** 578 (471 GND), not 556 or 216 (old §10).
- **Line lengths:** RGB 86.7–107.9 mm (spec 12.3 still says 101–124 mm); 8080 bus 31–74 mm.
- **RGB vias:** the old F3 says every RGB line has one via. Now only B2, B3, PCLK, HSYNC, VSYNC and DE have vias, 2 each; old §4 says only VLED and the R-lane stubs cross the 3V3/+5V split.
- **Thermocouple capacitors:** C221/C222 are now 10 nF X7R ±10 % (CL10B103KB8NNNC); spec §2/§6 and the EMI analysis assumed C0G 1 %.
- **PCB value fields lag the schematic:** C6 100 nF vs 1 µF, L12 2.2 vs 10 µH, R4 200 vs 120 Ω, K1, C125.
- **Firmware:** 0xF0 = 0x00 (RGB888, 3 writes per pixel); spec §5 says 0x03.
- **New part, no decoupling:** U6 (74AHC1G14 ZCD Schmitt trigger) has no local decoupling capacitor (nearest 55.7 mm away).
- **PCLK emission:** old F3 had "PCLK alone 17–21 dBµV/m"; the FPC common-mode term was missing.

## 9. What the models cannot see

Dielectric and full-wave detail, the oven steel (only coarsely, ≤ 400 MHz), the panel's internal grounding, the ESP32 module (40/80/240 MHz), SSD1963 PLL noise and the touch controller. Pre-compliance should settle three things:
1. Near-field and FAR scan with and without the panel bonding.
2. LISN measurement with and without Y1.
3. Injection with a grounded vs insulated thermocouple probe.

## 10. Files

`Design Reports/Rev3.0/sim/emc_tests/C_rf/`
- Scripts: `c0_common.py`, `c1_export_geom.py` (KiCad Python, run on a board copy), `c2_layout_audit.py`, `c3_inductance2d.py`, `c4_spice_chain.py`, `c4b_spice_proposals.py`, `c4c_ydist.py`, `spice_worker.py`, `mom.py`, `c5_cm_structure.py`, `c5v_validate_mom.py`, `c5e_energy_check.py`, `c6_emission.py` (v2), `c6q_loaded_q.py`, `c7_pdn.py`, `c8_injected_immunity.py`, `c9_radiated_immunity.py`, `c10_conducted_via_Y1.py`
- `results.json` (`emission` holds only the v2 results; `mom_energy_check`, `spice_chain["Ydist"]`, `emission["mode"]`, `cross_scope_conducted_Y1`, `injected`, `radiated_immunity`, `pdn`, layout sections)
- `plots/*.png`
- Work files (geometry export, MoM npz) are in the session scratchpad `agentC/` folder.
