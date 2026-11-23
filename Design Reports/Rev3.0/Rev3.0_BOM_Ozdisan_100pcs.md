# Rev3.0 BOM — Özdisan availability and 100-board unit cost

Generated 2026-11-23 by `tools/make_bom_ozdisan.py` from the Özdisan product pages read on 2026-11-23 (USD prices as shown by Özdisan, **excluding KDV / VAT**; TRY/USD on the site that day ≈ 50.6). Every link was opened on that date and its page title matched the part number. The heatsink, its retaining clip and the FPC ferrite (DigiKey), the thermocouple probe (Motorobit) and the earth lead and PCB screws (bought locally, estimated prices) are the only non-Özdisan lines; the display panel is included. Order quantity = max(100 × qty, MOQ) rounded up to the MOQ multiple (Özdisan's order multiple equals its MOQ on every line); the unit price is that quantity's tier.

Lines without a link: J5 earth lead, H1-H9 screws.

## Not covered by this list

- bare PCB, assembly and the carrier frame / Formex sheet
- the off-PCB heater-lead inductor of spec §12.12 (≈ 200 µH, 4.35 A rms, chassis-mounted)
- the M4 nut and lock washer that may be needed to hold the earth lead's ring lug on chassis stud FH9 (how the lug is held there is still open, spec §12.12.8)
- fuses beyond one set per board (no spares counted), mains / fan / heater wiring and the fan

## Totals

| | USD / board |
|---|---|
| Components at the 100-board price breaks (qty × tier price) | **73.32** |
| Same, including MOQ rounding (what you actually pay ÷ 100) | **73.32** |
| of which not from Özdisan (HS1 heatsink, its clip and the FPC ferrite from DigiKey, thermocouple probe from Motorobit, earth lead and PCB screws bought locally) | 7.45 |
| of which the display panel | 33.81 |

## Lines that need attention

| Ref | Value | Part (link) | Özdisan stock | Order qty (100 boards) | Availability | Lead time (weeks) | Note |
|---|---|---|---|---|---|---|---|
| PS1 | HLK-10M05 | [HLK-10M05](https://www.ozdisan.com/p/ac-dc-donusturuculer-606/hi-link-hlk-10m05-702430) | 26 | 100 | SHORT: stock 26 < 100 | 7-8 | Ozdisan stock fell to 26 (333 on 2026-11-12), no incoming stock listed, lead time 7-8 weeks: order 26 now and back-order 74, or take the balance from LCSC (C403745, 4,433 pcs, 3.27 USD at 1 pc, https://www.lcsc.com/product-detail/C403745.html) |
| TC1 (probe) | K-type thermocouple, M6 ring tip, 1 m | [WRNT-02](https://www.motorobit.com/wrnt-02-k-tip-0-600c-m6-termokupl-1-metre) | 10 | 100 | SHORT: stock 10 < 100 |  | K-type, M6 ring-terminal tip, 1 m fibreglass/SS-braid lead, 0-600 C, bare ends; 147.29 TL + KDV = 2.91 USD at 50.57 TL/USD (2026-11-23); web stock shows '10+', ask Motorobit for 100 pcs; Motorobit SKU SNS.SCK.01.000085 |
| DS1 (panel) | 7 inch 800x480 RGB TFT + capacitive touch | [SAT70AT40D21-33KN-CTP-V1](https://www.ozdisan.com/p/tft-paneller-381/satoz-sat70at40d21-33kn-ctp-v1-621995) | 61 | 100 | SHORT: stock 61 < 100 |  | 7 inch 800x480 24-bit RGB panel with GT911 capacitive touch, box of 60; Ozdisan has 61 for the 100 needed, no incoming stock and no lead time shown: order 60 now and ask Ozdisan for a date on the other 40 |

## Substitutions and merged parts (vs the schematic values)

| Ref | Value | Part number | Note |
|---|---|---|---|
| C2 | 220uF 16V | PKRJ-016V221ME070-T2.5 | 220 uF 16 V 6.3x7 2.5 mm 105 C (fits the 6.3x11 footprint) |
| C5,C8 | 100n | CC0402KRX7R9BB104 | one 50 V X7R part for every 100 nF 0402 position (C5,C6,C8, C112-C115,C117-C119,C123,C126,C223,C225,C226, C129,C332) |
| C6 | 1uF 6.3V X5R | CL05A105KQ5NNNC | C6 100 nF -> 1 uF: ESP32 EN RC per Espressif (10k + 1 uF), decided 2026-11-13 |
| C116,C122,C336 | 10uF 6.3V X5R | CL21A106KPFNNNE | 10 V X5R used for both the 6.3 V (C116,C122,C336) and 10 V (C124,C127,C330,C331) positions |
| C120,C121,C337 | 1uF 6.3V X7R | C1608X7R1C105K080AC | 16 V X7R for C120,C121,C337 (6.3 V) and C224,C335 (16 V) |
| C125 | 4.7uF 25V X7R | CL21A475KBQNNNE | 4.7 uF 50 V X5R instead of 25 V X7R (no 25 V X7R 0805 in stock; the 50 V rating gives better DC bias) |
| C128 | 47uF 10V | EEEFK1C470UR | 47 uF 16 V 5x5.8 SMD (fits CP_Elec_5x5.4) |
| C221,C222 | 10nF 50V C0G 1% | CL10B103KB8NNNC | X7R 10 % instead of C0G 1 % (no 10 nF C0G 0603 in stock); thermocouple input filter, DC measurement, acceptable |
| C333,C334 | 22uF 10V X5R | CL21A226KOQNNNE | 22 uF 16 V X5R (10 V X5R not in stock) |
| D5 | 1N4148W | 1N4148W_R1_00301 | 1N4148W (Panjit), SOD-123; the symbol is Diode:MMSD4148 (same SOD-123 pinout), value 1N4148W |
| D111 | SS14 | SS14-SMA-N-JQ | SS14 alternative (ON/Panjit not stocked) |
| F1 | 250VAC 1A Slow Blow | STC1A250V | 5x20 1 A time-lag glass (TBC1100A out of stock) |
| F3 | 250VAC 8A Normal | 5GT8A | 5x20 8 A fast glass |
| HS1 | SK 409 63,5 STC | SK 409 63,5 STC TO 220 | NOT at Ozdisan (largest TO-220 heatsink there is 35 mm); DigiKey 5496-SK40963,5STCTO220-ND, 5.6 K/W natural, 995 in stock, minimum 5, DigiKey Marketplace item (ships from the supplier, separate shipping); checked 2026-11-23. Clip-mounted version: Q1 is held by the Fischer retaining spring THF 409 TO 220 (own BOM line), with thermal compound |
| K1 | RZ03-1A4-D005 | RZ03-1A4-D005 | replaces HJR-3FF-S-Z-4/05VDC (SRD type, 1500 VAC coil-contact) - owner decision 2026-11-21: reinforced 5 kV / 10 mm; MPQ 20. Second source on the same footprint: Hongfa HF115FD/005-1H3A(335), stock 93,169, 0.84704 USD at 50+ (https://www.ozdisan.com/p/genel-tip-roleler-403/hongfa-hf115fd-005-1h3a335-979825) |
| L12 | 10uH 1A | PCD0403MT100 | 2.2 uH PCD0403 not stocked; L12 changed to 10 uH PCD0403MT100 (same part as L11, same footprint): pi-filter corner 34 kHz -> 16 kHz, DCR 182 mOhm at ~0.3 A = 55 mV, Isat 1.04 A OK |
| PS1 | HLK-10M05 | HLK-10M05 | Ozdisan stock fell to 26 (333 on 2026-11-12), no incoming stock listed, lead time 7-8 weeks: order 26 now and back-order 74, or take the balance from LCSC (C403745, 4,433 pcs, 3.27 USD at 1 pc, https://www.lcsc.com/product-detail/C403745.html) |
| Q2,Q3 | S8050-J3Y | MMBT4401-TP | S8050 not stocked; MMBT4401 600 mA 40 V NPN SOT-23, same pinout |
| R4 | 120 | 0603SAJ0121T5E | R4 0402 -> 0603 1/10 W (2026-11-21): TRIG held on during a burst runs it continuously, up to 49 mW at 85 C |
| R122,R123 | 18R 0.125W | TC0525B180JT5F | the only 18 R 0805 in stock is the 0.1 % thin-film part |
| R132 | 0.5R 0.25W | HP06W2F500LT5E | 0.5 R 1 % 0.5 W 1206 (HP series); Uniohm RR1206J050KT5E 5 % 0.25 W is the cheaper alternative (0.046 USD) |
| R331 | 10k 1% | RT0402BRD0710KL | 10 k 0.1 % 25 ppm thin film instead of 1 % thick film: on 2026-11-23 every 10 k 1 % 0402 at Ozdisan is at zero stock (CQ02WGF1002TCE, 0402WGF1002TCE, RC0402FR-0710KL, AC0402FR-0710KL, RC1005F103CS, RK73H1ETTP1002F); same footprint, tighter tolerance, +0.05 USD per board |
| RN1-RN7 | 100R x4 | 4D02WGJ0101TCE | 33 R -> 100 R (EMC fix 2026-11-21): 150 R 0402x4 (4D02WGJ0151TCE) not stocked; 100 R is the nearest stocked value in the same 0402x4 footprint |
| TH220 | 10k NTC B3380 | TSM1B103F3381RZ | NCP18XH103F03RB not stocked; Thinking 10k 1 % B3380 0603 |
| U5 | MOC3083 | MOC3083X | MOC3052X -> MOC3083X (owner decision 2026-11-21): 800 V zero-cross; no 800 V random-phase driver stocked. X = VDE-approved version (Isocom DE93284 p.7) |
| U6 | SN74AHC1G14DBVR | SN74AHC1G14DBVR | value field aligned to the purchased AHC part (was SN74LVC1G14DBVR on the symbol, 2026-11-21) |
| D6 | 1.5KE440CA | 1.5KE440CA-TKS | replaces RV2 (TVR10561K MOV) across the triac: 1 kV surge clamp 620 V (EMC fix 2026-11-21) |
| RV3 | TVR10471KSY | TVR10471KSY | RV3 moved across the K1 contact, 300 V ac class (16 % margin to 253 V ac); MPQ 200. No thermally protected varistor stocked at Özdisan (Littelfuse TMOV14/20 all 0) |
| F1/F3 clips | 5x20 fuse clip | R3-5A | 5x20 PCB fuse clip, 4 per board (not in the schematic; clip pin diameter vs the 1.3 mm footprint holes to be confirmed) |
| TC1 (probe) | K-type thermocouple, M6 ring tip, 1 m | WRNT-02 | K-type, M6 ring-terminal tip, 1 m fibreglass/SS-braid lead, 0-600 C, bare ends; 147.29 TL + KDV = 2.91 USD at 50.57 TL/USD (2026-11-23); web stock shows '10+', ask Motorobit for 100 pcs; Motorobit SKU SNS.SCK.01.000085 |
| SF1-SF8 (on BP1,6,8,10,11,13,15,16) | SMD spring contact finger 7.5 mm | LT17BH0731 | SMD contact finger, 7.5 mm free height, hand-soldered last on the back landing pads; 8 per board = recommended contact set BP1, 6, 8, 10, 11, 13, 15, 16 (minimum set is 6: without BP8, BP16); reel of 700; the bench test of this finger is still open, so the quantity is provisional |
| DS1 (panel) | 7 inch 800x480 RGB TFT + capacitive touch | SAT70AT40D21-33KN-CTP-V1 | 7 inch 800x480 24-bit RGB panel with GT911 capacitive touch, box of 60; Ozdisan has 61 for the 100 needed, no incoming stock and no lead time shown: order 60 now and ask Ozdisan for a date on the other 40 |
| FB-FPC (on the TFT tail) | flat-cable ferrite core, 2 in series ≈ 142 Ω at 100 MHz | 2643178551 | NOT at Ozdisan; DigiKey 1934-1266-ND, one-piece flat-cable core, material 43, two in series on the TFT tail (owner decision 2026-11-23: the single large core 2643166551, 45 x 12.5 x 29 mm and 71 g, is too bulky and heavy). Each 26.5 x 6.6 x 12 mm, 8.2 g, opening 21.1 x 1.35 mm for the 20.5 mm tail (0.3 mm spare per side), typical 71 / 119 ohm at 100 / 250 MHz (Fair-Rite datasheet), so about 142 / 238 ohm for the pair against the 150 ohm from 100 MHz assumed in the simulations. Fit in the tail pocket of frame v2 and of the glass front is NOT checked |
| Q1 clip | TO-220 retaining spring for SK 409 | THF 409 TO 220 | NOT at Ozdisan (its clips are for Kunze profiles only); DigiKey 5496-THF409TO220-ND, Fischer's retaining spring for the SK 409 / SK 459 profiles, TO-220; minimum 100, DigiKey Marketplace item (ships from the supplier, like the heatsink). Owner decision 2026-11-23: clip on the current heatsink, no screw |
| Q1 thermal compound | silicone thermal compound, 100 g jar per 100 boards | AL-701 WHITE 100 GR | white silicone thermal compound, 100 g jar, between Q1 and HS1 (owner decision 2026-11-23, instead of a pad: Q1's tab is insulated). One jar is counted for 100 boards, about 1 g per board available; the Ozdisan page gives no thermal conductivity |
| J5 screw | M3 × 8 hex-socket cap screw | İMBUS CİVATA 3X8 SİYAH | M3 x 8 hex-socket cap screw, black, inserted from the PCB back through J5. Chosen for its head diameter (DIN 912: 5.5 mm, inside the 5.6 mm bare seat; the Ozdisan pan-head screws are DIN 7985 with a head up to 6.0 mm). Its head is 3.0 mm high instead of the 2.4 mm in the first requirement: about 1.6 mm to the Formex sheet and 2.0 mm to the panel back. Head dimensions are the standard's, not stated on the Ozdisan page |
| J5 ring lug | insulated ring terminal, M3 / M3.5, 0.5–1.5 mm² | L-KLS8-01103-RVS1.25-3.5 | red insulated ring terminal for 0.5-1.5 mm2, ring 5.7 mm wide, 17.8 mm long, hole 3.7 mm (M3.5), used on the M3 screw of J5 with the tongue at 150 degrees. The exact M3 size L-KLS8-01103-RV1.25-3 (hole 3.2 mm) is out of stock (1,000 incoming, 5-6 weeks): https://www.ozdisan.com/p/yuvarlak-tip-konnektorler-344/kls-electronic-l-kls8-01103-rv1-25-3-531584 |
| J5 flat washer | M3 flat washer 0.5 mm | MFWZ 003 | M3 flat washer, 0.53 mm, zinc-plated steel, on top of the ring lug |
| J5 spring washer | M3 spring washer | YAYLI RONDELA M3 INOX | M3 spring washer, stainless, 3.0 / 5.2 mm; the locking element under the nut |
| J5 nut | M3 hex nut | SOMUN M3 | M3 hex nut on the front, on top of the washers |
| J5 earth lead | 1 mm² green/yellow lead, 0.06 m per board (price per metre) | H05V-K 1 mm² green/yellow (NYAF) | bought from a local electrical supplier (owner decision 2026-11-23), no link; flexible single-core PVC lead, 1 mm2, green/yellow, fits the red 0.5-1.5 mm2 ring terminals. About 60 mm per board, 6 m for 100 boards. Price is an estimate: about 10 TL per metre seen on a price-comparison site, not verified. A linked alternative is Alpha Wire 3055 GY005 at DigiKey (18 AWG, 30.5 m spool, 123.75 USD) |
| FH9 ring lug | insulated ring terminal, M4, 0.5–1.5 mm² | L-KLS8-01103-RVS1.25-4 | red insulated ring terminal for 0.5-1.5 mm2, ring 6.6 mm wide, 20.1 mm long, hole 4.3 mm (M4), on chassis stud FH9; 125 in stock for the 100 needed. How it is held on FH9 (second M4 nut or under the existing nut) is still open and no M4 nut is listed |
| H1-H9 screws | ST2.9 × 9.5 pan-head self-tapping screw, A2 | ISO 7049-C / DIN 7981 ST2.9 × 9.5 A2 | pan-head self-tapping screw, cross recess, stainless A2, into the nine frame bosses under H1-H9 (blind 2.4 mm pilots, 0.3-0.4 Nm), as specified for frame v2 and the glass front (spec 12.11). Not at Ozdisan (its tapping screws are 2.2 x 6.5, PT 3 x 14 and 2.9 x 40 only) and no DigiKey part found (DigiKey's site showed a bot check), so it is a local purchase with no link. Price is an estimate from a 100-piece pack price seen online, not verified. The exact article exists at Wurth as ISO 7049-C A2 2.9 x 9.5: https://eshop.wuerth.de/Pan-head-tapping-screws-with-recessed-head-ISO-7049-A2-70-stainless-steel-plain-SCR-PANHD-ISO7049-C-A2-20H-H1-29X95/505122995.sku/en/US/EUR (page not opened by me; trade customers only) |

## Not purchased

- **J3** — solder-wire pads for the mains lead (no part)
- **J4** — solder-wire pads for the fan lead (no part)
- **R1** — the 1 kW heater element (customer-side)
- **V1** — simulation source, not a part

## Thermocouple probe (not on the PCB, screws into J20)

**Chosen: Motorobit WRNT-02** (BOM line TC1). Özdisan lists no thermocouple probes (sensor categories and site search checked). The probe that ships with the MAX6675 kit used on Rev2.1 is a generic **K-type, M6 ring-terminal tip, 1 m fibreglass-insulated lead with stainless-steel braid, 0–600 °C (heat-shrink at the tip softens above ≈300 °C), bare/spade ends**, which goes straight into the DG127H screw terminal J20 (red = +, blue = −; the braid can be bonded to the enclosure at the gland for EMC). Sources: Motorobit WRNT-02 (K-type, M6, 0–600 °C, 1 m) 147.29 TL + KDV ≈ 2.9 USD (2026-11-23), stock 10+, https://www.motorobit.com/wrnt-02-k-tip-0-600c-m6-termokupl-1-metre ; ProtoSupplies THC-3 (same part) 2.45 USD, https://protosupplies.com/product/thermocouple-k-type-m6-ring-terminal-sensor-1m/ ; for 100 pieces the same item is the usual AliExpress/LCSC-market 'K type thermocouple M6 1 m' at roughly 1.5–2.5 USD. If the chamber will exceed 300 °C at the sensor, use the stainless 4 × 30 mm cylindrical variant (same lead, 0–400 °C, no heat-shrink at the tip). Budget ≈ 2.5 USD per unit.

## Full BOM

| Ref | Qty/board | Value | Part (link) | Manufacturer | Supplier | Özdisan stock | MOQ | Order qty (100 boards) | Unit price USD | Line / board USD | Availability |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 1 | 100n 275VAC X2 | [C42P2104M6SC361](https://www.ozdisan.com/p/film-kapasitorler-179/faratronic-c42p2104m6sc361-488131) | FARATRONIC | Özdisan | 21368 | 2 | 100 | 0.05076 | 0.0508 | OK |
| C2 | 1 | 220uF 16V | [PKRJ-016V221ME070-T2.5](https://www.ozdisan.com/p/aluminyum-kapasitorler-180/koshin-pkrj-016v221me070-t2-5-354875) | Koshin | Özdisan | 15946 | 5 | 100 | 0.02784 | 0.0278 | OK |
| C4 | 1 | 10n 305VAC X2 | [C42Q2103K40A405](https://www.ozdisan.com/p/film-kapasitorler-179/faratronic-c42q2103k40a405-350791) | FARATRONIC | Özdisan | 9651 | 2 | 100 | 0.06048 | 0.0605 | OK |
| C5,C8 | 2 | 100n | [CC0402KRX7R9BB104](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/yageo-cc0402krx7r9bb104-609906) | Yageo | Özdisan | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| C6 | 1 | 1uF 6.3V X5R | [CL05A105KQ5NNNC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl05a105kq5nnnc-418943) | SAMSUNG | Özdisan | 1801951 | 25 | 100 | 0.00469 | 0.0047 | OK |
| C7 | 1 | 10uF | [CL10A106KP8NNNC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl10a106kp8nnnc-350863) | SAMSUNG | Özdisan | 1265387 | 2 | 100 | 0.05537 | 0.0554 | OK |
| C40 | 1 | 1uF 275VAC X2 | [C42P2105KBSC400](https://www.ozdisan.com/p/film-kapasitorler-179/faratronic-c42p2105kbsc400-466649) | FARATRONIC | Özdisan | 56805 | 1 | 100 | 0.22272 | 0.2227 | OK |
| C110,C111 | 2 | 27pF C0G | [GRM1555C1H270JA01D](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/murata-grm1555c1h270ja01d-810946) | Murata | Özdisan | 50730 | 20 | 200 | 0.00457 | 0.0091 | OK |
| C112-C115,C117-C119,C123,C126,C223,C225,C226 | 12 | 100nF 16V X7R | [CC0402KRX7R9BB104](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/yageo-cc0402krx7r9bb104-609906) | Yageo | Özdisan | 4545 | 5 | 1800 | 0.01923 | 0.2308 | OK |
| C116,C122,C336 | 3 | 10uF 6.3V X5R | [CL21A106KPFNNNE](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl21a106kpfnnne-336384) | Samsung | Özdisan | 351570 | 5 | 700 | 0.02152 | 0.0646 | OK |
| C120,C121,C337 | 3 | 1uF 6.3V X7R | [C1608X7R1C105K080AC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/tdk-c1608x7r1c105k080ac-600193) | TDK | Özdisan | 4120 | 5 | 500 | 0.04085 | 0.1225 | OK |
| C124,C127,C330,C331 | 4 | 10uF 10V X5R | [CL21A106KPFNNNE](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl21a106kpfnnne-336384) | Samsung | Özdisan | 351570 | 5 | 700 | 0.02152 | 0.0861 | OK |
| C125 | 1 | 4.7uF 25V X7R | [CL21A475KBQNNNE](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl21a475kbqnnne-360305) | Samsung | Özdisan | 41993 | 1 | 100 | 0.10025 | 0.1003 | OK |
| C128 | 1 | 47uF 10V | [EEEFK1C470UR](https://www.ozdisan.com/p/aluminyum-kapasitorler-180/panasoniceurope-eeefk1c470ur-1102511) | Panasonic | Özdisan | 315 | 1 | 100 | 0.18224 | 0.1822 | OK |
| C129,C332 | 2 | 100nF 25V X7R | [CC0402KRX7R9BB104](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/yageo-cc0402krx7r9bb104-609906) | Yageo | Özdisan | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| C130-C133 | 4 | 1nF 50V C0G | [CL05C102JB5NNNC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl05c102jb5nnnc-519291) | Samsung | Özdisan | 2181 | 10 | 500 | 0.01398 | 0.0559 | OK |
| C220 | 1 | 100nF 50V X7R | [CC0603KRX7R9BB104](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/yageo-cc0603krx7r9bb104-476015) | Yageo | Özdisan | 1801416 | 10 | 100 | 0.01727 | 0.0173 | OK |
| C221,C222 | 2 | 10nF 50V C0G 1% | [CL10B103KB8NNNC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl10b103kb8nnnc-9649) | Samsung | Özdisan | 9376446 | 20 | 200 | 0.00709 | 0.0142 | OK |
| C224,C335 | 2 | 1uF 16V X7R | [C1608X7R1C105K080AC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/tdk-c1608x7r1c105k080ac-600193) | TDK | Özdisan | 4120 | 5 | 500 | 0.04085 | 0.0817 | OK |
| C333,C334 | 2 | 22uF 10V X5R | [CL21A226KOQNNNE](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl21a226koqnnne-399002) | Samsung | Özdisan | 814 | 1 | 200 | 0.18779 | 0.3756 | OK |
| D5 | 1 | 1N4148W | [1N4148W_R1_00301](https://www.ozdisan.com/p/dogrultucu-diyotlar-389/panjit-1n4148w-r1-00301-1579142) | Panjit | Özdisan | 230130 | 5 | 100 | 0.02021 | 0.0202 | OK |
| D111 | 1 | SS14 | [SS14-SMA-N-JQ](https://www.ozdisan.com/p/schottky-diyotlar-385/jiaqi-ss14-sma-n-jq-533239) | Jiaqi | Özdisan | 69278 | 5 | 100 | 0.02606 | 0.0261 | OK |
| D112,D113,D115,D116,D220,D221 | 6 | PESD5V0S1BA | [PESD5V0S1BA,115](https://www.ozdisan.com/p/tvs-diyotlar-386/nexperia-pesd5v0s1ba-115-488980) | NEXPERIA | Özdisan | 10966 | 1 | 600 | 0.11625 | 0.6975 | OK |
| D114 | 1 | 15V 500mW | [MMSZ15V-HT](https://www.ozdisan.com/p/zener-diyotlar-390/hottech-mmsz15v-ht-465503) | Hottech | Özdisan | 44030 | 5 | 100 | 0.01873 | 0.0187 | OK |
| F1 | 1 | 250VAC 1A Slow Blow | [STC1A250V](https://www.ozdisan.com/p/sigortalar-849/reomax-stc1a250v-475613) | Reomax | Özdisan | 3953 | 1 | 100 | 0.04685 | 0.0469 | OK |
| F3 | 1 | 250VAC 8A Normal | [5GT8A](https://www.ozdisan.com/p/sigortalar-849/reomax-5gt8a-445944) | Reomax | Özdisan | 12835 | 5 | 100 | 0.01700 | 0.0170 | OK |
| HS1 | 1 | SK 409 63,5 STC | [SK 409 63,5 STC TO 220](https://www.digikey.com/en/products/detail/fischer-elektronik/SK-409-63-5-STC-TO-220/25833367) | Fischer Elektronik | DigiKey | 995 | 5 | 100 | 2.60000 | 2.6000 | OK |
| J2 | 1 | FTDI | [DS1021-1X6SF11-B](https://www.ozdisan.com/p/pin-headerlar-293/connfly-ds1021-1x6sf11-b-423407) | Connfly | Özdisan | 12224 | 2 | 100 | 0.02376 | 0.0238 | OK |
| J10 | 1 | TFT_SAT070AT40D21_FPC40 | [DS1020-09-40VBT1B](https://www.ozdisan.com/p/ffc-ve-fpc-konnektorler-716/connfly-ds1020-09-40vbt1b-358712) | CONNFLY | Özdisan | 161 | 1 | 100 | 0.38183 | 0.3818 | OK |
| J11 | 1 | CTP_GT911_FPC6 | [L-KLS1-242D-1.2-06-T-U-R](https://www.ozdisan.com/p/ffc-ve-fpc-konnektorler-716/kls-electronic-l-kls1-242d-1-2-06-t-u-r-787840) | KLS ELECTRONIC | Özdisan | 1123 | 1 | 100 | 0.19290 | 0.1929 | OK |
| J20 | 1 | K-type TC | [DG127H-5.08-02P-14-00AH](https://www.ozdisan.com/p/pcb-klemensler-410/degson-dg127h-5-08-02p-14-00ah-1585380) | DEGSON | Özdisan | 43697 | 1 | 100 | 0.15014 | 0.1501 | OK |
| K1 | 1 | RZ03-1A4-D005 | [RZ03-1A4-D005](https://www.ozdisan.com/p/genel-tip-roleler-403/te-connectivity-rz03-1a4-d005-1211236) | TE CONNECTIVITY | Özdisan | 110352 | 1 | 100 | 0.82527 | 0.8253 | OK |
| L1 | 1 | LFU09V-103 | [LFU09V-103](https://www.ozdisan.com/p/ortak-mod-bobinler-470/core-master-lfu09v-103-526799) | CORE MASTER | Özdisan | 8868 | 1 | 100 | 0.38576 | 0.3858 | OK |
| L11 | 1 | 10uH 1A | [PCD0403MT100](https://www.ozdisan.com/p/sabit-induktorler-468/viking-pcd0403mt100-1061950) | VIKING | Özdisan | 8939 | 1 | 100 | 0.11086 | 0.1109 | OK |
| L12 | 1 | 10uH 1A | [PCD0403MT100](https://www.ozdisan.com/p/sabit-induktorler-468/viking-pcd0403mt100-1061950) | VIKING | Özdisan | 8939 | 1 | 100 | 0.11086 | 0.1109 | OK |
| L30 | 1 | 4.7uH 4A | [SRI0605B-4R7M](https://www.ozdisan.com/p/sabit-induktorler-468/core-master-sri0605b-4r7m-587415) | CORE MASTER | Özdisan | 1949 | 1 | 100 | 0.32479 | 0.3248 | OK |
| L40 | 1 | 100uH 5A | [RC1415U-101K](https://www.ozdisan.com/p/sabit-induktorler-468/core-master-rc1415u-101k-500941) | CORE MASTER | Özdisan | 594 | 1 | 100 | 0.68691 | 0.6869 | OK |
| PS1 | 1 | HLK-10M05 | [HLK-10M05](https://www.ozdisan.com/p/ac-dc-donusturuculer-606/hi-link-hlk-10m05-702430) | HI-LINK | Özdisan | 26 | 1 | 100 | 3.90413 | 3.9041 | SHORT: stock 26 < 100 |
| Q1 | 1 | BTA24-800CWRG | [BTA24-800CWRG](https://www.ozdisan.com/p/discrete-triyaklar-420/stm-bta24-800cwrg-360751) | STM | Özdisan | 5086 | 1 | 100 | 1.27265 | 1.2727 | OK |
| Q2,Q3 | 2 | S8050-J3Y | [MMBT4401-TP](https://www.ozdisan.com/p/discrete-transistorler-442/m-c-c-mmbt4401-tp-1211020) | MCC | Özdisan | 1780 | 20 | 200 | 0.01149 | 0.0230 | OK |
| Q4 | 1 | BC817-25-HT | [BC817-25-HT](https://www.ozdisan.com/p/discrete-transistorler-442/hottech-bc817-25-ht-448900) | HOTTECH | Özdisan | 17760 | 10 | 100 | 0.01294 | 0.0129 | OK |
| R2,R3 | 2 | 360 1/2W 350V | [MFR-50FTF52-360R](https://www.ozdisan.com/p/tht-dip-direncler-193/yageo-mfr-50ftf52-360r-923549) | YAGEO | Özdisan | 5214 | 5 | 200 | 0.02561 | 0.0512 | OK |
| R4 | 1 | 120 | [0603SAJ0121T5E](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0603saj0121t5e-341209) | ROYALOHM | Özdisan | 72660 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R5 | 1 | 47 2W 500V | [KNP02SJ0470A10](https://www.ozdisan.com/p/tht-dip-direncler-193/royalohm-knp02sj0470a10-690542) | ROYALOHM | Özdisan | 590 | 5 | 100 | 0.02610 | 0.0261 | OK |
| R6,R7 | 2 | 33k 1W 500V | [CFR01SJ0333A10](https://www.ozdisan.com/p/tht-dip-direncler-193/royalohm-cfr01sj0333a10-444800) | ROYALOHM | Özdisan | 4213 | 5 | 200 | 0.02552 | 0.0510 | OK |
| R8,R10-R15,R124,R224 | 9 | 10k | [0402WGJ0103TCE](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0402wgj0103tce-362331) | ROYALOHM | Özdisan | 146800 | 200 | 1000 | 0.00044 | 0.0040 | OK |
| R9 | 1 | 180 1/10W | [0603SAJ0181T5E](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0603saj0181t5e-336227) | ROYALOHM | Özdisan | 217830 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R16 | 1 | 1k | [0402WGJ0102TCE](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0402wgj0102tce-431887) | ROYALOHM | Özdisan | 298200 | 200 | 200 | 0.00050 | 0.0005 | OK |
| R110-R121 | 12 | 33R | [RC0402JR-0733RL](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/yageo-rc0402jr-0733rl-832557) | Yageo | Özdisan | 58300 | 100 | 1200 | 0.00145 | 0.0174 | OK |
| R122,R123 | 2 | 18R 0.125W | [TC0525B180JT5F](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-tc0525b180jt5f-442649) | Royalohm | Özdisan | 8395 | 5 | 200 | 0.03348 | 0.0670 | OK |
| R125,R129 | 2 | 0R | [0805WAJ0000T5E](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0805waj0000t5e-337715) | Royalohm | Özdisan | 14300 | 100 | 200 | 0.00153 | 0.0031 | OK |
| R126,R128 | 2 | 0R | [CQ02WGJ0000TCE](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-cq02wgj0000tce-587856) | Royalohm | Özdisan | 31704 | 200 | 200 | 0.00076 | 0.0015 | OK |
| R127 | 1 | 100k | [CQ02WGF1003TCE](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-cq02wgf1003tce-587906) | Royalohm | Özdisan | 41120 | 200 | 200 | 0.00090 | 0.0009 | OK |
| R130,R131 | 2 | 2.2k | [AC0402JR-072K2L](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/yageo-ac0402jr-072k2l-650156) | Yageo | Özdisan | 294360 | 50 | 200 | 0.00216 | 0.0043 | OK |
| R132 | 1 | 0.5R 0.25W | [HP06W2F500LT5E](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-hp06w2f500lt5e-602953) | Royalohm | Özdisan | 7610 | 2 | 100 | 0.05084 | 0.0508 | OK |
| R220,R221 | 2 | 1k 0.1% | [TC0325B1001T5F](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-tc0325b1001t5f-700043) | Royalohm | Özdisan | 25023 | 5 | 200 | 0.02778 | 0.0556 | OK |
| R222,R223 | 2 | 10M | [0603SAJ0106T5E](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0603saj0106t5e-343167) | Royalohm | Özdisan | 114300 | 200 | 200 | 0.00090 | 0.0018 | OK |
| R225-R227 | 3 | 10k 0.1% | [TC0325B1002T5F](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-tc0325b1002t5f-600390) | Royalohm | Özdisan | 71251 | 5 | 300 | 0.02778 | 0.0833 | OK |
| R330 | 1 | 33.2k 1% | [0402WGF3322TCE](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/royalohm-0402wgf3322tce-506353) | Royalohm | Özdisan | 12048 | 200 | 200 | 0.00059 | 0.0006 | OK |
| R331 | 1 | 10k 1% | [RT0402BRD0710KL](https://www.ozdisan.com/p/smt-smd-ve-cip-direncler-194/yageo-rt0402brd0710kl-1048858) | YAGEO | Özdisan | 500000 | 5 | 100 | 0.04921 | 0.0492 | OK |
| RN1-RN7 | 7 | 100R x4 | [4D02WGJ0101TCE](https://www.ozdisan.com/p/ag-ve-sira-direncler-196/royalohm-4d02wgj0101tce-467030) | ROYALOHM | Özdisan | 10227 | 20 | 700 | 0.00487 | 0.0341 | OK |
| RV1 | 1 | TVR14431KSU15Y | [TVR14431KSU15Y](https://www.ozdisan.com/p/varistorler-863/thinking-tvr14431ksu15y-603701) | Thinking | Özdisan | 14877 | 1 | 100 | 0.10859 | 0.1086 | OK |
| TH220 | 1 | 10k NTC B3380 | [TSM1B103F3381RZ](https://www.ozdisan.com/p/ntc-termistorler-852/thinking-tsm1b103f3381rz-509282) | Thinking | Özdisan | 6906 | 5 | 100 | 0.08670 | 0.0867 | OK |
| U1 | 1 | H11AA1 | [H11AA1X](https://www.ozdisan.com/p/transistor-ve-fotovoltaik-cikisli-optokuplorler-189/isocom-h11aa1x-636378) | Isocom | Özdisan | 1568 | 1 | 100 | 0.38750 | 0.3875 | OK |
| U3 | 1 | ESP32-WROOM-32E-N16 | [ESP32-WROOM-32E-N16](https://www.ozdisan.com/p/wifi-modulleri-652/espressif-systems-esp32-wroom-32e-n16-690893) | ESPRESSIF SYSTEMS | Özdisan | 914 | 1 | 100 | 4.75200 | 4.7520 | OK |
| U5 | 1 | MOC3083 | [MOC3083X](https://www.ozdisan.com/p/triyak-scr-cikisli-optokuplorler-190/isocom-moc3083x-636495) | Isocom | Özdisan | 930 | 1 | 100 | 0.49275 | 0.4928 | OK |
| U6 | 1 | SN74AHC1G14DBVR | [SN74AHC1G14DBVR](https://www.ozdisan.com/p/logic-kapi-ve-cevirici-entegreleri-248/texas-sn74ahc1g14dbvr-616783) | TEXAS | Özdisan | 23130 | 1 | 100 | 0.08700 | 0.0870 | OK |
| U10 | 1 | SSD1963QL9 | [SSD1963QL9](https://www.ozdisan.com/p/arayuz-kontrolor-entegreleri-227/solomon-ssd1963ql9-353972) | SOLOMON | Özdisan | 278 | 1 | 100 | 5.15494 | 5.1549 | OK |
| U11 | 1 | MIC2288YD5 | [MIC2288YD5-TR](https://www.ozdisan.com/p/dc-dc-voltaj-regulatorleri-275/micrel-microchip-mic2288yd5-tr-613161) | MICREL-MICROCHIP | Özdisan | 5640 | 1 | 100 | 0.85840 | 0.8584 | OK |
| U20 | 1 | ADS1115IDGSR | [ADS1115IDGSR](https://www.ozdisan.com/p/analogtan-dijitale-donusturucu-entegreler-adc-225/texas-ads1115idgsr-616336) | TEXAS | Özdisan | 3806 | 1 | 100 | 6.09870 | 6.0987 | OK |
| U30 | 1 | TPS562201DDCR | [TPS562201DDCR](https://www.ozdisan.com/p/dc-dc-voltaj-regulatorleri-275/texas-tps562201ddcr-708034) | TEXAS | Özdisan | 2319 | 1 | 100 | 0.38280 | 0.3828 | OK |
| U31 | 1 | LD1117S12CTR | [LD1117S12CTR](https://www.ozdisan.com/p/lineer-voltaj-regulatorleri-279/stm-ld1117s12ctr-427395) | STM | Özdisan | 2500 | 1 | 100 | 0.13999 | 0.1400 | OK |
| Y10 | 1 | 10MHz | [CX3225GB10000P0HPQCC](https://www.ozdisan.com/p/kristaller-508/kyocera-avx-cx3225gb10000p0hpqcc-728628) | Kyocera AVX | Özdisan | 3906 | 1 | 100 | 0.27840 | 0.2784 | OK |
| D6 | 1 | 1.5KE440CA | [1.5KE440CA-TKS](https://www.ozdisan.com/p/tvs-diyotlar-386/thinking-1-5ke440ca-tks-639232) | THINKING | Özdisan | 1083 | 1 | 100 | 0.34684 | 0.3468 | OK |
| C9 | 1 | 1nF 50V C0G | [CL05C102JB5NNNC](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/samsung-cl05c102jb5nnnc-519291) | Samsung | Özdisan | 2181 | 10 | 500 | 0.01398 | 0.0140 | OK |
| C134,C135 | 2 | 100nF 50V X7R | [CC0402KRX7R9BB104](https://www.ozdisan.com/p/smt-smd-ve-mlcc-kapasitorler-184/yageo-cc0402krx7r9bb104-609906) | Yageo | Özdisan | 4545 | 5 | 1800 | 0.01923 | 0.0385 | OK |
| RV3 | 1 | TVR10471KSY | [TVR10471KSY](https://www.ozdisan.com/p/varistorler-863/thinking-tvr10471ksy-351283) | Thinking | Özdisan | 81163 | 1 | 100 | 0.07112 | 0.0711 | OK |
| F1/F3 clips | 4 | 5x20 fuse clip | [R3-5A](https://www.ozdisan.com/p/sigorta-yuvalari-847/reomax-r3-5a-575555) | Reomax | Özdisan | 39652 | 2 | 400 | 0.02272 | 0.0909 | OK |
| TC1 (probe) | 1 | K-type thermocouple, M6 ring tip, 1 m | [WRNT-02](https://www.motorobit.com/wrnt-02-k-tip-0-600c-m6-termokupl-1-metre) | Motorobit | Motorobit | 10 | 1 | 100 | 2.91000 | 2.9100 | SHORT: stock 10 < 100 |
| SF1-SF8 (on BP1,6,8,10,11,13,15,16) | 8 | SMD spring contact finger 7.5 mm | [LT17BH0731](https://www.ozdisan.com/p/rf-aksesuarlari-657/laird-signal-lt17bh0731-708029) | LAIRD SIGNAL | Özdisan | 602220 | 1 | 800 | 0.11338 | 0.9070 | OK |
| DS1 (panel) | 1 | 7 inch 800x480 RGB TFT + capacitive touch | [SAT70AT40D21-33KN-CTP-V1](https://www.ozdisan.com/p/tft-paneller-381/satoz-sat70at40d21-33kn-ctp-v1-621995) | SATOZ | Özdisan | 61 | 1 | 100 | 33.81000 | 33.8100 | SHORT: stock 61 < 100 |
| FB-FPC (on the TFT tail) | 2 | flat-cable ferrite core, 2 in series ≈ 142 Ω at 100 MHz | [2643178551](https://www.digikey.com/en/products/detail/fair-rite-products-corp/2643178551/8594019) | Fair-Rite | DigiKey | 3044 | 1 | 200 | 0.75990 | 1.5198 | OK |
| Q1 clip | 1 | TO-220 retaining spring for SK 409 | [THF 409 TO 220](https://www.digikey.com/en/products/detail/fischer-elektronik/THF-409-TO-220/25835046) | Fischer Elektronik | DigiKey | 29800 | 100 | 100 | 0.14000 | 0.1400 | OK |
| Q1 thermal compound | 0.01 | silicone thermal compound, 100 g jar per 100 boards | [AL-701 WHITE 100 GR](https://www.ozdisan.com/p/sogutucu-aksesuarlari-463/alpa-al-701-white-100-gr-1580017) | ALPA | Özdisan | 77 | 1 | 1 | 3.80512 | 0.0381 | OK |
| J5 screw | 1 | M3 × 8 hex-socket cap screw | [İMBUS CİVATA 3X8 SİYAH](https://www.ozdisan.com/p/civatalar-793/ler-cvata-mbus-cvata-3x8-syah-370549) | İLERİ CİVATA | Özdisan | 800 | 5 | 100 | 0.06287 | 0.0629 | OK |
| J5 ring lug | 1 | insulated ring terminal, M3 / M3.5, 0.5–1.5 mm² | [L-KLS8-01103-RVS1.25-3.5](https://www.ozdisan.com/p/yuvarlak-tip-konnektorler-344/kls-electronic-l-kls8-01103-rvs1-25-3-5-531595) | KLS ELECTRONIC | Özdisan | 547 | 5 | 100 | 0.03335 | 0.0333 | OK |
| J5 flat washer | 1 | M3 flat washer 0.5 mm | [MFWZ 003](https://www.ozdisan.com/p/somunlar-ve-rondelalar-794/akin-cvata-mfwz-003-1590223) | AKIN CİVATA | Özdisan | 1195 | 1 | 100 | 0.00664 | 0.0066 | OK |
| J5 spring washer | 1 | M3 spring washer | [YAYLI RONDELA M3 INOX](https://www.ozdisan.com/p/somunlar-ve-rondelalar-794/ler-cvata-yayli-rondela-m3-inox-358162) | İLERİ CİVATA | Özdisan | 4980 | 10 | 100 | 0.01101 | 0.0110 | OK |
| J5 nut | 1 | M3 hex nut | [SOMUN M3](https://www.ozdisan.com/p/somunlar-ve-rondelalar-794/oem-somun-m3-343878) | OEM | Özdisan | 966 | 1 | 100 | 0.00873 | 0.0087 | OK |
| J5 earth lead | 0.06 | 1 mm² green/yellow lead, 0.06 m per board (price per metre) | H05V-K 1 mm² green/yellow (NYAF) | any (e.g. Prysmian, Öznur) | Local |  | 1 | 6 | 0.20000 | 0.0120 | local purchase |
| FH9 ring lug | 1 | insulated ring terminal, M4, 0.5–1.5 mm² | [L-KLS8-01103-RVS1.25-4](https://www.ozdisan.com/p/yuvarlak-tip-konnektorler-344/kls-electronic-l-kls8-01103-rvs1-25-4-531596) | KLS ELECTRONIC | Özdisan | 125 | 5 | 100 | 0.02438 | 0.0244 | OK |
| H1-H9 screws | 9 | ST2.9 × 9.5 pan-head self-tapping screw, A2 | ISO 7049-C / DIN 7981 ST2.9 × 9.5 A2 | any (e.g. Würth) | Local |  | 1 | 900 | 0.03000 | 0.2700 | local purchase |
