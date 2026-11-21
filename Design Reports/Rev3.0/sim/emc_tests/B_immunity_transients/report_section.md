# Scope B — immunity to transients and supply disturbances (ESD, EFT/burst, surge, voltage dips)

*Saved by the main session on 2026-11-18 at the owner's request, from the scope-B agent's hand-back texts (the harness blocks subagents from writing .md files). The surge numbers are the agent's re-issued values after review: a node-name collision in the first surge netlist (`G` = gate, `g` = generator output; SPICE is case-insensitive) had the generator driving A1 through R2 and hid about 63 V of triac stress.*

Rev3.0 controller, board and schematic as of 2026-11-13. Simulation campaign, 2026-11-18.

**This is a model-based assessment, not an accredited measurement.** Generators, parasitics and two black boxes (HLK-10M05, the panel's CTP) are modelled with stated assumptions, and every verdict names the assumption it depends on. Verdicts are not rounded upward. Where something cannot be simulated honestly, the settling bench test is named.

**Citation tags**
- **STD:** BS EN 55014-2:2015, owner's copy, clause/table and PDF page.
- **NRS (not read from the standard):** basic-standard values (IEC 61000-4-2/-4/-5/-11 are not on disk), taken from public sources: TI SLVA711 and IS 14700-4-2/-4-4/-4-11:2008 (law.resource.org). The IS documents adopt older editions (4-2:2001, 4-4:2004) than the 2008/2012 editions EN 55014-2 cites; 4-11:2004 is the edition cited.
- **DS:** datasheet (file, page). **SCH:** current schematic (`netlist_extract.py` exports a fresh netlist from a scratch copy). **ASM:** assumed, with the swept range.

All numbers are in `results.json`; the verdict table comes from `make_summary.py` (`results.json["verdict_table"]`).

## Verdict summary

| Test (STD) | Part | Worst | Rating | Margin | Verdict |
|---|---|---|---|---|---|
| Surge 5.6 T12 p.20–21 | MOC3052 off-state | 780 V | VDRM 600 V | −30 % | **FAIL** |
| Surge | K1 open contact (COM now on LINE_FUSED) | 1162 V | 750 Vac = 1061 Vpk | −9.6 % | **FAIL** |
| Surge | BTA24 off-state | 780 V | 800 V (VDSM 900 V) | 2.5 % (13.3 %) | MARGINAL |
| Surge | RV1 / F3 / F1 / H11AA1 / R6-R7 / dV/dt | 224 A; 0.8 A²s; 0.03 A²s; 11 mA; 374 V; 126 V/µs | per datasheets | ≥ 25 % | PASS (no fuse opens) |
| Surge | HLK bulk (black box) | ≤ 0.95 × Hi-Link's own reference circuit | — | — | NOT SIMULABLE |
| EFT 5.2 T4 p.16–17 | U6 input | 11.3 V for < 60 ns | 6.5 V | −74 % | **FAIL** |
| EFT | ZCD false edges | 4 of 36 corners | U6 switching thresholds | — | MARGINAL |
| EFT | Triac gate–A1 | 0.153 V | VGD 0.2 V | 23 % | PASS |
| EFT | ESP32 EN line | ≈ 0 | — | — | PASS |
| EFT | Thermocouple reading | 0.18 °C | 0.5 °C | — | PASS |
| Dips 5.7 T13 p.21 | 3V3 rail, all three rows | no reset with bulk ≥ 22 µF; heater cannot be on while the MCU is in reset | C | — | PASS |
| ESD 5.1 T1 p.16 | Isolation barrier, 4 kV contact on the TC probe | 3.98 kV (2.30 kV at 100 pF) | relay coil–contact 2121 Vpk | −88 % | **FAIL** for C_bar ≤ ~120 pF (see §4) |
| ESD | TVS; ADS1115 input | 4.6 A; −0.296 V | 12 A; −0.3 V | 62 %; 1.2 % | PASS; MARGINAL |
| ESD | Steel sheet; glass over touch | 1.43 kV; 0.16 × coupling | 2121 V; panel maker's ±8 kV | 33 %; — | PASS; NOT SIMULABLE |

**Recommended changes (all re-simulated, none applied):** P-S1 + P-S4 (+ P-S2b) for surge, P-E1 (+ P-E2) for EFT; for ESD measure the HLK barrier capacitance first (§4).

## 0. Requirements

**Category IV.** Category II requires no clock above 15 MHz (STD 4.3, PDF p.15); a clock is "any signal used in the device, excluding those which are solely used inside ICs" (3.1.18, p.15). Clocks outside ICs on this board: ESP32 crystal 40 MHz, PCLK 33.3 MHz, 8080 strobe 10–20 MHz → Category IV (4.5, p.16).

Category IV criteria (7.2.4, p.23):

| Test | Criterion | Scope |
|---|---|---|
| ESD | B | B |
| EFT | B | B |
| Injected current 0.15–80 MHz (5.4, Tables 8–10) | A | C |
| RF fields (5.5) | A | C |
| Surge | B | B |
| Dips | C | B |

**Ports.** The mains cord is the only a.c. power port (EN 55014-1 3.4.2, PDF p.26). The heater, fan and the 1 m thermocouple are inside the appliance, so they are not associated ports (3.4.3, p.27). If the controller were ever sold alone, the heater and fan leads would become output a.c. ports, needing EFT only for leads over 3 m (Table 4 note, p.17).

**Test matrix**

| Test | Level / conditions | Applicable | Reason |
|---|---|---|---|
| ESD, Table 1 (5.1, p.16) | 8 kV air / 4 kV contact, 10+/10− per point | yes (enclosure) | — |
| EFT signal/control, Table 2 (p.16) | 0.5 kV, only cables > 3 m | no | No such port; thermocouple simulated as information |
| EFT d.c. power, Table 3 (p.17) | — | no | No d.c. port |
| EFT a.c. power, Table 4 (p.16–17) | 1 kV, 5/50 ns, 5 kHz, 2 min per polarity, CDN | yes | — |
| Surge L–N, Table 12 (p.20–21) | 1 kV / 2 Ω, 5+ at 90°, 5− at 270° | yes | — |
| Surge L–E / N–E | — | no | "No line-to-earth surges … products which do not have provision for connection to earth" (p.21) |
| Dips, Table 13 (p.21) | 0 % / 0.5 cycle; 40 % / 10 cycles; 70 % / 25 cycles; change at zero crossing | yes | — |
| Interruptions | — | no | "Not performed" (5.7, p.21); information only |

**Operating conditions.** Most susceptible normal mode, setting about 50 % (8.1, p.23); each mode of operation (8.3, p.24); heating cabinet with no load (EN 55014-1 A.4.7, p.81). Modelled: heater regulating (on and off cycles), heater off, K1 open and closed.

**Engineering pass criteria** (from STD 6, p.21–22, and Annex A p.26; note d: "switching-on not allowed")

| Criterion | Pass condition |
|---|---|
| All tests | No part beyond absolute maximum; no fuse opening; MOV stress within its life curve; no triac firing while the controller commands zero heating |
| B | No reset, lock-up or lost setting afterwards; power may deviate during a burst if the PID recovers; temperature reading back within 0.5 °C |
| C | Reset allowed; heater off during reset; recovery by itself or by the controls |

**Requirements outside A, B and C.** EN 301 489-1/-17 for the ESP32 radio (RED): not on disk, nobody's scope; it is known (not verified here) to include interruptions. The ZCD firing-timing risk in §3.5.

## 1. Surge 1 kV L–N, 2 Ω (STD 5.6 Table 12, p.20–21; criterion B)

### Set-up

**Generator.** SLVA711 Fig. 6 topology, fitted (NRS): Cc 5.93 µF, Rs1 20.2 Ω, Rm 0.81 Ω, Lr 10.9 µH, Rs2 26.2 Ω. Validated in ngspice (`val_cwg.png`): open circuit 1.20/50.0 µs; short circuit 8.00/20.0 µs; 1000 V / 500 A, 2.00 Ω.

**Coupling.** 18 µF L–L (NRS, SLVA711 p.8). Mains 325 Vpk behind 1.5 mH decoupling per line (ASM) and a 0.4 Ω + 0.8 mH source; 1 m cord at 1 µH per conductor (ASM). Pulses + at 90°, − at 270°.

**EUT** (SCH)
- J3 → F3 (10 mΩ) → LINE_FUSED, which carries K1 COM. The fan is on the NO contact: 200 pF ∥ 600 Ω + 3 H (ASM); K1 open (1.5 pF) or closed.
- L40: 100 µH, 0.1 Ω, saturating. Knee and saturated inductance swept 20 A/20 µH, 10 A/10 µH, 6 A/5 µH (ASM).
- LINE_FILT: C40 1 µF, C1 100 nF, RV1 TVR14431.
- Q1: on 0.05 Ω, or off 10 MΩ ∥ 100 pF. Across Q1: RV2 TVR10561 and the 47 Ω + 10 nF snubber.
- Gate drive: R3 360 Ω → MOC (1 pF) → gate; R2 360 Ω.
- Heater 52.9 Ω + 2 µH.
- F1 → L1 (differential leakage 20/100/200 µH, ASM) → HLK black box: 11 Ω (from the 34 A inrush, DS p.2), bridge, bulk 4.7/10/22 µF, 7 W.
- ZCD: R6/R7 33 kΩ and the H11AA1 LEDs on the HLK AC pins.

**Varistors.** Thinking datasheet "max clamping" curves, digitised (DS p.23/24); nominal and minimum corners scaled by V1mA. Model at the table points: RV1 710 V @ 50 A (table 710); RV2 938 V @ 25 A (table 930).

**Sweep.** 48 runs (polarity × heater × K1 × varistor corner × saturation) plus 9 PSU-branch runs; 200 ns step (agrees with 20 ns to within 0.1 V).

### Results (re-issued)

At the triac-voltage peak (worst case: heater off, varistors at the max-voltage corner, L40 knee 6 A / 5 µH, 20 ns step): V(LINE_FILT,NEUT) 788.9 V; V(A2,A1) 779.8 V; V(A1,NEUT) 9.0 V; I(heater) 0.172 A; I(C4) 0.009 A; I(RV2) 0.163 A — the 9 V between LINE_FILT and the triac are RV2's own current through the heater.

| Part | Worst | Rating | Margin | Verdict |
|---|---|---|---|---|
| Q1 BTA24 off-state | 780 V | VDRM 800 V; VDSM 900 V / 10 ms (ST DS2112 Rev 12 p.2) | 2.5 % / 13.3 % | MARGINAL |
| U5 MOC3052 (≈ V(A2–A1)) | 780 V | VDRM 600 V (onsemi p.3) | −30 % | **FAIL** |
| K1 open contact | 1162 V | 750 Vac = 1061 Vpk (HJR-3FF p.2); no impulse rating | −9.6 % | **FAIL** |
| dV/dt across Q1 | 126 V/µs | 500 V/µs (ST p.2) | 75 % | PASS |
| RV1 | 224 A / 2.2 J | 4500 A; ≈ 1.2 kA for 10 pulses at Td 20 µs (DS p.18); 115 J | 81 % / 98 % | PASS |
| RV2 (TVR10561) | 0.16 A | — | — | barely conducts (no function) |
| F3 I²t | 0.8 A²s | ≥ 10.2 A²s (lower bound from the 400 %/10 ms point, DS Normal FUSE p.2) | 92 % | PASS |
| F1 I²t | 0.03 A²s | 3.5 A²s (Reomax TBC 1 A, p.3) | 99 % | PASS |
| H11AA1 LED | 11.3 mA | ±40 mA (Vishay p.2) | 72 % | PASS |
| R6/R7 | 374 V | 500 V (BOM field) | 25 % | PASS |
| HLK bulk | 360–491 V | Vendor reference circuit (10D561K, DS p.9–10): 385–552 V | ours ≤ 0.95 × vendor | NOT SIMULABLE |

**Breakover (argument, not a simulated result).** Above 600 V the MOC3052 can be expected to break over and gate Q1 through R3; the heater would then run for the rest of that half cycle (≤ 5 ms). A behavioural latch model (`sim_surge.py --breakover` → `surge_breakover`) shows the driver conducting partially, the triac voltage held at 615 V and a heater current pulse of 8.7 A for 35 µs with no latched half-cycle — but it depends on unpublished quantities (real breakover voltage, turn-on charge, Q1 gate-controlled turn-on time) and is recorded as "ARGUMENT (model inconclusive)". Either way the driver is operated beyond its absolute maximum, so it stays FAIL. With an 800 V driver plus P-S3 or P-S4 the model shows no breakover.

### Proposals (`--proposal`; Q1 and the 800 V driver see the same voltage)

| Variant | Q1 / 800 V driver | Margin to VDRM 800 V | Verdict |
|---|---|---|---|
| P-S1 alone (800 V random-phase driver, same DIP-6 pin-out, FOD4218 class; RV2 unchanged) | 780 V | 2.5 % | MARGINAL — not enough by itself |
| P-S3 alone (RV2 → TVR14431) | 653 V | 18.4 % | MARGINAL |
| P-S1 + P-S2b + P-S3 | 651 V | 18.7 % | MARGINAL (still under 20 %) |
| **P-S1 + P-S4 (RV2 → 1.5KE440CA bidirectional TVS)** | **606 V** | **24.3 %** | **PASS** (TVS 3.45 A / 0.045 J against 13 A 8/20 µs: 73 % margin) |
| P-S1 + P-S2b + P-S4 | 601 V | 24.9 % | PASS |
| RV2 → TVR14391 (250 Vac varistor) | 599 V | 25.2 % | rejected: fails the 253 Vac check |
| P-S2b (RV3 = second TVR14431 across LINE_FUSED–NEUT) | K1 contact 773 V | 27.1 % | PASS (RV3 228 A / 1.93 J) |
| P-S2a (RV1 moved in front of L40) | 858 V at the triac | — | rejected |

The 800 V driver is needed in every case (all options leave more than 600 V across it); the clamp across the triac (P-S4, or P-S3 with less margin) is what actually protects Q1 and the driver.

**Steady-state checks at 230 V + 10 % = 253 Vac (358 Vpk)**

| Part | Rating | Margin | Verdict |
|---|---|---|---|
| 1.5KE440CA | VRM 376 V, IRM ≤ 1 µA | 4.8 % | MARGINAL (VBR rises with temperature) |
| TVR14391 | 250 Vac | −1.2 % | FAIL |
| TVR14431 | 275 Vac | 8 % | MARGINAL |

TVS data from the SGS-Thomson 1.5KExx Transil sheet p.3 (VRM 376 V, VBR 418–462 V, VCL 603 V at 3.5 A 10/1000 µs and 776 V at 13 A 8/20 µs; copy in `datasheets/`); the model uses the higher 10/1000 µs point. Özdisan stock for the 1.5KE440CA and the 800 V driver was not checked; generic class "1500 W bidirectional TVS, 376 V stand-off, DO-201".

**Verdict.** Current design FAIL. With P-S1 + P-S3 MARGINAL; with **P-S1 + P-S4 (+ P-S2b) PASS**.

**The model cannot see** HLK internals, the real L40 saturation, relay-gap impulse breakdown or breakover physics.

**Bench test.** 1 kV at 90°/270°, heater off, K1 open: measure V(A2–A1) with a 1 kV differential probe, put a current probe on the heater lead, and watch K1 for flashover.

Plots: `plots/surge_waveforms.png`, `surge_margins.png`, `val_cwg.png`, `val_mov.png`, `val_L40_sat.png`.

## 2. EFT 1 kV common mode on the mains (STD 5.2 Table 4, p.16–17; criterion B)

### Set-up

**Generator (NRS).** 1 kV open circuit, 50 Ω source, 5/50 ns (model 5.00/50.0 ns), 10 nF blocking capacitor, 33 nF CDN to L and N together, burst 15 ms at 5 kHz every 300 ms. Sources: IS 14700-4-4 6.1.1 p.11 and 6.2.1 p.13; SLVA711 p.4–5.

**Strays (all ASM)**

| Element | Value |
|---|---|
| HLK primary→SELV (C_hlk) | 20 pF / 100 pF / 1 nF |
| Opto I/O | 0.5 pF (swept 0.3–2 pF) |
| MOC I/O | 1 pF |
| K1 coil–contact | 2 pF |
| Heatsink | 15 pF to the A2 tab, 3 pF to the plane, 1 pF to SELV |
| Heater to chassis / fan to chassis | 100 pF / 50 pF |
| SELV ground to plane / chassis to plane | 5–50 pF / 20–150 pF |
| Q1 junction capacitance | 50–200 pF |
| ZCD node | 10 kΩ, 8 pF |
| Thermocouple | probe on the chassis, 1 µH per wire, its filter with 10 % capacitor mismatch |

### Results

| Victim | Worst | Limit | Verdict |
|---|---|---|---|
| ZCD node → U6 → IO34 | False edges in 4 of 36 corners (negative pulse, transistor off, C_hlk ≤ 100 pF), ≤ 57 ns | VT+ ≥ 1.5 V, VT− ≤ 1.14 V at 3 V (DS sn74lvc1g14 p.6) | MARGINAL |
| U6 input | 11.3 V | 6.5 V (DS p.4) | **FAIL** (< 1 nC) |
| Q1 gate–A1 | 0.153 V (triac sees 41 V and 3.6 kV/µs for ~20 ns; 1.4–4 nC) | VGD 0.2 V (ST p.2); ≈ 50 nC implied by the 500 V/µs rating (an argument) | PASS (23.5 %) |
| MOC3052 | 34 V; LED 26 mA for ns (1.3 nC) | — | PASS (argument) |
| ESP32 EN | 0.003 mV | — | PASS |
| Barrier | 549 V | 2121 Vpk | PASS (74 %) |
| SELV vs plane | 1.17 kV common-mode | — | info |
| Thermocouple reading (information) | 0.18 °C in the one conversion containing a burst | 0.5 °C | PASS |
| Thermocouple input CM | ±0.6 V; clamp current ≤ 9.5 mA | 10 mA (ADS p.4) | MARGINAL (info) |

**Firmware (ISR l.765–795, no debounce; worst case = every burst pulse gives an edge)**

| Duty | 0 | 0.2 | 0.5 | 0.8 | 1 |
|---|---|---|---|---|---|
| Power error, % of full | 0 (never fires) | +3.5 | +3.0 | +0.6 | −0.2 |
| Random-phase turn-ons in 6 s | 0 | 30 | 4 | 6 | 0 |

This meets B functionally.

### Proposals

- **P-E1:** 1 nF C0G from the ZCD node to GND. Over 72 corners the node stays ≥ 3.07 V idle-high and ≤ 0.26 V when held low; peak 3.5 V; edge delay 8.4 µs → PASS.
- **P-E2 (firmware):** level-qualify edges (pin still low 50 µs later; the real low window is ≈ 450 µs). In the model this equals the no-burst case. A 9–11 ms window gate made things worse.

**Verdict.** Current design FAIL (U6 absolute maximum), functionally MARGINAL. With P-E1 (+ P-E2): PASS.

**The model cannot see** the real strays (C_hlk above all), ground-bounce effects on the GT911 and SSD1963, or software lock-up.

**Bench test.** 1 kV, 2 min per polarity, at duty 50 % and 0 %: log the ISR count and heater current, then check the display, touch and temperature reading.

Plots: `plots/eft_waveforms.png`, `eft_zcd_sweep.png`, `val_eft.png`.

## 3. Voltage dips (STD 5.7 Table 13, p.21; criterion C)

### Set-up

**Dips.** Steps at the zero crossing; the generator's 1–5 µs edge and < 0.4 + j0.25 Ω source are negligible (NRS: IS 14700-4-11 Table 4 p.13).

**HLK black box** (Hi-Link 10M series V1.5)

| Parameter | Value | Source |
|---|---|---|
| Input range | 85–264 Vac; 70–350 Vdc | p.2 |
| Efficiency | ≥ 80 % | p.4 |
| Load curve | 85 Vac → ≈ 85 % load; 70 Vdc → 70 % | Fig. 6 p.9 |
| Input resistor | 11 Ω | p.2 |

**Derived bulk capacitance:** holding 85 % of 12.5 W for a half cycle at 85 Vac, staying ≥ 70 V, needs ≥ 22 µF. Swept 10/22/33 µF; dropout 50/70/90 V; load 3.5 and 5.5 W.

**Rails.** 5 V: C2 220 µF + 20 µF. 3V3, TPS562201 (p.5): maximum duty from t_off,min 310 ns; UVLO 3.3/3.8–4.3 V; 1 ms soft start; 0.9 A. ESP32 brown-out 2.43 V (ESP-IDF default, not a datasheet value).

### Results

| Row | Bulk minimum (22 µF, 5.5 W) | 5 V / 3V3 | Reset | Verdict |
|---|---|---|---|---|
| 0 % / 0.5 cycle | 304 V | 5.00 / 3.32 V | 0 of 18 corners | PASS (even A) |
| 40 % / 10 cycles | 106 V | 5.00 / 3.32 V | 1 of 18 (10 µF, 90 V dropout, 5.5 W) | PASS |
| 70 % / 25 cycles | 212 V | 5.00 / 3.32 V | 0 of 18 | PASS |

**If a reset happens**
- IO33 (TRIG) is "oe=0, ie=0" with no pull, at and after reset (ESP32 v5.3 p.69–70). The MOC LED has no current source, so the heater cannot be on during reset.
- `setup()`: fan on, 1 s delay with TRIG floating, then TRIG driven low; the setpoint restarts at 20 °C, so the user restarts the program. C allows restoration by the controls (STD 6, p.22).
- EN timing: 10 kΩ / 1 µF reaches 0.75·VDD in ≈ 14 ms (WROOM-32E p.39), against a 1 ms soft start.

**ZCD under sag** (CTR 20 % minimum, Vishay p.2). The edge comes before the zero crossing by:

| Mains | Advance | LED peak |
|---|---|---|
| 230 V | 475–597 µs | — |
| 70 % | 680–860 µs | 3.4 mA |
| 40 % | 1.21–1.54 ms | 1.95 mA |

At 0 % exactly one edge is missed: a harmless parity flip. Heater power falls during the dip (fail-safe). Information: the first reset needs a 0 % interruption of 8 cycles.

**Bench test.** Programmable source: log 5 V and 3V3, and find the shortest 0 % interruption that resets.

Plot: `plots/dips_rails.png`.

### 3.5 Firing-timing finding (functional, not EMC)

With a minimum-CTR H11AA1 (20 %), edge + 230 µs lands 245–367 µs *before* the zero crossing even at nominal mains. The triac then conducts only a sliver and the heater barely heats. Fire relative to the centre of the measured ZCD window instead (scope A found the same and proposes F1).

## 4. ESD 8 kV air / 4 kV contact (STD 5.1 Table 1, p.16; criterion B)

### Discharge points (GF-2.1 documents)

Rules (NRS): only points accessible in normal use; contact to conductive parts, air to insulating ones; charge removal on an ungrounded EUT (IS 14700-4-2 8.3.1 p.17, 5 p.12, 7.2.2 p.14).

| Point | Test | Modelled as |
|---|---|---|
| 3 mm glass + 0.3 mm LOCA over the 0.7 mm CTP cover | air 8 kV | E3 |
| 0.40 mm gaps at the glass edge (internal conductors ≥ 12 mm away behind the sealed bead) | air 8 kV | lands on the steel → E2 |
| Floating steel oven sheet | contact 4 kV (bare) or air 8 kV (coated) | E2 |
| Thermocouple probe ring (assumed grounded junction, accessible) | contact 4 kV | E1 |
| J2, FPC tails, heatsink | — | not accessible in normal use; J2 must be handled ESD-safe in service |

### Set-up

**Generator.** 150 pF / 330 Ω (SLVA711 p.2) + Lm 1.78 µH ∥ a 4.95 pF / 155 Ω / 179 nH tip branch. At 4 kV into 2 Ω: 15.0 A, 0.80 ns, 7.9 A at 30 ns, 4.0 A at 60 ns (targets NRS, IS Table 2 p.11).

**TVS.** PESD5V0S1BA model through 10 V @ 1 A and 14 V @ 12 A, 35 pF (Nexperia 2024 p.3–4). **ADS1115:** input clamp diodes.

**Board.** SELV to plane C_env 10/30/100 pF; SELV↔mains C_bar 20 pF … 2.2 nF (ASM); mains to plane through 2 µH + 25 Ω.

### Results

| Point / part | Worst | Rating | Margin | Verdict |
|---|---|---|---|---|
| E1 TVS | 4.6 A | 12 A / ±30 kV | 62 % | PASS |
| E1 J20 | 13.2 V | — | — | — |
| E1 ADS input | ±0.296 V; 7 µA | −0.3 V; 10 mA | 1.2 % | MARGINAL (voltage rule only) |
| E1 R220 | 0.023 µJ | — | — | PASS |
| **E1 barrier** | 3.98 kV (20 pF / 10 pF); 2.30 kV (100 pF / 30 pF); stays ≈ 2.2–3.4 kV until bled | Relay coil–contact 2121 Vpk; HLK 2500 Vac = 3536 Vpk (p.11); K1.1↔coil pads 3.52 mm ≈ 4 kV impulse (IEC 60664-1, NRS) | −88 % | **FAIL** for small C_bar (table below) |
| E2 steel sheet | barrier ≤ 1.43 kV | 2121 Vpk | 33 % | PASS |
| E3 glass | Direct-coupling bound (unphysical): 10–29 A into the GT911 clamp. Our stack couples 0.16 × the bare CTP cover | CTP rated ±8 kV air / ±4 kV contact (SAT070 p.23); LCM ±2 kV (p.15); GT911 3.47 V, HBM 2 kV (Rev.10 p.22) | — | NOT SIMULABLE |

**Why E1 fails.** The SELV circuit floats. A 4 kV contact into accessible SELV metal shares the gun's 600 nC with a small board capacitance, so the barrier sits at kV level until bled. The ICs see nothing locally; the risk is flashover across the insulation.

**Barrier voltage versus C_bar** (15 points 20 pF … 2.2 nF, both polarities; `results.json["esd_barrier_vs_Cbar"]`, `plots/esd_barrier_vs_Cbar.png`). C_bar is the total SELV↔mains capacitance: the HLK reading plus about 5 pF for the optos, relay and heatsink.

| C_env | C_bar at which the barrier reaches 2121 Vpk | C_bar needed for PASS (≤ 80 % of rating) |
|---|---|---|
| 10 pF | 138 pF | 207 pF |
| 30 pF | 120 pF | 186 pF |
| 100 pF | 66 pF | 138 pF |

Against the HLK's own 3536 Vpk, C_bar ≥ 37 pF is enough when C_env = 10 pF.

**How to read the owner's LCR measurement of the HLK +Vout↔AC capacitance:** ≥ about 210 pF → passes with margin; 140–200 pF → marginal; below about 120 pF → fails. The verdict also assumes the probe is accessible and has a grounded junction.

**I2C, INT and RST lines.** The TVS clamps (≥ 5.5–9.5 V) sit above the IC limits, so the IC's internal clamps conduct first. This matters only if charge reaches the FPC, which E3 bounds.

### Proposal

**P-D1:** Y1 1 nF, 400/500 Vac, from SELV GND to NEUT near PS1 — only if the measurement shows C_bar is too small.

| Effect | Value |
|---|---|
| ESD barrier | ≤ 532 V (75 %, PASS) |
| EFT | no false edges with C_hlk = 1 nF |
| Touch current | ≈ 80 µA (class II ≈ 0.25 mA, IEC 60335-1, NRS) |
| Conducted and radiated emission | see scopes A and C: scope C finds Y1 likely to create a conducted failure at the buck/boost fundamentals |

Use a Y1 part only, and keep the 6.4 mm rule. Alternative: an insulated-junction or guarded probe.

**Verdict.** Current design FAIL for a small barrier capacitance (E1), otherwise PASS; E3 is a bench item.

**Bench test.** 4 kV on the probe with an electrostatic voltmeter on SELV; 8 kV air on the glass centre, corners and the bottom edge over the tails.

Plots: `plots/esd_barrier.png`, `esd_barrier_vs_Cbar.png`, `esd_tc_probe.png`, `val_esd_gun.png`, `val_tvs.png`.

## 5. Where the old assessment and other files no longer match

1. RV1 is now the 14 mm 275 V varistor, not a 10561K. The old report never checked the 600 V triac driver.
2. Surge criterion is B, not "B (C acceptable)"; dips criterion is C, not B/C.
3. Old claims that the HLK "rides ≥ 0.5 cycle at 12 W" and that the 40 % dip browns it out have no datasheet basis.
4. The ZCD is no longer a 4N28 "with firmware debounce": it is an H11AA1 and there is no debounce.
5. D115/D116 now exist on TP_INT and LCD_RST.
6. K1 is in front of L40, not behind the filter.
7. "5.3 Table 10" should read 5.4.
8. `Design Reports/Rev3.0/Rev3.0_netlist.net` is stale (C6 100 nF, MOC3053, R4 200 Ω, K1 on LINE_FILT).
9. Spec §1/§7.1 still say 4N28 and MOC3053, and give Rd 20 mΩ where ST says ≤ 16 mΩ.
10. U6 value field says LVC1G14, but its MPN is AHC1G14.
11. The HLK datasheet gives isolation as 3000 Vac on p.1 and 2500 Vac on p.11.
12. K1 has a 3.52 mm LINE_FUSED-to-coil spacing, inside the 6.4 mm barrier (component-inherent); its coil–contact rating is 1500 Vac.

## 6. Assumptions that move the verdicts most

1. HLK barrier capacitance (unpublished). It decides the ESD verdict and most EFT false edges.
2. Whether the thermocouple probe is user-accessible with a grounded junction.
3. Varistors at the +10 % tolerance corner, and the L40 saturation curve.
4. K1 open-contact impulse withstand: only the 50 Hz rating exists.
5. HLK bulk capacitance: ≥ 22 µF, derived from its load curve.
6. Generator values not read from the standard, taken from older public editions (IS 14700-4-x) and TI SLVA711.

## 7. Not done

Firmware lock-up, glass ESD physics, indirect ESD (HCP/VCP), relay and PCB gap flashover, HLK internals, EN 301 489.

**Datasheets** (in `datasheets/`): ST BTA24 Rev 12; Nexperia PESD5V0S1BA 2024; Espressif ESP32 v5.3 and WROOM-32E v2.1; Goodix GT911 Rev 10; Hi-Link 10M V1.5; Vishay H11AA1 (the BOM part is Isocom); Tianbo HJR-3FF; SGS-Thomson 1.5KExx; TI SLVA711; IS 14700-4-2/-4-4/-4-11. The TVR14431 data come from `Datasheets/TVR10391KSY.pdf`. FOD4218 was checked on onsemi's product page only.

## 8. Files and re-run order

All scripts use `python -X utf8`; the whole set runs in about 10 min:
1. `netlist_extract.py`
2. `validate_generators.py`
3. `sim_surge.py`
4. `sim_surge.py --proposal` (and `--breakover`)
5. `sim_eft.py`
6. `firmware_zcd_model.py`
7. `sim_dips.py`
8. `sim_esd.py`
9. `make_summary.py`
