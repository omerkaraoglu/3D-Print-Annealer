"""Rev3.0 hand routing, region "signals": thermocouple front end, ESP32 support, I2C/touch, slow lines to the isolation parts.
Idempotent: rebuilds tracks_signals.json from scratch.  Local board mm (see handroute.py).
Layer plan:
  F.Cu  : thermocouple block, U20 fan-out, ESP32 support parts, short pin stubs, TRIG/ZCD/Q4-B/D5-A east of x 71, J11 touch parts.
  B.Cu  : (a) slow-line run along y 56.70/57.35/58.00 (ZCD/TRIG/Q4-B) from the ESP32 to x 71..76 (under the display bus);
          (b) touch bundle RST/SCL/SDA/INT: under the display bottom bundle (y 59.3..65.85), down x 39.5..41.75, along the
              bottom edge y 95.85..98.10 (south of J10) and up into J11's pads (J11 is on B.Cu; the power agent's VLED pair
              closes the B.Cu approach from the north at y 86.4..88.1);
          (c) J2 programming lines DTR/RTS/RXD/TXD and IO0 under the ESP32 module (antenna keep-out respected).
"""
from handroute import Router
R = Router("geom.json")
TCN = "/Thermocouple front end (K-type, ADS1115)/"
TC_P, TC_N, TCF_P, TCF_N = TCN + "TC_P", TCN + "TC_N", TCN + "TCF_P", TCN + "TCF_N"
NTC, VREF = TCN + "NTC_MID", TCN + "VREF_HALF"
G, P3 = "GND", "+3V3"
SDA, SCL, INT, RST, RDY = "I2C_SDA", "I2C_SCL", "TP_INT", "LCD_RST", "ADC_RDY"
DTR, RTS, RXD, TXD = "Net-(J2-Pin_2)", "Net-(J2-Pin_3)", "Net-(J2-Pin_4)", "Net-(J2-Pin_5)"
IO0, EN, Q2B, Q3B = "Net-(Q2-C)", "Net-(Q3-C)", "Net-(Q2-B)", "Net-(Q3-B)"
ZCD, TRIG, FAN, Q4B, D5A = "/ZCD", "/TRIG", "/FAN", "Net-(Q4-B)", "Net-(D5-A)"
R4P2, R8P2, R9P1, TPV = "Net-(R4-Pad2)", "Net-(R8-Pad2)", "Net-(R9-Pad1)", "/Display/TP_VDD"
p = R.pad


def F(net, *pts, w=0.25): R.track(net, "F", list(pts), w)
def B(net, *pts, w=0.25): R.track(net, "B", list(pts), w)
def V(net, x, y): R.via(net, x, y, 0.6, 0.3)
def jog(a, b):
    """point on a's row from which a 45-degree step lands exactly on b (for sub-0.1 mm row offsets inside a pad)"""
    return (b[0] - abs(b[1] - a[1]) * (1 if b[0] > a[0] else -1), a[1])


