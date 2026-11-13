"""Root sheet (A1).
Row 1 (mains, top): Mains input -> Zero-cross detector -> Heater power stage.
Row 2: the four hierarchical sheet symbols with their notes (right).
Row 3: Programmer & auto-boot above the MCU (left), MCU notes, Fan control (right).
Every group is drawn at its own origin (dx, dy) so whole groups can be moved."""


class G:
    """coordinate helper: group origin offset"""

    def __init__(self, b, dx, dy):
        self.b, self.dx, self.dy = b, dx, dy

    def p(self, x, y):
        return (round(x + self.dx, 4), round(y + self.dy, 4))

    def place(self, ref, x, y, rot=0, **kw):
        f = kw.get("f")
        if isinstance(f, dict):
            kw["f"] = {k: (v[0] + self.dx, v[1] + self.dy, v[2]) for k, v in f.items()}
        return self.b.place(ref, round(x + self.dx, 4), round(y + self.dy, 4), rot, **kw)

    def w(self, *pts):
        return self.b.w(*[q if isinstance(q, str) else self.p(*q) for q in pts])

    def note(self, x, y, lines):
        self.b.note(x + self.dx, y + self.dy, lines)


def mains(b, dx=0, dy=0):
    g = G(b, dx, dy)
    YL, YN = 76.2, 101.6
    g.place("J3", 38.1, 88.9, 0, f={"Reference": (35.56, 87.63, "right"), "Value": (35.56, 90.17, "right")})
    g.w("J3.1", (48.26, 88.9), (48.26, YL))
    g.w("J3.2", (45.72, 91.44), (45.72, YN))
    g.place("V1", 60.96, 88.9, 0, f="R")
    g.w((60.96, YL), "V1.1")
    g.w("V1.2", (60.96, YN))
    g.place("F3", 101.6, YL, 270, f="A")
    g.w((48.26, YL), "F3.2")
    b.power(g.p(71.12, YL), "LINE")
    b.flag(g.p(83.82, YL))
    b.lab("F3.1", 7.62)
    # back from the filter sheet
    xf = 152.4
    b.lab_at(g.p(xf, YL), "L", spec="F1.1")
    g.place("RV1", 165.1, 88.9, 0, f="R")
    g.place("C1", 190.5, 88.9, 0, f="R")
    g.place("F1", 226.06, YL, 90, f="A")
    g.w((xf, YL), "F1.1")
    for r in ("RV1", "C1"):
        x = b.P(r + ".1")[0]
        g.w((x - dx, YL), r + ".1")
        g.w(r + ".2", (x - dx, YN))
    # PSU branch: F1 -> PSU_L -> L1 -> PS1
    g.place("L1", 254.0, 78.74, 0, mirror="x", f="A", dx=6.35)
    g.w("F1.2", "L1.4")
    g.w((241.3, YL), (241.3, 71.12))
    b.lab_at(g.p(241.3, 71.12), "U", spec="F1.2")
    # neutral rail
    g.w((45.72, YN), (243.84, YN), (243.84, 81.28), "L1.1")
    b.power(g.p(71.12, YN), "NEUT")
    b.flag(g.p(83.82, YN))
    # AC pair to PS1, ZCD feed resistors R6 (up) / R7 (down), flags
    g.place("PS1", 307.34, 78.74, 0, f="TL")
    g.w("L1.3", "PS1.1")
    g.w("L1.2", "PS1.2")
    g.place("R6", 266.7, 72.39, 180, f="R")
    g.w("R6.2", (266.7, 66.04), (274.32, 66.04))
    b.lab_at(g.p(274.32, 66.04), "R", spec="R6.2")
    g.place("R7", 266.7, 85.09, 0, f="R")
    g.w("R7.2", (266.7, 91.44), (274.32, 91.44))
    b.lab_at(g.p(274.32, 91.44), "R", spec="R7.2")
    b.flag(g.p(289.56, YL))
    g.w((284.48, 81.28), (284.48, 93.98), (292.1, 93.98))
    b.flag(g.p(292.1, 93.98))
    # 5 V output
    g.w("PS1.4", (342.9, YL))
    b.power(g.p(342.9, YL), "+5V")
    g.place("C2", 330.2, 80.01, 0, f="R")
    b.gnd(b.P("C2.2"))
    b.pw("PS1.3", 2.54)
    g.note(96.52, 106.68, ["Fuse clips: Reomax R3-5A, 2 per fuse (BOM line, no symbol)"])
    g.note(38.1, 119.38, [
        "Mains input (Rev3.0 layout pass 3/4): J3 mains lead pads -> F3 8 A main fuse -> LINE_FUSED -> sheet 'Mains input EMC filter' (L40 100 uH 5 A, C40 1 uF X2) -> LINE_FILT",
        "LINE_FILT feeds the heater triac Q1, the fan relay K1 and, through F1 (1 A time-lag), the PSU branch PSU_L",
        "RV1 TVR14431KSU15Y (14 mm, 275 V ac class MOV) and C1 100 nF X2 across LINE_FILT-NEUT; the X2 capacitors are bled by R6/R7",
        "L1 LFU09V-103 common-mode choke; PS1 HLK-10M05 (5 V / 2 A, 10 W); C2 220 uF 16 V on the 5 V output",
        "V1 is the simulation source only (230 V rms, 50 Hz), not a part; PWR_FLAGs on LINE/NEUT (wire pads) and on the PS1 AC pins (driven through L1)",
    ])
    return [("mains_input", 20 + dx, 52 + dy, 352 + dx, 136 + dy)]


