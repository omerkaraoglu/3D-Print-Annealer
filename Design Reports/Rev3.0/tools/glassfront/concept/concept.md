# Rev3.0 OVEN CONTROLLER - glass-front display, concept study (2026-11-15)

Status: **concept study, no CAD.** Purpose: let the lead brief CAD agents. Every number is traceable to
`concept_calc.py` (plain Python, run log `concept_calc_out.txt`) and to the frame v2 documents. Every dimension of
the recommended concept is in `concept_params.json` (name / value / unit / group / note).

Frame v2 (`Mechanical/Rev3.0_Frame/`, `Design Reports/Rev3.0/Rev3.0_Frame_Design.md`) is not touched. This is a new
part family ("glassfront"). The PCB and the SAT070AT40D21 panel are unchanged.

Conventions as v2 §1: X = KiCad abs x, y = KiCad abs y (down), Z = 0 at the physical PCB back, −Z towards the front.
Front view (what the user sees) mirrors X: u = −(x − 103.85), v = 82.085 − y, origin = glass centre.
"v2 §n" = `Rev3.0_Frame_Design.md` section; `key` = key in `Rev3.0_Frame_v2_params.json`; DS = panel datasheet as
transcribed in `tools/models3d/tft7_sat070at40d21.py` (LCM sheet 16, Fannal CT0476; CTP spec checked in the PDF text:
"G+G", VA 155.08 × 86.92, outline 164.9 × 100 × 1.58 glass stack, 1.98 with the 0.4 PU tape, CTP −20…70 °C).

---

## 0. Recommendation in ten lines

> **Revision GF-1.0 (lead amendments A1–A8, 2026-11-15).** The lead accepted option A with chin. The numbers in §0–§5
> are updated to the frozen values; §11 lists every amendment, the full level table for glass 1.1 / 2.0 / 3.0 / 4.0,
> F1–F8 and the points where I deviate. The single source of truth for CAD is now
> `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json`.

1. Keep the lead's architecture: **rear-mounted PA6-GF30 frame, plain laser-cut rounded-rectangle cut-out, 1.0 mm black lip filling the sheet thickness**. No press tool. Flush is real: glass, lip and steel front faces in one plane.
2. **Glass 181.48 × 143.83 × `glass_t` (default 3.0, valid 1.1–4.0), R6**, black print on the inner face with a window 0.3 mm inside the active area (153.48 × 85.32); equal **14.0 mm borders top/left/right and a 44.5 mm chin** (logo zone) below the window.
3. The chin exists because no glass land is possible over the tail exits; the chin's land lies beyond the tail loops (y 147.7–154.0). Result: the glass is bonded on **all four sides** (lands 6.1–8.9 mm), the front is sealed, the tail pocket needs no floor.
4. Glass bonded to a recessed land with a **4.0 × 1.0 mm elastic gap-filling bead** (2-C/1-C silicone or MS polymer, ≥ ±25 % movement class) and 8 stand-off pips (Ø1.5 × 0.5). The jig puts the **glass front and the lip top on the same flat vacuum plate**, so glass-to-lip is ±0.06 RSS regardless of glass thickness.
5. The lip stands on a **sheet-seat ring** (1.5 wide, Z = sheet back) that gives the sheet's cut edge a hard Z stop exactly where flushness is seen: lip vs steel ±0.09 RSS (±0.07 with sheet ordered to ±0.05).
6. Frame-to-sheet: **four straight 12 mm VHB strips** (1.1 tape in the 1.0 gap between hard stops) carry push loads between the corners, seal the flange (plus a sealant dab at each corner), and hold the sheet's cut edge on the seat ring. **Four corner M4 studs** (hidden CD weld studs, nyloc, radial stadium slots 5.4 × 7.0) locate, clamp during wet-out and are the mechanical back-up; the same slots take Ø4.8 rivets (R4). Four studs **alone** are not enough: 0.58 mm sink at a mid-edge under 50 N.
7. Visible result (front): steel | 0.40 shadow line | 1.00 matte black lip | 0.40 black-on-black line | glossy black glass border | image. Push (3.0 glass): ≤ 14 µm at 5 N, ≤ 0.14 mm dish / ≤ 0.07 mm at the lip line at 50 N; 250 N survives (glass ~64 MPa global, SF ≈ 1.9).
8. Panel hangs on the glass by the optical bond; it no longer touches the Formex (0.8 mm back-stop gap, 0.06–1.54 worst case). Everything behind Z −5.0 (Formex, shelf, 26 ribs, 9 PCB bosses, tail-pocket walls, mains creepage) is v2 geometry; the stand-off becomes 5.8 ± 0.74.
9. "Click into a plain slot and truly flush" is **not achievable** with one part: a click-in needs a shoulder on the sheet front (not flush) or a second, rear-mounted receiver. The rear frame is the receiver; the click-in only adds a part, a tolerance and a wider gap.
10. Main risks: **GT911 touch through 3.0 + 0.25 + 0.7 mm of glass** (retune or 2.0 mm CS glass), the **0.5 J impact** on 3 mm tempered glass (SF ≈ 1.2 by estimate, must be tested), and in-house optical-bond yield. Overall size grows to 223.5 × 185.8 at the sheet and 15.6–18.5 mm deep behind it (glass 1.1–4.0).

---

## 1. What I did with the lead's hypothesis (attack summary)

| item | hypothesis | verdict | change |
|---|---|---|---|
| rear frame + plain laser cut + 1 mm lip | yes | **kept** | lip now stands on a sheet-seat ring (§5.4) |
| land depth "~3.1 behind the flange face (glass 3.0 + adhesive − sheet 1.0)" | arithmetic | the formula gives **2.0 + a**; 3.1 needs a = 1.1 | with a = 1.0 the land is 3.0 behind the sheet back / 2.0 behind the flange face (the VHB adds 1.0) |
| gap-filling adhesive, jig on the glass front | yes | **kept** | reference the **lip top**, not the flange plane: glass↔lip ±0.06 RSS instead of ±0.07, and the lip-height tolerance drops out of the visible glass/lip step |
| thin adhesive | implied 0.1–0.5 | **too thin** | thermal shear at the bead corners 0.23 mm (50 ppm) → 1.0 mm bond line (23 %; 46 % at the 70 ppm bound with the thinnest line) |
| 4 corner fasteners | yes | **not enough alone** | 0.56 mm at a mid-edge under 50 N; the sheet's cut edge is unsupported between corners. VHB ring added (§7) |
| blind rivets set from the front, washer behind | yes | works, not recommended | uncontrolled clamp (~1 kN → 11.8 MPa under the washer), dome head ~1.0–1.3 proud = not flush; hidden studs preferred (open question 2) |
| panel hangs from the glass, v2 shelf as back-stop | yes | **kept** | needs a real gap (0.8 nominal), §4c |
| (a) moulded 2 mm floor in front of the tails | yes | **true, margin 0.02 mm** | CTP leg front surface is 3.52 behind the sheet back → floor 2.02 for 1.5 clearance, on an *estimated* exit height. Not needed with the chin |
| (b) bottom edge | (i)/(ii)/(iii) | **(ii) chin** | §3 |
| (c)–(e) | | quantified | §3, §6, §7 |

---

## 2. Options matrix (laser-cut / press-brake sheet only)

Notation in the sketches: `▓` steel sheet, `█` frame plastic, `▒` glass, `░` adhesive/tape, front = up.

