# Rev3.0 OVEN CONTROLLER — carrier frame design, v2 (2026-11-13)

Owner: Ömer Karaoğlu (READARK). Part: one injection-moulded **carrier frame** that holds the Rev3.0 PCB and the 7" SATOZ SAT070AT40D21 panel (GT911 CTP), and mounts the pair to the oven's steel front sheet from the inside.

This is **v2**. v1's eight cantilevered feet are replaced by a continuous perimeter flange with ten M4 stud bosses. The panel seat, the PCB seat, the tail pocket and the material are carried over from v1, with the v2 numbers.

- CAD: native parametric Fusion 360 part "Rev3.0 Frame v2" (version 6) and "Rev3.0 Frame v2 fit assembly" (version 6). Built by the numbered scripts in `Design Reports/Rev3.0/tools/frame_v2/fusion/` (README there).
- Independent verification: `Design Reports/Rev3.0/tools/frame_v2/build_v2.py` (CadQuery). It reads the exported STEP and the parameters JSON and models nothing itself (README there).
- Outputs: `Mechanical/Rev3.0_Frame/` (`Rev3.0_Frame_v2.*`, `Rev3.0_Frame_v2_params.json`, `Rev3.0_FrontSheet_Pattern_v2.dxf`, `renders_v2/`).
- Numbers below come from `Rev3.0_Frame_v2_params.json` (Fusion side) and from `tools/frame_v2/out/summary.json`, `fitcheck.json`, `cadcheck.json` and `calc.json` (CadQuery run of 2026-11-13). The two agree. Where they measure different things, both values are given. File list in §9.

**What changed from v1, and why**

| item | v1 | v2 | why |
|---|---|---|---|
| mounting | 8 cantilevered feet (12 mm pads with tubes) | continuous flange 14 × 2.5 mm, R 12 corners, merged with the outer wall | owner: the feet "will break" in glass-filled nylon |
| studs | 8 × M4, round Ø 4.5 holes | 10 × M4, stadium slots 4.5 × 5.3, radial from the datum | every 8-hole layout fails the gasket-lift limit (best 178 µm against 90); PA6-GF30 grows 0.2–0.4 mm more than the steel at the studs |
| stud boss | Ø 9.5 tube on the pad, seat Z −6.02 | Ø 10 tube 5 mm above the flange back, seat Z −3.52, full-height rib | flange bending at a stud 46 → 23.5 MPa |
| stud | PEM FH-M4-15 | PEM FH-M4-18 | stack 13.5 mm from the sheet |
| pegs | on the corner-cell floors, round sheet holes | on the side flanges at y 69.5, sheet slots 3.2 × 3.9 along X | they set the thermal datum and the y line |
| material above Z 0 | tail-pocket walls 0.40 mm from the board edge at the H6 ear (11.9 mm³ inside board + 1 mm) | side walls rise only for y ≥ 129: 0 mm³ | component side fully open |
| support ribs | end 0.5 mm before the shelf edge | flush with the shelf window face | no narrow land at the rib end |
| PCB pilots | through, cored from both sides | blind, 1.0 mm floor | closed sealing face |
| root fillets | not modelled | R 0.5 on 337 roots, modelled | the toolmaker gets them in the CAD |
| size / mass | 192.0 × 148.0 mm, 32.5 cm³, 44 g | 198.4 × 165.45 mm, 55.06 cm³, 74.9 g | the flange |

## 1. Concept

The frame is a flat ring that sits between the panel (in front) and the PCB (behind). A continuous flange runs round it in the plane of the oven sheet. Ten M4 studs on the sheet clamp the flange.

- **Mould direction.** One pull direction, along the panel axis. There are no undercuts and no side actions.
- **Component side open.**
  - The outer wall, the PCB boss tops and the support-rib tops all end at the PCB back (Z = 0).
  - Above Z = 0 there are only the tail-pocket side walls (for y ≥ 129) and the bottom beam, up to Z +4.05. They stay ≥ 2.6 mm outside the board edge.
  - Inside the board outline + 1 mm, the frame volume above Z 0 is exactly 0 mm³ (Fusion point cloud and CadQuery common volume).
  - The stud tubes end at Z −3.52. Washers and nuts sit outside the board outline.
  - Wires leave J3/J4/R1 at the top edge and J20/J2 at the left edge. Nothing obstructs them. The J3/J4/R1 wire stubs keep ≥ 7.0 mm in plan from the stud sockets.

**Coordinates.** X = board x. Y = −(board y). Z = 0 at the physical PCB back; −Z points towards the oven front. Plan values in this document are KiCad absolute (x, y down), as the Fusion parameters are typed.

| item | Z (mm) |
|---|---|
| top of the tail-pocket walls (y ≥ 129, outside the board) | +4.05 |
| PCB back = boss tops = support-rib tops = outer-wall top | 0.00 |
| shelf back face | −2.10 |
| stud-tube tops = DIN 9021 washer / nut seat | −3.52 |
| shelf front face = back of the Formex sheet | −4.60 |
| panel back (5.0 mm stand-off) | −5.00 |
| corner-cell rib tops | −6.02 |
| flange back = corner-cell floor back | −8.52 |
| cover-glass front (panel 5.32 thick) | −10.32 |
| flange front = parting plane = inner face of the oven sheet (gasket 1.0 → 0.70) | −11.02 |
| peg tips | −11.82 |

### 1.1 Panel seat
The panel drops into a pocket from the front. Unchanged from v1.

- **Pocket:** 165.40 × 100.50 mm (abs x 19.77–185.17, y 18.75–119.25), i.e. the outline + 0.25 mm per side. Locating faces have a 0.5° draft, opening to the front. The mouth has a 0.8 × 45° lead-in. Pocket corners are R 0.5.
  - The sides keep 0.25 mm. The panel's square corners keep 0.138 mm, where the R 0.5 shelf-front root fillet meets the R 0.5 pocket corner.
- **Shelf (rim):** 2.5 mm thick. It reaches 2.6 mm inside the panel outline, so its inner edge is at abs x 22.62 / 182.32 and y 21.60 / 116.40.
  - The panel's back border rests on the Formex sheet, and the sheet rests on the shelf.
  - The shelf never reaches the active area. The closest point is 1.38 mm, on the right edge.
  - The F3 fuse-clip leads keep 1.36 mm from the shelf back edge.
