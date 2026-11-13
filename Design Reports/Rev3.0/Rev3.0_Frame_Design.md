# Rev3.0 OVEN CONTROLLER — carrier frame design (2026-11-13)

Owner: Ömer Karaoğlu (READARK). Part: one injection-moulded **carrier frame** that holds the Rev3.0 PCB and the 7" SATOZ SAT070AT40D21 panel (GT911 CTP), and mounts the pair to the oven's steel front sheet from the inside.

- Model and scripts: `Design Reports/Rev3.0/tools/frame/` (`frame.py` parameters and geometry, `build.py`, `fitcheck.py`, `calc.py`, `render.py`, `sections.py`, `drawing.py`, `dump_board.py`, README with the venv recipe).
- Outputs: `Mechanical/Rev3.0_Frame/`. All numbers below come from `tools/frame/out/summary.json` (build of 2026-11-13).

## 1. Concept

The frame is a flat ring that sits between the panel (in front) and the PCB (behind).

- **Mould direction.** One pull direction, along the panel axis. There are no undercuts and no side actions.
- **Component side open.** Nothing is above the PCB plane over the board:
  - the outer wall, the boss tops and the PCB support ribs all end at the PCB back (Z = 0);
  - the only features above Z = 0 are the tail-pocket walls, which stand below the board's bottom edge (outside the board, Z ≤ +4.05).
  - Wires leave J3/J4/R1 at the top edge and J20/J2 at the left edge. Nothing obstructs them.

**Coordinates.** X = board x. Y = −(board y). Z = 0 at the physical PCB back; −Z points towards the oven front.

| item | Z (mm) |
|---|---|
| PCB back = boss tops = support-rib tops = outer-wall top | 0.00 |
| shelf back face | −2.10 |
| shelf front face = back of the Formex sheet | −4.60 |
| panel back (5.0 mm stand-off) | −5.00 |
| cover-glass front (panel 5.32 thick) | −10.32 |
| feet plane = inner face of the oven sheet (gasket 1.0 → 0.70) | −11.02 |
| top of the tail-pocket walls (outside the board) | +4.05 |

### 1.1 Panel seat
The panel drops into a pocket from the front.

- **Pocket:** 165.40 × 100.50 mm, i.e. the outline + 0.25 mm per side. Locating faces have a 0.5° draft, opening to the front. The mouth has a 0.8 × 45° lead-in. Pocket corners are R 0.5; the panel's square corner keeps 0.15 mm.
- **Shelf (rim):** 2.5 mm thick. It reaches 2.6 mm inside the panel outline, so its inner edge is at abs x 22.62 / 182.32 and y 21.60 / 116.40.
  - The panel's back border rests on the Formex sheet, and the sheet rests on the shelf.
  - The shelf never reaches the active area. The closest point is 1.38 mm, on the right edge.
  - The shelf was narrowed from 3.0 mm to 2.6 mm so that the F3 fuse-clip leads keep ≥ 1 mm from it.
- **Formex sheet pocket:** the sheet is 163.90 × 99.00 × 0.4 mm (the panel outline − 1 mm), R 1 corners. It is located by the panel pocket walls (0.75 mm per side) and clamped between the shelf and the panel.
- **No front lip.** The oven sheet's window shows only glass.
- **Glass to sheet:** the glass front bears on the sheet through a 1 mm closed-cell silicone sponge gasket (not moulded).
  - Gasket: outer 164.30 × 99.40, inner 157.08 × 88.92 (the cover view area + 1 mm per side), 2364 mm².
  - Design compression: 30 % (0.30 mm), set by the feet plane.
- **Tail exits:** over the tail-pocket width (abs x 39.2–167.4) the pocket wall is removed, and the shelf ends flush with the panel's bottom edge.
  - The tails leave the panel edge face at Z −7.6 (TFT) and −8.9 (CTP), in front of the shelf, so the shelf is never over a tail exit.

### 1.2 PCB seat
- **Bosses:** nine, under the ears H1–H9.
  - Ø 8.0 at the top, Ø 8.38 at the base (1° draft), 11.02 mm tall from the feet plane.
  - Ø 2.4 pilot through (cored from both sides, uniform 2.8 mm wall), with a Ø 3.2 × 0.5 relief at the mouth so formed material cannot lift the PCB.
  - Each boss merges into the outer wall, which serves as the boss-to-rim rib.
