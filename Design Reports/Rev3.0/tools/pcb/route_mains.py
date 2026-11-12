"""Mains band (230 VAC) - hand routing, Rev3.0 layout pass 3 (agent "mains").  Idempotent: rebuilds tracks_mains.json.
Placement: placement_override_mains.py.  Pass 3b: heater (R1) and fan (J4) wire pads on the top edge.  Pass 3 topology: J3.L -> F3 (main fuse) -> L40 (RC1415U) -> LINE_FILT, with C40 / C1 /
RV1 to NEUT at the filter output; LINE_FILT feeds the heater (Q1.A2), the fan relay (K1.COM) and the PSU fuse F1 -> PSU_L -> L1.
Local board mm.  Layer plan:
  F.Cu  - LINE / LINE_FUSED on the top edge and down to L40, the 2.5 mm LINE_FILT trunk L40.1 -> y 17.5 -> F1.1a, heater NEUT
          return R1.N -> J3.N on the edge, C40.2 link, NEUT east to L1 (y 13.2), K1.COM drop, PS1 AC pair at L1, ZCD feeds,
          triac drive, LINE_FILT snubber bus (y 39.1, below the heatsink fins), C4n.
  B.Cu  - LINE_FILT from F1.1a (THT fuse-clip pad, same type as F3's heater clips) straight down x 112.75 into Q1.A2, the A1
          trunk from R1.A1 (top edge) down x 109 / 107.6 into Q1.A1, A1 snubber bus, A1 -> R2, NEUT J3.N -> fan (y 8.5/8.0)
          and C40.2 -> RV1.2, F1 -> C1.1, PSU_L, fan NO -> K1, AC/L R6.1 -> PS1.1, AC/N L1.2 -> PS1.2, D1-A -> U1.
No vias anywhere in the mains band (every layer change is at a THT pad).  Heater path 2.5 mm, necked to 1.6 mm over the
last 2.5 mm into the TO-220 pins."""
from handroute import Router
R = Router("geom_mains.json", placed="rev3_placed_mains.kicad_pcb")
H, W, NK, S = 2.5, 1.0, 1.6, 1.5
def T(net, layer, pts, w=W): R.track(net, layer, pts, w)
A1, LF, G = "Net-(Q1-A1)", "LINE_FILT", "Net-(Q1-G)"

# ================= heater loop: J3.L -> F3 -> L40 -> LINE_FILT trunk -> Q1.A2 | Q1.A1 -> R1.A1 , R1.N -> J3.N =================
T("LINE", "F", [(87.76, 3.5), (83.5, 3.5)], H)                                    # J3.L -> F3.2b
T("LINE", "F", [(78.3, 3.5), (83.5, 3.5)], H)                                     # F3.2 clip pads
T("LINE_FUSED", "F", [(63.0, 3.5), (68.2, 3.5)], H)                               # F3.1 clip pads
T("LINE_FUSED", "F", [(63.0, 3.5), (63.0, 13.1), (61.0, 15.1)], H)                # F3.1a -> L40.2
T(LF, "F", [(68.5, 15.1), (70.9, 17.5), (112.75, 17.5), (112.75, 21.0)], H)       # L40.1 -> F.Cu trunk -> F1.1a (layer change)
T(LF, "F", [(76.25, 12.5), (76.25, 17.5)], H)                                     # C40.1 onto the trunk (7.8 mm from L40.1)
T(LF, "B", [(112.75, 21.0), (112.75, 34.15)], H)                                  # F1.1a -> straight down under the heatsink
T(LF, "B", [(112.75, 34.15), (112.75, 36.65)], NK)                                # neck into Q1.2 (A2)
T(A1, "B", [(110.21, 36.65), (107.6, 34.04)], NK)                                 # neck out of Q1.1
T(A1, "B", [(107.6, 34.04), (107.6, 16.4), (109.0, 15.0), (109.0, 3.5)], H)       # A1 trunk up to R1.A1 on the top edge (under the F.Cu trunk)
T("NEUT", "F", [(101.2, 3.5), (95.56, 3.5)], H)                                   # R1.N -> J3.N along the edge

