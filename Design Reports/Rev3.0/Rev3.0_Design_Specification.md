# 3D Printer Filament Dryer / Print Annealer — Hardware Rev3.0 Design Specification

Date: 2026-11-09  ·  Branch: `Rev3.0`  ·  Author: generated with Claude for M. Ömer Karaoğlu (READARK)

## 1. Scope of Rev3.0

| # | Change | Why |
|---|--------|-----|
| 1 | Display changed from 2.8"/3.2" ILI9341 SPI header to **SATOZ SAT70AT40D21-33KN-CTP-V1** (7", 800x480, 24-bit TTL RGB, capacitive touch) | Requested |
| 2 | **SSD1963QL9** display controller added on the PCB (8-bit 8080 bus from the ESP32, 1215 KB frame buffer, RGB timing generator) | The panel has no controller of its own; the ESP32-WROOM-32E cannot generate RGB timing; every ESP32-S3 module is out of stock at Özdisan, so the MCU was kept |
| 3 | MAX6675 header module removed; **ADS1115IDGSR** 16-bit ADC thermocouple front end built from SMD parts, K-type thermocouple on a 5.08 mm screw terminal, NTC cold-junction sensor | Requested |
| 4 | Power: **HLK-10M05** (5 V / 2 A) replaces HLK-PM01; **TPS562201** buck replaces the TLV1117-33 LDO; **LD1117S12** added for the SSD1963 1.2 V core; **MIC2288** boost LED driver for the backlight | 7" backlight (1.35 W) and the display controller push the 5 V budget to ~5.5 W and the 3.3 V load to ~0.9 A; an LDO would dissipate ~1.5 W at 85 °C ambient |
| 5 | Mains input EMC stage **L40 + C42P2105KBSC400 (1 µF X2)** as the main filter at the mains input (L40 = Core Master RC1415U-101K 100 µH / 5 A since pass 3; the IND-120UH-THT of the built unit has no published current rating): LINE → F3 (8 A main fuse) → L40 → LINE_FILT feeds the triac, the fan relay and, through F1 (1 A), the common-mode choke L1 and the PSU (pass 3, 2026-11-12; passes 1–2 wrongly had it on the PSU branch only) | Requested (filter existed in the earlier design but was not on the board; the choke carries the heater current) |
| 6 | 33 Ω series terminations on all ESP32→SSD1963 bus lines, 2.2 kΩ I2C pull-ups, ESD/TVS on the thermocouple and touch lines, LC pi-filter on mains | EMC (CISPR 32 Class B target) |
| 7 | ESP32 module part number changed to **ESP32-WROOM-32E-N16** | -N4 has 0 stock at Özdisan, -N16 has 1,213 |

Unchanged: mains fuses/MOVs/snubber, MOC3053 triac driver (the BTA12 triac became a BTA24-800CWRG on a solder-pin heatsink in layout pass 2, §7.1), 4N28 zero-cross detector, SRD-05 fan relay, FTDI/auto-boot circuit, ESP32 pin usage for TRIG (IO33), ZCD (IO34) and FAN (IO13).

## 2. Sourcing (Özdisan, prices at qty 1 excl. VAT, 2026-11-09, ≈50 TRY/USD)

All new main components were checked on ozdisan.com for stock and operating temperature. Every IC is rated to at least +85 °C; the only exceptions to the 85 °C ambient target are listed in §9.

| Ref | Part (MPN) | Function | Stock | Price | Temp |
|-----|-----------|----------|------:|------:|------|
| U3 | ESP32-WROOM-32E-N16 | MCU, 16 MB flash | 1,213 | ₺256 / $5.1 | -40..+85 |
| U10 | SSD1963QL9 (Solomon, LQFP-128 0.4 mm) | TFT controller | 279 | ₺303 / $6.1 | -40..+85 |
| J10 panel | SAT70AT40D21-33KN-CTP-V1 (SATOZ) | 7" 800x480 RGB + GT911 CTP | 61 | ₺1,990 / $39.7 | -20..+70 (!) |
| J10 | DS1020-09-40VBT1A (Connfly, 40p 0.5 mm, lower contact — confirmed from the panel drawing, §12.3) | panel FPC connector | 31,182 | ₺20 | -40..+105 |
| J11 | DS1020-09-06VBT1A (Connfly, 6p 0.5 mm, lower contact — confirmed from the CTP drawing) | touch FPC connector | 1,918 | ₺11 | -40..+105 |
| Q1 | BTA24-800CWRG (ST, insulated TO-220AB, 25 A / 800 V, IGT 35 mA, Rth(j-c) 1.7 K/W) | heater triac (1 kW = 4.35 A RMS) | 5,449 | ₺58 | -40..+125 |
| HS1 | SK 409 63,5 STC (Fischer Elektronik, 45 × 12.7 × 63.5 mm, 5.6 K/W, solder pins) — **DigiKey** 5496-SK40963,5STCTO220-ND (995 pcs, $2.60, min. 5), not stocked by Özdisan | triac heatsink | 995 (DigiKey) | $2.6 | — |
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
| L40 | RC1415U-101K (Core Master, radial 100 µH ±10 %, 5 A, 100 mΩ, Ø16.5 × 17 mm, P7.5) — pass 3; was IND-120UH-THT (no rating published) | mains filter choke, carries the heater current | 613 | ₺43.6 / $0.87 | — |
| C40 | C42P2105KBSC400 (Faratronic 1 µF 275 VAC X2, P27.5) | mains filter cap | 57,151 | ₺12 | -40..+125 |
| L12, C127/C124, R132, C128 | 2.2 µH ≥1 A SMD, 2 × 10 µF, 0.5 Ω 1206, 47 µF 10 V | backlight boost input pi-filter + damper (added from the EMI analysis) | commodity values; pick in-stock MPNs at Özdisan (Viking PCD0403 / Core Master FPI0403S 2.2 µH, Koshin 47 µF) | — | — |
| R220/R221, C221/C222 | 1 kΩ 0.1 % 0603, 10 nF C0G 1 % 0603 | thermocouple filter precision parts (EMI analysis: common-mode rejection depends on their matching) | commodity | — | — |

Not available / rejected: MAX31855, MAX31856, MCP9600, ADS1118 (not stocked); OPA333/OPA2333 (0 stock); every ESP32-S3 variant (0 stock, order on request); TMP235/LMT86 (0 stock); SSD1963-based Winstar 7" modules (in stock but ≈$95); UART HMI modules (thin stock, UI rewrite).

## 3. Architecture

```
mains ─ F3 8A ─ [L40 100µH 5A ─ C40 1µF X2 / C1 / RV1] ─┬─ Q1 triac ─ heater 1 kW
                                                   ├─ K1 relay ─ fan
                                                   └─ F1 1A ─ L1(CMC) ─ PS1 HLK-10M05 ─ 5V ─┬─ U30 TPS562201 ─ 3V3 ─┬─ ESP32 / ADS1115 / GT911
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
| LCD_D0..D7 | IO16, IO14, IO27, IO26, IO25, IO21, IO22, IO23 | all < 32 for the TFT_eSPI/LovyanGFX fast parallel path; order chosen by the PCB routing so the bus is planar (see §12), the 33 Ω resistors stay at the module pins |
| LCD_WR | IO19 | 8080 write strobe |
| LCD_DC | IO18 | data/command |
| LCD_CS | IO5 | strap pin, idles high — OK |
| LCD_RST | IO17 | shared with GT911 RST |
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
- Pixel path: 16-bit RGB565 packed over the 8-bit bus (SSD1963 command 0xF0 = 0x03), frame buffer → 24-bit RGB output. On the PCB the SSD1963 LDATA23..16 lanes go to the panel's B7..B0 pins and LDATA7..0 to R7..R0 (crossed so every RGB line routes with one via); set_address_mode (0x36) bit 3 = 1 (TFT_eSPI `TFT_RGB_ORDER TFT_BGR`) puts red back on the panel's R pins — confirm on hardware.
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

### 7.1 Heater triac thermal design (layout pass 2, 2026-11-11)

Heater 1 kW at 230 V → 4.35 A RMS, worst case 100 % conduction (burst firing through the MOC3053). Triac conduction loss
P = Vt0 · Iavg + Rd · Irms² with Iavg = 0.9 · Irms (full sine), datasheet maxima at Tj = 125 °C:

| Triac (insulated TO-220) | Vt0 / Rd | P at 4.35 A | Rth(j-c) | Tj at 85 °C ambient on HS1 | Tj at 60 °C |
|---|---|---|---|---|---|
| BTA12-600BW (Rev2.1 / pass 1) | 0.85 V / 35 mΩ | 4.0 W | 2.3 K/W | 126 °C (over the 125 °C limit) | 101 °C |
| **BTA24-800CWRG (chosen)** | 0.85 V / 20 mΩ (VTM 1.55 V at 35 A) | 3.7 W | 1.7 K/W | **121 °C** | **96 °C** |

Heatsink: Fischer **SK 409 63,5 STC** (HS1) — 45 × 12.7 mm profile standing 63.5 mm tall on two Ø2.3 mm solder pins 35.5 mm
apart, TO-220 clip- or M3-mounted on the 3 mm plate, black anodised, natural convection, 5.6 K/W at the catalogue 80 K rise
(DigiKey: 14.29 W at 80 °C rise); at our ≈ 26 K rise natural convection is weaker, Rth ≈ 5.6 · (80/26)^0.25 ≈ 7.4 K/W is used
above together with 0.5 K/W case-to-sink (thermal pad + clip). Rejected: Fischer SK 104 25.4/38.1/50.8/63.5 STS (14/11/9/8 K/W,
too warm for 85 °C), Boyd 577202B00000G (24 K/W), Boyd 530002B02500G (2.6 K/W but 63 × 42 × 25 mm), SK 129 (no solder-pin 63.5 mm
variant found). The heatsink is floating metal on the triac's 2500 V RMS insulated tab; its pins keep 2.5 mm from mains and 6.4 mm
from SELV copper (`heatsink_pins_*` rules). Gate drive is unchanged (MOC3053 + 360 Ω: ≥ 35 mA gate current above ≈ 15 V
instantaneous; IH 50 mA / IL 80 mA are far below the 4.35 A load). F3 (8 A, 5 × 20) and the 2.5 mm heater tracks (≈ 6.3 A at 20 K)
are unchanged. Values for the ST part are taken from the ST datasheet table as reproduced by second sources (st.com could not be
fetched); confirm Vt0/Rd on the ST PDF when it is available.

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

## 9. Ambient rating: 60 °C declared, 85 °C design target

**Decision (2026-11-11):** the board is **declared for 0..60 °C ambient** because the HLK-10M05 module is rated −25..+60 °C and the panel +70 °C; every other part, the copper widths, the isolation and the triac heatsink are nevertheless designed for 85 °C so that only the PSU module limits the rating.

- SATOZ panel: operating −20..+70 °C (storage +80 °C). The display must be mounted outside the heated enclosure airflow; this is an accepted exception.
- HLK-10M05: distributor data (JLCPCB/LCSC, Tinytronics, Makers Electronics) gives −25..+60 °C operating, −40..+85 °C storage; the official Hi-Link PDF could not be fetched, so confirm the derating curve. The previous HLK-PM01 had the same class of rating. An 85 °C-rated discrete flyback was rejected as a separate project.
- TPS562201, LD1117, MIC2288, ADS1115, SSD1963, ESP32, crystal, TVS, connectors (−40..+105), NTC, X2 cap (+125) are all ≥85 °C rated. Use X7R/X5R ceramics rated ≥25 V for 100 nF and ≥10 V for 10/22 µF; 0402 resistors 1 % thick film.

## 10. Open items before PCB layout

1. ~~FPC contact side~~ Resolved 2026-11-11 from the drawings: the SAT sheet shows a front view (active area) and a back view (barcode); the 40-pin tail's fingers are drawn in the front view (Section C) and the CTP's in its front view (Detail A, steel stiffener on the back), so after the 180° fold both contact faces point at the PCB → **lower-contact** connectors (as bought). Positions in board coordinates (back view): TFT tail x 125.4–145.9 mm, pin 1 right; CTP tail x ≈ 40 mm, pin 1 right; both at the bottom edge. (Upper-contact alternatives if ever needed: DS1020-09-40VBT1B 233 pcs, KLS L-KLS1-1242E-2.0-40-T-UR, AMTEK 5FP4AMRUD-40T0WUT-01.)
2. Footprint placeholders to verify against the vendor drawings: L30 (SRI0605B on a Bourns SRN6045 pad set), L11 (PCD0403 on a Taiyo-Yuden NR-40xx pad set), J10/J11 (TE 1734839 pad set for the Connfly DS1020-09 — same 0.5 mm pitch, check the mechanical pads), J20 (Phoenix MKDS 1,5/2-5.08 pad set for DEGSON DG127H), L40/C40 custom footprints generated from Özdisan dimensions. — Pass 1 replaced these with footprints from the vendor drawings (Connfly DS1020-09, Core Master SRI0605B, Viking PCD0403, DEGSON DG127 family drawing via the DigiKey/Suntsu listing: Ø1.3 holes at 5.08 mm, body 10.7 × 8.1 × 10 mm — corrected 2026-11-13 from the DEGSON DG127H-5.08 drawing: the H version is 19.1 mm tall, 8.6 mm deep, pins 3.5 mm; Özdisan's figure was right and the 10 mm body is the low DG127; the 1.3 mm drill / 5.08 pitch footprint is right either way). SRI0605B-4R7M is not in Core Master's table (2.2 → 6.8 µH); Özdisan lists it as 4.7 µH ±20 %, 4 A, 70 mΩ (interpolated 3.4 A / 66 mΩ), adequate for the 1 A buck.
3. ~~MIC2288 pin assignment~~ Verified against Microchip DS20006034C (copied to `Datasheets/MIC2288.pdf`): TSOT23-5 pins 1 SW, 2 GND, 3 FB (1.24 V ±1 %), 4 EN (on ≥1.5 V, off ≤0.4 V, must not float — R127 100k pull-down), 5 VIN (2.5-10 V); switch limit 1.2 A, 1.2 MHz, TJ −40..+125 °C. Schematic symbol matches.
4. PCB layout: the Rev2.1 PCB (162.5 × 47 mm) is not reused — new board outline sized to the 165 × 100 mm panel, controller near the FPC connector, mains section separated. Import the new netlist into a fresh layout.
5. Firmware (ported, compiled, **not flashed or bench-tested**): `AnnealerFirmware.ino.ino` v3.0.0 with `Display_SSD1963.h` (PLL 100 MHz, PCLK 33.3 MHz, panel timing per §5, 0xBE brightness), `Thermocouple_ADS1115.h` (non-blocking ADS1115 state machine, NIST ITS-90 type-K, ratiometric NTC CJC matching the schematic: NTC to 3V3, R225 to GND, AIN3 = half rail), `User_Setup_Rev3.h` (TFT_eSPI 2.5.44 SSD1963_800 8-bit parallel; must be installed as the TFT_eSPI user setup for IDE builds). Libraries: TFT_eSPI 2.5.44, lvgl 8.4.0, TAMC_GT911 1.0.2, Adafruit ADS1X15 2.6.2. Compiled with the Arduino IDE's arduino-cli for `esp32:esp32:esp32` (16 MB, app3M_fat9M_16MB partition): 1,580,980 B flash (50 %), 67,888 B RAM. UI is the 320x240 layout scaled 2.5×/2× with the existing Inter fonts (first pass, not redesigned); touch orientation (TOUCH_SWAP_XY/FLIP) and SSD1963 colour order need checking on hardware; display reset is driven once through the GT911 init on IO17 and then by SSD1963 software reset. Pin defines updated for the §12 layout remap on 2026-11-10 (not recompiled since). **Deferred firmware change, decided 2026-11-12 (will be done):** replace the per-cycle sigma-delta heater firing by a 20 s burst frame with error carry (1000 mains cycles; at frame start `acc += sd_increment*1000; n_on = acc>>16; acc &= 0xFFFF`; fire for `cyc < n_on`), keep the 230 µs delay / 150 µs gate pulse / both-zero-crossing firing, retune the PID for the 20 s hold and average the thermocouple over the frame — required for IEC 61000-3-3 flicker (current pattern P_st 1.70, new 0.54; `EMC_PostLayout_Assessment.md` F2).
6. Footprints for the pi-filter parts (L12 4x4 mm inductor pad set, C128 5 mm electrolytic) are placeholders until the MPNs are chosen.

## 11. Files in this folder

- `Rev3.0_Schematic.pdf` — all 5 sheets
- `Rev3.0_BOM.csv` — grouped BOM with MPN / manufacturer / Özdisan link
- `Rev3.0_netlist.net` — KiCad netlist (for the new PCB)
- `Rev3.0_ERC.rpt` — ERC report (0 errors; 3 pre-existing library warnings)
- `EMI_Signal_Integrity_Analysis.md` + `sim/` — formulas, ngspice/PySpice scripts, JSON results, 11 plots, 24 layout rules, pre-compliance test plan (near-field scan points, LISN conducted, radiated bands, EN 61000-4-x)
- `tools/gen_rev3.py` — regenerates the Rev3 sheets and patches the root from the Rev2.1 root in git (re-run instead of hand-editing when changing the structure)
- `Rev3.0_CPL.csv` — pick-and-place (both sides, mm, from the Rev3.0 board)
- `EMC_Scorecard_Decided_Design.pdf` — pass/fail scorecard of the decided configuration only (pass-4 hardware + 20 s burst-frame firmware; `sim/emc/make_decided_pdf.py`)
- `Rev3.0_BOM_Ozdisan_100pcs.md` / `.csv` — BOM with Özdisan stock, MOQ and USD tiers read 2026-11-12, 100-board unit cost (≈ 29.3 USD/board without PCB, panel and probe), substitutions for the lines Özdisan does not stock, thermocouple probe choice (`tools/make_bom_ozdisan.py` + `tools/bom_ozdisan_input.json`; rerun with the board count as argument). Schematic follow-ups from the substitutions (all applied in the 2026-11-13 tidy round, §12.7): R4 200 Ω → 120 Ω because U5 is now the MOC3052 (R4 is the opto LED resistor; R9 stays 180 Ω); L12 = 10 µH PCD0403MT100 (same footprint as L11); K1 = Tianbo HJR-3FF-S-Z (SRD footprint); Q2/Q3 = MMBT4401; fuse clips (4×) as a BOM line with a note at F3.
- `EMC_Simulation_Results.pdf` — the simulation results as a report (built by `sim/emc/make_emc_pdf.py` from the JSON results and plots)
- `EMC_PostLayout_Assessment.md` + `sim/emc/` — post-layout EMC assessment against EN 55014-1/-2, IEC 61000-3-2/-3-3 (conducted/radiated estimates, IEC 61000-4-15 flickermeter model, test plan, open items)
- `tools/pcb/` — PCB layout generator and hand-routing scripts (see §12 and its README; pass 2: `sch_pass2.py`, `gen_heatsink_fp.py`, `placement_override_*.py`, `mains2_check.py`, `PASS2_BRIEF.md`); the design rules live in `KiCad/3dFilamentDryer/3dFilamentDryer.kicad_dru` + the net classes in the `.kicad_pro`

## 12. PCB layout note (Rev3.0, pass 1 2026-11-10, pass 2 2026-11-11, passes 3 and 4 2026-11-12)

Board file: `KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb` (the Rev2.1 board is kept as `3dFilamentDryer_Rev2.1.kicad_pcb`). The board was generated from the schematic netlist by the scripts in `tools/pcb/` (placement, planes and rules by script; every track written by hand-routing scripts, one per region, in the style of the Battery Sentinel layout: fan-out with reserved exits, 0/45/90° only, 90° turns as two 45°s, track ends at pad centres). Re-run the scripts rather than hand-editing when the placement changes (see `tools/pcb/README.md`). **Pass 2 (2026-11-11)** re-placed and re-routed three regions for the connector positions read from the panel drawings, the 1 kW heater's triac + heatsink and the moved LV power block; the ESP32 / 8080 bus / thermocouple / relay / mains-input-filter regions are unchanged from pass 1.

### 12.1 Outline, stackup, fabrication class

- Outline 164 × 99 mm, sits behind the 164.9 × 100 mm SATOZ panel; four M3 holes (Ø3.2 mm) at (4, 4), (4, 95), (160, 95) and (97, 95.5) mm from the top-left corner (none in the mains band). Coordinates below are from the top-left corner, x right, y down.
- 4-layer, 1.6 mm FR4, 35 µm copper on all layers, ENIG: **F.Cu signal / In1 solid GND / In2 3V3 power (+5 V island under the PSU DC pins, buck and boost) / B.Cu signal**. Prepreg 0.2 mm (εr 4.4) between F.Cu–In1 and In2–B.Cu, 1.0 mm core. Microstrip 0.25 mm over the 0.2 mm prepreg ≈ 59 Ω (Hammerstad, EMI report §2.1); 0.30 mm ≈ 54 Ω. Bus and RGB traces are 0.25 mm (the bus is necked to 0.20 mm at 0.35 mm pitch for its first 15 mm past the FTDI header).
- IPC references: conductor spacing per IPC-2221B table 6-1 (B2 external uncoated, 301–500 Vpk → 2.5 mm between mains conductors; 6.4 mm reinforced insulation mains↔SELV per IEC 62368-1 at 250 Vrms, PD2, material group IIIb); current-carrying widths per IPC-2152/2221 for 1 oz copper and ≤ 20 K rise at 85 °C ambient; land patterns per the vendor drawings / IPC-7351 nominal density; annular rings per IPC-6012 class 2 (vias 0.6/0.3 mm signal, 0.9/0.45 mm power, 1.2/0.6 mm mains; THT pads ≥ 0.5 mm larger than the drill).
- Design rules (`3dFilamentDryer.kicad_pro` net classes + `3dFilamentDryer.kicad_dru`): Default 0.2 mm clearance / 0.25 mm track; Bus 0.15/0.25; TC 0.25/0.3; Power 0.2/1.0; P1V2 0.2/0.25; Mains 2.5/1.0; MainsHeater 2.5/2.5. Rule exceptions are limited to component-inherent pin spacing (BTA24 TO-220 2.54 mm, 4N28/MOC3053 DIP-6, SRD-05 relay coil-to-COM 6.3 mm, the D1-A/D2-K bridge pair that differs by one diode drop, and the same-potential L and N chains across the fuse, choke and filter at 1.0 mm) and to the 0.13 mm escapes at the LQFP-128 (0.4 mm) and TSSOP-10 (0.5 mm) pads. Edge clearance 0.5 mm (1.0 mm for mains), hole-to-hole 0.5 mm. Pass 2 adds the heatsink rules `heatsink_pins_vs_mains(_creepage)` (2.5 mm) and `heatsink_pins_vs_selv(_creepage)` (6.4 mm) for the HS1 solder pins — KiCad evaluates creepage per net pair, so the two HS1 pin nets are named explicitly and excluded from the generic 6.4 mm mains↔SELV creepage rule — and `q1_on_heatsink_courtyard` (severity ignore: the BTA24's courtyard lies inside the heatsink's by design).

### 12.2 Isolation (230 VAC ↔ SELV)

- The mains section is the full-width band at the top of the board (y < 35.5 mm left of the relay, y < 56 mm under the relay, y < 55 mm under the ZCD/triac optocouplers, y < 60 mm under the PSU body at x > 130 mm — pass 2 moved this corner up from 80 mm so the In2 3V3 plane reaches the strip east of the +5 V island; the nearest mains copper there is the PSU AC pin row at y 45 mm and the AC/N track at y 49 mm) and is drawn on `Cmts.User`. No inner-layer copper exists under it, and the SELV GND/3V3 planes and pours stop ≥ 6.4 mm from any mains copper (KiCad `clearance` **and** `creepage` constraints, both 6.4 mm, checked by DRC).
- HLK-10M05 stands vertically on the right with its AC pins up in the mains band and its DC pins down in the SELV area, so the module itself bridges the boundary (42.5 mm pin-row spacing). The common-mode choke L1 and the 33 kΩ ZCD taps sit next to its AC pins.
- 1.2 × 12 mm slots under U1 (4N28) and U5 (MOC3053) between the pin rows; the creepage path around the slot ends is ≈ 8.9 mm (pad-to-pad air distance of the DIP-6 is 6.0 mm).
- The SRD-05 relay's coil pins are 6.3 mm from its COM contact by construction; only the two coil nets (+5V, D5-A) are allowed inside that radius (explicit rule), and the relay carries the reinforced insulation.
- Mains placement was iterated with a spacing checker (pass 1 `tools/pcb/mains_propcheck.py`, pass 2 `mains2_check.py`, which also models the heatsink as a 45 × 12.7 × 63.5 mm box and keeps every tall part ≥ 1 mm from it): heater loop (J3 → F3 → BTA24 → R1 pads) local to the triac, two parallel 2.5 mm trunks on B.Cu under the heatsink necked to 1.6 mm into the TO-220 pins (87 mm of heater copper in total; ≈ 6.3 A at 20 K rise, IPC-2221), gate loop Q1.G → R2 → U5 14 mm, bridge-rectifier ladder right of the heatsink next to U1; PSU branch 1.0 mm; no mains vias.
- **Heatsink (pass 2, §7.1):** Fischer SK 409 63,5 STC (HS1) at (112.75, 31.95) mm, standing 63.5 mm tall across the band with its two Ø2.3 mm solder pins 35.5 mm apart (footprint `Rev3:Heatsink_Fischer_SK409_63.5_STC`, F.Cu keep-out under the fins and the plate); the BTA24-800CWRG (Q1) sits on its plate at (110.21, 36.65) mm. The heatsink is floating metal on the triac's insulated tab (2500 V RMS), so its pins are kept 2.5 mm from mains copper (actual 2.58 mm to the A1 trunk) and 6.4 mm from SELV copper (DRC rules above). To make room, L1 moved up to y 16, J3/R1 moved 4.7 mm right, the snubber C4/RV2/R5 stood up in the column between the relay and the heatsink, RV1 stood up left of the relay (its NEUT run along y 27 is gone) and the D1–D4 ladder moved to x 137–147. Tall-part gaps to the heatsink envelope: L1 1.1 mm, PS1 2.95 mm, C40 7.8 mm, K1 12.3 mm. The C1 and L1 bodies overlap by ≈ 2.75 × 1.3 mm in plan (L1 has no courtyard; pass 1 already had this) — check at assembly.

### 12.3 Placement rationale

- ESP32-WROOM-32E at the left edge with the antenna hanging over the board edge; copper keep-out on all layers under and beside the antenna; the FTDI header J2 sits above it, the thermocouple block below.
- 33 Ω series resistors R110–R121 directly at the ESP32 pads (1.4 mm stubs) on both pin rows. **The 8080 pin order was re-assigned by the layout** so the bus is planar (no layer change on any of the 12 lines): the resistors stay at the module pins, only the functions moved — D0 = IO16, D1 = IO14, D2 = IO27, D3 = IO26, D4 = IO25, D5 = IO21, D6 = IO22, D7 = IO23, WR = IO19, DC = IO18, CS = IO5, RST = IO17 (also the GT911 reset). §4, the schematic and `User_Setup_Rev3.h` carry the new map. The top bundle runs east above the resistors and down at x ≥ 33 mm, the bottom bundle east into U10 pins 8–11; both over the unbroken In1 ground.
- SSD1963 (U10) centre-bottom: 10 MHz crystal and its 27 pF caps at pins 22/24 with the ground pour as guard and a GND via between the crystal's case pads; 100 nF per supply group pad-to-pin (C112, C114, C115, C116, C117, C119) plus 10 µF; GND and 3V3 pins fan inward to a via ring 2.3 mm inside the pad ring (In1/In2 planes); the 1.2 V pins are tied by a ring on B.Cu 3.3 mm inside the pads, fed by the LD1117-1.2 (U31) 0.5 mm track with C336/C337 on its tab. The four corner pins are power pins and connect outward.
- 40-pin and 6-pin Connfly FPC connectors (lower contact, §10 item 1) are on the **back** side at the bottom edge where the panel drawings put the tails: **J10 at x 135.65 mm** (TFT tail x 125.4–145.9, pin 1 east) and **J11 at x 40.3 mm** (CTP tail, pin 1 east). Pass 1 had them at x 53–72 / 79–84; pass 2 moved them and freed the area between U10 and J10. The 24 RGB + 4 sync lines leave U10 eastward in a 0.5 mm-pitch ribbon (corridor y 60–71), turn south at x 100–124 and enter J10's pad row from the north-west; the line order leaving U10 (R0..R7, G0..G7, B0 then B1, B4..B7) already matches J10's east-to-west order, and the six remaining crossings (B2/B3 and the four syncs) are resolved in the via field next to J10 with short B.Cu runs under the neighbouring F.Cu lines. Because the connector is on the back, every RGB line has exactly one via (28 vias), each with a GND return via ≤ 1.5 mm away. **The R and B lanes stay crossed at the SSD1963** (LDATA23..16 → panel B7..B0, LDATA7..0 → panel R7..R0; the uncrossed mapping would cost 187 ribbon crossings versus 59) and the controller's set_address_mode bit 3 (BGR) restores the colour order in firmware. RGB traces 101–124 mm (longest B7 124.4 mm), 0.25 mm over solid In1 ground; PCLK 107.6 mm, HSYNC/VSYNC 107 mm, DE 105 mm. The EMI report's rule 11 assumed ≤ 40 mm RGB lines; with 100+ mm, series 33 Ω on PCLK/HSYNC/VSYNC/DE at U10 is recommended (open item, schematic change).
- Thermocouple front end in the bottom-left corner: DG127H terminal at the board edge, TVS → 10 MΩ bias → 1 kΩ 0.1 % → 100 nF / 2 × 10 nF C0G at the ADS1115 AIN pins, TC_P/TC_N routed as a coupled pair (0.3 mm track, 0.3 mm gap, 21 mm, no vias) over the quiet plane region; NTC TH220 next to the terminal body; ≥ 60 mm from the triac and mains, ≥ 65 mm from the buck inductor.
- The LV power block (buck U30/L30, boost U11/L11, pi filter, VLED sense) moved west to x 70–100, y 71–98.5 in pass 2 (the RGB ribbon runs where it was); C2 (220 µF) stays at the PSU +5 V pin at (126.5, 72.6). No inner-layer copper under either inductor; SW loops: C330/C331 → U30 → L30 → C333/C334 ≤ 10 mm; L11 → U11 SW → D111 → C125 within 6.5 × 4 mm; the boost pi-filter (C127, L12, C124, R132/C128) sits between the +5 V island and U11; VLED sense resistors R122/R123 at the boost; VLED+/− run as a pair on B.Cu along the bottom strip to J10 pins 1/2. The In2 +5 V island is x 70–147, y 70–98 (it reaches x 147 so the back-side R-lane runs next to J10 keep one reference plane); the +5 V relay feed runs on B.Cu at x 82.6; U31 (LD1117-1.2) with C335–C337 sits south of U10. The relay coil driver Q4/D5 sits under the relay on the SELV side.
- I2C pull-ups at the ESP32; the touch-FPC TVS (D112/D113), TP_VDD (R129/C126) sit on the top side above J11 (x 45–51), TFT_VDD (R125/C122/C123) above J10 (x 139–147; R125's 3V3 via lands on the In2 plane east of the +5 V island, which is why the mains boundary corner moved to y 60); I2C runs from the ESP32 pull-ups past the ADS1115 to J11 at the bottom-left (3 vias each), TP_INT likewise.

### 12.4 Verification

- DRC (`kicad-cli pcb drc --severity-error`, project rules incl. 6.4 mm clearance + creepage, schematic parity): pass 1 0/0/0 on 2026-11-10; **pass 2 (2026-11-11): 0 violations, 0 unconnected, 0 parity errors** on the board as saved (zones filled) and again with `--refill-zones`; `kicad-cli pcb drc --severity-error --all-track-errors --schematic-parity`.
- Bus length ESP32 pin → 33 Ω → SSD1963 pin: 29–73 mm, 0 vias (limit 80 mm); longest D7 72.6 mm, D6 70.1 mm, D5 65.1 mm (unchanged pass-1 routing, U10 moved 2 mm).
- Layer changes (pass 3): 221 vias in total (GND 104, +3V3 38, +1V2 8, +5V 7, signals 64: 28 RGB/sync, 3 LCD_RST, 6 I2C, the rest fan/relay/ZCD/boost); no vias on mains nets; 8080 bus 0 vias. Every RGB/sync via has a GND return via within 1.5 mm and ≥ 1.35 mm from the next signal via (no merged anti-pads). Total track length 6.29 m, 1238 segments. (Pass 2 had 234 vias / 6.45 m.)
- Courtyard overlaps: none except Q1 on the HS1 plate (intended; `q1_on_heatsink_courtyard` rule). Mains placement checker (`mains2_check.py`): 0 issues.
- Schematic changes made during layout: D114 (15 V zener) was drawn backwards in Rev3_Display and has been turned round (cathode on VLED_P); the 8080 function-to-pin remap and the R/B lane crossing above (labels only; the firmware pin defines and §4/§5 follow).
- Open items after pass 2 (see also `EMC_PostLayout_Assessment.md` §9 for the EMC items): series 33 Ω on PCLK/HSYNC/VSYNC/DE at U10 (schematic change, see 12.3); confirm the BTA24-800CWRG data (Rth(j-c) 1.7 K/W, IGT 35 mA) against the ST datasheet (the ST site could not be fetched; the values come from second-source copies of the ST table); firmware recompile with the §12 pin map and the colour-order / touch-orientation check on hardware; DG127H body height (Özdisan's 19.1 mm vs the 10 mm drawing); HLK-10M05 derating above 60 °C (§9).

### 12.5 Layout pass 3 (2026-11-12, from the post-layout EMC assessment)

- **Input filter moved to the mains input** (schematic `sch_pass3.py`): LINE → F3 (8 A, now the main fuse) → LINE_FUSED → L40 (Core Master RC1415U-101K, 100 µH 5 A, new footprint `Rev3:L_Radial_CoreMaster_RC1415U`) → LINE_FILT; C40 (1 µF X2), C1 (100 nF X2) and RV1 across LINE_FILT/NEUT; LINE_FILT feeds Q1.A2 (heater), K1.1 (fan relay) and F1 (1 A) → new net PSU_L → L1 → PS1. Net classes: LINE/LINE_FUSED/LINE_FILT joined the 2.5 mm MainsHeater class, PSU_L is Mains; the 1.0 mm same-potential L-chain rule covers LINE, LINE_FUSED, LINE_FILT, PSU_L and PS1-AC/L. Reason: the triac's zero-cross turn-on steps (0.44 A at 100 Hz) reached the LISN unfiltered in passes 1–2 (≈ 27 dB over the EN 55014-1 limit at 150 kHz by model); behind L40/C40 the estimate is 11 dB under the limit.
- **Via anti-pad slots in the In1 ground plane removed** (`tools/pcb/in1_web_check.py`): non-GND vias now sit ≥ 1.35 mm apart (≥ 1.10 mm to GND vias) at the J10 via field, the RGB down-leg staircase and the U10 3V3/1V2 ring, so the zone's 0.25 mm minimum web survives everywhere (IPC-2221C 9.1.4.1).
- Mains band re-placed and re-routed around the new filter position by the mains agent; display region re-spaced by the display agent; power, signals and thermocouple regions unchanged.
- Verification: DRC 0 violations / 0 unconnected / 0 parity errors on the board as saved (zones filled) and with `--refill-zones` (2026-11-12); mains placement checker 0 issues; In1 anti-pad check: 0 merged groups in the display and mains regions, 4 residual two-via pairs of DC/low-speed nets (J2 FTDI pins 2/3 and 4/5, a +3V3/GND pair at the ESP32 and a +3V3 pair at the buck output, ≈ 2 mm slots each, accepted). 221 vias (GND 104, +3V3 38, +1V2 8 — the 1.2 V core pins are now tied by an F.Cu ring instead of a B.Cu ring —, +5V 7, signals 64), no mains vias; total track length 6.29 m. Heater copper F3 → L40 → Q1 82 mm, whole heater loop 132 mm (pass 2: 87 mm without the choke in the path); C40 8 mm from L40's output pad; LINE_FILT changes from F.Cu to B.Cu through F1's clip pad (Ø1.3 mm barrel, plated cross-section ≈ the 2.5 mm trunk's). RGB lines 100.9–124.5 mm, 8080 bus unchanged (29–73 mm, 0 vias). The heater and fan wire pads (R1, J4) stay on the top edge with J3; the band's west end x 25–50 is free.

### 12.6 Layout pass 4 (2026-11-12): top-side FPC connectors, EMC provisions, screw-hole keep-outs

- **Mechanical concept (Ömer):** the panel's back and the PCB's back lie flush, held by a plastic frame that also carries the oven-panel mounting; the PCB's back is now component-free. The panel tails hang straight down past the flush bottom edges and fold once around the PCB's bottom edge onto the top side, so the connectors are **upper-contact** parts on F.Cu: J10 Connfly DS1020-09-40VBT1B (233 pcs), J11 KLS L-KLS1-242D-1.2-06-T-U-R (1,123 pcs; land pattern from the KLS drawing: pads 0.30 × 1.25 on 0.5 mm, anchors 2.0 × 2.45). Their footprints (`...TopSide` in Rev3.pretty) are numbered in panel order, i.e. mirrored relative to the connector's physical terminals, because the folded tail presents conductor 1 at the east end. The Connfly B version is assumed to share the A version's land pattern (to be confirmed on the Connfly drawing's legend before fabrication). J10 at (135.65, 92.0), J11 at (42.1, 92.4), pad rows ≈ 10 mm from the edge for the fold; the 68 mm TFT tail and the 40 mm CTP tail are long enough.
- **PSU moved:** with J10 on the top side it collided with the HLK-10M05 body, so PS1 moved to the top-right corner (AC pins on the top edge at y 5, DC pins at y 47.5; body x 130.6–161.6, y 1.2–51.3). The mains "no inner copper" / Cmts.User boundary is y 40 for x > 130; the In2 +5 V island has a lobe x 132–147, y 49–70 under the +5 V pin, which is joined by a 1.5 mm F.Cu bar and two vias to C2 (now at (134.8, 55.8)).
- **Mains band re-placed (third time):** the heatsink at HS1.x ≈ 104 with the BTA24 on its **north** face (Q1 rot 180; the q1_fanout rule area now follows Q1), the LC filter capacitor C40, C1 and RV1 at the band's west end, LINE_FILT trunk along y ≈ 10, wire pads on the top edge. To make the band close next to the PSU the **zero-cross detector lost its discrete bridge**: U1 is now an H11AA1 AC-input optocoupler (Isocom, 1,573 pcs; same DIP-6 output pins as the 4N28) fed by R6/R7 (vertical DIN0414 footprints) — nets /ZCD_L, /ZCD_N, one LED drop apart (`zcd_dc_pair` 0.5 mm rule). D1–D4 are gone. RV1 is a 14 mm 275 V-class MOV (Thinking TVR14431KSU15Y, footprint RV_Disc_D15.5mm_W5mm_P7.5mm).
- **EMC provisions:** RN1–RN7 33 Ω 0402x4 arrays (Royalohm 4D02WGJ0330TCE) on all 24 RGB + 4 sync lines, grouped in SSD1963 pin order (the controller-side nets are `<net>_T`, Bus class); they sit at the east end of the ribbon corridor (x ≈ 108–110, 45–78 mm from the SSD1963 pins — the corridor between the relay driver and the boost block is too narrow for them nearer the driver; see the EMC report F3). C129 100 nF across VLED_P/VLED_N and C130/C131/C132 1 nF to GND at J10 pins 1/2/4, C133 1 nF at J11 pin 1; D115/D116 PESD5V0S1BA on TP_INT and LCD_RST at J11.
- **Screw holes, by the book:** 9.4 mm copper keep-out rule areas on all four copper layers around each M3 hole (ISO 7089 washer OD 7 mm plus position tolerance; IPC-2221 mounting-hole clearance per the Battery Sentinel IPC summary R8). Because kicad-cli 10 does not report tracks/vias inside rule areas, every keep-out area now also has an explicit `disallow track via` rule in the `.kicad_dru` (washer rings, inductor inner layers, antenna, mains inner layers, heatsink fins/plate, U10 corner) — 28 rules in total.
- **Routing result:** the RGB lines run on F.Cu from the SSD1963 through the arrays into J10 with a 12-via re-sort zone for the six lines whose order differs (B2, B3 and the four syncs; lane analysis unchanged: 59 crossings with the current R/B mapping versus 187 uncrossed); RGB lengths 87–109 mm (pass 3: 101–125). VLED pair on B.Cu along the bottom strip, around the washer ring of the hole at (97, 95.5), ending in two tented vias under the J10 body. J11's four signals change layer in a via staircase north of its pads.
- Verification: DRC 0 violations / 0 unconnected / 0 parity errors on the board as saved (zones filled) and with --refill-zones, with all 28 rules including the keep-out disallow rules (2026-11-12); In1 anti-pad check 0 merged groups board-wide; mains placement checker 0 issues. 216 vias (GND 109, +3V3 38, +1V2 8, +5V 9, signals 52: 12 RGB/sync re-sort, 4 LCD_RST, 6 I2C, J11 staircase, the rest fan/relay/ZCD/boost), no mains vias, 8080 bus unchanged (29–73 mm, 0 vias); total track length 5.80 m. Heater copper 113.7 mm (F3 → L40 → Q1 66.9 mm), heater trunks on F.Cu with no crossing, C40 15 mm from L40; tall-part gaps to the heatsink envelope K1 2.6 mm, PS1 5.1 mm, L40 10.9 mm, L1 15.5 mm. RGB lines 87–109 mm from the SSD1963 to J10 through the arrays. BOM: 149 footprints (D1–D4 removed; RN1–RN7, C129–C133, D115/D116 added; U1 H11AA1; RV1 TVR14431KSU15Y; J10/J11 upper-contact). Vias under the J10 body (VLED pair, GND pins) are tented.

### 12.7 Schematic tidy round (2026-11-13)

- **What:** the five sheets redrawn in the house style (schematic-style-rulebook: every group in its own region with a 1.27 mm plain-text note, GND down / supplies up, vertical dividers with the supply on top, decoupling as supply rails, labels on stubs, junctions where ≥ 3 items meet, field offsets R ±2.54 / C ±3.81, no text touching anything). Paper: root A1 (rows: mains input → zero-cross detector → heater power stage; sub-sheet row with notes; programmer/auto-boot above the ESP32, fan relay), Display A2 (8080 series resistors | SSD1963 with 1V2/3V3 decoupling rails and crystal | RN1–RN7 block | J10 | panel power entry; backlight boost and touch at the bottom), Thermocouple / Power / Input filter A3 with each group in its own region. Title blocks: "3D Printer Filament Dryer & Print Annealer - <sheet>", READARK, rev 3.0, 2026-11-13, comments 1/2 summaries, comment 3 the author.
- **Kept:** every symbol instance UUID, reference, instance path and sheet; sheet symbols and file UUIDs; the netlist (188 nets, same names and pin sets as the pass-4 baseline). Only positions, wires, labels, junctions, power symbols (renumbered #PWR0101…#PWR0601 ranges, unique over the five files), notes and fields changed. The PCB file was not touched.
- **Substitutions (value / fields):** K1 HJR-3FF-S-Z-4/05VDC, U5 MOC3052M, R4 120 R (MOC3052 LED resistor; R9 stays 180 R, see round 2), Q2/Q3 MMBT4401, D5 1N4148W, D111 SS14 (Jiaqi), D114 MMSZ15V, F1 STC1A250V / F3 5GT8A (Reomax; fuse clips R3-5A ×4 as a BOM line, note at F3), TH220 Thinking TSM1B103F3381RZ, L12 10 µH PCD0403MT100 (pi-filter corner 34 → 16 kHz), C2 Koshin, C125 4.7 µF 50 V X5R, C128 47 µF 16 V, C221/C222 10 nF X7R (note corrected), C333/C334 22 µF 16 V, C116/C122/C336 10 µF 10 V, C120/C121/C337 1 µF 16 V, all 100 nF 0402 → Yageo CC0402KRX7R9BB104 (100 nF 50 V X7R), R122/R123 18 R 0.1 %, R132 0.5 R 0.5 W 1 %, HS1 Fischer (DigiKey URL). Every BOM line carries hidden MPN / Manufacturer / Datasheet from `tools/bom_ozdisan_input.json`; the thermocouple probe is the pinless BOM item TC1 (`Rev3:BOM_Item`, WRNT-02, Motorobit) inside a dashed "Off-board" frame at J20. U11 VIN: PWR_FLAG on BL_VIN.
- **Checks (real files):** netlist compare 188/188 nets identical (names and pin sets), 146 parts + TC1, no footprint change, 40 value changes as listed; ERC 5 → 1 (power_pin_not_driven fixed by the flag, the three lib_symbol_mismatch fixed: J10/J11 library default footprint aligned with the embedded copy, J2 embedded copy replaced by the identical-pin library symbol; the remaining warning is L1's unconfigured library nickname); PyMuPDF text-collision checker 0 hits at 0 mm and 0 near-misses at 0.5 mm on all five pages; `kicad-cli sch export bom --group-by MPN` matches `Rev3.0_BOM_Ozdisan_100pcs.csv` reference by reference and in quantity (0 mismatches; J3, J4, R1, V1 carry no MPN); no duplicate references, all UUIDs / paths unchanged.
- **Scripts:** `tools/sch_tidy/` (README there). Backups of the five sheets and Rev3.kicad_sym before the round: scratch `sch_tidy_backup/`. Renders: scratch `schview_tidy/` (pages at 60 dpi, every group at 150 dpi).
- **Round 2 (same day):** (1) R4/R9 corrected: the MOC3052 LED resistor is R4 (TRIG -> U5 pin 1), now 120 R (Royalohm 0402WGJ0121TCE; (3.3 - 1.5 - 0.1) V / 120 R = 14 mA worst case against IFT 10 mA, 18 mA / 39 mW best case); R9 (ZCD series resistor) back to 180 R 1/10 W (Royalohm 0603SAJ0181T5E); notes updated. The Özdisan BOM files are regenerated separately. (2) Programmer / auto-boot block redrawn without long wires or crossings: J2, the Q2/Q3 pair and the R11/C6 EN network are separate small blocks reached by root-local labels. Approved net renames (connectivity identical, "Update PCB from Schematic" renames these six nets only, no track changes): Net-(Q3-C) -> /EN, Net-(Q2-C) -> /IO0, Net-(J2-Pin_2) -> /RTS, Net-(J2-Pin_3) -> /DTR, Net-(J2-Pin_4) -> /RXD0 (U3 RXD0/IO3, fed by the adapter TXD), Net-(J2-Pin_5) -> /TXD0 (U3 TXD0/IO1, to the adapter RXD); ESP32-side names. (3) Rev3:SSD1963QL9: the four top supply pins moved inward along the top edge (x -11.43/-3.81/3.81/11.43 -> -10.16/-5.08/0/5.08, same pin numbers) so their names no longer run into D0-D2 / LDATA23-21; library and embedded copy identical. (4) The 35 mm CLK -> GND stub on U10 stays (a short stub would put the GND symbol on the XTAL_IN wire).
- **Later the same day (owner decisions):** (1) C6 (ESP32 EN RC) 100 nF -> 1 uF 6.3 V X5R (Samsung CL05A105KQ5NNNC, Özdisan 1.8 M stock), per Espressif's 10 k + 1 uF recommendation; BOM regenerated (C6 is its own line, 32.09 USD/board). (2) The fan relay K1 is fed from LINE_FUSED instead of LINE_FILT: the oven fan needs no EMC filter and its current no longer flows through L40 (K1 pin 1 net change on the root sheet, notes updated on the root and the Input-filter sheet). The PCB follows in the smoothing round (§12.8).
- **Round 2 checks (real files):** netlist 188/188 nets identical in pin sets, names identical except the six approved renames; ERC 1 (L1 library nickname only); text collisions 0 / 0 on all pages, with the SSD1963's own pin names no longer excused (the round-1 drawing showed VDDLCD within 0.36 mm of LDATA21-23); BOM export: R4 and R9 MPNs changed as above, every other reference and quantity unchanged; UUIDs, paths, references unchanged, no duplicates; all sheets CRLF.
- **Open item for the owner:** datasheet-completeness gaps listed in the tidy report (ESP32 EN capacitor 100 nF vs 1 µF recommended, optional 0.1 µF at the TPS562201 VIN, HLK-10M05 output TVS/ceramic per Hi-Link's application circuit) — no parts were added.

### 12.8 Smoothing round (2026-11-13)

Scripts: `tools/pcb_smooth/` (README there). Full report with the hole table: side-session note `rev3-pcb-smooth-report.md`. Backups of the board, `.kicad_pro` and `.kicad_dru` from before the round: scratch `pcb_smooth_backup/`. Renders and region crops: scratch `pcbview_smooth/`.

- **Fan feed off the filter.** The schematic change is now in the layout: K1.1 (fan relay COM) moves from LINE_FILT to **LINE_FUSED**, fed by a 2.5 mm F.Cu track from L40.2. That is the heater-trunk width, because only the 8 A F3 protects it: IPC-2221 external, 0.0875 mm² → 6.3 A at 20 K. The LINE_FILT drop to K1 is gone. The LINE_FILT branch L40.1 → C40.1 now runs on B.Cu (1.0 mm, through-hole pads as the layer change, no vias); C40 → C1 → RV1 and the triac / F1 trunk are unchanged. In the `.kicad_dru`, the K1 coil-pin exceptions of `mains_to_selv_clearance` / `_creepage` name LINE_FUSED instead of LINE_FILT. Its last 4.5 mm (3.0 mm outside the K1.1 pad) is necked to 1.6 mm with a curved 2.5 → 1.6 mm track-to-track teardrop, so the COM copper keeps 3.86 / 3.96 mm from the coil pads K1.5 / K1.2. K1.1's own pad is 3.52 / 3.61 mm from them. 1.6 mm external 1 oz carries 4.55 A at 20 K (IPC-2221), the same neck as at the triac pins.
- **Screw ears.** The 164.9 × 100 mm panel (abs x 20.02–184.92, y 19–119) covers the four old M3 holes. The frame is therefore screwed through five ears with M3 holes, all `MountingHole_3.2mm_M3`, each with 9.4 mm washer keep-outs on all copper layers:
  - **H5 (10, −5.8), H6 (73, −5.8), H7 (154, −5.8)** on the top edge
  - **H8 (169.8, 10), H9 (169.8, 89)** on the right edge

  Tabs are 9 mm wide with a full-round end; all project 10.3 mm, so the 9.4 mm washer keep-outs end 0.10 mm (top) / 0.18 mm (right) outside the panel. Every hole is ≥ 9.17 mm from mains copper and ≥ 6.46 mm from mains bodies, and every Ø 5.5 mm screw head is ≥ 2.05 mm outside the panel. H6 is at x 73, not the centre: at x 82 the F3 clips are 7.75 mm away. Board bounding box including ears: 174.3 × 109.3 mm. The four old holes are H1 (4, 4), H2 (4, 95), H3 (97, 95.5) and H4 (160, 95), all under the panel. All nine holes are board-only and excluded from the BOM and position files.
- **Outline.** One closed chain of 23 lines and 19 arcs: R3 board corners, R1 ear fillets, R4.5 ear ends. The two overlapping 1.2 × 12 mm slots under U5/U1 are now one 1.2 × 23.5 mm round-ended slot with the same extremes.
- **Tracks.** 621 corners are replaced by tangent arcs: R 0.29–6.0 mm, median 1.7 mm, mains trunks ≥ 2.5 mm. 24 short 45° jogs became S-curves. The checker finds 0 corners between two track items; bends on pads (63) and vias (12) and junctions remain. Track items: 958 segments + 669 arcs (before: 1183 segments). Widths are unchanged, except that the Q1-A1 1.6 mm neck starts 1.04 mm earlier.
- **Teardrops.** 441 KiCad teardrop zones: 439 pad/via, 2 track-to-track. Curved, length ≤ 0.5 × size (max 1 mm), width ≤ 1.0 × size (max 2 mm). None at U10/U20 or in their escape areas, none in the antenna keep-out, none on the 2.5 mm mains trunks (they are wider than 0.9 × the pad).
- **Pours.** Fillet corner smoothing (1 mm; 0.5 mm on the +5V island). Minimum width 0.5 mm and island removal "always" on the outer GND pours: 0 necks, 0 unconnected islands. The SELV pours now reach the right edge (x 161 → 163.5).
- **Stitching.** 340 GND vias, 0.6/0.3 mm, "free": a 4.5 mm grid, a 3 mm edge fence, a 3 mm fence along the In2 +5V split, vias beside the 8080 bus / RGB lanes, a ring at U10, vias at the J10/J11 GND pads, and return vias at signal vias. Rules: ≥ 0.3 mm from any copper, ≥ 1.35 mm between via centres, ≥ 6.4 mm from mains, none in the thermocouple quiet area. GND vias: 449 (before 109); vias in total: 556. 43 of the 52 signal vias have a GND via ≤ 1.0 mm edge-to-edge and 9 within 1.5 mm. Four of them were placed by hand: VLED_N, J2 TXD0 (it also serves RXD0), Q4-B and BL_PWM.
- **IPC references applied:**
  - IPC-2221B Table 6-1 B2: 2.5 mm between mains conductors; IEC 62368-1 reinforced: 6.4 mm creepage / 4 mm clearance to SELV. All kept by DRC.
  - IPC-2221 / IPC-2152: fan feed 2.5 mm and LINE_FILT branch 1.0 mm (3.2 A at 20 K against 72 mA of C40 ripple current).
  - IPC-2221B land-to-conductor filleting: the teardrops. IPC-7351 land patterns are unchanged.
  - IPC-6012 class 2 / IPC-2221B annular ring for the stitching vias: 0.15 mm nominal; aspect ratio 5.3:1.
- **Verification (real files):** `kicad-cli pcb drc --severity-all`, zones as saved and refilled: **0 errors, 0 unconnected**, 261 silkscreen/text warnings (271 before). The pass-2 mains checker reports 0 issues. Connectivity is identical to pass 4 except K1.1. The `.kicad_pro` was restored to the committed net classes; an open KiCad session had written back stale pass-3 patterns. Teardrop options are curved.
- **Final pass (same day).**
  - 3D models from `tools/models3d/models.json` on 15 footprints: C40, HS1, J10, J11, J20, L1, L11, L12, L30, L40, F1, F3, J3, R1, J4.
  - **DS1** `Rev3:TFT7_SAT070AT40D21_Mech` is added: placed on F at abs (102.47, 69.0), then flipped to B.Cu at 180°. Its outline is abs x 20.02–184.92, y 19.00–119.00. It is board-only, excluded from the BOM and position files, has no pads and adds no DRC item.
  - Holes renamed H1–H4 and set board-only.
  - K1 COM neck and the four hand-placed return vias, as above.
  - Real files: DRC 0 errors, 0 unconnected, 261 warnings (unchanged). Corner checker 0. Connectivity unchanged except K1.1 and the hole references. Mains checker 0 issues.
  - Side view: the THT leads, most visibly HS1's Ø 2.3 mm pins, protrude from the PCB back into the space the panel's back occupies. This is an open item for the frame or for lead trimming.
- **Round 3 (2026-11-13, owner requests).**
  - **J11 2.08 mm west**, local (42.10, 92.40) → (40.02, 92.40) (abs 60.02, 112.40), rotation unchanged: the CTP tail fingers (DS1 Dwgs.User finger zone x 38.22–41.82) now land square on the pad row (38.62–41.42). The six escapes are redrawn with the same widths, layers and layer-change vias: SDA / SCL / LCD_RST keep their staircase (R 0.854 arcs, rows 2.08 mm longer), TP_INT turns onto its row with an R 0.6 arc instead of the 45° dog-leg, the GND and TP_VDD vias move with the connector (TP_VDD B.Cu link 2.08 mm longer). ESD diodes D112/D113/D115/D116 and R129/C126/C133 did not move. Forced by the move (west side, thermocouple VREF divider): C226 0.5 mm west with its GND via; R227 re-placed horizontal just north of the J11 courtyard, (36.0, 90.0) 90° → (35.775, 88.35) 180° (the courtyards overlapped by 2.3 mm); C225's GND via 0.7 mm to (34.13, 87.35) (it would have touched R227's pad).
  - **No holes inside the board.** The four old holes under the panel and their 16 washer keep-outs are gone; the pours close over them and the stitching was extended into those areas (edge fence and 4.5 mm grid; ≤ 3.4 mm from any pour point to a GND via; no island, no new sliver). Four ears in the H1–H9 style are added on the left (hole centres x −4.8, y 10 / 89) and bottom (y 103.8, x 10 / 155, clear of the CTP and TFT tail loops by 7.9 / 6.3 mm head-edge). The panel is flush on those edges, so 4.8 mm puts the 9.4 mm washer keep-out 0.1 mm outside the panel and the Ø 5.5 mm head 2.05–2.07 mm outside it. All holes ≥ 9.17 mm from mains copper and ≥ 6.46 mm from mains bodies (unchanged for the old ears; the new ones ≥ 37 mm), ≥ 19 mm from the antenna keep-out. Holes renumbered **H1–H9 clockwise from the top-left**: H1 (10, −5.8), H2 (73, −5.8), H3 (154, −5.8), H4 (169.8, 10), H5 (169.8, 89), H6 (155, 103.8), H7 (10, 103.8), H8 (−4.8, 89), H9 (−4.8, 10). Envelope incl. ears **183.6 × 118.6 mm** (abs x 10.7–194.3, y 9.7–128.3).
  - **Panel stand-off.** The owner adds a 5 mm spacer in the frame between the PCB back and the panel (it also clears the THT leads, open item O8 of the smoothing round). It is modelled in the panel model by the 3D toolchain; nothing changes on the board (`models.json` still lists DS1 with offset 0, so DS1 is unchanged).
  - **Checks (real files):** DRC 0 errors / 0 unconnected, 261 silkscreen/text warnings (unchanged), as saved and refilled; connectivity identical (189 nets, unconnected 0); corner checker 0; filled copper 0 necks / 0 unconnected islands (9 pre-existing slivers, none new); mains checker 0 issues; 23 new stitching vias (471 GND vias, 578 vias). Scripts `tools/pcb_smooth/r3_*.py`, `build.py` steps 10–15.

### 12.9 3D models and the display in the board model (2026-11-13)

- Every footprint now carries a 3D model. KiCad's generic models stay for passives and standard packages; 15 parts were modelled from manufacturer drawings with CadQuery (`tools/models3d/`, venv recipe in its README, `build_all.py`; STEP + WRL in `KiCad/ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/`): L40 RC1415U, L30 SRI0605B, L11/L12 PCD0403, L1 LFU09V-103 (envelope only, drawing not obtainable), HS1 SK 409 63,5 STC, J10 Connfly DS1020-09-40VBT1B, J11 KLS L-KLS1-242D (envelope from the footprint values, no KLS PDF), J20 DG127H (19.1 mm tall), C40 Faratronic C42 32 × 18 × 9, F1/F3 Reomax R3-5A clips with a 5 × 20 fuse, the solder-wire stubs J3/J4/R1, and the display. Every model's pins were checked against the footprint pads (0.000 mm on all 124 pads). K1 keeps the SRD model (Tianbo outline within 0.6 mm), PS1 the Hi-Link model.
- **Display DS1** (`Rev3:TFT7_SAT070AT40D21_Mech`, board-only mechanical footprint, no pads, excluded from BOM and position files) sits on the back side at (102.47, 69.00) abs, 180°: panel back flush on the PCB back, bottom and left edges flush, outline abs x 20.02–184.92 / y 19.00–119.00 (overhangs the PCB 1.00 mm at the top, 0.92 mm on the right). Derived from the SAT070AT40D21 V.2 drawing (LCM 164.9 × 100 × 3.34, CTP stack +1.98 mm; active area 154.08 × 85.92 at 4.03 / 4.87) with the TFT tail fingers on J10. The tails are modelled folded around the bottom edge into J10/J11.
- **Open mechanical items for the owner:** (1) with the TFT tail on J10, the CTP tail fingers land at abs x 60.02, J11 is at 62.10: move J11 2.08 mm west or accept the skew on the 3.5 mm tail end; (2) both tails are longer than the fold needs (TFT 67.65 mm, CTP 50 mm): the surplus forms a U-loop ≈ 28 / 20 mm below the board edge that the frame must pocket (≈ 5.3–6.4 mm thick), or an S-fold behind a frame lip; (3) the panel covers the four original M3 holes H1–H4, so the frame can only use the ears H5–H9 (§12.8); (4) through-hole leads (HS1's Ø 2.3 mm pins most of all) protrude from the PCB back into the panel's space: the frame needs a ≥ 2 mm spacer between PCB and panel, or all leads are cut flush (≤ 0.5 mm) before assembly.

### 12.10 Silkscreen and reference designators (2026-11-13)

Scripts: `tools/silk_refdes/` (README there; adapted from the Battery Sentinel refdes round, same rules and parameters). Full report: side-session note `rev3-silk-refdes-report.md`. Backups: scratch `silk_backup/`; renders: scratch `silk_renders/`.

- **Designators:** every one of the 145 placed footprints has its Reference on F.SilkS, centred, 0°/90°, not mirrored.
  - Sizes: 0.8 × 0.7 / 0.10 mm (91), 0.8 × 0.6 / 0.10 (11), 1.0 × 1.0 / 0.15 for connectors and large parts (36). The board minimum of 0.8 mm / 0.08 mm is met and was not changed.
  - Placement: 138 sit directly at their part (obstacle raster 0.025 mm; mask 0.15, silk 0.15, edge/holes 0.30 mm; ownership test d_oth ≥ d_own + 0.30 / 0.22 and ≥ 2 × d_own; rows read the same way).
  - Seven are in three framed legend maps (true uniform-scale copies, leader with arrow): LEG1 C129/C130 at J10, LEG2 C225/R227/C226 next to J11, LEG3 C133/C126 at J11.
  - The U10 bus block, the RN arrays, the decoupling rows and the thermocouple front end all have direct labels.
  - H1–H9 and DS1 (board-only) keep hidden references; values stay hidden.
- **Board legend (1.0 mm / 0.15 mm):**
  - J3: L / N under the pads with "J3" between them, "MAINS IN" below.
  - R1: "HEATER" under "R1".
  - J4: "FAN" between the pads.
  - J2: "FTDI", "GND" at pin 1, "3V3" at pin 6.
  - J20: "K-TYPE TC", "+" / "−" at the TC+ / TC− pads.
  - "TFT" under J10, "TOUCH" under J11.
  - Mains warning "230 V~ MAINS / HAZARDOUS VOLTAGE" in the mains band.
  - Title block "3D Printer Filament Dryer / & Print Annealer / PCB Rev3.0  2026-11-13 / readark" right of the RGB ribbon.
  - Placed at free spots: pads 0.25 mm, silk, edge and holes 0.5 mm.
  - The six old board texts are removed. Three of them were at the wrong connector: "MAINS IN" at J4, "FAN" at J3, "HEATER" at PS1.
- **Fabrication notes:** added on Cmts.User, right of the board. They cover outline and size with ears, 4 layers / 1.6 mm / 1 oz, ENIG (TBD), 0.15/0.15 mm, vias 0.6/0.3 and 0.9/0.45, 9 × Ø3.2 NPTH, the 1.2 × 23.5 mm creepage slot, the mains band and IPC class 2.
- **Checks (real file):**
  - Exact checker: 0 failures.
  - Structural diff: only the Reference fields, the removed texts and the new silk/Cmts texts differ; copper is byte-identical.
  - `kicad-cli pcb drc --severity-all`, as saved and refilled: 0 errors, 0 unconnected. Warnings 261 → 10, text_height 145 → 0.
  - The 10 remaining warnings are library silk, all present before this round: U1/U5 outlines across the creepage slot (4), Q1 outline on the HS1 plate (4), J20 outline over D220 and its pad 1 (2).
  - Schematic parity: 218 items, unchanged from before. They are the pending "Update PCB from schematic" items of §12.7 (MPN fields, values, renames, TC1).
  - `.kicad_pro` restored from HEAD; an open KiCad had written back stale teardrop and net-class settings.
- **Warnings cleared (follow-up, same day):** silk-only edits by `silk_fix.py`; no copper or placement change.
  - U5 and U1: the outline sides crossing the creepage slot are cut back to ≥ 0.30 mm from the slot. The DIP notch arcs, which lay wholly inside the slot band, are replaced by pin-1 triangles at pad 1.
  - J20: the pin-1 corner mark is cut back off D220's outline and pad 1.
  - `.kicad_dru`: new rule `q1_on_heatsink_silk`, F.SilkS ↔ F.SilkS between Q1 and HS1 only, silk_clearance 0 with severity ignore, as in `q1_on_heatsink_courtyard`. Clearance 0 alone still reports the touching outlines.
  - Result: DRC `--severity-all` on the real file shows 0 errors, 0 unconnected, **0 warnings**, as saved and refilled. `.kicad_pro` still matches HEAD.
- **Front artwork (owner request, same day):** the title-block texts are replaced by the readark logo with Manrope lines under it (scripts `tools/silk_refdes/art/`).
  - Lines: "OVEN CONTROLLER" (board name, 2.7 mm cap), "PCB Rev3.0 · 2026-11-13", "Designed by Ömer Karaoğlu · readark" and the ratings line `230 V~ · 1 kW heater · 7" touch · K-type TC`.
  - Placement: logo 35 mm wide, block 35 × 15.8 mm at abs x 148–183, y 82–98, right of the RGB arrays. It is the largest free front spot; clearances: mask/silk/courtyards 0.15, edge 1.0, holes 0.3 mm. Strokes are ≥ 0.15 mm.
  - Fabrication note 1 now names the board "OVEN CONTROLLER PCB Rev3.0".
  - Checks: exact checker 0 failures; DRC 0 / 0 / 0; only F.SilkS / Cmts.User items changed.
- **QR code (same day):** a QR code on the front silkscreen opens the AnnealX product video at `https://readark.eu/annealx/7j7aux/` (an unlisted page on readark.eu, noindex, not linked from the site).
  - Code: QR version 3, error level M, 29 × 29 modules of 0.5 mm. The white square is 18.5 mm with a 4-module quiet zone and R1.8 mm corners, as on Battery Sentinel. The light modules and the quiet zone are printed; the dark modules are holes, so the mask shows through.
  - Placement: abs x 121.5–140.0, y 99.5–118.0, centre (130.75, 108.75), in the empty pocket left of J10 along the bottom edge. It is 1.0 mm from the edge and 2.2 mm from J10's courtyard; R122/R123, RN7 and C128 bound the pocket.
  - Why 0.5 mm modules and not Battery Sentinel's 0.625: the largest free square in the pocket is 19.22 mm. At 0.625 mm, v3 is 23.125 mm and v2 is 20.625 mm, so neither fits. v2 could not hold the 34-character URL anyway (v2-M holds 26 bytes). The code is still well over 12 mm, so the spot the owner asked for was kept.
  - Clearances: mask, other silk and courtyards 0.15 mm, edge 0.5 mm, holes 0.3 mm; ESP32 antenna keep-out.
  - Scripts: `tools/silk_refdes/art/qr_gen.py` (segno, placement search) and `art/qr_apply.py` (37 filled F.SilkS gr_poly, uuid5). `run_all.py` step 6d runs them, and `refdes_check.py` / `refdes_diff.py` check the QR too.
  - Checks on the real file:
    - Exact checker: 0 failures. Worst QR clearance is 1.01 mm to the edge; nothing else lies within 0.65 mm.
    - Structural diff against HEAD: all 3114 items byte-identical and in order, plus exactly 37 new F.SilkS gr_poly.
    - DRC `--severity-all`, as saved and refilled: 0 errors, 0 unconnected, 0 warnings.
    - A 60 px/mm render decodes to the URL with OpenCV and pyzbar, and still does at 12 and 6 px/mm.
    - `run_all.py` from the pre-silk board reproduces the file byte for byte (md5 `82cfd261…`).

### 12.11 Carrier frame (2026-11-13 v2)

Design document: `Rev3.0_Frame_Design.md` (v2). CAD: Fusion 360 part "Rev3.0 Frame v2" v6 and "Rev3.0 Frame v2 fit assembly" v6 (hub1 › Oven › "Rev3.0 OVEN CONTROLLER"), built by `tools/frame_v2/fusion/` (README there). Independent CadQuery checks: `tools/frame_v2/build_v2.py`. Outputs: `Mechanical/Rev3.0_Frame/`. The v1 CadQuery model in `tools/frame/` (eight feet) is superseded.

- **Part:** one injection-moulded PA6-GF30 frame, heat-stabilised, halogen-free FR. Material requirements: UL94 V-0, GWFI 960 °C, GWIT ≥ 775 °C (IEC 60335-1 cl. 30). Example grade: Durethan BKV30FN04, to be confirmed. One pull, no undercuts, wall 2.5 mm, ribs 1.5 mm, draft 1° (0.5° on locating faces, pilots, slots, pegs), R 0.5 root fillets modelled on 337 roots.
- **What changed from v1:** the owner rejected the eight cantilevered feet. v2 has a continuous perimeter flange (14 × 2.5 mm, R 12 corners, front face = sealing / parting plane at Z −11.02), ten M4 stud bosses with radial slots, and the locating pegs on the side flanges. Every eight-stud layout failed the gasket-lift limit (best 178 µm against 90 µm).
- **Size:** body 170.4 × 137.45 mm; 198.4 × 165.45 × 15.07 mm overall (+0.8 mm pegs); 55.06 cm³, 74.9 g (v1: 192 × 148 mm, 44 g).
- **Z stack (PCB back = 0):**
  - Formex sheet 0.4 on a 2.6 mm shelf at −4.6; panel back −5.0; glass front −10.32;
  - stud-tube tops (washer seat) −3.52; flange back −8.52; flange front −11.02 (1.0 mm silicone sponge gasket at 30 %).
  - Nothing above Z 0 within the board outline + 1 mm (0 mm³). The tail-pocket walls rise to +4.05 only for y ≥ 129, ≥ 2.6 mm off the board.
- **Panel seat:** 165.40 × 100.50 pocket (0.25 mm per side, 0.8 × 45° lead-in), as v1.
- **PCB seat:** nine Ø 8 bosses under H1–H9 with blind Ø 2.4 pilots (1.0 mm floor), ISO 7049-C / DIN 7981 ST2.9 × 9.5 A2 at 0.3–0.4 Nm; 26 support ribs flush with the shelf edge, ≥ 1.21 mm from every B.Cu pad (J4.1).
- **Tail pocket:** 128.2 × 32.1 mm below the bottom edge, open front (closed by the oven sheet) and open back. Clearance ≥ 1.55 mm to both U-loops; R 5 inner corners.
- **Mounting:**
  - 10 PEM FH-M4-18 studs on the sheet (stack 7.5 frame + 1.0 washer + 5 nut = 13.5 mm), DIN 9021 M4 washers, ISO 10511 M4 nyloc at 0.6 Nm;
  - stud bosses Ø 10, 5 mm above the flange back, one full-height 1.5 mm rib each, hole 7.5 mm outside the wall. Slots 4.5 × 5.3 radial from the datum (102.47, 69.5) take the 0.2–0.4 mm frame-to-steel growth at ΔT 60 K;
  - pegs Ø 3 × 0.8 on the side flanges at (9.77 / 195.17, 69.5) into two 3.2 × 3.9 sheet slots along X: glass located y ±0.1, x ±0.25;
  - Ø 12 socket from the component side: ≥ 1.29 mm to the board, 1.64 mm to the frame.
  - Sheet window 156.08 × 87.92 mm R 1 (cover view area + 0.5 mm per side), stud holes Ø 4.22 +0.08. The hole table is in the design document (§1.4), `Rev3.0_Frame_Drawing_v2.png` and `Rev3.0_FrontSheet_Pattern_v2.dxf`.
- **Fit check (real board STEP, every model; the Fusion assembly and CadQuery agree):**
  - 0 intersections with the 145 component models (282 bodies); closest part: the F3 clip leads, 1.364 mm;
  - PCB 0.08 mm (copper + mask); panel 0.138 mm; tails 1.554 / 1.557 mm; Formex sheet touching, gasket 0.607 mm, oven-sheet patch coplanar, 0 overlap;
  - lead tips to the Formex sheet: PS1 1.335 mm, HS1 1.735 mm, Q1 2.10 mm (leads trimmed to ≤ 2.5 mm, mandatory);
  - mains copper → frame → panel metal: creepage 7.95 mm (≥ 6.4), clearance 6.70 mm (≥ 4.0);
  - 0 slivers on design faces, 0 draft flags, no wall < 1 mm.
- **Stresses (PA6-GF30 FR at 110 °C: tensile 75 MPa, creep allowance 15 MPa):**
  - PCB bosses as v1 (bearing 8–16 MPa, hoop SF 8.4, thread shear SF 2.3); stud-tube bearing 8.4 / 12.6 MPa;
  - flange bending at a stud: T-section with the 5 mm rib 23.5 MPa worst (SF 3.2), 6.2 MPa sustained. The plate-only model gives 46 MPa: FEA before tooling;
  - gasket lift at 1000 h, nominal: top 44, sides 38, bottom 72 µm (limit 90); beam I 713 mm⁴ = 2.3 × v1;
  - thermal: at the pessimistic bound FH6/FH8 bear 0.007 mm across their slots (self-limiting, ≤ 12.2 MPa); covered at ΔT 40 K.
- **Open:**
  - gasket 1.0 vs 1.5 mm (LCM ± 0.3 tolerance gives 0–64 % compression);
  - insulating sheet grade and layers (GK-17 is 0.43 mm, GK-10 0.25 mm; reinforced insulation per cl. 29.3);
  - slots and the thermal / moisture bound (ten studs instead of eight: accepted 2026-11-13);
  - pegs visible on the front (`pegs_on`); PEM vs weld studs and the sheet thickness; Q1 trimming step;
  - four sharp tail-pocket corners; stud-boss FEA and Moldflow before steel; material grade; tail handling.
- **Files** (`Mechanical/Rev3.0_Frame/`):
  - `Rev3.0_Frame_v2.step`, `.stl`, `.f3d`; `Rev3.0_Frame_v2_params.json`; `Rev3.0_FrontSheet_Pattern_v2.dxf`;
  - `renders_v2/`: `Frame_*`, `Assembly_*`, sections `Section_A_stud_FH2_x103.5`, `Section_B_pcb_bosses_x30`, `Section_C_tail_pocket_x125`, `Section_D_flange_plan_Z-9.77`, `Section_E_stud_FH10_y40.5`, `Rev3.0_Frame_Drawing_v2`, Fusion screenshots `Fusion_*` (.png);
  - scripts: `tools/frame_v2/fusion/01…68` + `fv2lib.py` (Fusion build), `tools/frame_v2/build_v2.py` (checks; v1 regression with `--v1`), `tools/frame_v2/hole_pattern_calc.py`.

### 12.12 EMC-fix round (2026-11-21)

**Purpose.** The EMC test-simulation campaign of 2026-11-18 (`sim/emc_tests/`, picture version `Rev3.0_EMC_Test_Simulation_Results.pdf`; EN 55014-1/-2, IEC 61000-3-2/-3-3) and its re-run for an **earthed chassis** (`sim/emc_tests_earthed/`; the owner stated on 2026-11-21 that the oven chassis and sheet metal are connected to protective earth, so the 2 kV line-to-earth surge of EN 55014-2 Table 12 applies) found weak points. This round fixes them in the schematic and on the PCB. All results quoted from the campaign are simulations, not accredited measurements. Coordinates are local board mm (KiCad absolute − 20 mm) unless "abs" is given.

**12.12.1 Schematic changes**

- **D6**, 1.5KE440CA-TKS (Thinking, bidirectional TVS, 1500 W, VRWM 376 V, VC 602 V at 2.5 A), replaces RV2 (TVR10561K) across the triac A2–A1 (LINE_FILT – /Q1_A1). It clamps the 1 kV line-to-neutral surge to about 620–635 V across Q1 and U5 (20.6–22.5 % margin to 800 V). Its stand-off is only 4.8 % above the mains peak at 253 Vac.
- **U5**: MOC3052 → **Isocom MOC3083X** (800 V zero-cross opto-triac, IFT 5 mA, 5000 Vrms, UL + VDE "X" version, inhibited-state leakage 0.5 mA max). Reason: with D6 the surge still leaves 620–635 V across the driver, over any 600 V part's rating, and no 800 V random-phase driver is stocked at Özdisan. Owner's decision: phase-angle control was already discarded, burst firing is the only mode. **Firmware requirement:** the trigger must be on from before each zero crossing until at least 0.35 ms after it (or held for the whole burst); Q1 fires through R3 = 360 Ω at 14–31 V, 0.14–0.34 ms after the crossing (85 °C … −20 °C). Today's firmware (/ZCD falling edge + 230 µs, 150 µs pulse) ends before the crossing with the H11AA1 and can miss; this supersedes the "keep the 230 µs delay / 150 µs gate pulse" wording of §10 item 5. With the trigger on while the line is above the inhibit voltage and Q1 off, the driver's leakage across R2 = 360 Ω is 0.18 V against Q1's VGD of 0.2 V (10 % margin; R2 ≤ 200 Ω would give 50 %) — bench test at 85 °C.
- **R4**: 120 Ω unchanged, 0402 → 0603 (Royalohm 0603SAJ0121T5E), because a trigger held through a burst dissipates up to 49 mW. LED current 8.5 mA guaranteed minimum (ESP32 VOH ≥ 0.8 VDD) / 11.3 mA realistic minimum / 14.6 mA typical / 20.8 mA maximum against IFT 5 mA (× 1.45 at −20 °C): the owner's 150 % rule (7.5 mA) is met. R2 / R3 stay 360 Ω (owner's design).
- **K1**: Tianbo HJR-3FF-S-Z-4/05VDC (SRD type; 1500 Vac coil-to-contact, 3.6 mm coil-to-contact pad spacing, contact code 4 "unsuitable for inductive load") → **TE Connectivity Schrack RZ03-1A4-D005**: 1 form A, 16 A 250 Vac, AC-15 6 A, AgNi 90/10; coil 5 V, 60 Ω, 420 mW; 5000 Vrms and ≥ 10 / 10 mm coil-to-contact, reinforced insulation; open contact 1000 Vrms; RTII flux-proof (not washable); −40…+85 °C. Second source on the same footprint: Hongfa HF115FD/005-1H3A(335). Symbol `Rev3:Relay_SPST-NO_11-14` (A1 / A2 coil, 11 COM, 14 NO). Coil 83 mA / 0.42 W nominal, 97 mA / 0.51 W worst case; Q4 (BC817-25, R16 1 kΩ) stays saturated. Hot-coil pick-up 4.5 V at 60 °C and 4.75 V at 85 °C (datasheet graph): a restart with a hot coil is guaranteed to about 60 °C ambient, not at 85 °C. The simulated stress on the coil-to-contact barrier in the 2 kV line-to-earth surge is 2.3–2.9 kV; TE states no impulse figure (5 kV rms ≈ 7 kV peak).
- **RV3**, Thinking **TVR10471KSY** (10 mm, 300 Vac / 385 Vdc, V1mA 470 V ± 10 %, 775 V at 25 A, 2500 A, 70 J), **across the K1 contact** (pin 11 LINE_FUSED to pin 14 / fan). Owner's decision after the surge re-simulation with the RZ relay: only this position keeps the open contact under its 1000 Vrms (1414 Vpk) rating over the whole assumed fan range (596–703 V; up to 1918 V without it in the 2 kV line-to-earth surge), and it clamps the fan turn-off spike to ≤ 626 V. The first proposal (TVR14431 across LINE_FUSED–NEUT) could not be routed and did not help the line-to-earth case. With K1 open the disc leaks about 0.1 mA peak into the fan; a short-circuited disc makes the fan run permanently (the fan limits the current, F3 does not clear); a partly degraded disc could overheat — no thermally protected varistor is stocked.
- **C9**, 1 nF C0G 0402, from the zero-cross node (/ZCD_RAW, U6 input) to GND: the 1 kV EFT burst at that node drops from 11.3 V to 3.5 V (U6 absolute maximum 7 V), edge delay about 8 µs.
- **C134 / C135**, 100 nF X7R 0402, +5V to GND either side of the J10 via field: the +5 V island's 253 Ω resonance at 498.5 MHz (15th pixel-clock harmonic) drops to about 3 Ω. (2 × 1 nF was proposed first and rejected: it creates a 26.5 Ω peak at 64.6 MHz.)
- **RN1–RN7**: 33 Ω → **100 Ω** 0402×4 (Royalohm 4D02WGJ0101TCE). The radiated-emission study asked for 150 Ω, which is not stocked in this footprint; 100 Ω gives a 1.6 ns pixel-clock edge at the panel and leaves 13.3 ns each for set-up and hold (the panel datasheet states no figures).
- **U6**: value text corrected to the purchased SN74AHC1G14DBVR.
- **Net renames:** Net-(Q1-A1) → /Q1_A1, Net-(R8-Pad2) → /ZCD_RAW; the PCB also received the six renames of the 2026-11-13 tidy round (/EN, /IO0, /RTS, /DTR, /RXD0, /TXD0).
- **Checks after each step (real files):** netlist differences only the intended ones (188 nets); ERC 1 warning (the pre-existing L1 library nickname); text collisions 0 at 0 mm / 0 near-misses at 0.5 mm on all five sheets; BOM export agrees with the Özdisan list (0 mismatches); 100-board cost 33.14 USD per board (was 32.09). Scripts: `tools/sch_emc/`.

