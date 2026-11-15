# R1: Glass front: reference part, touch through cover glass, optical bonding, glass-to-frame bonding

Rev3.0 glass-front upgrade, research note R1, 2026-11-15. Scope: four topics set by the lead. The mechanical concept and Turkish sourcing are covered by other agents and are not repeated here.

**Tags.** **[F]** = fact with a source (numbered `[Sn]`, list at the end). **[P]** = typical industry practice; no single authoritative source was found. **[I]** = my inference or calculation. A claim marked "(excerpt)" comes from a search-result excerpt of a page that could not be opened (blocked, region-locked or behind Cloudflare). Repo inputs: the panel datasheet `Datasheets/SAT070AT40D21Y0-35100T071KN (7in TFT + GT911 CTP).pdf` (SAT V.2, LCM drawing p.16, Fannal CTP FN070A133 / drawing CT0476-V2.0 p.27) and `Design Reports/Rev3.0/Rev3.0_Frame_Design.md` §1–2.

---

## 0. Verdicts first

1. **DA82-02711L** is the service ("A/S") version of a Samsung **refrigerator Family Hub "cover display" assembly**: the large (~21.5") touchscreen unit in the fridge door. It is not a small oven-style display. No construction details (glass thickness, bonding, fixing) are published or reachable. Use it as a concept reference only. The numeric template below comes from a well-documented 7" analogue, Riverdi uxTouch.
2. **Touch through an added 3 mm glass on this GT911 module: marginal. 4 mm: not acceptable.** Total glass over the sensor would be 4.2 mm, about 4.7 mm glass-equivalent, against the datasheet maximum of 2 mm glass. Expect roughly a fifth of today's signal. Confidence 70 %. The thresholds can be rewritten over I²C. Whether that is enough must be settled by the 10-minute bench test in §2.6 before any glass is ordered. An **air gap kills touch** at these thicknesses (high confidence).
3. **Optical bonding in house:** recommended process is a **silicone LOCA (liquid optically clear adhesive) with dual cure (UV + moisture or heat), about 0.3 mm bond line, with active alignment on the lit display**. Dry OCA (optically clear adhesive film) is cleaner, but it needs vacuum lamination plus an autoclave, cannot be re-aligned after contact, and tolerates tempered-glass bow poorly. Air gap with a gasket: no. It fails touch, and optically the window reads grey, not black-on-black.
4. **Glass to frame:** a jig-referenced **neutral-cure silicone bead about 1.5 mm thick on an 8 mm land** gives a truly flush face that does not depend on glass-thickness tolerance. Foam tape (VHB) is stronger on day 1 but fixes the gap thickness, so flushness is no better than about ±0.15–0.25 mm. Bond onto **fired ceramic frit** if the tempering house offers it; otherwise onto 2K organic ink, but only after adhesion qualification.
5. **Biggest risk:** touch on the GT911 through 3 mm of added glass. The clean fix is a **custom CTP (capacitive touch panel) from the module maker with the oversize printed cover lens laminated directly to the sensor**, which removes one glass layer and one bond and gets a factory-tuned controller. That option also removes the in-house optical bonding step.

---

## 1. Samsung DA82-02711L as a reference

### 1.1 What the part is

| claim | tag | source |
|---|---|---|
| Listed as "Samsung DA82-02711L Cover Display Assembly", refrigerator part, about USD 665–740 | [F] | [S1][S3] |
| Replaces / cross-references **DA97-20810D**, also listed as AP7012227, EAP16554118, PS16554118 | [F] | [S1][S2] |
| One retailer's title reads "Assembly Cover Display **Rf600**" | [F] (excerpt) | [S4] |
| DA97-20810D: refrigerator display cover assembly for bottom-mount models; text names "rf6000t and **f-hub 4.0**" | [F] (excerpt) | [S5] |
| Sister part DA82-02711D is the listed substitute for **DA97-17068V**, the "Family Hub LCD display" of RF28R7551SR/AA | [F] | [S6] |
| Sister part DA82-02711V replaces DA97-20810L; listed for "Rf9000a, Us, **Hub6.0**" | [F] (excerpt) | [S7] |
| Family Hub = a 21.5" full-HD LCD touchscreen set into the upper-right door (later models 32") | [F] (excerpt) | [S8] |
| A comparable Family Hub display assembly ships in a 16 × 31 × 5 in box at 16 lb | [F] | [S10] |
| A repair shop describes the Family Hub display as one integrated unit (LCD + digitizer bonded + processor board + Wi-Fi). Secondary source | [F] | [S9] |

**Conclusion [I]:** the DA82-02711 suffix family is Samsung's service replacement for the **Family Hub door display** (Family Hub 4.0 / 6.0 generations). It is 3× the diagonal of our panel, and it includes a full Tizen computer.

### 1.2 Construction: what could and could not be established
- Glass thickness, edge finish, mask method (frit or organic ink), touch-to-glass bonding (optical or air gap), glass-to-carrier joint and door fixing: **not found.** Every retailer page with photos or diagrams (PartSelect, AppliancePartsPros, HnK, ReliableParts, Encompass, eBay) returned 403 or a Cloudflare challenge. The Samsung service manuals on ManualsLib sit behind a Cloudflare challenge, which was not bypassed. The samsungparts.com page has no photo and an empty model list [S3]. No teardown was found. **I am not going to describe the Samsung construction. Anything stated about it would be invented.**
- One weak data point: a repair blog states the LCD and digitizer are bonded and replaced as one unit [S9]. "Bonded" may mean optical bonding or a perimeter tape. **Unverified.**
- If the owner has the physical part or photos, a 15-minute inspection answers most of these questions (see open risks).

### 1.3 Related, documented reference: Riverdi uxTouch 7" (RVT70HSPNWC00)
This is the closest well-documented analogue: a 7" (164.90 × 100.00 mm) TFT with an oversize printed cover glass, front-mounted to a housing by adhesive.

| item | value | tag/source |
|---|---|---|
| Cover glass (CG) outline | 179.96 × 119.00 mm, i.e. the TFT outline + 15.1 / 19.0 mm | [F] [S12] |
| CG thickness | **1.1 mm** | [F] [S12] |
| Stack | CG 1.1 / SCA (solid OCA) **0.2** / sensor 0.55 / DST 0.6 to TFT; touch panel G+G | [F] [S12] |
| CG-to-TFT bonding | **"Air Bonding"** (tape frame). The LCD is not optically bonded | [F] [S12] |
| CG corners / edge | **R5.00**; edge chamfer **0.20 × 45°** both faces | [F] [S12] |
| Mask | black mask printing, RAL 9005 | [F] [S12] |
| Mounting to housing | double-sided tape **3M 9495LE, 0.175 mm**, on the CG border; "can be mounted by fastening the glass to the housing"; rear support brackets recommended | [F] [S12][S13][S14] |
| Touch controller | ILITEK ILI2132A; Riverdi rates ILI2132A / ILI2511 for glass up to 10 mm, EXC80W32 up to 15 mm | [F] [S12][S15] |
| Linearity | ±1.5 mm | [F] [S12] |

Industrial HMI glass fronts, e.g. Beckhoff CP29xx: aluminium or stainless housing, glass pane with anti-reflection coating, projected-capacitive touch, IP65 front [F, S43]. No bonding details are published.