def zcd(b, dx=0, dy=0):
    g = G(b, dx, dy)
    g.place("U1", 406.4, 78.74, 0, f="TL")
    b.lab("U1.1", 7.62)
    b.lab("U1.2", 7.62)
    b.pw("U1.4", 2.54)
    g.place("R8", 424.18, 74.93, 0, f="R")
    b.pw("R8.1", 0)
    g.place("U6", 447.04, 78.74, 0, f={"Reference": (453.39, 71.12, "left"), "Value": (453.39, 73.66, "left")})
    g.w("U1.5", "R8.2", "U6.2")
    g.w("U6.5", (441.96, 58.42), (459.74, 58.42))
    b.power(g.p(441.96, 58.42), "+3V3")
    g.place("C5", 459.74, 62.23, 0, f="R")
    b.gnd(b.P("C5.2"))
    b.pw("U6.3", 0)
    g.place("R9", 482.6, 78.74, 90, f="A")
    g.w("U6.4", "R9.1")
    g.place("R10", 495.3, 82.55, 0, f="R")
    b.gnd(b.P("R10.2"))
    g.w("R9.2", "R10.1", (505.46, 78.74))
    b.lab_at(g.p(505.46, 78.74), "R", spec="R10.1")
    g.note(381.0, 101.6, [
        "Zero-cross detector (layout pass 4): U1 H11AA1 AC-input optocoupler (Isocom H11AA1X)",
        "fed by R6/R7 (2 x 33k 1 W 500 V) from the PSU AC pair; ZCD_L/ZCD_N differ by one LED drop (0.5 mm layout rule)",
        "the 4N28 + D1-D4 bridge of passes 1-3 is gone",
        "R8 10k pull-up, U6 SN74LVC1G14 Schmitt inverter (C5 100 nF), R9 180 R series, R10 10k pull-down",
        "-> ZCD (ESP32 IO34)",
    ])
    return [("zcd", 365 + dx, 50 + dy, 525 + dx, 118 + dy)]


