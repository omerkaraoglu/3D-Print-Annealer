# Rev3.0 placement v4, local board coordinates (mm): x right, y down, origin = board top-left corner. Board 164 x 99.
# Mains (230 V): full-width band y < 52 for x > 27 (input filter left, ZCD bridge middle, triac/relay right),
# HLK-10M05 vertical at the right with AC pins up (y=45) and DC pins down (y=87.5) so the module itself straddles the
# isolation boundary.  SELV: ESP32 at the left edge (antenna off the edge), SSD1963 centre-bottom, FPC connectors on the
# back side at the bottom edge, thermocouple front end bottom-left, buck/boost bottom-right next to the PSU DC pins.
W, H = 164.0, 99.0
OX, OY = 20.0, 20.0
P = {}
def put(ref, x, y, rot=0, side='F'): P[ref] = (x, y, rot, side)

# ---------------- ESP32 (antenna out of the left edge) ----------------
put('U3', 13.25, 50.0, 90)         # top row pins 25-38 at y=41.25 (x 24.5..8.0), bottom row pins 1-14 at y=58.75 (x 8.0..24.5), right col 15-24 x=25.75
for ref, n in (('R110', 27), ('R111', 28), ('R118', 29), ('R112', 30), ('R113', 31), ('R114', 33), ('R115', 36), ('R116', 37)):
    put(ref, 24.5 - 1.27 * (n - 25), 39.3, 90)          # 33R at the ESP32 pins; pad1 (ESP32 side) at +y
put('R12', 24.5, 39.3, 270)                                 # IO0 pull-up at pin 25
for ref, n in (('R117', 10), ('R120', 11), ('R119', 12), ('R121', 13)):
    put(ref, 8.0 + 1.27 * (n - 1), 61.4, 270)           # D7/WR/DC/RST, pad1 at the top (ESP32 side)
put('C5', 9.27, 61.4, 270)         # 100n at pin 2 (3V3)
put('C7', 12.5, 64.5, 0)           # 10u
put('C8', 9.3, 64.5, 0)
put('R11', 10.5, 67.5, 0)          # EN pull-up
put('C6', 14.0, 67.5, 180)
put('Q3', 15.0, 71.0, 0)           # auto-reset
put('Q2', 20.5, 71.0, 0)           # auto-boot
put('R14', 11.0, 71.0, 90); put('R13', 24.5, 71.0, 90)
put('J2', 4.5, 10.5, 0)            # FTDI header, left edge
put('R131', 29.5, 45.6, 180)         # SCL pull-up at pin 23
put('R130', 29.5, 42.5, 180)         # SDA pull-up (pin 26 top row)
put('R16', 29.5, 54.4, 180)          # FAN series at pin 16

# ---------------- SSD1963 ----------------
put('U10', 58.0, 70.0, 0)          # left pads x=50.34 (y 63.8..76.2), top y=62.34, right x=65.66, bottom y=77.66
put('C112', 47.2, 65.0, 90); put('C117', 45.6, 68.9, 180)   # display routing: C117 off the left-column bus entry band
put('C110', 47.2, 70.0, 90); put('Y10', 44.2, 73.0, 180); put('C111', 44.2, 76.5, 0)
put('C118', 45.4, 81.2, 90)   # display routing: off the R/B (pins 28-31) west exits
put('C120', 47.2, 78.0, 90); put('C121', 47.2, 81.2, 90)
put('C113', 50.4, 81.2, 180)   # display: GND pad west (pin 33), 3V3 east (pin 34)
put('R124', 54.5, 56.6, 270)        # RD pull-up (pin 121 x=54.6)
put('C119', 58.5, 58.6, 0); put('C115', 61.5, 58.6, 0); put('C116', 66.0, 58.6, 0)
put('C114', 67.5, 62.5, 90)    # display: next to pin 95
put('U31', 64.0, 82.0, 180)        # LD1117-1.2: pins at x=79.15 (GND 65.7 / OUT 68 / IN 70.3), tab (72.85,68)
put('C335', 70.0, 82.0, 270)   # display: 3V3 pad toward U31.3, GND toward U31.1
put('C336', 62.0, 88.0, 0); put('C337', 66.0, 88.0, 0)

