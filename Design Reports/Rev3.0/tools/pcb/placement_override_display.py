# Display region, layout pass 2 (display agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# The 14 RGB/sync lines of U10's bottom row / left column run east under U10 at y 79.0..84.2 and sweep NE into the corridor,
# so the 1.2 V regulator group moves below that band (x 55.9..65.5, y 84.4..96).
put('U31', 59.8, 89.0, 90)         # LD1117-1.2 rot 90: tab (OUT) north at y 85.85 (1V2 via -> B.Cu straight up to pin 46's via), pins south
put('C337', 65.0, 85.85, 0)        # 1V2 out 0603 next to the tab (pad 1 west), GND via east
put('C336', 59.8, 95.0, 0)         # 1V2 out 10u 0805 at the OUT pin (pin 2), GND pad east
put('C335', 65.0, 93.3, 0)         # 3V3 in at U31.3 (pad 1 west), GND pad east
put('R128', 65.6, 89.4, 270)       # BL_PWM 0R: pad 1 (BL_PWM) north toward the B.Cu crossing from the U10 pocket via
put('R127', 65.6, 91.45, 270)       # BL_EN 100k pull-down under R128 (pad 1 BL_EN north, pad 2 GND south)
# ---- pass 4: J10 / J11 on the TOP side (placement.py: J10 (135.65, 92.0) rot 0 F = pad 1 east at 145.4, entry south; J11 (40.3, 92.0))
# 33R arrays (R_Array_Convex_4x0402: 0.5 mm pin pitch, pins 1-4 west = U10 side, 5-8 east = panel side, pin 1 north), pass 4b:
# grouped in U10 order; at the end of the corridor (first place where the 0.5-mm-pitch band fits), rows y = 63.4 + 0.5 k
# (k = corridor order B2..B7), two staggered columns so the 2.0 x 2.5 courtyards do not touch
for _k, (_x, _y) in enumerate(((107.6, 64.15), (110.2, 66.15), (107.6, 68.15), (110.2, 70.15), (107.6, 72.15), (110.2, 74.15), (107.6, 76.15))):
    put('RN%d' % (_k + 1), _x, _y, 0)
# J10 pins 1/2 (VLED_N/VLED_P, fed from the south by the power agent's under-body vias) -> north stubs, nested east runs at
# y 87.2 (N) / 86.24 (P) to the RF caps; pin 4 (TFT_VDD) north along x 143.9, 45 deg to x 144.4 above R0's column past C132/C123/C122 to R125
put('C129', 147.0, 86.72, 270)     # 100n VLED_P (north pad) - VLED_N (south pad) across the two runs
put('C130', 148.2, 85.76, 90)      # 1n VLED_P (south pad on the P run) - GND (north) -> via
put('C131', 150.0, 87.68, 270)     # 1n VLED_N (north pad on the N run) - GND (south) -> via
put('C132', 144.88, 84.4, 0)        # 1n TFT_VDD (west pad on the pin-4 trunk) - GND (east) -> via
put('C123', 144.88, 82.8, 0)        # 100n TFT_VDD on the trunk, GND east -> via
put('C122', 145.35, 81.0, 0)       # 10u 0805 TFT_VDD on the trunk, GND east -> via
put('R125', 145.3125, 79.0, 180)     # 0R 3V3 -> TFT_VDD: pad 2 (TFT_VDD) west on the trunk, pad 1 (+3V3) east -> In2 3V3 via outside the +5V island (x > 147)
# J11 touch block (pass 4, top side): J11 1.8 E / 0.4 S of the first cut (pass 4b: courtyard clear of R227) (its west anchor was 0.02 mm from R227.1; the LCD_RST
# lead now clears C226).  The four signals come down on B.Cu and change to F.Cu in a staircase of vias right north of the pads
# (the B.Cu column order is the reverse of the top-side pad order); the TVS diodes hang east of those vias; TP_VDD leaves pin 1
# southwards under the body (via) to C133/C126/R129 east of the connector.
put('J11', 42.1, 92.4, 0, 'F')
put('D116', 47.6, 85.0, 180)       # LCD_RST TVS: signal pad west on the via stub, GND pad east -> via
put('D112', 47.6, 87.6, 180)       # SDA TVS
put('D113', 51.2, 86.3, 180)       # SCL TVS
put('D115', 51.2, 88.9, 180)       # TP_INT TVS
put('C133', 48.78, 93.4, 0)        # TP_VDD 1n on the TP_VDD trunk (x 47.0), GND east -> via
put('C126', 48.78, 94.8, 0)        # TP_VDD 100n
put('R129', 49.2125, 96.3, 180)    # +3V3 -> TP_VDD: pad 2 (TP_VDD) west on the trunk, pad 1 (+3V3) east -> In2 3V3 via
