# Rev3.0 controller — post-layout EMC assessment (EU household appliance)

Date 2026-11-12. Board: `KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb` (layout pass 3, see §8). Scripts and results: `sim/emc/` (`estimates.py` → `estimates.json`, `conducted_heater.png`; flickermeter `flickermeter.py` + `flicker_report.md`), `tools/pcb/in1_web_check.py`. This assessment is model-based; it does not replace a pre-compliance measurement (§7). Where a number is an estimate, its model and assumptions are stated.

## 1. Standards applied and what was available

| Standard | Edition read | Used for |
|---|---|---|
| EN 55014-1:2017 + A11:2020 (CISPR 14-1:2016) | full text | emissions: mains-port disturbance voltage Table 5, disturbance power Table 7/8 or radiated Table 9, discontinuous disturbances (clicks) 4.4 / 5.4, operating conditions Annex A |
| EN 55014-2:2015 (CISPR 14-2:2015) | full text | immunity: category IV, ESD Table 1, EFT Tables 2–4, injected RF Tables 9/10, radiated RF Table 11, surge Table 12, dips Table 13, performance criteria A/B/C |
| IEC 61000-3-2:2018 + A1:2020 + A2:2024 and IEC 61000-3-2:2024 | full text | harmonic currents: Class A limits Table 1, symmetrical-control rule for heating elements (6.2), Class D-style Table 3 limits |
| IEC 61000-3-3 ed. 3.2 | **21-page webstore preview only** (scope, definitions; no limits clause) | flicker: the limits P_st ≤ 1.0, P_lt ≤ 0.65, d_c ≤ 3.3 %, d_max ≤ 4 %, T_max 500 ms and Z_ref = (0.24 + j0.15) + (0.16 + j0.10) Ω are taken from the standard as known, not read from the file — confirm against a full copy |
| IEC 61000-4-15 (flickermeter) | not available | implemented from the published filter specification; validated against the standard's test points as known (§3.2) |
| IPC-2221B / 2221C, IPC-2152, IPC-7351B, IPC-6012 | tables of contents only (Battery Sentinel research folder) plus its public-source summary `ipc_rules.md` | layout checks by clause number: IPC-2221B 6.1.2 power distribution / Fig. 6-1, 6.4.5–6.4.6 capacitance and inductance, 4.7.1 ESD; IPC-2221C 9.1.4.1 small-pitch clearance areas in planes |

The product is a mains-powered household appliance with electronic control: EN 55014-1 "all equipment not listed" limits, EN 55014-2 category IV. The Wi-Fi module is covered separately by RED (EN 301 489-1/-17 for the radio part); this assessment covers the non-radio EMC. Conducted emissions are measured on the mains port only (the heater, fan, thermocouple and display cables are not "associated ports" leaving the appliance longer than 3 m; if the heater or fan lead can exceed 3 m, Table 5 columns 4–7 and the EFT test of EN 55014-2 Table 4 apply to that port).

Because the SSD1963 pixel clock is 33 MHz and the ESP32 runs at 240 MHz, condition 2) of EN 55014-1 4.3.4.2 ("maximum clock frequency below 30 MHz") is not met, so **radiated emissions must be measured over 30–1000 MHz** (Table 9), not only disturbance power 30–300 MHz.

## 2. Operating modes for all tests (EN 55014-1 clause 6, Annex A)