**12.12.2 PCB stage 1: synchronisation and the low-voltage side**

- Board updated from the schematic by script: fields on 149 footprints, the eight net renames, RV2 removed (the /Q1_A1 trunk merged at x 108, y 3.5–25.5).
- R4 (0603) at (101.335, 57.5). C5 moved from the ESP32 corner to U6's supply pin at (123.617, 58.9), 1.65 mm from the pin, own GND via. C9 at (118.96, 61.975), 1.9 mm from U6 pin 2. C134 at (118.2, 73.1) and C135 at (120.9, 75.4), each 0.85 mm from its own +5V and GND via.
- The `.kicad_pro` committed with 76f5b79 had been written by an open KiCad and had lost netclass patterns and teardrop settings (513 false DRC errors on the untouched board); the smoothing-round file was restored and this round's net names added.

**12.12.3 PCB stage 2: display-panel bond — 18 ground landing pads on the back**

- Purpose: the radiated-emission study found that the panel's FPC returns the current of 28 fast lines on three ground pins, which drives the panel's metal frame against the PCB ground; only a direct, low-inductance bond between the two (together with a ferrite on the FPC) passed. The pads are the PCB side of that bond; the frame side is not designed.
- Footprint `Rev3:LandingPad_GND_Bare6.0x5.0mm_Cu8.0x7.0mm` on B.Cu: copper 8.0 × 7.0 mm, bare ENIG area 6.0 × 5.0 mm, no paste; 5–8 GND vias 0.6 / 0.3 on the masked rim (landing area flat); about 0.1 nH per pad to In1 (budget 15 nH per contact); board-only (not in BOM or position file, no parity item, like H1–H9); labels BP1–BP18 on B.SilkS. No tracks were moved.
- Pad centres, local mm [nearest mains copper]: BP1 (18.5, 7.0) [9.8]; BP2 (18.5, 18.0) [9.5]; BP3 (18.5, 29.0) [10.3]; BP4 (36.0, 45.0) [13.2]; BP5 (45.0, 45.0) [12.6]; BP6 (146.0, 48.0) [19.7]; BP7 (155.5, 59.0) [29.2]; BP8 (155.5, 70.0) [31.3]; BP9 (155.5, 81.0) [36.7]; BP10 (155.5, 92.0) [44.2]; BP11 (116.5, 92.0) [32.7]; BP12 (108.0, 84.0) [24.7]; BP13 (91.5, 88.5) [32.6]; BP14 (59.0, 91.0) [38.6]; BP15 (29.5, 92.0) [53.0]; BP16 (16.0, 92.0) [62.8]; BP17 (21.0, 50.0) [22.8]; BP18 (137.0, 70.0) [15.5]. BP10 / BP11 flank J10, BP12 / BP18 are interior pads near the FPC end, BP15 sits by J11.
- Frame side, from the frame documents (read only): every pad lies inside the shelf window (local x 2.62–162.32, y 1.6–96.4), where the panel's metal back is 5.0 mm from the PCB and the Formex sheet 4.6 mm; each pad used needs an opening in the Formex sheet; no rib or boss lies over a pad (nearest rib 1.9 mm from a bare area); the FPC tails fold outside the board.