### 1.4 The construction pattern this class uses [P/I]
Printed glass (black on the inner face, surface 2) → touch sensor laminated to the glass → LCD either air-bonded with a tape frame (Riverdi) or fully bonded (premium) → glass border bonded to a carrier → carrier fixed from behind. Our plan matches this pattern. The one structural difference: **our touch sensor already has its own 0.7 mm cover lens, so we would stack glass on glass.** That difference drives §2 and §3.

### Design consequences
- Adopt the stack **printed glass (surface 2) / full-face optical bond / existing CTP+LCM / module retained mechanically to the frame from behind / perimeter bead from glass border to frame land / frame to sheet (v2 studs)**. With the module both optically bonded and mechanically retained, the glass has two independent load paths. A single-path adhesive failure cannot drop glass and module out of the front. [I]
- Take dimensions from the Riverdi template: **corner R5**, edge **0.2–0.3 × 45° arris on both faces** (larger for 3 mm thermally tempered glass, §4.6), **black border ≥ 7.5 mm** each side, mask RAL 9005.
- Treat DA82-02711L as a styling reference only.

### Open risks
- The Samsung construction is unverified. If the owner holds a sample, measure the glass thickness (caliper), look edge-on for a bond line between glass and LCD (optical bond: no visible air gap; air gap: a double reflection of a pen tip), and check whether the black border is matte and slightly rough (fired ceramic frit) or glossy (organic ink).

---

## 2. Touch through an added cover glass (GT911)

### 2.1 Existing CTP: Fannal FN070A133 / drawing CT0476-V2.0 (datasheet pp. 20–27)

| item | value | tag |
|---|---|---|
| Structure | **G+G**; cover glass **0.7 ± 0.05 soda-lime**, OCR **0.175**, ITO sensor glass **0.7 ± 0.05**; TP 1.58 ± 0.15; + PU foam tape Y9040B **0.4** to the LCM → TP+PU **1.98 ± 0.25** | [F] datasheet p.27 |
| CTP-to-LCD | **air gap**: 0.4 mm PU tape frame, no optical bond | [F] p.27 |
| Cover outline (OD) | 164.9 ± 0.15 × 100 ± 0.15, R0.3 corners, **C0.15 all round** | [F] p.27 |
| Cover view area (black-print window) | **155.08 ± 0.2 × 86.92 ± 0.2** | [F] p.27 |
| VA position (front view) | left 3.53 ± 0.2, bottom (FPC side) 8.85 ± 0.2 → right 6.29, top 4.23 (derived); VA centre 1.38 mm off-centre in x and 2.31 mm towards the top | [F]/[I] p.27; matches frame doc window centre |
| Sensor active area (AA) | **156.48 × 88.32** (0.70 mm beyond the VA each side) | [F] p.27 |
| Sensor OD | 164.3 ± 0.2 × 99.4 ± 0.2 | [F] p.27 |
| LCD active area | **154.08 × 85.92**; bezel opening 156.80 × 89.10 ± 0.3; LCM 164.90 ± 0.3 × 100.00 ± 0.3 × 3.34 ± 0.3 | [F] p.16 |
| Window rule | "TP window size unilateral increase 0.3~0.5mm than LCM A.A" → CTP VA = LCD AA + 0.50 / side | [F] p.16 |
| Controller / config | GT911, FW 0x95, factory config `FN070A133_GT911_VER95_20200116.cfg`, test `FN070A133_CTP_MP.ini` | [F] p.24 |
| CTP mechanical | operating force ≤ 10 g finger; impact: **steel ball 132 g from 25 cm (0.32 J)** at centre; static 5 kg over Ø10 cm | [F] p.24 |
| Temperatures | operating −20…70 °C, storage −30…80 °C | [F] p.23 |
| Inconsistency | LCM general spec says "Normally White"; LCM drawing note says "transmissive Normally Black" | [F] p.4 vs p.16 |

### 2.2 GT911: what Goodix specifies
- **Cover lens supported: 0.55 mm ≤ glass ≤ 2 mm; 0.5 mm ≤ PMMA ≤ 1.2 mm** ("for details refer to Sensor Design Guide"), datasheet Rev.10 (2015) [F, S18]. An older Chinese datasheet (2013) gives **0.7 mm ≤ glass ≤ 2 mm** [F, S19]. Both cap glass at **2 mm**. The larger-panel GT9110P carries the same 0.55–2 mm limit [F, S25].
- 26 Tx × 14 Rx channels; 7"–8" panels; adaptive frequency hopping; self-calibration at power-up (first 200 ms) and automatic drift compensation; flash embedded, in-system reprogrammable; operating −40…+85 °C [F, S18].
- Electrode pitch [I]: if all channels are used over the 156.48 × 88.32 AA, the pitch is about **6.0 × 6.3 mm**. The real channel count is in config bytes 0x8062–0x8064 and 0x80B7–0x80EE.

### 2.3 What adding glass does
Glass-equivalent thickness d_eq = Σ tᵢ · (εr,glass / εr,i), with εr glass ≈ 7 and OCA ≈ 4. 3M's CEF05/8146 OCA measures **εr 4.11 at 100 kHz / 3.72 at 500 kHz** [F, S28]. Silicone LOCA ≈ 3, air = 1. Riverdi uses the same series-capacitor reasoning to explain a field failure [S16]. "Rel. signal" assumes touch Δ ∝ 1/d_eq. That is a crude parallel-plate model; for covers approaching the electrode pitch the real fall-off is steeper, so these figures are **optimistic** [I].

| stack over the ITO (top → sensor) | physical glass+adhesive (mm) | d_eq (mm) | rel. signal |
|---|---|---|---|
| module as delivered: 0.7 lens + 0.175 OCR | 0.88 | 1.01 | 100 % |
| GT911 datasheet ceiling: 2.0 glass + 0.175 OCR | 2.18 | 2.31 | **44 %** |
| + 0.7 CS glass, 0.2 OCA | 1.77 | 2.06 | 49 % |
| + 1.1 CS glass, 0.2 OCA | 2.17 | 2.46 | 41 % |
| + 2.0 glass, 0.3 LOCA | 3.17 | 3.71 | 27 % |
| **+ 3.0 tempered, 0.3 LOCA (plan)** | **4.17** | **4.71** | **21 %** |
| + 4.0 tempered, 0.3 LOCA | 5.17 | 5.71 | 18 % |
| + 3.0 tempered, **0.3 air gap** | 4.17 | 6.11 | 16 % |
| + 3.0 tempered, **0.5 air (gasket)** | 4.38 | 7.51 | 13 % |
| custom CTP: 3.0 lens laminated to sensor | 3.18 | 3.31 | 30 % |
| custom CTP: 2.0 lens laminated to sensor | 2.18 | 2.31 | 44 % |

