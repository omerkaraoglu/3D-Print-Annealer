# Rev3.0 controller board — layout pass 2 (common brief for the three region agents)

Read `AGENT_BRIEF.md` first (working folder, helper, coordinates, what "orderly" means, deliverables). This file says what
changed since pass 1 (commit 8b0cc13, DRC-clean) and how the regions are split now. Local board mm everywhere (origin top-left,
x right, y down, board 164 × 99; KiCad adds 20 mm to both).

## Why there is a pass 2
1. The 7" panel's TFT FPC tail is at the RIGHT end of the bottom edge (board x 125.4..145.9, pin 1 on the right, lower-contact
   Connfly DS1020-09-40VBT1A as before) and the touch (CTP) tail at the left (board x ≈ 40, pin 1 on the right, DS1020-09-06VBT1A).
   Pass 1 had J10 at x 53..72 and J11 at x 79..84. **J10 is now at (135.65, 94.6) B.Cu, J11 at (40.3, 94.6) B.Cu** (placement.py).
2. The heater is 1 kW (4.35 A RMS). The triac is now **BTA24-800CWRG** (same TO-220 footprint/pinout, Rth(j-c) 1.7 K/W) on a
   Fischer **SK 409 63,5 STC** heatsink (**HS1**, new footprint `Rev3:Heatsink_Fischer_SK409_63.5_STC`: 45 × 12.7 mm standing
   63.5 mm tall, two solder pins Ø2.3 at x ±17.75 from the plate centre, F.Cu keep-out zones under the fins and the plate are in the
   footprint). Q1 sits on the plate: **Q1 at (HS1.x − 2.54, HS1.y + 4.7) rot 0**. First cut: HS1 (112.62, 33.6), Q1 (110.08, 38.3)
   — this overlaps the bridge D1/D2 and the snubber R5; the mains agent re-places.
3. Because J10 moved to the right, the LV power block (buck U30/L30, boost U11/L11, pi filter, VLED sense, C2) moves WEST to
   **x 70..100, y 71..98.5** (first cut = old positions shifted by (−24, +4.5); the power agent re-places inside that box) and the
   24+4 RGB/sync lines run from U10 eastward to J10 through the freed area. U31 (LD1117-1.2) + C335/C336/C337 moved south of U10.
4. The In2 +5 V island is now x 70..140, y 70..98 (`build_board.py`); everywhere else In2 is 3V3.

## Unchanged (do not re-route, do not move)
ESP32 U3 + 33 R resistors + FTDI J2 + auto-reset; the 8080 bus to U10 (planar, pass-1 `tracks_display.json` stages 1–2);
the thermocouple block (J20/U20/… bottom-left, x 1..39, y 75..91); the relay K1 and its driver Q4/D5/R15; the ISO parts U1/U5/U6
and R4/R8/R9/R10; PS1 (HLK-10M05); mains input filter (J3, F1, L40, C40, C1, RV1, L1, R6/R7, J4). `tracks_signals.json` (ESP32,
TC, FTDI, relay driver, ZCD SELV side, FAN) stays as it is **except the nets I2C_SCL, I2C_SDA, TP_INT and /Display/TP_VDD, which
the display agent strips from it and re-routes** (they went to the old J11 position). Pass-1 track files are kept as
`tracks_<region>_p1.json` for reference; `tracks_signals.json` (minus those four nets) is an `extra_json` input for everyone.

## Regions, owners, corridors
| region | owner | parts | area |
|---|---|---|---|
| display | display agent | U10 fan-out/decoupling (keep pass-1 stage 1), 8080 bus (keep pass-1 stage 2), RGB/sync fan-in to J10, LCD_RST, U31 + C335/C336/C337 (1V2), R128/R127 (BL_PWM/BL_EN stubs to the boost's edge), J10 companions C122/C123/R125 (TFT_VDD), J11 + D112/D113/C126/R129, I2C_SDA/SCL (ESP32 pull-ups → U20 → J11), TP_INT | U10 block x 40..70, y 56..90; **RGB corridor y 60..71 from x 66 to x 100, then x 100..124 down to J10**; J10 fan-in x 122..150, y 80..98.5; J11 block x 36..54, y 85..98.5 |
| power | power agent | U30, C332, L30, C333/C334, C330/C331, R330/R331, U11, L11, D111, C125, D114, R122/R123, R126, L12, C127, C124, R132, C128, C2; nets +5V, +3V3 (buck out → In2 vias), BUCK_*, BL_* (except the two stubs at R128/R127), VLED_P/VLED_N to J10 pins 1/2 (x ≈ 145.4/144.9, y ≈ 92.3 on B.Cu) | **x 70..100, y 71..98.5** for the parts (C2 next to the PSI +5V pin at x 124..129, y 76..90); VLED pair along the bottom strip y 93..98 or B.Cu |
| mains | mains agent | HS1 + Q1 and everything in the 230 V band that has to move for the heatsink (D1–D4, R2, R3, R5, C4, RV2, F3, R1 wires, J4 if needed); all mains nets (`tracks_mains.json` regenerated) | the mains band (Cmts.User boundary); the SELV parts U1/U5 straddling the boundary stay |

Keep ≥ 1 mm between the corridor's outermost track and another region's parts. If you must cross another region's area, say so.

## Placement edits (new mechanism)
`placement.py` applies every `placement_override_<region>.py` it finds (name order) after its own list. Put your part moves in
**your** override file only (`put('REF', x, y, rot[, 'B'])` lines, with a one-line reason each), never edit `placement.py`,
`build_board.py`, `netclasses.py` or project files. Rebuild **your own** placed board after each change:
```
"C:/Program Files/KiCad/10.0/bin/python.exe" build_board.py rev3_placed_<region>.kicad_pcb
"C:/Program Files/KiCad/10.0/bin/python.exe" export_geom.py rev3_placed_<region>.kicad_pcb geom_<region>.json
"C:/Program Files/KiCad/10.0/bin/python.exe" overlap.py rev3_placed_<region>.kicad_pcb      # courtyard overlaps (ignore H/H and U3 off-board)
R = Router("geom_<region>.json", placed="rev3_placed_<region>.kicad_pcb")
```
(The HS1/Q1 courtyard overlap is intentional; the mains agent keeps Q1 on the plate.) Other agents' override files are picked
up too, so your build sees their current placement; re-run the three commands before your final check.

## Rules added for pass 2 (in the .kicad_dru, already active)
- `heatsink_pins_vs_mains`: HS1 pads ≥ 2.5 mm from any mains copper; `heatsink_pins_vs_selv`: ≥ 6.4 mm from any SELV copper.
  (The triac's own leads are 15 mm from the pins.) The heatsink is floating metal on the insulated BTA24 tab.
- Everything in `AGENT_BRIEF.md` still holds (0/45/90°, two-45° turns, pad-centre ends, return vias ≤ 1.5 mm, bus pitch 0.4–0.5).

## Deliverables (per agent)
`route_<region>.py` (idempotent, builds the whole region), `tracks_<region>.json`, `placement_override_<region>.py`, PNG crops
of every part of the region at ≥ 300 dpi that you have looked at yourself, and a report: nets routed, DRC for your nets
(0 violations / 0 unconnected expected, with the other regions' current track files as `extra_json`), vias per net, bus/RGB
lengths, parts moved (with reasons), anything you could not solve. Work in small saved stages (a single reply over the output
limit loses everything); if you are cut off, continue from the saved files.
