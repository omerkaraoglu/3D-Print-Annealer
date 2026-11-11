# LV power region, layout pass 2 (power agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# Box x 70..100, y 71..98.5 (mounting hole H at (97, 95.5) takes the south-east corner).  North band: MIC2288 boost + pi filter,
# output to the east (VLED pair drops to B.Cu at the east edge); south band: TPS562201 buck, 3V3 output to the west (In2 3V3 vias
# at x < 70).  C2 at the PSU +5V pin.
# ---- boost core: L11 straight under U11 (VIN pad under pin 5, SW pad under pin 1), D111 east of U11 (anode at the SW row),
#      C125 east of D111.K, its GND next to U11.2's via -> hot loop SW -> D111 -> C125 -> GND about 6.5 x 4 mm
put('U11', 84.0, 77.0, 180)        # MIC2288: EN/VIN pins face west (EN toward R127/R128), SW/GND/FB face east
put('L11', 83.9125, 81.35, 0)       # pads under U11.5 (VIN) and U11.1 (SW)
put('D111', 88.6, 76.35, 270)      # SS14: A (SW) at y 78.35 level with the SW junction, K (VLED_P) at y 74.35
put('C125', 91.6, 75.3, 270)       # output cap: VLED_P pad on the D111.K line, GND pad toward U11
put('D114', 94.2, 76.0, 270)       # 15 V clamp: K on the VLED_P line, A to GND
put('R122', 96.5, 80.0, 270)       # LED current sense (VLED_N -> GND) at the boost output, next to the pair vias
put('R123', 98.5, 80.0, 270)
put('R126', 85.1375, 73.8, 90)      # 0R FB link right above U11.3 (FB stub 1.7 mm), Kelvin from R122.1 along the box top
# ---- input pi filter (west of the core, south of the display's RGB sweep): +5V -> C127 -> L12 -> BL_VIN (C124) -> U11.5 / L11.1;
#      damper R132 + C128 across BL_VIN east of the core
put('C124', 80.05, 80.0, 270)      # 10u at the BL_VIN node between L12 and L11
put('R132', 86.6, 86.0, 0)         # damper R east of the core (the display RGB sweep takes the box's NW corner x 70..80, y 71..81): BL_VIN pad 45 deg from L11.1
put('C128', 93.0, 86.0, 0)         # damper 47u in the free area east of L11 / north of the hole, + pad toward R132.2
put('L12', 76.45, 82.3, 270)       # pi-filter 2.2u: BL_VIN pad up (toward C124.1), +5V pad down; courtyard >= 1 mm from the RGB sweep (B7 lane x + y = 151.32)
put('C127', 72.4, 83.3, 90)        # +5V side 10u, island vias under its +5V pad; courtyard >= 1 mm from the RGB sweep
# ---- buck (south band): pass-1 local geometry, 3V3 output caps at the west edge -> In2 3V3 vias at x 68.3
put('U30', 82.8, 89.5, 0)          # TPS562201
put('C332', 82.8, 86.7, 180)       # bootstrap
put('L30', 76.3, 90.0, 180)        # SRI0605B, pin 1 (SW) toward U30
put('C330', 81.3, 94.5, 90); put('C331', 84.3, 94.5, 90)       # input caps, GND pads toward the IC, +5V bar + island vias below
put('R331', 86.9, 91.8, 0); put('R330', 86.9, 93.2, 180)      # FB divider at U30.4 (FB stub < 3 mm), 3V3 sense from C334.1
put('C333', 71.8, 96.0, 90); put('C334', 74.8, 96.0, 90)      # output caps, +3V3 bar at y 96.95 -> west to the 3V3 vias
# ---- bulk at the PSU +5V pin
put('C2', 126.5, 72.6, 90)   # reviewer 2026-11-11: moved north (display agent: at (127,88) its pads cut 10 B.Cu RGB rows); pads +5V (126.5,72.6) / GND (126.5,70.1) on the In2 island / In1         # 220u radial at the bottom of its window, 7.8 mm west of the PSU +5V pin: both pads THT on the In2 +5V island / In1 GND (no track: the J10 RGB fan-in runs between C2 and PS1.4); the RGB band passes north of it, the DE..PCLK drops (x >= 128.9) pass east of its pads; courtyard clear of PS1 (x 130.56)