# ======================= 1. Thermocouple front end (F.Cu, 0.3 mm) =======================
W = 0.3
# TC_P/TC_N: coupled pair 0.3 mm / 0.3 mm gap on y 82.2/82.8 from the terminal to the 1k resistors (13.2/13.2 mm),
# the TVS and the 10M bias (terminal side of the 1k) are short stubs off the pair; mirror-symmetric about y = 82.5
F(TC_P, p("J20", 1), (7.3, 80.0), (9.5, 82.2), (14.975, 82.2), p("R220", 2), w=W)
F(TC_N, p("J20", 2), (7.22, 85.08), (9.5, 82.8), (14.975, 82.8), p("R221", 2), w=W)
F(TC_P, (14.05, 82.2), p("D220", 2), w=W)
F(TC_N, (14.05, 82.8), p("D221", 2), w=W)
F(TC_P, p("R220", 2), (17.675, 76.65), p("R222", 2), w=W)
F(TC_N, p("R221", 2), (17.675, 88.0), p("R223", 1), w=W)
# filtered side: symmetric to C220 (AIN0/AIN1 cap) and the two 10n CM caps, then the pair closes in on U20 pins 4/5
F(TCF_P, p("R220", 1), (21.725, 79.5), (23.5, 81.275), p("C220", 1), w=W)
F(TCF_P, (21.725, 79.5), p("C221", 1), w=W)
F(TCF_P, p("C220", 1), (24.525, 81.725), (25.8, 83.0), p("U20", 4), w=W)
F(TCF_N, p("R221", 1), (21.725, 85.5), (23.5, 83.725), p("C220", 2), w=W)
F(TCF_N, (21.725, 85.5), p("C222", 1), w=W)
F(TCF_N, p("C220", 2), (23.725, 83.5), p("U20", 5), w=W)
# analog-ground vias of the block (all land on the In1 plane under the block), symmetric pairs
for ref, num, v in (("D220", 1, (11.95, 77.05)), ("D221", 1, (11.95, 87.95)), ("C221", 2, (24.2, 76.5)), ("C222", 2, (24.2, 88.5)),
                    ("R223", 2, (19.25, 89.0))):
    F(G, p(ref, num), v); V(G, *v)
F(P3, p("R222", 1), (15.75, 76.0)); V(P3, 15.75, 76.0)
# U20: GND pins 1/3 tied on the outside and taken to one via on the digital (top) side
F(G, p("U20", 3), (26.7, 82.5), (26.2, 82.0), (26.2, 80.6)); F(G, p("U20", 1), (26.2, 81.5)); V(G, 26.2, 80.6)
# cold junction: TH220 above D220; NTC_MID has to pass the TC/TCF lines and ADC_RDY, so it runs on B.Cu (quiet DC node)
F(P3, p("TH220", 1), (11.175, 74.75)); V(P3, 11.175, 74.75)
F(NTC, p("TH220", 2), (13.9, 75.8)); V(NTC, 13.9, 75.8)
B(NTC, (13.9, 75.8), (24.9, 86.8), (28.9, 86.8)); V(NTC, 28.9, 86.8)
F(NTC, p("U20", 6), (32.52, 84.32), p("C225", 1))
F(NTC, (28.9, 86.8), (32.52, 86.8)); F(NTC, (29.825, 86.8), p("R225", 1))
F(G, p("R225", 2), (27.2, 88.0)); V(G, 27.2, 88.0)
F(G, p("C225", 2), (34.4, 88.0)); V(G, 34.4, 88.0)
# half-supply reference
F(VREF, p("U20", 7), (32.6, 83.0), (33.775, 84.175), p("R226", 2))
F(VREF, p("R226", 2), (36.7, 84.175), (37.2, 84.675), (37.2, 90.0), (36.375, 90.825), p("R227", 1))
F(VREF, (37.2, 87.98), p("C226", 1))
F(P3, p("R226", 1), (35.0, 85.825)); V(P3, 35.0, 85.825)
F(G, p("R227", 2), (35.0, 89.175)); V(G, 35.0, 89.175)
F(G, p("C226", 2), (38.5, 86.1)); V(G, 38.5, 86.1)
# ADS1115 supply: pin 8 straight to the 100n, plane via at the bend; 1u and the GND pads on their own vias
F(P3, p("U20", 8), (33.0, 82.5), (34.02, 81.48), p("C223", 1)); V(P3, 34.02, 81.48)
F(P3, p("C224", 1), (34.225, 77.3)); V(P3, 34.225, 77.3)
F(G, p("C223", 2), (35.95, 80.5)); V(G, 35.95, 80.5)
F(G, p("C224", 2), (36.75, 78.3)); V(G, 36.75, 78.3)
# ALERT/RDY: enters pin 2 from under the body (pins 1/3 are GND), runs north 4 mm clear of the TC pair
F(RDY, p("U20", 2), (28.25, 82.0), (28.75, 81.5), (28.75, 67.1), (28.25, 66.6), (16.36, 66.6), (15.61, 65.85), p("U3", 7))
F(RDY, (28.75, 73.8), (33.01, 73.8), (33.51, 74.3), p("R224", 2))
F(P3, p("R224", 1), (32.49, 74.9)); V(P3, 32.49, 74.9)

