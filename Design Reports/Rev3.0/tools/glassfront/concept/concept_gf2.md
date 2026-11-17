# Rev3.0 glass front, revision GF-2.0 - concept study: equal borders, FPC tails bent back (2026-11-16)

Status: **concept study with proposed frozen numbers, no CAD.** Base: GF-1.1 (master `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json`,
not edited). Every number below comes from `concept_gf2_calc.py` (run log `concept_gf2_calc_out.txt`) or from the models measured by
`concept_gf2_measure.py` (`concept_gf2_measured.json`, `concept_gf2_measure_out.txt`). Proposed values: `concept_gf2_params.json`.

Coordinates as the master: X = KiCad abs x, y = KiCad abs y (down), Z = 0 at the PCB back, -Z towards the front. Glass 3.0 unless stated.

Tags: **[M]** measured from a model in the repo, **[C]** calculated, **[A]** my assumption, **[E]** estimated in the panel model (read off the
drawing by scale), **[G]** GF-1.1 master value, **[DS]** datasheet.

---

## 0. Answer in ten lines

1. **Border 14.0 is not sound.** At the bottom the panel itself takes 9.51 (print window edge -> panel edge), the bend gap takes 3.00, so
   1.49 is left for the land. A sealed bead needs 5.9 (0.9 + 4.0 + 1.0). Even a 3.0 bead would need a negative bend gap. [C]
2. **Recommendation: border 18.5 on all four sides**, with the full GF-1.1 bead (4.0 x 1.0, margins 0.9 / 1.09) along the bottom too. It is
   the smallest 0.5 step that keeps the GF-1.1 bead and margins (18.41 needed). Glass 190.48 x 122.32 (GF-1.1 181.48 x 143.83). [C]
3. Alternative if the owner wants 1 mm less: **17.5 with a 3.0 bead along the bottom only** (area -12 %, same thickness, a different bead
   size on one side). 16.5 / 17.0 give 2.1 / 2.6 beads (marginal), 14.0-16.0 give none worth having. [C]
4. **Tail route**: 0.5 straight beyond the panel edge, 90 deg bend back (inner R1.5), straight up, 90 deg bend R1.5 over the bridge's
   R1.5 nose, front legs at Z -5.10 behind the bridge, U-loops R3.75 (TFT) / R3.65 (CTP), return legs into J10/J11 unchanged. The loops hang
   where they hang now (TFT 145.83, CTP 136.70 outer), inside the unchanged tail pocket (bottom face 147.7). [C]
5. Clearance tail -> bridge 1.51 (TFT) / 0.93 (CTP) nominal, >= 0.60 with the panel edge 0.35 towards the bridge, 0.46 if the panel needs a
   1.0 straight; to the pocket bottom 1.87 / 1.62 at tail length +0.5. Exit heights +-0.3 change it by < 0.2. [C]
6. **Bridge**: land plate + step wall + flange plate + the frame's bottom wall form a channel (I 2160 mm4 vs 1222 of the GF-1.1 ring; 124
   without the bottom wall). **S4/R4, glass 3.0: bottom edge mid 0.062 mm at 50 N (0.075 in the bridge-only bound), glass 29 MPa at
   250 N (82 in that bound)**; GF-1.1: 0.067 / 39. Equal or better than GF-1.1 at every load point and glass thickness. [C]
7. **S8 cannot keep F7**: the bottom fastener line runs through the tail pocket. Dropping F7 gives 0.50 mm at 50 N and 164 um gasket lift at
   the bottom edge (GF-1.1 S8 0.127 / 39 um). The best buildable fix (divider rib between the tails + F7 on a flange tab) gives 0.20 mm / 70 um.
   **S8 is not recommended at GF-2.0**; S4 stays the recommendation, R4 the visible-rivet alternative. [C]
8. A **divider rib between the tails** (x 79.92, 2.5 thick, 2.85 clear of each tail) is the only possible mid support. Not needed for S4
   strength (0.062 -> 0.057); recommended for all variants for moulding (feeds and holds the 128.8 mm bridge) and it carries the S8 option.
9. Flange: glass + 21 on top and sides, bottom edge at the frame's bottom wall y 150.20 (only 1.21 below glass + 21). Overall 232.48 x 165.53
   (GF-1.1 223.48 x 185.83). F1-F4 symmetric about the glass (R4 heads at u +-106.24, v +-72.16); all fastener rules pass. [C]
10. **Gate before the tool is cut**: one real panel - measure the free straight at the exit, the tail thickness in the bend zone and the exit
    heights, and fold both tails over a 3.0 mm gauge block. 18.5 holds while the bend gap stays <= 3.09. [A]

---

## 1. What is measured, what is estimated