- **Formex sheet pocket:** the sheet is 163.90 × 99.00 × 0.4 mm (the panel outline − 1 mm), R 1 corners. It is located by the panel pocket walls (0.75 mm per side) and clamped between the shelf and the panel.
- **No front lip.** The oven sheet's window shows only glass.
- **Glass to sheet:** the glass front bears on the sheet through a 1 mm closed-cell silicone sponge gasket (not moulded).
  - Gasket: outer 164.30 × 99.40, inner 157.08 × 88.92 (the cover view area + 1 mm per side), 2364 mm².
  - Design compression: 30 % (0.30 mm), set by the flange front face.
- **Tail exits:** over the tail-pocket width (abs x 39.2–167.4) the pocket wall is removed, and the shelf ends flush with the panel's bottom edge.
  - The tails leave the panel edge face at Z −7.6 (TFT) and −8.9 (CTP), in front of the shelf, so the shelf is never over a tail exit.

### 1.2 PCB seat
- **Bosses:** nine, under the ears H1–H9.
  - Ø 8.0 at the top, 1° draft. They stand on the flange back (H1–H5, H8, H9) or on a corner-cell floor (H6, H7) at Z −8.52 and rise to Z 0.
  - Each boss merges into the outer wall, which serves as the boss-to-rim rib.
  - **Pilot: blind**, Ø 2.4 at the mouth, 0.5° draft. It ends 1.0 mm above the front face (Z −10.02), so the sealing face is closed. Wall 2.8 mm at the top.
  - A Ø 3.2 × 0.5 relief at the mouth keeps formed material from lifting the PCB.
- **Outer wall:** 2.5 mm thick, from the front face up to the PCB plane. Its top lies under the ear roots (copper-free washer keep-outs).
- **PCB support ribs:** 26 ribs, 1.5 mm thick, about every 20 mm along the four edges, at v1's positions.
  - Each runs from the outer wall (buried 0.5 mm) to the shelf window face, 2.6 mm inside the panel outline, on the shelf, with its top at Z 0. Over the tail pocket they run to the shelf end. The window and tail-pocket cuts trim them flush, so there is no land between rib end and shelf edge.
  - All 26 keep ≥ 1.0 mm from every B.Cu pad or solder fillet at the contact face. The minimum is 1.21 mm at J4.1 (mains), §6.
  - The B.Cu GND pour runs under solder mask to 0.5 mm from the edge, so the ribs bear on mask over GND. That is acceptable: it is not mains and not exposed copper.
- **Locating pins:** omitted, as v1. The PCB is located by the nine PT screws in the Ø 3.2 ear holes (±0.3 mm). The panel is located by the frame, not by the PCB.

### 1.3 Tail pocket
- **Size:** a through-opening below the bottom edge, abs x 39.2–167.4 and y 119.11–151.2 at the front face (128.2 × 32.1 mm).
  - It gives 1.5 mm to both U-loop envelopes in x: CTP from x 40.7, TFT to 165.9.
  - It gives 5.0 mm below the TFT loop (y 146.2), so the R 5 inner corners still keep ≥ 1.5 mm from the loop corner.
- **Walls:** 2.5 mm side walls and bottom beam, from the front face.
  - The side walls stay at Z 0 for y < 129 and rise to Z +4.05 from y 129 (parameter `tail_wall_step_y`). This keeps all frame material above Z 0 outside the board outline + 1 mm.
  - The bottom beam and the stepped side walls reach Z +4.05, 1.5 mm above the loops' return legs (Z +2.55).
- **Open front.** The oven sheet closes it, 1.96 mm in front of the CTP leg. A moulded floor was not possible: the CTP tail leaves at Z −8.9, so a floor with 1.5 mm clearance would be only 0.46 mm thick.
- **Open back** for assembly. The FPC ends are folded over the PCB edge into J10/J11 without threading.
- **FPC bend radius** (as v1):
  - The frame has no edge inside or across the loop. The R 5 is the loops' own U-bend (leg spacing 10 mm) plus R 5 inner corners where the loop bottom can rest.
  - A tail pulled taut would wrap the PCB's sharp bottom edge, not the frame. This is an assembly instruction: leave the loop slack, do not tug.
  - A moulded mandrel nose inside the U was studied in v1 and rejected (only R 3.35 possible with 1.5 mm clearance; it needs a stepped parting line or a 6.7 mm solid section).
- **Corner cells:** two cells beside the pocket, closed at the front by a 2.5 mm floor in the front face. They carry the bosses H6/H7. Cell ribs (2.5 mm tall, top Z −6.02) tie boss → bottom beam and run across at y 139. The pegs are no longer here (§1.4).

### 1.4 Mounting to the oven front sheet
- **Flange.** Continuous, 14 mm wide outside the outer wall on all four sides (`flange_w`), 2.5 mm thick (`flange_t`, Z −11.02 … −8.52), outer corners R 12 (`flange_r`).
  - It merges with the 2.5 mm outer wall through an R 0.5 root fillet.
  - Its front face, the corner-cell floors and the tail-pocket wall fronts form one flat face of 11 440 mm² at Z −11.02. That face is the parting plane and the face that bears on the sheet. Only the pegs stand proud of it.
- **Why a flange.** v1's feet were pads cantilevered off the wall. In glass-filled PA6 such a cantilever is notch-sensitive at its root; the owner rejected them ("they will break"). The flange carries the stud load into the wall along its whole length. It also raises the beam stiffness against the gasket 2.3 × (I 713 mm⁴ against 309, §5.4).
- **Stud bosses FH1–FH10.** Each boss is:
  - a tube Ø 10 at the top, 1° draft, standing 5 mm above the flange back (`stud_boss_h`). Its top at Z −3.52 is the washer/nut seat;
  - one 1.5 mm rib from the tube to the wall, full tube height (flange back → tube top), 1° draft, both ends buried 0.5 mm;
  - a hole centred 7.5 mm outside the wall's outer face (`stud_offset`), i.e. 6.5 mm inside the flange edge;
  - a stadium slot 4.5 × 5.3 at the front face (`stud_hole`, `stud_slot` 0.8), 0.5° draft, wider towards the back.
- **Hole rules** (`tools/frame_v2/hole_pattern_calc.py`):
  - ≥ 6.5 mm from the PCB outline including the ears, and ≥ 11.0 mm from the ear holes H1–H9, so that a Ø 12 socket reaches every nut from the component side;
  - ≥ 15 mm from the flange corners (along the edge, from the start of the R 12 arc; minimum 18.67 mm at FH6);
  - top spans ≤ 60 mm (60.0 / 58.5).