What the field evidence says:
- **Riverdi case** [F, S16]: a working design with a consumer-grade controller under 1 mm cover glass had an extra **3 mm glass air-bonded with a 0.2 mm gap** added. Raising the gain gave ghost touches. Lowering it again meant touch worked only with hard presses (larger contact area). No workable gain/threshold balance was found.
- Air gaps: one vendor's air-gap PCAP app note limits the gap to **≤ 0.3 mm**, and it must be uniform [F (excerpt), S27].
- Vendor claims of "up to 6–15 mm glass" apply to **industrial controllers co-designed with the sensor stack** (ILI2132A/ILI2511 up to 10 mm, EXC80 up to 15 mm [S15]; HYCON up to 5 mm [S17]; "up to 8 mm" [S26]). None apply to an off-the-shelf GT911 tuned for a 0.7 mm lens.
- The GT911 Goodix forum thread: a user lowering thresholds "for a thicker cover glass" could not get the config write to take, and Goodix declined support [F, S22].

### 2.4 GT911 sensitivity registers and host rewrite
Source: GT911 Programming Guide Rev.10 (2017-07-26, firmware V1040+) [S20] unless noted.

| addr | name | role |
|---|---|---|
| 0x8047 | Config_Version | accepted only if **newer than the stored one, or equal with changed content**; 'A'…'Z'; **writing 0x00 resets it to 'A'** [F] |
| 0x8053 | Screen_Touch_Level | **touch threshold** [F] |
| 0x8054 | Screen_Leave_Level | **release threshold** (keep below the touch level) [F] |
| 0x8050 / 0x804F | Filter / Shake_Count | coordinate filter, touch-down/up de-jitter [F] |
| 0x8052 | Noise_Reduction | noise decrement 0–15 [F] |
| 0x8057 / 0x8058 | x_ / y_threshold | **coordinate-delta reporting thresholds, not sensitivity** [F] |
| 0x8062–0x8064 | Drv/Sensor group numbers | channel counts → pitch [F] |
| 0x8065–0x8068 | FreqA/B factor, BitFreq L/H | drive frequency (1526 Hz < f₀ < 14600 Hz) [F] |
| **0x806B** | Pannel_Tx_Gain | Drv_output_R (4 levels) + **DAC gain 0 = max … 7 = min** [F] |
| **0x806C** | Pannel_Rx_Gain | PGA_C, PGA_R, Rx_Vcmi + **PGA gain (8 levels)** [F] |
| 0x806D | Dump_Shift | raw-data magnification 2^N [F] |
| 0x806E | Drv_Frame_Control | sub-frame drive count, accumulative sampling count (more samples → better SNR, slower) [F] |
| 0x806F | Charging_Level_Up | threshold raise in charger mode [F] |
| 0x807A–0x807E | frequency-hopping start/end, detect counts, Hopping_Flag, threshold | [F] |
| 0x80FF | Config_Chksum | checksum over 0x8047–0x80FE [F] |
| 0x8100 | Config_Fresh | host writes 1 to apply [F] |

- **Host rewrite is supported over I²C** [F, S20 §4.4]. Write the changed bytes in 0x8047–0x80FE, update 0x80FF, then set 0x8100 = 1; otherwise "the modification is invalid".
- The Linux mainline driver confirms: GT911 config length **186 bytes**; checksum = **two's complement of the 8-bit sum** of the first 184 bytes; then config_fresh = 1; then a **10 ms** wait for the firmware to reconfigure [F, S21].
- Persistence: config is held in the chip's flash ("Stationary Configuration") [F, S18]. A user whose config "got overwritten by my experiments" ended up with **large dead zones** and no factory copy [F, S23]. One vendor says the config persists across power cycles and recommends comparing the checksum at boot and rewriting only on mismatch [F, S24]. **Flash write endurance: not found.**
- **Sources disagree:** the Kadi blog calls 0x8057/0x8058 the "sensitivity/release threshold" [S24]. The Goodix guide defines them as coordinate-delta thresholds [S20]. **Use the Goodix guide.**
- Raw/diff data (command 0x8040 = 1/2) exists, but the data addresses are not documented in the guide [F, S20].

### 2.5 Verdict
- **3 mm thermally tempered + 0.3 mm LOCA over this module: marginal; confidence 70 %.** It is 2.3× the datasheet's maximum glass and gives about 21 % of today's signal. The datasheet ceiling would give about 44 %, so the plan has half the signal of the worst case Goodix supports [I]. Expect it to register deliberate taps after lowering 0x8053/0x8054 and raising gain, with real costs: misses on light or dry-finger taps, worse accuracy near the AA edges, glove use fails, water/humidity and LCD noise produce ghosts. Acceptable only for a UI with large targets (≥ 12 mm) and only if the §2.6 test shows margin.
- **4 mm: reject** (about 18 % signal, 2.8× over).
- **Any air gap between the added glass and the CTP: reject** (16 % at 0.3 mm, 13 % at 0.5 mm).
- **1.1 mm chemically strengthened glass, OCA-bonded: likely fine** (about 41 %, at the datasheet envelope); expect only minor threshold retuning. Confidence 75 %.

### 2.6 Ten-minute bench test (bare module + window glass, today)
Material: the running board, a clean 3 mm and/or 4 mm float glass larger than 165 × 100 (picture-frame or window glass), clear **mineral oil (baby oil) or silicone oil** as optical coupling (εr ≈ 2–3, non-conductive), IPA and lint-free cloth. **Do not use water** as coupling: it is conductive and high-εr and gives false results.
1. **Back up (2 min).** Read 0x8140–0x8143 (product ID "911"). Read and save all **186 bytes from 0x8047** (I²C 0x5D or 0x14). Note 0x8047 (version), 0x8053/0x8054, 0x806B/0x806C, 0x8062–0x8064. This dump is the only way back if a write goes wrong [S23].
2. **Baseline (2 min), bare module.** Run a finger-paint screen (dots at reported coordinates). 20 taps on each of 9 points (centre, mid-edges and corners, 5 mm inside the VA); slow straight strokes edge to edge; one 2-finger tap.
3. **Coupled glass (3 min).** A few drops of oil on the CTP; lay the glass on and press out the bubbles. **Pulse RST with hands off** (GT911 takes its baseline in the first 200 ms after reset). Repeat step 2. Then: light single-finger taps; a hover check (finger held 5–10 mm above for 10 s must not report); a wet fingertip; a thin glove.
4. **Dry glass (1 min).** Wipe the oil off and repeat a few taps: this demonstrates the air-gap case.
5. **Retune trial (2 min, optional).** Write the same config with **0x8053 and 0x8054 reduced to about 60 %**, same version byte, new checksum, 0x8100 = 1. Repeat step 3, then restore the dump.

