# Mains region, layout pass 3 (mains agent).  Executed by placement.py after its own list; put(ref, x, y, rot[, side]).
# Pass 3b: heater (R1) and fan (J4) wire pads back on the top edge.
# Pass 3: the LC filter (F3 main fuse -> L40 RC1415U -> C40/C1/RV1) sits at the mains input and feeds everything (heater, fan
# relay, PSU branch F1 -> L1).  West block: F3 / J3 on the top edge, L40 and C40 under them, heater wire pads R1 south of the
# LINE_FILT trunk; the trunk runs east on B.Cu and drops straight into Q1.A2 under the Fischer SK 409 heatsink (as pass 2).
# PSU block (F1 -> L1 -> PS1, R6/R7) moves east next to PS1; heatsink, triac drive, snubber and ZCD ladder keep pass-2 places.
put('F3', 63.0, 3.5, 0)       # main fuse on the top edge: LINE clip (78.3/83.5) at J3.L, LINE_FUSED clip (63.0/68.2) above L40.2
put('J3', 87.76, 3.5, 0)      # mains wire pads: L 87.76 (-> F3, 4 mm), N 95.56 (-> R1.N by one 45 deg run)
put('L40', 64.75, 15.1, 180)  # 100 uH / 5 A RC1415U: LINE_FUSED pad (61.0) below F3.1a, LINE_FILT pad (68.5) east toward C40.1
put('C40', 90.0, 12.5, 0)     # 1 uF X2 right at L40's output: LINE_FILT 76.25 (7.8 mm from L40.1), NEUT 103.75 next to R1.N
put('R1', 109.0, 3.5, 180)    # heater wire pads on the top edge next to J3: N 101.2 (5.6 mm from J3.N), A1 109.0 (A1 trunk drops on B.Cu)
put('J4', 50.5, 3.5, 0)       # fan wire pads on the top edge west of F3: NO 50.5 (-> K1 NO west of L40), N 57.5 (B.Cu NEUT under F3/J3)
put('C1', 129.7, 3.5, 180)    # 100 nF X2 on the top edge east of R1: NEUT 114.7, LINE_FILT 129.7 (fed from F1.1 on B.Cu)
put('RV1', 90.0, 21.0, 0)     # input MOV south of the LINE_FILT trunk: LINE_FILT 90.0 on the trunk, NEUT 97.5 (B.Cu from C40.2)
put('F1', 112.75, 21.0, 0)    # 1 A PSU fuse south of the trunk: its LINE_FILT clip (112.75) is the trunk's F.Cu -> B.Cu change (same clip as F3), PSU_L -> L1.4
put('L1', 143.0, 15.5, 0)     # CM choke next to PS1: PSU_L/NEUT west, AC/L / AC/N east
put('R6', 156.0, 9.5, 270)    # ZCD 33k taps stood up at the right edge: AC side on top, ladder side below
put('R7', 161.0, 9.5, 270)
# unchanged from pass 2 (heatsink, triac drive, snubber, ZCD ladder)
put('HS1', 112.75, 31.95, 0); put('Q1', 110.21, 36.65, 0)
put('C4', 80.3, 37.04, 90); put('RV2', 84.7, 36.0, 90); put('R5', 83.6, 41.35, 0); put('R3', 98.5, 45.9, 180); put('R2', 102.59, 44.0, 0)
put('D3', 137.2, 27.9, 0); put('D4', 147.36, 31.3, 180); put('D1', 147.36, 36.0, 180); put('D2', 137.2, 39.4, 0)