| item | value | source |
|---|---|---|
| panel outline | x 20.02-184.92, y 19.00-119.00 | [M] DS1 STEP in the board export; [G] |
| print window | x 27.11-180.59, y 24.17-109.49 | [G] |
| bottom bezel (window edge -> panel edge) | **9.51** (top 5.17, abs left 7.09, abs right 4.33) | [C] |
| PCB bottom edge between the ears | y 119.000 at x 45 / 60 / 103.85 / 140 / 160 | [M] board STEP |
| PCB back-side parts near the tails | none (only J20, x 21.9-30.6, y 97.5-107.6, reaches Z -1.87) | [M] |
| J10 / J11 bodies | x 142.85-168.45 / 55.52-64.52, entry faces y 114.875 / 114.45, Z 1.635-3.635 / 1.635-2.835 (top side) | [M] |
| TFT tail exit | x 84.02-122.62 (38.60 wide) at the panel edge; widens to x 165.90 from 7 mm out (L shape) | [M] width, [E] outline |
| CTP tail exit | x 40.72-75.82 (35.10 wide) | [M] |
| gap between the tails | 8.20 (x 75.82-84.02) | [M] |
| exit heights (centre) | TFT Z -8.40, CTP Z -9.70 | [E] (2.6 / 3.9 above the panel back) |
| tail thickness | 0.30 | [E] CTP drawing 0.3 +-0.05 (ZIF finger thickness); used for both |
| developed lengths | TFT 67.65, CTP 50.0 +-0.5 | [DS] |
| return legs | Z +2.40 (TFT) / +2.20 (CTP) = PCB top 1.6 + entry height 0.8 / 0.6 | [E] |
| tail ends in J10 / J11 | y 110.875 / 111.45 (insertion 4.0 / 3.0) | [E] panel model |
| GF-1.1 shelf end over the tail span | y 118.97 (Z -4.6 .. -2.1) | [M] frame STEP |
| GF-1.1 tail-pocket bottom face / bottom wall | y 147.707 / outer face 150.07-150.2 (1 deg) | [M] |
| stiffeners | CTP: steel stiffener on the finger end (back) only; none known near either exit | [DS] via the spec notes; TFT unknown |

**Length model check [C vs M].** The semicircle model of the panel script reproduces the DS1 STEP exactly at the v2 stand-off: loop bottom
146.059 (TFT) and 137.207 (CTP), difference 0.000. The same model gives the GF-1.1 loops (panel back -5.80): TFT 145.83, CTP 136.98 (outer
surface).

**Note on the tooling.** `concept_calc.py` is not imported: importing it re-runs it and rewrites the GF-1.1 master with GF-1.0 values. Its
grillage, ring-section, impact and fastener-rule code is copied into `concept_gf2_calc.py` and reproduces `concept_calc_out.txt` to 0.001 mm
at every load point (asserted in the script, sec. 5.0).

---

## 2. Tail route

### 2.1 Bend assumptions (to confirm on a real panel)

| parameter | value | why |
|---|---|---|
| straight beyond the panel edge face before the first bend (`tail_straight_l0`) | **0.5** [A] | keeps the bend off the glass edge / bezel edge at the exit and off the bond. Typical panel practice; the SAT drawing gives no number |
| minimum inner bend radius (`tail_R_in_min`) | **1.5** [A] (centre line 1.65) | IPC-2223 static ("bend to install") single-sided flex: >= 6 x total thickness (some sources 3-6 x; double-sided 12 x). The 0.30 in the model is the ZIF finger thickness with stiffener; the bending body of a single-sided display FPC is typically 0.10-0.15 [A]. R1.5 = 10-15 x that and 5 x the conservative 0.30. The Fannal CTP spec qualifies the tail for "tail bending 90 deg, 10 times left & right" and "tail peeling 500 g/cm at 90 deg" [DS] |
| bridge nose radius (`bend_nose_R`) | **1.5** | the only frame edge a taut tail can wrap; R1.5 + t/2 = 1.65 = the design centre-line radius, so a pulled tail is never bent tighter |
| clearance tail surface -> bridge pocket face | 0.45 worst case [A] | contact is harmless (smooth face); the clearance keeps the tail free while the frame is lowered in J2 |
| panel edge position towards the bridge | 0.25 RSS (0.35 WC) [A] | AA -> outline 0.2 (concept sec. 9), J1 alignment 0.1, J2 centring 0.05 |

**Bend gap** g_bend = 0.5 + 1.5 + 0.30 + 0.45 + 0.25 = **3.00** -> bridge pocket face at y **122.00** over the tail span (x 38.9-167.7).
If the tail is double-sided (0.30 body, 12 x -> R3.6) the gap would be 5.1 and the border 20.5. That is why the real-panel check comes first.

### 2.2 The route (nominal, both tails) [C]

Seen in the y-Z plane (figures `concept_gf2_section_bottom.png`, `concept_gf2_bend_zoom.png`):

| segment | TFT | CTP |
|---|---|---|
| exit at the panel edge | y 119.00, Z -8.40 | y 119.00, Z -9.70 |
| straight | 0.5 (to y 119.50) | 0.5 |
| bend 1, back (+Z) | 90 deg, centre line R1.65, ends at y 121.15 | same |
| vertical straight | 0.00 | 1.30 |
| bend 2, out (+y), over the nose | 90 deg, R1.65, ends at y 122.80, Z -5.10 | same |
| S-bend on the tail | v 0.5-5.68 (inside the 0-7 bonded-width part) | v 0.5-6.98 (inside the 0-9.5 first segment) |
| front leg at Z -5.10 | 19.13 long, to y 141.93 | 10.10, to y 132.90 |
| U-loop | R 3.75 (GF-1.1 5.40), on tail v 24.8-36.6 | R 3.65 (GF-1.1 5.95), v 17.1-28.6 |
| loop bottom, outer surface | **145.83** (GF-1.1 145.83) | **136.70** (GF-1.1 136.98) |
| return leg | Z +2.40 over the PCB edge into J10 (unchanged) | Z +2.20 into J11 (unchanged) |

The front legs sit at Z_TAIL_LEG = Z_TAIL_TFT_EXIT + 2 x 1.65 = -5.10 at every glass thickness. No frame feature depends on it; it is the
design path for the clearance checks. The excess length still hangs as a U-loop in the existing tail pocket and folds over the PCB bottom
edge into J10/J11 as before.

### 2.3 Clearances [C] (`concept_gf2_calc_out.txt` sec. 2)

