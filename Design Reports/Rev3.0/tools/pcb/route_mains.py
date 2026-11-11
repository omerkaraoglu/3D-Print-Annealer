"""Mains band (230 VAC) - hand routing, Rev3.0 layout pass 2 (agent "mains").  Idempotent: rebuilds tracks_mains.json.
Placement: placement_override_mains.py (Fischer SK 409 heatsink HS1 at (112.75, 31.95), BTA24 Q1 on its plate).
Local board mm.  Layer plan:
  F.Cu  - PSU corridor along the top edge (NEUT y 3.5 / 8.45, LINE y 8.3 / 11.95), input filter, PS1 AC pair
          (AC/L y 20.27, AC/N y 23.77, between F3 and the heatsink), triac drive (gate, R3), A2 snubber bus (y 39.1,
          below the heatsink fins), C4n, ZCD D2-K / D1-A rung links.
  B.Cu  - the two 2.5 mm heater trunks A1 / A2 under the heatsink (TO-220, F3 and R1 pads are THT -> no vias), the A1
          snubber bus (y 26.77) and A1 -> R2, the NEUT drop J4.2 -> C40.2 -> C1.2, the L40 crossing, LINE -> K1 COM,
          J4 -> K1 NO, the ZCD AC feeds from R6/R7 and D1-A to U1, AC/L R6.1 -> PS1.1.
No vias anywhere in the mains band.  Heater path 2.5 mm, necked to 1.6 mm over the last 2.5 mm into the TO-220 pins."""
from handroute import Router
R = Router("geom_mains.json", placed="rev3_placed_mains.kicad_pcb")
H, W, NK = 2.5, 1.0, 1.6
def T(net, layer, pts, w=W): R.track(net, layer, pts, w)
A1, A2, G = "Net-(Q1-A1)", "Net-(Q1-A2)", "Net-(Q1-G)"

# ================= heater loop: J3.1 -> F3 -> Q1.A2 | Q1.A1 -> R1.1 , R1.2 -> J3.2 =================
T("NEUT", "F", [(114.8, 3.5), (120.25, 3.5)], H)                                   # R1.N - J3.N along the edge
T("LINE", "F", [(128.05, 3.5), (128.05, 16.1)], H)                                 # J3.L straight down to F3.2b
T("LINE", "F", [(122.85, 16.1), (128.05, 16.1)], H)                                # F3.2 clip pads
T(A2, "B", [(107.55, 16.1), (112.75, 16.1)], H)                                    # F3.1 clip pads (B: LINE feed passes above)
T(A2, "B", [(112.75, 16.1), (112.75, 34.15)], H)                                   # A2 trunk under the heatsink
T(A2, "B", [(112.75, 34.15), (112.75, 36.65)], NK)                                 # neck into Q1.2
T(A1, "B", [(110.21, 36.65), (107.71, 34.15)], NK)                                 # neck out of Q1.1 (45 deg)
T(A1, "B", [(107.71, 34.15), (102.35, 28.79), (102.35, 8.15), (107.0, 3.5)], H)    # A1 trunk -> R1.1

# ================= PSU corridor (1.0 mm): NEUT under R1.1 to J4.2, LINE 3.5 mm below it to F1 =================
T("NEUT", "F", [(114.8, 3.5), (114.8, 3.84), (110.19, 8.45), (103.81, 8.45), (98.86, 3.5), (90.0, 3.5)])   # 2.5 mm round the square R1.1 pad
T("LINE", "F", [(128.05, 11.95), (102.36, 11.95), (98.71, 8.3), (73.8, 8.3), (70.5, 5.0)])
T("LINE", "F", [(65.3, 5.0), (70.5, 5.0)])                                         # F1.1 clip pads
T("LINE", "B", [(65.3, 5.0), (65.3, 9.4), (70.0, 14.1), (70.0, 48.0)])             # F1.1a -> relay COM (under C40/C1)
T("LINE_FUSED", "F", [(50.0, 5.0), (55.2, 5.0)])                                    # F1.2 clip pads
T("LINE_FUSED", "F", [(50.0, 5.0), (50.0, 17.5), (46.5, 21.0)])                     # -> L40.2

