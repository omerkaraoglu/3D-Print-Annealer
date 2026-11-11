# Display pass 2 - stage 0: RGB lane mapping for the U10 -> J10 fan-in

Board: `rev3_placed_display.kicad_pcb` / `geom_display.json` (pass-2 placement, no overrides yet). Local mm.
Script: `d2_lanes.py` (reads `rev3.net` pin functions and the J10 pad geometry).

## Geometry (geom)
U10 SSD1963 at (58, 70) rot 0, LQFP-128 0.4 mm. Counter-clockwise pin numbering: left column 1..32 (x 50.34, y down),
bottom row 33..64 (y 77.66, x up), right column 65..96 (x 65.66, y up), top row 97..128.

| U10 pin | function | net (current schematic) | pad (x, y) |
|---|---|---|---|
| 86 | LDATA18 | B2 | 65.66, 67.80 |
| 85 | LDATA19 | B3 | 65.66, 68.20 |
| 81..76 | LDATA0..5 | R0..R5 | 65.66, 69.80 .. 71.80 |
| 72, 71 | LDATA6, 7 | R6, R7 | 65.66, 73.40 / 73.80 |
| 70..67 | LDATA8..11 | G0..G3 | 65.66, 74.20 .. 75.40 |
| 63..60 | LDATA12..15 | G4..G7 | 63.80 .. 62.60, 77.66 |
| 59 | LDATA16 | B0 | 62.20, 77.66 |
| 51 | PWM | BL_PWM (not in the bundle) | 59.00, 77.66 |
| 49 | LDEN | DE | 58.20, 77.66 |
| 45 | LSHIFT | PCLK | 56.60, 77.66 |
| 44 | LLINE | HSYNC | 56.20, 77.66 |
| 43 | LFRAME | VSYNC | 55.80, 77.66 |
| 35 | LDATA17 | B1 | 52.60, 77.66 |
| 31..28 | LDATA20..23 | B4..B7 | 50.34, 75.80 .. 74.60 |

J10 (Connfly DS1020-09-40VBT1A) at (135.65, 94.6) on B.Cu, pads 0.3 x 1.8 at y 91.725 (90.83..92.63), pitch 0.5,
pin 1 at the east:

| pins | 1 | 2 | 3 | 4 | 5..12 | 13..20 | 21..28 | 29 | 30 | 31 | 32 | 33 | 34 | 35 | 36 | 37..40 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| net | VLED_N | VLED_P | GND | TFT_VDD | R0..R7 | G0..G7 | B0..B7 | GND | PCLK | NC | HSYNC | VSYNC | DE | NC | GND | NC (touch XR/YD/XL/YU) |
| x | 145.40 | 144.90 | 144.40 | 143.90 | 143.40..139.90 | 139.40..135.90 | 135.40..131.90 | 131.40 | 130.90 | 130.40 | 129.90 | 129.40 | 128.90 | 128.40 | 127.90 | 127.40..125.90 |

## Topology
The bundle leaves U10 eastward (corridor y 60..71), turns south at x 100..124 and enters J10's pad row from the north-west.
Following the ribbon (right turn, then left turn, then each line drops south into its pad), the line that is
north-most when leaving U10 ends at the east-most pad. So a crossing-free fan-in needs the U10 perimeter order
(right column top -> bottom, bottom row east -> west, left column bottom -> top) to equal the J10 order east -> west:
R0..R7, G0..G7, B0..B7, PCLK, HSYNC, VSYNC, DE.

## Comparison (pairwise crossings = inversions between the two orders)

| mapping | ribbon order leaving U10 (north -> south) | pairwise crossings | largest crossing-free subset |
|---|---|---|---|
| **current** (LDATA23..16 -> B7..B0, LDATA7..0 -> R7..R0, firmware TFT_BGR) | B2 B3 \| R0..R7 G0..G7 B0 \| DE PCLK HSYNC VSYNC \| B1 B4 B5 B6 B7 | **59** | **22 of 28** |
| uncrossed (LDATA23..16 -> R7..R0, LDATA7..0 -> B7..B0) | R2 R3 \| B0..B7 G0..G7 R0 \| DE PCLK HSYNC VSYNC \| R1 R4..R7 | 187 | 13 of 28 |

The SSD1963 has no bit-reversal option (0x36 only swaps R/B), so G must stay on LDATA15..8 and every colour must keep
its bit order; the two rows above are the only firmware-supported choices.

## Decision
**The current netlist is the best mapping - no schematic change.** With it, 17 lines (R0..R7, G0..G7, B0) leave the
right column / bottom-right corner already in J10 order, and B1, B4..B7 follow in order. Only six lines are out of
place: B2/B3 (top of the right column, must land between B1 and B4) and the four syncs (DE, PCLK, HSYNC, VSYNC; they
must land west of B7, with DE west of VSYNC). These six crossings are resolved in the J10 via field, using each
line's single F.Cu -> B.Cu via (J10 is on B.Cu, so every line needs that via anyway): the long run of every line stays
on F.Cu over the In1 GND plane, and only short B.Cu runs next to J10 pass under the neighbouring F.Cu lines.
The uncrossed mapping would cross the whole blue byte over the green byte (187 crossings) and is rejected.