| | TFT | CTP |
|---|---|---|
| to the frame (bridge nose / pocket face / floor / bottom wall), glass 1.1 / 2.0 / 3.0 / 4.0 | 1.51 (all) | 0.93 (all) |
| to the glass back (at the exit) | 2.87 | 1.57 |
| to the panel edge face above the exit / its back corner | >= 0.45 at the exit itself (the tail leaves there), >= 1.6 further up | same |
| to the Formex / shelf end | 2.84 / 2.59 | 2.84 / 2.59 |
| to the PCB (return leg over the edge, unchanged by design) | 0.65 | 0.45 |
| to the tail-pocket side walls (x) | 1.80 | 1.82 |
| loop bottom to the pocket bottom face 147.7 | 1.87 | 11.00 |
| TFT loop corner to the R1.5 pocket corner (plan) | 1.84 | - |
| front leg to the tail-pocket floor | 2.67 at glass 1.1 (floor -7.92), more at 2.0-4.0 | same |

Tolerance cases (glass 3.0): panel edge +0.25 -> 1.30 / 0.69; +0.35 -> 1.22 / 0.60; exit Z +0.3 -> 1.68 / 1.03; exit Z -0.3 -> 1.35 / 0.84
(CTP to the glass back 1.27); straight 1.0 instead of 0.5 -> 1.10 / **0.46**; R_in 1.8 -> 1.38 / 0.73; tail length +0.5 -> TFT loop 1.62 above
the pocket bottom. All positive. The route is insensitive to the estimated exit heights: the bend gap depends on the straight, the radius and
the thickness, not on Z.

### 2.4 What must be confirmed on a real panel

1. Where the FPC is free at each exit: bezel / frame edge, any UV glue or silicone bead, coverlay end -> the straight `l0` (assumed 0.5).
2. Tail body thickness and layer count in the bend zone (assumed <= 0.30 single-sided -> R_in 1.5).
3. Exit heights (estimated -8.40 / -9.70) and that bending **back towards the LCM** at the exit is allowed by the maker (it is the usual fold
   direction for these panels; not stated for this one).
4. Components or stiffeners on the TFT tail's L-shaped wide part (v 7-31). The U-loop bends there, as it already does in GF-1.1.
5. The panel's bottom edge position relative to the AA (assumed +-0.2).
6. Test: fold both tails over a 3.0 mm gauge block held against the panel edge (with an R1.5 edge), unforced; the tail surface must stay within
   2.55 of the edge face. Then the full fit in a printed GF-2.0 frame with display and touch running.

---

## 3. Bottom-edge section and the border budget

### 3.1 The section over the tail span (x 38.9-167.7), border 18.5, glass 3.0

| feature | y (abs) | Z |
|---|---|---|
| panel edge (CTP + LCM) | 119.00 | -11.12 .. -5.80 |
| **bend-gap slot**, open front-to-back, closed at the front by the glass | 119.00-122.00 | from the glass back up, opens into the tail pocket |
| **bridge pocket face** (land-plate inner face) | 122.00 | Z_LAND -10.42 .. -9.42 flat, then the **R1.5 nose** to y 123.50 at Z -7.92 |
| land (recess floor) | 122.00-128.39 | -10.42 (land plate -10.42 .. -7.92) |
| bead 4.0 x 1.0 | 123.09-127.09 (0.9-4.9 inside the glass edge) | -11.42 .. -10.42 |
| glass edge / recess wall (lip inner face) | 127.99 / 128.39 | glass -14.42 .. -11.42 |
| lip, seat ring | 128.39-129.39, 129.39-130.89 | as GF-1.1 |
| sheet cut-out edge | 129.79 | sheet -14.42 .. -13.42 |
| step wall | 128.39-130.89 | -13.42 .. -7.92 |
| VHB strip (S4/R4) | 131.89-143.89 | -13.42 .. -12.42 |
| **flange plate = tail-pocket floor** | 130.89-147.70 | -12.42 .. -9.92 (glass 1.1: back snaps to -7.92) |
| bottom wall (tail-pocket bottom face 147.70) = frame bottom outer wall = flange edge | 147.70-150.20 | -12.42 .. +4.05 |

Border budget at the bottom: bezel 9.51 + bend gap 3.00 + land 5.99 = **18.50**. Outside the tail span the pocket face stays at y 119.8 (land
8.19).

### 3.2 What fits at each border [C]

Bottom land = border - 9.51 - 3.00; widest bottom bead = land - 0.9 - 1.0 (GF-1.1 margins). Bead area scaled to the modelled 2486.7.

| border | bottom land | widest bottom bead | bead area (4.0 elsewhere) | vs 2486.7 | glass | verdict |
|---|---|---|---|---|---|---|
| **14.0** | 1.49 | **-0.41** | 1548 | -38 % | 181.48 x 113.32 | **impossible: no bead fits** |
| 15.0 | 2.49 | 0.59 | 1676 | -33 % | 183.48 x 115.32 | not sound |
| 16.0 | 3.49 | 1.59 | 1879 | -24 % | 185.48 x 117.32 | not sound |
| 16.5 | 3.99 | 2.09 | 1982 | -20 % | 186.48 x 118.32 | marginal |
| 17.0 | 4.49 | 2.59 | 2086 | -16 % | 187.48 x 119.32 | marginal |
| **17.5** | 4.99 | 3.09 -> **3.0 bead** | 2191 | -12 % | 188.48 x 120.32 | sound with a narrower bottom bead |
| 18.0 | 5.49 | 3.59 | 2297 | -8 % | 189.48 x 121.32 | sound with a narrower bottom bead |
| **18.5** | 5.99 | 4.09 -> **4.0 bead** | 2387 | -4 % | 190.48 x 122.32 | **full GF-1.1 bead and margins** |