# ================= input filter =================
T("LINE_FILT", "B", [(37.5, 21.0), (45.0, 13.5), (56.75, 13.5)])                    # L40.1 -> C40.1 (under L40)
T("LINE_FILT", "F", [(56.75, 13.5), (55.9, 14.35), (55.9, 25.3), (59.1, 28.5)])     # C40.1 -> RV1.1 (left of RV1.2)
T("LINE_FILT", "F", [(59.1, 28.5), (65.1, 22.5), (73.0, 22.5)])                     # RV1.1 -> C1.1
T("LINE_FILT", "F", [(73.0, 22.5), (77.5, 18.0), (85.9, 18.0), (90.0, 13.9), (90.0, 12.0)])  # C1.1 -> L1.4
T("NEUT", "B", [(90.0, 3.5), (90.0, 5.1), (84.25, 10.85), (84.25, 13.5)])            # J4.2 -> C40.2 under the LINE feed
T("NEUT", "B", [(84.25, 13.5), (84.25, 18.25), (88.0, 22.0), (88.0, 22.5)])         # C40.2 -> C1.2 under the LINE_FILT run
T("NEUT", "F", [(88.0, 22.5), (90.0, 20.5), (90.0, 20.0)])                          # C1.2 -> L1.1
T("NEUT", "F", [(84.25, 13.5), (64.0, 13.5), (60.5, 17.0), (60.5, 21.0)])           # C40.2 -> RV1.2 along C40's pad axis

# ================= fan relay =================
T("Net-(J4-Pin_1)", "B", [(83.0, 3.5), (79.4, 7.1), (79.4, 22.13), (76.05, 25.48), (76.05, 33.85)])  # J4.1 -> K1 NO

# ================= PS1 AC pair (1.0 mm, 3.5 c-c) between F3 and the heatsink =================
T("Net-(PS1-AC/L)", "F", [(97.0, 12.0), (101.5, 16.5), (101.5, 18.77), (103.0, 20.27), (150.0, 20.27), (150.0, 11.7), (151.7, 10.0)])
T("Net-(PS1-AC/L)", "B", [(151.7, 10.0), (151.7, 43.3), (150.0, 45.0)])             # R6.1 -> PS1.1 under the AC/N run
T("Net-(PS1-AC/N)", "F", [(97.0, 20.0), (97.0, 22.27), (98.5, 23.77), (153.9, 23.77), (156.0, 21.67), (156.0, 15.1)])
T("Net-(PS1-AC/N)", "F", [(156.0, 21.67), (156.0, 46.4), (153.2, 49.2), (146.4, 49.2), (142.2, 45.0)])  # round PS1.1 under the module

# ================= ZCD ladder (DC column x 137.2 toward U1, AC column x 147.36 under R6/R7) =================
T("Net-(D3-A)", "B", [(136.46, 10.0), (137.31, 10.85), (147.36, 10.85), (147.36, 27.9), (147.36, 31.3)])   # R6.2 -> AC1 rungs
T("Net-(D1-K)", "B", [(140.76, 15.1), (142.26, 16.6), (142.26, 34.5), (143.76, 36.0), (147.36, 36.0), (147.36, 39.4)])  # R7.2 -> AC2 rungs
T("Net-(D2-K)", "F", [(137.2, 27.9), (139.4, 30.1), (139.4, 37.2), (137.2, 39.4)])   # DC+ rungs (right of the DC column)
T("Net-(D1-A)", "F", [(137.2, 31.3), (137.2, 36.0)])                                # DC- rungs
T("Net-(D2-K)", "F", [(137.2, 39.4), (137.2, 44.56), (134.38, 47.38), (121.5, 47.38)])          # DC+ -> U1.1 along the pin row
T("Net-(D1-A)", "B", [(137.2, 36.0), (135.4, 36.0), (134.9, 36.5), (134.9, 41.1), (131.0, 45.0), (118.96, 45.0), (118.96, 47.38)])  # DC- -> U1.2

# ================= triac drive =================
T(G, "F", [(115.29, 36.65), (115.29, 44.0), (111.91, 47.38), (110.08, 47.38)])     # Q1.G -> R2.2 -> U5.4
T(A1, "B", [(110.21, 36.65), (110.21, 37.0), (103.21, 44.0), (102.59, 44.0)])      # Q1.A1 -> R2.1
T("Net-(R3-Pad1)", "F", [(98.5, 45.9), (99.98, 47.38), (105.0, 47.38)])             # R3.1 -> U5.6

# ================= snubber / MOV =================
T(A2, "F", [(112.75, 36.65), (112.75, 39.1), (87.8, 39.1), (84.7, 36.0)])           # A2 bus under the fins -> RV2.1
T(A2, "F", [(98.84, 39.1), (98.84, 41.35)])                                         # -> R5.2
T(A2, "F", [(98.84, 41.35), (90.35, 41.35), (85.8, 45.9)])                          # -> R3.2 (under R5's body)
T("Net-(C4-Pad1)", "F", [(80.3, 37.04), (80.3, 38.05), (83.6, 41.35)])              # C4.1 -> R5.1
T(A1, "B", [(102.35, 26.77), (87.83, 26.77), (86.1, 28.5)])                         # A1 bus -> RV2.2
T(A1, "B", [(87.83, 26.77), (80.57, 26.77), (80.3, 27.04)])                         # -> C4.2

R.save("tracks_mains.json")