**A. Rear frame + moulded lip through a plain cut (RECOMMENDED, = hypothesis as modified)**
```
 ▓▓▓▓▓▓▓▓│ │█│ │▒▒▒▒▒▒▒▒▒▒   front plane: steel | g1 | lip | g2 | glass
 ▓▓▓▓▓▓▓▓│ │█│ │▒▒▒▒▒▒▒▒▒▒
 ░░░░░░░░███████ ▒▒▒▒▒▒▒▒▒▒
 ██flange███ step █░bead░█ land
```
**B. No lip - glass edge faces the steel edge directly** (same frame, seat ring directly under the sheet edge)
```
 ▓▓▓▓▓▓▓▓│ │▒▒▒▒▒▒▒▒▒▒▒▒   steel | 0.35 | glass
 ▓▓▓▓▓▓▓▓│ │▒▒▒▒▒▒▒▒▒▒▒▒
 ░░░░░░███ █▒▒▒▒▒▒▒▒▒▒▒▒
```
**C1. Front click-in into a plain cut with a front bezel** (the only thing that can stop a front-inserted part at depth is a shoulder on the sheet front)
```
   █████▒▒▒▒▒▒▒▒   bezel 0.8-1.5 proud of the steel
 ▓▓▓▓▓▓█ ▒▒▒▒▒▒▒
 ▓▓▓▓▓▓█<snap
```
**C2. Front click-in into a rear-mounted receiver frame** (two moulded parts)
```
 ▓▓▓▓▓│ │█│ │▒▒▒▒   module (glass+carrier) clicks into receiver; receiver = frame of A
 ░░░░███ █<█▒▒▒▒   snap travel needs 0.5-0.8 gap all round
```
**D. Rear snap / push-on clips**: frame of A, fixed with push-on spring clips (Starlock type) on sheet studs instead of nuts. Snap hooks that catch the sheet itself would have to reach round the cut edge onto the front face (visible).

**E. Two-layer laser-cut rabbet (doubler)**
```
 ▓▓▓▓▓▓│ │▒▒▒▒▒▒   rebate depth must be glass + bond = 3.5-4.0:
 ▓▓▓▓spacer 2.5▓▒▒   front 1.0 + spacer ring 2.5 + doubler 1.0, joined by
 ▓▓▓▓▓▓doubler▓▓░░   spot welds (marks on the cosmetic face) / rivets / adhesive
```
**F. VHB-bonded frame, no fasteners**: A without the studs.

**G. Bent return-flange window**: inner flanges bent back on a press brake (segmented punch through the 181 × 143 window), corner relief notches 1–2 mm, bend radius ≈ t at the visible edge.
```
 ▓▓▓▓▓▓╮  ▒▒▒▒▒   rounded steel edge, V-groove ~1 mm at the glass, open corners
       ▓  ▒▒▒▒▒
```
**H. Stepped (rebated) glass - the glass is its own lip**: glass front 1.0 deep × 3 wide rebate ground before tempering (or a 1.0 + 2.0 two-glass laminate); the glass's back step bears on the sheet back through the VHB.
```
 ▓▓▓▓▓▓│ │▒▒▒▒▒▒▒
 ░░░░░░░░▒▒▒▒▒▒▒▒▒   flush = rebate depth (+-0.05) vs sheet (+-0.08)
```
**I. Soft lip**: as A, but an extruded black silicone T-profile fills the steel-to-glass gap instead of the moulded lip.

| | front view | glass↔steel flush (RSS / WC) | sheet ops | parts added | assembly | service | 50 N push (worst, mm) | sealing | cost @100 (indicative) | score /5 |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | steel \| 0.4 \| 1.0 black lip \| 0.4 \| glass | ±0.11 / ±0.25 (glass↔lip ±0.06) | laser cut, deburr, 4 CD studs | frame, bead, VHB ring, 4 nuts | 2 jigs, medium | cut VHB, ~40 min | 0.13 (dish), 0.06 at lip | bead + VHB, closed | lowest (1 tool) | **4.5** |
| A′ (hypothesis, 4 fasteners, no VHB, thin bond) | same | ±0.11 / ±0.25, plus sheet waviness unheld | laser, 4 holes | frame, adhesive, 4 rivets | easy | drill rivets | **0.56** at a mid-edge | flange open | lowest | 3 |
| B | steel \| 0.35 \| glass | ±0.11 / ±0.25 | as A | as A | jig references the pads, not a lip | as A | as A | as A | as A | 3.5 |
| C1 | bezel ring 0.8–1.5 **proud** | not flush | laser | carrier with bezel + hooks | easy, tool-less | best (pull out) | 0.1 (bezel bears on the front) | gasket under bezel | low | 2 |
| C2 | steel \| 0.6–0.8 \| glass | ±0.16 / ±0.40 (+ snap play) | as A | 2nd moulded part (2nd tool) | medium | front, suction cup | as A + snap play 0.1–0.2 | needs a second seal | +1 tool | 2.5 |
| D | as A | as A | studs | push-on clips | fastest | clips destroyed on removal | as A | as A | as A | 3.5 (= A, fastener variant) |
| E | steel \| gap \| glass, 3 sheet layers | ±0.15 / ±0.35 (3 layer tolerances) | 3 laser parts + joining | spacer + doubler | heavy, weld/flatness risk | poor | good | adhesive | high (3 sheets, joining) | 1.5 |
| F | as A | as A | laser only | no studs | blind placement, no locating | as A | as A | as A | lowest | 3.5 |
| G | rounded steel edge, ~1 mm V-groove, open corners | ±0.2 / ±0.4 (bend line) | laser + 4 internal bends (special punch) | - | medium | as A | as A | corner reliefs leak | medium | 1.5 |
| H | steel \| 0.35 \| glass | ±0.09 / ±0.16 | laser | rebated glass (or 2-glass laminate) | easy | as A | as A | VHB | glass ×2–3; tempering a stepped glass is a supplier risk | 2.5 |
| I | steel \| black rubber ~1.2 \| glass (no air gap) | rubber top ±0.2 | laser | profile die + corner joint | medium | as A | as A | best | + profile die | 3 |

**Can it simply click into a rectangular slot and be truly flush?** No, not as one part. A part pushed in from the
front must be stopped at flush depth by a shoulder; in a plain cut the only faces it can bear on are the sheet's front
face (then the shoulder is visible and proud, C1) or something behind the sheet that is itself fixed to the sheet (a
second, rear-mounted part, C2). Snap hooks resist pull-out, not push-in, and a 50 N press on the touch screen is a
push-in. With a 1.0 mm sheet there is also no edge thickness for a hidden hook to grip without showing. Click-in is
possible as a *serviceability* feature into a rear receiver, at the price of a second tool, a second tolerance chain
(±0.1–0.2) and a wider gap for the snap travel. A press-formed recess is not needed for flushness either: A is flush
with a plain cut because the lip fills the sheet thickness.

---

## 3. Bottom edge, tails and the panel back (lead's points a–c)

**(a) Tails vs the new levels.** The tails' Z is fixed relative to the glass, not to the frame: CTP leg front surface =
glass back + 0.25 + 5.32 − 3.9 − 0.15 = **glass back + 1.52**; TFT leg 2.82 behind. With the flush stack the CTP leg is
**3.52 mm behind the sheet back**. A floor in the flange plane can be 2.02 thick for 1.5 clearance - true, but with
0.02 mm margin on exit heights that the panel model itself marks as "ESTIMATED". Needed only for the no-chin variant.

**(b) The bottom edge.** No land is possible between x 39.2 and 167.4: the land plane (glass back + bond) lies where
the tails leave the panel.

| | (i) no chin: glass to window + 12, free bottom edge | **(ii) chin: glass to y 152.0, land beyond the loops** | (iii) bridge in front of the tails |
|---|---|---|---|
| support | lands on 3 sides + 2 bottom corners; free edge 128.2 mm | lands on all 4 sides | 1.0 plate between glass back and the CTP tail: 0.3 clearance on an estimated exit height → rejected |
| 50 N at bottom-edge mid (with VHB) | **0.35 mm** (glass sinks relative to the lip) | 0.06 mm | - |
| 250 N at bottom-edge mid | 182 MPa global (> 120) until the panel lands on the shelf after the 0.8 gap → relies on the back-stop | 39 MPa | - |
| sealing | the bottom g2 gap opens into the tail pocket; needs a 2.0 floor and still leaks behind the glass | closed bead all round | - |
| look | symmetric 12 mm borders, glass 177.5 × 109.3 | 12 / 12 / 12 mm and a **42.5 mm chin** with a logo zone | - |