# ---------------- FPC connectors (back side, bottom edge) ----------------
put('J10', 135.65, 92.0, 0, 'F')     # pass 4: TOP side, upper-contact connector, 7 mm from the edge for the tail fold (display agent orients: pin 1 east, entry toward the edge)     # mirrored: pin1 (VLED-) x=72.25 ... pin40 x=52.75
put('J11', 40.3, 92.0, 0, 'F')       # pass 4: TOP side, KLS upper-contact     # mirrored: pin1 x=81.25 .. pin6 x=78.75
put('C123', 139.5, 96.0, 0); put('C122', 142.0, 96.0, 0); put('R125', 144.5, 96.0, 0)   # TFT_VDD
put('D113', 45.0, 88.5, 90); put('D112', 47.0, 88.5, 90); put('C126', 49.0, 88.5, 90); put('R129', 51.3, 88.5, 90)

# ---------------- Thermocouple front end (bottom-left) ----------------
put('J20', 6.5, 80.0, 270)         # pins (6.5,80),(6.5,85.08); body x 1..10.8; wires exit left
put('TH220', 12.0, 75.8, 0)
put('D220', 13.0, 78.0, 0); put('D221', 13.0, 87.0, 0)
put('R222', 17.5, 76.0, 0); put('R223', 17.5, 89.0, 0)
put('R220', 18.5, 79.5, 180); put('R221', 18.5, 85.5, 180)
put('C221', 22.5, 76.5, 0); put('C222', 22.5, 88.5, 0)
put('C220', 23.5, 82.5, 270)
put('U20', 29.55, 82.5, 0)
put('C223', 34.5, 80.5, 0); put('C224', 35.0, 78.3, 0)
put('R224', 33.0, 76.0, 0)
put('R225', 29.0, 88.0, 180); put('C225', 33.0, 88.0, 0)
put('R226', 36.0, 85.0, 90); put('R227', 36.0, 90.0, 90); put('C226', 38.5, 87.5, 90)

# ---------------- LV power: buck / boost at the PSU DC pins ----------------
# PS1 DC pins: +5V (134.8, 87.5), GND (157.4, 87.5)
put('C2', 127.5, 80.5, 90)          # 220u bulk: +5V (125.5,90), GND (128,90)
put('U30', 88.0, 74.5, 0)         # TPS562201
put('C332', 88.0, 71.7, 180)
put('L30', 81.5, 75.0, 180)       # SRI0605B, pin1 (SW) toward U30
put('C333', 77.0, 81.0, 90); put('C334', 80.0, 81.0, 90)
put('C330', 86.5, 79.5, 90); put('C331', 89.5, 79.5, 90)
put('R330', 92.5, 73.0, 0); put('R331', 92.5, 76.0, 0)
put('U11', 88.0, 92.5, 0)         # MIC2288
put('L11', 82.5, 89.5, 0)
put('D111', 82.5, 96.5, 0)
put('C125', 77.5, 95.5, 90); put('D114', 77.5, 90.5, 270)   # D114 rot 270 + schematic polarity fix: K (pin 1) on VLED_P at the same pad position
put('R122', 73.0, 90.5, 90); put('R123', 73.0, 94.5, 90); put('R126', 78.5, 86.0, 0)
put('R128', 60.0, 87.0, 0); put('R127', 64.0, 87.0, 0)       # BL_PWM/EN next to the SSD1963 PWM pin
put('L12', 92.0, 87.0, 0); put('C127', 96.0, 87.5, 90); put('C124', 88.0, 86.0, 90)
put('R132', 83.5, 84.5, 0); put('C128', 72.0, 84.5, 0)

# ---------------- Isolation boundary parts (SELV side, y >= 55) ----------------
put('R4', 101.0, 57.5, 90)
put('U5', 105.0, 55.0, 90)         # MOC3053 rot90: pins 1-3 SELV at y=55 (x 105..110.08), 4-6 mains at y=47.38
put('U1', 121.5, 47.38, 270)       # 4N28 rot270: pins 1-3 mains at y=47.38 (x 121.5,118.96,116.42), 4-6 SELV at y=55
put('R8', 118.0, 59.5, 90); put('U6', 122.0, 61.5, 0); put('R9', 126.5, 60.0, 0); put('R10', 126.5, 62.5, 0)
put('Q4', 82.0, 57.5, 0); put('D5', 86.5, 57.5, 180); put('R15', 78.0, 57.5, 0)   # relay driver, coil pins at (73.95/86.05, 46.05)