- **Outer wall:** 2.5 mm thick, from the feet plane up to the PCB plane. Its top lies under the ear roots (copper-free washer keep-outs).
- **PCB support ribs:** 26 ribs, 1.5 mm thick, about every 20 mm along the four edges.
  - Each runs from the outer wall to 2.1 mm inside the panel outline, on the shelf, with its top at Z 0.
  - Each was placed ≥ 1.0 mm from every B.Cu pad or solder fillet. The minimum is 1.32 mm, at J3.1.
  - Over the tail pocket they stop 0.5 mm before the shelf end.
  - The B.Cu GND pour runs under solder mask to 0.5 mm from the edge, so the ribs bear on mask over GND. That is acceptable: it is not mains and not exposed copper.
- **Locating pins:** omitted. The PCB is located by the nine PT screws in the Ø 3.2 ear holes (±0.3 mm) and needs no closer location. The panel is located by the frame, not by the PCB.

### 1.3 Tail pocket
- **Size:** a through-opening below the bottom edge, abs x 39.2–167.4 and y 119.25–151.2 (128.2 × 31.9 mm).
  - It gives 1.5 mm to both U-loop envelopes in x: CTP from x 40.7, TFT to 165.9.
  - It gives 5.0 mm below the TFT loop (y 146.2), so the R 5 inner corners still keep ≥ 1.5 mm from the loop corner.
- **Walls:** 2.5 mm side walls and bottom beam, from the feet plane to Z +4.05, i.e. 1.5 mm above the loops' return legs (Z +2.55).
- **Open front.** The oven sheet closes it, 1.96 mm in front of the CTP leg. A moulded floor was not possible: the CTP tail leaves at Z −8.9, so a floor with 1.5 mm clearance would be only 0.46 mm thick.
- **Open back** for assembly. The FPC ends are folded over the PCB edge into J10/J11 without threading.
- **FPC bend radius:**
  - The frame has no edge inside or across the loop. The R 5 is the loops' own U-bend (leg spacing 10 mm) plus R 5 inner corners where the loop bottom can rest.
  - A tail pulled taut would wrap the PCB's sharp bottom edge, not the frame. This is an assembly instruction: leave the loop slack, do not tug.
  - A moulded mandrel nose inside the U was studied and rejected. With 1.5 mm clearance it could only be R 3.35. A half-cylinder on the parting plane needs a stepped parting line or a solid 6.7 mm section (sinks).
- **Corner cells:** two cells beside the pocket, closed at the front by a 2.5 mm floor. They carry the bosses H6/H7, the bottom feet F6/F7 and the locating pegs. Ribs tie boss → foot → cell walls.

### 1.4 Mounting to the oven front sheet
- **Eight feet** (the brief proposed six):
  - corners F1 and F4;
  - top F2 and F3 at the third points;
  - sides F5 and F8 at mid-height;
  - bottom F6 and F7 in the corner cells.
  - Why eight: the gasket pushes the panel and the frame away from the sheet, and between feet the 2.5-wall frame bends (§5.4). With six feet the top span was 80 mm. Corner feet bring every span to ≤ 60 mm and cut the lift by 3×.
- **Each foot:** a 12 mm pad plate (2.5 mm thick, in the feet plane) running into the wall, plus a tube Ø 9.5 / Ø 4.5 (wall 2.5 mm), 5 mm tall. The nut seat is the tube top, Z −6.02.
- **Fixing:** M4 studs on the sheet pass through the Ø 4.5 holes, with a DIN 9021 washer and an M4 nyloc nut.
  - Socket access is from the component side. No ear or board edge is within 2 mm of a Ø 12 socket.
  - Fit the frame before wiring J20, because the J20 wires pass over F8.
- **Coplanar front.** The feet, the outer-wall front, the cell floors and the tail-pocket walls all lie in the feet plane. Tightening therefore brings the whole front face onto the sheet and sets the gasket compression by geometry.
- **Locating pegs:** two Ø 3 × 0.8 mm (P1/P2, parameter `PEGS`), on the cell floors, into Ø 3.2 holes in the sheet. They locate the glass in the window to ±0.1 mm instead of the stud clearance (±0.25).
- **Sheet window, studs and peg holes:** see `Rev3.0_Frame_Drawing.png` and `Rev3.0_FrontSheet_Pattern.dxf`. Coordinates are front view, from the window centre.
  - The window is 156.08 × 87.92 mm (the cover view area + 0.5 mm per side), R 1.