**12.12.4 PCB stage 3: mains band**

- **K1**, footprint `Relay_THT:Relay_SPST_Schrack-RT1-16A-FormA_RM5mm`, abs origin (92.75, 72.0), rotated 90°: coil A1 (72.75, 52.0) / A2 (65.25, 52.0); pin 11 at y 31.70 and pin 14 at y 26.66 (x 65.25 and 72.75). Coil feeds: +5V 1.0 mm on B.Cu, Net-(D5-A) 0.3 mm on F.Cu; Q4 / D5 unchanged. The `Cmts.User` boundary and the "mains: no inner copper" area are notched at x 61.5–77.0, y 45–56 so that the coil pins and feeds lie on the low-voltage side.
- **RV3** west of the contact pins: pad 1 (57.65, 30.30) LINE_FUSED, pad 2 (60.35, 22.80) fan; footprint `Varistor:RV_Disc_D12mm_W5.8mm_P7.5mm`.
- **LINE_FUSED**, 2.5 mm on F.Cu, from L40.2 round the east side of K1 to both pin-11 pads and on to RV3 pad 1. **Fan route**, 2.5 mm on B.Cu, from J4.1 through RV3 pad 2 to both pin-14 pads. The net class asks only 1.0 mm; 2.5 mm is used because these branches are protected only by F3 (8 A): about 556 A²s adiabatic withstand against the fuse's 307 A²s upper bound, +34 K at 8 A (1.0 mm: 89 A²s, +155 K). No mains vias; the heater trunks are not crossed.
- **D6** (DO-201AD horizontal, bidirectional, no polarity mark, both pads round): pads (94.0, 13.2) LINE_FILT and (109.24, 13.2) /Q1_A1; PSU_L moved to x 114.5 (3.16 mm to D6).
- **Barrier with the generic rules only — no relay exception remains:** coil pads and feeds to mains copper ≥ 13.6 mm; contact pads, RV3 and the new mains tracks to low-voltage copper ≥ 6.85 mm on every layer (In1 / In2 included); RV3 pads ≥ 7.2 mm.
- **Tall parts to the heatsink envelope:** L40 10.90, C40 22.65, K1 4.70, L1 15.45, PS1 5.10, D6 16.90, RV3 18.36 mm. Courtyard gaps: K1–RV3 0.06, L40–C40 0.06, L40–K1 1.06, C40–RV3 2.31, L40–RV3 2.66 mm; no overlap other than Q1 on HS1.
- Designators for K1, D6, RV3 (and L40, displaced by K1) placed by the silk_refdes method; library 3D models for the three parts.