- **Why ten.** The owner asked for eight. Under these rules every eight-hole layout fails the gasket-lift criterion: the best one (two per side) gives 178.1 µm at 1000 h against 90 µm. Ten give 71.6 µm (Fusion) / 71.8 µm (CadQuery), §5.4.

| stud | x | y | slot axis ° | r from datum | to PCB outline | nearest ear hole | Ø 12 socket to board |
|---|---|---|---|---|---|---|---|
| FH1 | 43.5 | 8.75 | −134.15 | 84.66 | 10.06 | H1 14.56 | 4.06 |
| FH2 | 103.5 | 8.75 | −89.03 | 60.76 | 7.33 | H2 11.83 | 1.33 |
| FH3 | 162.0 | 8.75 | −45.58 | 85.06 | 8.68 | H3 13.18 | 2.68 |
| FH4 | 195.17 | 40.5 | −17.37 | 97.13 | 7.30 | H4 11.79 | 1.29 |
| FH5 | 195.17 | 98.5 | 17.37 | 97.13 | 7.30 | H5 11.79 | 1.29 |
| FH6 | 171.0 | 161.2 | 53.23 | 114.48 | 33.11 | H6 37.61 | 9.98 (TFT tail) |
| FH7 | 102.5 | 161.2 | 89.98 | 91.70 | 42.2 | H6/H7 81.58 | 9.14 (TFT tail) |
| FH8 | 34.0 | 161.2 | 126.75 | 114.44 | 33.11 | H7 37.61 | 23.36 (CTP tail) |
| FH9 | 9.77 | 98.5 | 162.63 | 97.13 | 7.32 | H8 11.82 | 1.32 |
| FH10 | 9.77 | 40.5 | −162.63 | 97.13 | 7.32 | H9 11.82 | 1.32 |

The slot axis angle is measured from +X in KiCad coordinates (y down). The stud lines are x 9.77 / 195.17 and y 8.75 / 161.2 (`stud_xl`, `stud_xr`, `stud_yt`, `stud_yb`). Spans along the stud line: top 60.0 / 58.5, sides 58.0, bottom 68.5 / 68.5, round the corners 64.9–86.9.

- **Socket clearance.** A Ø 12 socket from Z −4.0 upwards clears every board body (DS1 and its tails included) by ≥ 1.29 mm (FH4/FH5). It clears the frame wall and bosses above the washer top (Z −2.52) by 1.64 mm at every stud.
- **Slots, radial from the datum.** The datum is (102.47, 69.5), the midpoint of the two pegs (`datum_x`, `datum_y`). Each slot's long axis points at it.
  - Over ΔT 60 K the frame (30 / 70 ppm/K) grows 0.21–0.40 mm more than the steel sheet (12 ppm/K) at the studs. The slots take it along their length (§5.5).
- **Locating pegs P1/P2.** Ø 3 × 0.8 mm, 0.5° draft, on the side flanges' front faces at (9.77, 69.5) and (195.17, 69.5), on the stud lines (`peg1_*`, `peg2_*`, `pegs_on`).
  - The sheet has two slots 3.2 × 3.9 along X.
  - The pegs hold the y = 69.5 line and the rotation. x self-centres on the stud slots: FH2 and FH7 point along y, so they locate x within ±0.25.
  - Glass location: y ±0.1 by the pegs, x ±0.25 by the studs. Without pegs (`pegs_on` = 0) the studs locate the glass to ±0.25 both ways.
- **Fixing.** PEM FH-M4-18 studs on the sheet pass through the slots. A DIN 9021 washer and an M4 nyloc nut go on each tube top.
  - Stack from the sheet: 7.5 frame + 1.0 washer + 5 nut = 13.5 mm.
  - Socket access is from the component side (above).
  - Fit the frame before wiring J20: its wires leave the left edge over FH9 (J20 pads at y 100.0 / 105.08, FH9 at y 98.5). Keep the J2 programming cable off FH10 the same way (J2 pins y 30.5–43.2, FH10 at y 40.5).
- **Coplanar front.** Tightening brings the whole front face onto the sheet. It therefore sets the gasket compression by geometry.
- **Sheet window, stud holes and peg slots:** see `renders_v2/Rev3.0_Frame_Drawing_v2.png` and `Rev3.0_FrontSheet_Pattern_v2.dxf` (layers CUTOUT, HOLES, FLANGE_REF, BODY_REF, TEXT).
  - Coordinates are front view, from the window centre (abs x 103.85, y 66.69): u = −(x − 103.85), v = 66.69 − y.
  - The window is 156.08 × 87.92 mm (the cover view area + 0.5 mm per side), R 1.

| hole | u | v | | hole | u | v |
|---|---|---|---|---|---|---|
| FH1 | 60.35 | 57.94 | | FH7 | 1.35 | −94.51 |
| FH2 | 0.35 | 57.94 | | FH8 | 69.85 | −94.51 |
| FH3 | −58.15 | 57.94 | | FH9 | 94.08 | −31.81 |
| FH4 | −91.32 | 26.19 | | FH10 | 94.08 | 26.19 |
| FH5 | −91.32 | −31.81 | | P1 (slot along X) | 94.08 | −2.81 |
| FH6 | −67.15 | −94.51 | | P2 (slot along X) | −91.32 | −2.81 |

Stud holes in the sheet are round, Ø 4.22 +0.08/−0 (PEM FH-M4; the Fusion oven-sheet patch models Ø 4.3). Peg slots are 3.20 × 3.90 along X, +0.1/−0. The stud slots are in the frame, not in the sheet.

### 1.5 Size and mass
- Frame body: 170.40 × 137.45 mm (as v1).
- Overall at the sheet (flange): 198.40 × 165.45 mm, R 12 corners. v1 with feet: 192.0 × 148.0 mm.
- Depth: Z −11.02 … +4.05 = 15.07 mm, plus the 0.8 mm pegs.
- Volume 55.06 cm³, mass ≈ 74.9 g (1.36 g/cm³). v1: 32.5 cm³, 44 g.
- One valid solid, 732 faces. The Fusion body (55.0553 cm³) and the exported STEP (55.053 cm³) match.

## 2. Assumptions (all are user parameters in the Fusion part)