| hole | u | v | | hole | u | v |
|---|---|---|---|---|---|---|
| F1 | 90.85 | 54.69 | | F6 | −73.15 | −72.31 |
| F2 | 31.15 | 54.69 | | F7 | 75.85 | −72.31 |
| F3 | −28.45 | 54.69 | | F8 | 91.25 | −2.31 |
| F4 | −88.15 | 54.69 | | P1 | 71.35 | −79.31 |
| F5 | −88.55 | −2.31 | | P2 | −68.65 | −79.31 |

Stud holes are Ø 4.22 +0.08 (PEM FH-M4). Peg holes are Ø 3.2 +0.1.

### 1.5 Size and mass
- Frame body: 170.40 × 137.45 mm.
- Overall with feet: 192.0 × 148.0 mm.
- Depth: Z −11.02 … +4.05 = 15.07 mm, plus the 0.8 mm pegs.
- Volume 32.5 cm³, mass ≈ 44 g (1.36 g/cm³).

## 2. Assumptions (all are parameters in `frame.py`)

| parameter | value | note |
|---|---|---|
| Oven front sheet | steel, 1.0 mm (`OVEN_SHEET_T`, 1.0–1.5) | PEM FH-M4 needs ≥ 1.0 mm (FHS for stainless) |
| Gasket | closed-cell silicone sponge 1.0 mm, 30 % compression (`GASKET_T`, `GASKET_COMP`) | PSA on the sheet side; see open question 1 |
| Stand-off | 5.0 mm PCB back → panel back (`STANDOFF`) | as baked into the panel model |
| Insulating sheet | 0.4 mm (`SHEET_T`), outline − 1 mm | see open question 2 |
| Panel | 164.90 × 100.00, LCM 3.34 ± 0.3 + CTP 1.98 | SAT V.2 sheet 16, Fannal CT0476 |
| Tail loops | CTP x 40.7–75.8 to y 137.4; TFT x 84.0–165.9 to y 146.2; Z −9.06…+2.55 | from the panel model; the fit check measures the real tail solids |
| Weights | PCB 120 g, panel 200 g, heatsink + Q1 60 g, PSU 50 g, rest 60 g = 0.49 kg | estimates |

## 3. Material

**PA6-GF30, heat-stabilised, flame-retardant (halogen-free), UL94 V-0 at ≤ 1.5 mm, GWFI 960 °C, GWIT ≥ 775 °C, RTI (electrical) ≥ 105 °C, black.**

- **Why this grade:** the part supports a PCB with connections carrying > 0.2 A in an appliance that runs unattended. IEC 60335-1 cl. 30.2.3 therefore asks for GWFI ≥ 850 °C and GWIT ≥ 775 °C (or the 750 °C glow-wire test without flaming > 2 s).
- **Example grade:** Lanxess Durethan BKV30FN04 (PA6-GF30, halogen-free FR), or an equivalent. **Confirm on the datasheet / UL Yellow Card** before ordering the tool.
- **Strength values used:** FR grades are about 15 % weaker than the standard grade, so the calculations use the low end of the owner's PA6-GF30 values at 110 °C:
  - tensile 75 MPa;
  - long-term compressive creep allowance 15 MPa;
  - HDT ≈ 200 °C;
  - E 3500 MPa short-term, 1750 MPa at 1000 h.