**12.12.5 Rule-file changes**

- `.kicad_pro`: /Q1_A1 in the MainsHeater netclass pattern (old auto name removed); `unconnected-(K1-Pad4)` pattern removed.
- `.kicad_dru`: /Q1_A1 and /ZCD_RAW in the triac-pin and opto-pin rules; the K1 exclusions removed from `mains_to_selv_clearance` / `_creepage`; K1 removed from the same-footprint pin rules; the `k1_pins` rule area and its terms removed; `relay_coil_clearance` and `relay_coil_creepage` deleted; the mains inner-copper keep-out notched for the K1 coil.

**12.12.6 Verification (real files, 2026-11-21)**

- `kicad-cli pcb drc --severity-all --schematic-parity`, as saved and with `--refill-zones`: **0 errors, 0 warnings, 0 unconnected**; schematic parity 13 items, all pre-existing (12 net names that differ only in how a slash is written on L1, PS1, R6, R7 and six unused ESP32 pins; V1, the simulation source, has no footprint).
- Corner checker 0; In1 anti-pad check: the 3 pre-existing GND-return pairs only; mains placement checker 0 issues; pads against the schematic netlist: 0 net differences.
- `Rev3.0_CPL.csv`, the netlist, the schematic PDF, the ERC report and both BOM files regenerated. Scripts: `tools/pcb_emc/` (`stage1.py`, `stage2.py`, `stage3.py`), renders in `tools/pcb_emc/stage2_data/` and `stage3_data/`.