| parameter | value | note |
|---|---|---|
| Oven front sheet | steel, 1.0 mm (`oven_sheet_t`, 1.0–1.5) | PEM FH-M4 needs ≥ 1.0 mm (FHS for stainless) |
| Gasket | closed-cell silicone sponge 1.0 mm, 30 % compression (`gasket_t`, `gasket_comp`) | PSA on the sheet side; see open question 1 |
| Stand-off | 5.0 mm PCB back → panel back (`standoff`) | as baked into the panel model |
| Insulating sheet | 0.4 mm (`sheet_t`), outline − 1 mm | see open question 2 |
| Panel | 164.90 × 100.00, LCM 3.34 ± 0.3 + CTP 1.98 (`panel_t` 5.32) | SAT V.2 sheet 16, Fannal CT0476 |
| Tail loops | CTP x 40.7–75.8 to y 137.4; TFT x 84.0–165.9 to y 146.2; Z −9.06…+2.55 (`loop_*`) | from the panel model; the fit check measures the real tail solids |
| Stud pattern | `fh1_x` … `fh10_y` on the stud lines, `stud_offset` 7.5 | `hole_pattern_calc.py` |
| Thermal | ΔT 60 K; PA6-GF30 30 ppm/K (flow) / 70 ppm/K (transverse); steel 12 ppm/K | `calc_v2.py` |
| Position tolerance | frame slot ± 0.10 (tool-held), PEM stud ± 0.075; RSS 0.125 | `calc_v2.py` |
| Weights | PCB 120 g, panel 200 g, heatsink + Q1 60 g, PSU 50 g, rest 60 g = 0.49 kg | estimates |

## 3. Material

**PA6-GF30, heat-stabilised, flame-retardant (halogen-free), UL94 V-0 at ≤ 1.5 mm, GWFI 960 °C, GWIT ≥ 775 °C, RTI (electrical) ≥ 105 °C, black.** Unchanged from v1.

- **Why this grade:** the part supports a PCB with connections carrying > 0.2 A in an appliance that runs unattended. IEC 60335-1 cl. 30.2.3 therefore asks for GWFI ≥ 850 °C and GWIT ≥ 775 °C (or the 750 °C glow-wire test without flaming > 2 s).
- **Example grade:** Lanxess Durethan BKV30FN04 (PA6-GF30, halogen-free FR), or an equivalent. **Confirm on the datasheet / UL Yellow Card** before ordering the tool.
- **Strength values used:** FR grades are about 15 % weaker than the standard grade, so the calculations use the low end of the owner's PA6-GF30 values at 110 °C:
  - tensile 75 MPa;
  - long-term compressive creep allowance 15 MPa;
  - HDT ≈ 200 °C;
  - E 3500 MPa short-term, 1750 MPa at 1000 h;
  - CLTE 30 ppm/K along the flow, 70 ppm/K transverse.