- **Temperatures:** the frame sees at most 70 °C (the panel limit) to 85 °C (the board's design target), well below 110 °C.
- **Moisture:** swelling 0.2–0.3 % conditioned. The 0.25 mm pocket clearance minus panel tolerance absorbs it (§6).

## 4. Moulding rules applied

| rule | value in the model |
|---|---|
| nominal wall | 2.5 mm (outer wall, shelf, cell floors, pocket walls, foot tubes) |
| ribs | 1.5 mm = 0.6 × wall; PCB support ribs 2.1 mm tall, cell ribs 2.5 mm (≤ 3 × wall) |
| bosses | Ø 8 / pilot Ø 2.4, wall 2.8 (1.1 × nominal), cored through, 0.5 mm mouth relief |
| draft | 1° on every face along the pull (walls, bosses, ribs, feet, cells, tail pocket, window); 0.5° on the panel locating faces and the pegs; lead-in 45° |
| undercuts | none (one pull, Z) |
| inside fillets | frame corners R 5, tail-pocket bottom R 5, cell corners R 2, pad corners R 3, window R 1, pocket R 0.5. **Not yet modelled:** R 0.5 at the boss, rib and wall roots. Add them in the tooling CAD (CadQuery fillets on the drafted boolean body were not robust) |
| slivers | owner's cadcheck rule (faces 2A/P < 0.3 mm or area < 0.5 mm²): **0 of 342 faces** |

## 5. Fasteners and stress / creep checks (`calc.py`)

### 5.1 Fasteners (commodity, stocked in Turkey)

| use | part | qty | Turkish trade name |
|---|---|---|---|
| PCB to bosses | ISO 7049-C / DIN 7981 ST2.9 × 9.5, pan head, A2 (alt. PT K30 × 10 thread-forming screw for plastics, same Ø 2.4 pilot) | 9 | "DIN 7981 yıldız başlı sac vidası 2,9×9,5 paslanmaz" |
| studs on the sheet | PEM FH-M4-15 self-clinching stud (alt. ISO 13918 PT M4 × 15 weld stud) | 8 | "PEM çakma saplama M4×15" / "punta kaynak saplaması M4×15" |
| washers | DIN 9021 M4 (Ø 12 × 1.0), A2 | 8 | "DIN 9021 geniş pul M4" |
| nuts | ISO 10511 (DIN 985) M4 nyloc, A2 | 8 | "DIN 985 fiberli somun M4" |

The PEM / weld studs are made by the sheet-metal supplier. A rivet-nut variant (DIN 7985 M4 screw into an M4 rivet nut) is also possible, but it leaves the rivet-nut flange visible on the front. Studs are flush.

### 5.2 PCB screw bosses (ST2.9 in Ø 2.4 pilot, engaged 6.4 mm, OD/d = 2.76)

| quantity | conservative (all 0.4 Nm into preload) | realistic (0.2 Nm drive torque subtracted) | limit |
|---|---|---|---|
| preload | 690 N | 345 N | — |
| bearing on the boss top (42.2 mm²) | 16.3 MPa | 8.2 MPa | creep 15–20 MPa |
| thread shear (fill factor 0.6) | 19.7 MPa → SF 2.3 | — | 45 MPa |
| hoop stress (Lamé, flank 30°) | 8.9 MPa → SF 8.4 short-term, 3.4 long-term (0.4×) | — | 75 MPa |

- **Seating torque: 0.3–0.4 Nm.**
- Measure the drive torque and the strip torque on the first articles and keep strip ≥ 3 × drive. The boss OD was raised from 6 to 8 mm to bring the bearing stress down to the creep allowance.

### 5.3 Feet (M4 nyloc, 0.6 Nm including about 0.2 Nm prevailing torque)
- Preload 500 N (750 N conservative).
- Bearing under the DIN 9021 washer on the tube top (55 mm²): 9.1 MPa (13.6 MPa conservative), under the 15 MPa allowance.
- Clamp margin over the worst-case gasket share per foot: 5.1×.

### 5.4 Gasket, shelf and frame beam
- **Gasket force:** 165 N nominal (0.07 MPa at 30 %), 591 N at 0.25 MPa (the high-compression case).
- **Shelf as a cantilever:** 1.12 N/mm on a 2.0 mm lever. Bending 2.1 MPa, deflection 1.3 µm. Seat pressure 0.45 MPa.
- **Top side between adjacent feet** (span 59.7 mm, I = 309 mm⁴, outer wall + shelf):

| case | bending | lift, short-term | lift, 1000 h |
|---|---|---|---|
| nominal | 2.7 MPa | 48 µm | 96 µm |
| worst | 9.6 MPa | 171 µm | 341 µm |

- The nominal lift costs ≤ 0.1 mm of the 0.3 mm compression. The worst case is self-limiting, because a gasket at 60 % has excess squeeze to give up.
- The PCB screwed on top (FR4, E ≈ 20 GPa) stiffens the ring further. That is not counted here.

### 5.5 Weight
- 0.49 kg → 4.8 N static.
- At 10 g shock: 8 N per M4 stud and 3.2 N per PCB screw. Negligible.

## 6. Fit check against the real board (`fitcheck.py`, BRepExtrema distances + common volumes)

**Board model.** Board STEP from `kicad-cli pcb export step --subst-models` with every footprint model, shifted +0.08 mm in Z. KiCad leaves the copper and mask out, so the physical PCB back sits 0.08 mm below the exported core.

| check | result |
|---|---|
| frame vs 145 component models | **0 intersections**. Closest: F3 fuse-clip leads 1.27 mm (shelf edge), C333 / U3 / R129 on the top side 1.64 mm (above the ear/wall tops), J2 header leads 1.75 mm, R1/J3 wire stubs 2.02 mm |
| frame vs PCB body | 0 volume. 0.08 mm = the missing copper + mask, i.e. physical contact at the 9 boss tops and 26 rib tops only |
| support ribs vs B.Cu pads (2D) | min 1.32 mm (J3.1) ≥ 1.0 ✓. Bosses vs pads min 4.46 mm (J2.1) |
| tail loops vs frame | TFT 1.557 mm, CTP 1.554 mm (≥ 1.5 ✓). Fingers 3.4 / 4.5 mm. 0 volume |
| panel vs frame | 0 volume. Min 0.15 mm (the panel's square corners in the R 0.5 pocket corners); sides 0.25 mm |
| Formex sheet | touches the shelf (0 volume); panel on the sheet |
| gasket vs frame | 0.61 mm (gasket inside the pocket) |
| oven-sheet patch vs frame | 0 volume (coplanar contact in the feet plane) |
| lead protrusions vs the Formex sheet (Z −4.6) | PS1 3.27 → **1.33 mm**; HS1 pins 2.87 → 1.73; Q1 (leads trimmed to 2.5; 8.12 untrimmed) → 2.10; L40/L1/F1/F3/J20/C40 1.86 → 2.73; K1 2.83; U1/U5 2.93; rest ≥ 3.2 |
| mains copper → frame contact → panel metal | closest mains copper to a frame contact 1.32 mm (J3.1, LINE). Creepage path (PCB surface + rib side + shelf back + shelf inner face + shelf/sheet interface) **8.52 mm ≥ 6.4** ✓. Air clearance around the shelf corner + interface **6.70 mm ≥ 4.0** ✓ |
| sliver faces | 0 of 342 |

Tolerance notes:
- **Pocket vs panel:** the pocket is 165.40 ± 0.1 and the LCM is 164.90 ± 0.3, so the clearance per side ranges from 0.05 to 0.35 mm. Interference is not possible.
- **Gasket:** RSS of the LCM ± 0.3, the CTP stack ± 0.1, the frame seat ± 0.1 and the sheet ± 0.05 is ± 0.34 mm. That moves the 1.0 mm gasket between **0 % and 64 %** compression (open question 1).

## 7. Moulding notes

- **Tool:** single-cavity, 2-plate, no slides or lifters.
- **Parting line:** in the feet plane (Z −11.02), on the outer perimeter and around the feet pads.
  - Fixed half (A): the flat front face, plus a core block that forms the panel pocket up to the shelf (Z −4.6). The window and the tail pocket are shut-offs against the moving half.
  - Moving half (B): the back. Bosses, ribs, cells, foot tubes, tail-pocket walls and the open space above the shelf. The part shrinks onto the B cores and stays on the moving half.
- **Gates:** 4 tunnel / sub-gates (or hot-runner valve gates) on the B side, into the outer-wall tops (Z 0 faces). Suggested positions:
  - mid-left and mid-right (abs y ≈ 69);
  - top at abs x ≈ 62 and 145;
  - so that the weld lines fall between bosses, not on them.
  - Run a fill / warp simulation (Moldflow or equivalent) before the steel is cut: PA-GF rings are prone to warp. Put the weld lines on the long straight walls away from H1–H9 and F1–F8.
- **Ejectors (B side, on non-visible faces):**
  - sleeve ejectors around the 9 pilot core pins (boss tops);
  - Ø 2 pins on the outer-wall tops about every 40 mm;
  - pins on the 8 foot-tube tops, the corner-cell floor backs and the tail-pocket wall tops.
  - No ejector marks on the front face (it is the sealing face).
- **Shrinkage:** PA6-GF30 0.3 % flow / 0.5 % transverse.
  - Scale the tool per the gating direction.
  - Hold the pocket at 165.40 / 100.50 ± 0.1 and the boss positions ± 0.1. Check the boss pattern against the PCB ears on the first shots: pitch 174.6 × 109.6 mm.
- **Flatness:** feet plane ≤ 0.3 mm over the part, measured unclamped. It sets the gasket compression.
- **General tolerance:** ISO 20457 TG5.
- **Marking:** material code `>PA6-GF30 FR<` and the cavity number on the back of a cell floor.
- **Assembly order:**
  1. Panel glass-down on a soft fixture.
  2. Formex sheet on the panel back.
  3. Frame over it.
  4. PCB onto the bosses; 9 screws at 0.3–0.4 Nm.
  5. Fold the tails into J10 / J11 with the loops left slack in the pocket.
  6. Mount on the oven sheet over the studs (the gasket is already on the sheet); 8 nuts at 0.6 Nm.

  Before mounting, the panel is held only by the PCB/sheet stack. For handling, use two strips of double-sided tape (e.g. 3M 9088) on the shelf, or a PSA-backed Formex sheet.

## 8. Open questions for the owner

1. **Gasket thickness.**
   - With the LCM's ± 0.3 mm thickness tolerance, a 1.0 mm gasket can end up at 0 % (no seal) or 64 % compression.
   - Proposal: a **1.5 mm** gasket at 30 % (0.45 mm). That needs `GASKET_T = 1.5`, which moves the feet plane 0.35 mm forward.
   - Alternative: measure real panels and keep 1.0 mm.
2. **Insulation between the mains leads and the panel's metal back.**
   - "0.4 mm Formex GK-10" is inconsistent: GK-10 is 0.25 mm and **GK-17 is 0.43 mm**.
   - The air gap from PS1's AC pins to the sheet is only 1.33 mm. The sheet is therefore the insulation that counts.
   - If the LCM frame is SELV-connected or accessible, IEC 60335-1 cl. 29.3 needs reinforced insulation. A thin sheet counts as reinforced only as ≥ 3 layers that each pass the electric-strength test (e.g. 3 × 0.13 mm), or ≥ 2 mm solid.
   - Decide the grade and the layer count. The pocket takes 0.4 mm as modelled.
3. **Eight feet instead of six** (stiffness, §1.4). OK? If six are required, the wall must grow to about 3.5 mm or a back rib must be added along the top side.
4. **Locating pegs** need two Ø 3.2 holes in the sheet, visible from the front unless the decor film covers them. Keep them or set `PEGS = False`?
5. **Stud type:** PEM FH-M4-15 (sheet ≥ 1.0 mm steel; FHS for stainless) or weld studs? Also, what is the final sheet thickness?
6. **Q1 lead trimming** to ≤ 2.5 mm becomes a mandatory assembly step (8.12 mm untrimmed would hit the sheet). Add it to the assembly instructions and the PCBA order notes?
7. **Tail handling:** the loops are slack in an open pocket; there is no mandrel. Accept the "do not tug, leave slack" instruction, or shorten the tails (custom FPC length) in a later panel order?
8. **Material grade:** confirm Durethan BKV30FN04 (or the supplier's equivalent) on its datasheet / UL card. Check GWIT 775 °C at 2.5 mm and RTI.
9. **Boss/rib root fillets (R 0.5):** to be added in the tooling CAD by the toolmaker, or should the CadQuery model carry them? The latter needs a fillet pass on the final body.

## 9. Files

`Mechanical/Rev3.0_Frame/`:
- `Rev3.0_Frame.step` and `.stl`.
- `Rev3.0_Assembly.step`: board with all models + panel + frame + Formex sheet + compressed gasket. It is in KiCad export coordinates; the frame is shifted −0.08 mm.
- `Rev3.0_Frame_Drawing.png`: main dimensions, hole table, Z stack.
- `Rev3.0_FrontSheet_Pattern.dxf`: window, stud and peg holes, front view.
- Renders: `Frame_iso_front`, `Frame_iso_back`, `Frame_front`, `Frame_back`, `Assembly_iso_front`, `Assembly_iso_back`, `Assembly_front`, `Assembly_back`, `Assembly_side` (.png).
- Sections:
  - `Section_A_ear_bosses_x30` (through H1 and H7);
  - `Section_B_tail_pocket_x125`;
  - `Section_C_gasket_feet_plane` (plan section at Z −10.67);
  - `Section_D_foot_F2_x72.7` (.png).