| Mode | Heater | Backlight | Display / Wi-Fi | Fan | Why |
|---|---|---|---|---|---|
| M1 | 100 % (all cycles on) | 100 % | full-screen refresh loop, Wi-Fi connected | on | maximum continuous disturbance from the triac (100 Hz pulse train) and the digital side |
| M2 | regulating at ≈ 50 % duty (the firmware's burst pattern) | 100 % | normal UI | on | discontinuous-disturbance assessment, flicker (61000-3-3), harmonics at partial power |
| M3 | off | minimum (PWM at low duty) | normal UI | off | boost converter restarting every PWM cycle, worst 1.2 MHz input-current steps |

Flicker (61000-3-3) is evaluated at the duty that gives the worst P_st for the firmware's pattern (§3.2); harmonics (61000-3-2) at M1.

## 3. Findings, ranked

### F1 — Conducted emission from the heater triac: the heater branch bypassed the mains filter (fixed in pass 3)

Mechanism. The firmware fires the triac at both zero crossings of an "on" cycle, 230 µs after the ZCD edge, i.e. at an instantaneous mains voltage of roughly 10–40 V (23 V nominal). The heater current therefore starts with a step of ΔI = V_on / 52.9 Ω ≈ 0.44 A (0.19–0.76 A), repeated at 100 Hz. The rise time is set by the series inductance (LISN 2 × 50 µH, cable, heater element) over 52.9 Ω, τ ≈ 1.5 µs. A 100 Hz train of such steps is a continuous disturbance in CISPR terms (repetition rate ≫ 30/min) and is weighted by the quasi-peak detector exactly as CISPR 16-1-1 specifies for a 100 Hz pulse train in Band B (impulse area 0.158 µVs at the receiver input ↔ 60 dBµV).

In passes 1–2 the LC filter (L40 120 µH + C40 1 µF X2, plus C1 100 nF X2 and the common-mode choke L1) sat only on the PSU branch behind the 1 A fuse F1; the heater branch (F3 → triac → heater) connected straight to the mains terminals, so the triac's current steps reached the LISN unfiltered. Model result (QP, mains port, `estimates.py`):

| Case | 150 kHz | 500 kHz | 1 MHz | 5 MHz | Worst margin to Table 5 QP |
|---|---|---|---|---|---|
| heater branch unfiltered, V_on 23 V | 93 dBµV | 75 | 63 | 36 | **−27 dB** at 150 kHz |
| same, V_on 40 V (late ZCD edge) | 98 | 80 | 68 | 40 | −32 dB |
| same, V_on 10 V | 86 | 68 | 56 | 28 | −20 dB |
| X2 0.47 µF across the heater branch only | 70 | 45 | 28 | — | −4 dB |
| **heater behind L40 + C40 1 µF + C1 (pass-3 topology; model with 120 µH, 100 µH gives 1 dB less)** | **55** | 25 | 3 | — | **+11 dB** |
| same, V_on 40 V | 60 | 30 | 8 | — | +6 dB |

Limits: 66 → 56 dBµV QP (0.15–0.5 MHz), 56 (0.5–5 MHz), 60 (5–30 MHz); average limits 10 dB lower, met with the same margins because the QP reading of a 100 Hz train already sits ≈ 10 dB under its peak and the average detector reads lower still. Uncertainty ± 6 dB (turn-on voltage, triac turn-on time, element inductance).

Design change (pass 3, schematic + layout): the LC filter is the main input filter — LINE → F3 (8 A, main fuse) → LINE_FUSED → L40 → LINE_FILT, with C40, C1 and RV1 across LINE_FILT/NEUT; LINE_FILT feeds the triac (Q1.A2), the fan relay (K1) and, through F1 (1 A), the common-mode choke L1 and the PSU. This is Ömer's original filter arrangement from the built unit (the pass-1 schematic had placed it on the PSU branch; that was a generation error). Because L40 now carries the heater current (4.4 A rms) and Özdisan publishes no rating for the IND-120UH-THT of the built unit, L40 is the Core Master RC1415U-101K (100 µH ±10 %, 5 A, 100 mΩ → 1.9 W at 4.4 A; 613 pcs at Özdisan). With 100 µH instead of 120 µH the margin at 150 kHz is 10 dB instead of 11. The X2 capacitors remain fused by F3.

Residual risk: the HLK-10M05 module's own 60–100 kHz flyback is the other conducted source; the vendor claims EN 55022 class B for the family, and it now sits behind L40/C40 and L1 (additional ≈ 40 dB differential attenuation at 150 kHz). The on-board buck (580 kHz) and boost (1.2 MHz) are two isolation barriers and the pi filter away from the mains port; their contribution at the LISN is negligible (§4).

### F2 — Flicker (IEC 61000-3-3): the current heater-firing pattern fails; a 20 s burst frame passes (firmware change)

The firmware (SECTION 7 of the `.ino`) decides once per mains cycle with a 16-bit first-order sigma-delta modulator. A 1 kW resistive load stepping on and off produces a 0.752 % voltage change at the terminals (exact R-L model with Z_ref). The sigma-delta puts that change at 5–20 Hz, where the IEC 61000-4-15 eye-lamp weighting peaks. Flickermeter model validated at the standard's rectangular test points 1–1620 changes/min within +2.8 % (allowed ± 5 %) and at the 8.8 Hz sine within +3.1 %.

| | Current firmware | Recommended |
|---|---|---|
| pattern | sigma-delta, decision every cycle | burst PWM with error carry, 1000-cycle (20 s) frame |
| worst P_st over duty | **1.70 at duty 0.80** (limit 1.0) | 0.54 at duty 0.99 |
| P_lt (= P_st at steady duty; limit 0.65) | fails for every duty from 0.015 to 0.99 | passes with 17 % margin |
| d_c / d_max (limits 3.3 % / 4 %) | 0.75 % / 0.75 % | 0.75 % / 0.75 % |
| voltage changes per minute (max) | 3000 | 6 |
| chamber temperature ripple at duty 0.5, τ = 3 min | negligible | ≈ 3 % of the full-power rise peak-to-peak |

No pattern switching faster than about once per second passes at all duties; second-order modulators are worse (their limit-cycle tones land at 8–15 Hz); sigma-delta with a long decision interval has the same P_st as a fixed burst but an irregular pattern. Firmware rule (not implemented here — firmware is deferred by decision): keep the ISR, the 230 µs delay, the 150 µs gate pulse and the both-zero-crossing firing; at the existing decision point advance a cycle counter 0…999; at 0 latch the increment, `acc += sd_increment * 1000; n_on = acc >> 16; acc &= 0xFFFF`; fire for `cyc < n_on`. Retune the PID for the 20 s hold (lower derivative, anti-windup, thermocouple averaged over the frame). 1500 cycles (30 s) gives P_st 0.47 if more margin is wanted; do not go below 1000 cycles (10 s fails P_lt at 0.68). Full tables: `sim/emc/flicker_report.md`.

### F3 — Radiated emissions 30–1000 MHz: the 110 mm RGB bus to the 7" panel is the one source that can fail; pre-compliance measurement needed

The switching converters are not a radiated problem (§4): their loops are 10–20 mm², their edge-limited harmonic currents give −6 to +3 dBµV/m at 3 m, 40 dB under the FAR limit (42 → 35 dBµV/m 30–230 MHz, 42 dBµV/m above). The digital side is:

| Source | Model | E at 3 m (FAR limit) | Reading |
|---|---|---|---|
| RGB bus, 28 lines over solid In1 GND, 110 mm, 0.2 mm prepreg, 2 ns edges, **all lines switching in phase** (worst test pattern) | DM loop, Ott, + 6 dB ground reflection | 36 dBµV/m at 30 MHz (limit 42), 45.5 at 50–100 MHz (40 / 38), 49.6 at 200 MHz + (35.5 / 42) | fails by up to 14 dB for a pathological pattern |
| same, typical content (half the lines toggling, uncorrelated) | −17.5 dB on the above | 28 dBµV/m at 50–100 MHz, 32 at 200 MHz | passes with 4–10 dB margin |
| PCLK alone (always toggling) | single line | 17–21 dBµV/m | passes |
| common-mode current on cables | E = 1.257·10⁻⁶·f·L·I/r (short) or 60·I/r (resonant) | **budget**: mains cable 3–6 µA, heater/thermocouple leads 3–10 µA, 50 mm FPC 14–200 µA | cannot be computed without measurement: it depends on the ground-noise voltage at the connectors |

What the layout already does (EMI report rules 1–3, 6, 9, 12): 4-layer stack with solid In1 ground under the whole bus, every RGB line with one via and a GND return via within 1.5 mm, 0.5 mm ribbon pitch, no plane splits under the bus (the pass-2 via-field slots were found and fixed, F4). Pass 4 (2026-11-12) implemented the provisions: 33 Ω 0402x4 arrays on all 28 RGB/sync lines (RN1–RN7; 0 Ω arrays are not stocked at Özdisan, 33 Ω is the EMI report's own value), 100 nF across the backlight pair and 1 nF to GND on VLED+, VLED−, TFT_VDD at J10 and on TP_VDD at J11, and the connectors moved to the top side so the RGB lines need no layer change except a 12-via re-sort zone. The arrays sit 45–78 mm from the SSD1963 pins (the corridor near the driver is too narrow for a 28-line band at 0.5 mm pitch through 1206-size arrays); they still slow the edges that reach the FPC and damp the far segment, but the first 45 mm are unterminated at the driver — acceptable for EMI, noted for the measurement. The decisive lever remains the FPC's return path (three ground pins for 28 signals), which is the panel maker's; the 1 nF capacitors give the supply conductors an RF return role.

### F4 — Ground-plane slots under via rows (IPC-2221C 9.1.4.1, EMI rule 2) — fixed in pass 3

Non-GND vias keep their 0.6 mm pad on In1 and the zone keeps 0.25 mm clearance (anti-pad Ø1.1 mm); with the zone minimum width 0.25 mm, any two such vias closer than 1.35 mm leave no copper between them and the plane gets a slot. `tools/pcb/in1_web_check.py` found 21 merged groups (57 vias) on the pass-2 board: the B2–B7 row at J10 (6 vias at 0.8 mm pitch, a 4 mm slot directly under the RGB lines), the three +3V3/+1V2 via groups of the U10 ring and four staircase triplets of the RGB down-leg. Pass 3 re-spaces them (≥ 1.35 mm between non-GND vias, ≥ 1.10 mm GND-to-signal), result in §8.

### F5 — Harmonics (IEC 61000-3-2): passes, with the clause that makes it so

Whole-cycle control: every mains cycle is either fully conducted or not, so the gate function is constant over each cycle and adds **no integer harmonics** (only interharmonics at multiples of 50 Hz / pattern period, which 61000-3-2 does not limit and which 61000-3-3 covers as flicker). The only harmonic source is the 230 µs turn-on notch after each zero crossing: with t_d = 230 µs, I₃ = I₅ = I₇ = 0.010 A against Class A limits of 2.30 / 1.14 / 0.77 A (worst order 39 at 14 % of its limit); even with a 1 ms notch the worst order reaches 66 % of its limit. Classification: Class A (6.2, "equipment not specified as B, C or D"); the heating-element restriction of 6.2 for symmetrical control that can produce integer harmonics up to the 40th order does not bite, because the control does not produce them (Annex D "symmetry of mains current waveforms" shows the multi-cycle patterns meant here). Rated power 1 kW > 200 W, so this argument, not the 200 W exemption, is the basis. The HLK-10M05 (10 W) is below the 75 W no-limit threshold.

### F6 — Discontinuous disturbances (clicks, EN 55014-1 4.4): assessed, no relaxation needed or claimed

The triac switching at the mains-cycle rate (current firmware) or in 20 s frames (recommended) is "disturbances other than clicks" or a click rate N ≥ 30 in the sigma-delta case → the continuous limits of Table 5 apply without relaxation (4.4.2.2); with the 20 s frame, N = 6 switching operations per minute, so the click limit L_q = L + 20·lg(30/6) = L + 14 dB would apply to the switching transients if they were measured as clicks (4.4.2.3) — not relied on, F1 already meets the continuous limit. The fan relay K1 switches a 230 V fan (relay contact, thermostatic use): an individual switching operation at most a few times per hour, disregarded under 5.4.3.2 d) / Annex B factor rules; its contact arcing is behind the input filter in pass 3.

### F7 — Immunity (EN 55014-2 category IV): design provisions and the gaps

| Test | Level | Port / provision on the board | Expected criterion | Gap |
|---|---|---|---|---|
| ESD (5.1, Table 1) | 8 kV air / 4 kV contact | enclosure; touch panel glass (GT911 on the panel), display bezel; thermocouple terminal (TVS D220/221 on both leads), FPC ESD diodes D112/D113 on SDA/SCL at J11 | B | TP_INT and LCD_RST lines to the CTP/TFT FPC have no ESD device; the enclosure design (openings near the terminal) decides the discharge points |
| EFT (5.2, Table 4) | 1 kV, 5 kHz, 2 min each polarity on the mains port | L40/C40/C1 filter now in front of everything, L1 for the PSU; ZCD input is a 2 × 33 kΩ-fed opto (4N28) with firmware debounce | B | the ZCD ISR must tolerate spurious edges (missed or double firing is criterion B as long as the heater control recovers); add I2C bus-recovery and a temperature-read watchdog (EMI report 5.4) |
| EFT signal lines (Table 2) | 0.5 kV capacitive clamp, only if the cable can exceed 3 m | thermocouple lead (1 kΩ + 100 nF filter, TVS), fan lead (230 V, behind the relay) | B | state the maximum lead lengths in the manual (≤ 3 m avoids the test) |
| Injected RF (5.3, Table 10) | 3 V rms, 0.15–80 MHz, 1 kHz 80 % AM, mains port | input filter, HLK isolation; the thermocouple front end rejects 100 kHz bursts by 43 dB (EMI report 3.3) and the ADS1115 reading is averaged | A | the demodulated 1 kHz on the thermocouple input must stay below the 0.5 °C control resolution: measure, firmware averaging over the 20 s frame helps |
| Radiated RF (5.5, Table 11) | 3 V/m, 80–1000 MHz, 1 kHz 80 % AM | thermocouple RC filter, I2C 2.2 kΩ pull-ups, 33 Ω bus resistors | A | same demodulation risk at the thermocouple input |
| Surge (5.6, Table 12) | 1 kV L–N (2 Ω); L–E / N–E not applicable (no earth connection, class II) | RV1 (10 mm MOV) across LINE_FILT–NEUT behind L40, RV2 across the triac, BTA24-800 (800 V) , X2 capacitors, HLK-10M05 | B (C acceptable if self-recovering) | RV1/RV2 are "10561K" (560 V class, max 350 V ac): the 2 Ω 1 kV surge is clamped near 900–950 V, above the triac's 800 V; a 10D431K (275 V ac class, ≈ 710 V clamp at 25 A) across the triac gives the BTA24 margin. L40 (120 µH) in front of RV1 helps by limiting di/dt |
| Dips (5.7, Table 13) | 100 % 0.5 cycle, 40 % 10 cycles, 70 % 25 cycles | HLK primary bulk capacitor rides through ≥ 0.5 cycle at 12 W; 220 µF (C2) on 5 V | B / C | the 40 %-for-10-cycles dip will brown out the module: the ESP32 must reset cleanly (criterion C: self-recovering) and the heater must not stay on through a reset — the ZCD firing stops when the ISR stops, the triac turns off at the next zero crossing |

## 4. Switching converters — what was designed in, and the post-layout numbers

| Item | Design intent (EMI report §3.4, §4.6; spec §12.3) | Layout result (pass 2/3 board) |
|---|---|---|
| Buck TPS562201, 580 kHz, 1 A | input 10 µF + 100 nF at VIN, output 2 × 22 µF, SW copper minimum, loop ≤ 10 mm | hot loop C330/C331–U30–GND ≈ 10 mm²; SW node 3.6 × 3.3 mm (7.4 mm of copper), bootstrap 2 mm; no inner copper under L30; output ripple 2–3 mV pp (SPICE) |
| Boost MIC2288, 1.2 MHz, 0.32 A input | pi filter 10 µF ‖ 2.2 µH ‖ 10 µF with 0.5 Ω + 47 µF damper (undamped it rang 23 mV at 33 kHz); dimming PWM at ≈ 26 kHz above the LC resonance and above 20 kHz | loop L11–U11–D111–C125 ≈ 6.5 × 4 mm; SW node 6.6 mm of copper; no inner copper under L11; 1.2 MHz ripple on the 5 V rail < 0.01 mV pp (SPICE) |
| VLED to the panel | pair on B.Cu along the bottom edge, 100 nF + ferrite at the connector recommended | 78 / 89 mm pair to J10 pins 1/2; **no capacitor at J10 on VLED** — add 100 nF (open item, F3 b) |
| Radiated DM from the loops | — | buck −6 dBµV/m, boost +3 dBµV/m at 3 m across 30–1000 MHz (limit ≥ 35): irrelevant |
| Conducted to the mains port | both converters behind the HLK isolation and now behind L40/C40/L1 | not the limiting item; the HLK's own flyback and the triac (F1) are |

The In2 power layer carries the 3V3 plane with a +5 V island (x 70–147, y 70–98) under the PSU output, buck and boost; the island boundary is crossed by nothing but the B.Cu VLED pair and the R-lane stubs next to J10, for which the island was extended to x 147 in pass 2.

## 5. Layout against the IPC clauses that bear on EMC

| IPC clause (TOC) | Requirement as summarised in `ipc_rules.md` | Rev3.0 board |
|---|---|---|
| IPC-2221B 6.1.2 power distribution, Fig. 6-1 voltage/ground distribution | one solid reference plane; power as planes/islands | In1 solid GND, In2 3V3 + 5 V island; no analog ground net, analog region of the plane at the ADS1115 |
| IPC-2221C 9.1.4 / 9.1.4.1 clearance areas in planes, small pitch | anti-pads must not merge into slots; web ≥ zone minimum width | pass 2: 21 merged groups (F4); pass 3: 0 (target, §8) |
| IPC-2221B 6.4.5 / 6.4.6 capacitance and inductance considerations | controlled loop area, return next to signal | 0.2 mm prepreg microstrip (59 Ω), RGB/8080 over unbroken ground, return via ≤ 1.5 mm at every signal via |
| IPC-2221B 4.7.1 ESD | discharge paths at the connectors | TVS at the thermocouple terminal, ESD diodes on the touch I2C at J11, ground pour along the connector edge |
| IPC-2221B Table 6-1 B2 / IEC 62368-1 | 2.5 mm mains–mains, 6.4 mm mains–SELV | DRC rules `mains_mains`, `mains_to_selv_clearance/creepage`; the heatsink pins have their own rules (spec §12.1) |
| IPC-2152 | widths for 4.35 A at ≤ 20 K rise | MainsHeater class 2.5 mm (LINE, LINE_FUSED, LINE_FILT, Q1-A1/A2 in pass 3) |

## 6. What this assessment did not do

- No 3D field solver and no full-board conducted-emission model: the triac estimate is a one-pulse circuit model with the CISPR pulse weighting; the radiated estimates are loop and wire models with stated assumptions; common-mode currents on the cables are given as budgets, not predictions.
- The HLK-10M05's emission is the vendor's claim; the module is treated as a black box.
- The IPC texts are not available; clauses are cited from the tables of contents and the public summaries, and the checks are the quantitative ones (anti-pads, loop areas, widths, spacings).

## 7. Pre-compliance test plan (replaces EMI report §5 for the EMC part)

1. **Conducted, mains port, 150 kHz–30 MHz, LISN 50 Ω/50 µH, QP + AV (EN 55014-1 Table 5 col. 2–3)**, modes M1, M2, M3. Watch 150–500 kHz for the triac train (F1; QP should sit ≈ 55 dBµV at 150 kHz, limit 66) and 60–200 kHz harmonics of the HLK flyback (below the band start, their 3rd/5th harmonics at 180–500 kHz are the ones to see). If the triac shows more than the model, the knobs are the ZCD timing (earlier firing = smaller step, limited by the latching current) and C1 (100 nF → 470 nF X2).
2. **Click analysis** (4.4, Annex C) at 150 kHz, 500 kHz, 1.4 MHz, 30 MHz in M2 with the recommended 20 s frame: expect "continuous limits met", no click relaxation needed; record the fan relay operations as individual switching operations.
3. **Radiated 30–1000 MHz, FAR 3 m or OATS/SAC 10 m (Table 9)**, mode M1 with the worst display pattern (alternating columns, so every RGB line toggles every pixel clock) and with the normal UI; vertical and horizontal, turntable. Expect the 33 MHz harmonics (100, 133, 166, 200 MHz …) from the FPC/panel; if over the limit, fit the series resistors (F3) and 1 nF at J10, and ask the panel maker for the FPC ground pin usage. Then the ESP32 240 MHz and Wi-Fi are the next lines (radio part under RED).
4. **Harmonics IEC 61000-3-2**, Class A, mode M1 (steady) and M2 (fluctuating, 10-cycle observation per Table 4): expect every order < 15 % of its limit.
5. **Flicker IEC 61000-3-3** with the flickermeter, 10-min P_st at the duties 0.2, 0.5, 0.8, 0.99 of the recommended frame (and 2 h P_lt at the duty the unit settles at): expect P_st ≤ 0.55; the current sigma-delta firmware would read 1.1–1.7 (F2).
6. **Immunity EN 55014-2 cat. IV**: ESD 8/4 kV on the touch panel, bezel, thermocouple terminal and connector openings (B); EFT 1 kV mains 2 min/polarity (B: temperature control continues, no false heater-on); surge 1 kV L–N (B/C, check RV1/RV2 clamp vs the BTA24 — F7); injected RF 3 V and radiated 3 V/m (A: thermocouple reading stable within 0.5 °C under 1 kHz AM); dips per Table 13 (C: clean reset, heater off during reset).

## 8. Layout pass 3 (this assessment's changes) — results

Pass 3 (2026-11-12): DRC 0 violations / 0 unconnected / 0 parity errors on the board as saved (zones filled) and with `--refill-zones` (2026-11-12); mains placement checker 0 issues; In1 anti-pad check: 0 merged groups in the display and mains regions, 4 residual two-via pairs of DC/low-speed nets (J2 FTDI pins 2/3 and 4/5, a +3V3/GND pair at the ESP32 and a +3V3 pair at the buck output, ≈ 2 mm slots each, accepted). 221 vias (GND 104, +3V3 38, +1V2 8 — the 1.2 V core pins are now tied by an F.Cu ring instead of a B.Cu ring —, +5V 7, signals 64), no mains vias; total track length 6.29 m. Heater copper F3 → L40 → Q1 82 mm, whole heater loop 132 mm (pass 2: 87 mm without the choke in the path); C40 8 mm from L40's output pad; LINE_FILT changes from F.Cu to B.Cu through F1's clip pad (Ø1.3 mm barrel, plated cross-section ≈ the 2.5 mm trunk's). RGB lines 100.9–124.5 mm, 8080 bus unchanged (29–73 mm, 0 vias). The heater and fan wire pads (R1, J4) stay on the top edge with J3; the band's west end x 25–50 is free. Schematic: `tools/pcb/sch_pass3.py`; mains band re-placed/re-routed (`placement_override_mains.py`, `route_mains.py`), display vias re-spaced (`route_display.py`, `disp_web.py`); the layout note is §12.5 of `Rev3.0_Design_Specification.md`.

## 9. Open items and decisions

| # | Item | Owner / type | Status |
|---|---|---|---|
| 1 | Heater firing pattern → 20 s burst frame with error carry (F2) | firmware | **required for 61000-3-3**; rule given in F2; **decided 2026-11-12: will be implemented, deferred together with the other firmware work** (spec §10 item 5) |
| 1a | ZCD now uses an H11AA1 AC-input optocoupler instead of 4N28 + bridge (pass 4, layout-driven) | firmware check | same polarity/pulse behaviour expected (output transistor on while |v| > LED threshold); confirm the 230 µs firing delay on hardware |
| 2 | Series 33 Ω on all 28 RGB/sync lines, 100 nF/1 nF at J10/J11 (F3) | schematic + layout | **done in pass 4** (arrays mid-corridor, see F3) |
| 3 | RV1/RV2 class vs the BTA24-800 (F7 surge) | schematic (part number) | **RV1 = TVR14431KSU15Y (275 V ac class, 14 mm) in pass 4**; RV2 across the triac stays 10561K behind it |
| 4 | ESD on TP_INT / LCD_RST at the FPCs (F7) | schematic | **done in pass 4** (D115/D116 PESD5V0S1BA) |
| 5 | Lead-length statement (heater, fan, thermocouple ≤ 3 m) in the manual | documentation | — |
| 6 | Full copy of IEC 61000-3-3 (and 61000-4-15) to confirm the limits used | documentation | — |
| 7 | Pre-compliance measurement per §7 | test | after assembly |

## 10. Layout pass 4 (2026-11-12)

Top-side FPC connectors (flat PCB back for the panel frame), PSU moved to the top-right corner, mains band re-placed with the H11AA1 ZCD, series arrays, connector capacitors, ESD diodes, 275 V MOV, 9.4 mm washer keep-outs with explicit DRC rules (kicad-cli 10 does not report tracks/vias in rule areas on its own). DRC 0 violations / 0 unconnected / 0 parity errors on the board as saved (zones filled) and with --refill-zones, with all 28 rules including the keep-out disallow rules (2026-11-12); In1 anti-pad check 0 merged groups board-wide; mains placement checker 0 issues. 216 vias (GND 109, +3V3 38, +1V2 8, +5V 9, signals 52: 12 RGB/sync re-sort, 4 LCD_RST, 6 I2C, J11 staircase, the rest fan/relay/ZCD/boost), no mains vias, 8080 bus unchanged (29–73 mm, 0 vias); total track length 5.80 m. Heater copper 113.7 mm (F3 → L40 → Q1 66.9 mm), heater trunks on F.Cu with no crossing, C40 15 mm from L40; tall-part gaps to the heatsink envelope K1 2.6 mm, PS1 5.1 mm, L40 10.9 mm, L1 15.5 mm. RGB lines 87–109 mm from the SSD1963 to J10 through the arrays. BOM: 149 footprints (D1–D4 removed; RN1–RN7, C129–C133, D115/D116 added; U1 H11AA1; RV1 TVR14431KSU15Y; J10/J11 upper-contact). Vias under the J10 body (VLED pair, GND pins) are tented. Details: spec §12.6.