(The -4 % at 18.5 is the smaller glass perimeter, not a narrower bead.)

**Why 14.0 cannot be rescued.**
- Even with an aggressive bend (straight 0.3, R_in 1.0, no clearance, g_bend 1.6) the land is 2.89: a 1.0 bead with margins.
- A sealed 3.0 bead at 14.0 would need a bend gap of -0.41, i.e. the tail bent inside the panel. Not physical.
- Ideas checked and rejected: a thin plate in front of the tails (the CTP tail is 0.57 behind the land plane; concept option iii was already
  rejected at 0.3 clearance); potting the tail exits in the bead silicone (bonds the panel edge and the FPC roots into the seal, no rework,
  stresses the bonds over temperature, untested); no bottom bead (concept option i: unsealed into the tail pocket, 0.35 mm at 50 N).

**The 17.5 option (narrow bottom bead).** Bottom bead 3.0 wide, margins 0.9 to the glass edge and 1.09 to the pocket face.
- Retention: bead area about 2191 mm2 (-12 %), 250 N pull 0.114 MPa mean (GF-1.1 0.100). Fine.
- Shear movement: the capability depends on the bead thickness (1.0, unchanged), not the width. The bottom corners see the same 0.224 / 0.333
  mm as the other corners. Fine.
- Seal: continuous. Fine.
- Dispensing: the bottom side needs 75 % of the bead volume. That is a second nozzle size or a faster path on one side (robot), with
  transitions at the two bottom corners. That is the only real cost.
- I would take it only if the owner values the 1 mm.

**Recommendation: 18.5.** Same bead, margins, nozzle and J2 process as GF-1.1, all four sides equal. Its reserve is small (largest bend gap
that still fits: 3.09), so it is gated by the real-panel check of sec. 2.4. If the panel needs more than 3.09, go to 19.0, not to a thinner
bead.

---

## 4. Bridge strength and stiffness

Method: the concept grillage, ported and checked against `concept_calc_out.txt` (sec. 5.0 of the log). Glass strips on a frame ring,
panel / LOCA / PCB stiffness not counted, frame E 3500, VHB E 1 MPa. GF-2.0 change: one ring section per edge.

### 4.1 Ring sections (glass 3.0) [C]

| edge | I (mm4) | note |
|---|---|---|
| top / abs left / abs right | 1232 / 1229 / 1233 | as GF-1.1 (1222) with the wider land plates |
| bottom, bridge only | **124** | lip + step wall + flange + land plate; the bend gap cuts the pocket wall and the shelf |
| bottom, channel | **2160** | + flange plate to the bottom wall + bottom wall (Z -12.42 .. +4.05). Glass 1.1 / 2.0 / 4.0: 1580 / 1831 / 2545 |

The bottom wall is the backbone of the bridge. The channel is an open section; the truth lies between the two bounds, close to the
channel because the flange plate ties both webs along their full length. Both bounds are reported.

### 4.2 Push results, glass 3.0 [C]

| 50 N (mm) / 250 N glass (MPa) | window centre | top mid | side mid | bottom border over the bend gap | **bottom edge mid** | bottom edge over the CTP tail |
|---|---|---|---|---|---|---|
| GF-1.1 S4 (concept) | 0.139 / 64 | 0.067 / 39 | 0.066 / 40 | (chin 0.092 / 57) | 0.067 / 39 | - |
| **GF-2.0 S4/R4, channel** | **0.122 / 63** | 0.066 / 39 | 0.065 / 42 | 0.069 / 50 | **0.062 / 29** | 0.058 / 31 |
| GF-2.0 S4/R4, bridge only | 0.124 / 63 | 0.066 / 39 | 0.065 / 41 | 0.077 / 56 | 0.075 / 82 | 0.074 / 85 |
| GF-2.0 S4/R4 + divider rib | 0.122 / 63 | 0.066 | 0.065 | 0.066 | 0.057 / 29 | 0.053 |
| GF-1.1 S8 (concept, F7 on the line) | 0.193 / 66 | 0.127 | 0.113 | - | 0.127 / 47 | - |
| GF-2.0 S8, F7 dropped (7 studs) | 0.258 / 68 | 0.131 | 0.105 | 0.428 / 83 | **0.497 / 79** | 0.349 |
| GF-2.0 S8, F7 on a tab below the bottom wall (x 103.85) | 0.245 | 0.131 | 0.104 | 0.367 | 0.414 / 67 | 0.303 |
| GF-2.0 S8, F7a/F7b beside the tail pocket (9 studs) | 0.198 | 0.129 | 0.100 | 0.229 | 0.258 / 62 | 0.165 |
| GF-2.0 S8, divider rib + F7' at the rib | 0.211 | 0.131 | 0.102 | 0.205 | **0.203 / 172*** | 0.142 |
| GF-2.0 S8, F7 on the line (bound, not buildable) | 0.176 | 0.128 | 0.100 | 0.132 | 0.124 / 46 | 0.141 |
| GF-2.0 4 studs only (reference) | 0.427 | 0.627 | 0.297 | 0.486 | 0.541 / 82 | 0.386 |

\* hard point support at the rib in a model without bead compliance: a local peak that the soft bead will spread. Needs FEA before it is
believed or dismissed.

