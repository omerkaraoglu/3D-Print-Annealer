# Rev3.0 BOM — Özdisan availability and 100-board unit cost

Generated 2026-11-21 by `tools/make_bom_ozdisan.py` from the Özdisan product pages read on 2026-11-12 (USD prices as shown by Özdisan; TRY/USD on the site that day ≈ 50.3). PCB, assembly and the display panel (SAT070AT40D21) are **not** included; the thermocouple probe (Motorobit) and the heatsink (DigiKey) are the only non-Özdisan lines. Order quantity = max(100 × qty, MOQ) rounded up to the MOQ multiple; the unit price is that quantity's tier.

## Totals

| | USD / board |
|---|---|
| Components at the 100-board price breaks (qty × tier price) | **33.14** |
| Same, including MOQ rounding (what you actually pay ÷ 100) | **33.15** |
| of which not from Özdisan (HS1 heatsink from DigiKey, thermocouple probe from Motorobit) | 22.11 |

## Lines that need attention

| Ref | Value | Part number | Özdisan stock | Order qty (100 boards) | Availability |
|---|---|---|---|---|---|
| TC1 (probe) | K-type thermocouple, M6 ring tip, 1 m | WRNT-02 | 10 | 100 | SHORT: stock 10 < 100 |

## Substitutions and merged parts (vs the schematic values)