def power_stage(b, dx=0, dy=0):
    g = G(b, dx, dy)
    yr, ya = 66.04, 96.52
    b.lab_at(g.p(568.96, yr), "L", spec="Q1.2")
    g.place("U5", 579.12, 81.28, 0, f="TL")
    g.place("Q1", 614.68, 81.28, 0, f="R")
    g.place("R4", 558.8, 78.74, 90, f="A")
    g.w("R4.2", "U5.1")
    b.lab("R4.1", 5.08)
    b.pw("U5.2", 5.08)
    g.place("R3", 599.44, 69.85, 180, f="L")
    g.w("U5.6", (599.44, 78.74), "R3.1")
    g.w("U5.4", "Q1.3")
    g.place("R2", 601.98, 90.17, 180, f="L")
    g.w((601.98, 83.82), "R2.2")
    g.w("R2.1", (601.98, ya))
    g.w("Q1.1", (614.68, ya))
    g.w("Q1.2", (614.68, yr))
    # snubber, MOV, heater
    g.place("R5", 640.08, 69.85, 180, f="R")
    g.place("C4", 640.08, 81.28, 0, f="R")
    g.w("R5.1", "C4.1")
    g.w("C4.2", (640.08, ya))
    g.place("RV2", 662.94, 81.28, 0, f="R")
    g.w((662.94, yr), "RV2.1")
    g.w("RV2.2", (662.94, ya))
    g.place("R1", 685.8, 100.33, 0, f="R")
    b.power(b.P("R1.2"), "NEUT")
    g.w((568.96, yr), "R3.2", (614.68, yr), "R5.2", (662.94, yr))
    g.w((601.98, ya), (614.68, ya), (640.08, ya), (662.94, ya), "R1.1")
    g.place("HS1", 614.68, 109.22, 0, f="R")
    g.note(553.72, 124.46, [
        "Heater power stage: TRIG (IO33) -> R4 120 R -> U5 MOC3052M random-phase opto-triac (Isocom MOC3052X)",
        "R4 120 R because the MOC3052 needs IFT 10 mA: (3.3 - 1.5 - 0.1) V / 120 R = 14 mA worst case, 18 mA / 39 mW best case",
        "R3/R2 360 R 1/2 W gate network, Q1 BTA24-800CWRG (insulated TO-220) on HS1 Fischer SK 409 63,5 STC (5.6 K/W)",
        "R5 47 R 2 W + C4 10 nF X2 snubber, RV2 10561K MOV across the triac; R1 = the 1 kW heater on wire pads, return to NEUT",
        "burst firing; worst case 4.35 A rms -> 3.7 W in Q1, Tj 121 C at 85 C ambient (spec 7.1)",
    ])
    return [("power_stage", 540 + dx, 50 + dy, 760 + dx, 140 + dy)]


def subsheets(b, dx=0, dy=0):
    g = G(b, dx, dy)
    y = 236.22
    items = [
        ("Mains input EMC filter", 480.06, [
            "Mains input EMC filter (Rev3_InputFilter)",
            "L40 100 uH 5 A + C40 1 uF X2 after F3:",
            "LINE_FUSED in, LINE_FILT out",
            "carries the heater current",
        ]),
        ("Power", 548.64, [
            "Power (Rev3_Power)",
            "5 V -> 3.3 V buck U30 TPS562201,",
            "3.3 V -> 1.2 V LDO U31 LD1117S12",
            "(SSD1963 core), power budget",
        ]),
        ("Display", 617.22, [
            "Display (Rev3_Display)",
            "SSD1963 U10 + 7\" 800x480 RGB TFT J10,",
            "MIC2288 backlight boost U11,",
            "GT911 touch J11, I2C pull-ups",
        ]),
        ("Thermocouple front end (K-type, ADS1115)", 685.8, [
            "Thermocouple (Rev3_Thermocouple)",
            "K-type input J20, TVS, bias, RC filter,",
            "ADS1115 U20 (0x48), NTC cold junction,",
            "probe TC1 (BOM item)",
        ]),
    ]
    for name, x, lines in items:
        b.place_sheet(name, x + dx, y + dy)
        g.note(x, y - 16.51, lines)
    g.note(480.06, 279.4, [
        "Sub-sheets: flat hierarchy, no sheet pins; cross-sheet signals are global labels, rails are global power symbols",
        "Rev3.0 (2026-11): 7\" RGB TFT via SSD1963, K-type thermocouple on ADS1115, 5 V -> 3V3 buck + 1V2 LDO, mains LC filter;",
        "PS1 upgraded to HLK-10M05 (10 W); the MAX6675 module and the ILI9341 header of Rev2.1 are removed",
    ])
    return [("subsheets", 470 + dx, 205 + dy, 760 + dx, 290 + dy)]


