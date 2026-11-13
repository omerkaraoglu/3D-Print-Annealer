"""Thermocouple sheet (A3): off-board probe | J20 + protection + RC filter | ADS1115 (top row), CJC dividers (bottom row)."""
import bomitem


def build(b, table):
    b.shapes = {"ADC_RDY": "output", "I2C_SDA": "bidirectional", "I2C_SCL": "input"}
    # ------------------------------------------------------------------ off-board probe (BOM item TC1)
    tc = table["TC1"]
    bomitem.instance(b.doc, "TC1", "K-type thermocouple, M6 ring tip, 1 m",
                     {"Datasheet": tc["url"], "Description": "K-type thermocouple probe, M6 ring-terminal tip, 1 m fibreglass/SS-braid lead, 0-600 C, bare ends into J20",
                      "MPN": tc["mpn"], "Manufacturer": tc["mfr"]})
    b.rect(15.24, 93.98, 66.04, 121.92)
    b.note(17.78, 97.79, ["Off-board: thermocouple probe wired to J20", "(red = TC_P, blue = TC_N)"])
    b.place("TC1", 29.21, 109.22, 0, f={"Reference": (38.1, 109.22, "left"), "Value": (17.78, 116.84, "left")})
    # ------------------------------------------------------------------ J20, protection, bias, RC filter
    Xj, Yj = 71.12, 106.68
    b.place("J20", Xj, Yj, 0, mirror="y", f={"Reference": (69.85, 100.33, "left"), "Value": (69.85, 102.87, "left")})
    Yp, Yn = 96.52, 121.92
    p1, p2 = b.P("J20.1"), b.P("J20.2")
    b.w(p1, (83.82, p1[1]), (83.82, Yp))
    b.w(p2, (81.28, p2[1]), (81.28, Yn))
    xe = 165.1
    b.lab_at((86.36, Yp), "R", spec="J20.1")
    b.lab_at((86.36, Yn), "R", spec="J20.2")
    # bias resistors: R222 pull-up on TC_P, R223 pull-down on TC_N
    b.place("R222", 96.52, Yp - 3.81, 0, f="R")
    b.pw("R222.1", 0)
    b.place("R223", 96.52, Yn + 3.81, 0, f="R")
    b.pw("R223.2", 0)
    # TVS to GND
    b.place("D220", 106.68, Yp + 3.81, 90, f="R")
    b.gnd(b.P("D220.1"))
    b.place("D221", 106.68, Yn + 3.81, 90, f="R")
    b.gnd(b.P("D221.1"))
    # series 1k
    b.place("R220", 123.19, Yp, 270, f="A")
    b.place("R221", 123.19, Yn, 270, f="A")
    b.w((83.82, Yp), b.P("R220.2"))
    b.w((81.28, Yn), b.P("R221.2"))
    b.w(b.P("R220.1"), (xe, Yp))
    b.w(b.P("R221.1"), (xe, Yn))
    # common-mode caps and the differential cap
    b.place("C221", 135.89, Yp + 3.81, 0, f="R")
    b.gnd(b.P("C221.2"))
    b.place("C222", 135.89, Yn + 3.81, 0, f="R")
    b.gnd(b.P("C222.2"))
    xc = 156.21
    b.place("C220", xc, (Yp + Yn) / 2, 0, f="R")
    b.w((xc, Yp), b.P("C220.1"))
    b.w(b.P("C220.2"), (xc, Yn))
    b.lab_at((xe, Yp), "R", spec="R220.1")
    b.lab_at((xe, Yn), "R", spec="R221.1")
    b.note(17.78, 144.78, [
        "Thermocouple input: J20 DEGSON DG127H-5.08-02P screw terminal, ESD protection, open-probe bias, RC filter",
        "D220/D221 PESD5V0S1BA bidirectional TVS to GND: ESD/EFT from the probe wiring",
        "R222/R223 10M on the terminal side of R220/R221 (their bias current does not flow through the 1k):",
        "an open probe pulls the inputs to the rails -> ADS1115 reads full scale -> firmware reports NAN",
        "R220/R221 1k 0.1% + C220 100 nF differential: fc = 1/(2*pi*2k*100n) = 0.8 kHz",
        "C221/C222 10 nF X7R common mode: fc = 16 kHz (X7R 10 % instead of C0G 1 %: no 10 nF C0G 0603 in stock; DC measurement)",
        "Layout: TC_P/TC_N as a tightly coupled pair, away from the triac/heater wiring and the LCD bus; single-point ground at U20",
    ])
    # ------------------------------------------------------------------ ADC U20
    Xu, Yu = 228.6, 109.22
    b.place("U20", Xu, Yu, 0, f={"Reference": (226.06, 92.71, "right"), "Value": (226.06, 95.25, "right")})
    for n in ("4", "5", "6", "7"):
        b.lab("U20." + n, 5.08)
    yr = 88.9
    b.w(b.P("U20.8"), (Xu, yr), (Xu + 50.8, yr))
    b.power((Xu, yr), "+3V3")
    b.pw("U20.3", 0)
    # ALERT/RDY with R224 pull-up from the VDD rail
    al = b.P("U20.2")
    xr = Xu + 17.78
    b.place("R224", xr, al[1] - 3.81, 0, f="R")
    b.w(b.P("R224.1"), (xr, yr))
    b.w(al, (Xu + 30.48, al[1]))
    b.lab_at((Xu + 30.48, al[1]), "R", spec="U20.2")
    b.lab("U20.10", 12.7)
    b.lab("U20.9", 17.78)
    b.pw("U20.1", 5.08)
    for ref, x in (("C223", Xu + 27.94), ("C224", Xu + 50.8)):
        b.place(ref, x, yr + 3.81, 0, f="R")
        b.gnd(b.P(ref + ".2"))
    b.note(200.66, 132.08, [
        "ADC: U20 ADS1115IDGSR (Texas Instruments), 16-bit delta-sigma, PGA, I2C",
        "AIN0-AIN1 differential, PGA +/-256 mV (7.8 uV/LSB = 0.19 C for K-type), 16 SPS",
        "ADDR = GND -> I2C address 0x48; ALERT/RDY -> ADC_RDY (ESP32 IO35), R224 10k pull-up",
        "C223 100 nF + C224 1 uF at VDD; the I2C pull-ups (R130/R131 2.2k) are on the Display sheet",
    ])
    # ------------------------------------------------------------------ cold junction dividers
    yt = 180.34
    for top, bot, cap, x, fl in (("TH220", "R225", "C225", 165.1, "R"), ("R226", "R227", "C226", 220.98, "R")):
        b.place(top, x, yt + 3.81, 0, f=fl)
        b.pw(top + ".1", 0)
        b.place(bot, x, yt + 13.97, 0, f="L")
        b.w(b.P(top + ".2"), b.P(bot + ".1"))
        b.gnd(b.P(bot + ".2"))
        tap = b.P(bot + ".1")
        b.place(cap, x + 12.7, tap[1] + 3.81, 0, f="R")
        b.gnd(b.P(cap + ".2"))
        b.w(tap, (x + 25.4, tap[1]))
        b.lab_at((x + 25.4, tap[1]), "R", spec=bot + ".1")
    b.note(142.24, 213.36, [
        "Cold junction: TH220 10k NTC B25/50 = 3380 K (Thinking TSM1B103F3381RZ), placed touching the J20 terminal metal",
        "TH220/R225 on AIN2 (NTC_MID), read ratiometrically against the R226/R227 half-supply on AIN3 (VREF_HALF):",
        "the 3.3 V tolerance cancels; C225/C226 100 nF filter the two taps",
    ])
    return dict(paper="A3", name="Thermocouple", shift=(38.1, 0),
                c1="K-type thermocouple J20 -> TVS, bias, RC filter -> ADS1115 U20 (I2C 0x48)",
                c2="Cold-junction NTC TH220 ratiometric on AIN2/AIN3; probe TC1 is BOM-only",
                regions=[("probe_input", 14, 82, 172, 168), ("adc", 195, 80, 300, 150), ("cjc", 138, 172, 280, 225)])
