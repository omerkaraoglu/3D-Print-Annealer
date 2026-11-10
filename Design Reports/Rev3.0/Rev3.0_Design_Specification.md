# 3D Printer Filament Dryer / Print Annealer — Hardware Rev3.0 Design Specification

Date: 2026-11-09  ·  Branch: `Rev3.0`  ·  Author: generated with Claude for M. Ömer Karaoğlu (READARK)

## 1. Scope of Rev3.0

| # | Change | Why |
|---|--------|-----|
| 1 | Display changed from 2.8"/3.2" ILI9341 SPI header to **SATOZ SAT70AT40D21-33KN-CTP-V1** (7", 800x480, 24-bit TTL RGB, capacitive touch) | Requested |
| 2 | **SSD1963QL9** display controller added on the PCB (8-bit 8080 bus from the ESP32, 1215 KB frame buffer, RGB timing generator) | The panel has no controller of its own; the ESP32-WROOM-32E cannot generate RGB timing; every ESP32-S3 module is out of stock at Özdisan, so the MCU was kept |
| 3 | MAX6675 header module removed; **ADS1115IDGSR** 16-bit ADC thermocouple front end built from SMD parts, K-type thermocouple on a 5.08 mm screw terminal, NTC cold-junction sensor | Requested |
| 4 | Power: **HLK-10M05** (5 V / 2 A) replaces HLK-PM01; **TPS562201** buck replaces the TLV1117-33 LDO; **LD1117S12** added for the SSD1963 1.2 V core; **MIC2288** boost LED driver for the backlight | 7" backlight (1.35 W) and the display controller push the 5 V budget to ~5.5 W and the 3.3 V load to ~0.9 A; an LDO would dissipate ~1.5 W at 85 °C ambient |
| 5 | Mains input EMC stage **IND-120UH-THT + C42P2105KBSC400 (1 µF X2)** inserted after fuse F1 on the PSU branch | Requested (filter existed in the earlier design but was not on the board) |
| 6 | 33 Ω series terminations on all ESP32→SSD1963 bus lines, 2.2 kΩ I2C pull-ups, ESD/TVS on the thermocouple and touch lines, LC pi-filter on mains | EMC (CISPR 32 Class B target) |
| 7 | ESP32 module part number changed to **ESP32-WROOM-32E-N16** | -N4 has 0 stock at Özdisan, -N16 has 1,213 |

Unchanged: mains fuses/MOVs/snubber, BTA12 triac + MOC3053 driver, 4N28 zero-cross detector, SRD-05 fan relay, FTDI/auto-boot circuit, ESP32 pin usage for TRIG (IO33), ZCD (IO34) and FAN (IO13).

## 2. Sourcing (Özdisan, prices at qty 1 excl. VAT, 2026-11-09, ≈50 TRY/USD)

All new main components were checked on ozdisan.com for stock and operating temperature. Every IC is rated to at least +85 °C; the only exceptions to the 85 °C ambient target are listed in §9.

| Ref | Part (MPN) | Function | Stock | Price | Temp |
|-----|-----------|----------|------:|------:|------|
| U3 | ESP32-WROOM-32E-N16 | MCU, 16 MB flash | 1,213 | ₺256 / $5.1 | -40..+85 |
| U10 | SSD1963QL9 (Solomon, LQFP-128 0.4 mm) | TFT controller | 279 | ₺303 / $6.1 | -40..+85 |
| J10 panel | SAT70AT40D21-33KN-CTP-V1 (SATOZ) | 7" 800x480 RGB + GT911 CTP | 61 | ₺1,990 / $39.7 | -20..+70 (!) |
| J10 | DS1020-09-40VBT1A (Connfly, 40p 0.5 mm, bottom contact) | panel FPC connector | 31,182 | ₺20 | -40..+105 |
| J11 | DS1020-09-06VBT1A (Connfly, 6p 0.5 mm, bottom contact) | touch FPC connector | 1,918 | ₺11 | -40..+105 |
| U20 | ADS1115IDGSR (TI) | 16-bit ΔΣ ADC, PGA, I2C | 3,843 | ₺178 / $3.5 | -40..+125 |
| J20 | DG127H-5.08-02P-14-00AH (DEGSON) | thermocouple screw terminal | 44,980 | ₺7.8 | — |
| TH220 | NCP18XH103F03RB (Murata 10k 1% 0603) | cold-junction NTC | 2,240 | ₺0.4 | -40..+125 |
| D220/221, D112/113 | PESD5V0S1BA,115 (Nexperia SOD-323) | ESD/TVS | 11,013 | ₺6.7 | -65..+150 |
| PS1 | HLK-10M05 (Hi-Link) | AC/DC 5 V / 2 A, 10 W | 400 | ₺230 / $4.6 | -25..+60 (!) |
| U30 | TPS562201DDCR (TI, TSOT23-6) | 5→3.3 V buck 2 A | 2,328 | ₺11 / $0.22 | -40..+125 |
| L30 | SRI0605B-4R7M (Core Master, 4.7 µH 4 A) | buck inductor | 1,961 | ₺17 | — |
| U31 | LD1117S12CTR (ST, SOT-223) | 3.3→1.2 V LDO 800 mA | 2,500 | ₺6.1 | -40..+125 |
| U11 | MIC2288YD5-TR (Microchip, TSOT23-5) | backlight boost 1.2 A / 34 V | 5,740 | ₺34 / $0.68 | -40..+125 |
| L11 | PCD0403MT100 (Viking, 10 µH 1 A) | boost inductor | 8,969 | ₺5.9 | — |
| D111 | SS14 (SMA) | boost rectifier | >10,000 | ₺1–6 | -65..+125 |
| Y10 | CX3225GB10000P0HPQCC (Kyocera, 10 MHz 18 pF) | SSD1963 crystal | 3,906 | ₺15 | -40..+85 |
| L40 | IND-120UH-THT (radial 120 µH, D22.5 P9) | mains filter choke | 9,774 | ₺233 / $4.6 | — |
| C40 | C42P2105KBSC400 (Faratronic 1 µF 275 VAC X2, P27.5) | mains filter cap | 57,151 | ₺12 | -40..+125 |
| L12, C127/C124, R132, C128 | 2.2 µH ≥1 A SMD, 2 × 10 µF, 0.5 Ω 1206, 47 µF 10 V | backlight boost input pi-filter + damper (added from the EMI analysis) | commodity values; pick in-stock MPNs at Özdisan (Viking PCD0403 / Core Master FPI0403S 2.2 µH, Koshin 47 µF) | — | — |
| R220/R221, C221/C222 | 1 kΩ 0.1 % 0603, 10 nF C0G 1 % 0603 | thermocouple filter precision parts (EMI analysis: common-mode rejection depends on their matching) | commodity | — | — |

Not available / rejected: MAX31855, MAX31856, MCP9600, ADS1118 (not stocked); OPA333/OPA2333 (0 stock); every ESP32-S3 variant (0 stock, order on request); TMP235/LMT86 (0 stock); SSD1963-based Winstar 7" modules (in stock but ≈$95); UART HMI modules (thin stock, UI rewrite).

## 3. Architecture

```
mains ─ F1 ─ [L40 120µH ─ C40 1µF X2] ─ RV1/C1/L1(CMC) ─ PS1 HLK-10M05 ─ 5V ─┬─ U30 TPS562201 ─ 3V3 ─┬─ ESP32 / ADS1115 / GT911
                                                                              │                      └─ U31 LD1117-1.2 ─ 1V2 ─ SSD1963 core
                                                                              ├─ U11 MIC2288 boost ─ 9.6 V / 138 mA ─ backlight
                                                                              └─ relay coil, fan
ESP32 ──8-bit 8080 (D0-7, WR, DC, CS, RST), 33 Ω series──> SSD1963 ──24-bit RGB + PCLK/HS/VS/DE──> 40-pin FPC ──> 7" panel
ESP32 ──I2C 400 kHz (2.2k pull-ups)──> ADS1115 (0x48) + GT911 (0x5D)
```

Sheets: `3dFilamentDryer.kicad_sch` (root: mains, triac, ZCD, MCU, fan), `Rev3_Display.kicad_sch`, `Rev3_Thermocouple.kicad_sch`, `Rev3_Power.kicad_sch`, `Rev3_InputFilter.kicad_sch`. Custom symbols/footprints: `KiCad/ComponentsLibrary/User Created/Rev3/` (SSD1963QL9, MIC2288YD5, 40-pin TFT FPC, 6-pin CTP FPC, L40 and C40 footprints).

## 4. ESP32 GPIO map (Rev3.0)

| Signal | GPIO | Notes |
|--------|------|-------|
| LCD_D0..D7 | IO16, IO17, IO18, IO19, IO21, IO22, IO23, IO25 | all < 32 for the TFT_eSPI/LovyanGFX fast parallel path |
| LCD_WR | IO26 | 8080 write strobe |
| LCD_DC | IO27 | data/command |
| LCD_CS | IO5 | strap pin, idles high — OK |
| LCD_RST | IO14 | shared with GT911 RST |
| LCD_RD | — | SSD1963 RD# pulled to 3V3 (R124); no read-back |
| I2C_SDA / I2C_SCL | IO4 / IO15 | IO15 is a strap pin; SCL idles high through the pull-up — OK |
| TP_INT | IO32 | driven low during reset → GT911 address 0x5D |
| ADC_RDY | IO35 (input only) | ADS1115 ALERT/RDY, 10k pull-up (R224) |
| TRIG / ZCD / FAN | IO33 / IO34 / IO13 | unchanged from Rev2.1 |
| BOOT, TXD0/RXD0 | IO0, IO1/IO3 | unchanged |
| spare | IO2 (status LED), IO12 (NC — MTDI strap) | |

Backlight brightness is driven by the SSD1963 PWM pin (no ESP32 pin used).

## 5. Display subsystem

- Panel: 800x480, 24-bit RGB stripe, DE mode, PCLK typ 33.3 MHz (max 50), H total 1056 (HBP 46, HFP 210, HPW 1-40), V total 525 (VBP 23, VFP 22, VPW 1-20), VDD 3.0-3.6 V (panel generates AVDD/VGH/VGL internally). Backlight: 3 LEDs in series × 7 strings, 9.6 V typ (8.7-10.5 V), 140 mA typ (105-175).
- SSD1963: 8080 mode (CONF = 3V3), CS#/D/C#/WR#/RESET# from ESP32, RD# pulled up, D8-D23 open, TE open, CLK = GND, 10 MHz crystal with 27 pF load caps (CX3225GB CL = 18 pF: C = 2·(CL − Cstray≈3 pF) ≈ 30 pF → 27 pF). VDDD/VDDPLL = 1.2 V (U31), VDDIO/VDDLCD = 3.3 V. Decoupling 100 nF per 2-3 supply pins + 1 µF at VDDPLL + 10 µF bulk.
- Pixel path: 16-bit RGB565 packed over the 8-bit bus (SSD1963 command 0xF0 = 0x03), frame buffer → 24-bit RGB output (LDATA23..16 = R, 15..8 = G, 7..0 = B).
- Bus speed: TFT_eSPI 8-bit parallel on ESP32 strobes at roughly 10-20 MHz; a full 800x480x16-bit frame is 768 kB → 40-80 ms; LVGL partial redraws make the UI responsive.
- Touch: GT911 over I2C (0x5D), INT = IO32, RST = LCD_RST, 3.3 V, 5-point.
- Backlight: MIC2288 boost, FB = 1.24 V across R122‖R123 (2 × 18 Ω 0805 → 9 Ω) → 138 mA; D114 15 V zener clamps the output if the LED string opens; EN from SSD1963 PWM through R128 (0 Ω) with 100k pull-down (backlight off until the controller is configured). PWM dimming runs at ≈26 kHz (SSD1963 prescaler 0x0E at 100 MHz PLL) so the 0.32 A input-current steps stay above the audio band and the LISN measurement band start. Boost input: pi-filter C127 10 µF | L12 2.2 µH | C124 10 µF with an R132 0.5 Ω + C128 47 µF damper (an undamped pi-filter rings at 33 kHz and is worse than none); 1.2 MHz ripple on the 5 V rail < 0.01 mV pp.

## 6. Thermocouple front end

- K-type thermocouple on J20 (DEGSON 5.08 mm). R220/R221 1 kΩ 0.1 % + C220 100 nF differential (fc = 758 Hz) and C221/C222 10 nF C0G 1 % common-mode (fc = 15.9 kHz); −42 dB at 100 kHz, −50 dB at 250 kHz (SPICE, see EMI report §3.3). D220/D221 bidirectional 5 V TVS to ground.
- Bias: R222 10 MΩ to 3V3 and R223 10 MΩ to GND, connected on the **terminal side** of the 1 kΩ resistors so the bias current does not develop an offset across them (0.04 °C error, versus 8 °C if placed after the 1 kΩ). With the probe open the input is pulled to the rails and the ADC reads about +113 mV (14,430 LSB, far outside the K-type range) → firmware reports NAN (same behaviour as the MAX6675 open-TC flag).
- 50 Hz common mode: 1 V CM with 10 % mismatch of C221/C222 leaves 628 µV pp before the ADC and 15 µV pp after the 16 SPS sinc filter — use 16 SPS, not 32 (32 SPS leaves 123 µV).
- ADS1115: AIN0−AIN1 differential, PGA ±256 mV → 7.8 µV/LSB = 0.19 °C/LSB for K-type (41 µV/°C); 16 SPS with 1 s averaging gives ≈0.05 °C rms resolution. Range: ±256 mV covers −200 °C … >1000 °C. ADDR = GND (0x48), ALERT/RDY → IO35.
- Cold junction: TH220 10 kΩ NTC (B25/50 = 3380 K) with R225 10 kΩ 0.1 % on AIN2, read ratiometrically against the R226/R227 half-supply divider on AIN3 so the 3.3 V tolerance cancels. Place TH220 touching the J20 terminal block metal.
- Conversion in firmware: NIST ITS-90 inverse polynomials for type K (both ranges) + CJC.

## 7. Power

| Rail | Source | Load (peak) | Notes |
|------|--------|-------------|-------|
| 5 V | HLK-10M05 10 W | ≈5.5 W: backlight 1.6 W (incl. boost loss), 3V3 rail 3 W input, relay 0.36 W, fan up to 1.5 W | 2× margin vs. HLK-PM01 (3 W) |
| 3.3 V | TPS562201, 580 kHz, L30 4.7 µH, 2 × 22 µF out, 2 × 10 µF in, VBST 100 nF, FB 33.2k/10k → 3.32 V | ≈0.9 A: ESP32 Wi-Fi 0.5 A, SSD1963 I/O + panel 0.15 A, GT911/ADS1115 0.03 A, 1V2 rail 0.07 A | ~90 % efficient, ≈0.3 W loss |
| 1.2 V | LD1117S12 from 3.3 V, 10 µF + 1 µF out | ≈60 mA (SSD1963 core at 100-110 MHz PLL) | 0.13 W loss |
| 9.6 V | MIC2288 boost from 5 V, 10 µH, SS14, 4.7 µF/25 V | 138 mA | ≈85 % efficient, Iin ≈ 0.32 A |

## 8. EMC design measures (summary — `EMI_Signal_Integrity_Analysis.md` has the formulas, ngspice results and plots)

Simulation engine: ngspice 46 (KiCad's shared library) through PySpice; analytic parts in numpy. Key results:

| Item | Result |
|------|--------|
| 8080 bus, unterminated, 105/130 Ω 2-layer trace | receiver peaks 4.29/4.49 V and −0.99/−1.19 V — above the SSD1963 3.8 V absolute maximum |
| 8080 bus with 33 Ω series | peaks 3.51/3.69 V, ring-back margin to VIH 0.6 V, receiver edge 1.4 ns (2.0 ns on a 55 Ω 4-layer trace); 22 Ω under-damps, 47 Ω over-damps |
| Driver-current harmonics, 33 Ω vs 0 Ω | −0.9/−4.2/−5.1 dB at 100/200/300 MHz: the resistor is a small lever; the ground return and loop area dominate (10 nH return detour = +26 dB common mode, 4-layer = −17 dB differential mode) |
| Radiated estimate at 3 m, nine lines in phase | 2-layer DM 47-52 dBµV/m vs 40/47 dBµV/m Class B limit; 4-layer 29-34 dBµV/m; CM 51-56 dBµV/m with a solid plane → the 4-layer stackup with an unbroken L2 ground is the recommended build |
| I2C 400 kHz, 100 pF | 2.2 kΩ: tr = 186 ns (limit 300 ns); 4.7 kΩ fails (398 ns); allowed window 0.97-3.5 kΩ |
| Thermocouple filter | f_dm 758 Hz, f_cm 15.9 kHz, −42 dB at 100 kHz; resolution 0.19 °C/LSB, 0.09 °C rms per sample, 0.02 °C rms after 1 s at 16 SPS |
| Buck ripple | 1.9 mV pp (2 × 22 µF), 2.9 mV derated |
| Boost input | ΔI_L 0.2 A pp, I_in 0.32 A; damped pi-filter leaves <0.01 mV at 1.2 MHz on the 5 V rail |

Design rules carried into the schematic and to be followed in layout:

1. 33 Ω series resistors (R110-R121) on every ESP32→SSD1963 bus line, placed at the ESP32 pins (source termination of the ~35 Ω driver); bus length ≤ 80 mm (tr/4 boundary for a 2 ns edge); solid ground plane under the bus with no splits; one return via next to each signal via.
2. I2C at 400 kHz with 2.2 kΩ pull-ups and TVS on SDA/SCL at the touch FPC.
3. Thermocouple input as a tightly coupled pair with RC filtering and TVS at the terminal; analog ground at U20 only; keep ≥10 mm from the triac/heater wiring and the LCD bus; L40 (unshielded) away from the thermocouple input.
4. Mains: existing X2 100 nF + MOV + common-mode choke, plus the new 120 µH / 1 µF X2 differential stage (pi-filter with C1, fc ≈ 14.5 kHz, ≈26 dB at the HLK-10M05 switching fundamental).
5. Switching converters: short SW loops (C330/C331 at VIN, L30-C333/C334 tight; L11-D111-C125 tight), no copper under L30/L11 on inner layers, 100 nF + 10 µF per SSD1963 supply group, crystal with ground guard.
6. SSD1963 RGB output to the panel: 20-40 mm on-board + 50 mm FPC at 33 MHz; keep PCLK away from board edges, route over ground, connector placed so the FPC does not cross the mains section.
7. Recommended stackup: 4-layer (sig/GND/PWR/sig) with 0.2 mm prepreg gives ≈55 Ω microstrip and halves loop areas; 2-layer is possible with a continuous bottom ground pour under all digital traces.

## 9. 85 °C ambient rating — exceptions and notes

- SATOZ panel: operating −20..+70 °C (storage +80 °C). The display must be mounted outside the heated enclosure airflow; this is an accepted exception.
- HLK-10M05: distributor data (JLCPCB/LCSC, Tinytronics, Makers Electronics) gives −25..+60 °C operating, −40..+85 °C storage; the official Hi-Link PDF could not be fetched, so confirm the derating curve. The previous HLK-PM01 had the same class of rating. An 85 °C-rated discrete flyback was rejected as a separate project.
- TPS562201, LD1117, MIC2288, ADS1115, SSD1963, ESP32, crystal, TVS, connectors (−40..+105), NTC, X2 cap (+125) are all ≥85 °C rated. Use X7R/X5R ceramics rated ≥25 V for 100 nF and ≥10 V for 10/22 µF; 0402 resistors 1 % thick film.

## 10. Open items before PCB layout

1. **FPC contact side**: DS1020-09-xxVBT1A are bottom-contact connectors; confirm against the panel and CTP FPC drawings (the FPC exposed-contact side). Upper-contact alternatives in stock: KLS L-KLS1-1242E-2.0-40-T-UR (40p), AMTEK 5FP4AMRUD-40T0WUT-01.
2. Footprint placeholders to verify against the vendor drawings: L30 (SRI0605B on a Bourns SRN6045 pad set), L11 (PCD0403 on a Taiyo-Yuden NR-40xx pad set), J10/J11 (TE 1734839 pad set for the Connfly DS1020-09 — same 0.5 mm pitch, check the mechanical pads), J20 (Phoenix MKDS 1,5/2-5.08 pad set for DEGSON DG127H), L40/C40 custom footprints generated from Özdisan dimensions.
3. ~~MIC2288 pin assignment~~ Verified against Microchip DS20006034C (copied to `Datasheets/MIC2288.pdf`): TSOT23-5 pins 1 SW, 2 GND, 3 FB (1.24 V ±1 %), 4 EN (on ≥1.5 V, off ≤0.4 V, must not float — R127 100k pull-down), 5 VIN (2.5-10 V); switch limit 1.2 A, 1.2 MHz, TJ −40..+125 °C. Schematic symbol matches.
4. PCB layout: the Rev2.1 PCB (162.5 × 47 mm) is not reused — new board outline sized to the 165 × 100 mm panel, controller near the FPC connector, mains section separated. Import the new netlist into a fresh layout.
5. Firmware (ported, compiled, **not flashed or bench-tested**): `AnnealerFirmware.ino.ino` v3.0.0 with `Display_SSD1963.h` (PLL 100 MHz, PCLK 33.3 MHz, panel timing per §5, 0xBE brightness), `Thermocouple_ADS1115.h` (non-blocking ADS1115 state machine, NIST ITS-90 type-K, ratiometric NTC CJC matching the schematic: NTC to 3V3, R225 to GND, AIN3 = half rail), `User_Setup_Rev3.h` (TFT_eSPI 2.5.44 SSD1963_800 8-bit parallel; must be installed as the TFT_eSPI user setup for IDE builds). Libraries: TFT_eSPI 2.5.44, lvgl 8.4.0, TAMC_GT911 1.0.2, Adafruit ADS1X15 2.6.2. Compiled with the Arduino IDE's arduino-cli for `esp32:esp32:esp32` (16 MB, app3M_fat9M_16MB partition): 1,580,980 B flash (50 %), 67,888 B RAM. UI is the 320x240 layout scaled 2.5×/2× with the existing Inter fonts (first pass, not redesigned); touch orientation (TOUCH_SWAP_XY/FLIP) and SSD1963 colour order need checking on hardware; display reset is driven once through the GT911 init on IO14 and then by SSD1963 software reset.
6. Footprints for the pi-filter parts (L12 4x4 mm inductor pad set, C128 5 mm electrolytic) are placeholders until the MPNs are chosen.

## 11. Files in this folder

- `Rev3.0_Schematic.pdf` — all 5 sheets
- `Rev3.0_BOM.csv` — grouped BOM with MPN / manufacturer / Özdisan link
- `Rev3.0_netlist.net` — KiCad netlist (for the new PCB)
- `Rev3.0_ERC.rpt` — ERC report (0 errors; 3 pre-existing library warnings)
- `EMI_Signal_Integrity_Analysis.md` + `sim/` — formulas, ngspice/PySpice scripts, JSON results, 11 plots, 24 layout rules, pre-compliance test plan (near-field scan points, LISN conducted, radiated bands, EN 61000-4-x)
- `tools/gen_rev3.py` — regenerates the Rev3 sheets and patches the root from the Rev2.1 root in git (re-run instead of hand-editing when changing the structure)