def mcu(b, dx=0, dy=0):
    g = G(b, dx, dy)
    X3, Y3 = 203.2, 393.7
    g.place("U3", X3, Y3, 0, f={"Reference": (200.66, 351.79, "right"), "Value": (200.66, 354.33, "right")})
    # supply and decoupling
    g.w("U3.2", (X3, 342.9), (223.52, 342.9))
    b.power(g.p(X3, 342.9), "+3V3")
    g.place("C7", 213.36, 346.71, 0, f="L")
    b.gnd(b.P("C7.2"))
    g.place("C8", 223.52, 346.71, 180, f="R")
    b.gnd(b.P("C8.1"))
    b.pw("U3.1", 0)
    # EN: R11 pull-up + C6 at the pin, label EN (auto-boot Q3 drives it from the programmer block)
    g.place("R11", 172.72, 359.41, 0, f="L")
    b.pw("R11.1", 0)
    g.place("C6", 172.72, 367.03, 180, f="L")
    b.gnd(b.P("C6.1"))
    g.w("U3.3", (162.56, 363.22))
    b.lab_at(g.p(162.56, 363.22), "L", spec="U3.3")
    # right side: labels for every named pin
    for n in ("26", "29", "13", "23", "27", "28", "30", "31", "33", "36", "37", "10", "11", "12", "8", "7"):
        b.lab("U3." + n, 7.62)
    for n in ("16", "9", "6"):            # local labels clear of the global label column
        b.lab("U3." + n, 33.02)
    # IO0 with R12 pull-up, UART to J2: labels on stubs (round 2)
    g.place("R12", 233.68, 359.41, 0, f="R")
    b.pw("R12.1", 0)
    for n in ("25", "35", "34"):
        b.lab("U3." + n, 33.02)
    g.note(152.4, 452.12, [
        "MCU: U3 ESP32-WROOM-32E-N16 (Espressif), 3V3 from U30 (sheet Power); C7 10 uF + C8 100 nF at VDD",
        "EN: R11 10k pull-up + C6 100 nF; IO0 boot strap: R12 10k pull-up; IO2 and IO12 (MTDI strap) unused (NC)",
        "GPIO map: LCD D0-D7 = IO16, IO14, IO27, IO26, IO25, IO21, IO22, IO23; WR = IO19, DC = IO18, CS = IO5, RST = IO17",
        "I2C SDA = IO4, SCL = IO15; TP_INT = IO32; ADC_RDY = IO35; TRIG = IO33, ZCD = IO34, FAN = IO13",
        "LCD_* and I2C/TP_INT/ADC_RDY go to the Display and Thermocouple sheets as global labels; the 33 R series resistors are on the Display sheet",
    ])
    return [("mcu", 150 + dx, 330 + dy, 300 + dx, 445 + dy)]