# ================= filter / PSU branch =================
T("NEUT", "F", [(103.75, 12.5), (103.75, 6.05), (101.2, 3.5)], S)                 # C40.2 -> R1.N / J3.N
T("NEUT", "B", [(95.56, 3.5), (95.56, 6.5), (93.56, 8.5), (82.6, 8.5), (82.1, 8.0), (60.0, 8.0), (57.5, 5.5), (57.5, 3.5)])  # J3.N -> fan N (J4.2) under J3 / F3
T("NEUT", "B", [(103.75, 12.5), (103.75, 13.5), (97.5, 19.75), (97.5, 22.4)])     # C40.2 -> RV1.2 under the trunk
T(LF, "F", [(90.0, 21.0), (90.0, 17.5)], S)                                       # RV1.1 onto the trunk
T(LF, "F", [(112.75, 21.0), (117.95, 21.0)], S)                                   # F1.1 clip pads
T(LF, "B", [(117.95, 21.0), (117.95, 15.25), (129.7, 3.5)], S)                    # F1.1b -> C1.1 (top edge) under the NEUT run
T("PSU_L", "F", [(128.05, 21.0), (133.25, 21.0)])                                 # F1.2 clip pads
T("PSU_L", "B", [(133.25, 21.0), (133.25, 17.75), (139.5, 11.5)])                 # -> L1.4 under the NEUT run
T("NEUT", "F", [(103.75, 12.5), (104.45, 13.2), (133.2, 13.2), (139.5, 19.5)])    # NEUT east -> L1.1 (north of the trunk)
T("NEUT", "F", [(114.7, 3.5), (114.7, 13.2)])                                     # C1.2 -> NEUT run
T(LF, "F", [(68.5, 15.1), (69.0, 15.6), (69.0, 47.0), (70.0, 48.0)])              # L40.1 -> fan relay COM
T("Net-(J4-Pin_1)", "B", [(50.5, 3.5), (50.5, 24.0), (55.5, 29.0), (71.2, 29.0), (76.05, 33.85)])  # J4.1 -> K1 NO west of L40

# ================= PS1 AC pair at L1 =================
T("Net-(PS1-AC/L)", "F", [(146.5, 11.5), (148.5, 9.5), (156.0, 9.5)])             # L1.3 -> R6.1
T("Net-(PS1-AC/L)", "B", [(156.0, 9.5), (151.6, 13.9), (151.6, 43.4), (150.0, 45.0)])   # R6.1 -> PS1.1 (right of the ladder)
T("Net-(PS1-AC/N)", "F", [(146.5, 19.5), (150.0, 16.0), (157.5, 16.0), (161.0, 12.5), (161.0, 9.5)])  # L1.2 -> R7.1 (under R6)
T("Net-(PS1-AC/N)", "B", [(146.5, 19.5), (143.0, 23.0), (143.0, 44.2), (142.2, 45.0)])  # L1.2 -> PS1.2 between the ladder columns

# ================= ZCD ladder (DC column x 137.2 toward U1, AC column x 147.36) =================
T("Net-(D3-A)", "F", [(156.0, 24.74), (152.84, 27.9), (147.36, 27.9), (147.36, 31.3)])  # R6.2 -> AC1 rungs
T("Net-(D1-K)", "F", [(161.0, 24.74), (161.0, 30.6), (155.6, 36.0), (147.36, 36.0), (147.36, 39.4)])  # R7.2 -> AC2 rungs
T("Net-(D2-K)", "F", [(137.2, 27.9), (139.4, 30.1), (139.4, 37.2), (137.2, 39.4)])  # DC+ rungs
T("Net-(D1-A)", "F", [(137.2, 31.3), (137.2, 36.0)])                               # DC- rungs
T("Net-(D2-K)", "F", [(137.2, 39.4), (137.2, 44.56), (134.38, 47.38), (121.5, 47.38)])  # DC+ -> U1.1
T("Net-(D1-A)", "B", [(137.2, 36.0), (135.4, 36.0), (134.9, 36.5), (134.9, 41.1), (131.0, 45.0), (118.96, 45.0), (118.96, 47.38)])  # DC- -> U1.2

# ================= triac drive (pass 2) =================
T(G, "F", [(115.29, 36.65), (115.29, 44.0), (111.91, 47.38), (110.08, 47.38)])    # Q1.G -> R2.2 -> U5.4
T(A1, "B", [(110.21, 36.65), (110.21, 37.0), (103.21, 44.0), (102.59, 44.0)])     # Q1.A1 -> R2.1
T("Net-(R3-Pad1)", "F", [(98.5, 45.9), (99.98, 47.38), (105.0, 47.38)])            # R3.1 -> U5.6

# ================= snubber / MOV (pass 2; the A2 node is LINE_FILT now) =================
T(LF, "F", [(112.75, 36.65), (112.75, 39.1), (87.8, 39.1), (84.7, 36.0)])          # LINE_FILT bus under the fins -> RV2.1
T(LF, "F", [(98.84, 39.1), (98.84, 41.35)])                                        # -> R5.2
T(LF, "F", [(98.84, 41.35), (90.35, 41.35), (85.8, 45.9)])                         # -> R3.2 (under R5's body)
T("Net-(C4-Pad1)", "F", [(80.3, 37.04), (80.3, 38.05), (83.6, 41.35)])             # C4.1 -> R5.1
T(A1, "B", [(107.6, 26.7), (87.9, 26.7), (86.1, 28.5)])                            # A1 bus from the A1 trunk -> RV2.2
T(A1, "B", [(87.9, 26.7), (80.64, 26.7), (80.3, 27.04)])                           # -> C4.2

R.save("tracks_mains.json")