# ---------------- Mains band (y < 52) ----------------
put('PS1', 150.0, 5.0, 270)        # pass 4: HLK-10M05 moved to the top-right corner: AC L (150,5), N (142.2,5) at the top edge; DC GND (157.4,47.5), +5V (134.8,47.5); body x 130.6..161.6, y 1.2..51.3 -> J10 fits on the top side
put('J3', 123.4, 3.5, 180)            # mains in: LINE (30,3.5), NEUT (37.8,3.5)
put('F1', 70.5, 5.0, 180)            # LINE (44/49.2,5) .. LINE_FUSED (59.3/64.5,5)
put('L40', 42.0, 21.0, 0)          # 120u radial: LINE_FILT (38.5,21), LINE_FUSED (47.5,21)
put('C40', 70.5, 13.5, 0)          # 1u X2: LINE_FILT (59.25,12.5), NEUT (86.75,12.5)
put('C1', 73.0, 22.5, 0)           # 100n X2: LINE_FILT (65.5,22.5), NEUT (80.5,22.5)
put('RV1', 56.0, 26.0, 0)          # MOV: LINE_FILT (60,29.5), NEUT (67.5,30.9)
put('L1', 93.5, 20.0, 0)           # CM choke: NEUT (92.5,24), PS1-N (99.5,24), PS1-L (99.5,16), LINE_FILT (92.5,16)
put('R7', 155.7, 15.1, 180)          # 33k: PS1-N (104,24) .. D1-K (119.24,24)
put('R6', 151.7, 10.0, 180)          # 33k: PS1-L (104,16) .. D3-A (119.24,16)
put('D3', 126.3, 27.9, 0)        # bridge, vertical: D3 bottom D2-K / top D3-A (113,28)
put('D4', 136.46, 31.3, 180)        # top D3-A / bottom D1-A
put('D1', 136.46, 36.0, 180)        # top D1-K / bottom D1-A
put('D2', 126.3, 39.4, 0)        # bottom D2-K / top D1-K
put('K1', 70.0, 48.0, 90)          # relay rot90: COM (80,48), coil (86.05,46.05)/(73.95,46.05), NO (86.05,33.85), NC (74,33.8); body x 72..88, y 29.7..49.9
put('J4', 83.0, 3.5, 0)            # fan wires: NO (93,3.5), NEUT (100.8,3.5)
put('F3', 107.42, 16.1, 0)           # Q1-A2 (105/110.2,5) .. LINE (120.3/125.5,5)
put('HS1', 112.62, 33.6, 0)          # Fischer SK 409 63,5 STC: plate centre; TO-220 at (x-2.54, y+4.7)
put('Q1', 110.08, 38.3, 0)          # BTA12 vertical: A1 (138,24), A2 (140.54,24), G (143.08,24); heatsink box x 126..150, y 10..22
put('R3', 98.5, 45.7, 180)          # 360R: U5.6 (104,43) .. A2 (116.7,43)
put('R2', 102.46, 44.1, 0)        # gate 360R: A1 (158,27) .. G (145.3,27)
put('R1', 102.32, 3.5, 0)           # heater wires: A1 (140,3.5), NEUT (147.8,3.5)
put('RV2', 98.0, 37.1, 180)         # across triac: A2 (152,32), A1 (159.5,33.4)
put('R5', 83.5, 41.1, 0)         # snubber 47R: C4n (156.5,20) .. A2 (156.5,4.76)
put('C4', 83.5, 31.9, 0)         # snubber 10n X2: C4n (161.5,20) .. A1 (161.5,10)

# ---------------- pass-2 region overrides: one file per routing agent (placement_override_<region>.py), applied in name order ----------------
# pass 4 first-cut positions (display agent re-places in placement_override_display.py)
for _k in range(7): put('RN%d' % (_k + 1), 73.0, 60.5 + 1.8 * _k, 90)   # 33R x4 arrays at the start of the RGB ribbon (0.8 mm pin pitch)
put('C129', 139.5, 89.0, 0); put('C130', 142.0, 89.0, 0); put('C131', 144.5, 89.0, 0); put('C132', 147.0, 89.0, 0)   # RF return caps at J10
put('C133', 53.5, 88.5, 90); put('D115', 56.0, 88.5, 90); put('D116', 58.5, 88.5, 90)   # TP_VDD 1 nF, ESD on TP_INT / LCD_RST at J11
import os as _os, glob as _glob
for _f in sorted(_glob.glob(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "placement_override_*.py"))):
    exec(open(_f, encoding="utf-8").read())