Recommendation **(ii)**. The chin is the honest price of tails that cannot be moved (fixed PCB, fixed panel). It also
hides the tail pocket behind glass, so the frame needs no floor there.

**(c) Panel referenced from its front.** Panel back → Formex gap `g_bs` = 0.80 nominal; WC 0.06–1.54, RSS 0.42–1.18
(LCM ±0.3 dominates; glass ±0.2, CTP ±0.1, OCA ±0.05, frame/sheet ±0.05, Formex ±0.04).
- Stand-off PCB back → panel back: 5.80 (5.06–6.54) instead of 5.00. The tails take it in their U-loops: U radius
  TFT 5.00 → 5.40 (5.03–5.77), CTP 5.55 → 5.95; the loop bottoms move **up** by 0.02–0.44 mm (more clearance to the
  pocket bottom). The tail loops have ~22 mm of hang; length is not critical.
- Back-stop if the optical bond fails: the panel drops ≤ 1.54 mm onto the Formex/shelf (v2's normal state), stays
  captured by the clearance pocket (0.8/side), and cannot reach mains: Formex in between, PS1 lead tips 1.335 mm behind
  the Formex (v2 §6). The tails have slack.
- If LOCA (up to 1.0) replaces OCA, every level in front of the panel moves 0.75 forward; drive them from `t_opt` in
  CAD, do not eat the back-stop gap.

---

## 4. Recommended concept - dimensions

### 4.1 Level table (Z, mm; GF-1.0: LOCA `t_opt` 0.30, glass `glass_t` 3.0, sheet 1.0, gap 1.0, bond 1.0)

The full table for glass 1.1 / 2.0 / 3.0 / 4.0 and the expressions are in §11.3.

| level | Z | note |
|---|---|---|
| `Z_TROUGH_TOP` | +4.05 | tail-pocket walls and bottom beam top, outside the board only (v2) |
| `Z_PCB` | 0.00 | PCB back = boss / support-rib / pocket-wall tops (v2) |
| `Z_SHELF_BACK` | −2.10 | shelf back (v2) |
| `Z_SEAT` | −4.60 | shelf front = Formex back; Formex PSA-bonded (v2 level) |
| `Z_FORMEX_FRONT` | −5.00 | = v2 panel back |
| `Z_PANEL_BACK` | −5.80 | nominal, floats −5.08…−6.52 worst case (§3c) |
| `Z_TUBE_TOP` | −7.42 | fastener tube top, washer / rivet seat |
| `Z_LANDPLATE_BACK` = `Z_STEPWALL_BACK` | −7.92 | back of the 2.5 land plate (corner-cell floors, boss bases) |
| `Z_TAIL_TFT_EXIT` | −8.40 | estimated (panel model) |
| `Z_TAIL_CTP_EXIT` | −9.70 | estimated |
| `Z_LOOP_FRONT` | −9.85 | CTP leg front surface |
| `Z_FLANGE_BACK` | −9.92 | flange back |
| `Z_LAND` | −10.42 | glass land = floor of the glass recess |
| `Z_PIP_TOP` | −10.92 | stand-off pip tops |
| `Z_CTP_FRONT` | −11.12 | CTP cover-lens front |
| `Z_GLASS_BACK` | −11.42 | printed face |
| `Z_FLANGE_FRONT` | −12.42 | flange front, tape on it |
| `Z_SHEET_BACK` | −13.42 | sheet inner face = top of the sheet-seat ring and the corner pads = parting plane |
| `Z_GLASS_FRONT` = lip top = sheet front | **−14.42** | flush plane |

Derived: recess depth lip top → land 4.00 (= glass + bond); lip 1.00 above the seat ring; frame depth behind the sheet
back 17.47 (v2 15.07); everything at Z ≥ −5.0 is v2.

### 4.2 Plan (abs, y down)

| item | x | y | size | R |
|---|---|---|---|---|
| active area (DS) | 26.81–180.89 | 23.87–109.79 | 154.08 × 85.92 | 0 |
| CTP view area (`va_*`) | 26.31–181.39 | 23.23–110.15 | 155.08 × 86.92 | - |
| **print window** = AA − 0.30/side | 27.11–180.59 | 24.17–109.49 | 153.48 × 85.32 | 0.5 |
| **glass** | 13.11–194.59 | 10.17–154.00 | 181.48 × 143.83 ±0.2 | 6.0 |
| lip inner face (g2 0.40) | 12.71–194.99 | 9.77–154.40 | 182.28 × 144.63 | 6.4 |
| lip outer face (lip 1.00) | 11.71–195.99 | 8.77–155.40 | 184.28 × 146.63 | 7.4 |
| **sheet cut-out** (g1 0.40) | 11.31–196.39 | 8.37–155.80 | **185.08 × 147.43** ±0.1 | **7.8** |
| sheet-seat ring | lip outer face … glass + 2.9 | | 1.5 wide | 8.9 outer |
| tape strips (12 wide) | glass + 3.9 … glass + 15.9 | | top/bottom 183.48 long, sides 145.83 long | straight |
| fastener lines | 2.11 / 205.59 | −0.83 / 165.00 | 203.48 × 165.83 | - |
| **flange** | −7.89–215.59 | −10.83–175.00 | **223.48 × 185.83** | 10 (centred on F1–F4) |
| clearance pocket (panel + 0.8) | 19.22–185.72 | 18.20–119.80 | 166.5 × 101.6 | 0.5 |
| tail pocket | 39.2–167.4 (v2) | to **147.70** (v2 151.2) | | **1.5** (v2 5) |
| logo zone (chin) | centre 103.85 | centre 131.75 | ≤ 100 × 20 | |

Borders (window edge → glass edge): 14.00 top, left, right; **44.51 chin**. Lands (pocket face → glass edge): 6.11
(abs left = front-view right), 8.87 (abs right), 8.03 (top), 6.30 (bottom, over the beam); the bead (0.9–4.9 inside the
glass edge) keeps 1.21 / 3.97 / 3.13 / 1.40 to the pocket face. Window centre 15.26 above the glass centre.

**Fasteners**: F1–F4 at the glass corners + 11.0 in x and y, F5–F8 (optional, S8 only) at the mid-sides on the same
lines; all symmetric about the glass centre (103.85, 82.085). Table with clearances in §11.4. The new cut-out centre is
15.40 mm lower than v2's sheet window centre (103.85, 66.69).

### 4.3 Glass and print

- 3.0 ± 0.2 thermally tempered soda-lime (EN 12150-1), outline ±0.2 (CNC ground; ±0.3 costs 0.05 of g2 margin, §6),
  R6.0 corners, flat-ground + **polished** edge, 0.5 × 45° arris front and back (a frosted ground arris shows as a white
  line in the 0.4 gap). Flatness ≤ 0.1 mm over the pane (tighter than EN 12150's general bow, specify it).
- Print on the inner face, ceramic enamel fired in tempering: (1) logo colour (white/grey) in the chin zone, (2) black
  over everything except the window, 10–25 µm, to ≤ 0.3 mm from the edge (the land and black bead behind hide the rim).
  Window 153.48 × 85.32, R0.5, at AA − 0.30 per side. It hides the CTP's own print edge (0.36–0.64 outside the AA)
  and the LCM black matrix, the panel edges and the tails.
- Alignment budget (per side): **active alignment** (panel lit with a 1-px border, aligned under a loupe/USB
  microscope) ±0.10 RSS / ±0.16 WC → the window covers 1.0–2.6 px of the image and never shows the black matrix or the
  CTP print. Passive alignment on outlines: ±0.32 RSS / ±0.70 WC → up to 0.40 of black matrix visible; not good enough.
  **GUI rule: keep the outer 5 px of the 800 × 480 frame black.**
- Optional anti-fingerprint coating on the front (supplier option).

### 4.4 Frame (new part "glassfront frame", PA6-GF30 FR as v2 §3)

Section through a top or side edge (not to scale; s = distance outward from the glass edge, mm):
```
 s:         -8.2      -4.8   -2.3          0  0.4 1.4 1.8  2.9                      19.0
 Z -14.37   ===== GLASS 3.0 (print on back) ==|  |lip|  |#### STEEL 1.0 (cut edge at s 1.8) ####
            =====================================|  |   |  |#########################################
 Z -13.37   =====================================|  |   +--+-seat ring--+-------------------------
            =====================================|  |  step wall      |:::: VHB 1.0 :::: (F pad)
 Z -12.37   =====================================|  |  (s 0.4-2.9)    +--------------------------+
 Z -11.37   ------ glass back ------------------ +  |                 |  FLANGE 2.5              |
            OCA 0.25, CTP front -11.12, panel    |  |                 |                          |
 Z -10.37        |pocket face  ::bead 3.0 x 1.0::   +-- land ---------+--------------------------+ -9.87
                 |  [######## LAND PLATE 2.5 (Z -10.37..-7.87) ########]
 Z  -7.87        |  [pocket wall 2.5, s -4.8..-2.3, up to Z 0]
 Z -4.6..-2.1  shelf (s -8.2..-4.8), Formex 0.4 PSA-bonded on its front face (v2 levels)
 Z   0.00   ................................................ PCB back
```
g2 = 0.40 between the glass edge (s 0) and the lip inner face (s 0.4); g1 = 0.40 between the lip outer face (s 1.4)
and the sheet's cut edge (s 1.8). The bead sits on the land 0.9–3.9 inside the glass edge.

| feature | dimension | note |
|---|---|---|
| glass recess | lip inner face (glass + 0.4), 4.00 deep from the lip top to the land | 1° draft |
| land | Z −10.42 (3.0 glass), from the pocket face to the recess face; min 6.11 wide | bead 4.0 wide, 0.9–4.9 inside the glass edge; 8 pips Ø1.5 × 0.5 on the bead centre line (§11.5) |
| lip | 1.00 wide × 1.00 above the seat ring, 1° draft (top 0.97), R0.3 both top edges (flat 0.37), root R0.2 | on the inner edge of the step wall |
| sheet-seat ring | s 1.4–2.9, top Z −13.37 (= sheet back), continuous | sheet edge overlaps it 1.1; sets the VHB compression and the sheet edge Z |
| step wall | s 0.4–2.9, Z −13.37 … −7.87 (2.5 thick) | joins flange plate and land plate |
| flange | Z −12.42 … −9.92 (2.5; 3.0 glass), outline glass + 21.0, R10 centred on F1–F4 | tape strips s 3.9–15.9 |
| land plate | Z −10.37 … −7.87 (2.5), between pocket face and step wall; full-width under the bottom corners (corner-cell fronts) | |
| clearance pocket | panel + 0.8/side, 1° draft, from the land back to the shelf | panel no longer located by the frame |
| shelf, Formex, 26 support ribs, 9 PCB bosses | **v2 geometry and Z**; ribs 0.55 longer at their wall end (wall face moved out); bosses H1–H9 rise from the land plate (Z −7.87) to Z 0; blind pilots as v2 | creepage path not shortened (≥ 7.95 mm, v2 §6); panel 0.8 farther away, clearance grows |
| tail pocket | x 39.2–167.4 (v2), bottom face y 147.70, R1.5 corners (exactly 1.5 to the TFT loop corner), walls 2.5 to Z +4.05, step at y 129 (v2) | **no floor**: the glass chin closes the front; open to the back as v2 |
| corner cells, H6/H7 | as v2, behind the land plate | |
| fasteners F1–F4 (+ optional F5–F8) | stadium slot 5.4 × 7.0, axis to the glass centre; F1–F4 Ø18 front pad (top Z_SHEET_BACK); tube Ø18 to Z_TUBE_TOP (2.5 above the flange back), one 1.5 rib to the step wall; F5–F8 same tube and slot, no front pad | stud: DIN 9021 M4 + ISO 10511 nyloc, 0.6 Nm; rivet: Ø4.8 + DIN 9021 M5 backing washer (§11.4) |
| v2 pegs | dropped (`pegs_on` 0) | the cut-out edge locates (shims in g1) |
| mass | ~70 cm³ ≈ 95 g (estimate) | v2 55 cm³ / 75 g |

Moulding: single pull along Z, no slides. Parting line on the flange's outer edge in the flange front plane
(Z −12.37); the seat ring, stud pads, lip and glass recess are formed in the A half; gates and ejectors on the B side
as v2 §7. The 646 mm lip ring
fills last: vents at the lip top about every 50 mm. Flatness of the frame matters less than in v2: the bonded glass
(D = 165 500 N·mm, ~30 × the frame) flattens it in the jig.

AM / CNC for the first 100: the 1.0 lip and 2.5 walls are fine for MJF/SLS (min ~0.8). Two flags: (1) **CLTE** of
PA12 is ~2 × PA6-GF30 → g1 and g2 must grow to ~0.6 and the bond line to ~1.5; (2) **fire rating**: the frame carries
a mains PCB, so IEC 60335-1 cl. 30.2.3 (GWFI 850 °C / GWIT 775 °C) applies to the AM material too. CNC from PA6-GF30
plate is possible; the lip corners are the fragile spot.

### 4.5 Sheet

- Cut-out 185.08 × 147.43, R7.8, ±0.1, centred on the glass centre. No pierce points, lead-ins or micro-joints on the
  visible edge; brush-deburr / edge-round R0.2–0.5, then coat (powder coat wraps the cut edge).
- Variants (§11.6): **S4** 4 × M4 × 16 CD weld studs on the back at F1–F4, welded **before** coating, template ±0.2;
  **S8** 8 studs at F1–F8 + soft foam gasket; **R4** 4 holes Ø5.0 +0.1 (ISO 15977 Ø4.8) or Ø5.2 +0.1 (tri-fold).
- **Correction (A6):** a PEM FH-M4 stud needs a **Ø4.0 +0.08/−0** hole (PEM: min sheet 1.0, head Ø5.9 ±0.4, edge
  ≥ 7.2). The 4.22 used in v2 §1.4 and in my first draft is the upper limit of the FH-832 hole (.163 +.003 in).
- Thickness: 1.0 (EN 10131). Ordering ±0.05 ("restricted") cuts the lip/steel step from ±0.09 to ±0.07 RSS.
- Other thicknesses: `t_sheet` drives the lip height and every level in front of the panel (the frame moves, the
  glass front stays flush). PEM needs ≥ 1.0; CD studs are fine from 0.8.

### 4.6 What the user sees (front, 20 °C, nominal)

From outside in: painted steel | **0.40** dark shadow line (floor of the slot = black seat ring) | **1.00** matte black
lip with R0.3 rounded edges | **0.40** line, black on black, hardly visible | glossy black glass border **14.0** at the
top, left and right, **44.5** at the bottom with the logo | image 153.48 × 85.32. All front faces in one plane within
±0.11 (RSS). No fastener visible with studs (S4/S8); with rivets (R4), four heads Ø10 (dome, 1.5–2.0 proud) at
9.2 / 9.2 mm outside the cut-out corners. Visible module 185.08 × 147.43.

The lip is matte glass-filled PA, the glass glossy black: they will read as two blacks (a thin "bezel" line). If that
is unwanted, the lip can be textured (VDI 3400 Ref 24) or option B (no lip) used.

---

## 5. Calculations (summary of `concept_calc_out.txt`)

### 5.1 Flushness stacks
| stack | RSS | WC |
|---|---|---|
| glass vs lip, **jig on the lip top** (plate 0.02, glass bow 0.05, cure shrinkage 0.02, spring-back 0.02) | ±0.06 | ±0.11 |
| glass vs lip, jig on the flange pads | ±0.07 | ±0.13 |
| glass vs lip, **fixed-thickness tape** (glass ±0.2 shows directly) | ±0.22 | ±0.35 |
| lip vs sheet front (lip height 0.03, sheet 0.08, seating 0.03) | ±0.09 | ±0.14 |
| same, sheet ±0.05 | ±0.07 | ±0.11 |
| **glass vs sheet front, recommended** | **±0.11** | **±0.25** |
| glass vs sheet front, fixed tape | ±0.24 | ±0.49 |
| bond line (gap-filling) | 0.79–1.21 | 0.73–1.27 |

### 5.2 Gaps over temperature (per side; frame CLTE 30 flow / 50 design / 70 bound; glass 9; steel 12)
| case | g2 glass↔lip (nominal 0.40) | g1 lip↔steel (nominal 0.40) |
|---|---|---|
| −20 °C, 50 ppm | 0.25 (RSS min 0.13) | 0.51 |
| +70 °C frame / +50 °C sheet, 50 ppm | 0.54 | 0.21 (RSS min 0.12) |
| −20 °C, 70 ppm | 0.18 (RSS 0.06, **WC −0.02**: touch) | 0.57 |
| +70 / +50 °C, 70 ppm | 0.61 | 0.12 (RSS 0.03, **WC −0.03**: touch) |
Tolerances per side: g2 ±0.12 RSS (glass ±0.2), g1 ±0.09 RSS. Moisture (dry → conditioned) moves both by ~0.09.
A touch is harmless (plastic on glass / steel, self-limiting) but the visible gap runs from ~0.1 to ~0.6.

### 5.3 Joints
- Bead glass→frame (GF-1.0, 4.0 wide): 2510 mm². Thermal shear at the bead corner (r 111.7): 23 % (50 ppm, +70 °C, t 1.0), 31 % at the
  thinnest bond line, 47 % at the 70 ppm bound → **movement class ≥ ±25 %, prefer ±50 % (silicone)** or hold glass
  thickness to ±0.1. Dead load (glass + panel 3.8 N) 2 kPa (silicone static design 14 kPa); 10 g 20 kPa; 250 N pull
  0.14 MPa mean, 0.41 peak (strength 1.5–2.5).
- OCA: panel 2 N over 16 490 mm² = 0.12 kPa; 10 g 1.2 kPa. Trivial.
- VHB flange→sheet: 10 040 mm²; module dead load 7.6 N → 0.75 kPa (3M static guideline 1.7–3.5); 250 N → 25 kPa
  (dynamic ~500). Thermal shear 30 % (50 ppm), 43 % (70 ppm) - within VHB's slow-movement capability.
- Corner studs: radial thermal move 0.24 (50 ppm) / 0.37 (70 ppm) against 0.65 float; washer bearing 5.9 MPa at
  500 N (creep 15). Rivet variant 11.8 MPa short-term, relaxing.

### 5.4 Push stiffness (grillage: glass strips + frame ring I = 1174 mm⁴ on the glass edge + corner links + supports;
frame E 3500 MPa, VHB E 1 MPa, panel and PCB stiffness **not** counted - real values are lower)

| 3.0 mm glass (2.0 / 4.0 where marked) | 5 N, window centre | 50 N centre | 50 N mid top edge | 50 N mid side edge | 250 N, worst of 5 load points: glass / ring / stud |
|---|---|---|---|---|---|
| 4 corner studs only | 44 µm | 0.44 | **0.58** | 0.39 | 101 / 28 MPa / 118 N |
| S8: 8 studs F1–F8 (foam carries no tension) | 19 µm | 0.19 | 0.13 | 0.11 | 66 / 9 MPa / 175 N |
| **S4/R4: 4 studs + VHB strips** | **14 µm** | **0.14** (lip line 0.05) | **0.07** | **0.07** | **64 / 11 MPa / ≤ 14 N** |
| 1.1 CS + VHB (no panel credit) | 141 µm | 1.41 | 0.13 | 0.13 | 420 / 21 MPa (char. 250: needs the panel behind) |
| 2.0 CS + VHB | 37 µm | 0.37 | 0.09 | 0.09 | 139 / 16 MPa (char. 250) |
| 4.0 + VHB | 7 µm | 0.07 | 0.05 | 0.05 | 37 / 8 MPa |

GF-1.0 geometry (lands 6.1–8.9, flange glass + 21, slots 5.4 × 7.0); earlier draft values were within 5 % of these.
The 6-stud variant of the first draft is dropped. Glass strength and the chin impact per thickness: §11.7.

The glass carries most of the push: the bead is soft in shear (no composite action) but stiff in compression, so glass
and ring move together. 4 fasteners alone fail a "no visible movement at 50 N" goal; 8 hidden studs would pass but
leave the sheet edge unheld between them. VHB fixes both and seals.

### 5.5 Glass strength
- 250 N on a Ø10 probe at the window centre: 55 MPa local (Roark), 64 MPa grillage → SF ≈ 1.9 on 120 MPa (3.0),
  3.9 (4.0), 2.0 (2.0 CS on 250).
- IEC 60335-1 cl. 21.1, 0.5 J: quasi-static upper bound 625 N / 192 MPa (SF 0.6); with the striker (0.25 kg) / plate
  mass ratio, 0.14 J goes into bending → 330 N / 103 MPa (**SF 1.2**). 4.0 mm: SF 1.5; 2.0 CS: SF 1.8. Order of
  magnitude only; **test it**. Cl. 21.1 judges safety (8.1, 15.1, 29 unimpaired); with the panel OCA-bonded the
  fragments stay in place and nothing live becomes accessible, but a cracked display is still a field failure.

---

## 6. Assembly sequence and jigs (in-house, 100 pcs)

**J1 - optical bond (panel → glass).** Flat vacuum plate, PET protective film, glass printed face up, located on 3
edge stops. OCA (0.25) laminated to the glass back with a roller under the window and the panel's 164.9 × 100 face.
Panel in a carrier with X/Y micrometer screws, connected to a test board showing a 1-px white border and crosshair.
Align so the print window hides 1–3 px on every side (loupe / USB microscope), then lower and laminate. Autoclave or
vacuum 30 min to clear micro-bubbles. Inspect: no bubble > 0.2 mm in the window, 1–3 px hidden per side.
(LOCA: dam-and-fill with UV cure in the same jig; levels shift, §3c.)

**J2 - flush plate (glass + panel → frame).** Ground aluminium plate (flatness 0.02) with vacuum grooves and a PET film.
1. Formex (PSA) onto the shelf's front face of the frame (before the panel goes in).
2. Prime the land (adhesive primer per supplier), dispense the bead on the land: triangular nozzle, 3.0 wide after
   squeeze, guided along the step wall.
3. Glass + panel face-down on the plate (vacuum on), against 3 stops.
4. Lower the frame (4 pins in the plate engage the Ø6 corner holes for rough position) until the **lip top lands on
   the plate** all round; 8 × 0.40 PTFE shims in g2 centre the glass; 5 kg ring weight on the flange back.
5. Cure: 1-C silicone/MS 24 h (→ 5 jigs for 100 in ~4 weeks) or 2-C / booster version 1–2 h (1–2 jigs). Recommended:
   2-C.
6. Check: a 0.05 feeler must not enter between the lip top and the plate at 8 points; g2 0.30–0.50 by feeler.
7. Apply the four 12 mm VHB strips to the flange at s 3.9–15.9 (PA primer first; strips end 1.0 before the corner
   pads), liner left on. At mounting, put a dab of the bead adhesive over each of the 4 corner gaps (GF-1.0, §11.5).

**PCB and tails** (as v2 §7 steps 4–5): PCB on the 9 bosses, Q1 leads ≤ 2.5, 9 × ST2.9 at 0.3–0.4 Nm; fold the tails
into J10/J11, loops slack. Function test: display + touch (GT911 config loaded, §8 risk 1).

**Mounting in the oven sheet** (sheet or front panel face-down on a felt-covered flat table, before it goes on the
oven body if possible): IPA-wipe the sheet back (VHB primer on powder coat if the supplier asks for it), remove the
liner, lower the module from behind (lip into the cut-out, studs through the Ø6 holes), centre with 8 × 0.40 shims in
g1, press the flange with a pressure frame (~1 kN ≈ 100 kPa on the tape) for 30 s, washers + nyloc nuts crosswise at
0.6 Nm, remove the shims. Then wire J20 etc.
Inspection: dial gauge on a bridge at 12 points round the cut-out: glass and lip vs steel within ±0.15; g1 0.25–0.55
by feeler. VHB reaches handling strength at once, ~90 % in 24 h.

**Rework / field replacement.** Before the VHB touches: lift and retry. After: remove the 4 nuts, warm the front around
the cut-out to ~60 °C with a heat gun, cut the VHB from behind with a plastic wedge / fishing line, clean with
adhesive remover + IPA, fit a new module with a new VHB ring (~40 min). The spare part is the bonded unit
glass + panel + frame; the PCB is re-used (9 screws). A broken glass cannot be replaced alone in the field.

---

## 7. Weaknesses and risks of the recommended concept

1. **Touch through 4 mm of glass** (3.0 + 0.25 OCA + 0.7 CTP cover). The GT911/Fannal tuning assumes the 0.7 cover;
   thick-cover operation needs a new config (sensitivity, drive) and may need a different panel option. Unverified -
   gate the whole concept on a sample test. Fallback: 2.0 mm chemically strengthened glass.
2. **Impact 0.5 J**: SF ≈ 1.2 on 3 mm tempered by estimate (bound 0.6). Test early; 4.0 mm helps strength, hurts touch.
3. **The chin** (42.5 mm) is forced by the fixed tails; the no-chin variant is unsealed and has a 128 mm free edge.
4. **Gap breathing**: g1 and g2 run ~0.1–0.6 over −20…+70 °C and moisture; at the 70 ppm bound both can touch
   (harmless, but a hot oven shows a near-zero line on one side).
5. **Lip and glass are two different blacks** (matte GF-PA vs glossy print).
6. **Adhesive thermal shear** 23 % design, up to 46 % at the bound with the thinnest bond line → silicone ±50 % class
   or glass thickness ±0.1.
7. **Back-stop gap** WC min 0.06 mm: an over-thick LCM (+0.3) with an over-thick glass (+0.2) almost touches; measure
   LCM thickness on incoming panels or open `g_bs` to 1.0 if the batch is thick.
8. **In-house optical bonding yield** (bubbles, dust, mura, alignment) and the need for active alignment.
9. **Service**: the module is a bonded unit; the VHB must be cut; the sheet back needs cleaning before re-bonding.
10. **Bigger and deeper**: 215.5 × 177.8 at the sheet (v2 198.4 × 165.5) and 17.4 mm behind the sheet back (+2.35);
    check against the oven's internal space.
11. **Model limits**: grillage with conservative E and no panel/PCB stiffness; VHB modulus assumed 1 MPa; exit heights
    of the tails are estimates. Run an FEA of glass + frame + VHB before cutting steel.
12. **AM first batch**: PA12 CLTE doubles gap breathing and bead shear; FR/GWFI rating of the AM nylon unconfirmed.
13. **Cosmetic face**: CD stud welding on 1.0 mm can leave a witness mark; weld before coating, or use rivets/PEM.
14. **Glass flatness** ≤ 0.1 per pane must be specified and checked; it is in the glass↔lip stack.

---

## 8. Open questions for the owner (each with my recommendation)

1. **Chin or no chin?** Chin: 42.5 mm black glass with logo below the image, bonded all round, sealed, robust. No chin:
   symmetric 12 mm borders, but 128 mm of unbonded bottom edge (0.35 mm at 50 N) and an unsealed gap into the tail
   pocket. → **Chin.**
2. **Fasteners: hidden studs or visible rivets?** 4 hidden M4 CD weld studs + VHB (nothing visible) vs 4 blind rivets
   + VHB (domes ~1 mm proud, clamp uncontrolled). → **Hidden studs.**
3. **Lip or no lip?** Lip: two 0.4 shadow lines and a 1 mm black frame line, glass edge protected by plastic. No lip:
   one 0.35 line, steel edge facing the tempered glass edge. → **Lip.**
4. **Glass thickness**: 3.0 tempered (default) vs 2.0 chemically strengthened (better touch, 3 × softer) vs 4.0
   tempered (stronger, worse touch). → **Bond three samples each of 3.0 and 2.0, test GT911 and a 0.5 J hammer, then
   decide; default 3.0.**
5. **Print window 0.3 mm inside the active area** and a 5-px black margin in the GUI. → **Accept.**
6. **Sheet**: order 1.0 mm to ±0.05, brush-deburr the cut-out, studs before powder coat. → **Yes** (lip/steel step
   ±0.07 instead of ±0.09).
7. **Frame production for the first 100**: injection mould (as v2) or MJF/SLS/CNC (then gaps 0.6, bond line 1.5, and
   an FR-rated material must be found). → **Decide after the manufacturing research; parameters already allow both.**
8. **Service concept**: the glass + panel + frame unit is the field spare; replacing it means cutting the VHB
   (~40 min). → **Accept.**

---

## 9. Assumptions (not from the v2 documents)

- Glass E 70 GPa, ν 0.22, α 9 ppm/K, 2.5 g/cm³; tempered characteristic 120 MPa (EN 12150-1); CS glass 250 MPa.
- PA6-GF30 E 3500 MPa (v2 §3, conservative); in-plane CLTE 50 ppm/K as design value between v2's 30 / 70.
- VHB: 3M 5952-class black acrylic foam, 1.1 ± 0.1, E ≈ 1 MPa for slow loads, 93 °C long-term; primer on PA and
  powder coat.
- Adhesive: elastic 1-C/2-C silicone or MS polymer, E ≈ 2 MPa, ±25–50 % movement class.
- LCM outline-to-AA position ±0.2 (no tolerance on the DS drawing).
- Sheet EN 10131 ±0.08 (normal) / ±0.05 (restricted); laser cut ±0.1; CD stud position ±0.2 with a template.
- Spring hammer striker 0.25 kg; effective plate mass 25 % of glass + panel.
- Frame mass ~70 cm³ (not modelled); weights of panel / PCB etc. from v2 §2.
- Costs are indicative only; the manufacturing research agent owns the real numbers.

## 10. Files

- `concept.md` - this study.
- `concept_calc.py` - all calculations; `concept_calc_out.txt` - its output (run: system Python 3.11, no packages).
- `concept_params.json` - flat list of the GF-1.0 parameters (116 entries, same values as the master).
- `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json` - **frozen master** (generated by `concept_calc.py`).

---

## 11. Lead's amendments and frozen values (GF-1.0, 2026-11-15)

### 11.1 What changed

| # | amendment | status | frozen value |
|---|---|---|---|
| A1 | borders 14.0, glass bottom y 154.0, lands ≥ 6, bead 4.0 × 1.0, ≥ 1.0 to the pocket face, ≥ 0.9 to the glass edge | **done** | glass 181.48 × 143.83 (x 13.11–194.59, y 10.17–154.00), chin 44.51; lands 6.11 / 8.87 / 8.03 / 6.30 (abs left / abs right / top / bottom); bead 0.9–4.9 inside the edge → 1.21 / 3.97 / 3.13 / 1.40 to the pocket face |
| A2 | 8 pips Ø1.5 × 0.5 | **done** | on the bead centre line (2.9 inside the edge), 2 per side at ±¼ of the side; never touch the glass (min clearance +0.13 at glass ±0.2, +0.23 at 1.1 ±0.1) |
| A3 | 1.0 gap between hard stops, 12 mm VHB strips, ≥ 1 mm margin, foam alternative | **done, with a limit** | strips at s 3.9–15.9, flat face s 2.9–21.0 (margins 1.0 / 5.1); 4 straight strips 183.48 / 145.83 long. The corner pads interrupt the band, so **straight strips cannot close the corners**: 4 sealant dabs (or one die-cut ring) are needed for a sealed flange |
| A4 | stadium slots 5.0 × 6.5, rivet option, F5–F8, S4/S8/R4 | **done, two deviations** | slot **5.4 × 7.0** (§11.4); F5–F8 have the same tube and slot but **no moulded front pad** (§11.4) |
| A5 | `glass_t` driving, valid at 1.1 / 2.0 / 3.0 / 4.0 | **done; 1.1 is marginal mechanically** | §11.3, §11.7 |
| A6 | PEM FH-M4 hole | **verified** | Ø4.0 +0.08/−0 (§11.6) |
| A7 | `print_inset` 0.30, alternative AA + 0.25 | **done** | in the master `print` block |
| A8 | rest unchanged | - | `t_opt` default now 0.30 (LOCA, R1), so every level in front of the panel is 0.05 further forward than in the first draft |

### 11.2 Changed plan values (abs, y down)

| item | x | y | size | R |
|---|---|---|---|---|
| glass | 13.11–194.59 | 10.17–154.00 | 181.48 × 143.83 | 6.0 |
| lip inner / outer | 12.71–194.99 / 11.71–195.99 | 9.77–154.40 / 8.77–155.40 | | 6.4 / 7.4 |
| sheet-seat ring outer edge | 10.21–197.49 | 7.27–156.90 | | 8.9 |
| sheet cut-out | 11.31–196.39 | 8.37–155.80 | 185.08 × 147.43 | 7.8 |
| tape strips | glass + 3.9 … + 15.9 | | 12 wide | straight |
| fastener lines | 2.11 / 205.59 | −0.83 / 165.00 | | |
| flange | −7.89–215.59 | −10.83–175.00 | 223.48 × 185.83 | 10 on F1–F4 |
| logo zone | centre 103.85 | centre 131.75 | ≤ 100 × 20 | |
| print window, pocket, tail pocket | unchanged | | | |

### 11.3 Levels for the four glass thicknesses (Z, mm)

| level | expression | 1.1 | 2.0 | 3.0 | 4.0 |
|---|---|---|---|---|---|
| Z_FORMEX_FRONT … Z_TROUGH_TOP | v2 | −5.00 … +4.05 | same | same | same |
| Z_PANEL_BACK | Z_FORMEX_FRONT − g_bs | −5.80 | −5.80 | −5.80 | −5.80 |
| Z_CTP_FRONT | − panel_t | −11.12 | −11.12 | −11.12 | −11.12 |
| Z_GLASS_BACK | − t_opt | −11.42 | −11.42 | −11.42 | −11.42 |
| **Z_GLASS_FRONT** (= lip top = sheet front) | − glass_t | −12.52 | −13.42 | −14.42 | −15.42 |
| Z_SHEET_BACK (seat ring, pads) | + t_sheet | −11.52 | −12.42 | −13.42 | −14.42 |
| Z_FLANGE_FRONT | + t_gap | −10.52 | −11.42 | −12.42 | −13.42 |
| Z_FLANGE_BACK | + flange_t (snap) | **−7.92** (snapped, flange 2.60) | −8.92 | −9.92 | −10.92 |
| Z_LAND | Z_GLASS_BACK + t_bond | −10.42 | −10.42 | −10.42 | −10.42 |
| Z_PIP_TOP | Z_LAND − pip_h | −10.92 | −10.92 | −10.92 | −10.92 |
| Z_LANDPLATE_BACK = Z_STEPWALL_BACK | Z_LAND + wall | −7.92 | −7.92 | −7.92 | −7.92 |
| Z_TUBE_TOP | Z_FLANGE_BACK + tube_h | −5.42 | −6.42 | −7.42 | −8.42 |
| tails / loop front | panel | −8.40 / −9.70 / −9.85 | same | same | same |
| step wall height | | 3.60 | 4.50 | 5.50 | 6.50 |
| frame depth behind the sheet back | | 15.57 | 16.47 | 17.47 | 18.47 |

What degenerates and how CAD handles it:
- **1.1 mm:** the land comes within 0.10 of the flange front, and the flange back within 0.10 of the land-plate back.
  The two plates become one 2.6 mm plate behind the seat ring (level snap: flange back → Z_STEPWALL_BACK). The step
  wall shrinks to the seat ring + lip (1.0 + 1.0 tall above that plate on the front side). Keep the step wall as one
  body from Z_SHEET_BACK to Z_STEPWALL_BACK in every case, so the topology never changes; only the snap rule
  (|Δ| < 0.5) removes the 0.1 mm step face. The nut top reaches Z +0.58 (outside the board, allowed).
- **4.0 mm:** the flange plate lies wholly in front of the land; the 6.5 mm step wall carries the connection. No
  degeneracy; the frame is 1.0 deeper.
- At every thickness the glass recess is glass_t + 1.0 deep, the lip is 1.0 above the seat ring, the pips stand 0.5
  below Z_LAND, and nothing changes at Z ≥ −5.0.

### 11.4 Fasteners F1–F8 (radial stadium slots, axis towards the glass centre)

| | x | y | slot axis ° (from +X, y down) | r from glass centre | to board outline incl. ears (≥ 6.5) | nearest ear hole (≥ 11.0) | to J20 / J2 wire corridor | to tail pocket / loops | tube (R9) to PCB boss (R4) | to cut-out edge (≥ 8) | used by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 2.11 | −0.83 | 39.18 | 131.2 | 27.2 | H1 31.7 | 27.5 | 125.4 | 18.7 | 16.24 | S4 R4 S8 |
| F2 | 205.59 | −0.83 | 140.82 | 131.2 | 30.1 | H4 34.6 | 181.4 | 125.8 | 21.6 | 16.24 | S4 R4 S8 |
| F3 | 205.59 | 165.00 | −140.82 | 131.2 | 46.8 | H6 51.3 | 182.7 | 41.9 | 38.3 | 16.24 | S4 R4 S8 |
| F4 | 2.11 | 165.00 | −39.18 | 131.2 | 45.3 | H7 49.8 | 54.8 | 40.9 | 36.8 | 16.24 | S4 R4 S8 |
| F5 | 103.85 | −0.83 | 90.00 | 82.9 | 14.0 | H2 18.5 | 82.3 | 119.8 | 5.5 | 9.20 | S8 |
| F6 | 205.59 | 82.09 | 180.00 | 101.7 | 21.6 | H5 31.2 | 174.7 | 53.1 | 18.2 | 9.20 | S8 |
| F7 | 103.85 | 165.00 | −90.00 | 82.9 | 46.0 | H6 82.2 | 90.9 | 17.3 | 69.2 | 9.20 | S8 |
| F8 | 2.11 | 82.09 | 0.00 | 101.7 | 17.9 | H8 29.9 | 12.8 | 52.3 | 16.9 | 9.20 | S8 |

All eight pass every rule at their nominal places; none had to move. The board outline is the real KiCad Edge.Cuts
polygon (`board_geom.json`); the wire corridors run from the J20 / J2 courtyards to −x, ±2 mm. The tube edge sits
1.0 inside the flange edge everywhere (flange = glass + 21).

- **Slot 5.4 × 7.0, not the asked 5.0 × 6.5.** With 5.0 a Ø4.8 rivet has 0.10 per side across the slot. That is
  below the frame-to-sheet location stack (0.12 RSS: slot position ±0.1, hole ±0.05, centring ±0.05) and below the
  tri-fold maker's hole of 5.1–5.4 (R2 §3.1). 5.4 × 7.0 gives the rivet 0.30 per side and the M4 stud 1.15 along /
  0.35 across after stud position (±0.2) and centring (0.15). The thermal move is 0.25 (50 ppm) / 0.38 (70 ppm), so it
  is covered. The 5.0 × 6.5 slot works for studs only (float 0.90 along / 0.15 across).
- **Washers:** DIN 9021 M4 (Ø12) on the stud keeps a 1.0 rim beyond the slot's far end at the worst stud offset, and
  82 mm² of bearing (6.1 MPa at 500 N). DIN 9021 M5 (Ø15 × 1.2) as the rivet backing washer keeps a 2.9 rim and stays
  on the Ø18 tube top (edge at R8.6), with 145 mm² of bearing (~17 MPa transient while setting, relaxing).
- **Rivet grip** = sheet 1.0 + gap/pad 1.0 + flange 2.5 + tube 2.5 + washer 1.2 = **8.2 mm** (8.3 at glass 1.1). Use
  a Ø4.8 tri-fold / bulb Al/Al rivet whose grip range covers 7.8–8.6 (typically L ≈ 16–18; confirm on the maker's
  table). Sheet hole: Ø5.0 +0.1 for an ISO 15977 rivet, Ø5.2 +0.1 for a tri-fold. Heads Ø10, 1.5–2.0 proud.
- **F5–F8 front pad (deviation):** a moulded Ø18 pad at the mid-sides would cut the straight tape strips into eight
  pieces in S4/R4. So F5–F8 have the tube and slot but a flat front face; the tape runs over the slot. In S8 a
  DIN 9021 M4 washer (1.0 thick) on each stud between sheet and flange is the hard stop. F1–F4 keep moulded Ø18 pads.
- **Studs:** M4 × 16 CD weld studs (stack above the sheet back 13.5 incl. 1.5 thread), welded before coating.

### 11.5 Lands, bead, pips, tape, gasket

- Bead 4.0 × 1.0 (WC 0.73–1.27 at glass ±0.2; 0.83–1.17 at 1.1 ±0.1), area 2510 mm²: 1.55 kPa dead load, 0.10 MPa
  mean at a 250 N pull.
- Pips: P1/P3 (58.48 / 149.22, 13.07), P2/P4 (58.48 / 149.22, 151.10), P5/P7 (16.01, 46.13 / 118.04), P6/P8
  (191.69, 46.13 / 118.04). Tops at Z_LAND − 0.5. Minimum clearance to the glass back in the jig stack, including
  glass bow 0.05 and pip height +0.05: **+0.13** (glass ±0.2) / **+0.23** (1.1, ±0.1). They never touch, so no lowering
  was needed. If glass ±0.3 were ever accepted, lower them to 0.4.
- Tape: 3M VHB 5952-class 12 × 1.1 in the 1.0 gap (9 % compression), area 7903 mm². Thermal shear at the outer
  corner 30 % (50 ppm) / 43 % (70 ppm). **Spring-back risk:** the 0.1 mm of tape compression can push the lip line up
  to ~0.1 mm off the seat ring between the corner studs until the acrylic foam relaxes. Keep the pressure frame on
  ≥ 20 min after mounting and measure the first articles.
- **S8 foam gasket (serviceable, tape-free variant)** - lift of the lip line between the 8 studs from the gasket's
  push (grillage):

| gasket line load | glass 3.0 | glass 1.1 |
|---|---|---|
| 0.10 N/mm (e.g. 12 mm at ≤ 8 kPa, or 5 mm at ≤ 20 kPa) | 39 µm | 73 µm |
| 0.36 N/mm (12 mm at 30 kPa) | 141 µm | 263 µm |
| 0.84 N/mm (12 mm at 70 kPa, v2's nominal gasket stress) | 328 µm | 614 µm |

  So S8 works only with an extra-soft or narrow gasket (≤ 0.10 N/mm). A v2-type silicone sponge at 30 % would put
  the lip line 0.14–0.33 mm behind the steel between studs.

### 11.6 Sheet variants and the PEM finding

| variant | sheet features (besides the cut-out 185.08 × 147.43 R7.8) | frame side | seal |
|---|---|---|---|
| **S4** (recommended) | 4 × M4 × 16 CD weld studs at F1–F4, template ±0.2, welded before coating | 4 strips VHB + 4 corner dabs, washers + nylocs | tape |
| **S8** (serviceable) | 8 × M4 × 16 CD weld studs at F1–F8 | soft foam gasket strips, notched round the 4 mid-side spacers; 4 spacers DIN 9021 M4 | foam |
| **R4** (visible rivets) | 4 holes at F1–F4: Ø5.0 +0.1/0 (ISO 15977 Ø4.8) or Ø5.2 +0.1/0 (tri-fold) | VHB strips; rivets with DIN 9021 M5 backing washers | tape |

**PEM finding (A6):** PEM's catalogue page for FHS-M4-8 gives sheet hole **4.0 mm +0.08**, minimum sheet 1.00 mm,
head Ø5.9 ±0.4, minimum hole-centre-to-edge 7.2 mm. PEM's FH-M4 product pages give the same 4.0 +0.08 hole
([catalog.pemnet.com, FHS-M4-8](https://catalog.pemnet.com/sl/printitem/flush-head-threaded-studs-types-fh-fha-fhs/lf-clinching-threaded-studs-type-fh-fhs-fha-metric/fhs-m4-8);
[pemnet.com, FH-M4-8ZC](https://www.pemnet.com/products/product-finder/fh-m4-8zc/)). The unified FH-832 hole is
.163 +.003 in = 4.14 +0.08 mm, and 4.22 mm = .166 in is its upper limit. So v2's "Ø4.22 +0.08/−0" (frame report §1.4
and its drawing hole table) and my first draft are wrong for M4: they mix the FH-832 limit with the M4 tolerance. Only
this study is corrected; the v2 files are untouched.

### 11.7 Glass per thickness (S4 + VHB; grillage without panel credit; local Roark estimates)

| glass | type (char. strength) | 50 N centre / lip line | 250 N centre: no panel credit / on the LOCA-panel foundation | 250 N on the chin over the tail pocket (local, nothing behind) | 0.5 J window centre: bound / mass-ratio (SF) | 0.5 J chin over the pocket (SF) |
|---|---|---|---|---|---|---|
| 1.1 | CS (250) | 1.41 / 0.17 mm | 378 / 151 MPa | ~247 MPa (SF 1.0) | 457 / 222 MPa (1.1) | 236 MPa (**1.1**) |
| 2.0 | CS (250) | 0.37 / 0.09 | 114 / 62 | ~75 (3.3) | 256 / 131 (1.9) | 131 (1.9) |
| 3.0 | tempered (120) | 0.14 / 0.05 | 51 / 33 | ~33 (3.6) | 175 / 95 (1.3) | 86 (1.4) |
| 4.0 | tempered (120) | 0.07 / 0.03 | 29 / 20 | ~19 (6) | 130 / 74 (1.6) | 62 (2.0) |

The chin over the tail pocket spans 128.2 × 28.7 between the panel's bonded bottom edge (y 119) and the beam land
(y 147.7), with nothing behind it. Locally it is stiff (short span), so at 2.0–4.0 mm it is no weaker than the window
centre. **At 1.1 mm it is the weak spot:** about 247 MPa locally at 250 N and SF ≈ 1.1 at 0.5 J. A cracked chin
opens into the tail pocket (FPC tails, SELV), with no live part reachable. 3.0 tempered keeps its SF of 1.3–1.4 on the
5 % characteristic strength; if the supplier can only make 3.0 as CS glass (R2: tempering from 3.2), the margins
double.

### 11.8 Where I disagree or could not make it work

1. **Slot 5.0 × 6.5 → 5.4 × 7.0** (§11.4). The asked slot is too tight for a Ø4.8 rivet (0.10 per side against a
   0.12 RSS location stack and a 5.1–5.4 maker's hole).
2. **"Same pad" at F5–F8:** a moulded pad there breaks the straight tape strips. F5–F8 get no front pad; S8 uses
   1.0 spacer washers.
3. **Straight 12 mm strips cannot seal the corners.** The corner pads sit inside the band. Either 4 sealant dabs at
   assembly (frozen) or a die-cut ring with pad cut-outs.
4. **S8 with a v2-type foam gasket fails flushness:** 141–328 µm lift between studs. Only an extra-soft or narrow
   gasket (≤ 0.10 N/mm → 39 µm) is acceptable.
5. **Glass 1.1 is geometrically valid but mechanically marginal:** 1.4 mm at 50 N without panel credit; the chin
   sees ~250 MPa at 250 N, and 0.5 J has SF ≈ 1.1. If the touch test forces 1.1, add a 2.5 mm "chin rib" between
   the two tail loops (x 77.3–82.5, 1.5 clear of both) under the chin, and test 0.5 J on the chin. Otherwise keep
   ≥ 2.0.
6. **Flange 223.5 × 185.8** (glass + 21): needed so the Ø18 pad/tube stays 1 mm inside the flange at the lead's
   fastener positions; 8 mm larger each way than with the first draft's 12 mm borders.