**12.12.7 Decided against, and open**

- Decided against (owner, 2026-11-21): a Y1 capacitor (no footprint; with the chassis earthed no case needs it, and it would likely fail conducted emission at the buck and boost frequencies); a snubber or X2 capacitor across the fan output; an on-board heater-lead inductor (if needed it goes into the heater wiring, chassis-mounted); RV3 across LINE_FUSED–NEUT.
- Open hardware decisions: the single-point **ground-to-earth bond** (position reserved, not placed: local (7.0, 92.5), Ø7 mm copper with a Ø3.2 mm plated hole next to BP16, nearest chassis stud FH9 about 22 mm). With an earthed chassis and a grounded-junction thermocouple the power module's leakage returns through the thermocouple inputs (−0.5…+3.9 V at 50 Hz, outside the ADC range); the bond removes that, but then only an **insulated-junction probe** leaves the front end correct (with a grounded junction one leg sits below ground and an open negative lead is not detected).
- Open, off the board: the **frame-side panel bond** (springs or gasket in the 5 mm spacer, Formex openings, conductive spots on the panel back; 6 contacts already give most of the benefit) — to be discussed with the owner before any frame design is changed; the **FPC ferrite** (about 150 Ω at 100–300 MHz on the 40-way tail), on which every passing radiated-emission result depends and which Özdisan does not stock; the **heater-lead inductor** (about 200 µH, 4.35 A rms) needed for conducted emission with an earthed chassis unless the heater measures about 100 pF or less to the oven body; the 2.5 kV impulse rating of heater, fan and wiring to the chassis.
- Open, firmware: the trigger timing above; the ZCD edge qualification (pin still low 50 µs later); the 1500-cycle burst frame (flicker P_lt 0.47 instead of 0.53); no 1-pixel alternating column patterns in the UI.
- To measure or bench-test: heater-to-chassis capacitance; whether the thermocouple probe's junction is grounded to its ring; continuity between the panel's metal frame and its FPC ground; the fan's current and type (the K1 open-contact results assume fan data); K1 hot-restart pick-up; the 1 kV and 2 kV surges on K1 / RV3 / D6; conducted emission with the heater off (the HLK-10M05 is a black box); EMC pre-compliance as a whole. RN 150 Ω and a thermally protected varistor are not stocked; the radio standards under RED are not assessed.