def programmer(b, dx=0, dy=0):
    """J2 header block and the Q2/Q3 auto-boot block, both reached by labels (round 2: no long wires, no crossings)"""
    g = G(b, dx, dy)
    g.place("J2", 276.86, 325.12, 180, f={"Reference": (279.4, 323.85, "left"), "Value": (279.4, 326.39, "left")})
    b.pw("J2.6", 5.08)
    b.pw("J2.1", 5.08)
    for n in ("5", "4", "3", "2"):
        b.lab("J2." + n, 7.62)
    for q, r, x in (("Q2", "R13", 317.5), ("Q3", "R14", 368.3)):
        g.place(q, x, 325.12, 0, f="R")
        g.place(r, x - 12.7, 325.12, 270, f="A")
        g.w(r + ".1", q + ".1")
        b.lab(r + ".2", 5.08)
        c, e = b.P(q + ".3"), b.P(q + ".2")
        b.w(c, (c[0], c[1] - 5.08), (c[0] + 5.08, c[1] - 5.08))
        b.lab_at((c[0] + 5.08, c[1] - 5.08), "R", spec=q + ".3")
        b.w(e, (e[0], e[1] + 5.08), (e[0] + 5.08, e[1] + 5.08))
        b.lab_at((e[0] + 5.08, e[1] + 5.08), "R", spec=q + ".2")
    g.note(256.54, 297.18, [
        "Programmer and auto-boot: J2 6-pin FTDI header (1 GND, 2 RTS, 3 DTR, 4 RXD0, 5 TXD0, 6 3V3)",
        "ESP32-side names: RXD0 = U3 RXD0/IO3 <- adapter TXD (J2 pin 4); TXD0 = U3 TXD0/IO1 -> adapter RXD (J2 pin 5)",
        "Q2/Q3 MMBT4401 cross-coupled auto-boot (Espressif scheme): Q2 -> IO0, Q3 -> EN; R13/R14 10k base resistors",
        "net names EN, IO0, RTS, DTR, TXD0, RXD0 replace the auto names of the pass-4 netlist (round 2, no connectivity change)",
    ])
    return [("programmer", 250 + dx, 288 + dy, 395 + dx, 345 + dy)]


def fan(b, dx=0, dy=0):
    g = G(b, dx, dy)
    g.place("K1", 482.6, 393.7, 180, f={"Reference": (469.9, 392.43, "right"), "Value": (469.9, 394.97, "right")})
    g.w("K1.2", (487.68, 381.0), (497.84, 381.0))
    b.power(g.p(487.68, 381.0), "+5V")
    g.place("D5", 497.84, 393.7, 270, f="R")
    g.w((497.84, 381.0), "D5.1")
    g.w("K1.5", (487.68, 406.4), (497.84, 406.4), "D5.2")
    g.place("Q4", 485.14, 424.18, 0, f="R")
    g.w("Q4.3", (487.68, 406.4))
    b.pw("Q4.2", 0)
    g.place("R15", 472.44, 427.99, 0, f="L")
    b.gnd(b.P("R15.2"))
    g.place("R16", 462.28, 424.18, 270, f="A")
    g.w("R16.1", "R15.1", "Q4.1")
    b.lab("R16.2", 5.08)
    g.w("K1.1", (477.52, 381.0), (467.36, 381.0))
    b.lab_at(g.p(467.36, 381.0), "L", spec="K1.1")
    g.place("J4", 452.12, 403.86, 0, f="L")
    g.w("K1.3", (474.98, 403.86), "J4.1")
    g.w("J4.2", (459.74, 406.4))
    b.power(g.p(459.74, 406.4), "NEUT")
    g.note(440.69, 449.58, [
        "Fan control: FAN (IO13) -> R16 1k -> Q4 BC817-25 (R15 10k pull-down) -> K1 coil (5 V), D5 1N4148W flyback",
        "K1 HJR-3FF-S-Z-4/05VDC (Tianbo; SRD-05 footprint and pinout, SPDT 7 A): COM = LINE_FILT,",
        "NO -> J4 fan lead pads (the fan returns to NEUT), NC unused",
    ])
    return [("fan", 430 + dx, 365 + dy, 620 + dx, 465 + dy)]


def build(b, table):
    b.shapes = {"LINE_FUSED": "output", "LINE_FILT": "input", "PSU_L": "passive", "I2C_SDA": "bidirectional",
                "I2C_SCL": "output", "TP_INT": "bidirectional", "ADC_RDY": "input"}
    for n in ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "WR", "DC", "CS", "RST"):
        b.shapes["LCD_" + n] = "output"
    regions = []
    regions += mains(b)
    regions += zcd(b)
    regions += power_stage(b)
    regions += subsheets(b)
    regions += mcu(b)
    regions += programmer(b)
    regions += fan(b)
    return dict(paper="A1", name="Main",
                c1="Mains input, zero-cross detector, heater triac stage, fan relay, ESP32 MCU",
                c2="Sub-sheets: input filter, power (buck/LDO), display (SSD1963/TFT), thermocouple",
                regions=regions)