- **Temperatures:** the frame sees at most 70 °C (the panel limit) to 85 °C (the board's design target), well below 110 °C. The thermal check uses ΔT 60 K.
- **Moisture:** swelling 0.2–0.3 % conditioned. The 0.25 mm pocket clearance minus panel tolerance absorbs it (§6). Over the stud pattern it is not yet checked (open question 4).

## 4. Moulding rules applied

| rule | value in the model |
|---|---|
| nominal wall | 2.5 mm (outer wall, flange, shelf, cell floors, tail-pocket walls) |
| ribs | 1.5 mm = 0.6 × wall. PCB support ribs 2.1 mm tall, cell ribs 2.5 mm, stud ribs 5.0 mm (≤ 3 × wall) |
| bosses | PCB: Ø 8 / blind pilot Ø 2.4, wall 2.8 (1.1 × nominal), 1.0 mm floor, 0.5 mm mouth relief. Studs: Ø 10 tube, 5 mm above the flange back, one rib each |
| draft | 1° on every face along the pull (walls, flange edge, bosses, tubes, ribs, cells, tail pocket, window); 0.5° on the panel locating faces, the pilots, the stud slots and the pegs; lead-in 45°. Scan: **0 flagged of 732 faces** (cones: 44 at 0.5°, 45 at 1.0°, 4 at 45°) |
| undercuts | none (one pull, Z) |
| inside fillets | flange corners R 12, body corners R 5, tail-pocket bottom R 5, cell corners R 2, window R 1, pocket R 0.5. **R 0.5 root fillets modelled** on 337 roots in 8 features: stud tubes + ribs; PCB bosses on the walls; corner cells + cell ribs + cell bosses; support-rib sides; shelf back (not into the tail pocket); wall to flange; shelf front (pocket); tail walls to wall top. Four short corners at the tail pocket stay sharp (§7) |
| slivers | owner's rule (2A/P < 0.3 mm or area < 0.5 mm²): **0 design faces**. 57 hits, all R 0.5 blend patches at fillet corners (47 sphere, 8 B-spline, 1 torus, 1 cylinder; max 0.466 mm²). Fusion and CadQuery agree |
| thin walls | no wall or slot < 1.0 mm (inscribed-disc probe at Z −9.77, −6, −3, −0.5); 0 V-notches |

## 5. Fasteners and stress / creep checks (`calc_v2.py`)

### 5.1 Fasteners (commodity, stocked in Turkey)

| use | part | qty | Turkish trade name |
|---|---|---|---|
| PCB to bosses | ISO 7049-C / DIN 7981 ST2.9 × 9.5, pan head, A2 (alt. PT K30 × 10 thread-forming screw for plastics, same Ø 2.4 pilot) | 9 | "DIN 7981 yıldız başlı sac vidası 2,9×9,5 paslanmaz" |
| studs on the sheet | PEM FH-M4-18 self-clinching stud (alt. ISO 13918 PT M4 weld stud of the same projecting length) | 10 | "PEM çakma saplama M4×18" / "punta kaynak saplaması M4" |
| washers | DIN 9021 M4 (Ø 12 × 1.0), A2 | 10 | "DIN 9021 geniş pul M4" |
| nuts | ISO 10511 (DIN 985) M4 nyloc, A2 | 10 | "DIN 985 fiberli somun M4" |

The PEM / weld studs are made by the sheet-metal supplier. A rivet-nut variant (DIN 7985 M4 screw into an M4 rivet nut) is also possible, but it leaves the rivet-nut flange visible on the front. Studs are flush.

### 5.2 PCB screw bosses (ST2.9 in Ø 2.4 pilot, engaged 6.4 mm, OD/d = 2.76)

Unchanged from v1.

| quantity | conservative (all 0.4 Nm into preload) | realistic (0.2 Nm drive torque subtracted) | limit |
|---|---|---|---|
| preload | 690 N | 345 N | — |
| bearing on the boss top (42.2 mm²) | 16.3 MPa | 8.2 MPa | creep 15–20 MPa |
| thread shear (fill factor 0.6) | 19.7 MPa → SF 2.3 | — | 45 MPa |
| hoop stress (Lamé, flank 30°) | 8.9 MPa → SF 8.4 short-term, 3.4 long-term (0.4×) | — | 75 MPa |

- **Seating torque: 0.3–0.4 Nm.**
- Measure the drive torque and the strip torque on the first articles and keep strip ≥ 3 × drive. The 0.5° pilot draft narrows the pilot towards the screw tip; the first-article check covers it.

### 5.3 Stud bosses (M4 nyloc, 0.6 Nm including about 0.2 Nm prevailing torque)

| quantity | value | limit |
|---|---|---|
| preload | 500 N (750 N conservative) | — |
| bearing under the DIN 9021 washer on the tube top (ring measured on the STEP, 59.4 mm²) | 8.4 MPa (12.6 MPa conservative) | creep 15 MPa |
| clamp margin over the worst-case gasket share per stud (59.1 N) | 8.5× | > 2 |

**Flange bending at a stud.** Load per stud: worst gasket share 59.1 N + 10 g shock 4.8 N = 63.9 N. Sustained: nominal gasket + 1 g = 17.0 N. Lever 7.5 mm (hole centre to the wall face). The worst stud is FH9.

| model | worst load, short-term | sustained | verdict (37.5 MPa = SF 2 on 75; 15 MPa sustained) |
|---|---|---|---|
| a. plate only, b = 10 (tube OD), t 2.5 | 46.0 MPa | 42.6 MPa (worst gasket held) | **fails** |
| c. lever from the tube face 2.5 mm, 45° spread (b 15) | 10.2 MPa | 9.5 MPa | passes |
| d. T-section: flange strip 10 × 2.5 + the real rib 1.5 × 5.0 (height measured on the STEP), I 109.8 mm⁴ | 23.5 MPa at the rib top (SF 3.2), 9.2 MPa at the front face | 6.2 MPa (nominal gasket) | **passes** |

- The rib carries the load. With v2.1's 2.5 mm rib the same T-section gave 46.5 MPa (Fusion-side check). That is why v2.2 raised the tubes to 5 mm above the flange back.
- If the worst gasket force (64 % compression, §6) were held for good, the rib top would see 21.7 MPa > 15. The rib would creep and relax the gasket. That is self-limiting, like the gasket lift in §5.4.
- These are beam models of a 3D corner. **Run an FEA of one stud boss (flange + tube + rib + wall, at the 110 °C values above) before the tool is cut** (open question 9).

### 5.4 Gasket, shelf and frame beam
- **Gasket force:** 165 N nominal (0.07 MPa at 30 %), 591 N at 0.25 MPa (the high-compression case). As a line load round the glass: 0.312 N/mm nominal, 1.116 N/mm worst.
- **Shelf as a cantilever** (geometry unchanged; v1 `tools/frame/out/calc.json`): 1.12 N/mm on a 1.8 mm lever. Bending 1.93 MPa, deflection 0.95 µm. Seat pressure 0.53 MPa.
- **Frame beam.** Section = outer wall 2.5 × 11.02 + flange 14 × 2.5 + shelf 2.85 × 2.5: A 69.7 mm², **I 713 mm⁴ = 2.31 × v1** (309 mm⁴).
  - Measured on the STEP section: 685 mm⁴ on the top and sides, 1270 mm⁴ on the bottom (the cells), 558 mm⁴ near the corners.
  - Model: runs between studs along each edge, corners count as supports, gasket load where the glass edge runs alongside, the smaller of the analytic and the measured I.
  - Limit: min(100 µm, 0.3 × compression) = 90 µm at 1000 h, nominal load.

| edge | longest run | lift, nominal, 1000 h | lift, worst force, 1000 h | bending, worst |
|---|---|---|---|---|
| top | FH1–FH2, 60.0 mm | 44.0 µm | 157 µm | 5.2 MPa |
| sides | FH10–FH9 / FH4–FH5, 58.0 mm | 38.4 µm | 137 µm | 4.9 MPa |
| bottom | FH8–FH7 / FH7–FH6, 68.5 mm | 71.8 µm | 256 µm | 6.8 MPa |

- All nominal runs pass (worst 71.8 µm against 90). v1's top span gave 96 µm nominal and 341 µm worst at 1000 h.
- The worst-force case is self-limiting, as in v1: a gasket at 64 % has excess squeeze to give up.
- The corner runs FH5/FH9 → corner (55.2 mm, 20.5 mm loaded) give 11.8 µm. Walking round a corner as a straight beam, with the gasket load on the whole path, would give up to 186 µm (FH8–FH9). That is an upper bound; with the load only where the glass edge runs it is 35 µm (Fusion `lift_calc`).
- The PCB screwed on top (FR4, E ≈ 20 GPa) stiffens the ring further. That is not counted here.

### 5.5 Thermal mismatch, frame against the steel sheet
- ΔT 60 K; PA6-GF30 30 ppm/K along the flow, 70 ppm/K transverse; steel 12 ppm/K. Stud pattern 185.4 × 152.45 mm.
- **Kinematics.** Both sheet peg holes are slots along X. The pegs fix only the y = 69.5 line and the rotation. The stud slots locate x (FH2/FH7, 0.25 mm across-clearance). The frame therefore grows about the datum (102.47, 69.5), within ±0.25 mm in x.
- **Available travel** per stud: along the slot (5.3 − 4.0)/2 − 0.125 = 0.525 mm; across it (4.5 − 4.0)/2 − 0.125 = 0.125 mm (0.125 = position tolerance, §2).

| stud | r from datum | along the slot (70 / 70 ppm/K) | across the slot (worst anisotropic case) |
|---|---|---|---|
| FH1 / FH3 | 84.7 / 85.1 | 0.295 / 0.296 | 0.102 |
| FH2 | 60.8 | 0.211 | 0.002 |
| FH4 / FH5 / FH9 / FH10 | 97.1 | 0.338 | 0.066 |
| FH6 / FH8 | 114.5 | 0.398 | **0.132** |
| FH7 | 91.7 | 0.319 | 0.000 |

- Along the slots every stud is covered (≤ 0.398 against 0.525).
- Across the slots, FH6 and FH8 would bear by 0.007 mm (0.132 against 0.125) at the pessimistic bound: fibres along x (30 ppm/K), 70 ppm/K along y, ΔT 60 K. With the frame also offset by its ±0.25 mm x-float, every stud could bear on a slot side.
- **Pegs:** peg-to-peg growth 0.645 mm, shared by the two slots: 0.323 mm per peg against 0.325 mm play. With the ±0.25 x-float it is 0.573 mm, so a peg can touch its slot end.
- **Why this is acceptable.** Bearing is self-limiting: fully restrained, the frame would see 12.2 MPa short-term, relaxing to 6.1 MPa at 1000 h (both under the allowances). It is no assembly problem: the slots are centred at room temperature. At ΔT 40 K everything is covered in the datum case (FH6/FH8 across 0.088 mm; 0.215 mm per peg). Listed as open question 4.

### 5.6 Weight
- 0.49 kg → 4.8 N static.
- At 10 g shock: 4.8 N per M4 stud and 3.2 N per PCB screw. Negligible.

## 6. Fit check against the real board

Two independent checks:
- **Fusion:** the fit assembly (board STEP with every model, DS1 and its folded tails, shifted +0.08 mm in Z; Formex sheet; compressed gasket; oven-sheet patch; hidden Ø 12 socket cylinders). Scripts 34, 51 and 65; results in the `checks` block of `Rev3.0_Frame_v2_params.json`.
- **CadQuery:** `build_v2.py` on the exported STEP (BRepExtrema distances + common volumes). Results in `tools/frame_v2/out/fitcheck.txt` / `.json`.

**Board model.** `kicad-cli pcb export step --subst-models` with every footprint model. KiCad leaves the copper and mask out, so the physical PCB back sits 0.08 mm below the exported core; the board is shifted +0.08 mm.

| check | result |
|---|---|
| frame vs 145 component models (282 bodies) | **0 intersections** (both checks). Closest: F3 fuse-clip leads and J3 wire stubs 1.364 mm (shelf back edge); U3 / C333 / R129 on the top side 1.64 mm; J2 header leads 1.84 mm; PS1 1.99 mm; R1/J3 wire stubs 2.07 mm |
| frame vs PCB body | 0 volume. 0.08 mm = the missing copper + mask, i.e. physical contact at the boss tops, rib tops and wall top only |
| contact faces (Z 0) vs B.Cu pads | min **1.21 mm (J4.1, mains)** at a rib ≥ 1.0 ✓. Bosses 6.17 mm (F3.2), wall 2.84 mm (J3.1). 3D distance frame → J4 model 2.20 mm |
| rib footprint (information) | nominal rib outline 1.15 mm to J4.1 (`rib_pad_check.py`); rib base with its R 0.5 root fillets at Z −2.08: 0.83 mm in plan, 2.1 mm below the board |
| tail loops vs frame | TFT 1.557 mm, CTP 1.554 mm (≥ 1.5 ✓). Fingers 3.06 / 4.58 mm. 0 volume |
| panel vs frame | 0 volume. Min 0.138 mm (LCM corners at the R 0.5 pocket corners); PU tape 0.18, CTP 0.18, glass 0.19 mm; sides 0.25 mm |
| Formex sheet | touches the shelf (0 volume); panel on the sheet |
| gasket vs frame | 0.607 mm (gasket inside the pocket) |
| oven-sheet patch vs frame | 0 volume (coplanar contact at Z −11.02, pegs in the slots) |
| lead protrusions vs the Formex sheet (Z −4.6) | PS1 **1.335 mm**; HS1 1.735; Q1 2.10 only with the leads trimmed to ≤ 2.5 (untrimmed 8.1 mm goes 0.54 mm³ through the sheet); L40/L1/F1/F3/J20/C40 2.735; K1 2.835; U1/U5 2.935 |
| mains copper → frame contact → panel metal | closest mains copper to a frame contact 1.21 mm (J4.1). Creepage (PCB surface + rib side + shelf back + shelf inner face + shelf/sheet interface) **7.95 mm ≥ 6.4** ✓ (v1 8.52; Fusion-side 7.85 with the nominal rib). Air clearance round the shelf corner + interface **6.70 mm ≥ 4.0** ✓ (R1.2) |
| tool access (Ø 12 socket, Z −4.0 → +45, all board bodies incl. DS1) | min 1.29 mm (FH4/FH5, PCB edge); FH9/FH10 1.32, FH2 1.33, FH3 2.68, FH1 4.06; FH6–FH8 ≥ 9.1 mm to the tails |
| washer + socket vs frame | clear. 1.64 mm to the frame faces above the washer top (Z −2.52) at every stud |
| nothing above Z 0 inside board + 1 mm | **0 mm³**. Frame above Z 0 = tail-pocket walls only (1518 mm³), ≥ 2.6 mm from the board edge (Fusion 2.596, CadQuery 2.68) |
| sliver / draft / thin wall | 0 design-face slivers; 0 draft flags; no wall < 1.0 mm (§4) |

Tolerance notes (as v1):
- **Pocket vs panel:** the pocket is 165.40 ± 0.1 and the LCM is 164.90 ± 0.3, so the clearance per side ranges from 0.05 to 0.35 mm. Interference is not possible.
- **Gasket:** RSS of the LCM ± 0.3, the CTP stack ± 0.1, the frame seat ± 0.1 and the sheet ± 0.05 is ± 0.34 mm. That moves the 1.0 mm gasket between **0 % and 64 %** compression (open question 1).

## 7. Moulding notes

- **Tool:** single-cavity, 2-plate, no slides or lifters.
- **Parting line:** in the flange front plane (Z −11.02), on the outer flange perimeter.
  - Fixed half (A): the flat front face with the two peg pockets, plus a core block that forms the panel pocket up to the shelf (Z −4.6). The window and the tail pocket are shut-offs against the moving half.
  - Moving half (B): everything else. Flange back, stud tubes and ribs, the slot pins (the slots widen towards the back), PCB bosses and their blind pilot pins, support ribs, cells, tail-pocket walls and the open space above the shelf. The part shrinks onto the B cores and stays on the moving half.
- **Gates:** 4 tunnel / sub-gates (or hot-runner valve gates) on the B side, into the outer-wall tops (Z 0 faces). Suggested positions:
  - mid-left and mid-right (abs y ≈ 69, between FH9/FH10 and FH4/FH5);
  - top at abs x ≈ 62 and 145, between the bosses and between the studs;
  - so that the weld lines fall between bosses, not on them.
  - Run a fill / warp simulation (Moldflow or equivalent) before the steel is cut: PA-GF rings with a flange are prone to warp. Keep the weld lines off H1–H9 and FH1–FH10.
- **Ejectors (B side, on non-visible faces):**
  - sleeve ejectors round the 9 pilot core pins (boss tops);
  - Ø 2 pins on the outer-wall tops about every 40 mm;
  - pins on the 10 stud-tube tops (witness flush: it is the washer seat), on the flange back, the corner-cell floor backs and the tail-pocket wall tops.
  - No ejector marks on the front face (it is the sealing face).
- **Shrinkage:** PA6-GF30 0.3 % flow / 0.5 % transverse.
  - Scale the tool per the gating direction.
  - Hold the pocket at 165.40 / 100.50 ± 0.1, the boss positions ± 0.1 and the stud-slot positions ± 0.1 (the thermal check assumes ± 0.10).
  - Check on the first shots: boss pattern against the PCB ears, pitch 174.6 × 109.6 mm; stud pattern 185.4 × 152.45 mm against the sheet.
- **Flatness:** flange front face ≤ 0.3 mm over the part, measured unclamped. It sets the gasket compression.
- **General tolerance:** ISO 20457 TG5.
- **Marking:** material code `>PA6-GF30 FR<` and the cavity number on the flange back.
- **Inside corners left sharp** (accepted by the owner, 2026-11-13; listed for the toolmaker in the Fusion README). An R 0.5 there rolls up the tail wall or across the free shelf strip:
  1. tail-pocket corner, left: shelf end face (y 119.0) ↔ tail-pocket side face (x ≈ 39.2), vertical, Z −4.6 … −2.1;
  2. the same on the right, x ≈ 167.4;
  3. shelf back ↔ bottom pocket wall, left segment: y 119.25, x ≈ 29.3–39.0, Z −2.1;
  4. the same on the right, x ≈ 167.6–175.7.

  The toolmaker may break these four with a small radius in the steel (≤ 0.2) if the polishing allows.
- **Assembly order:**
  1. Panel glass-down on a soft fixture.
  2. Formex sheet on the panel back.
  3. Frame over it.
  4. PCB onto the bosses (Q1 leads already trimmed to ≤ 2.5 mm); 9 screws at 0.3–0.4 Nm.
  5. Fold the tails into J10 / J11 with the loops left slack in the pocket.
  6. Mount on the oven sheet (the gasket is already on the sheet): pegs into the sheet slots, flange over the 10 studs; 10 DIN 9021 washers and 10 nyloc nuts at 0.6 Nm, tightened crosswise.
  7. Then wire J20 (its wires pass over FH9).

  Before mounting, the panel is held only by the PCB/sheet stack. For handling, use two strips of double-sided tape (e.g. 3M 9088) on the shelf, or a PSA-backed Formex sheet.

## 8. Open questions for the owner

1. **Gasket thickness.**
   - With the LCM's ± 0.3 mm thickness tolerance, a 1.0 mm gasket can end up at 0 % (no seal) or 64 % compression.
   - Proposal: a **1.5 mm** gasket at 30 % (0.45 mm). That needs `gasket_t` = 1.5, which moves Z_FRONT (and with it the flange and the stud tubes) 0.35 mm forward. The stack from the sheet stays 13.5 mm.
   - Alternative: measure real panels and keep 1.0 mm.
2. **Insulation between the mains leads and the panel's metal back.**
   - "0.4 mm Formex GK-10" is inconsistent: GK-10 is 0.25 mm and **GK-17 is 0.43 mm**.
   - The air gap from PS1's AC pins to the sheet is only 1.335 mm. The sheet is therefore the insulation that counts.
   - If the LCM frame is SELV-connected or accessible, IEC 60335-1 cl. 29.3 needs reinforced insulation. A thin sheet counts as reinforced only as ≥ 3 layers that each pass the electric-strength test (e.g. 3 × 0.13 mm), or ≥ 2 mm solid.
   - Decide the grade and the layer count. The pocket takes 0.4 mm as modelled.
3. **Ten studs instead of eight: accepted by the owner on 2026-11-13.** Every eight-hole layout fails the gasket lift (best 178.1 µm against 90 µm; ten: 71.8 µm). Eight would have needed about twice the beam stiffness, e.g. a back rib along each side (not studied).
4. **Slots, radial orientation and the thermal bound.**
   - At the pessimistic bound (ΔT 60 K, 30 / 70 ppm/K) FH6/FH8 bear across their slot by 0.007 mm, and with the ±0.25 x-float every stud and one peg can bear. It is self-limiting (≤ 12.2 MPa restrained), and at ΔT 40 K everything is covered (§5.5).
   - Moisture swelling (0.2–0.3 %, §3) is not in this check. Over r ≈ 115 mm it is of the same order as the thermal growth (≈ 0.3 mm), radial, so mostly along the slots. Decide whether the tool is scaled for the conditioned state, and accept or re-check.
   - Accept, or lengthen / widen the slots (`stud_slot`, `stud_hole`)?
5. **Pegs on the side flanges.** The sheet gets two 3.2 × 3.9 slots at u 94.08 / −91.32, v −2.81, visible from the front unless the decor covers them. Keep them, or set `pegs_on` = 0? Without pegs the glass locates to ±0.25 by the studs.
6. **Stud type:** PEM FH-M4-18 (sheet ≥ 1.0 mm steel; FHS for stainless) or weld studs? What is the final sheet thickness? Confirm the stud length against it (13.5 mm needed above the sheet's inner face).
7. **Q1 lead trimming** to ≤ 2.5 mm is a mandatory assembly step (8.1 mm untrimmed goes through the Formex sheet). Add it to the assembly instructions and the PCBA order notes?
8. **Four sharp inside corners** at the tail pocket (§7). Accepted on 2026-11-13; the toolmaker may break them ≤ 0.2 mm.
9. **FEA and Moldflow before steel:** an FEA of one stud boss (§5.3; the plate-only model fails, the T-section passes) and a fill / warp study for the flange flatness (≤ 0.3 mm) and the weld lines.
10. **Material grade:** confirm Durethan BKV30FN04 (or the supplier's equivalent) on its datasheet / UL card. Check GWIT 775 °C at 2.5 mm and RTI.
11. **Tail handling:** the loops are slack in an open pocket; there is no mandrel. Accept the "do not tug, leave slack" instruction, or shorten the tails (custom FPC length) in a later panel order?

v1's question 9 (root fillets in the tooling CAD) is closed: the fillets are modelled.

## 9. CAD and files

**Fusion 360** (hub1 › project Oven › folder "Rev3.0 OVEN CONTROLLER"):
- `Rev3.0 Frame v2`, version 6: the parametric part, one body "Frame v2", 109 timeline features.
  - 137 user parameters, among them `wall`, `rib`, `draft`, `draft_loc`, `fillet_root`, `standoff`, `sheet_t`, `panel_t`, `gasket_t`, `gasket_comp`, `oven_sheet_t`, `flange_w` / `flange_t` / `flange_r`, `stud_hole`, `stud_slot`, `stud_boss_od` / `stud_boss_h`, `stud_offset`, `datum_x` / `datum_y`, `tail_wall_step_y`, `fh1_x` … `fh10_y`, `peg1_*` / `peg2_*`, `pegs_on`.
  - The Z levels are derived parameters (`Z_FRONT = Z_GLASS − gasket_t × (1 − gasket_comp)`, `Z_FLANGE_BACK`, `Z_STUD_TOP`, …).
  - Not parametric: the 26 support ribs (fixed v1 geometry, `fv2lib.RIBS`) and the radial slot sketches (re-run script 59b if `fhN`, `datum_*`, `stud_hole` or `stud_slot` change).
- `Rev3.0 Frame v2 fit assembly`, version 6: the frame as a linked occurrence; the board STEP with every model incl. DS1 and its tails, shifted +0.08 Z; Formex sheet; compressed gasket; oven-sheet patch (10 × Ø 4.3 stud holes, 2 peg slots); hidden socket cylinders.

**History** (`tools/frame_v2/fusion/README.md`):

| step | frame version | content |
|---|---|---|
| v2.0 | v1–v3 | flange and 10 round stud holes; root fillets |
| v2.1 | v4–v5 | symmetric flange 14 / offset 7.5, slots 4.5 × 5.3 along the edge, tail walls stepped at y 129, ribs to the shelf edge, hole shift |
| v2.2 | v6 | stud tubes 5 mm above the flange back (seat Z −3.52, full-height ribs, PEM FH-M4-18), pegs on the side flanges, radial slots |
| v2.2 final | v6 (assembly v6) | both sheet peg holes slots along X (owner decision) |

**Build scripts** `Design Reports/Rev3.0/tools/frame_v2/fusion/`: `01_…` to `68_…` plus the shared helper `fv2lib.py`, run through the Fusion MCP. The README holds the rebuild order, the run log, the final hole table and the four sharp corners.

**Offline scripts** `Design Reports/Rev3.0/tools/frame_v2/`: `hole_pattern_calc.py` (stud rules, gasket lift, thermal; `hole_pattern_result.json`), `rib_pad_check.py` (`rib_pad_result.json`), `above_z0_check.py`, `fit_analyse.py`, `build_params_json.py` (writes the params JSON).

**Independent verification** `Design Reports/Rev3.0/tools/frame_v2/` (CadQuery, README with the venv recipe): `build_v2.py` with `cadcheck_v2.py`, `fitcheck_v2.py`, `calc_v2.py`, `render_v2.py`, `sections_v2.py`, `drawing_v2.py`, `common_v2.py`, `dump_board.py`. Outputs in `out/`: `summary.json`, `cadcheck.json`, `fitcheck.json` / `.txt`, `calc.json` / `.md`.
- The board STEP for the run is exported by `kicad-cli` into the session scratchpad; `--export-board` regenerates it.
- **v1 regression** (`build_v2.py --v1`, `out/v1/`, `renders_v2/v1_regression/`): it reproduces v1's numbers (F3 1.268, tails 1.554, panel 0.15, creepage 8.52, gasket 0.607, 32.5 cm³, I 309 mm⁴), with the differences explained in `out/v1/summary.json`. Its stricter checks also flag on v1: washer/socket against the wall at F2, F3, F5, F8; 11.9 mm³ above Z 0 inside the board + 1 mm (0.40 mm plan gap); 26 axial cylinders without draft; 17 V-notches. v2 clears all of them.

**Exports** `Mechanical/Rev3.0_Frame/`:
- `Rev3.0_Frame_v2.step`, `.stl`, `.f3d` (frame version 6).
- `Rev3.0_Frame_v2_params.json`: parameters, derived Z levels, `stud_holes` (slot axes, thermal), `pegs`, `oven_sheet`, `body`, `lift_calc`, `stud_bending_T_section`, `checks`.
- `Rev3.0_FrontSheet_Pattern_v2.dxf`: window, 10 stud holes, 2 peg slots, flange and body outlines (reference), front view.
- `renders_v2/`:
  - CadQuery renders `Frame_iso_front`, `Frame_iso_back`, `Frame_front`, `Frame_back`, `Assembly_iso_front`, `Assembly_iso_back`, `Assembly_front`, `Assembly_back`, `Assembly_side`;
  - sections `Section_A_stud_FH2_x103.5`, `Section_B_pcb_bosses_x30` (through H1 and H7), `Section_C_tail_pocket_x125`, `Section_D_flange_plan_Z-9.77`, `Section_E_stud_FH10_y40.5`;
  - drawing `Rev3.0_Frame_Drawing_v2` (main dimensions, hole table, Z stack);
  - Fusion screenshots `Fusion_Frame_front`, `_back`, `_iso_front`, `_iso_back`, `_closeup_stud_boss_FH2`, `_closeup_peg_P1_side_flange`, `_closeup_tail_pocket`, `Fusion_Assembly_iso_front`, `_iso_back`, `_iso_back_no_PCB`, `_back_no_PCB` (.png).

**Superseded (v1):** the CadQuery model in `Design Reports/Rev3.0/tools/frame/` and its outputs `Mechanical/Rev3.0_Frame/Rev3.0_Frame.*`, `Rev3.0_Assembly.step`, `Rev3.0_Frame_Drawing.png`, `Rev3.0_FrontSheet_Pattern.dxf` and the unsuffixed renders/sections; kept for reference only.