# ======================= 2. I2C =======================
# F.Cu from the ESP32 to the pull-ups and down the trunk (SCL x 30.70, SDA x 31.45; 0.5 mm gap)
F(SDA, p("U3", 26), (23.23, 41.75), (23.98, 42.5), p("R130", 2))
F(SDA, p("R130", 2), (28.99, 42.7), (29.49, 43.2), (30.95, 43.2), (31.45, 43.7), (31.45, 60.75))
F(SCL, p("U3", 23), jog(p("U3", 23), p("R131", 2)), p("R131", 2))
F(SCL, p("R131", 2), (28.99, 45.8), (29.49, 46.3), (30.2, 46.3), (30.7, 46.8), (30.7, 60.0))
F(P3, p("R130", 1), (30.01, 41.6)); V(P3, 30.01, 41.6)
F(P3, p("R131", 1), (30.01, 44.7)); V(P3, 30.01, 44.7)
V(SCL, 30.7, 60.0); V(SDA, 31.45, 60.75); V(G, 29.6, 60.9)          # via1 pair under the display bottom bundle + return via
# branch to the ADS1115 on B.Cu (under ADC_RDY), up next to U20: SCL enters pin 10 from under the body, SDA pin 9 from the east
B(SCL, (30.7, 60.0), (30.7, 78.6)); V(SCL, 30.7, 78.6)
F(SCL, (30.7, 78.6), (30.7, 81.0), (31.2, 81.5), p("U20", 10))
B(SDA, (31.45, 60.75), (31.45, 75.7), (32.85, 77.1)); V(SDA, 32.85, 77.1)
F(SDA, (32.85, 77.1), (32.85, 81.6), (32.45, 82.0), p("U20", 9))
V(G, 31.7, 77.6)                                                    # return via for both via2
# ======================= 3. Touch bundle to J11 (B.Cu): order RST, SCL, SDA, INT =======================
F(RST, p("R121", 1), (24.01, 60.89), (24.6, 60.3)); V(RST, 24.6, 60.3)          # ends at R121 pad 1 centre
F(INT, p("U3", 8), (16.88, 65.1), (17.63, 65.85), (32.6, 65.85)); V(INT, 32.6, 65.85); V(G, 33.5, 66.8)
B(RST, (24.6, 60.3), (25.6, 59.3), (41.25, 59.3), (41.75, 59.8), (41.75, 95.35), (42.25, 95.85), (79.8, 95.85), (80.3, 95.35), p("J11", 6))
B(SCL, (30.7, 60.0), (40.5, 60.0), (41.0, 60.5), (41.0, 96.1), (41.5, 96.6), (80.05, 96.6), (80.8, 95.85), p("J11", 5))
B(SDA, (31.45, 60.75), (39.75, 60.75), (40.25, 61.25), (40.25, 96.85), (40.75, 97.35), (80.3, 97.35), (81.3, 96.35), p("J11", 4))
B(INT, (32.6, 65.85), (39.0, 65.85), (39.5, 66.35), (39.5, 97.6), (40.0, 98.1), (80.55, 98.1), (81.8, 96.85), p("J11", 3))
# J11 area: TVS taps (F) dropping into the pads from the north through the B.Cu pocket y 88.3..91.1
F(SCL, p("D113", 2), (78.5, 87.45), (79.0, 87.95), (79.0, 88.75)); V(SCL, 79.0, 88.75); B(SCL, (79.0, 88.75), (80.8, 90.55), p("J11", 5))
F(SDA, p("D112", 2), (80.55, 87.45), (81.05, 87.95), (81.05, 88.75)); V(SDA, 81.05, 88.75); B(SDA, (81.05, 88.75), (81.3, 89.0), p("J11", 4))
F(G, p("D113", 1), p("D112", 1)); F(G, (79.0, 89.55), (79.0, 90.3)); V(G, 79.0, 90.3)
F(TPV, (83.0, 90.45), (83.0, 88.3875), (83.8, 87.5875), p("R129", 2)); V(TPV, 83.0, 90.45); B(TPV, (83.0, 90.45), (82.8, 90.65), p("J11", 1))
F(TPV, (83.0, 89.48), (82.5, 88.98), p("C126", 1))
F(P3, p("R129", 1), (84.3, 90.45)); V(P3, 84.3, 90.45)
F(G, p("C126", 2), (82.0, 85.8)); V(G, 82.0, 85.8)
B(G, p("J11", 2), (82.3, 89.95)); V(G, 82.3, 89.95)                      # J11 GND via in the pocket above the pads

