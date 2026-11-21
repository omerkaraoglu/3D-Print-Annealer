"""Display sheet (A2).
Left: 8080 bus series resistors (block). Middle: U10 SSD1963 with its 1V2 / 3V3 decoupling rails above, crystal
below-left. Right of U10: RN1-RN7 series arrays (7 rows), then J10 panel connector. Right of J10: panel power entry
(TFT_VDD, VLED EMC caps). Bottom: backlight boost U11 (left-to-right flow), touch J11 with its support parts."""

import os

G = 2.54
NEW = not os.environ.get("EMC_REPRO")      # EMC-fix round 2026-11-21: RN 100 R note, C134/C135 at the J10 via field


def build(b, table):
    b.shapes = {"I2C_SDA": "bidirectional", "I2C_SCL": "input", "TP_INT": "bidirectional", "LCD_RST": "input"}
    for n in ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "WR", "DC", "CS"):
        b.shapes["LCD_" + n] = "input"
    regions = []
    X, Y = 254.0, 215.9
    # ------------------------------------------------------------------ U10
    b.place("U10", X, Y, 0, f={"Reference": (X - 27.94, Y - 5.08, "right"), "Value": (X - 27.94, Y - 2.54, "right")})
    for n in ("7", "8", "9", "10", "11", "116", "115", "114", "123", "122", "120", "121", "127"):
        b.lab("U10." + n, 5.08)
    b.pw("U10.128", 22.86)                 # CONF -> 3V3 (8080 mode)
    b.pw("U10.15", 35.56)                  # CLK -> GND (clear of the crystal wires)
    rights = ["28", "29", "30", "31", "85", "86", "35", "59", "60", "61", "62", "63", "67", "68", "69", "70", "71", "72",
              "76", "77", "78", "79", "80", "81", "45", "44", "43", "49", "51"]
    for n in rights:
        b.lab("U10." + n, 5.08)
    b.pw("U10.2", 2.54)
    b.pw("U10.19", 2.54)
    # crystal: XTAL_IN turns down further out than XTAL_OUT (no crossing), wires enter the crystal pins sideways
    xi, xo = X - 44.45, X - 36.83
    xa, xb = X - 52.07, X - 29.21
    yy = Y + 55.88
    b.place("Y10", (xi + xo) / 2, yy, 0, f="A")
    b.w("U10.22", (xa, Y + 38.1), (xa, yy), "Y10.1")
    b.w("U10.24", (xb, Y + 40.64), (xb, yy), "Y10.3")
    b.pw("Y10.2", 2.54)
    b.place("C110", xa, yy + 3.81, 0, f="L")
    b.place("C111", xb, yy + 3.81, 0, f="R")
    b.gnd(b.P("C110.2"))
    b.gnd(b.P("C111.2"))
    b.lab_at((xa, Y + 50.8), "U", spec="C110.1")
    b.lab_at((xb, Y + 50.8), "U", spec="C111.1")
    b.note(172.72, 292.1, [
        "Display controller: U10 SSD1963QL9 (Solomon Systech), 1215 KB frame buffer,",
        "drives the 7\" 800x480 panel (24-bit RGB, 33.3 MHz PCLK) from the 8-bit 8080 bus",
        "CONF = 1 -> 8080 mode; RD# pulled up by R124; CLK = GND, 10 MHz crystal Y10 + C110/C111 27 pF",
        "D8-D23, TE, GPIO0-3 and GAMAS0/1 left open (no-connect flags)",
    ])
    regions.append(("u10_xtal", 165, 150, 300, 305))
    # ------------------------------------------------------------------ decoupling rails
    yr = 139.7
    vddd, vpll, vio, vlcd = (b.P("U10." + n) for n in ("1", "18", "4", "27"))
    b.w(vddd, (vddd[0], yr))
    b.w(vpll, (vpll[0], yr), (116.84, yr))
    b.power((vddd[0], yr), "+1V2")
    b.w(vio, (vio[0], yr), (377.19, yr))
    b.w(vlcd, (vlcd[0], yr))
    b.power((vlcd[0], yr), "+3V3")
    for ref, x in (("C121", 218.44), ("C120", 193.04), ("C117", 167.64), ("C118", 142.24), ("C119", 116.84)):
        b.place(ref, x, yr + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    for ref, x in (("C112", 275.59), ("C113", 300.99), ("C114", 326.39), ("C115", 351.79), ("C116", 377.19)):
        b.place(ref, x, yr + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.note(116.84, 124.46, [
        "SSD1963 supply decoupling (datasheet: 100 nF per 2-3 supply pins + 1 uF at VDDPLL + 10 uF bulk)",
        "1V2 rail (U31, sheet Power): VDDD (17 pins) and VDDPLL (pin 18): C121 1 uF at VDDPLL, C120 1 uF, C117-C119 100 nF",
        "3V3 rail: VDDIO (9 pins) and VDDLCD (9 pins): C112-C115 100 nF, C116 10 uF bulk",
    ])
    regions.append(("decoupling", 105, 115, 405, 160))
    # ------------------------------------------------------------------ 8080 bus series resistors
    order = [("R110", 0), ("R121", 1), ("R119", 2), ("R120", 3), ("R117", 4), ("R114", 5), ("R115", 6), ("R116", 7),
             ("R118", 8), ("R112", 9), ("R113", 10), ("R111", 11)]
    y0 = 175.26
    for ref, k in order:
        y = y0 + 7.62 * k
        b.place(ref, 76.2, y, 90, f={"Reference": (76.2, y - 2.54, "center"), "Value": (76.2, y + 2.54, "center")},
                hide_val=True)
        b.lab(ref + ".1", 7.62)
        b.lab(ref + ".2", 7.62)
    b.place("R124", 76.2, y0 + 7.62 * 12 + 5.08, 0, f="R")
    b.pw("R124.1", 0)
    p = b.P("R124.2")
    b.w(p, (p[0], p[1] + G), (p[0] + 7.62, p[1] + G))
    b.lab_at((p[0] + 7.62, p[1] + G), "R", spec="R124.2")
    b.note(30.48, 289.56, [
        "8080 bus from the ESP32 (root sheet): R110-R121 33 R series terminations (Yageo RC0402JR-0733RL),",
        "placed at the ESP32 end of each line, bus < 80 mm over solid ground; values hidden, all 33 R",
        "R124 10k pulls RD# high (no read-back); CONF = 3V3 -> 8080 mode; CLK = GND, 10 MHz crystal Y10",
    ])
    regions.append(("bus", 25, 165, 175, 305))
    # ------------------------------------------------------------------ RN1-RN7 series arrays
    xr = 325.12
    for k in range(7):
        ref = "RN%d" % (k + 1)
        yk = 185.42 + 17.78 * k
        b.place(ref, xr, yk, 270, f={"Reference": (xr, yk - 8.89, "center"), "Value": (xr, yk + 6.35, "center")})
        for n in ("1", "2", "3", "4"):
            b.lab("%s.%s" % (ref, n), 5.08)
        for n in ("5", "6", "7", "8"):
            b.lab("%s.%s" % (ref, n), 5.08)
    b.note(297.18, 161.29, [
        "RN1-RN7: 100 R x4 arrays (Royalohm 4D02WGJ0101TCE),",
        "series termination of the 24 RGB + 4 sync lines at the",
        "SSD1963 (EMC pass 4); <net>_T = controller side",
        "33 R -> 100 R on 2026-11-21 (radiated emission)",
    ] if NEW else [
        "RN1-RN7: 33 R x4 arrays (Royalohm 4D02WGJ0330TCE),",
        "series termination of the 24 RGB + 4 sync lines at the",
        "SSD1963 (EMC pass 4); <net>_T = controller side",
    ])
    regions.append(("rn_block", 295, 158, 360, 305))
    # ------------------------------------------------------------------ J10 panel connector
    JX, JY = 386.08, 215.9
    b.place("J10", JX, JY, 0, f="TL")
    for n in range(1, 41):
        spec = "J10.%d" % n
        net = b.net(spec)
        if net == "GND":
            b.pw(spec, 17.78)
        elif not net.startswith("unconnected"):
            b.lab(spec, 5.08)
    regions.append(("j10", 345, 150, 405, 272))
    # ------------------------------------------------------------------ panel power entry (right of J10)
    yt = 160.02
    b.power((419.1, yt), "+3V3")
    b.place("R125", 429.26, yt, 90, f="A")
    b.w((419.1, yt), "R125.1")
    b.w("R125.2", (508.0, yt))
    for ref, x in (("C122", 441.96), ("C123", 467.36), ("C132", 492.76)):
        b.place(ref, x, yt + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.lab_at((508.0, yt), "R", spec="R125.2")
    yp, yn = 187.96, 200.66
    b.place("C129", 434.34, (yp + yn) / 2, 0, f="R")
    b.place("C131", 459.74, yn + 3.81, 0, f="R")
    b.place("C130", 485.14, yp + 3.81, 0, f="R")
    b.w((419.1, yp), (434.34, yp), "C130.1")
    b.w((434.34, yp), "C129.1")
    b.w((419.1, yn), (434.34, yn), "C131.1")
    b.w("C129.2", (434.34, yn))
    b.gnd(b.P("C131.2"))
    b.gnd(b.P("C130.2"))
    b.lab_at((419.1, yp), "L", spec="C130.1")
    b.lab_at((419.1, yn), "L", spec="C131.1")
    b.note(414.02, 220.98, [
        "Panel power entry at J10 (EMC pass 4):",
        "TFT_VDD = 3V3 through R125 0R (0805), C122 10 uF + C123 100 nF + C132 1 nF at J10 pin 4",
        "C129 100 nF across VLED+/VLED- (RF return for the FPC), C130/C131 1 nF to GND at pins 2/1",
    ])
    regions.append(("panel_power", 405, 145, 560, 232))
    if NEW:
        # ---------------------------------------------------------- +5V return caps at the J10 via field (C 6.1)
        y5 = 187.96
        b.power((513.08, y5), "+5V")
        b.w((513.08, y5), (551.18, y5))
        for ref, x in (("C134", 525.78), ("C135", 551.18)):
            b.place(ref, x, y5 + 3.81, 0, f="R")
            b.gnd(b.P(ref + ".2"))
        b.note(510.54, 205.74, [
            "J10 via-field caps (EMC test campaign C 6.1):",
            "C134/C135 100 nF X7R +5V-GND, one on each side",
            "of the vias where B2, B3, PCLK, HSYNC, VSYNC, DE",
            "change to B.Cu over the In2 +5V island;",
            "island impedance at 498.5 MHz: 253 -> 3 Ohm",
        ])
        regions.append(("j10_vias", 503, 175, 585, 222))
    # ------------------------------------------------------------------ touch J11 and its support parts
    KX, KY = 548.64, 262.89
    b.place("J11", KX, KY, 0, f="TL")
    for n in ("1", "3", "4", "5", "6"):
        b.lab("J11." + n, 5.08)
    b.pw("J11.2", 30.48)
    yv = 287.02
    b.power((406.4, yv), "+3V3")
    b.place("R129", 416.56, yv, 90, f="A")
    b.w((406.4, yv), "R129.1")
    b.w("R129.2", (467.36, yv))
    for ref, x in (("C126", 429.26), ("C133", 452.12)):
        b.place(ref, x, yv + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.lab_at((467.36, yv), "R", spec="R129.2")
    lines = [("D112", "R130", 312.42), ("D113", "R131", 330.2), ("D115", None, 347.98), ("D116", None, 365.76)]
    xl, xe = 406.4, 449.58
    for d, r, y in lines:
        b.w((xl, y), (xe, y))
        b.lab_at((xl, y), "L", spec=d + ".2")
        b.place(d, 449.58, y + 3.81, 90, f="R")
        b.gnd(b.P(d + ".1"))
        if r:
            b.place(r, 426.72, y - 3.81, 0, f="R")
            b.w(b.P(r + ".2"), (426.72, y))
            b.pw(r + ".1", 0)
    b.note(480.06, 299.72, [
        "Touch: GT911 controller on the panel, J11 6-pin FPC (KLS L-KLS1-242D)",
        "I2C 400 kHz: R130/R131 2.2k are the ONLY pull-ups on the bus (ADS1115 shares it)",
        "TP_VDD = 3V3 through R129 0R, C126 100 nF + C133 1 nF at J11 pin 1",
        "TP_INT = IO32 (driven low at reset -> GT911 address 0x5D), RST = LCD_RST",
        "D112/D113/D115/D116 PESD5V0S1BA ESD diodes at J11 (EMC pass 4)",
    ])
    regions.append(("touch", 395, 250, 590, 372))
    # ------------------------------------------------------------------ backlight boost U11
    xu, yu = 177.8, 340.36
    y_r = yu - 10.16
    b.place("U11", xu, yu, 0, f={"Reference": (xu - 3.81, yu + 7.62, "right"), "Value": (xu - 3.81, yu + 10.16, "right")})
    b.power((xu - 121.92, y_r), "+5V")
    b.place("C127", xu - 114.3, y_r + 3.81, 0, f="R")
    b.gnd(b.P("C127.2"))
    b.place("L12", xu - 96.52, y_r, 270, f="A")
    b.w((xu - 121.92, y_r), "L12.2")
    b.place("R132", xu - 83.82, y_r + 3.81, 0, f="R")
    b.place("C128", xu - 83.82, y_r + 16.51, 0, f="R")
    b.w("R132.2", "C128.1")
    b.gnd(b.P("C128.2"))
    pd = b.P("R132.2")
    b.lab_at((pd[0], pd[1] + 2.54), "R", spec="R132.2")
    b.place("C124", xu - 60.96, y_r + 3.81, 0, f="R")
    b.gnd(b.P("C124.2"))
    b.place("L11", xu, y_r, 90, f="A")
    b.w("L12.1", "L11.1")
    b.flag((xu - 30.48, y_r))
    b.lab_at((xu - 50.8, y_r), "R", spec="L11.1")
    vin = b.P("U11.5")
    b.w(vin, (xu - 11.43, vin[1]), (xu - 11.43, y_r))
    sw = b.P("U11.1")
    b.w(sw, (xu + 11.43, sw[1]), (xu + 11.43, y_r))
    b.lab_at((xu + 11.43, sw[1]), "R", spec="U11.1")
    b.place("D111", xu + 19.05, y_r, 180, f="A")
    b.w("L11.2", (xu + 11.43, y_r), "D111.2")
    b.place("C125", xu + 33.02, y_r + 3.81, 0, f="R")
    b.gnd(b.P("C125.2"))
    b.place("D114", xu + 55.88, y_r + 3.81, 270, f="R")
    b.gnd(b.P("D114.2"))
    b.w("D111.1", (xu + 68.58, y_r))
    b.lab_at((xu + 68.58, y_r), "R", spec="D111.1")
    # FB: U11.FB -> BL_FB -> R126 0R -> VLED_N (R122 || R123 to GND)
    fb = b.P("U11.3")
    yf = yu + 12.7
    b.place("R126", xu + 29.21, yf, 90, f="A")
    b.w(fb, (xu + 13.97, fb[1]), (xu + 13.97, yf), "R126.1")
    b.lab_at((xu + 13.97, yf), "R", spec="U11.3")
    b.place("R122", xu + 40.64, yf + 3.81, 0, f="R")
    b.place("R123", xu + 58.42, yf + 3.81, 0, f="R")
    b.gnd(b.P("R122.2"))
    b.gnd(b.P("R123.2"))
    b.w("R126.2", (xu + 71.12, yf))
    b.lab_at((xu + 71.12, yf), "R", spec="R126.2")
    # EN: BL_PWM -> R128 0R -> BL_EN (R127 100k pull-down) -> U11.EN
    en = b.P("U11.4")
    b.place("R127", xu - 25.4, yu + 3.81, 0, f="L")
    b.gnd(b.P("R127.2"))
    b.place("R128", xu - 38.1, yu, 90, f="A")
    b.w("R128.2", "R127.1", en)
    b.lab_at((xu - 22.86, yu), "R", spec="U11.4")
    b.lab("R128.1", 5.08)
    b.pw("U11.2", 0)
    b.note(50.8, 375.92, [
        "Backlight boost: U11 MIC2288 (Microchip), 5 V -> VLED+ 9.6 V typ (8.7-10.5 V), 3 LEDs in series x 7 strings",
        "FB = 1.24 V across R122 || R123 (2 x 18 R 0.1 % -> 9 R) -> 138 mA; D114 MMSZ15V clamps an open LED string",
        "EN from the SSD1963 PWM pin through R128 0R, R127 100k pull-down (backlight off until the controller runs); PWM ~26 kHz",
        "Input pi-filter C127 10 uF | L12 10 uH | C124 10 uF, R132 0.5 R + C128 47 uF damper: corner 16 kHz with 10 uH (was 34 kHz with 2.2 uH)",
        "L11 10 uH Viking PCD0403MT100, D111 SS14; PWR_FLAG on BL_VIN: the rail is driven through L12 (passive)",
    ])
    regions.append(("backlight", 45, 315, 260, 392))
    return dict(paper="A2", name="Display", shift=(0, -38.1), date="2026-11-21" if NEW else "2026-11-13",
                c1="SSD1963 U10 with 8080 bus from the ESP32, RN series arrays to the 40-pin TFT J10",
                c2="Backlight boost U11 MIC2288, touch J11 (GT911), panel supply and EMC parts",
                regions=regions)