| Ref | Value | Part number | Note |
|---|---|---|---|
| C2 | 220uF 16V | PKRJ-016V221ME070-T2.5 | 220 uF 16 V 6.3x7 2.5 mm 105 C (fits the 6.3x11 footprint) |
| C5,C8 | 100n | CC0402KRX7R9BB104 | one 50 V X7R part for every 100 nF 0402 position (C5,C6,C8, C112-C115,C117-C119,C123,C126,C223,C225,C226, C129,C332) |
| C6 | 1uF 6.3V X5R | CL05A105KQ5NNNC | C6 100 nF -> 1 uF: ESP32 EN RC per Espressif (10k + 1 uF), decided 2026-11-13 |
| C116,C122,C336 | 10uF 6.3V X5R | CL21A106KPFNNNE | 10 V X5R used for both the 6.3 V (C116,C122,C336) and 10 V (C124,C127,C330,C331) positions |
| C120,C121,C337 | 1uF 6.3V X7R | C1608X7R1C105K080AC | 16 V X7R for C120,C121,C337 (6.3 V) and C224,C335 (16 V) |
| C125 | 4.7uF 25V X7R | CL21A475KBQNNNE | 4.7 uF 50 V X5R instead of 25 V X7R (no 25 V X7R 0805 in stock; the 50 V rating gives better DC bias) |
| C128 | 47uF 10V | EEEFK1C470UR | 47 uF 16 V 5x5.8 SMD (fits CP_Elec_5x5.4); stock 316 |
| C221,C222 | 10nF 50V C0G 1% | CL10B103KB8NNNC | X7R 10 % instead of C0G 1 % (no 10 nF C0G 0603 in stock); thermocouple input filter, DC measurement, acceptable |
| C333,C334 | 22uF 10V X5R | CL21A226KOQNNNE | 22 uF 16 V X5R (10 V X5R not in stock) |
| D5 | 1N4148W | 1N4148W_R1_00301 | 1N4148W (Panjit), SOD-123; the symbol is Diode:MMSD4148 (same SOD-123 pinout), value 1N4148W |
| D111 | SS14 | SS14-SMA-N-JQ | SS14 alternative (ON/Panjit not stocked) |
| F1 | 250VAC 1A Slow Blow | STC1A250V | 5x20 1 A time-lag glass (TBC1100A out of stock) |
| F3 | 250VAC 8A Normal | 5GT8A | 5x20 8 A fast glass |
| HS1 | SK 409 63,5 STC | SK 409 63,5 STC TO 220 | NOT at Ozdisan (largest TO-220 heatsink there is 35 mm); DigiKey 5496-SK40963,5STCTO220-ND, 5.6 K/W natural |
| K1 | RZ03-1A4-D005 | RZ03-1A4-D005 | replaces HJR-3FF-S-Z-4/05VDC (SRD type, 1500 VAC coil-contact) - owner decision 2026-11-21: reinforced 5 kV / 10 mm; MPQ 20. Second source on the same footprint: Hongfa HF115FD/005-1H3A(335), stock 93,169, 0.84704 USD at 50+ (https://www.ozdisan.com/p/genel-tip-roleler-403/hongfa-hf115fd-005-1h3a335-979825) |
| L12 | 10uH 1A | PCD0403MT100 | 2.2 uH PCD0403 not stocked; L12 changed to 10 uH PCD0403MT100 (same part as L11, same footprint): pi-filter corner 34 kHz -> 16 kHz, DCR 182 mOhm at ~0.3 A = 55 mV, Isat 1.04 A OK |
| Q2,Q3 | S8050-J3Y | MMBT4401-TP | S8050 not stocked; MMBT4401 600 mA 40 V NPN SOT-23, same pinout |
| R4 | 120 | 0603SAJ0121T5E | R4 0402 -> 0603 1/10 W (2026-11-21): TRIG held on during a burst runs it continuously, up to 49 mW at 85 C |
| R122,R123 | 18R 0.125W | TC0525B180JT5F | the only 18 R 0805 in stock is the 0.1 % thin-film part |
| R132 | 0.5R 0.25W | HP06W2F500LT5E | 0.5 R 1 % 0.5 W 1206 (HP series); Uniohm RR1206J050KT5E 5 % 0.25 W is the cheaper alternative (0.046 USD) |
| RN1-RN7 | 100R x4 | 4D02WGJ0101TCE | 33 R -> 100 R (EMC fix 2026-11-21): 150 R 0402x4 (4D02WGJ0151TCE) not stocked; 100 R is the nearest stocked value in the same 0402x4 footprint |
| TH220 | 10k NTC B3380 | TSM1B103F3381RZ | NCP18XH103F03RB not stocked; Thinking 10k 1 % B3380 0603 |
| U5 | MOC3083 | MOC3083X | MOC3052X -> MOC3083X (owner decision 2026-11-21): 800 V zero-cross; no 800 V random-phase driver stocked. X = VDE-approved version (Isocom DE93284 p.7) |
| U6 | SN74AHC1G14DBVR | SN74AHC1G14DBVR | value field aligned to the purchased AHC part (was SN74LVC1G14DBVR on the symbol, 2026-11-21) |
| D6 | 1.5KE440CA | 1.5KE440CA-TKS | replaces RV2 (TVR10561K MOV) across the triac: 1 kV surge clamp 620 V (EMC fix 2026-11-21) |
| RV3 | TVR10471KSY | TVR10471KSY | RV3 moved across the K1 contact, 300 V ac class (16 % margin to 253 V ac); MPQ 200. No thermally protected varistor stocked at Özdisan (Littelfuse TMOV14/20 all 0) |
| F1/F3 clips | 5x20 fuse clip | R3-5A | 5x20 PCB fuse clip, 4 per board (not in the schematic; clip pin diameter vs the 1.3 mm footprint holes to be confirmed) |
| TC1 (probe) | K-type thermocouple, M6 ring tip, 1 m | WRNT-02 | K-type, M6 ring-terminal tip, 1 m fibreglass/SS-braid lead, 0-600 C, bare ends; 145.86 TL + KDV = 2.90 USD at 50.3 TL/USD (2026-11-12); web stock shows '10+', ask Motorobit for 100 pcs; Motorobit SKU SNS.SCK.01.000085 |

## Not purchased

- **J3** — solder-wire pads for the mains lead (no part)
- **J4** — solder-wire pads for the fan lead (no part)
- **R1** — the 1 kW heater element (customer-side)
- **V1** — simulation source, not a part

## Thermocouple probe (not on the PCB, screws into J20)

**Chosen: Motorobit WRNT-02** (BOM line TC1). Özdisan lists no thermocouple probes (sensor categories and site search checked). The probe that ships with the MAX6675 kit used on Rev2.1 is a generic **K-type, M6 ring-terminal tip, 1 m fibreglass-insulated lead with stainless-steel braid, 0–600 °C (heat-shrink at the tip softens above ≈300 °C), bare/spade ends**, which goes straight into the DG127H screw terminal J20 (red = +, blue = −; the braid can be bonded to the enclosure at the gland for EMC). Sources: Motorobit WRNT-02 (K-type, M6, 0–600 °C, 1 m) 145.86 TL + KDV ≈ 2.9 USD, stock 10+, https://www.motorobit.com/wrnt-02-k-tip-0-600c-m6-termokupl-1-metre ; ProtoSupplies THC-3 (same part) 2.45 USD, https://protosupplies.com/product/thermocouple-k-type-m6-ring-terminal-sensor-1m/ ; for 100 pieces the same item is the usual AliExpress/LCSC-market 'K type thermocouple M6 1 m' at roughly 1.5–2.5 USD. If the chamber will exceed 300 °C at the sensor, use the stainless 4 × 30 mm cylindrical variant (same lead, 0–400 °C, no heat-shrink at the tip). Budget ≈ 2.5 USD per unit.

## Full BOM

| Ref | Qty/board | Value | Part number | Manufacturer | Özdisan stock | MOQ | Order qty (100 boards) | Unit price USD | Line / board USD | Availability |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 1 | 100n 275VAC X2 | C42P2104M6SC361 | FARATRONIC | 31530 | 2 | 100 | 0.05076 | 0.0508 | OK |
| C2 | 1 | 220uF 16V | PKRJ-016V221ME070-T2.5 | Koshin | 17966 | 5 | 100 | 0.02784 | 0.0278 | OK |
| C4 | 1 | 10n 305VAC X2 | C42Q2103K40A405 | FARATRONIC | 9691 | 2 | 100 | 0.06048 | 0.0605 | OK |
| C5,C8 | 2 | 100n | CC0402KRX7R9BB104 | Yageo | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| C6 | 1 | 1uF 6.3V X5R | CL05A105KQ5NNNC | SAMSUNG | 1813001 | 25 | 100 | 0.00469 | 0.0047 | OK |
| C7 | 1 | 10uF | CL10A106KP8NNNC | SAMSUNG | 1489217 | 2 | 100 | 0.05537 | 0.0554 | OK |
| C40 | 1 | 1uF 275VAC X2 | C42P2105KBSC400 | FARATRONIC | 56806 | 1 | 100 | 0.22272 | 0.2227 | OK |
| C110,C111 | 2 | 27pF C0G | GRM1555C1H270JA01D | Murata | 50830 | 20 | 200 | 0.00464 | 0.0093 | OK |
| C112-C115,C117-C119,C123,C126,C223,C225,C226 | 12 | 100nF 16V X7R | CC0402KRX7R9BB104 | Yageo | 4545 | 5 | 1800 | 0.01923 | 0.2308 | OK |
| C116,C122,C336 | 3 | 10uF 6.3V X5R | CL21A106KPFNNNE | Samsung | 352710 | 5 | 700 | 0.01898 | 0.0569 | OK |
| C120,C121,C337 | 3 | 1uF 6.3V X7R | C1608X7R1C105K080AC | TDK | 4130 | 5 | 500 | 0.04150 | 0.1245 | OK |
| C124,C127,C330,C331 | 4 | 10uF 10V X5R | CL21A106KPFNNNE | Samsung | 352710 | 5 | 700 | 0.01898 | 0.0759 | OK |
| C125 | 1 | 4.7uF 25V X7R | CL21A475KBQNNNE | Samsung | 62505 | 1 | 100 | 0.10025 | 0.1003 | OK |
| C128 | 1 | 47uF 10V | EEEFK1C470UR | Panasonic | 316 | 1 | 100 | 0.18514 | 0.1851 | OK |
| C129,C332 | 2 | 100nF 25V X7R | CC0402KRX7R9BB104 | Yageo | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| C130-C133 | 4 | 1nF 50V C0G | CL05C102JB5NNNC | Samsung | 2181 | 10 | 500 | 0.01398 | 0.0559 | OK |
| C220 | 1 | 100nF 50V X7R | CC0603KRX7R9BB104 | Yageo | 2443557 | 10 | 100 | 0.01727 | 0.0173 | OK |
| C221,C222 | 2 | 10nF 50V C0G 1% | CL10B103KB8NNNC | Samsung | 9799961 | 20 | 200 | 0.00709 | 0.0142 | OK |
| C224,C335 | 2 | 1uF 16V X7R | C1608X7R1C105K080AC | TDK | 4130 | 5 | 500 | 0.04150 | 0.0830 | OK |
| C333,C334 | 2 | 22uF 10V X5R | CL21A226KOQNNNE | Samsung | 1537 | 1 | 200 | 0.18779 | 0.3756 | OK |
| D5 | 1 | 1N4148W | 1N4148W_R1_00301 | Panjit | 230280 | 5 | 100 | 0.02021 | 0.0202 | OK |
| D111 | 1 | SS14 | SS14-SMA-N-JQ | Jiaqi | 70013 | 5 | 100 | 0.02606 | 0.0261 | OK |
| D112,D113,D115,D116,D220,D221 | 6 | PESD5V0S1BA | PESD5V0S1BA,115 | NEXPERIA | 10971 | 1 | 600 | 0.11625 | 0.6975 | OK |
| D114 | 1 | 15V 500mW | MMSZ15V-HT | Hottech | 44065 | 5 | 100 | 0.01873 | 0.0187 | OK |
| F1 | 1 | 250VAC 1A Slow Blow | STC1A250V | Reomax | 3979 | 1 | 100 | 0.04685 | 0.0469 | OK |
| F3 | 1 | 250VAC 8A Normal | 5GT8A | Reomax | 12985 | 5 | 100 | 0.01700 | 0.0170 | OK |
| HS1 | 1 | SK 409 63,5 STC | SK 409 63,5 STC TO 220 | Fischer Elektronik | 995 | 5 | 100 | 2.60000 | 2.6000 | OK |
| J2 | 1 | FTDI | DS1021-1X6SF11-B | Connfly | 12474 | 2 | 100 | 0.02376 | 0.0238 | OK |
| J10 | 1 | TFT_SAT070AT40D21_FPC40 | DS1020-09-40VBT1B | CONNFLY | 233 | 1 | 100 | 0.38183 | 0.3818 | OK |
| J11 | 1 | CTP_GT911_FPC6 | L-KLS1-242D-1.2-06-T-U-R | KLS ELECTRONIC | 1123 | 1 | 100 | 0.19290 | 0.1929 | OK |
| J20 | 1 | K-type TC | DG127H-5.08-02P-14-00AH | DEGSON | 44783 | 1 | 100 | 0.15014 | 0.1501 | OK |
| K1 | 1 | RZ03-1A4-D005 | RZ03-1A4-D005 | TE CONNECTIVITY | 110352 | 1 | 100 | 0.82527 | 0.8253 | OK |
| L1 | 1 | LFU09V-103 | LFU09V-103 | CORE MASTER | 8868 | 1 | 100 | 0.38576 | 0.3858 | OK |
| L11 | 1 | 10uH 1A | PCD0403MT100 | VIKING | 8969 | 1 | 100 | 0.11086 | 0.1109 | OK |
| L12 | 1 | 10uH 1A | PCD0403MT100 | VIKING | 8969 | 1 | 100 | 0.11086 | 0.1109 | OK |
| L30 | 1 | 4.7uH 4A | SRI0605B-4R7M | CORE MASTER | 1961 | 1 | 100 | 0.32479 | 0.3248 | OK |
| L40 | 1 | 100uH 5A | RC1415U-101K | CORE MASTER | 613 | 1 | 100 | 0.68691 | 0.6869 | OK |
| PS1 | 1 | HLK-10M05 | HLK-10M05 | HI-LINK | 333 | 1 | 100 | 3.90413 | 3.9041 | OK |
| Q1 | 1 | BTA24-800CWRG | BTA24-800CWRG | STM | 5449 | 1 | 100 | 1.29286 | 1.2929 | OK |
| Q2,Q3 | 2 | S8050-J3Y | MMBT4401-TP | MCC | 1780 | 20 | 200 | 0.00850 | 0.0170 | OK |
| Q4 | 1 | BC817-25-HT | BC817-25-HT | HOTTECH | 18050 | 10 | 100 | 0.01294 | 0.0129 | OK |
| R2,R3 | 2 | 360 1/2W 350V | MFR-50FTF52-360R | YAGEO | 5214 | 5 | 200 | 0.02561 | 0.0512 | OK |
| R4 | 1 | 120 | 0603SAJ0121T5E | ROYALOHM | 72660 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R5 | 1 | 47 2W 500V | KNP02SJ0470A10 | ROYALOHM | 590 | 5 | 100 | 0.02610 | 0.0261 | OK |
| R6,R7 | 2 | 33k 1W 500V | CFR01SJ0333A10 | ROYALOHM | 4213 | 5 | 200 | 0.02552 | 0.0510 | OK |
| R8,R10-R15,R124,R224 | 9 | 10k | 0402WGJ0103TCE | ROYALOHM | 189000 | 200 | 1000 | 0.00044 | 0.0040 | OK |
| R9 | 1 | 180 1/10W | 0603SAJ0181T5E | ROYALOHM | 219230 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R16 | 1 | 1k | 0402WGJ0102TCE | ROYALOHM | 299000 | 200 | 200 | 0.00050 | 0.0005 | OK |
| R110-R121 | 12 | 33R | RC0402JR-0733RL | Yageo | 58600 | 100 | 1200 | 0.00145 | 0.0174 | OK |
| R122,R123 | 2 | 18R 0.125W | TC0525B180JT5F | Royalohm | 13395 | 5 | 200 | 0.03348 | 0.0670 | OK |
| R125,R129 | 2 | 0R | 0805WAJ0000T5E | Royalohm | 54900 | 100 | 200 | 0.00153 | 0.0031 | OK |
| R126,R128 | 2 | 0R | CQ02WGJ0000TCE | Royalohm | 135304 | 200 | 200 | 0.00076 | 0.0015 | OK |
| R127 | 1 | 100k | CQ02WGF1003TCE | Royalohm | 152340 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R130,R131 | 2 | 2.2k | AC0402JR-072K2L | Yageo | 294360 | 50 | 200 | 0.00216 | 0.0043 | OK |
| R132 | 1 | 0.5R 0.25W | HP06W2F500LT5E | Royalohm | 7660 | 2 | 100 | 0.05084 | 0.0508 | OK |
| R220,R221 | 2 | 1k 0.1% | TC0325B1001T5F | Royalohm | 25373 | 5 | 200 | 0.02778 | 0.0556 | OK |
| R222,R223 | 2 | 10M | 0603SAJ0106T5E | Royalohm | 115000 | 200 | 200 | 0.00090 | 0.0018 | OK |
| R225-R227 | 3 | 10k 0.1% | TC0325B1002T5F | Royalohm | 71416 | 5 | 300 | 0.02778 | 0.0833 | OK |
| R330 | 1 | 33.2k 1% | 0402WGF3322TCE | Royalohm | 32048 | 200 | 200 | 0.00059 | 0.0006 | OK |
| R331 | 1 | 10k 1% | CQ02WGF1002TCE | Royalohm | 1185 | 200 | 200 | 0.00090 | 0.0009 | OK |
| RN1-RN7 | 7 | 100R x4 | 4D02WGJ0101TCE | ROYALOHM | 10227 | 20 | 700 | 0.00487 | 0.0341 | OK |
| RV1 | 1 | TVR14431KSU15Y | TVR14431KSU15Y | Thinking | 14877 | 1 | 100 | 0.10859 | 0.1086 | OK |
| TH220 | 1 | 10k NTC B3380 | TSM1B103F3381RZ | Thinking | 7301 | 5 | 100 | 0.08670 | 0.0867 | OK |
| U1 | 1 | H11AA1 | H11AA1X | Isocom | 1573 | 1 | 100 | 0.31775 | 0.3177 | OK |
| U3 | 1 | ESP32-WROOM-32E-N16 | ESP32-WROOM-32E-N16 | ESPRESSIF SYSTEMS | 1173 | 1 | 100 | 4.75200 | 4.7520 | OK |
| U5 | 1 | MOC3083 | MOC3083X | Isocom | 930 | 1 | 100 | 0.49275 | 0.4928 | OK |
| U6 | 1 | SN74AHC1G14DBVR | SN74AHC1G14DBVR | TEXAS | 23130 | 1 | 100 | 0.08700 | 0.0870 | OK |
| U10 | 1 | SSD1963QL9 | SSD1963QL9 | SOLOMON | 279 | 1 | 100 | 5.15494 | 5.1549 | OK |
| U11 | 1 | MIC2288YD5 | MIC2288YD5-TR | MICREL-MICROCHIP | 5640 | 1 | 100 | 0.63522 | 0.6352 | OK |
| U20 | 1 | ADS1115IDGSR | ADS1115IDGSR | TEXAS | 3828 | 1 | 100 | 3.31769 | 3.3177 | OK |
| U30 | 1 | TPS562201DDCR | TPS562201DDCR | TEXAS | 2323 | 1 | 100 | 0.20824 | 0.2082 | OK |
| U31 | 1 | LD1117S12CTR | LD1117S12CTR | STM | 2500 | 1 | 100 | 0.11377 | 0.1138 | OK |
| Y10 | 1 | 10MHz | CX3225GB10000P0HPQCC | Kyocera AVX | 3906 | 1 | 100 | 0.27840 | 0.2784 | OK |
| D6 | 1 | 1.5KE440CA | 1.5KE440CA-TKS | THINKING | 1083 | 1 | 100 | 0.34684 | 0.3468 | OK |
| C9 | 1 | 1nF 50V C0G | CL05C102JB5NNNC | Samsung | 2181 | 10 | 500 | 0.01398 | 0.0140 | OK |
| C134,C135 | 2 | 100nF 50V X7R | CC0402KRX7R9BB104 | Yageo | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| RV3 | 1 | TVR10471KSY | TVR10471KSY | Thinking | 81163 | 1 | 100 | 0.07112 | 0.0711 | OK |
| F1/F3 clips | 4 | 5x20 fuse clip | R3-5A | Reomax | 41572 | 2 | 400 | 0.02272 | 0.0909 | OK |
| TC1 (probe) | 1 | K-type thermocouple, M6 ring tip, 1 m | WRNT-02 | Motorobit | 10 | 1 | 100 | 2.90000 | 2.9000 | SHORT: stock 10 < 100 |
