"""Mains band (230 VAC) - hand routing, Rev3.0 layout pass 4 (agent "mains").  Idempotent: rebuilds tracks_mains.json.
Placement: placement_override_mains.py (pass 4: PS1 top right, Q1 on the heatsink's north face, input filter at the west end,
H11AA1 ZCD fed straight from R6/R7).  Local board mm.  No vias anywhere in the mains band (every layer change is at a THT pad).
Heater path 2.5 mm, necked to 1.6 mm over the last 2.5 mm into the TO-220 pins.
Layer plan:
  F.Cu  - heater loop: LINE J3.L -> F3.2, LINE_FUSED F3.1 -> L40.2, LINE_FILT trunk L40.1 -> y 12.8 east -> x 103.0 straight down
          into Q1.2, A1 trunk R1.A1 straight down x 108.0 into Q1.1, heater NEUT return R1.N -> J3.N on the top edge.
          LINE_FILT west bus (y 18) to C40/C1/RV1 and the K1 COM drop, NEUT west bus (y 8.75) to C40/C1/RV1, triac-drive rungs
          (RV2, F1, C4, R2) and stubs, C4 node, gate R2 -> Q1.3, PSU_L F1.2 -> L1.4, AC/N L1.2 -> R7.1 and -> PS1.2.
  B.Cu  - NEUT corridor J4.N -> J3.N under F3/J3 (y 8.5), NEUT R1.N -> L1.1 under the A1 trunk (y 8.5), fan NO J4.1 -> K1 NO,
          AC/L L1.3 -> PS1.1 and -> R6.1 (under PS1's west edge, north of y 40), and everything under the heatsink:
          R3-P1 -> U5.6, gate Q1.3 -> U5.4, /ZCD_N R7.2 -> U1.2, /ZCD_L R6.2 -> U1.1."""
from handroute import Router
R = Router("geom_mains.json", placed="rev3_placed_mains.kicad_pcb")
H, W, NK = 2.5, 1.0, 1.6
def T(net, layer, pts, w=W): R.track(net, layer, pts, w)
A1, LF, G = "Net-(Q1-A1)", "LINE_FILT", "Net-(Q1-G)"
ACL, ACN = "Net-(PS1-AC/L)", "Net-(PS1-AC/N)"

# ================= heater loop: J3.L -> F3 -> L40 -> LINE_FILT trunk -> Q1.2 | Q1.1 -> A1 trunk -> R1.A1, R1.N -> J3.N =================
T("LINE", "F", [(87.0, 3.5), (82.9, 3.5)], H)                                     # J3.L -> F3.2b
T("LINE", "F", [(77.7, 3.5), (82.9, 3.5)], H)                                     # F3.2 clip pads
T("LINE_FUSED", "F", [(62.4, 3.5), (67.6, 3.5)], H)                               # F3.1 clip pads
T("LINE_FUSED", "F", [(67.6, 3.5), (67.6, 14.15), (68.55, 15.1)], H)              # F3.1b straight down into L40.2
T(LF, "F", [(76.05, 15.1), (78.35, 12.8), (84.5, 12.8), (89.0, 12.8), (100.5, 12.8), (103.0, 12.8),
            (103.0, 20.4), (103.0, 32.1)], H)                                      # L40.1 -> y 12.8 (R3.2, R5.2 on it) -> down x 103
T(LF, "F", [(103.0, 32.1), (103.0, 34.6)], NK)                                    # neck into Q1.2
T(A1, "F", [(108.0, 3.5), (108.0, 13.9), (108.0, 25.5), (108.0, 29.8), (108.0, 32.14)], H)   # R1.A1 straight down (RV2.2, C4.2, R2 taps)
T(A1, "F", [(108.0, 32.14), (105.54, 34.6)], NK)                                  # neck into Q1.1
T("NEUT", "F", [(94.8, 3.5), (100.2, 3.5)], H)                                    # heater return R1.N -> J3.N on the top edge