Other glass thicknesses, S4/R4 (channel), bottom edge mid at 50 N: 1.1 **0.112** (GF-1.1 0.128), 2.0 **0.077** (0.086), 4.0 **0.052**
(0.054). Glass at 250 N, worst point: 1.1 412 MPa at the window centre (no panel credit, as GF-1.1's 420), 303 MPa over the bend gap (GF-1.1
chin 361); 2.0 137; 4.0 37.

**Against the criteria.** S4/R4: every load point at every glass thickness is equal to or better than GF-1.1; the bottom edge moves 0.062 at
50 N (limit 0.15 = the flushness inspection limit); glass SF at 250 N >= 1.9 on 120 MPa at 3.0 (1.5 in the bridge-only bound at the bottom
edge). **The VHB strip along the bottom makes the bridge stiffness almost irrelevant for S4/R4.** No extra tape and no extra fastener are
needed at the bottom.

**S8 fails at the bottom edge in every buildable form** (0.20-0.50 mm at 50 N against 0.127 in GF-1.1 and the 0.15 limit). Foam gasket lift
at 0.10 N/mm (glass 3.0 / 1.1): F7 dropped 164 / 457 um; tab 133 / 306; F7a/F7b 68 / 129; rib + F7' 70 / 233; GF-1.1 39 / 73.

### 4.3 Mid support between the tails

- A tooth across the bend gap (x 77.32-82.52) would tie the bridge to the shelf end, which over the tail span is a 2.6 x 2.5 strip. It adds
  nothing. Not proposed.