**Pass criteria for 3 mm (proposed).** ≥ 19/20 taps at all 9 points with a light touch; strokes with no breaks; no reports in the hover test; with oil coupling, the factory or 60 % thresholds work with no ghosts during 2 min of normal use with the display showing a busy image. **"Works only with a firm press" is a fail** (Riverdi's symptom).

### 2.7 Fallbacks, ranked
1. **Custom CTP from the module maker (SATOZ/Fannal) on the oversize printed cover lens.** Sensor laminated directly to a 2–3 mm lens (one glass layer instead of two; d_eq 2.3–3.3 mm), factory-tuned GT911 or a thick-glass controller (ILI2132A / ILI2511 class), and optionally full optical bonding of the CTP to the LCD. This gives the best touch and the best "dead front" (display looks black when off), with no in-house optical bonding. Cost, MOQ and NRE (one-off tooling and engineering charges) for 100 pcs: **not found; request a quote** (supplier agent). [I]
2. **Thin chemically strengthened (CS) glass** (0.7–1.1 mm soda-lime CS or aluminosilicate), OCA-bonded over the existing CTP. Within the GT911 envelope; flat float surface, so OCA lamination is feasible. Trade-offs: not thermally tempered (no safety-glass fragmentation), and local CS processing capability is uncertain (supplier agent).
3. **3 mm tempered + GT911 retune**, only if §2.6 passes with margin. Design the frame so glass thickness is a parameter (1.1–4 mm).
4. **2 mm thermally tempered**: about 27 % signal; needs a thin-glass furnace. Most tempering lines start at 3 mm / 1/8" [S35][S37].
5. 4 mm, or any air gap: rejected.

### Design consequences
- **Do not release glass tooling or orders until §2.6 has been run** with 3 mm (and ideally 2 mm) glass.
- Make the glass thickness a CAD parameter (1.1 / 2 / 3 / 4) for the frame land and bonding jig.
- Firmware: on boot, read the GT911 config checksum and rewrite the tuned config only if it differs [S24]; never write version 0x00. Keep the factory 186-byte dump in the firmware repo.
- Ask SATOZ/Fannal for the factory `.cfg` and `.ini` and for a quote on tuning for the chosen stack.
- UI rule if 3 mm is accepted: touch targets ≥ 12 mm; nothing interactive within 5 mm of the VA edge [I].

### Open risks
- The 1/d model is optimistic; the real signal at 3 mm may be lower.
- The flash endurance of repeated config writes is unknown.
- The grounded steel sheet now sits at the glass edge, about 10 mm outside the AA. Small edge desensitising is expected [I]; check it in the prototype.

---

## 3. In-house optical bonding at 100 pcs

### 3.1 What is actually being bonded
- **Rigid to rigid:** 3 mm tempered glass (surface 2 printed) onto the CTP's 0.7 mm cover lens. The CTP lens has a black print border [F, p.27, "Printing black"]. The drawing does not say which face; G+G lenses are normally printed on the underside [P], which would make the CTP top face flat glass. Check with a fingernail or by looking edge-on. If so, the only ink step is on our new glass.
- The **LCD stays air-gapped** behind the CTP (0.4 mm PU tape) [F, p.27]. Two consequences:
  - **No LCD mura risk** from adhesive shrinkage; only the CTP glass is loaded [I].
  - **A true Samsung-style dead front is not reachable** with this module, because the CTP/LCD air gap keeps its two reflecting surfaces whatever we do (§3.5).
- **Shadow zone:** outside the new window, the bond line sits between two black prints (our border and the CTP's border). **UV cannot reach a 4–9 mm wide perimeter band.** Any UV adhesive therefore needs a secondary cure (moisture or heat), or the band stays wet [F, S30][S31].
- **The CTP FPC exits the edge face** (CTP leg at Z −8.9 in the frame doc). Adhesive overflow must be kept off the FPC and the ACF bond.

### 3.2 Process comparison (165 × 100 mm, rigid-rigid, small team, no cleanroom)

| | **Dry OCA film** (e.g. 3M CEF05XX / 8146-x) | **Acrylic LOCA, dual cure** (UV + heat/moisture) | **Silicone LOCA / gel** (UV + moisture, or 2K heat cure) | **Air gap + perimeter gasket** |
|---|---|---|---|---|
| Bond line | 25–300 µm sheets [F, S28] | 0.1–0.5 mm, set by jig [P] | 0.2–0.5 mm, set by jig [P] | 0.3–1 mm air |
| Equipment | roller laminator; **vacuum laminator < 50 Pa, 0.1–0.2 MPa; autoclave 30–60 °C, 3–5 kgf/cm², 20–30 min** [F, S28] | dispenser/syringe, UV LED 365/395 nm, Z-guided jig, XY stage, 50–60 °C oven | same; for 2K: static mixer + **vacuum degassing** [F, S31] | none |
| Alignment | **passive only.** No re-positioning after contact, so alignment comes from the mechanical stack (LCM outline ±0.3) [F p.16] | **active**: float the parts on the wet film, align to the lit display, then UV-tack | active, same | n/a |
| Ink step | needs OCA ≥ 3–4× step height [F, S29]; a 25 µm black step → ≥ 100 µm OCA | fills steps easily (300 µm ≫ 25 µm) [F, S29] | same | n/a |
| Tempered-glass bow (§4.6) | poor: a thin film cannot bridge 0.1–0.5 mm of bow → edge voids [I] | good: liquid follows the gap | good | n/a |
| Shadow cure under borders | none needed (pressure-sensitive) | needs heat or moisture second stage [F, S30] | moisture (e.g. Loctite 5192-type UV/moisture silicone [F, S31]) or 2K addition cure (cures in bulk, < 70 °C, e.g. Wacker LUMISIL 100 A/B [F, S32]) | n/a |
| Typical defects | dust → bubble with a halo; delayed bubbles; edge voids | bubbles from dispense pattern; overflow; edge left soft if the shadow cure is incomplete [S30]; perimeter yellowing if heat-cured hot [S30] | air from mixing (degas!); **cure inhibition** by sulfur, plasticisers, urethanes, amines, organotin [F, S32]; overflow | dust and fog inside the gap; Newton rings; reflections |
| Temperature capability | 3M CEF05: −40/+95 °C 1000 h, +85/85 1000 h, thermal shock −40/+95 200 cycles, no bubbles, haze < 1 %, b* < 1 [F, S28] | −40…+85/105 °C class [P] | −40…+150 °C class, non-yellowing [P]; 5192T "high-temperature resistant, non-yellowing" [F, S31] | n/a |
| Rework | peel with heat + wire; easier on flat glass [P] | hard after cure; needs heat above the module's 80 °C storage limit [I] | **separable with a wire / thin blade at room temperature** [P] | trivial |
| Realistic yield, small team, no cleanroom | 70–90 %, dust-limited [I] | 85–95 % after ~20 pcs learning [I] | 85–95 % [I] | ~100 % assembly, but **fails touch** (§2) |
| Optical gain vs air | removes 2 reflecting surfaces (~8.5 %) | same | same (n silicone 1.40–1.41 vs glass 1.52: residual 0.15 % per interface) [I] | none |

### 3.3 Recommendation: silicone LOCA (UV + moisture dual cure, or 2K addition-cure gel), about 0.3 mm, actively aligned
Why [I]:
- Active alignment on the lit pixels is the only way to hold the window to the AA within ±0.2 mm. The mechanical chain (LCM outline ±0.3, CTP VA ±0.2, glass print-to-edge ±0.2–0.3) cannot.
- The liquid takes up the bow of tempered glass and the ink step.
- The shadow band cures without UV.
- Low modulus means no stress on the 0.7 mm CTP lens.
- Rework at room temperature protects the expensive module.
- Equipment is benchtop.

**Choose 2K addition-cure** if the printed glass passes an inhibition test (bulk cure, no UV needed). **Otherwise choose UV/moisture silicone.** An acrylic dual-cure LOCA is the second choice if silicone adhesion to the glass ink or CTP glass proves weak.

**Step by step**
1. **Incoming.** Glass: flatness ≤ 0.15 mm over the 165 × 100 bond zone (§4.6); print inspected on a light box; no pinholes. Module: functional test, protective film still on.
2. **Clean (separate room from any silicone sealant).** Glass surface 2 and CTP top: IPA, then a lint-free wipe; ionising air blower. Work under a HEPA hood or a laminar-flow box (about 600 × 600 mm is enough). Gloves; no powder.
3. **Mask.** Kapton tape over the CTP edge face along the FPC exit (bottom edge, x 39.2–167.4 in frame coordinates) and over the PU tape edge.
4. **Inhibition and adhesion coupon** (once per ink lot): a drop of the LOCA on a printed offcut, cured. Must be fully cured and tack-free (Wacker inhibitor list [S32]).
5. **Dispense.** Volume = 164.9 × 100 × 0.30 = **4.95 mL**. Dispense about **5.2 mL** on the CTP face in a **"double-Y / dog-bone" pattern** (spreads from the centre outward without enclosing air). 2K: vacuum-degas the mixed batch first.
6. **Lower the glass.** Glass is held printed face down in the top plate of a **Z-guided jig** (4 linear guide pins). Lower it slowly (≤ 1 mm/s near contact) onto **hard stops that set a 0.30 ± 0.03 mm gap** over the CTP face. Gap = stop height − measured CTP surface height; ground shims per lot. Let it wet out to the CTP edges: 1–3 min.
7. **Align.** Module powered, showing **a 1-pixel white frame on the outermost AA pixels plus a mid-grey field**. Its nest sits on a manual **XY + θ stage** (±0.01 mm micrometers). Two USB microscopes over diagonally opposite corners compare the window edge with the pixel frame. Built-in scale: **1 px = 0.1926 mm horizontal, 0.179 mm vertical** (154.08/800, 85.92/480). Target window edge = AA edge + 0.25 mm (≈ 1.3 px h / 1.4 px v), tolerance ±0.2 mm (±1 px).
8. **Tack.** UV-LED flood through the window (395 nm, about 1–2 J/cm², per the adhesive TDS), plus side-cure the exposed edge fillet. 2K gel: hold in the jig at room temperature to gel time, or 50–60 °C (≤ module 70 °C operating limit).
9. **Clean the squeeze-out** with IPA on a swab before it skins. Remove the masking.
10. **Secondary cure.** Moisture-cure grades: ≥ 72 h at room temperature and 50 % RH before stressing. 2K: per TDS, e.g. 1–4 h at 60 °C.
11. **Inspect.** Use the module's own CTP appearance criteria [F, p.26]: inclusions **≤ 0.2 mm ignore; 0.2–0.5 mm ≤ 5 pcs at ≥ 10 mm spacing; > 0.5 mm reject.** Touch test (9-point and stroke); edge-flex check for soft edges [S30].

**Jig requirements**
- Flat base plate (Al, ground, ≤ 0.02 mm flatness) with an XY-θ nest for the LCM: soft POM locators; FPC slot; power and I²C connector.
- Top plate carrying the glass: vacuum cups or a printed-side-safe POM pocket; 4 guide pins; Z stops adjustable by shims to 0.01 mm.
- Two USB microscopes (≥ 50×) on fixed arms over opposite corners.
- UV LED head on a swing arm.
- Fixture throughput is a few minutes per part, so one jig is enough for 100 pcs.
- Cost of this equipment: **not verified** (supplier agent); in my estimate it is a few thousand euros at most, versus vacuum laminator + autoclave for OCA [I].

### 3.4 Effect of the black-border step
Two-layer black organic ink is about 10–25 µm (Marabu MGL film 5–12 µm per pass [F, S34]). Against a 300 µm LOCA gap the step is under 10 % and harmless. For OCA the step would require ≥ 75–100 µm film [F, S29], and bubbles concentrate at the corners of the ink border [F (excerpt), S29]. A fired ceramic frit border (§4.3) gives a similar step [P].

### 3.5 Would an air gap look "black-on-black"? No.
Fresnel reflectance of a glass/air surface (n = 1.52): **4.26 %** [I, physics]. Under 300 lx room light each such surface returns about **4.1 cd/m²**. The LCD's own black is 280 cd/m² ÷ 400–500 CR = **0.56–0.70 cd/m²** [F, pp.7,14]. Window brightness is therefore set by reflections, not by the LCD.

| case | window: specular reflecting surfaces | ≈ R | border (black ink on surface 2) |
|---|---|---|---|
| air gap + gasket | front, glass rear, CTP top, sensor rear, polariser | ~21 % | ~4–6 % (front + ink diffuse) |
| optically bonded (plan) | front, sensor rear, polariser | ~13 % | ~4–6 % |
| bonded + **grey-tinted glass T = 60 %** | front + 0.6² × (sensor rear + polariser) | ~7 % | ~4–6 % |
| custom CTP fully bonded to LCD | front (+ polariser AG haze) | ~5 % | ~4–6 % |

Verdict [I]: with an air gap the window reads clearly grey and bright against the border (4–5× brighter), and it adds dust/fog and touch failure. Bonding halves the contrast step but does not remove it. **The cheap extra lever is a body-tinted grey float glass** (Turkish float makers sell "füme"; supplier agent to confirm). At T ≈ 60 % the display drops from 280 to about 170 cd/m², which is acceptable indoors. Only full lamination of CTP to LCD (module maker) reaches a real dead front.

### Design consequences
- Process: **silicone LOCA, 0.30 mm bond line, active pixel alignment, dual or bulk cure**. Volume 5.2 mL per unit. Allow a 72 h cure buffer before final test.
- Glass spec gains a **flatness requirement over the bond zone (≤ 0.15 mm)** and an **ink lot inhibition/adhesion coupon**.
- Window on the new glass: **AA + 0.25 mm per side = 154.58 × 86.42 mm**, between the LCD AA (154.08 × 85.92) and the CTP's own VA (155.08 × 86.92), so the CTP's print edge stays hidden under ours. Aligned ±0.2 mm to the lit AA, not to the glass edge.
- The frame pocket must leave a **≥ 1 mm clearance gutter** round the CTP edge face for squeeze-out, and must not clamp the module front (the glass carries it).
- If the custom-CTP fallback (§2.7-1) is taken, **delete this whole in-house step**.

### Open risks
- Dust is the yield killer without a cleanroom.
- Inhibition of Pt-cure silicone by 2K PU inks (MGL-type hardener) or the Y9040B PU tape at the edge must be tested.
- Tempered-glass bow beyond 0.15 mm makes the bond line uneven. That is harmless optically, but it raises the risk of edge voids.
- The LOCA product must be locally available (supplier agent).

---

## 4. Glass-to-frame bonding and glass specification

### 4.1 Movements to absorb (land 6–10 mm, glass about 185 × 120 × 3 mm, about 167 g)
Assembly at 23 °C. Extremes −20 °C (storage) and +70 °C. Glass 9 ppm/K (EN 572-1 value per float makers; Pilkington gives 8.3 ppm/K over 24–300 °C) [F, S42]. PA6-GF30 30 / 70 ppm/K (frame doc §3).

| case (190 mm span) | Δα (ppm/K) | ΔT | total Δ (mm) | at each end (mm) |
|---|---|---|---|---|
| along the glass-fibre flow direction, hot | 21 | +47 | 0.19 | **0.09** |
| transverse, hot | 61 | +47 | 0.55 | **0.27** |
| transverse, cold | 61 | −43 | −0.50 | **0.25** |
| PA6 moisture swelling 0.2–0.3 % (frame doc §3) | — | — | ≈ 0.48 | **0.24** |
| worst combined (hot + wet, transverse) | | | ≈ 1.0 | **≈ 0.5** |

- Shear strain at the ends = 0.5 mm / bond thickness: **45 % for 1.1 mm, 33 % for 1.5 mm, 25 % for 2.0 mm**.
- 3M allows differential shear movement **up to 3× tape thickness (300 %)** [F, S33]. Silicone (7091 class) elongates **680 %** [F, S34-Dow].
- Conclusion [I]: any of the soft options absorbs this. **Rigid adhesives (epoxy, PU > Shore A 60) are excluded:** they would bow the glass and frame like a bimetal and load the print.

### 4.2 Adhesive options

| option | fits glass / ink / PA6? | gap control (flush) | strength / time | temperature | verdict |
|---|---|---|---|---|---|
| **3M VHB 5952 family** (modified acrylic, black, 0.15–1.6 mm; 5952F 1.1 mm) | bonds HSE/MSE/LSE plastics and paints incl. powder coat; 3M application idea "bond and seal polycarbonate lens over LCD" [F, S33] | **fixed thickness** → flush = glass ±0.05 (one lot) [I] + tape ±0.1 [P] + land warpage ±0.1 [I] ≈ **±0.15 mm RSS** | 50 % at 20 min, 90 % at 24 h, 100 % at 72 h; ≥ 100 kPa roller pressure; apply ≥ 10 °C (most acrylics) [F, S33] | rated 150 °C short-term [F, S33] | good strength; **flush only ±0.15–0.25** |
| **3M VHB 4941 family** (multi-purpose acrylic, gray, 0.4–2.3 mm) | glass, HSE/MSE plastics and paints [F, S33] | same | same | 150 °C short / 93 °C long [F, S33] | alternative to 5952 |
| **3M VHB 4910** (clear, 0.5–2 mm) | for joining transparent materials, glass [F, S33] | same | same | 150 / 93 °C [F, S33] | not needed (bond is on black) |
| **Neutral-cure alkoxy silicone, 1-part** (DOWSIL 7091 class) | "designed for … differing thermal expansion, e.g. glass to plastic"; unprimed on glass, enamel and painted surfaces, "certain plastics"; primer DOWSIL 1200 OS for maximum adhesion [F, S34-Dow] | **gap-filling: the jig sets the flush plane** (±0.05 mm, limited by sheet thickness tolerance) [I] | skin 15 min, tack-free 28 min, **2 mm/24 h** cure depth; 2.5 MPa, 680 %, Shore A 32 [F, S34-Dow] | −40…+180 °C [F, S34-Dow] | **recommended** |
| 2-part silicone or 2K MS polymer | as above; bulk cure in 1–4 h | jig-set | fast jig turnover | silicone −40…+150 class [P]; MS −40…+90 class [P] | if jig time matters |
| VHB + silicone combined | VHB fixes thickness → it fights the jig; a compressible foam pre-fix springs back after unjigging [I] | worse than either alone | — | — | **no** |

PA6-GF30 surface: moulded PA6 counts as a medium/high surface-energy plastic [P], but the FR (flame-retardant) grade, mould release and moisture vary. **3M recommends primer for "higher adhesion, especially for paint or plastic surfaces", Primer 94 for LSE (low surface energy) plastics, and silane AP115 for glass** [F, S33]. AP115 only matters if bonding to bare glass or frit. Qualify on real moulded parts with an IPA wipe, ± light abrasion, ± primer.

### 4.3 Bonding onto ink: frit vs organic
- **Ceramic frit (enamel).** Printed on annealed glass and **fired in during toughening; it becomes an integral part of the glass surface** [F, S35]. This is the automotive practice: PU windscreen adhesive is bonded onto the black frit band, which also shields the adhesive from UV [F (excerpt), S40].
  - Cost in strength: EN 12150-1 minimum bending strength **120 MPa for float, 75 MPa for enamelled toughened** [F (excerpt), S36]. Fracture origins are found at the frit-side surface [S36].
  - For a 3 mm, 167 g display glass backed by the bonded module, 75 MPa is ample [I].
  - The frit must be printed by the tempering house before tempering [F, S35].
  - Black frit is slightly matte and greyer than organic ink [P]. Our window-edge print quality and colour against the LCD black need a sample.
- **Organic 2-component glass ink** (Marabu Mara Glass MGL type), printed after tempering:
  - Surface tension ≥ 40 mN/m; flame pre-treatment improves adhesion [F, S34].
  - Film **5–12 µm per pass**; **final cure 140 °C / 30 min** (or 6 days at 20 °C).
  - Tests: dishwasher ≥ 400 cycles, condensation 70 °C / 100 % RH / 30 min, cold-water immersion 24 h, MEK 50 double rubs [F, S34].
  - Medium opacity → **2–3 passes** for OD ≥ 4 [P].
  - **The ink-to-glass interface becomes the weak link of the frame bond** [P]. The adhesive peel load passes through the ink.
- Qualification tests to specify (either ink) [P, test methods per S34 / lens-coating practice]:
  - Cross-cut, 1 mm grid (ISO 2409 / ASTM D3359), **GT0–1 / ≥ 4B**, dry and after **1 h in boiling water**.
  - Optical density on a light box: no visible pin-holes at 1000 lx back-light.
  - **Adhesive peel on printed coupons:** silicone bead 8 × 1.5 mm, cured 7 days, 90° peel. Pass = **≥ 90 % cohesive failure in the adhesive** (Dow reports 100 % cohesive failure on glass and enamel [S34-Dow]). Repeat after 7 days at 70 °C / 95 % RH and after 10 cycles −20/+70 °C.
- **Recommendation:** frit if the tempering house prints black frit with ≤ ±0.3 mm edge position. Otherwise 2K organic ink + the tests above; bond onto the ink.

### 4.4 Flush jigging, independent of glass thickness [I]
- The goal is **glass front face = sheet outer face**. The frame flange front face *is* the sheet inner face (frame doc §1.4), so the glass front must sit **exactly one sheet thickness (1.00 mm) proud of the flange datum.**
- Jig: a ground plate with a **pocket 1.00 mm deep** (= nominal sheet), sized to the glass + 0.2 mm.
  - Glass face-down in the pocket (protect the print side with a PE film).
  - The frame lowered so its **flange front face rests on the plate top** around the pocket, located on the two pegs P1/P2 and two stud slots (same datums as on the oven).
  - The bead on the frame land is pre-dispensed with **1.5 mm nominal gap** (land design: glass back to land 1.5 ± 0.5 mm covers glass ±0.2, frame ±0.2 and warpage).
  - Light weight (0.5–1 kg) on the frame; glass held in the pocket by gravity or vacuum.
- Result: flushness = sheet thickness tolerance (EN 10131 cold-rolled 1.0 mm ±0.07–0.08 class [P]) + frame seating. **Glass and frame tolerances drop out.**
- Glass edge to sheet window: **0.4 mm per side nominal** [I]. Stack: glass outline ±0.15 + laser-cut window ±0.1 + frame-to-sheet location RSS ±0.125 (frame doc §2), giving 0.4 ± 0.22 → never touches. Glass-to-steel CTE difference over 190 mm × 50 K = 0.03 mm, negligible.
- Edge/corner breakage protection: the 0.4 mm gap + arris; the steel window edge must be deburred (mechanical agent).

### 4.5 Cure and handling
- 1K silicone between glass and frame cures only from the two exposed bead faces: about 4 mm path at 2 mm/24 h, so **≈ 2–3 days to full cure**, and handling strength after about 24 h [F rate S34-Dow; I extrapolation].
- With 6 jigs, 100 units take about 17 working days. With 2K silicone/MS (1–4 h in the jig), one or two jigs suffice [I].
- Keep silicone dispensing **away from the optical bonding and print areas**: silicone residue kills ink and LOCA adhesion [P].
- Order: print (supplier) → optical bond (§3) → glass-to-frame bead in the flush jig → PCB.

### 4.6 Glass specification practice

| item | normal practice / standard | recommend for this part | tag/source |
|---|---|---|---|
| Type | thermally toughened soda-lime safety glass EN 12150-1 (or heat-strengthened EN 1863-1: 1.5–2× annealed strength, not safety glass) | EN 12150-1 toughened, clear or grey-tinted float | [F] S35, S38 (excerpt) |
| Thickness tolerance | float 3/4/5/6 mm **±0.2**; 8/10/12 mm ±0.3 (EN 572-2 / GGF Table 1) | 3.0 ± 0.2; same lot per batch | [F] S35 |
| Minimum thickness for thermal tempering | GGF/EN 12150 tables start at **3 mm**; US tempering line minimum 1/8" (3.2 mm); 2 mm needs special furnaces | 3 mm (or 2 mm only if §2 needs it and a thin-glass furnace is found) | [F] S35, S37 (excerpt) |
| **Minimum pane size** | horizontal toughening "generally not less than **300 × 100 mm**"; consult the maker | **185 × 120 is below that**: use an appliance-glass toughener with a small-piece furnace | [F] S35 |
| Overall bow | horizontal, float: **0.003 mm/mm** (→ 0.56 mm over 185 mm) | **≤ 0.15 mm over the 165 × 100 bond zone** (custom; verify capability) | [F] S35; [I] |
| Local bow / roller wave | local bow **0.5 mm / 300 mm**; roller wave 3–5 mm glass **0.5 mm** | covered by the line above | [F] S35 |
| Edge work | all edge work and holes **before** toughening; arrissed, ground, smooth-ground (polished); bevel leftover ≥ 2 mm or t/3 | **flat polished edge, 0.3–0.5 × 45° arris front and back** (pencil/C-edge not needed; it widens the visible gap) | [F] S35; [I] |
| Outline tolerance | architectural ±2–3 mm (EN 12150); processed/CNC appliance glass ±0.1–0.3 [P] | **±0.15 mm**, CNC | [F] S35; [P] |
| Corner radius | smallest standard radius 3 mm ±0.5 (Schott); Riverdi CG R5 | **R5** | [F (excerpt)] S39; [F] S12 |
| Holes (avoid) | Ø ≥ t; hole edge to glass edge ≥ 2t; between holes ≥ 2t; to corner ≥ 6t; GGF hole rules for t ≥ 4 mm; Ø tolerance ±1.0 (4–20 mm) | **no holes** | [F] S35 |
| Print | ceramic (Schott: "mainly ceramic" for flat glass) or organic 2K; print-to-print tolerance ≤ 0.3 mm, min line 0.5 mm (Schott) | black 2–3 passes, OD ≥ 4, surface 2; window 154.58 × 86.42; **print-to-edge ±0.2–0.3**; border ≥ 7.5 mm so ±0.3 is invisible; window aligned to the AA at bonding (§3.3), not by the print-to-edge tolerance | [F (excerpt)] S39; [P]; [I] |
| Impact (IEC 60335-1 cl. 21.1) | spring hammer, **0.5 J**, IEC 60068-2-75 test Ehb | 3 mm toughened, backed by the bonded module, should pass with large margin. The CTP alone is rated for 0.32 J (132 g ball, 25 cm). Weak points to test: unsupported border near corners, glass edge in the 0.4 mm gap. If it breaks: no access to live parts (display is SELV) | [F (excerpt)] S41; [F] p.24; [I]. "Three blows per weak point" is from the standard's text as I recall it; **verify in the purchased standard** |

### Design consequences
- **Frame land**: 8 mm wide (6 min), **1.5 mm nominal adhesive gap** to the glass back face; land flat within 0.2 mm; ribs or a dam lip stop squeeze-out from reaching the visible gap.
- **Adhesive**: neutral alkoxy silicone (DOWSIL 7091 class, black), primer per qualification on PA6-GF30 FR; 2K version if jig time matters. VHB 5952F/4941 only if ±0.2 mm flushness is accepted.
- **Flush jig**: 1.00 mm pocket plate, locates the frame on P1/P2 + 2 stud slots; ≥ 24 h dwell (1K).
- **Glass**: 3 mm toughened EN 12150-1 (thickness pending §2), 185 × 120 class, CNC ±0.15, flat-polished + arris, R5, no holes, black frit (preferred) or 2K ink on surface 2, OD ≥ 4, bond-zone flatness ≤ 0.15 mm, small-piece toughening furnace.
- **Retention**: module retained mechanically to the frame (clips/brackets from behind), so the glass has two load paths (§1 consequences).
- **Sheet window** = glass outline + 0.4 mm per side.

### Open risks
- Small-piece tempering capacity and achievable flatness at 185 × 120 × 3 mm (supplier agent).
- Ink-to-glass adhesion through humidity and heat ageing at 70 °C (test before release).
- Silicone adhesion to PA6-GF30 FR grade (additive bloom, moisture).
- Moisture swelling of PA6 has not yet been checked over the stud pattern (frame doc open question 4); here it is absorbed by the 1.5 mm bead.

---

## 5. Not verified / gaps
- DA82-02711L physical construction: no photos, manuals or teardowns were reachable (403s / Cloudflare on all parts sites; service manuals behind Cloudflare, not bypassed).
- GT911 flash write endurance; raw-data register map; the actual signal through 3 mm (the §2.3 table is a model, not a measurement).
- EN 12150-1:2015 full text: values are taken from GGF 4.4 (2004, based on EN 12150) and from a secondary presentation. IEC 60335-1 cl. 21.1 text: from a vendor page, plus my recollection for "three blows".
- SCHOTT tolerance pages are region-locked; values come from search excerpts only.
- Equipment costs, LOCA product availability and the custom-CTP MOQ/NRE: not researched (supplier agent).

## 6. Sources
- [S1] iFixit, DA82-02711L: https://www.ifixit.com/products/da82-02711l-samsung-refrigerator-cover-display-assembly
- [S2] ApplianceParts4All, DA82-02711L (replaces list): https://www.applianceparts4all.com/samsung-display-board-da82-02711l
- [S3] Samsung Parts, DA82-02711L: https://samsungparts.com/products/da82-02711l
- [S4] ReliableParts listing title (excerpt): https://www.reliableparts.com/smg-da82-02711l.html
- [S5] AppliancePartsPros DA97-20810D (excerpt): https://www.appliancepartspros.com/samsung-assy-cover-display-da97-20810d-ap7022558.html
- [S6] Samsung Community, Family Hub LCD replacement thread: https://community.samsung.com/us/conversations/Kitchen/Looking-for-replacement-Family-Hub-LCD-screen/us_2877572
- [S7] PartSelect DA82-02711V (excerpt): https://www.partselect.com/PS16733206-Samsung-DA82-02711V-Display-Cover-Assembly.htm
- [S8] Consumer Reports, Family Hub (excerpt): https://www.consumerreports.org/french-door-refrigerators/samsung-family-hub-refrigerator
- [S9] EasyBear repair blog: https://easybear-appliancerepair.com/blog/smart-refrigerator-screen-not-responding
- [S10] ShopJimmy DA97-19331N: https://www.shopjimmy.com/samsung-da97-19331n-family-hub-display-assembly-for-rf22n9788sg-aa-control-board-da92-01065e
- [S11] iFixit DA82-02377H (→ DA97-19331E): https://www.ifixit.com/products/da82-02377h-samsung-refrigerator-cover-display-assembly
- [S12] Riverdi RVT70HSPNWC00 datasheet Rev.1.0: https://download.riverdi.com/RVT70HSPNWC00/DS_RVT70HSPNWC00_Rev.1.0.pdf
- [S13] Riverdi uxTouch Assembly Guide Rev.1.1: https://riverdi.com/wp-content/uploads/2024/04/UxTouch_assembly_guide_Rev._1.1.pdf
- [S14] Riverdi aTouch vs uxTouch: https://riverdi.com/?p=128848
- [S15] Riverdi PCAP knowledge base: https://riverdi.com/knowledge-base/projected-capacitive-touch-screens
- [S16] Riverdi, touch sensitivity case: https://riverdi.com/blog/how-to-solve-touch-screen-sensitivity-problems
- [S17] Riverdi, cover glass blog: https://riverdi.com/blog/cover-glass-in-smart-display-solutions
- [S18] GT911 Datasheet Rev.10 (mirror): https://files.waveshare.com/wiki/common/GT911_Datasheet.pdf
- [S19] GT911 Datasheet 2013 (Chinese, mirror): https://cdtech-display.com/wp-content/uploads/2024/07/GT911-Datasheet_20130827.pdf
- [S20] GT911 Programming Guide Rev.10: https://www.lcd-module.de/fileadmin/eng/pdf/zubehoer/GT911_Programming_Guide_Rev.10.pdf
- [S21] Linux goodix.c: https://raw.githubusercontent.com/torvalds/linux/master/drivers/input/touchscreen/goodix.c
- [S22] Goodix developer forum, threshold thread: https://developers.goodix.com/en/bbs/detail/b2116194e17b48429749b9b6f33ae96f
- [S23] ST Community, overwritten GT911 config: https://community.st.com/stm32-mcus-boards-and-hardware-tools-26/stm32n6570-dk-need-factory-gt911-touch-controller-config-rk050hr18c-b01-166679
- [S24] Kadi Display, GT911 stability guide: https://www.kadidisplay.com/blog-news/making-gt911-lvgl-touchscreens-stable-for-24-7-operation/
- [S25] GT9110P Datasheet Rev.09: https://www.cdtech-display.com/wp-content/uploads/2025/04/GT9110P-Datasheet_English_Rev.09.pdf
- [S26] CDTech, thick cover lenses: https://www.cdtech-display.com/knowledges/is-your-touch-display-ready-for-thick-cover-lenses-and-modern-hid-platforms/
- [S27] Texim, PCAP air-gap app note (excerpt): https://texim-europe.com/getfile.ashx?id=103976
- [S28] 3M CEF05XX / 8146-X TDS (mirror): https://www.plitek.com/wp-content/uploads/3M-Contrast-Enhancement-Film-CEF05XX-8146-X-Series.pdf
- [S29] 3M patent US10941321B2: https://patents.google.com/patent/US10941321B2/en
- [S30] Incure, LOCA defects / shadow cure (excerpt): https://incurelab.com/wp/?p=14667; Henkel primer-cure LOCA (excerpt): https://www.adhesivesmag.com/articles/92005-henkel-primer-and-liquid-optically-clear-adhesive
- [S31] Machine Design, Loctite LOCA line (5192T UV/moisture silicone, 3192T UV/heat): https://machinedesign.com/fastening-joining/article/21833724/optically-clear-adhesives
- [S32] Wacker LUMISIL 100 A/B: https://www.wacker.com/h/en-gb/c/lumisil-100-ab/p/000010093
- [S33] 3M VHB Tape Design Guide (EU 2024, mirror): https://cgrproducts.com/wp-content/uploads/3M-VHB-Design-Guide.pdf; original: https://multimedia.3m.com/mws/media/1400379O/3m-vhb-tape-design-guide.pdf
- [S34] Marabu Mara Glass MGL TDS: https://cdn.shopify.com/s/files/1/0068/0244/0276/files/Marabu_Glass_MGL_Tech_Data_Sheet.pdf; Marabu Glass Ink GL TDS: https://cdn.shopify.com/s/files/1/0068/0244/0276/files/Glass_Ink_GL_Technical_Data_Sheet.pdf. [S34-Dow] DOWSIL 7091 TDS: https://www.farnell.com/datasheets/2936560.pdf
- [S35] GGF Data Sheet 4.4 (toughened glass, EN 12150 based, 2004): https://cdn.shopify.com/s/files/1/0622/2749/files/GGF_Standard_Data_Sheet_4.4.pdf
- [S36] E. Mognato, EN 12150-1 strengths (excerpt): https://bin.yhdistysavain.fi/1589917/fP49ClGzDckekwKVNE630boJvX/Ennio%20Mognato%20-%20Short.pdf
- [S37] Glaztech tempered glass (excerpt): https://www.glaztech.com/tempered-glass
- [S38] Guardian, heat-strengthened vs tempered (excerpt): https://www.guardianglass.com/eu/en/why-glass/understand-glass/heat-strengthened-vs-tempered-glass
- [S39] SCHOTT processed flat glass technical details (region-locked; excerpt): https://www.schott.com/en-gb/products/processed-flat-glass/technical-details
- [S40] Windscreen frit function (excerpt): https://hackaday.com/tag/frit/
- [S41] IEC 60335-1 cl. 21.1 / IEC 60068-2-75 Ehb 0.5 J hammer, vendor page (excerpt): https://www.iectestingequipment.com/sale-41394004-iec-60335-home-appliance-testing-equipment-spring-hammer-test-with-0-5j-impact-energy.html
- [S42] Pilkington, properties of glass: https://www.pilkington.com/-/media/pilkington/site-content/usa/window-manufacturers/technical-bulletins/ats129propertiesofglass20130114.pdf
- [S43] Beckhoff CP2xxx glass front (Process Technology Online): https://process-technology-online.com/allgemein/multi-touch-panels-offer-maximum-flexibility/