# ================= LINE_FILT branches =================
T(LF, "F", [(76.05, 15.1), (73.15, 18.0), (70.5, 18.0), (63.5, 18.0), (60.75, 15.25), (60.75, 13.0)], W)   # L40.1 -> C40.1 (y 18 bus)
T(LF, "F", [(63.5, 18.0), (51.6, 18.0), (48.2, 21.4)], W)                         # bus -> C1.1
T(LF, "F", [(48.2, 21.4), (48.2, 23.8), (44.0, 28.0)], W)                         # C1.1 -> RV1.1
T(LF, "F", [(70.5, 18.0), (70.5, 47.5), (70.0, 48.0)], W)                         # K1 COM drop between the relay pins
T(LF, "F", [(100.5, 12.8), (100.5, 12.5)], W)                                     # RV2.1 at the trunk corner
T(LF, "F", [(97.6, 20.4), (102.8, 20.4), (103.0, 20.4)], W)                       # F1.1 clips onto the descent

# ================= NEUT =================
T("NEUT", "B", [(56.9, 3.5), (56.9, 8.5), (94.8, 8.5), (94.8, 3.5)], W)           # corridor J4.N -> J3.N under F3 / J3
T("NEUT", "F", [(56.9, 3.5), (56.9, 5.0), (53.15, 8.75), (33.25, 8.75), (33.25, 13.0)], W)   # J4.N -> C40.2 (west bus)
T("NEUT", "F", [(33.25, 13.0), (33.25, 21.35), (33.2, 21.4)], W)                  # C40.2 -> C1.2
T("NEUT", "F", [(33.2, 21.4), (33.2, 22.5), (36.5, 25.8)], W)                     # C1.2 -> RV1.2
T("NEUT", "B", [(100.2, 3.5), (100.2, 6.0), (102.7, 8.5), (114.6, 8.5), (119.1, 13.0), (120.0, 13.0)], W)   # R1.N -> L1.1 under A1

# ================= fan: J4.1 (NO) -> K1.3 =================
T("Net-(J4-Pin_1)", "B", [(49.9, 3.5), (49.9, 16.4), (52.5, 19.0), (52.5, 28.5), (55.0, 28.5), (57.5, 31.0),
                          (73.2, 31.0), (76.05, 33.85)], W)

# ================= PSU branch: F1 -> L1 -> PS1, ZCD taps =================
T("PSU_L", "F", [(112.9, 20.4), (118.1, 20.4)], W)                                # F1.2 clip pads
T("PSU_L", "F", [(112.9, 20.4), (112.9, 8.0), (115.9, 5.0), (120.0, 5.0)], W)     # F1.2a -> L1.4
T(ACL, "B", [(127.0, 5.0), (131.3, 9.3), (145.7, 9.3), (150.0, 5.0)], W)          # L1.3 -> PS1.1 (under PS1, around PS1.2)
T(ACL, "B", [(131.3, 9.3), (131.3, 16.7), (128.0, 20.0)], W)                      # -> R6.1
T(ACN, "F", [(127.0, 13.0), (124.5, 15.5), (123.0, 17.0), (123.0, 20.0)], W)      # L1.2 -> R7.1
T(ACN, "F", [(127.0, 13.0), (134.2, 13.0), (142.2, 5.0)], W)                      # L1.2 -> PS1.2
T("/ZCD_N", "B", [(123.0, 25.08), (114.0, 34.08), (114.0, 42.2), (118.96, 47.16), (118.96, 47.38)], W)        # R7.2 -> U1.2
T("/ZCD_L", "B", [(128.0, 25.08), (127.5, 25.08), (115.6, 36.98), (115.6, 41.4), (121.5, 47.3), (121.5, 47.38)], W)         # R6.2 -> U1.1

# ================= triac drive =================
T("Net-(C4-Pad1)", "F", [(89.0, 28.04), (91.54, 25.5), (98.25, 25.5)], W)         # R5.1 -> C4.1
T("Net-(R3-Pad1)", "B", [(84.5, 25.5), (84.5, 31.5), (85.3, 32.3), (91.5, 32.3), (91.5, 45.0), (102.62, 45.0), (105.0, 47.38)], W)  # R3.1 -> U5.6
T(G, "F", [(97.9, 29.8), (97.9, 32.04), (100.46, 34.6)], W)                       # R2.2 -> Q1.3
T(G, "B", [(100.46, 34.6), (100.46, 35.9), (110.08, 45.52), (110.08, 47.38)], W)  # Q1.3 -> U5.4 under the heatsink
T(A1, "F", [(108.0, 25.5), (108.25, 25.5)], W)                                    # C4.2 on the trunk
T(A1, "F", [(110.6, 29.8), (108.0, 29.8)], W)                                     # R2.1 stub

R.save("tracks_mains.json")