# ======================= 4. ESP32 support =======================
# J2 programming header: DTR/RTS on F.Cu north of the display bus, then B.Cu under the module; RXD/TXD on B.Cu to vias at the pins
F(DTR, p("J2", 2), (10.25, 13.04), (10.75, 13.54), (10.75, 34.0)); V(DTR, 10.75, 34.0)
F(RTS, p("J2", 3), (9.45, 15.58), (9.95, 16.08), (9.95, 34.8)); V(RTS, 9.95, 34.8)
B(RXD, p("J2", 4), (12.57, 18.12), (13.07, 18.62), (13.07, 39.3)); V(RXD, 13.07, 39.3); F(RXD, (13.07, 39.3), p("U3", 34))
B(TXD, p("J2", 5), (11.3, 20.66), (11.8, 21.16), (11.8, 39.3)); V(TXD, 11.8, 39.3); F(TXD, (11.8, 39.3), p("U3", 35))
# auto-reset: nested L's on B.Cu (RTS outer, DTR middle, IO0 inner), one via at each transistor/resistor pad
B(RTS, (9.95, 34.8), (9.95, 70.49), (9.95, 73.25), (10.45, 73.75), (18.8625, 73.75), (19.3625, 73.25))
V(RTS, 9.95, 70.49); F(RTS, (9.95, 70.49), p("R14", 2)); V(RTS, 19.3625, 73.25); F(RTS, (19.3625, 73.25), p("Q2", 2))
B(DTR, (10.75, 34.0), (10.75, 72.4), (11.25, 72.9), (13.8625, 72.9), (14.1875, 72.575), (23.365, 72.575), (25.45, 70.49))
V(DTR, 13.8625, 72.9); F(DTR, (13.8625, 72.9), p("Q3", 2)); V(DTR, 25.45, 70.49); F(DTR, (25.45, 70.49), p("R13", 2))
V(IO0, 25.9, 40.3); F(IO0, (25.9, 40.3), (25.41, 39.81), p("R12", 2)); F(IO0, p("R12", 2), p("U3", 25))
B(IO0, (25.9, 40.3), (25.6, 40.6), (13.9, 40.6), (13.4, 41.1), (13.4, 58.2), (15.25, 60.05), (15.25, 70.5), (15.95, 71.2), (21.8375, 71.2), (22.5375, 71.9))
V(IO0, 22.5375, 71.9); F(IO0, (22.5375, 71.9), p("Q2", 3))
F(Q3B, p("R14", 1), (11.55, 71.51), (13.01, 70.05), p("Q3", 1))
F(Q2B, p("R13", 1), (23.95, 71.51), (22.49, 70.05), p("Q2", 1))
F(EN, p("U3", 3), (10.53, 66.6), (11.01, 67.08), p("R11", 2))
F(EN, p("R11", 2), p("C6", 2))
F(EN, p("C6", 2), (13.52, 67.9), (14.02, 68.4), (15.2375, 68.4), (16.1375, 69.3), p("Q3", 3))
# decoupling and plane vias
F(P3, p("U3", 2), (9.26, 60.91), p("C5", 1)); F(P3, p("C5", 1), (8.2, 60.92)); V(P3, 8.2, 60.92)
F(G, p("C5", 2), (8.2, 61.88)); V(G, 8.2, 61.88)
F(G, p("U3", 1), (7.99, 57.3)); V(G, 7.99, 57.3)
F(G, p("U3", 38), (7.99, 39.6)); V(G, 7.99, 39.6)
F(G, p("U3", 15), (27.3, 55.715)); V(G, 27.3, 55.715)
F(G, p("C8", 1), (8.82, 65.55)); V(G, 8.82, 65.55)
F(P3, p("C8", 2), (9.78, 66.72), (9.0, 67.5)); F(P3, p("R11", 1), (9.0, 67.5)); V(P3, 9.0, 67.5)
F(P3, p("C7", 1), (11.725, 65.6)); V(P3, 11.725, 65.6)
F(G, p("C7", 2), (13.275, 65.6)); V(G, 13.275, 65.6)
F(G, p("C6", 1), (14.48, 66.55)); V(G, 14.48, 66.55)
F(P3, p("R12", 1), (23.6, 38.79)); V(P3, 23.6, 38.79)
# FAN pin -> R16 (wraps over R16.1)
F(FAN, p("U3", 16), jog(p("U3", 16), p("R16", 2)), p("R16", 2))

