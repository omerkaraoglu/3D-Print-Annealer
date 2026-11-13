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
2. Footprint placeholders to verify against the vendor drawings: L30 (SRI0605B on a Bourns SRN6045 pad set), L11 (PCD0403 on a Taiyo-Yuden NR-40xx pad set), J10/J11 (TE 1734839 pad set for the Connfly DS1020-09 — same 0.5 mm pitch, check the mechanical pads), J20 (Phoenix MKDS 1,5/2-5.08 pad set for DEGSON DG127H), L40/C40 custom footprints generated from Özdisan dimensions. — Pass 1 replaced these with footprints from the vendor drawings (Connfly DS1020-09, Core Master SRI0605B, Viking PCD0403, DEGSON DG127 family drawing via the DigiKey/Suntsu listing: Ø1.3 holes at 5.08 mm, body 10.7 × 8.1 × 10 mm — Özdisan's "19.1 mm profile height" for DG127H is unexplained; the 1.3 mm drill / 5.08 pitch footprint is right either way). SRI0605B-4R7M is not in Core Master's table (2.2 → 6.8 µH); Özdisan lists it as 4.7 µH ±20 %, 4 A, 70 mΩ (interpolated 3.4 A / 66 mΩ), adequate for the 1 A buck.
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