- A **divider rib in the tail pocket** at x 79.92 (2.5 thick, y 122.0-147.7, floor -> Z 0 for y < 129, -> +4.05 beyond; 2.85 clear of the
  CTP edge 75.82 and the TFT edge 84.02 all along both tails) ties the bridge to the bottom wall in the middle.
  - S4/R4 strength: **not needed** (0.062 -> 0.057).
  - Moulding: recommended. It feeds the 128.8 bridge from the body and holds the free inner edge of the land plate flat (the bond line).
  - S8: it is what makes the best S8 option (F7' on a tab at the rib) possible.
  - Assembly: each tail folds into its own compartment.

---

## 5. Everything that follows from the new glass (border 18.5)

### 5.1 Plan [C]

| item | x | y | size | R |
|---|---|---|---|---|
| print window (unchanged) | 27.11-180.59 | 24.17-109.49 | 153.48 x 85.32 | 0.5 |
| **glass** | 8.61-199.09 | 5.67-127.99 | **190.48 x 122.32** | 6.25 (unchanged) |
| glass centre = cut-out = fastener-pattern centre | 103.85 | **66.83** (= window centre; GF-1.1 82.085) | | |
| lip inner (at the lip top) | 8.21-199.49 | 5.27-128.39 | 191.28 x 123.12 | 6.4 |
| lip outer (root) | 7.21-200.49 | 4.27-129.39 | 193.28 x 125.12 | 7.4 |
| seat ring outer | 5.71-201.99 | 2.77-130.89 | 196.28 x 128.12 | 8.9 |
| **sheet cut-out** | 6.81-200.89 | 3.87-129.79 | **194.08 x 125.92** | 7.55 |
| tape strips | s 3.9-15.9 | | top/bottom 192.48, sides 124.32, 7603 mm2 (7903) | straight |
| fastener lines | -2.39 / 103.85 / 210.09 | -5.33 / 66.83 / 138.99 | 212.48 x 144.32 | |
| **flange** | -12.39-220.09 | -15.33-**150.20** | **232.48 x 165.53** | 10; top corners on F1/F2, bottom corners centred 10 inside the corner |
| clearance pocket (unchanged) | 19.22-185.72 | 18.20-119.80 | | 0.5 |
| bend-gap slot (new) | 38.9-167.7 | 119.00-122.00 | 128.8 x 3.0 | |
| tail pocket (x, bottom unchanged) | 38.9-167.7 | 119.0-147.7 | | 1.5 |

Lands (pocket face -> glass edge) / bead to pocket face: abs left 10.61 / 5.71, abs right 13.37 / 8.47, top 12.53 / 7.63, **bottom over the
tail span 5.99 / 1.09**, bottom outside the tail span 8.19 / 3.29. The side and top land plates grow 4.5; the bead stays 0.9-4.9 inside the
glass edge everywhere. Lip, seat ring, cut-out and corner radii keep their GF-1.1 offsets.

**Flange below the cut-out.** The frame body's bottom wall (y 147.7-150.2) must stay to close the tail pocket, so the flange ends there: 20.41
below the cut-out edge against 19.20 on the other sides. Only 1.21 more than glass + 21. Extra tape: none (the strip below the bottom VHB
strip is 6.3 wide, and S4 does not need it). Extra fastener: none for S4/R4.

### 5.2 Fasteners [C] (rules as concept 4a)

| | x | y | slot axis deg | r | outline (>= 6.5) | ear hole (>= 11) | J20/J2 corridor | tails | boss gap | cut edge (>= 8) | tube to flange edge | |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | -2.39 | -5.33 | 34.19 | 128.4 | 33.32 | H1 37.82 | 32.0 | 131.0 | 24.8 | 16.14 | 1.00 | ok |
| F2 | 210.09 | -5.33 | 145.81 | 128.4 | 36.24 | H4 40.74 | 186.5 | 131.4 | 27.7 | 16.14 | 1.00 | ok |
| F3 | 210.09 | 138.99 | -145.81 | 128.4 | 31.71 | H5 36.21 | 181.1 | 42.4 | 23.2 | 16.14 | 1.00 | ok |
| F4 | -2.39 | 138.99 | -34.19 | 128.4 | 30.27 | H8 34.77 | 28.8 | 41.3 | 21.8 | 16.14 | 1.00 | ok |
| F5 | 103.85 | -5.33 | 90.00 | 72.2 | 17.84 | H2 22.34 | 83.9 | 124.3 | 9.3 | 9.20 | 1.00 | ok |
| F6 | 210.09 | 66.83 | 180.00 | 106.2 | 26.09 | H4 42.05 | 180.9 | 67.2 | 29.0 | 9.20 | 1.00 | ok |
| **F7** | 103.85 | 138.99 | -90.00 | 72.2 | 19.99 | H6 72.75 | 78.0 | **0.0** | 59.8 | 9.20 | 2.21 | **inside the tail pocket** |
| F8 | -2.39 | 66.83 | 0.00 | 106.2 | 22.39 | H9 40.81 | 19.8 | 66.5 | 27.8 | 9.20 | 1.00 | ok |

- F1-F4 in front view (u, v): (+-106.24, +-72.16), symmetric about the glass. R4 head edge 9.14 from the cut-out corner arc (unchanged).
- Stud radial thermal move at r 128.4: 0.244 / 0.372 mm (50 / 70 ppm) against 1.15 float. Slots, counterbores, pads, tubes, coring unchanged.
- **F7 (S8).** It sits 8.7 inside the tail pocket over the TFT loop. Options [C]:
  - drop it (7 studs): 0.50 mm / 164 um (no);
  - on a tab below the bottom wall at (103.85, 160.70): 0.41 / 133 um. The 2.5 flange plate across 33 mm is too soft (no);
  - two studs F7a/F7b at (28.40, 138.99) / (178.20, 138.99) in the corner cells: 0.26 / 68 um. The cells and their cross rib must be rebuilt
    and the tubes merge into the tail-pocket side walls;
  - **divider rib + F7' at (79.92, 160.70)** on a 20-wide flange tab (x 69.92-89.92, to y 170.70): 0.20 / 70 um, a local glass stress peak
    to be checked by FEA.
- **Proposal:** S4 (recommended) and R4 only. Withdraw S8 at GF-2.0, or keep it with the divider rib + F7' tab and accept ~0.2 mm at 50 N at
  the bottom edge. Decide before the tool: the tab and the F7' tube are mould features. Do not mould anything at the old F7 position.

### 5.3 Other consequences

| topic | GF-2.0 |
|---|---|
| print window | unchanged (aligned to the AA, J1 process unchanged) |
| pips P1-P8 | (56.23, 8.57), (56.23, 125.09), (151.47, 8.57), (151.47, 125.09), (11.51, 36.25), (196.19, 36.25), (11.51, 97.41), (196.19, 97.41); same rule (bead centre line, +-1/4 of each side); P2/P4 sit on the 5.99 bottom land |
| logo | the 100 x 20 zone is gone. In the 18.5 bottom border: centre (103.85, 118.74), <= 100 x 15 (>= 1.0 from the window, >= 2.5 from the glass edge, strokes >= 0.5). The bead and the bend gap behind it are hidden by the black print layer that follows the logo colour |
| J1 | glass stops S1-S3 move with the outline (glass 9 wider, 21.5 lower); the top plate opening (window + 3) is unchanged; check the plate size on GF-D31 |
| J2 | the 290 x 250 plate still fits the 232.48 x 165.53 flange; pins move to F1-F4 (212.48 x 144.32 pattern); glass stops move. **New:** bend both tails back at the edge and hold them vertical (+Z, a removable post with a clip or a Kapton tab) while the frame is lowered, so they pass the 3.0 bend-gap slot without touching the bead. Break the leading inner edge of the land (land x pocket face) 0.3 x 45 deg so it cannot snag a tail. After cure fold the tails over the R1.5 nose into their compartments, then PCB and connectors as before |
| bead / tape | bead 2387 mm2 (estimate, -4 %), dead load 1.54 kPa, 250 N pull 0.105 MPa; bead corner r 109.2 -> shear 0.224 / 0.333 mm (GF-1.1 0.229 / 0.341); tape 7603 mm2, shear 29 / 42 % |
| gaps over temperature | the glass is 9.0 wider: g2 cold -0.011, g1 hot -0.014 against GF-1.1 by the same formula. The design-doc worst cases at the 70 ppm bound become about -0.038 (g2, +-0.2 glass) and -0.032 (g1): a touch, harmless, as before |
| glass | 174 g (196); 0.5 J window centre SF 1.21 at 3.0 (GF-1.1 1.27: the lighter glass absorbs less in the mass-ratio estimate) |
| impact case | the GF-1.1 "chin over the tail pocket" (128.8 x 28.7 of glass with nothing behind) is gone. What replaces it: the 4.09-wide strip from the panel edge to the bead over the bend gap, locally ~49 x stiffer. 0.5 J SF at 3.0: 2.76 with the strip (concept method), 1.38 if the whole border is taken as free (conservative; GF-1.1 chin 1.39). Window centre (1.21) now governs. 1.1: 1.41 / 0.81 (1.1 stays marginal) |
| moulding | (1) the tail pocket gets a floor (the flange plate); its B-side core is 14 deep with 1 deg draft and ejectors on the floor (not the land). (2) The only through-opening at the bottom is the 3.0 x 128.8 bend-gap slot: shut-off >= 3 wide between the recess core (A) and the tail-pocket core (B). (3) Nose R1.5 on the B side; the slot faces 1 deg. (4) No undercut, no slide, no new thin wall (min. still the 1.0 lip). (5) No junction thicker than the existing step-wall / land-plate / flange junction; bottom wall on flange plate 2.5 / 2.5 + R0.5; the divider rib 2.5; F3/F4 tubes cored as now. Expect the max inscribed sphere to stay <= 4.6 (to verify). (6) The land along the bottom is an exclusion zone like the rest of the land. (7) Run fill/warp with the bridge: its inner edge carries the bond line over 128.8 mm |
| H6/H7 corner cells | plan unchanged; their front changes from the land plate to land plate + step wall + flange plate (the floor steps 2.0 at y 130.89 at glass 3.0, flat at 1.1); bosses H6/H7 stay on the land plate |
| mains creepage, Formex | **unchanged.** Nothing at Z >= -5.0 inside the board outline changes (shelf, ribs, bosses, Formex, pocket walls); the changes are below the board edge (SELV tails) and in the outer ring |
| levels | all Z levels unchanged (derived_levels.expressions) |
| size | visible module 194.08 x 125.92 (185.08 x 147.43); flange 232.48 x 165.53; depth unchanged (17.47 at glass 3.0). The module is 9.0 wider: check the oven's internal width |

---

## 6. Proposed numbers for GF-2.0 (the CAD agent edits the master; `concept_gf2_params.json` has the full list)

| name | GF-1.1 | GF-2.0 | reason |
|---|---|---|---|
| border | 14.0 (top/left/right) | **18.5 (all four)** | equal borders; smallest 0.5 step with the full bead (sec. 3) |
| glass_y1 | 154.0 (driving) | 127.99 (derived = print window y1 + border) | no chin |
| plan_rectangles.glass | 13.11, 194.59, 10.17, 154.00 | 8.61, 199.09, 5.67, 127.99 | 190.48 x 122.32 |
| lip_in / lip_out / seat_ring_out | 12.71-194.99 x 9.77-154.40 / 11.71-195.99 x 8.77-155.40 / 10.21-197.49 x 7.27-156.90 | 8.21-199.49 x 5.27-128.39 / 7.21-200.49 x 4.27-129.39 / 5.71-201.99 x 2.77-130.89 | same offsets |
| cut (sheet cut-out) | 11.31, 196.39, 8.37, 155.80 | **6.81, 200.89, 3.87, 129.79** (194.08 x 125.92) | same offset, R7.55 |
| tape_in / tape_out | 9.21-198.49 x 6.27-157.90 / -2.79-210.49 x -5.73-169.90 | 4.71-202.99 x 1.77-131.89 / -7.29-214.99 x -10.23-143.89 | same offsets |
| fastener_line | 2.11, 205.59, -0.83, 165.00 | -2.39, 210.09, -5.33, 138.99 | glass + 11 |
| plan_rectangles.flange | -7.89, 215.59, -10.83, 175.00 | -12.39, 220.09, -15.33, **150.20** | glass + 21; bottom = frame bottom wall |
| flange_y1_bottom | - | **150.20** (new) | tail-pocket bottom face 147.7 + wall 2.5 |
| glass_centre | 103.85, 82.085 | **103.85, 66.83** | = window centre |
| chin_border | 44.51 | removed | |
| lands (abs left / abs right / top / bottom) | 6.11 / 8.87 / 8.03 / 6.30 | 10.61 / 13.37 / 12.53 / **5.99** (tail span; 8.19 outside it) | |
| bead_to_pocket | 1.21 / 3.97 / 3.13 / 1.40 | 5.71 / 8.47 / 7.63 / **1.09** (3.29 outside the tail span) | >= 1.0 |
| g_bend | - | **3.00** (new) | 0.5 + 1.5 + 0.30 + 0.45 + 0.25 |
| bend_gap_y1 (bridge pocket face) | - | **122.00** (new), over x 38.9-167.7, Z_LAND to the back | |
| bend_nose_R | - | **1.5** (new) | |
| tail_R_in_min / tail_straight_l0 | - | 1.5 / 0.5 (new, assumptions to confirm) | |
| Z_TAIL_LEG | - | Z_TAIL_TFT_EXIT + 3.30 = -5.10 (new, nominal, no frame feature) | |
| Z_LOOP_FRONT | Z_TAIL_CTP_EXIT - 0.15 = -9.85 | same value, now only at the exit (bend gap); front legs at -5.25 | |
| tail_pocket | x 38.9-167.7, y 119.0-147.7, R1.5, no floor | same x, bottom face, R; **floor = bridge + flange plate**; open slot y 119.0-122.0 | |
| bottom wall | y 147.7-150.2 from the land (-10.42) to +4.05 | y 147.7-150.2 from Z_FLANGE_FRONT to +4.05 = outer wall, flush with the flange edge | |
| divider_rib | - | **x 79.92, t 2.5, y 122.0-147.7, floor -> Z 0 (y < 129) / +4.05** (new, recommended) | |
| F1-F6, F8 | see master | F1 (-2.39, -5.33), F2 (210.09, -5.33), F3 (210.09, 138.99), F4 (-2.39, 138.99), F5 (103.85, -5.33), F6 (210.09, 66.83), F8 (-2.39, 66.83) | |
| F7 | (103.85, 165.00), S8 | not moulded at (103.85, 138.99). S8 only: F7' (79.92, 160.70) on a tab x 69.92-89.92 to y 170.70 | sec. 5.2 |
| S8 variant | 8 studs + foam | **not recommended**; if kept: 8 studs with F7' + divider rib | sec. 4.2 |
| pips | see master | sec. 5.3 | |
| logo_zone | centre (103.85, 131.745), 100 x 20 | centre (103.85, 118.74), 100 x 15 | |
| tape strip lengths | 183.48 / 145.83 | 192.48 / 124.32 | |
| bead_area | 2486.7 | ~2387 (estimate; CAD to measure) | |

**Unchanged:** glass_t and its valid set; t_opt, t_bond, t_sheet, t_gap, g_bs; print_inset and the window; R_glass 6.25, R_frame 6.0, R_cut 7.55;
g1, g2, lip_w, seat_ring_w; pocket_clr 0.8 (outside the tail span); bead_w 4.0, bead_edge 0.9, bead_pocket_min 1.0; fast_off 11,
flange_beyond_glass 21 (top/sides), flange_R 10, flange_t 2.5; slot, counterbore, pad, tube, coring, pip size; every Z level; everything
at Z >= Z_FORMEX_FRONT.

**GF-1.1 values that become invalid:** plan_points.chin_border and the logo zone; lands, bead_area, tape area and strip lengths, pips; the
whole fasteners.positions table (d_* values) and F7; checks.push_50N_*, impact_0p5J_SF_chin (case gone) and impact_0p5J_SF_centre (glass
mass); the gap tables of design doc 7.4; as_modelled volume / mass / max inscribed sphere and the 84-pass verification; drawings GF-D01..D50;
cad_rules[8] ("no floor, the glass chin closes the front") and "F5-F8 tube + slot always moulded" (F7); the tail checks (1.83 / 1.763 to
the pocket, "tails vs glass print 1.565 / 2.865", the split tail model in fit_check.py - the tails are re-routed, the DS1 STEP still carries
the old route; use `tail_route.*.centreline_yZ` in the params file); J1/J2 stop and pin positions; the sheet front-view fastener table;
design doc sections 0.1, 0.2, 2.1, 2.2, 7.3, 7.8 (chin rows) and 8.6.

---

## 7. Open risks and tests

| # | risk | test / action |
|---|---|---|
| 1 | **Tail bend at the exit**: straight 0.5, R_in 1.5, thickness, exit heights are assumptions / estimates. 18.5 holds only while g_bend <= 3.09 | real panel: inspect the exits, measure the tail thickness, fold over a 3.0 gauge with R1.5 edge (sec. 2.4). Before the border is frozen |
| 2 | maker's permission to fold the TFT tail back at the exit; components on the TFT tail's wide part | ask SATOZ via Ozdisan; inspect the tail |
| 3 | threading the tails through the 3.0 slot in J2 without touching the fresh bead | J2 tail holder; trial on a printed frame |
| 4 | bead squeeze-out over the bridge's inner edge onto the tails (margin 1.09) | dispense volume per GF-D20; first-article check |
| 5 | bridge stiffness between the two bounds (S4: 0.062-0.075 mm); local glass peak in the S8 rib option | FEA of glass + frame + VHB with the bead modelled |
| 6 | flatness of the 128.8 mm land along the bottom (bond line 0.73-1.27) | fill/warp simulation; divider rib |
| 7 | S8 is worse at the bottom than GF-1.1 in every buildable form | owner decision: S4 / R4 only |
| 8 | 0.5 J impact: window centre SF 1.21 at 3.0 (was 1.27) | spring-hammer test as planned (window centre, bottom border over the bend gap, corner, edge) |
| 9 | module 9.0 mm wider (232.48 flange) | check the oven's internal width |
| 10 | g1 / g2 touch at the 70 ppm bounds slightly earlier (-0.011 / -0.014) | thermal cycling as planned |
| - | GF-1.1 risks unchanged: touch through the glass, adhesion and ageing, coating step, stud flash, material rating | as the design document |

---

## 8. Corrections to the brief

1. "A 5 mm gap between the two tails around x 77-82": the gap between the tail exits is **8.20** (x 75.82-84.02); 5.20 (x 77.32-82.52) is what
   is left with 1.5 clearance each side.
2. "Tails leave the bottom edge face at x about 39-167": the tails leave at x 40.72-75.82 (CTP) and **84.02-122.62** (TFT). The TFT tail only
   widens to x 165.9 from 7 mm out. 38.9-167.7 is the tail pocket.
3. "The flange will extend further below the cut-out than elsewhere": at 18.5 only 1.21 more (20.41 vs 19.20). At 14.0 it would be 5.71.
4. "Reuse concept_calc.py functions": importing it executes the script and overwrites the GF-1.1 master with GF-1.0 values. I copied the code.
5. A "mid support between the tails" across the bend gap has nothing stiff to tie to (the shelf end is a 2.6 x 2.5 strip there). The useful
   mid support is the divider rib behind the bridge, between the bridge and the bottom wall.
6. The border budget is dominated by the panel: the bottom bezel alone is 9.51 (other sides 4.3-7.1). That is why 14.0 cannot work.

---

## 9. Files (all in this folder, new)

- `concept_gf2.md` - this study.
- `concept_gf2_measure.py` -> `concept_gf2_measured.json`, `concept_gf2_measure_out.txt` - measurements of the GF-1.1 frame STEP, the board STEP
  (kicad-cli export of the GF-1.1 verification, `%TEMP%\gf_verify\board_full.step`) and board_geom.json. Run with the CadQuery venv, `python -B`.
- `concept_gf2_calc.py` -> `concept_gf2_calc_out.txt`, `concept_gf2_params.json`, `concept_gf2_section_bottom.png` (bottom section with
  both routes, GF-1.1 routes dotted), `concept_gf2_bend_zoom.png` (bend gap + border-budget chart), `concept_gf2_plan_bottom.png` (plan of
  the bottom zone). Needs numpy + matplotlib, `python -B`.
- Nothing outside this folder was written. No git commit.