# ======================= 5. Slow lines to the isolation-boundary parts =======================
F(ZCD, p("U3", 6), (14.34, 56.7)); V(ZCD, 14.34, 56.7)
F(TRIG, p("U3", 9), (18.15, 57.35)); V(TRIG, 18.15, 57.35)
F(Q4B, p("R16", 1), (30.01, 58.0)); V(Q4B, 30.01, 58.0)
B(ZCD, (14.34, 56.7), (71.0, 56.7)); V(ZCD, 71.0, 56.7)
B(TRIG, (18.15, 57.35), (74.0, 57.35)); V(TRIG, 74.0, 57.35)
B(Q4B, (30.01, 58.0), (76.3, 58.0)); V(Q4B, 76.3, 58.0)
V(G, 16.25, 55.9); V(G, 72.6, 59.4)                                  # return vias at the two via clusters
F(Q4B, (76.3, 58.0), (76.8, 57.5), p("R15", 1)); F(Q4B, p("R15", 1), (77.49, 57.1), (78.04, 56.55), p("Q4", 1))
F(G, p("Q4", 2), (79.46, 58.45)); F(G, p("R15", 2), (79.46, 58.45)); V(G, 79.46, 58.45)
F(D5A, p("K1", 5), (64.05, 54.8), (64.55, 55.3), (82.4375, 55.3), (82.9375, 55.8), p("Q4", 3), w=0.3)   # up into the coil pin from below
F(D5A, p("Q4", 3), p("D5", 2), w=0.3)
F(TRIG, (74.0, 57.35), (75.95, 59.3), (98.71, 59.3), (100.0, 58.01), p("R4", 1))
F(R4P2, p("R4", 2), (102.99, 55.0), p("U5", 1))
# ZCD stays south of y 59 (outside the u1_pins/u5_pins fan-out areas) and passes under U6, between it and the buck's 3V3 via
F(ZCD, (71.0, 56.7), (74.2, 59.9), (113.0, 59.9), (115.4, 62.3), (116.6, 62.3), (117.9, 63.6), (125.29, 63.6), (125.99, 62.9), p("R10", 1))
F(ZCD, p("R10", 1), (125.99, 62.235), (127.325, 60.9), p("R9", 2))
F(G, p("R10", 2), (127.95, 62.5)); V(G, 127.95, 62.5)
# zero-cross receiver: U1.5 -> R8.2 -> U6.2
F(R8P2, p("U1", 5), (118.96, 58.99), p("R8", 2)); F(R8P2, (118.96, 58.99), (118.96, 60.6), (119.86, 61.5), p("U6", 2))
F(P3, p("R8", 1), (118.0, 60.95)); V(P3, 118.0, 60.95)
F(G, p("U6", 3), (119.7, 62.45)); V(G, 119.7, 62.45)
F(P3, p("U6", 5), (123.1375, 59.5)); V(P3, 123.1375, 59.5)
F(R9P1, p("U6", 4), (124.0, 62.45), (125.675, 60.775), p("R9", 1))

R.save("tracks_signals.json")
