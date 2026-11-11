# Display region, layout pass 2 (display agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# The 14 RGB/sync lines of U10's bottom row / left column run east under U10 at y 79.0..84.2 and sweep NE into the corridor,
# so the 1.2 V regulator group moves below that band (x 55.9..65.5, y 84.4..96).
put('U31', 59.8, 89.0, 90)         # LD1117-1.2 rot 90: tab (OUT) north at y 85.85 (1V2 via -> B.Cu straight up to pin 46's via), pins south
put('C337', 65.0, 85.85, 0)        # 1V2 out 0603 next to the tab (pad 1 west), GND via east
put('C336', 59.8, 95.0, 0)         # 1V2 out 10u 0805 at the OUT pin (pin 2), GND pad east
put('C335', 65.0, 93.3, 0)         # 3V3 in at U31.3 (pad 1 west), GND pad east
put('R128', 65.6, 89.4, 270)       # BL_PWM 0R: pad 1 (BL_PWM) north toward the B.Cu crossing from the U10 pocket via
put('R127', 65.6, 91.45, 270)       # BL_EN 100k pull-down under R128 (pad 1 BL_EN north, pad 2 GND south)
# J10 TFT_VDD parts on F.Cu south of the pad row: TFT_VDD via south of pin 4 (x 143.6), caps west of it on one F trace at
# y 93.75, R125 east of it with its +3V3 via at x > 146 (In2 3V3, outside the VLED B.Cu strip y 95.4..98.5)
put('C123', 142.6, 94.35, 270)     # 100n: TFT_VDD pad north on the trace, GND pad south -> via (141.85, 94.83)
put('C122', 140.8, 94.6, 270)      # 10u 0805: TFT_VDD pad north on the trace, GND pad south -> via west
put('R125', 147.3, 94.66, 90)      # 0R/ferrite 3V3 -> TFT_VDD: pad 2 (TFT_VDD) north on the trace, pad 1 (+3V3) south
# J11 touch block: the four J11 signals come down x 39.5..41.75, jog SE under the TVS area and enter the pad SOUTH ends from
# y 96..97.2 (order reverses correctly); TP_VDD/GND enter from the north; the TVS sit on SDA/SCL column vias east of the jog
put('D112', 50.0, 91.3, 180)       # SDA TVS: SDA pad west (via on the SDA column at 46.0), GND pad east
put('D113', 50.0, 93.4, 180)       # SCL TVS
put('C126', 43.4, 89.9, 0)         # TP_VDD 100n: pad 1 west to the TP_VDD via (41.85, 89.9), GND via south of pad 2
put('R129', 41.3, 87.6, 270)       # TP_VDD feed: pad 1 (+3V3) north -> via (40.4, 86.69), pad 2 south -> TP_VDD via
