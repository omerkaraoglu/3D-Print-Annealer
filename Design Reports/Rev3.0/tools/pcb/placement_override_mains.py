# Mains region, layout pass 4 (mains agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# Pass 4: PS1 sits in the top-right corner, so the PSU/ZCD block that lived at x 130..163 moves next to it, the triac goes on the
# heatsink's NORTH face (Q1 rot 180), the input filter (F3 -> L40 -> C40/C1/RV1) moves to the west end and the H11AA1 replaces
# the 4N28 + D1..D4 bridge (R6/R7 feed U1.1/U1.2 directly).  Heater loop: J3.L -> F3 -> L40 -> LINE_FILT trunk (F.Cu, y 12.8,
# then straight down x 103.0 into Q1.2) / Q1.1 -> A1 trunk (F.Cu, straight down x 108.0 from R1.1) / R1.N -> J3.N on the top edge.
# Triac drive parts are "rungs" across the two vertical trunks (or hang off the LINE_FILT trunk to the west); everything east of
# the A1 trunk is the PSU/ZCD block: L1 top right at PS1's AC pins, R7/R6 under it, F1 straddling the A1 trunk.
#
# top edge (wire pads and the main fuse), west to east
put('J4', 49.9, 3.5, 0)       # fan wire pads: NO 49.9 (B.Cu down the west side to K1 NO), N 56.9 (2.6 mm from the LINE_FUSED clip link)
put('F3', 62.4, 3.5, 0)       # main fuse: LINE_FUSED clips 62.4/67.6 (67.6 drops straight into L40.2), LINE clips 72.7/77.9 next to J3.L
put('J3', 87.0, 3.5, 0)       # mains wire pads: L 87.0 (9.1 mm to F3.2b), N 94.8 (5.4 mm to R1.N)
put('R1', 108.0, 3.5, 180)    # heater wire pads: N 100.2 (heater return to J3.N on the top edge), A1 108.0 = top of the A1 trunk
# west end: input filter (approved option 2)
put('L40', 72.3, 15.1, 180)   # RC1415U: LINE_FUSED 68.55 under F3.1b, LINE_FILT 76.05 -> trunk; x >= 72.25 keeps its round courtyard off C40
put('C40', 47.0, 13.0, 180)   # 1 uF X2 west of L40: LINE_FILT 60.75 (y 18 bus from L40.1), NEUT 33.25 (>= 6.4 mm from the LV edge x 25.5)
put('C1', 48.2, 21.4, 180)    # 100 nF X2 under C40: LINE_FILT 48.2, NEUT 33.2 (6.5 mm creepage to x 25.5)
put('RV1', 44.0, 28.0, 180)   # 14 mm MOV under C1: LINE_FILT 44.0 / NEUT 36.5; pads >= 6.4 mm from the LV edge y 35.5
# heatsink + triac (decision 1): HS1.x 103.0 so that (a) F1's PSU_L clip clears R7's AC/N pad by 2.5 mm east of the A1 trunk
# and (b) the /ZCD_L line to U1.1 still passes heatsink pin 2 at >= 2.5 mm (needs HS1.x >= 102.9)
put('HS1', 103.0, 39.3, 0)    # envelope x 80.5..125.5 (2.6 mm from K1, 5.1 mm from PS1); pins (85.25, 39.3) / (120.75, 39.3)
put('Q1', 105.54, 34.6, 180)  # north face, rot 180 at (HS1.x + 2.54, HS1.y - 4.7): G 100.46, LINE_FILT 103.0, A1 105.54
# triac drive: west-hanging parts on the LINE_FILT trunk (y 12.8) and rungs across the two vertical trunks
put('R3', 84.5, 25.5, 90)     # 360R MOC feed: LINE_FILT pad on the trunk (84.5, 12.8), R3-P1 pad 25.5 -> B.Cu under the heatsink to U5.6
put('R5', 89.0, 28.04, 90)    # snubber R: LINE_FILT pad on the trunk (89.0, 12.8), C4-node pad 28.04 -> C4.1
put('RV2', 100.5, 12.5, 0)    # triac MOV rung: LINE_FILT 100.5 at the trunk corner, A1 on the A1 trunk (108.0, 13.9)
put('F1', 97.6, 20.4, 0)      # PSU fuse rung: LINE_FILT clips 97.6/102.8 (on the descent), PSU_L clips 112.9/118.1 east of the A1 trunk
put('C4', 98.25, 25.5, 0)     # snubber C rung: C4-node 98.25 (2.5 mm from the descent), A1 108.25 on the A1 trunk
put('R2', 110.6, 29.8, 180)   # gate-A1 resistor rung: G 97.9 (-> Q1.3), A1 110.6 (stub to the trunk)
# PSU / ZCD block between the A1 trunk and PS1
put('L1', 123.5, 9.0, 0)      # CM choke at PS1's AC pins: PSU_L (120,5) / NEUT (120,13) west, AC/L (127,5) / AC/N (127,13) east
put('R7', 123.0, 20.0, 270)   # 33k AC/N tap under L1.2: AC/N 20.0 on top, /ZCD_N 25.08 below -> U1.2 on B.Cu
put('R6', 128.0, 20.0, 270)   # 33k AC/L tap (fed on B.Cu under PS1's west edge): AC/L 20.0, /ZCD_L 25.08 -> U1.1 on B.Cu
