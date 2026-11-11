# Mains region, layout pass 2 (mains agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# Fischer SK 409 63,5 STC heatsink HS1 (45 x 12.7 mm envelope, 63.5 mm tall) with the BTA24 on its plate.  The heatsink sits
# in the band between the PSU AC pair (y 20..24, under F3) and the triac drive row (R2/R3/U5); the heater loop stays
# J3 -> F3 -> Q1 -> R1 with two parallel 2.5 mm trunks (A2 / A1) on B.Cu under the heatsink (as pass 1).
put('J3', 128.05, 3.5, 180)   # mains wire pads +4.65 right: R1 can move right so the NEUT/LINE corridor rises before L1
put('R1', 107.0, 3.5, 0)      # heater wire pads +4.68 right (A1 107.0, N 114.8; N pad 5.45 from J3.N); A1 trunk jogs to x 102.35
put('F3', 107.55, 16.1, 0)    # +0.13: A2 clip 107.55/112.75 (A2 trunk straight down to Q1.2), LINE clip 122.85/128.05 under J3.1
put('L1', 93.5, 16.0, 0)      # CM choke up 4 mm (body bottom 24.5): the heatsink can sit 1 mm below it
put('HS1', 112.75, 31.95, 0)  # heatsink: courtyard clears C1 (x 89.75) / R5 (y 38.85), envelope 1.1 mm from L1, x <= 135.75 for the ladder
put('Q1', 110.21, 36.65, 0)   # BTA24 on the plate (HS1.x - 2.54, HS1.y + 4.7); pins stay in the q1_fanout rule area
# snubber + MOV: left column between the relay K1 and the heatsink (C4, RV2 standing in a row), R5 / R3 rows below
put('C4', 80.3, 37.04, 90)    # A1 pad up (y 27.04, on the A1 bus), C4n pad down -> R5.1
put('RV2', 84.7, 36.0, 90)    # A2 pad down (84.7, 36.0) <- A2 bus, A1 pad up (86.1, 28.5) <- A1 bus
put('R5', 83.6, 41.35, 0)     # C4n (83.6) 7.5 mm clear of the K1 +5V coil pin (SELV), A2 (98.84) on the A2 bus
put('R3', 98.5, 45.9, 180)    # pass-1 x, -> U5.6 along the U5 pin row; A2 end fed under R5's body
put('R2', 102.59, 44.0, 0)    # gate-A1 resistor under Q1 (G pad straight below Q1.3), as pass 1
# ZCD ladder: pass-1 arrangement moved right of the heatsink (DC column toward U1, AC column under R6/R7)
put('D3', 137.2, 27.9, 0); put('D4', 147.36, 31.3, 180); put('D1', 147.36, 36.0, 180); put('D2', 137.2, 39.4, 0)
put('R7', 156.0, 15.1, 180)   # +0.3: AC/L B.Cu drop at x 151.7 keeps 2.5 mm to R7.1 (AC/N)
put('RV1', 59.1, 28.5, 90)    # input MOV stood up left of the relay, NEUT pad on top (60.5, 21): NEUT reaches it above the LINE_FILT run,
                              # so the old NEUT run along y 26.9 (C1 -> RV1) is gone and the column x 78..90 is free for C4/RV2
