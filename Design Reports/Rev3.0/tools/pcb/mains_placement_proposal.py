# Rev3.0 mains band re-placement proposal (agent "mains").  Local board mm, rot in degrees (KiCad convention).
# Concept: heater loop local around U5 (J3 -> F3 -> Q1 -> R1 on the top edge right above the triac, gate 9-10 mm to U5.4),
# PSU feed (1.0 mm L/N) from J3 west to the unchanged input filter, PS1 AC pair east between F3 and the heatsink,
# right of the ZCD ladder to PS1; ladder bridge right of the heatsink next to U1; snubber/R3/R2 left-below the triac.
def put(ref, x, y, rot=0, side='F'): P[ref] = (x, y, rot, side)
P = {}
# top edge wire pads: R1 [A1 | N] + J3 [N | L]  (J3.N next to R1.N -> 5 mm NEUT heater link along the edge)
put('R1', 102.32, 3.5, 0)      # TWEAK2 (+0.3): A1 (102.32,3.5)  N (110.12,3.5) - A1 trunk 2.8 mm from L1.3 instead of 2.50
put('J3', 123.4, 3.5, 180)     # TWEAK2 (+0.3): L (123.4,3.5)    N (115.6,3.5)
put('J4', 83.0, 3.5, 0)        # TWEAK2: fan NO (83,3.5) west, N (90,3.5) east - NO drops west of C40.2, N stub to C40.2 east of it
# PSU input filter (left), F1 turned so its LINE clips face the feed coming from J3
put('F1', 70.5, 5.0, 180)      # LINE (70.5/65.3,5)  LINE_FUSED (55.2/50,5)
put('L40', 42.0, 21.0, 0)
put('C40', 70.5, 13.5, 0)
put('C1', 73.0, 22.5, 0)
put('RV1', 56.0, 26.0, 0)      # moved up-left out of the relay's new place
put('L1', 93.5, 20.0, 0)
put('K1', 70.0, 48.0, 90)      # COM (70,48); coil +5V (76.05,46.05), D5-A (64.05,46.05) - reached from y>48; NO (76.05,33.85); NC (64,33.8)
# heater fuse and triac (pins down toward U5, heatsink behind)
put('F3', 107.42, 16.1, 0)     # A2 (107.42/112.62,16.1)  LINE (122.72/127.92,16.1)
put('Q1', 110.08, 38.3, 0)     # A1 (110.08,38.3) A2 (112.62,38.3) G (115.16,38.3); G 9.9 mm to U5.4
HEATSINK = (100.62, 24.3, 124.62, 36.3)   # 24 x 12 behind Q1, F.Cu copper-free, no parts
Q1_FANOUT = (106.58, 35.3, 118.68, 43.3)  # same offsets as the current q1_fanout rule area (-3.5..+8.6, -3..+5)
K1_PINS = (60.5, 30.5, 79.5, 51.5)       # k1_pins rule area moved with K1 (same offsets as now)
# triac drive, snubber, MOV (left-below the triac, in the space freed by moving K1 left)
put('R2', 102.46, 44.1, 0)     # TWEAK2: A1 (102.46,44.1)  G (115.16,44.1) straight below Q1.G (frees the DC links to U1)
put('R3', 98.5, 45.7, 180)     # TWEAK2: R3-Pad1 (98.5,45.7) -> U5.6 ; A2 (85.8,45.7)
put('RV2', 98.0, 37.1, 180)    # TWEAK2: A2 (98,37.1)  A1 (90.5,35.7)
put('R5', 83.5, 41.1, 0)       # TWEAK2: C4n (83.5,41.1)  A2 (98.74,41.1)
put('C4', 83.5, 31.9, 0)       # TWEAK2: C4n (83.5,31.9)  A1 (93.5,31.9)
# zero-cross ladder right of the heatsink, next to U1: left column DC (to U1), right column AC (from R6/R7)
put('D3', 126.3, 27.9, 0)      # K D2-K (126.3)   A D3-A (136.46)
put('D4', 136.46, 31.3, 180)   # K D3-A (136.46)  A D1-A (126.3)
put('D1', 136.46, 36.0, 180)   # K D1-K (136.46)  A D1-A (126.3)
put('D2', 126.3, 39.4, 0)      # K D2-K (126.3)   A D1-K (136.46)
put('R6', 151.7, 10.0, 180)    # PS1-L (151.7,10)   D3-A (136.46,10)
put('R7', 155.7, 15.1, 180)    # PS1-N (155.7,15.1) D1-K (140.46,15.1)
# SELV boundary (LV pour polygon) - notch at x 92..96 removed, relay pocket moved with K1
LV_BOUNDARY = [(25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8),
               (126.0, 54.8), (130.0, 55.5), (130.0, 80.0)]   # ... continues as before (130,80)->(161,80)->...
